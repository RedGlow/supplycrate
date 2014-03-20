import transaction
from supplycrate.models import Item, DBSession
from supplycrate.updaters.tp.session import Session

__author__ = 'Mattia'


def update_or_insert_bulk(entries, now):
    """
    Updates or insert all given entries in the DB. entries are a list of dictionaries
    containing the keys data_id, buy_count, buy_price, sell_count, sell_price. Items
    not (yet?) existing in the DB are simply skipped.
    """
    session = DBSession()
    with transaction.manager:
        entries_data_id_list = [int(entry['data_id']) for entry in entries]
        existing_items = dict(session.\
                              query(Item.data_id, Item).\
                              filter(Item.data_id.in_(entries_data_id_list)))
        for entry in entries:
            data_id = int(entry['data_id'])
            if data_id not in existing_items:
                continue
            item = existing_items[data_id]
            item.buy_count = entry['buy_count']
            item.buy_price = entry['buy_price']
            item.sell_count = entry['sell_count']
            item.sell_price = entry['sell_price']
            item.last_tp_update = now