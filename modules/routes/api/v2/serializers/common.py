"""Field-normalization helpers shared by v2 serializers.

v2 exposes lowercase, snake_case vocabulary; the storage layer keeps the
mod-submitted vocabulary ("Weapon", "MaterialItem", ...). These tables are the
single translation point between the two.
"""

# storage item_type -> v2 label
_ITEM_TYPE_FROM_STORAGE = {
    'Weapon': 'weapon',
    'Armour': 'armour',
    'Accessory': 'accessory',
    'GearItem': 'gear',
    'MaterialItem': 'material',
    'PowderItem': 'powder',
    'AmplifierItem': 'amplifier',
    'EmeraldPouchItem': 'emerald_pouch',
}

# v2 label -> storage item_type (only labels accepted as filters)
ITEM_TYPE_TO_STORAGE = {
    'weapon': 'Weapon',
    'armour': 'Armour',
    'accessory': 'Accessory',
    'material': 'MaterialItem',
    'powder': 'PowderItem',
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
