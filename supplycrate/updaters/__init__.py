from supplycrate.models import MarketHistoryElement
from supplycrate.updaters.api import update_from_api
from supplycrate.updaters.gooddeed import update_gooddeed, update_karmaweaponsdata
from supplycrate.updaters.grandmaster import update_from_recipe_api
from supplycrate.updaters.gw2db import update_gw2db
from supplycrate.updaters.markethistory import update_market_history
from supplycrate.updaters.prices import update_from_tp
from supplycrate.updaters.skill_point_recipes import load_skill_point_recipes
from supplycrate.updaters.vendordata import update_vendor

__author__ = 'Mattia'


def _schedule(app, func, do_cycle_0, args, **kwargs):
    if do_cycle_0:
        func(*args)
    app.registry.scheduler.add_interval_job(func, args=args, **kwargs)


def _enabled(settings, name):
    return settings.get('supplycrate.updater.' + name, '1') == '1'


def register(app, settings):
    #update_karmaweaponsdata()
    #_schedule(app, update_gooddeed, True, (), seconds=60)
    if _enabled(settings, 'gw2db'):
        _schedule(app, update_gw2db, settings['supplycrate.run_gw2db_import_at_startup'] == 'True',
                   (settings,), days=1)
    if _enabled(settings, 'skill_point_recipes'):
        load_skill_point_recipes()
    if _enabled(settings, 'api'):
        _schedule(app, update_from_api, False, (), seconds=4)
    if _enabled(settings, 'tp'):
        _schedule(app, update_from_tp, False, (), seconds=10)
    if _enabled(settings, 'tp_history'):
        _schedule(app, update_market_history, True, (), seconds=MarketHistoryElement.TICK_SECONDS_LENGTH)
    if _enabled(settings, 'vendor'):
        _schedule(app, update_vendor, True, (settings,), days=1)
    if _enabled(settings, 'recipe'):
        _schedule(app, update_from_recipe_api, False, (), seconds=4)
