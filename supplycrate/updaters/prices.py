import datetime
from supplycrate import utils
from supplycrate.models import Item
from supplycrate.updaters import tp

__author__ = 'Mattia'
logger = utils.get_logger()
_block_size = 1000
_offset = 0


def update_from_tp():
    # start a new TP session
    logger.debug("Opening a TP session.")
    tp_session = tp.Session()
    tp_session.open()
    # initialize local variables
    logger.debug("Run TP update cycle.")
    # read the block at current offset
    now = datetime.datetime.now()
    global _block_size, _offset
    logger.debug("Reading block %d-%d from TP...", _offset, _offset + _block_size)
    data = tp_session.read_block(_offset, _block_size)
    if len(data['results']) == 0:
        # we went too far: start again at _offset 0
        logger.debug("Out of items, restart.")
        _offset = 0
        return
    logger.debug("Updating DB with TP data...")
    tp.update_or_insert_bulk(data['results'], now)
    logger.debug("Block %d-%d imported with success from TP.", _offset, _offset + _block_size)
    _offset += _block_size