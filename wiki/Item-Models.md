# Item Models

**Sources:** `modules/models/item.py`, `modules/models/weapon.py`, `modules/models/armour.py`, `modules/models/accessory.py`, `modules/models/base.py`, `modules/models/identification.py`, `modules/models/item_types.py`

## Overview

The item model hierarchy represents Wynncraft items as returned by the Wynncraft v3 API. These models are used by the item search/fetch endpoints to parse and serialize API responses. They are **not** used for trade market listings, which use flat dictionaries.

## Class Hierarchy

```
Item (base)
 +-- Weapon
 +-- Armour
 +-- Accessory
```

Each item contains:
- `Base` stats (damage/defense values)
- List of `Identification` objects (stat modifiers)

## Item (Base Class)

**Source:** `modules/models/item.py`

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Item name |
| `rarity` | str | Normal, Unique, Rare, Legendary, Fabled, Mythic, Set |
| `powder_slots` | int | Number of powder slots |
| `item_type` | ItemType | WEAPON, ARMOR, ACCESSORY, TOME |
| `item_subtype` | str | Specific subtype (Bow, Helmet, Ring, etc.) |
| `drop_restriction` | str | Drop restriction if any |
| `base` | Base | Damage and defense stats |
| `identifications` | list[Identification] | Stat modifiers |
| `requirements` | dict | Level and skill requirements |
| `drop_meta` | dict | Drop metadata |
| `lore` | str | Item lore text |

### from_dict(data)

Parses a Wynncraft API item response:
1. Extracts base stats via `Base.from_dict()`
2. Parses each identification via `Identification.from_dict()`
3. Builds requirements, drop metadata, and lore

### to_dict()

Serializes the item, including an `icon` field mapped by `map_local_icons()`.

## Weapon

**Source:** `modules/models/weapon.py`

Extends `Item` with:

| Field | Type | Description |
|-------|------|-------------|
| `attack_speed` | str | Attack speed tier |
| `class_req` | str | Required class |

### Class Requirement Mapping

| Weapon Type | Class |
|-------------|-------|
| DAGGER | Assassin/Ninja |
| RELIK | Shaman/Skyseer |
| SPEAR | Warrior/Knight |
| BOW | Archer/Hunter |
| WAND | Mage/Dark Wizard |

## Armour

**Source:** `modules/models/armour.py`

Extends `Item` with:

| Field | Type | Description |
|-------|------|-------------|
| `armor_material` | str | Material type |
| `class_req` | str | Required class |

Armour types: `HELMET`, `CHESTPLATE`, `LEGGINGS`, `BOOTS`

## Accessory

**Source:** `modules/models/accessory.py`

Extends `Item` with no additional fields. Accessories always have `powder_slots=0`.

Accessory types: `RING`, `BRACELET`, `NECKLACE`

## Base Stats

**Source:** `modules/models/base.py`

| Field | Type | Description |
|-------|------|-------------|
| `health` | int | Health points |
| `base_damage` | str | Base damage range (e.g., "100-200") |
| `fire_damage` | str | Fire elemental damage |
| `water_damage` | str | Water elemental damage |
| `air_damage` | str | Air elemental damage |
| `earth_damage` | str | Earth elemental damage |
| `thunder_damage` | str | Thunder elemental damage |
| `fire_defence` | int | Fire defense |
| `water_defence` | int | Water defense |
| `air_defence` | int | Air defense |
| `earth_defence` | int | Earth defense |
| `thunder_defence` | int | Thunder defense |
| `average_dps` | float | Average DPS (computed) |

## Identification

**Source:** `modules/models/identification.py`

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Internal identification name |
| `min_value` | int | Minimum roll value |
| `max_value` | int | Maximum roll value |
| `raw` | int | Fixed (non-rolling) value |

### Readable Name Mapping

The model contains a mapping of 60+ internal names to human-readable labels:

| Internal Name | Readable Label |
|---------------|---------------|
| `rawStrength` | Strength |
| `rawDexterity` | Dexterity |
| `rawIntelligence` | Intelligence |
| `rawDefence` | Defence |
| `rawAgility` | Agility |
| `healthRegen` | Health Regen |
| `manaRegen` | Mana Regen |
| `spellDamage` | Spell Damage |
| `mainAttackDamage` | Main Attack Damage |
| ... | ... |

### Value Formatting

Values include unit suffixes based on the identification type:
- Percentage values: `%` suffix
- Per-time values: `/5s` or `/3s` suffix
- Tier values: `tier` suffix
- Raw values: no suffix

## Type Enums

**Source:** `modules/models/item_types.py`

```python
class ItemType(Enum):
    WEAPON = "weapon"
    ARMOR = "armour"
    ACCESSORY = "accessory"
    TOME = "tome"

class WeaponType(Enum):
    DAGGER, RELIK, SPEAR, BOW, WAND

class ArmorType(Enum):
    HELMET, CHESTPLATE, LEGGINGS, BOOTS

class AccessoryType(Enum):
    RING, BRACELET, NECKLACE
```

## Usage Context

These models are used exclusively in the item search/fetch endpoints (`/api/item/{name}` and `/api/items`). The trade market, loot pool, and raid pool systems use raw dictionaries with their own field naming conventions.
