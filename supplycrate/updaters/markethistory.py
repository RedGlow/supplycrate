import datetime
from dateutil.tz import tzlocal
from sqlalchemy import func, insert, literal_column
import transaction
from supplycrate import utils
from supplycrate.models import DBSession, MarketHistoryElement, Item

__author__ = 'Mattia'
logger = utils.get_logger()


def update_market_history():
    session = DBSession()
    with transaction.manager:
        last_tick = session.query(func.max(MarketHistoryElement.ticks)).scalar()
        current_date = datetime.datetime.now(tzlocal())
        current_tick = int((current_date - MarketHistoryElement.START_ERA).total_seconds() / MarketHistoryElement.TICK_SECONDS_LENGTH)
        assert last_tick <= current_tick
        if last_tick == current_tick:
            logger.debug("Skipping update to market history: tick %d already saved.", current_tick)
            return
        origin_select = session.\
            query(Item.data_id,
                  literal_column(str(current_tick)),
                  Item.buy_count,
                  Item.buy_price,
                  Item.sell_count,
                  Item.sell_price).\
            filter(Item.buy_count > 0, Item.sell_count > 0)
        i = insert(MarketHistoryElement).from_select([
            MarketHistoryElement.item_id,
            MarketHistoryElement.ticks,
            MarketHistoryElement.buy_count,
            MarketHistoryElement.buy_price,
            MarketHistoryElement.sell_count,
            MarketHistoryElement.sell_price
        ], origin_select)
        logger.debug("Executing market history insert...")
        i.execute()
        logger.debug("Saved market data for tick %d.", current_tick)