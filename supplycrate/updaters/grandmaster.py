import json
import urllib2
import itertools
from sqlalchemy import func
import transaction
from supplycrate import utils
from supplycrate.models import Recipe, Item, RecipeItemType, DBSession
from supplycrate.updaters.api import import_entry

__author__ = 'Mattia'
_recipe_ids = []
logger = utils.get_logger()


def _fill_recipe_ids(session):
    global _recipe_ids
    if len(_recipe_ids) == 0:
        logger.info("Computing recipe ids...")
        # get a set of all recipe ids from gw2 api
        recipe_ids = set(json.load(urllib2.urlopen('https://api.guildwars2.com/v1/recipes.json'))['recipes'])
        # get a set of all recipe ids we already know about
        known_recipe_ids = set(recipe_id for recipe_id, in session.query(Recipe.recipe_id))
        # get the recipes we don't know
        unknown_recipe_ids = recipe_ids.difference(known_recipe_ids)
        # build a list with known recipes first, and unknown recipes afterwards (list is read from
        # end to start)
        _recipe_ids = list(itertools.chain(unknown_recipe_ids, known_recipe_ids))
        logger.info("Obtained %d unknown recipes, %d known recipes and %d total recipes.",
                    len(unknown_recipe_ids), len(known_recipe_ids), len(_recipe_ids))


def _body(session):
    # fill the recipe ids id necessary
    _fill_recipe_ids(session)
    global _recipe_ids
    assert len(_recipe_ids) > 0
    # download the first one
    recipe_id = _recipe_ids.pop()
    logger.debug("Downloading recipe id %d, still %d to go.", recipe_id, len(_recipe_ids))
    recipe = json.load(urllib2.urlopen('https://api.guildwars2.com/v1/recipe_details.json?recipe_id=%d' % recipe_id))
    assert len(recipe['ingredients']) <= 4, 'More than 4 ingredients for recipe %d!' % recipe_id
    # get the items we don't already have
    needed_items_ids = [int(recipe['output_item_id'])] + [int(ing['item_id']) for ing in recipe['ingredients']]
    existing_item_ids = session.query(Item.data_id).filter(Item.data_id.in_(needed_items_ids))
    for existing_item_id, in existing_item_ids:
        needed_items_ids.remove(existing_item_id)
    for needed_item_id in needed_items_ids:
        logger.info("Need item with id=%d, downloading it.", needed_item_id)
        item = import_entry(None, needed_item_id, session)
        if item is None:
            logger.info("Item with id %d not obtainable through the API.", needed_item_id)
            return
        session.add(item)
        logger.info("Obtained %s.", item.name)
    # produce recipe types and flags
    recipe_item_type = session.query(RecipeItemType).filter_by(name=recipe['type']).first()
    if recipe_item_type is None:
        logger.info("Creating new item type: %s.", recipe['type'])
        recipe_item_type = RecipeItemType(name=recipe['type'])
        session.add(recipe_item_type)
        session.flush()
    # save it
    r = Recipe(
        recipe_id=int(recipe['recipe_id']),
        type_id=recipe_item_type.id,
        output_item_id=int(recipe['output_item_id']),
        output_item_count=int(recipe['output_item_count']),
        min_rating=int(recipe['min_rating']),
        time_to_craft_ms=int(recipe['time_to_craft_ms']),
        can_armorsmith='Armorsmith' in recipe['disciplines'],
        can_artificer='Artificer' in recipe['disciplines'],
        can_chef='Chef' in recipe['disciplines'],
        can_huntsman='Huntsman' in recipe['disciplines'],
        can_jeweler='Jeweler' in recipe['disciplines'],
        can_leatherworker='Leatherworker' in recipe['disciplines'],
        can_tailor='Tailor' in recipe['disciplines'],
        can_weaponsmith='Weaponsmith' in recipe['disciplines'],
        vendor_value=int(recipe.get('vendor_value', '0')),
        autolearned=0,
        learned_from_item=0
    )
    # flags
    for flag in recipe['flags']:
        if flag == 'LearnedFromItem':
            r.learned_from_item = 1
        elif flag == 'AutoLearned':
            r.autolearned = 1
        else:
            raise ValueError('Unknown flag "%s"' % flag)
    # extra ingredients
    for i in range(4):
        if i >= len(recipe['ingredients']):
            item_id = None
            count = None
        else:
            ing = recipe['ingredients'][i]
            item_id = int(ing['item_id'])
            count = int(ing['count'])
        setattr(r, 'ingredient_%d_item_id' % (i + 1), item_id)
        setattr(r, 'ingredient_%d_count' % (i + 1), count)
    # save
    session.merge(r)


def update_from_recipe_api():
    session = DBSession()
    with transaction.manager:
        _body(session)