from sqlalchemy import or_, inspect
from sqlalchemy.orm import aliased
from supplycrate import models
from supplycrate.models import Item
from supplycrate.tablerenderer.model import Table, ColumnDescription, Cost
import supplycrate.tablerenderer.model as tmodels
from supplycrate import utils

__author__ = 'Mattia'
logger = utils.get_logger()


class GrandmasterTable(Table):
    categories = {
        'profession': [
            u'Armorsmith',
            u'Artificer',
            u'Huntsman',
            u'Leatherworker',
            u'Tailor',
            u'Weaponsmith',
            u'Chef',
            u'Jeweler'
        ],
        'level': [
            u'Exotic',
            u'Non-Exotic'
        ]
    }

    default_sorting_column = 4

    default_sorting_asc = False

    name = 'grandmaster'

    def __init__(self, session):
        # create aliases
        output_item = aliased(models.Item, name='output_item')
        self.__output_item = output_item
        ingredients = []
        for i in range(4):
            ingredients.append(aliased(models.Item, name='ingredient_%d_item' % (i+1)))
        self.__ingredients = ingredients
        vendor_datas = []
        for i in range(4):
            vendor_datas.append(aliased(models.VendorData, name='vendor_data_%d' % (i + 1)))
        cost_bo, cost_bi = Table._buy_o(
            lambda l, s: sum(models.Recipe.count_attributes()[idx] * getattr(ingredients[idx], l + '_price')
                             for idx
                             in range(4)).label("cost_b" + s))
        cost_b = {
            'o': cost_bo,
            'i': cost_bi
        }
        profit_so, profit_si = Table._buy_i(
            lambda l, s: (
                models.Recipe.output_item_count * getattr(output_item, l + "_price") * 0.85
            ).label("profit_s" + s)
        )
        profit_s = {
            'o': profit_so,
            'i': profit_si
        }
        net_profit_bo_so, net_profit_bo_si, net_profit_bi_so, net_profit_bi_si = Table._b_s(
            lambda b, s, buy, sell: (profit_s[s] - cost_b[b]).label('net_profit_b%s_s%s' % (b, s))
        )
        # create query
        query = session.query(
            models.Recipe,
            output_item,
            ingredients[0],
            ingredients[1],
            ingredients[2],
            ingredients[3],
            cost_bo,
            cost_bi,
            profit_so,
            profit_si,
            net_profit_bo_so,
            net_profit_bo_si,
            net_profit_bi_so,
            net_profit_bi_si). \
            join(output_item, models.Recipe.output_item_id == output_item.data_id)
        for i in range(4):
            query = query. \
                outerjoin(ingredients[i],
                          models.Recipe.ingredient_1_item_id == ingredients[i].data_id). \
                outerjoin(vendor_datas[i],
                          vendor_datas[i].item_id == ingredients[i].data_id)
        # set query filters
        query = query.filter(
            output_item.buy_price > 0,
            or_(vendor_datas[0].copper_cost > 0, ingredients[0].sell_price > 0),
            or_(models.Recipe.ingredient_2_item_id == None, vendor_datas[1].copper_cost > 0,
                ingredients[1].sell_price > 0),
            or_(models.Recipe.ingredient_3_item_id == None, vendor_datas[2].copper_cost > 0,
                ingredients[2].sell_price > 0),
            or_(models.Recipe.ingredient_4_item_id == None, vendor_datas[3].copper_cost > 0,
                ingredients[3].sell_price > 0),
            output_item.buy_price > 0,
            models.Recipe.autolearned == False,
            models.Recipe.learned_from_item == False,
        )
        logger.debug("Used query is:\n%s", utils.dump_query(query))
        # create column descriptions
        column_descriptions = [
            ColumnDescription('Item', True, output_item.name, name='item'),
            ColumnDescription('Ingredients', True, None, name='ingredients'),
            ColumnDescription('Cost', True,
                              [[cost_bo, cost_bo],
                               [cost_bi, cost_bi]],
                              name='goldcost'),
            ColumnDescription('Profit', True,
                              [[profit_so, profit_si],
                               [profit_so, profit_si]],
                              name='profit'),
            ColumnDescription('Net profit', True,
                              [[net_profit_bo_so, net_profit_bo_si],
                               [net_profit_bi_so, net_profit_bi_si]],
                              name='netprofit')
        ]
        Table.__init__(self, column_descriptions, query)

    def filter_by_category(self, queryset, category_name, category_values):
        #output_item__rarity = Item.EXOTIC,
        if category_name == 'profession':
            or_terms = []
            for category_value in category_values:
                or_terms.append(getattr(models.Recipe, 'can_%s' % category_value.lower()) == True)
            return queryset.filter(or_(*or_terms))
        else:  # level
            if len(category_values) == 2:
                return queryset  # both categories
            elif category_values == ['Exotic']:
                return queryset.filter(self.__output_item.rarity == Item.EXOTIC)
            else:  # non-exotic
                return queryset.filter(self.__output_item.rarity != Item.EXOTIC)

    def create_row(self, query_row):
        # create cost element
        cost = Cost.from_object(query_row, 'cost_b%(b)s')
        # create profit element
        profit = Cost.from_object(query_row, 'profit_s%(s)s')
        # create net profit element
        net_profit = Cost.from_object(query_row, 'net_profit_b%(b)s_s%(s)s')
        # create the ingredients
        ingredients = []
        for i in range(4):
            ing = self._get_qr(query_row, self.__ingredients[i])
            if ing is not None:
                count = getattr(query_row.Recipe, 'ingredient_%d_count' % (i+1))
                ingredients.append(tmodels.Item(ing, extra_pre_line=[
                    tmodels.Text([unicode(count), u'x']),
                    tmodels.Cost([[ing.buy_price, ing.buy_price], [ing.sell_price, ing.sell_price]])]))
        # create the row
        row = tmodels.Row([
            tmodels.Cell([tmodels.Item(query_row.output_item,
                                       extra_pre_line=[tmodels.Text([
                                           unicode(query_row.Recipe.output_item_count),
                                           u'x'])])]),
            tmodels.Cell(ingredients),
            tmodels.Cell([cost]),
            tmodels.Cell([profit]),
            tmodels.Cell([net_profit])
        ])
        # return it
        return row
