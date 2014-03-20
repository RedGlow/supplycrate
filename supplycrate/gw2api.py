import datetime
from supplycrate.mwt import MWT

__author__ = 'Mattia'

import urllib2
import json


class GW2APIException(Exception):
    def __init__(self, res, data_id):
        Exception.__init__(self, 'GW2API Exception: %' + res['text'])
        self.text = res['text']
        self.data_id = data_id
        self.error = res['error']
        self.product = res['product']
        self.module = res['module']
        self.line = res['line']

    def __str__(self):
        return 'GW2API Exception while asking for data_id=%d: %s' % (self.data_id, self.text)


def get_item_details(data_id):
    try:
        f = urllib2.urlopen('https://api.guildwars2.com/v1/item_details.json?item_id=%d' % data_id)
    except urllib2.HTTPError, e:
        raise GW2APIException(json.load(e), data_id)
    data = json.load(f)
    return data


@MWT(timeout=60*60*24)
def get_items_data_ids():
    try:
        f = urllib2.urlopen('https://api.guildwars2.com/v1/items.json')
    except urllib2.HTTPError, e:
        raise GW2APIException(json.load(e), None)
    data = json.load(f)
    return data['items']