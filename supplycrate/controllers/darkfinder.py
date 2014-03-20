from sqlalchemy.orm import aliased
from supplycrate import models
import supplycrate.tablerenderer.model as tmodels


__author__ = 'Mattia'


class DarkfinderTable(tmodels.Table):
    name = "darkfinder"

    default_sorting_column = 4

    default_sorting_asc = False

    def __init__(self, session):
        # prepare table aliases for all tables except main one
        self._glob_of_ecto_alias = aliased(models.Item, name='glob_of_ecto')
        self._upgrade_alias = aliased(models.Item, name='upgrade')
        # prepare named aliases
        profit_so, profit_si = self._buy_i(
            lambda l, s: (
                (self._get_price(self._upgrade_alias, l) +
                 1.2 * self._get_price(self._glob_of_ecto_alias, l)) * 0.85). \
            label("profit_s" + s)
        )
        self._profit_s = {'i': profit_si, 'o': profit_so}
        net_profit_bo_so, net_profit_bo_si, \
        net_profit_bi_so, net_profit_bi_si = self._b_s(
            lambda b, s, buy, sell: (
                self._profit_s[s] - self._get_price(models.Item, buy)
            ).label("net_profit_b" + b + "_s" + s)
        )
        self._net_profit_b_s = {
            'o': {
                'o': net_profit_bo_so,
                'i': net_profit_bo_si
            },
            'i': {
                'o': net_profit_bi_so,
                'i': net_profit_bi_si,
            }
        }
        # produce the queryset
        queryset = session.query(
            models.Item,
            self._upgrade_alias,
            profit_si,
            profit_so,
            net_profit_bo_so,
            net_profit_bo_si,
            net_profit_bi_so,
            net_profit_bi_si
        ). \
            join(self._glob_of_ecto_alias, self._glob_of_ecto_alias.data_id == 19721). \
            join(self._upgrade_alias, models.Item.upgrade_slot_id == self._upgrade_alias.data_id). \
            filter(models.Item.rarity == models.Item.EXOTIC). \
            filter(models.Item.sell_price > 0)
        # create column definitions
        column_descriptions = [
            tmodels.ColumnDescription('Item', True, models.Item.name, name='item'),
            tmodels.ColumnDescription('Upgrade', True, self._upgrade_alias.name, name='upgrade'),
            tmodels.ColumnDescription('Cost', True, [[models.Item.buy_price, models.Item.buy_price],
                                                     [models.Item.sell_price, models.Item.sell_price]],
                                      name='goldcost'),
            tmodels.ColumnDescription('Profit', True, [[profit_so, profit_si],
                                                       [profit_so, profit_si]], name='profit'),
            tmodels.ColumnDescription('Net Profit', True,
                                      [[net_profit_bo_so, net_profit_bo_si],
                                       [net_profit_bi_so, net_profit_bi_si]],
                                      name='netprofit')]
        # call super constructor
        tmodels.Table.__init__(self, column_descriptions, queryset)

    def create_row(self, query_row):
        # get the item referenced by this row
        i = query_row.Item
        # get the cost of buy the item
        cost = tmodels.Cost(
            [[i.buy_price, i.buy_price],
             [i.sell_price, i.sell_price]])
        # get the profit by selling upgrade and globs
        profit_so = self._get_qr(query_row, self._profit_s["o"])
        profit_si = self._get_qr(query_row, self._profit_s["i"])
        profit = tmodels.Cost([
            [profit_so, profit_si],
            [profit_so, profit_si],
        ])
        # get the net profit (profit - cost)
        net_profit = self._create_cost(query_row, self._net_profit_b_s)
        # produce and return the row
        row = tmodels.Row([
            tmodels.Cell([tmodels.Item(i)]),
            tmodels.Cell([tmodels.Item(self._get_qr(query_row, self._upgrade_alias))]),
            tmodels.Cell([cost]),
            tmodels.Cell([profit]),
            tmodels.Cell([net_profit])
        ])
        return row