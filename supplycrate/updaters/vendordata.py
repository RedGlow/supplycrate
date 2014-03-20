from decimal import Decimal
import transaction
from supplycrate import utils
from supplycrate.models import VendorData, DBSession, Item
from supplycrate.updaters.gw2db import get_raw_data_from_settings

__author__ = 'Mattia'
logger = utils.get_logger()

_name_to_sp_cost = {
    "Philosopher's stone": Decimal(1) / Decimal(10),
    "Crystal": Decimal(3) / Decimal(5),
    "Eldritch Scroll": Decimal(50),
    "Siege Masters Guide": Decimal(1),
    "Bloodstone Shard": Decimal(200)
}

_karma_materials_start_data = [
    {'cost': Decimal('3.08'), 'name': 'Almond'},
    {'cost': Decimal('1.4'), 'name': 'Apple'},
    {'cost': Decimal('3.08'), 'name': 'Avocado'},
    {'cost': Decimal('1.96'), 'name': 'Banana'},
    {'cost': Decimal('1.96'), 'name': 'Basil Leaf'},
    {'cost': Decimal('1.96'), 'name': 'Bell Pepper'},
    {'cost': Decimal('1.96'), 'name': 'Black Bean'},
    {'cost': Decimal('1.4'), 'name': 'Glass of Buttermilk'},
    {'cost': Decimal('1.4'), 'name': 'Celery Stalk'},
    {'cost': Decimal('1.4'), 'name': 'Cheese Wedge'},
    {'cost': Decimal('3.08'), 'name': 'Cherry'},
    {'cost': Decimal('4.48'), 'name': 'Chickpea'},
    {'cost': Decimal('4.48'), 'name': 'Coconut'},
    {'cost': Decimal('1.4'), 'name': 'Cumin'},
    {'cost': Decimal('6.16'), 'name': 'Eggplant'},
    {'cost': Decimal('3.08'), 'name': 'Ginger Root'},
    {'cost': Decimal('1.4'), 'name': 'Green Bean'},
    {'cost': Decimal('4.48'), 'name': 'Horseradish Root'},
    {'cost': Decimal('1.96'), 'name': 'Kidney Bean'},
    {'cost': Decimal('1.4'), 'name': 'Lemon'},
    {'cost': Decimal('3.08'), 'name': 'Lime'},
    {'cost': Decimal('1.4'), 'name': 'Loaf of Bread'},
    {'cost': Decimal('8.12'), 'name': 'Mango'},
    {'cost': Decimal('1.4'), 'name': 'Nutmeg Seed'},
    {'cost': Decimal('6.16'), 'name': 'Peach'},
    {'cost': Decimal('4.48'), 'name': 'Pear'},
    {'cost': Decimal('4.48'), 'name': 'Pinenut'},
    {'cost': Decimal('1.96'), 'name': 'Rice Ball'},
    {'cost': Decimal('4.48'), 'name': 'Shallot'},
    {'cost': Decimal('3.08'), 'name': 'Bowl of Sour Cream'},
    {'cost': Decimal('1.4'), 'name': 'Tomato'},
    {'cost': Decimal('1.4'), 'name': 'Packet of Yeast'},
    {'cost': Decimal('21'), 'name': 'Sun Bead'}
]


def _get_entry(data_id, existing_data_map, session, already_added):
    if data_id == 5509:
        print "ciao"
    if data_id in existing_data_map:
        vd = existing_data_map[data_id]
        already_added.add(data_id)
    else:
        vd = VendorData()
        vd.item_id = data_id
        existing_data_map[data_id] = vd
        session.add(vd)
    return vd


def update_vendor(settings):
    logger.debug("Importing vendor data...")
    gw2db_data = get_raw_data_from_settings(settings)

    session = DBSession()
    with transaction.manager:
        # get out all existing VendorData
        existing_data_map = dict(session.query(VendorData.item_id, VendorData))
        already_added = set()
        # update or add the karma/gold cost data
        for entry in gw2db_data:
            if len(entry['SoldBy']) > 0:
                data_id = entry['DataID']
                karma_cost = None
                copper_cost = None
                for sb in entry['SoldBy']:
                    if 'KarmaCost' in sb:
                        karma_cost = sb['KarmaCost']
                    if 'GoldCost' in sb:
                        copper_cost = sb['GoldCost']
                if karma_cost is not None or copper_cost is not None:
                    vd = _get_entry(data_id, existing_data_map, session, already_added)
                    vd.karma_cost = karma_cost
                    vd.copper_cost = copper_cost
        # update skill point costs
        for name, cost in _name_to_sp_cost.items():
            data_id = session.query(Item.data_id).filter_by(name=name).first()[0]
            vd = _get_entry(data_id, existing_data_map, session, already_added)
            vd.skill_point_cost = cost
        # update special karma costs (bundles, sun beads)
        for entry in _karma_materials_start_data:
            data_id = session.query(Item.data_id).filter_by(name=name).first()[0]
            vd = _get_entry(data_id, existing_data_map, session, already_added)
            vd.karma_cost = entry['cost']
        # delete unneeded elements
        for data_id, el in existing_data_map.items():
            if data_id not in already_added:
                session.delete(el)

    logger.debug("Importing vendor data done.")