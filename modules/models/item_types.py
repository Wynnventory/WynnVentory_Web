from enum import Enum


class ItemType(Enum):
    WEAPON = 'weapon'
    ARMOR = 'armor'
    ACCESSORY = 'accessory'
    TOME = 'tome'


class WeaponType(Enum):
    DAGGER = 'dagger'
    RELIK = 'relik'
    SPEAR = 'spear'
    BOW = 'bow'
    WAND = 'wand'


class ArmorType(Enum):
    HELMET = 'helmet'
    CHESTPLATE = 'chestplate'
    LEGGINGS = 'leggings'
    BOOTS = 'boots'


class AccessoryType(Enum):
    RING = 'ring'
    BRACELET = 'bracelet'
    NECKLACE = 'necklace'
