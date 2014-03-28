import urllib
from pyramid.renderers import render_to_response
import transaction
from supplycrate.tablerenderer import model
from supplycrate.models import Item as MItem, DBSession


__author__ = 'Mattia'
_cat_prefix = 'trcat_'


class Url(object):
    def __init__(self, kwargs):
        self.__kwargs = kwargs

    @property
    def kwargs(self):
        return dict(self.__kwargs)

    def __str__(self):
        rv = urllib.urlencode(self.kwargs, True)
        return rv


class _GenericWrapper(object):
    def __init__(self, inner_object, wraps, buy_instant, sell_instant):
        self.__inner_object = inner_object
        self.__buy_instant = buy_instant
        self.__sell_instant = sell_instant
        self.__wraps = wraps

    def __getattr__(self, name):
        value = getattr(self.__inner_object, name)
        rv = self.__wrap(value)
        return rv

    def __wrap(self, value):
        if isinstance(value, list):
            return map(self.__wrap, value)
        for (wrapped_class, wrapper) in self.__wraps:
            if isinstance(value, wrapped_class):
                return wrapper(value, self.__buy_instant, self.__sell_instant)
        return value


class _ColumnDescriptionWrapper(_GenericWrapper):
    def __init__(self, table, column_description, num, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, column_description, [], buy_instant, sell_instant)
        self.__table = table
        self.__num = num

    @property
    def current_sort_order(self):
        if self.__table.sorting_column == self.__num:
            return 'desc' if self.__table.sorting_desc else 'asc'
        else:
            return ''

    @property
    def anchor_sort_order(self):
        if self.__table.sorting_column == self.__num:
            return 'asc' if self.__table.sorting_desc else 'desc'
        else:
            return 'asc'


class Page(object):
    def __init__(self, num, text, has_link):
        self.num = num
        self.text = text
        self.has_link = has_link

    def __str__(self):
        return self.text


class _TableWrapper(_GenericWrapper):
    PAGE_SIZE = 20

    def __init__(self, inner_object, buy_instant, sell_instant, categories, sort, order, page):
        _GenericWrapper.__init__(self, inner_object, [], buy_instant, sell_instant)
        self.__sorting_column = sort
        self.__asc = order == 'asc'
        self.__buy_instant = buy_instant
        self.__sell_instant = sell_instant
        self.__categories = categories
        self.page = int(page)
        self.__num_rows = self.__filter_categories().count()

    def __filter_categories(self):
        if not self.categories:
            return self.queryset
        queryset = self.queryset
        for name, values in self.__categories.items():
            queryset = self.filter_by_category(queryset, name, values)
        return queryset

    def categories_data(self):
        global _cat_prefix
        for key, values in self.categories.items():
            if key not in self.__categories:
                lst = [(value, True) for value in values]
            else:
                lst = [(value, value in self.__categories[key]) for value in values]
            yield (key, _cat_prefix + key, lst)

    @property
    def sorting_column(self):
        return self.__sorting_column

    @property
    def sorting_desc(self):
        return not self.__asc

    def __inner_pages(self):
        ps = _TableWrapper.PAGE_SIZE
        num_around = 2  # there are num_around links to the left of the current page, and num_around links to the right
        last_page = (self.__num_rows + ps - 1) / ps
        if self.page - num_around > 1:
            yield Page(1, "1", True)
        if self.page - num_around > 2:
            yield Page(None, "...", False)
        for i in range(max(1, self.page - num_around), min(self.page + num_around + 1, last_page + 1)):
            yield Page(i, str(i), True)
        if self.page + num_around < last_page - 1:
            yield Page(None, "...", False)
        if self.page + num_around < last_page:
            yield Page(last_page, str(last_page), True)

    @property
    def pages(self):
        return list(self.__inner_pages())

    @property
    def extended_column_descriptions(self):
        for i, column_description in enumerate(self.column_descriptions):
            yield _ColumnDescriptionWrapper(self, column_description, i, self.__buy_instant, self.__sell_instant)

    def order_queryset(self, qs, column, asc):
        # TODO
        # get sorting column
        sorting_column = self.column_descriptions[self.__sorting_column]
        # get sorting keys
        sorting_keys = sorting_column.queryset_sorting_keys[int(self.__buy_instant)][int(self.__sell_instant)]
        # apply '-' if the order has been reversed
        if not asc:
            sorting_keys = map(lambda s: s.desc(), sorting_keys)
        # order the query set
        ordered_qs = qs.order_by(*sorting_keys)
        # return it
        return ordered_qs

    def rows(self):
        # filter the query set
        filtered_queryset = self.__filter_categories()
        # apply extra filtering
        filtered_queryset = self.filter_by_buy_sell(filtered_queryset,
                                                    self.__buy_instant != '0', self.__sell_instant != '0')
        # sort the queryset
        sorted_queryset = self.order_queryset(filtered_queryset, self.__sorting_column, self.__asc)
        # page the queryset
        ps = _TableWrapper.PAGE_SIZE
        paged_queryset = sorted_queryset.slice((self.page - 1) * ps, self.page * ps)
        # create the rows
        rows = map(self.create_row, paged_queryset.all())
        mapped_rows = map(lambda row: _RowWrapper(row, self.__buy_instant, self.__sell_instant), rows)
        return mapped_rows


class _RowWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object, [(model.Cell, _CellWrapper)], buy_instant, sell_instant)


class _CellWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object,
                                 [(model.Cost, _CostWrapper),
                                  (model.Item, _ItemWrapper),
                                  (model.SpecialItem, _SpecialItemWrapper),
                                  (model.Text, _TextWrapper),
                                  (model.Currency, _CurrencyWrapper)],
                                 buy_instant, sell_instant)


class _SpecialItemWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object,
                                 [(model.Cost, _CostWrapper),
                                  (model.Text, _TextWrapper), ],
                                 buy_instant, sell_instant)

    def sorting_key(self):
        return self.inner_item.name


def _correct_name(n):
    n = n.replace('_', ' ')
    return n[0].upper() + n[1:].lower()


class _ItemWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object,
                                 [(model.Cost, _CostWrapper),
                                  (model.Text, _TextWrapper), ],
                                 buy_instant, sell_instant)

    @property
    def first_line(self):
        """First line of description for this item"""
        return _correct_name(MItem.TYPE_CHOICES[self.inner_item.type])

    @property
    def second_line(self):
        """Second line of description for this item"""
        i = self.inner_item
        t = i.type
        if t == MItem.WEAPON:
            l = MItem.WEAPON_TYPE_CHOICES[i.weapon_type]
        elif t == MItem.ARMOR:
            l = MItem.ARMOR_WEIGHT_CHOICES[i.armor_weight] + ' ' + MItem.ARMOR_TYPE_CHOICES[i.armor_type]
        elif t == MItem.TRINKET:
            l = MItem.TRINKET_TYPE_CHOICES[i.trinket_type]
        else:
            l = ''
        if l:
            l = _correct_name(l)
        return l

    def data_id(self):
        return self.inner_item.data_id

    def external_id(self):
        return self.inner_item.external_id

    def sorting_key(self):
        return self.inner_item.name


class PriceElement(object):
    def __init__(self, amount, currency):
        self.amount = amount
        self.currency = currency


def _split_price(price):
    neg = price < 0
    if neg:
        price = -price
    coppers = price % 100
    price /= 100
    silvers = price % 100
    price /= 100
    golds = price
    rv = []
    if golds != 0:
        rv.append(PriceElement(golds if not neg else -golds, 'gold'))
        neg = False
    if golds != 0 or silvers != 0:
        rv.append(PriceElement(silvers if not neg else -silvers, 'silver'))
        neg = False
    rv.append(PriceElement(coppers if not neg else -coppers, 'copper'))
    return rv


class _CostWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object, [], buy_instant, sell_instant)
        self.real_cost = inner_object[int(buy_instant), int(sell_instant)]
        if self.real_cost is None:
            print "oh "
        assert self.real_cost is not None

    @property
    def costparts(self):
        return _split_price(int(self.real_cost))

    def sorting_key(self):
        return self.real_cost


class _TextWrapperPart(object):
    def __init__(self, kind, text, icon):
        self.kind = kind
        self.text = text
        self.icon = icon


class _TextWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object, [], buy_instant, sell_instant)

    def sorting_key(self):
        return self.inner_object.contents[0]

    def parts(self):
        for part in self.contents:
            if part == model.Text.KARMA_SYMBOL:
                yield _TextWrapperPart("icon", None, "supplycrate:static/img/karma.png")
            elif part == model.Text.SKILL_POINT_SYMBOL:
                yield _TextWrapperPart("icon", None, "supplycrate:static/img/skill_point.png")
            else:
                yield _TextWrapperPart("text", part, None)


class _CurrencyWrapper(_GenericWrapper):
    def __init__(self, inner_object, buy_instant, sell_instant):
        _GenericWrapper.__init__(self, inner_object, [], buy_instant, sell_instant)

    def sorting_key(self):
        return self.inner_object.amount


def get_categories(request):
    global _cat_prefix
    rv = {}
    for key in request.GET:
        if key.startswith(_cat_prefix):
            value = request.GET.getall(key)
            name = key[len(_cat_prefix):]
            rv[name] = value
    return rv


def table_render(request, table_class):
    buy_instant = request.GET.get('buy_instant', '1')
    sell_instant = request.GET.get('sell_instant', '1')
    sort = int(request.GET.get('sort', table_class.default_sorting_column))
    order = request.GET.get('order', 'asc' if table_class.default_sorting_asc else 'desc')
    page = request.GET.get('page', '1')
    categories = get_categories(request)
    query_dict = {
        'buy_instant': buy_instant,
        'sell_instant': sell_instant,
        'order': order,
    }
    if sort:
        query_dict['sort'] = sort
    for key, values in categories.items():
        query_dict[_cat_prefix + key] = values
    session = DBSession()
    with transaction.manager:
        table = table_class(session)
        wrapped_table = _TableWrapper(table, buy_instant, sell_instant, categories, sort, order, page)
        return render_to_response(
            'supplycrate:templates/tablerenderer.jinja2',
            dict(table=wrapped_table,
                 query_args=Url(query_dict),
                 querydct=query_dict,
                 request=request,
                 buy_instant=buy_instant == '1',
                 sell_instant=sell_instant == '1'),
            request=request)