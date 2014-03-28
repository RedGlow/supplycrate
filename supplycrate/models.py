from contextlib import contextmanager
import datetime
from pytz import utc
from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    String,
    SmallInteger,
    DateTime,
    Boolean,
    ForeignKey,
    Numeric)

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship)
import transaction

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

_long_time_ago = datetime.datetime.now()
_long_time_ago = _long_time_ago - datetime.timedelta(365 * 10)


class Ingredient(object):
    def __init__(self, item, count):
        self.item = item
        self.count = count


class Item(Base):
    __tablename__ = 'items'

    # type
    TROPHY = 1
    WEAPON = 2
    ARMOR = 3
    CONSUMABLE = 4
    GIZMO = 5
    TRINKET = 6
    CRAFTING_MATERIAL = 7
    CONTAINER = 8
    UPGRADE_COMPONENT = 9
    MINIPET = 10
    BAG = 11
    BACK = 12
    TRAIT_GUIDE = 13
    GATHERING = 14
    TOOL = 15
    MINIDECK = 16

    # trinket type
    ACCESSORY = 1
    AMULET = 2
    RING = 3

    # weapon type
    HAMMER = 1
    SWORD = 2
    DAGGER = 3
    HARPOON = 4
    STAFF = 5
    SCEPTER = 6
    GREATSWORD = 7
    LONGBOW = 8
    SHIELD = 9
    PISTOL = 10
    AXE = 11
    SPEARGUN = 12
    BUNDLE_LARGE = 13
    RIFLE = 14
    WARHORN = 15
    MACE = 16
    FOCUS = 17
    POLEARM = 18
    SHORTBOW = 19
    TORCH = 20
    TRIDENT = 21
    BUNDLE_SMALL = 22
    TOY = 23
    NO_WEAPON = 24
    SPECIAL_FIRE_GREATSWORD = 25
    SPECIAL_MAGNETIC_SHIELD = 26
    SPECIAL_BOW_OF_FROST = 27
    SPECIAL_LAVA_AXE = 28
    SPECIAL_LIGHTNING_HAMMER = 29
    SPECIAL_ELIXIR_GUN = 30
    SPECIAL_FLAME_THROWER = 31
    SPECIAL_TOOLKIT = 32
    SPECIAL_BOMBKIT = 33
    SPECIAL_GRENADEKIT = 34
    SPECIAL_MEDKIT = 35
    SPECIAL_MINEKIT = 36

    # armor weight
    LIGHT = 1
    HEAVY = 2
    MEDIUM = 3
    CLOTHING = 4

    # consumable type
    GENERIC = 1
    FOOD = 2
    UNLOCK = 3
    TRANSMUTATION = 4
    CONTRACT_NPC = 5
    MEGAPHONE = 6
    UTILITY = 7
    IMMEDIATE = 8
    BOOZE = 9
    POTION_ENDURANCE = 10
    POTION_HEALTH = 11
    UNK = 12

    # rarity
    JUNK = 1
    COMMON = 2
    FINE = 3
    MASTERWORK = 4
    RARE = 5
    EXOTIC = 6
    LEGENDARY = 7
    ASCENDED = 8

    # gathering type
    LOGGING = 1
    FORAGING = 2
    MINING = 3

    # armor type
    GLOVES = 1
    BOOTS = 2
    COAT = 3
    HELM = 4
    LEGGINGS = 5
    SHOULDERS = 6
    HELM_AQUATIC = 7

    # common fields
    data_id = Column(Integer, primary_key=True, nullable=False)
    gw2db_id = Column(Integer, unique=True, index=True, nullable=True)
    external_id = Column(Integer, unique=True, index=True, nullable=True)
    name = Column(String(64), index=True, nullable=False)
    description = Column(Text)
    type = Column(SmallInteger, index=True, nullable=False)
    level = Column(SmallInteger, index=True, nullable=False)
    required_level = Column(SmallInteger, index=True, nullable=False)
    value = Column(Integer, index=True, nullable=False)
    rarity = Column(SmallInteger, index=True)
    buy_count = Column(Integer, index=True, default=0, nullable=False)
    buy_price = Column(Integer, index=True, default=0, nullable=False)
    sell_count = Column(Integer, index=True, default=0, nullable=False)
    sell_price = Column(Integer, index=True, default=0, nullable=False)
    last_gw2db_update = Column(DateTime, default=_long_time_ago)
    last_tp_update = Column(DateTime, default=_long_time_ago)
    api_updated = Column(Boolean, default=False, nullable=False, index=True)
    api_failed = Column(Boolean, default=False, nullable=False)
    # full url is given by
    # 'http://media-ascalon.cursecdn.com/avatars/thumbnails/<num1>/<num2>/<width>/<height>/<num3>.png
    # width and height can be 32x32, 48x48, [others have not been tried]
    icon_num1 = Column(Integer, nullable=False)
    icon_num2 = Column(Integer, nullable=False)
    icon_num3 = Column(Integer, nullable=False)
    # full url can be reconstructed by gw2 api render service
    icon_file_id = Column(Integer, default=0)
    icon_file_signature = Column(String(40))

    # type-specific fields
    trinket_type = Column(SmallInteger, index=True)
    weapon_type = Column(SmallInteger, index=True)
    consumable_type = Column(SmallInteger, index=True)
    gathering_type = Column(SmallInteger, index=True)
    armor_type = Column(SmallInteger, index=True)
    bag_size = Column(SmallInteger, index=True)
    min_power = Column(Integer, index=True)
    max_power = Column(Integer, index=True)
    armor_weight = Column(SmallInteger, index=True)
    defense = Column(Integer, index=True)
    stat_power = Column(SmallInteger, index=True, default=None)
    stat_healing = Column(SmallInteger, index=True, default=None)
    stat_precision = Column(SmallInteger, index=True, default=None)
    stat_toughness = Column(SmallInteger, index=True, default=None)
    stat_critical_damage = Column(SmallInteger, index=True, default=None)
    stat_condition_damage = Column(SmallInteger, index=True, default=None)
    stat_vitality = Column(SmallInteger, index=True, default=None)
    stat_boon_duration = Column(SmallInteger, index=True, default=None)
    upgrade_slot_id = Column(Integer, ForeignKey("items.data_id"))

    # relationships
    vendor_data = relationship("VendorData", uselist=False, backref="item")
    upgrade = relationship("Item", uselist=False)


class MarketHistoryElement(Base):
    __tablename__ = 'market_history_elements'

    START_ERA = datetime.datetime(2011, 12, 16, 0, 0, 0, tzinfo=utc)  # first closed beta day
    TICK_SECONDS_LENGTH = 20 * 60

    item_id = Column(Integer, ForeignKey(Item.data_id), nullable=False, primary_key=True, autoincrement=False)
    item = relationship(Item, backref="market_history_element")
    ticks = Column(Integer, nullable=False, index=True, primary_key=True, autoincrement=False)
    buy_count = Column(Integer, index=True, nullable=False)
    buy_price = Column(Integer, index=True, nullable=False)
    sell_count = Column(Integer, index=True, nullable=False)
    sell_price = Column(Integer, index=True, nullable=False)


class VendorData(Base):
    __tablename__ = 'vendor_data'
    item_id = Column(Integer, ForeignKey(Item.data_id), primary_key=True)
    copper_cost = Column(Integer, default=None)
    karma_cost = Column(Numeric(precision=8, scale=2), default=None)
    skill_point_cost = Column(Numeric(precision=5, scale=2), default=None)


class SkillPointRecipe(Base):
    __tablename__ = 'skill_point_recipes'
    
    # possible kind of recipes
    MYSTIC_WEAPON = 0
    VARIOUS = 1
    PROMOTION_COMMON = 2
    PROMOTION_FINE = 3
    PROMOTION_RARE = 4
    SIEGE_BLUEPRINT = 5

    # fields
    output_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=False)
    output_item = relationship(Item, foreign_keys=[output_item_id])
    output_count = Column(SmallInteger, nullable=False)
    ingredient_1_item_id = Column(ForeignKey(Item.data_id), primary_key=True)
    ingredient_1_item = relationship(Item, foreign_keys=[ingredient_1_item_id])
    ingredient_1_count = Column(SmallInteger, nullable=False)
    ingredient_2_item_id = Column(ForeignKey(Item.data_id), primary_key=True)
    ingredient_2_item = relationship(Item, foreign_keys=[ingredient_2_item_id])
    ingredient_2_count = Column(SmallInteger, nullable=False)
    ingredient_3_item_id = Column(ForeignKey(Item.data_id), primary_key=True)
    ingredient_3_item = relationship(Item, foreign_keys=[ingredient_3_item_id])
    ingredient_3_count = Column(SmallInteger, nullable=False)
    ingredient_4_item_id = Column(ForeignKey(Item.data_id), primary_key=True)
    ingredient_4_item = relationship(Item, foreign_keys=[ingredient_4_item_id])
    ingredient_4_count = Column(SmallInteger, nullable=False)
    category = Column(SmallInteger, nullable=False)

    # utility functions
    def get_ingredient_count(self, i):
        if i == 0:
            return self.ingredient_1_count
        elif i == 1:
            return self.ingredient_2_count
        elif i == 2:
            return self.ingredient_3_count
        elif i == 3:
            return self.ingredient_4_count


class KarmaWeaponsData(Base):
    __tablename__ = 'karma_weapons_data'

    level = Column(SmallInteger, nullable=False, primary_key=True)
    weapon_type = Column(SmallInteger, primary_key=True)
    karma_cost = Column(Integer, nullable=False)


class RTLPMemoryTable(Base):
    __tablename__ = 'rtlp'
    __table_args__ = {'mysql_engine': 'MEMORY'}

    last_update = Column(DateTime, nullable=False)
    rarity = Column(SmallInteger, index=True, primary_key=True)
    weapon_type = Column(SmallInteger, index=True, primary_key=True)
    level = Column(SmallInteger, nullable=False, index=True, primary_key=True)
    price_i = Column(Integer, default=0, nullable=False)
    price_o = Column(Integer, default=0, nullable=False)


class Profit(Base):
    __tablename__ = 'profit'
    __table_args__ = {'mysql_engine': 'MEMORY'}

    level = Column(SmallInteger, nullable=False, index=True, primary_key=True)
    weapon_type = Column(SmallInteger, index=True, primary_key=True)
    avg_price_o = Column(Integer, default=0, nullable=False)
    avg_price_i = Column(Integer, default=0, nullable=False)
    last_update = Column(DateTime, nullable=False)


class RG_Raw(Base):
    __tablename__ = 'rg_raw'
    __table_args__ = {'mysql_engine': 'MEMORY'}

    weapon_type = Column(SmallInteger, index=True, primary_key=True)
    level = Column(SmallInteger, nullable=False, index=True, primary_key=True)
    karma_cost = Column(Integer, nullable=False)
    last_update = Column(DateTime, nullable=False)
    avg_profit_si = Column(Numeric)
    avg_profit_so = Column(Numeric)


#class RecipeGain(Base):
#    __tablename__ = 'recipe_gain'

class RecipeItemType(Base):
    __tablename__ = 'recipe_item_type'

    id = Column(SmallInteger, primary_key=True)
    name = Column(String(length=64), nullable=False)


class Recipe(Base):
    __tablename__ = 'recipe'

    recipe_id = Column(Integer, primary_key=True)
    type_id = Column(SmallInteger, ForeignKey(RecipeItemType.id))
    output_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=False, index=True)
    output_item = relationship(Item, foreign_keys=[output_item_id])
    output_item_count = Column(Integer, nullable=False)
    min_rating = Column(Integer, nullable=False)
    time_to_craft_ms = Column(Integer, nullable=False)
    vendor_value = Column(Integer, nullable=False)
    can_armorsmith = Column(Boolean, nullable=False, index=True)
    can_artificer = Column(Boolean, nullable=False, index=True)
    can_chef = Column(Boolean, nullable=False, index=True)
    can_huntsman = Column(Boolean, nullable=False, index=True)
    can_jeweler = Column(Boolean, nullable=False, index=True)
    can_leatherworker = Column(Boolean, nullable=False, index=True)
    can_tailor = Column(Boolean, nullable=False, index=True)
    can_weaponsmith = Column(Boolean, nullable=False, index=True)
    ingredient_1_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=False, index=True)
    ingredient_1_item = relationship(Item, foreign_keys=[ingredient_1_item_id])
    ingredient_1_count = Column(Integer, nullable=False)
    ingredient_2_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=True, index=True)
    ingredient_2_item = relationship(Item, foreign_keys=[ingredient_2_item_id])
    ingredient_2_count = Column(Integer, nullable=True)
    ingredient_3_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=True, index=True)
    ingredient_3_item = relationship(Item, foreign_keys=[ingredient_3_item_id])
    ingredient_3_count = Column(Integer, nullable=True)
    ingredient_4_item_id = Column(Integer, ForeignKey(Item.data_id), nullable=True, index=True)
    ingredient_4_item = relationship(Item, foreign_keys=[ingredient_4_item_id])
    ingredient_4_count = Column(Integer, nullable=True)
    learned_from_item = Column(Boolean, nullable=False)
    autolearned = Column(Boolean, nullable=False)

    def _ingredients(self):
        for i in range(4):
            ingredient_name = 'ingredient_%d_item'  % (i+1)
            count_name = 'ingredient_%d_count'  % (i+1)
            if getattr(self, ingredient_name) is not None:
                yield Ingredient(getattr(self, ingredient_name), getattr(self, count_name))

    @property
    def ingredients(self):
        return list(self._ingredients())

    @staticmethod
    def count_attributes():
        return [Recipe.ingredient_1_count,
                Recipe.ingredient_2_count,
                Recipe.ingredient_3_count,
                Recipe.ingredient_4_count]

    @property
    def has_ingredient_2(self):
        return self.ingredient_2_item is not None

    @property
    def has_ingredient_3(self):
        return self.ingredient_3_item is not None

    @property
    def has_ingredient_4(self):
        return self.ingredient_4_item is not None