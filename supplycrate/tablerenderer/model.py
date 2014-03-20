import datetime
from sqlalchemy import case, cast, Integer, inspect, func

__author__ = 'Mattia'


class Part(object):
    """A part of a cell content."""

    def __init__(self, kind):
        """
        Create a new Part object.

        kind: a str/unicode to identify the kind of part.
        """
        self.kind = kind


class Cost(Part):
    """
    A cost to buy or sell an item on the TP, which can vary according to whether we are buying
    instantaneously or through order, and sell instantaneously or through order.
    """

    def __init__(self, price_matrix):
        """
        Creates a new cost, whose value depends on whether we buy instantly or not, and whether
        we sell instantly or not.

        price_matrix: a 2x2 matrix (list of lists), where price_matrix[buy_instantly][sell_instantly] contains
            the actual price.
        """
        Part.__init__(self, 'cost')
        self.price_matrix = price_matrix

    def __neg__(self):
        p = self.price_matrix
        return Cost([[-p[0][0], -p[0][1]], [-p[1][0], -p[1][1]]])

    def __add__(self, other):
        p1 = self.price_matrix
        p2 = other.price_matrix
        return Cost([[p1[0][0] + p2[0][0], p1[0][1] + p2[0][1]],
                     [p1[1][0] + p2[1][0], p1[1][1] + p2[1][1]]])

    def __sub__(self, other):
        return self + (-other)

    def __getitem__(self, key):
        if not hasattr(key, '__len__'):
            raise TypeError()
        elif len(key) == 2:
            buy_instant, sell_instant = key
            return self.price_matrix[int(buy_instant)][int(sell_instant)]
        else:
            raise KeyError()

    @staticmethod
    def create_matrix(str_pattern):
        return [[(str_pattern % {'b': 'o', 's': 'o'},), (str_pattern % {'b': 'o', 's': 'i'},)],
                [(str_pattern % {'b': 'i', 's': 'o'},), (str_pattern % {'b': 'i', 's': 'i'},)]]

    @staticmethod
    def from_object(obj, str_pattern):
        return Cost(
            [[getattr(obj, str_pattern % {'b': 'o', 's': 'o'}), getattr(obj, str_pattern % {'b': 'o', 's': 'i'})],
             [getattr(obj, str_pattern % {'b': 'i', 's': 'o'}), getattr(obj, str_pattern % {'b': 'i', 's': 'i'})]])

    @staticmethod
    def constant(cost):
        return Cost([[cost, cost], [cost, cost]])


class Text(Part):
    """A text to display. It can be a mixture of text and special symbols (like currencies)."""

    KARMA_SYMBOL = 1
    SKILL_POINT_SYMBOL = 2

    def __init__(self, contents):
        """
        Create a new text object.

        contents: a list of unicode and numbers; the numbers must match the symbols in this
            class for displaying special symbols.
        """
        Part.__init__(self, 'text')
        self.contents = contents


class Currency(Part):
    """
    A non-gold currency.
    """

    KARMA = 1
    SKILL_POINT = 2

    def __init__(self, amount, currency):
        """
        Create a new currency object.

        amount: the amount of this currency (can be a non-integer number)
        currency: the currency used, taken between the symbols in this class.
        """
        Part.__init__(self, 'currency')
        self.amount = amount
        self.currency = currency


class Item(Part):
    """An item to display."""

    def __init__(self, item, extra_pre_line=None):
        """
        Create a new item object.

        item: a processor.models.Item object.
        extra_pre_line: an extra line to insert over the name; it is either None or a list of
            Text and Cost elements
        """
        Part.__init__(self, 'item')
        self.inner_item = item
        self.extra_pre_line = extra_pre_line

    @property
    def icon(self):
        return "https://render.guildwars2.com/file/%s/%s.png" % (
            self.inner_item.icon_file_signature,
            self.inner_item.icon_file_id
        )


class SpecialItem(Part):
    """A special item, not corresponding to anything in the DB."""

    def __init__(self, name, first_line, second_line, icon, extra_pre_line=None):
        """
        Create a new SpecialItem.

        name: name of the special item
        first_line: first line of description
        second_line: second line of description
        icon: url of the icon to use
        extra_pre_line: an extra line to insert over the name; it is either None or a list of
            Text and Cost elements
        """
        Part.__init__(self, 'specialitem')
        self.name = name
        self.first_line = first_line
        self.second_line = second_line
        self.icon = icon
        self.__extra_pre_line = extra_pre_line

    @property
    def extra_pre_line(self):
        return self.__extra_pre_line


class ColumnDescription(object):
    """Description of a column."""

    def __init__(self, title, has_right_border, queryset_sorting_keys, name=None):
        """
        Create a new column description.

        title: title of the column, as a Text object.
        has_right_border: whether this column displays a right border or not.
        queryset_sorting_keys: a matrix of tuple of keys to use in order to sort the queryset on this column;
            each tuple represent the value(s) to use for the [buy_instantly][sell_instantly] cases;
            if the object is just a tuple, it's assumed that all the values are the same.
        name: name of the column, to give a class to the header and cells of this column.
        """
        self.title = title
        self.has_right_border = has_right_border
        if not isinstance(queryset_sorting_keys, list):
            q = queryset_sorting_keys
            queryset_sorting_keys = [[(q,), (q,)], [(q,), (q,)]]
        if not isinstance(queryset_sorting_keys[0][0], tuple):
            q = queryset_sorting_keys
            queryset_sorting_keys = [[(q[0][0],), (q[0][1],)], [(q[1][0],), (q[1][1],)]]
        self.queryset_sorting_keys = queryset_sorting_keys
        self.name = name

    def order_queryset(self, queryset, asc=True):
        """
        Starting from given queryset, returns a new one ordered according to given
        parameters. If queryset_sorting_keys is sufficient, there's no need to overload
        order_queryset.

        queryset: the queryset to order
        asc: whether the order is ascending
        """
        keys = self.queryset_sorting_keys
        if not asc:
            keys = ['-' + key if key[0] != '-' else key[1:] for key in keys]
        return queryset.order_by(*keys)


class Table(object):
    """A whole table."""

    # A name for the table, used to give a base class element
    name = None

    # a map between category names and list of values for that category
    categories = {}

    # the column to sort the results with the first time
    default_sorting_column = 0

    # whether to sort by default in ascending order or descending
    default_sorting_asc = True

    def __init__(self, column_descriptions, queryset):
        """
        Creates a new table.

        queryset: the base queryset that returns all the results.
        column_descriptions: a list of ColumnDescription.
        """
        self.column_descriptions = column_descriptions
        self.queryset = queryset

    def create_row(self, query_row):
        """
        Create a Row object starting for a row obtained from the queryset_generator.
        If not overloaded, then create_row2 must be overloaded.

        query_row: the row obtained from the query that must be transformed
        """
        raise NotImplementedError()

    def filter_by_buy_sell(self, queryset, buy_instant, sell_instant):
        """
        Allows an extra filtering of the queryset according to buy_instant and sell_instant
        booleans. Returns the new queryset. By default, the queryset isn't changed.
        """
        return queryset

    def filter_by_category(self, queryset, category_name, category_values):
        """
        Starting from given queryset, return a new queryset that only contains given
        category values for the category set they belong to. Must be overloaded if
        categories are supported.

        queryset: a QuerySet to filter.
        category_name: name of the category family being filtered.
        categories: a list of unicode containing the category names to be included.
        """
        raise NotImplementedError()

    @staticmethod
    def _if(condition, satisfied, unsatisfied):
        """
        Produce an "if" sqlalchemy expressions.
        """
        return case([(condition, satisfied)], else_=unsatisfied)

    @classmethod
    def _least(cls, *args):
        """
        Produce a "least" sqlalchemy expression (minimum between values)
        """
        #return cls._if(a < b, a, b)
        return func.least(*args)

    @staticmethod
    def _round(sql):
        """
        Produce a round statement.
        """
        return cast(sql, Integer)

    @staticmethod
    def _map(element_func):
        """Map [0,1,2,3] over element_func."""
        return map(element_func, xrange(4))

    @classmethod
    def _fold(cls, element_func, fold_func):
        """Map [0,1,2,3] over element_func, then fold the element list using the fold_func."""
        return reduce(fold_func, cls._map(element_func))

    @staticmethod
    def _buy_o(element_func):
        """Map [('buy', 'o'), ('sell', 'i')] on element_func."""
        return map(lambda (buy, o): element_func(buy, o), [('buy', 'o'), ('sell', 'i')])

    @staticmethod
    def _buy_i(element_func):
        """Map [('sell', 'o'), ('buy', 'i')] on element_func."""
        return map(lambda (buy, o): element_func(buy, o), [('sell', 'o'), ('buy', 'i')])

    @staticmethod
    def _b_s(element_func):
        """
        Map [('o', 'o', 'buy', 'sell'), ('o', 'i', 'buy', 'buy'),
        ('i', 'o', 'sell', 'sell'), ('i', 'i', 'sell', 'buy')] to element_func (suggested parameter
        names: b, s, buy, sell).
        """
        seq = [
            ('o', 'o', 'buy', 'sell'),
            ('o', 'i', 'buy', 'buy'),
            ('i', 'o', 'sell', 'sell'),
            ('i', 'i', 'sell', 'buy')]
        return map(lambda (b, s, buy, sell): element_func(b, s, buy, sell),
                   seq)

    @staticmethod
    def _get_price(element, long_name):
        """
        Gets a "<long_name>_price" attribute from "element".
        """
        return getattr(element, long_name + "_price")

    @staticmethod
    def _get_qr(qr, alias):
        """
        Given a row from a query, returns the value corresponding the an aliased column.
        """
        name = inspect(alias).name
        return getattr(qr, name)

    @classmethod
    def _create_cost(cls, qr, matrix):
        """
        Given a query row and a matrix of aliases expressed as matrix["o" or "i"]["o" or "i"],
        creates a Cost object.
        """
        return Cost([
            [cls._get_qr(qr, matrix["o"]["o"]), cls._get_qr(qr, matrix["o"]["i"])],
            [cls._get_qr(qr, matrix["i"]["o"]), cls._get_qr(qr, matrix["i"]["i"])]])


class Row(object):
    """A row displayed in the rendered table."""

    def __init__(self, cells, last_update=None):
        """
        Create a new row.

        cells: a list of Cell objects.
        last_update: time of the last global update of the data contained in this row; if it's
            too old in the past (longer than MAX_LIFE) the row is marked with old=True, otherwise
            it's old=False (or if last_update is None, thus disabling this check)
        """
        self.cells = cells
        self.old = self.__is_old(last_update)

    MAX_LIFE = datetime.timedelta(0, 5 * 60)

    def __is_old(self, last_update):
        if last_update is None:
            return False
        else:
            return datetime.datetime.now() - last_update > Row.MAX_LIFE


class Cell(object):
    """A cell in a row."""

    def __init__(self, parts):
        """
        Create a new cell.

        parts: the parts that describe the content of this cell; this is a list of any mixture of Item, Text,
            Cost or Currency objects.
        """
        self.parts = parts