from sqlalchemy.orm import aliased
from sqlalchemy.sql import functions, literal_column, or_, and_
from supplycrate import models
import supplycrate.tablerenderer.model as tmodels
from supplycrate.utils import decimal_str


__author__ = 'Mattia'


class NigredoTable(tmodels.Table):
    name = "nigredo"

    default_sorting_column = 5

    default_sorting_asc = False

    categories = {
        'kind': [
            'Mystic Weapons',
            'Various',
            'Material Promotions (common)',
            'Material Promotions (fine)',
            'Material Promotions (rare)',
            'Siege Blueprints'
        ]
    }

    def __init__(self, session):
        # prepare aliases
        self._output_item_alias = aliased(models.Item, name='output_item')
        self._ingredient_1_item_alias = aliased(models.Item, name='ingredient_1_item')
        self._ingredient_1_vendor_data_alias = aliased(models.VendorData, name='ingredient_1_vendor_data')
        self._ingredient_2_item_alias = aliased(models.Item, name='ingredient_2_item')
        self._ingredient_2_vendor_data_alias = aliased(models.VendorData, name='ingredient_2_vendor_data')
        self._ingredient_3_item_alias = aliased(models.Item, name='ingredient_3_item')
        self._ingredient_3_vendor_data_alias = aliased(models.VendorData, name='ingredient_3_vendor_data')
        self._ingredient_4_item_alias = aliased(models.Item, name='ingredient_4_item')
        self._ingredient_4_vendor_data_alias = aliased(models.VendorData, name='ingredient_4_vendor_data')
        self._ingredient_item_aliases = [
            self._ingredient_1_item_alias,
            self._ingredient_2_item_alias,
            self._ingredient_3_item_alias,
            self._ingredient_4_item_alias
        ]
        self._ingredient_vendor_data_aliases = [
            self._ingredient_1_vendor_data_alias,
            self._ingredient_2_vendor_data_alias,
            self._ingredient_3_vendor_data_alias,
            self._ingredient_4_vendor_data_alias
        ]
        # produce the labeled columns
        sum_func = lambda t1, t2: t1 + t2
        skill_point_cost = self._fold(
            lambda i: functions.coalesce(self._ingredient_vendor_data_aliases[i].skill_point_cost, literal_column("0")),
            sum_func
        ).label("skill_point_cost")
        ingredients_are_sold = and_(*self._map(
            lambda i: or_(self._ingredient_vendor_data_aliases[i].skill_point_cost != None,
                          self._ingredient_vendor_data_aliases[i].copper_cost != None,
                          self._ingredient_item_aliases[i].sell_count > literal_column("0"))
        )).label("ingredients_are_sold")
        self.__ingredients_are_sold = ingredients_are_sold
        output_is_bought = (self._output_item_alias.buy_count > literal_column("0")).label("output_is_bought")
        self.__output_is_bought = output_is_bought
        cost_bo, cost_bi = self._buy_o(
            lambda buy, o:
            self._fold(
                lambda i: self._if(
                    self._ingredient_vendor_data_aliases[i].copper_cost == None,
                    self._get_price(self._ingredient_item_aliases[i], buy),
                    self._least(self._ingredient_vendor_data_aliases[i].copper_cost,
                                self._get_price(self._ingredient_item_aliases[i], buy))
                ) * self._get_ingredient_count(i),
                sum_func
            ).label("cost_b" + o)
        )
        cost_b = {
            "o": cost_bo,
            "i": cost_bi
        }
        profit_so, profit_si = self._buy_i(
            lambda buy, i:
            (self._get_price(self._output_item_alias, buy) * models.SkillPointRecipe.output_count *
             literal_column("85") / literal_column("100")).
            label("profit_s" + i)
        )
        profit_s = {
            "o": profit_so,
            "i": profit_si
        }
        net_profit_bo_so_per_sp, net_profit_bo_si_per_sp, \
        net_profit_bi_so_per_sp, net_profit_bi_si_per_sp = self._b_s(
            lambda b, s, buy, sell: (
                self._round(
                    (profit_s[s] - cost_b[b]) /
                    self._fold(
                        lambda i: functions.coalesce(
                            self._ingredient_vendor_data_aliases[i].skill_point_cost,
                            literal_column("0")),
                        sum_func))
            ).label("net_profit_b" + b + "_s" + s + "_per_sp")
        )
        # produce the query
        queryset = session.query(
            models.SkillPointRecipe,
            self._output_item_alias,
            self._ingredient_1_item_alias,
            self._ingredient_1_vendor_data_alias,
            self._ingredient_2_item_alias,
            self._ingredient_2_vendor_data_alias,
            self._ingredient_3_item_alias,
            self._ingredient_3_vendor_data_alias,
            self._ingredient_4_item_alias,
            self._ingredient_4_vendor_data_alias,
            skill_point_cost,
            ingredients_are_sold,
            output_is_bought,
            cost_bo,
            cost_bi,
            profit_so,
            profit_si,
            net_profit_bo_so_per_sp,
            net_profit_bo_si_per_sp,
            net_profit_bi_so_per_sp,
            net_profit_bi_si_per_sp
        ). \
            join(self._output_item_alias, models.SkillPointRecipe.output_item). \
            outerjoin((self._ingredient_1_item_alias, models.SkillPointRecipe.ingredient_1_item),
                      (self._ingredient_1_vendor_data_alias,
                       self._ingredient_1_vendor_data_alias.item_id == self._ingredient_1_item_alias.data_id)). \
            outerjoin((self._ingredient_2_item_alias, models.SkillPointRecipe.ingredient_2_item),
                      (self._ingredient_2_vendor_data_alias,
                       self._ingredient_2_vendor_data_alias.item_id == self._ingredient_2_item_alias.data_id)). \
            outerjoin((self._ingredient_3_item_alias, models.SkillPointRecipe.ingredient_3_item),
                      (self._ingredient_3_vendor_data_alias,
                       self._ingredient_3_vendor_data_alias.item_id == self._ingredient_3_item_alias.data_id)). \
            outerjoin((self._ingredient_4_item_alias, models.SkillPointRecipe.ingredient_4_item),
                      (self._ingredient_4_vendor_data_alias,
                       self._ingredient_4_vendor_data_alias.item_id == self._ingredient_4_item_alias.data_id))
        # create column definitions
        column_descriptions = [
            tmodels.ColumnDescription('Item', True, self._output_item_alias.name, name='item'),
            tmodels.ColumnDescription('Ingredients', True, None, name='ingredients'),
            tmodels.ColumnDescription('Skill point cost', True, skill_point_cost, name='skillpointcost'),
            tmodels.ColumnDescription('Gold cost', True, [[cost_bo, cost_bo], [cost_bi, cost_bi]], name='goldcost'),
            tmodels.ColumnDescription('Profit', True, [[profit_so, profit_si], [profit_so, profit_si]], name='profit'),
            tmodels.ColumnDescription('Net profit per skill point', True,
                                      [[net_profit_bo_so_per_sp, net_profit_bo_si_per_sp],
                                       [net_profit_bi_so_per_sp, net_profit_bi_si_per_sp]], name='netprofit')
        ]
        # call super constructor
        tmodels.Table.__init__(self, column_descriptions, queryset)

    def _get_ingredient_count(self, i):
        if i == 0:
            return models.SkillPointRecipe.ingredient_1_count
        elif i == 1:
            return models.SkillPointRecipe.ingredient_2_count
        elif i == 2:
            return models.SkillPointRecipe.ingredient_3_count
        elif i == 3:
            return models.SkillPointRecipe.ingredient_4_count

    def filter_by_buy_sell(self, queryset, buy_instant, sell_instant):
        if buy_instant:
            queryset = queryset.filter(self.__ingredients_are_sold == 1)
        if sell_instant:
            queryset = queryset.filter(self.__output_is_bought == 1)
        return queryset

    def filter_by_category(self, queryset, category_name, category_values):
        my_categories = self.categories['kind']
        if len(category_values) == len(my_categories):
            return queryset  # all categories are in
        else:
            return queryset.filter(
                or_(
                    *(models.SkillPointRecipe.category == self.categories['kind'].index(category) for category in
                      category_values)))

    def create_row(self, query_row):
        # create ingredient list
        ingredients = []
        for idx in xrange(4):
            i = self._get_qr(query_row, self._ingredient_item_aliases[idx])
            c = query_row.SkillPointRecipe.get_ingredient_count(idx)
            v = self._get_qr(query_row, self._ingredient_vendor_data_aliases[idx])
            extra = []
            if c > 1:
                extra.append(tmodels.Text([str(c) + ' x']))
            sp_cost = v.skill_point_cost if v is not None else None
            if sp_cost is None:
                extra.append(tmodels.Cost([[i.buy_price, i.buy_price],
                                           [i.sell_price, i.sell_price]]))
            else:
                extra.append(tmodels.Text([str(sp_cost), tmodels.Text.SKILL_POINT_SYMBOL]))
            ingredients.append(tmodels.Item(i, extra_pre_line=extra))
        # create row
        spc = decimal_str(query_row.skill_point_cost)  # TODO: perhaps dict access?
        row = tmodels.Row([
            tmodels.Cell([tmodels.Item(self._get_qr(query_row, self._output_item_alias))]),
            tmodels.Cell(ingredients),
            tmodels.Cell([tmodels.Text([spc, tmodels.Text.SKILL_POINT_SYMBOL])]),
            tmodels.Cell([tmodels.Cost.from_object(query_row, 'cost_b%(b)s')]),
            tmodels.Cell([tmodels.Cost.from_object(query_row, 'profit_s%(s)s')]),
            tmodels.Cell([tmodels.Cost.from_object(query_row, 'net_profit_b%(b)s_s%(s)s_per_sp')])
        ])
        # return it
        return row