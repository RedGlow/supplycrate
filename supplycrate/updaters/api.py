from sqlalchemy.sql import func
import transaction
from supplycrate import utils
from supplycrate.models import Item, DBSession
from supplycrate import gw2api
from supplycrate.mwt import MWT

__author__ = 'Mattia'

logger = utils.get_logger()
_id_list = []

_rev_type_id = {
    'Trophy': Item.TROPHY,
    'Weapon': Item.WEAPON,
    'Armor': Item.ARMOR,
    'Consumable': Item.CONSUMABLE,
    'Gizmo': Item.GIZMO,
    'Trinket': Item.TRINKET,
    'CraftingMaterial': Item.CRAFTING_MATERIAL,
    'Container': Item.CONTAINER,
    'UpgradeComponent': Item.UPGRADE_COMPONENT,
    'MiniPet': Item.MINIPET,
    'Bag': Item.BAG,
    'Back': Item.BACK,
    'TraitGuide': Item.TRAIT_GUIDE,
    'Gathering': Item.GATHERING,
    'Tool': Item.TOOL,
    'MiniDeck': Item.MINIDECK,
}

_rev_trinket_type = {
    'Ring': Item.RING,
    'Accessory': Item.ACCESSORY,
    'Amulet': Item.AMULET
}

_rev_weapon_type = {
    'Hammer': 1,
    'Sword': 2,
    'Dagger': 3,
    'Harpoon': 4,
    'Staff': 5,
    'Scepter': 6,
    'Greatsword': 7,
    'LongBow': 8,
    'Shield': 9,
    'Pistol': 10,
    'Axe': 11,
    'Speargun': 12,
    'BundleLarge': 13,
    'Rifle': 14,
    'Warhorn': 15,
    'Mace': 16,
    'Focus': 17,
    'Polearm': 18,
    'ShortBow': 19,
    'Torch': 20,
    'Trident': 21,
    'BundleSmall': 22,
    'Toy': 23,
    'NoWeapon': 24,
    'SpecialFireGreatsword': 25,
    'SpecialMagneticShield': 26,
    'SpecialBowOfFrost': 27,
    'SpecialLavaAxe': 28,
    'SpecialLightningHammer': 29,
    'SpecialElixirGun': 30,
    'SpecialFlameThrower': 31,
    'SpecialToolkit': 32,
    'SpecialBombkit': 33,
    'SpecialGrenadekit': 34,
    'SpecialMedkit': 35,
    'SpecialMinekit': 36,
    'TwoHandedToy': 23,
}

_rev_gathering_type = {
    'Logging': 1,
    'Foraging': 2,
    'Mining': 3,
}

_rev_armor_type = {
    'Gloves': 1,
    'Boots': 2,
    'Coat': 3,
    'Helm': 4,
    'Leggings': 5,
    'Shoulders': 6,
    'HelmAquatic': 7,
}

_rev_armor_weight = {
    'Light': 1,
    'Heavy': 2,
    'Medium': 3,
    'Clothing': 4,
}

_rev_rarity = {
    'Junk': 1,
    'Basic': 2,
    'Fine': 3,
    'Masterwork': 4,
    'Rare': 5,
    'Exotic': 6,
    'Legendary': 7,
    'Ascended': 8,
}

_rev_attr_name = {
    'Power': 'stat_power',
    'Precision': 'stat_precision',
    'Toughness': 'stat_toughness',
    'Vitality': 'stat_vitality',
    'Healing': 'stat_healing',
    'ConditionDamage': 'stat_condition_damage',
    'CritDamage': 'stat_critical_damage'
}


def import_entry(name, data_id, session):
    # get out the item, or create it, and add it to the session
    item = session.query(Item).filter_by(data_id=data_id).first()
    if item is None:
        item = Item(data_id=data_id)
    session.add(item)
    # try to get the data from the API, marking it as failed in case
    try:
        data = gw2api.get_item_details(data_id)
    except gw2api.GW2APIException, e:
        logger.info("Skipping item %s (data_id=%s), could not fill data through GW2API:\n%s",
                    name or '(name unknown)', data_id, e)
        item.api_failed = True
        return None
    # get/save upgrade
    specific_data = data[data['type'].lower()] if data['type'].lower() in data else {}
    upgrade_slot_id = int(specific_data['suffix_item_id']) if specific_data.get('suffix_item_id') else None
    upgrade_slot = None
    if upgrade_slot_id is not None:
        logger.debug('Item has an upgrade with data_id=%d.', upgrade_slot_id)
        if session.query(Item.data_id).filter_by(gw2db_id=upgrade_slot_id).first() is not None:
            logger.debug('Upgrade already in DB, no need to add it.')
        else:
            logger.debug('Upgrade not in DB, adding it.')
            upgrade_slot = import_entry(None, upgrade_slot_id, session)
    # transform data from API/database
    min_gw2db_id = session.query(func.min(Item.gw2db_id)).scalar() - 1
    min_external_id = session.query(func.min(Item.external_id)).scalar() - 1
    attributes = (dict((_rev_attr_name[attr['attribute']], int(attr['modifier']))
                       for attr
                       in specific_data['infix_upgrade']['attributes'])
                  if ('infix_upgrade' in specific_data and
                      'attributes' in specific_data['infix_upgrade'])
                  else {})
    # update item
    item.name = data['name']
    item.gw2db_id = item.gw2db_id or min_gw2db_id
    item.data_id = data_id
    item.external_id = item.external_id or min_external_id
    item.type = _rev_type_id[data['type']]
    item.description = data['description']
    item.level = data['level']
    item.required_level = data['level']
    item.rarity = _rev_rarity[data['rarity']]
    item.defense = int(data.get('defense', 0))
    item.icon_num1 = 0
    item.icon_num2 = 0
    item.icon_num3 = 0
    item.value = int(data['vendor_value'])
    item.icon_file_id = int(data['icon_file_id'])
    item.icon_file_signature = data['icon_file_signature']
    item.trinket_type = _rev_trinket_type[data['trinket']['type']] if data['type'] == 'Trinket' else None
    item.weapon_type = _rev_weapon_type[data['weapon']['type']] if data['type'] == 'Weapon' else None
    item.min_power = int(data['weapon']['min_power']) if data['type'] == 'Weapon' else None
    item.max_power = int(data['weapon']['max_power']) if data['type'] == 'Weapon' else None
    item.bag_size = int(data['bag']['size']) if data['type'] == 'Bag' else None
    item.gathering_type = _rev_gathering_type[data['gathering']['type']] if data['type'] == 'Gathering' else None
    item.armor_type = _rev_armor_type[data['armor']['type']] if data['type'] == 'Armor' else None
    item.armor_weight = _rev_armor_weight[data['armor']['weight_class']] if data['type'] == 'Armor' else None
    item.api_updated = True
    item.upgrade_slot = upgrade_slot.data_id if upgrade_slot else None
    for key, value in attributes.items():
        setattr(item, key, value)
    # return result
    return item


@MWT(timeout=60 * 60, ignore_args=True)
def missing_ids(session):
    existing_data_ids = session.query(Item.data_id).order_by(Item.data_id).all()
    all_data_ids = gw2api.get_items_data_ids()
    missing = []

    existing_iterator = iter(existing_data_ids)
    all_iterator = iter(sorted(all_data_ids))
    try:
        current = existing_iterator.next()
        for id_ in all_iterator:
            assert id_ <= current, 'lists desynchronized! id_=%d, current=%d' % (id_, current)
            if id_ != current:
                missing.append(id_)
            else:
                current = existing_iterator.next()
    except StopIteration:
        for id_ in all_iterator:
            missing.append(id_)
    return missing


def _get_next_id(session):
    # create the list if necessary
    global _id_list
    if len(_id_list) == 0:
        logger.debug('No list of data ids: creating it.')
        _id_list = map(lambda x: x[0],
                       session.query(Item.data_id).\
                       filter_by(api_updated=False).\
                       order_by(Item.api_failed.desc()).\
                       all())  # TODO: add random criteria to order_by
        if len(_id_list) == 0:
            logger.debug('No more elements with api_updated=False; proceed downloading all elements.')
            _id_list = missing_ids(session)
            pass
    # return the next element to download
    logger.debug('Still %d elements to download.', len(_id_list))
    if len(_id_list) == 0:
        return None
    else:
        return _id_list.pop()


def update_from_api():
    # find next element to update
    session = DBSession()
    with transaction.manager:
        logger.debug('Looking for a new element to update/create from the API...')
        data_id = _get_next_id(session)
        logger.debug('Got data_id=%d.', data_id)
        if data_id is None:
            return
        item = import_entry(None, data_id, session)
        if item is not None:
            logger.info('Updated (data_id=%d) from API.', item.data_id)