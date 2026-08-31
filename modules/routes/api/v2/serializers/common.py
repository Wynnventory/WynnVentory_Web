"""Field-normalization helpers shared by v2 serializers.

v2 exposes lowercase, snake_case vocabulary; the storage layer keeps the
mod-submitted vocabulary ("Weapon", "MaterialItem", ...). These tables are the
single translation point between the two.
"""

# storage item_type -> v2 label. The market storage vocabulary is the
# *Item family (see the listings filter UI and scripts/cleanup_duplicate_
# listings.py); the bare gear labels appear in pool submissions.
_ITEM_TYPE_FROM_STORAGE = {
    'GearItem': 'gear',
    'MaterialItem': 'material',
    'IngredientItem': 'ingredient',
    'PowderItem': 'powder',
    'RuneItem': 'rune',
    'DungeonKeyItem': 'dungeon_key',
    'AmplifierItem': 'amplifier',
    'EmeraldPouchItem': 'emerald_pouch',
    'AspectItem': 'aspect',
    'TomeItem': 'tome',
    'Weapon': 'weapon',
    'Armour': 'armour',
    'Accessory': 'accessory',
}

# v2 label -> storage item_type. Only labels stored in the market collection
# are accepted as listings filters, so every value read off a v2 listing
# round-trips as a filter.
ITEM_TYPE_TO_STORAGE = {
    'gear': 'GearItem',
    'material': 'MaterialItem',
    'ingredient': 'IngredientItem',
    'powder': 'PowderItem',
    'rune': 'RuneItem',
    'dungeon_key': 'DungeonKeyItem',
    'amplifier': 'AmplifierItem',
    'emerald_pouch': 'EmeraldPouchItem',
}


def item_type_from_storage(value):
    if not isinstance(value, str):
        return value
    return _ITEM_TYPE_FROM_STORAGE.get(value, value.lower())


def item_type_to_storage(label):
    if label is None:
        return None
    return ITEM_TYPE_TO_STORAGE[label]


def subtype_from_storage(value):
    if not isinstance(value, str):
        return value
    return value.lower()


def subtype_to_storage(label):
    # Stored subtypes are title-cased single words ("Bow", "Helmet", "Ring").
    if label is None:
        return None
    return label.title()


def rarity_from_storage(value):
    if not isinstance(value, str):
        return value
    return value.lower()
