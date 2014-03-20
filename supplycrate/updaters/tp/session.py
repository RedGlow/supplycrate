from supplycrate import private

__author__ = 'Mattia'
import urllib
import urllib2
import logging
import json
import time

from supplycrate.updaters.tp.exceptions import LoginException, DownloadException
from supplycrate.mwt import MWT


logger = logging.getLogger('gw2consolidate.' + __name__)


class Session(object):
    """
    A session to access the GW2 TP.
    """
    def __init__(self):
        self.__cookie_processor = urllib2.HTTPCookieProcessor()
        self.__opener = urllib2.build_opener(self.__cookie_processor)
        self.__opened = False

    def open(self):
        if self.__opened:
            return

        logger.debug("Opening new TP session...")
        self.__opener.addheaders = [('Referer', 'https://account.guildwars2.com/login')]
        try:
            stream = self.__opener.open(
                'https://account.guildwars2.com/login?redirect_uri=http%3A%2F%2Ftradingpost-live.ncplatform.net%2Fauthenticate%3Fsource%3D%252F&game_code=gw2',
                urllib.urlencode({
                    'email': private.GW2_EMAIL,
                    'password': private.GW2_PASSWORD
                }))
        except urllib2.HTTPError, stream:
            le = LoginException(stream)
            print 'login exception:', str(le)
            raise le

        self.__opened = True
        logger.debug("New TP session opened.")

    def close(self):
        if not self.__opened:
            return

        logger.debug("Closing TP session...")
        stream = self.__opener.open('https://account.guildwars2.com/logout')
        stream.read()
        logger.debug("TP session closed.")

    def __get_gems_data_internal(self, type_, quantity):
        session_key = list(self.__cookie_processor.cookiejar)[0].value
        url = 'https://exchange-live.ncplatform.net/api/v0/exchange/rate.json?o.type=%s&o.quantity=%d&m.sessionId=%s' % (
            type_, quantity, session_key)
        self.__opener.addheaders.append(('X-Requested-With', 'XMLHttpRequest'))
        stream = self.__opener.open(url)
        rv = int(json.load(stream)['body']['coins_per_gem'])
        self.__opener.addheaders.pop()
        return rv

    @MWT(timeout=5*60)
    def get_gems_data(self):
        gems = 100000
        coins = 100000000
        return {
            '100_gem_to_gold': self.__get_gems_data_internal('gems', gems),
            '100_gold_to_gem': self.__get_gems_data_internal('coins', coins),
        }

    def read_block(self, offset, block_size):
        url = 'https://tradingpost-live.ncplatform.net/ws/search.json?text=&levelmin=0&levelmax=80&offset=%d&count=%d' % (offset, block_size)
        stream = self.__opener.open(url)
        data = json.load(stream)
        return data

    def read_everything(self):
        try:
            logger.info('Downloading market data...')
            block_size = 1000
            offset = 0
            while True:
                data = self.read_block(offset, block_size)
                if len(data['results']) == 0:
                    break
                for entry in data['results']:
                    yield entry
                logger.info('%d%%' % (data['args']['offset'] * 100 / int(data['total'])))
                offset += block_size
                time.sleep(2)
            logger.info('Market data downloaded.')
        except urllib2.HTTPError, e:
            de = DownloadException(e)
            logger.debug('Download exception:\n%s', str(de))
            raise de