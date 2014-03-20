from sqlalchemy import func, insert, and_, exists
from sqlalchemy.orm import aliased
from sqlalchemy.sql import or_
from sqlalchemy.sql.functions import coalesce
import transaction
from supplycrate import models, DBSession
from supplycrate.models import RTLPMemoryTable, Profit, KarmaWeaponsData, RG_Raw
import supplycrate.tablerenderer.model as tmodels
from supplycrate.updaters.karmaweaponsdata import data
from supplycrate import utils
from supplycrate.utils import dump_query


__author__ = 'Mattia'
logger = utils.get_logger()


def _update_masterwork(session):
    # empty the rtlp table
    session.query(RTLPMemoryTable).delete()
    # fill the rtlp table with average prices per masterwork and rares
    select_query = session. \
        query(models.Item.rarity.label("rarity"),
              models.Item.weapon_type.label("weapon_type"),
              models.Item.level.label("level"),
              tmodels.Table._round(func.avg(models.Item.buy_price) * 0.85).label("price_i"),
              tmodels.Table._round(func.avg(models.Item.sell_price) * 0.85).label("price_o"),
              func.min(models.Item.last_tp_update).label("last_update")). \
        filter(models.Item.type == models.Item.WEAPON). \
        filter(or_(models.Item.rarity == models.Item.MASTERWORK, models.Item.rarity == models.Item.RARE)). \
        group_by(models.Item.rarity, models.Item.weapon_type, models.Item.level)
    insert_query = insert(RTLPMemoryTable).from_select(
        ["rarity", "weapon_type", "level", "price_i", "price_o", "last_update"],
        select_query
    )
    insert_query.execute()
    # clear the profit table
    session.query(Profit).delete()
    # fill the profit table with the average selling prices
    rtlp_m = aliased(models.RTLPMemoryTable, name="rtlp_m")
    rtlp_r = aliased(models.RTLPMemoryTable, name="rtlp_r")
    lvl = rtlp_m.level.label("level")
    select_query = session. \
        query(lvl,
              rtlp_m.weapon_type.label("weapon_type"),
              tmodels.Table._if(rtlp_r.price_o == None,
                                rtlp_m.price_o,
                                rtlp_m.price_o * 0.8 + rtlp_r.price_o * 0.2).label("avg_price_o"),
              tmodels.Table._if(rtlp_r.price_i == None,
                                rtlp_m.price_i,
                                rtlp_m.price_i * 0.8 + rtlp_r.price_i * 0.2).label("avg_price_i"),
              tmodels.Table._least(rtlp_r.last_update, rtlp_m.last_update).label("last_update")). \
        join(rtlp_r, and_(rtlp_m.weapon_type == rtlp_r.weapon_type, rtlp_m.level == rtlp_r.level)). \
        filter(rtlp_m.rarity == models.Item.MASTERWORK,
               rtlp_r.rarity == models.Item.RARE)
    insert_query = insert(Profit).from_select(
        ["level", "weapon_type", "avg_price_o", "avg_price_i", "last_update"],
        select_query
    )
    insert_query.execute()
    # create the rg_raw table
    session.query(RG_Raw).delete()
    # compute the average selling prices considering a uniform level-up probability between +5 and +12
    r = range(5, 13)
    p = {i: aliased(Profit, name="p_%d" % i) for i in r}
    avg_profit_so, avg_profit_si = tmodels.Table._buy_o(
        lambda l, s: (
            sum(coalesce(getattr(p[i], 'avg_price_'+s), 0) for i in r) /
            (8 - sum(tmodels.Table._if(getattr(p[i], "avg_price_" + s) == None, 1, 0) for i in r))
        ).label("avg_profit_s" + s)
    )
    last_update = tmodels.Table._least(*(
        coalesce(p[i].last_update, func.now())
        for i
        in r
    )).label("last_update")
    join_query = reduce(
        lambda prev, i: prev.outerjoin(p[i],
                                        and_(KarmaWeaponsData.weapon_type == p[i].weapon_type,
                                             KarmaWeaponsData.level + i == p[i].level)),
        r,
        session.query(KarmaWeaponsData.weapon_type,
                      KarmaWeaponsData.level,
                      KarmaWeaponsData.karma_cost,
                      avg_profit_so,
                      avg_profit_si,
                      last_update))
    condition1, condition2 = tmodels.Table._buy_o(
        lambda l, s: or_(*(getattr(p[i], "avg_price_" + s) != None for i in r))
    )
    filtered_query = join_query.filter(condition1).filter(condition2)
    insert_query = insert(RG_Raw).from_select(
        ['weapon_type', 'level', 'karma_cost', 'avg_profit_so', 'avg_profit_si', 'last_update'],
        filtered_query
    )
    insert_query.execute()


def update_karmaweaponsdata():
    session = DBSession()
    with transaction.manager:
        for entry in data:
            e = session. \
                query(exists().
                      where(KarmaWeaponsData.level == entry['level'] and
                            KarmaWeaponsData.weapon_type == entry['weapon_type'])). \
                scalar()
            if not e:
                kwd = KarmaWeaponsData(level=entry['level'],
                                       weapon_type=entry['weapon_type'],
                                       karma_cost=entry['karma_cost'])
                session.add(kwd)


def update_gooddeed():
    session = DBSession()
    with transaction.manager:
        _update_masterwork(session)