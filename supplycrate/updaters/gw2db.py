import json
import re
from os import path
import urllib2
import datetime
import itertools
import transaction
from supplycrate import utils
from supplycrate.models import Item, DBSession

__author__ = 'Mattia'
logger = utils.get_logger()

def _normalize_name(i):
    return re.sub(r'\[.*\]', '', i)


_icon_url_prefix = 'http://media-ascalon.cursecdn.com/avatars/thumbnails/'
_icon_url_suffix = '.png'


def _split_icon_url(url):
    # http://media-ascalon.cursecdn.com/avatars/thumbnails/112/698/32/32/63127.png
    original_url = url
    assert url.startswith(_icon_url_prefix), 'Icon URL does not start with expected prefix'
    assert url.endswith(_icon_url_suffix), 'Icon URL does not end with expected suffix'
    url = url[len(_icon_url_prefix): -len(_icon_url_suffix)]
    pieces = url.split('/')
    pieces = ['0' if piece == '' else piece for piece in pieces]  # permanent cute-quaggan finisher has wrong data
    return int(pieces[0]), int(pieces[1]), int(pieces[4])


def _re_encode(name):
    """Tries to re-encode the name, because sometimes the names in the gw2db results are twice utf8 encoded
    by error"""
    assert isinstance(name, unicode)
    all_ord = [ord(ch) for ch in name]
    if any(o > 255 for o in all_ord):
        return name  # at least one non-ascii-plane unicode character: cannot be double-encoded
    rebuilt = ''.join(chr(ord(ch)) for ch in name)
    try:
        # will return the re-encoded name if successful
        return rebuilt.decode('utf8')
    except UnicodeDecodeError:
        # re-encoding failed: original name was already correctly encoded
        return name


_stat_codes = {
    1: 'power',
    2: 'healing',
    3: 'precision',
    4: 'toughness',
    5: 'critical_damage',
    6: 'condition_damage',
    7: 'vitality',
    14: 'boon_duration',
}


def get_raw_data(url):
    # open the streams
    source_items_stream = urllib2.urlopen(url)

    # read the serialized data in the JSON streams
    try:
        source_items = json.load(source_items_stream)
    finally:
        source_items_stream.close()

    # sort by data_id
    source_items.sort(key=lambda i: i['DataID'])

    # return result
    return source_items


def _create_item(source_item, now, existing_items):
    # fetch existing item, or create a new one if it doesn't exist
    data_id = source_item['DataID']
    item = existing_items.get(source_item['DataID'], Item())
    # fill the item
    item.name = _normalize_name(_re_encode(source_item['Name']))
    item.gw2db_id = source_item['ID']
    item.data_id = source_item['DataID']
    item.external_id = source_item['ExternalID']
    item.type = source_item['Type']
    item.description = source_item.get('Description', '')
    item.level = source_item['Level']
    item.required_level = source_item['RequiredLevel']
    item.rarity = source_item['Rarity']
    item.defense = source_item['Defense']
    item.value = source_item['Value']
    item.last_gw2db_update = now
    item.icon_num1, item.icon_num2, item.icon_num3 = \
        _split_icon_url(source_item['Icon'])

    # type-dependent attributes
    if item.type == Item.TRINKET:
        item.trinket_type = source_item['TrinketType']
    elif item.type == Item.WEAPON:
        item.weapon_type = source_item['WeaponType']
        item.min_power = source_item['MinPower']
        item.max_power = source_item['MaxPower']
    elif item.type == Item.ARMOR:
        item.armor_type = source_item['ArmorType']
        item.armor_weight = source_item['ArmorWeightType']
    elif item.type == Item.BAG:
        item.bag_size = source_item['BagSize']
    elif item.type == Item.CONSUMABLE:
        item.consumable_type = source_item['ConsumableType']
    elif item.type == Item.GATHERING:
        item.gathering_type = source_item['GatheringType']

    # stats
    for stat in _stat_codes.values():
        setattr(item, 'stat_' + stat, None)
    for source_stat in source_item['Stats']:
        setattr(item, 'stat_' + _stat_codes[source_stat['Type']], source_stat['Value'])

    return item


def get_raw_data_from_settings(settings):
    url = settings['supplycrate.gw2db_url'].replace('C:\\', '/').replace('\\', '/')
    logger.info("Using %s", url)
    source_items = get_raw_data(url)
    return source_items


def update_gw2db(settings):
    logger.info('Starting GW2DB import.')

    source_items = get_raw_data_from_settings(settings)

    now = datetime.datetime.now()

    # import the items
    logger.info('Import items...')
    i = 0
    to_create = []

    amount_per_block = 5000
    grouped = itertools.groupby(enumerate(source_items), lambda (index, si): index / amount_per_block)
    for _, elements in grouped:
        session = DBSession()
        with transaction.manager:
            elements = list(elements)
            logger.info("Analyzing %d elements (%d%%)...", len(elements), elements[-1][0] * 100 / len(source_items))
            min_data_id = elements[0][1]['DataID']
            max_data_id = elements[-1][1]['DataID']
            existing_items = dict(session.query(Item.data_id, Item).\
                                  filter(Item.data_id >= min_data_id).\
                                  filter(Item.data_id <= max_data_id))
            for idx, source_item in elements:
                try:
                    # update / create object
                    item = _create_item(source_item, now, existing_items)
                    session.add(item)
                except:
                    logger.error('Error while importing element "%(Name)s" (id = %(ID)d)',
                                 source_item)
                    raise
            logger.info('Elements analyzed. Committing...')
        logger.info('Committed.')

    logger.info('GW2DB import completed.')