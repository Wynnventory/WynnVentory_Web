from modules.utils.utils import map_local_icons
from .base import Base
from .identification import Identification
from .item_types import ItemType


class Item:
    def __init__(self, name, rarity, powder_slots, item_type, item_subtype, drop_restriction, base, identifications, requirements, drop_meta=None, lore=None):
        self.name = name
        self.rarity = rarity.capitalize() if isinstance(rarity, str) else rarity
        self.powder_slots = powder_slots
        self.item_type = ItemType(item_type) if isinstance(item_type, str) else item_type
        self.item_subtype = item_subtype
        self.drop_restriction = drop_restriction
        self.base = base
        self.identifications = identifications
        self.requirements = requirements
        self.drop_meta = drop_meta
        self.lore = lore

    @staticmethod
    def from_dict(data, item_type):
        identifications = {k: Identification.from_dict(k, v) for k, v in data.get('identifications', {}).items()}
        base = Base.from_dict(data.get('base', {}), average_dps=data.get('averageDps'))
        name = data.get('item_name', "Unknown Item")

        # Capitalize requirements keys
        requirements = {k.capitalize(): v for k, v in data.get('requirements', {}).items()}

        # Determine the correct item subtype from the data
        item_subtype = data.get('weaponType', 
                                data.get('armorType', 
                                        data.get('accessoryType', 
                                                 data.get('tomeType',
                                                          data.get('type', 'Unknown Subtype')))))

        return Item(
            name=name,
            rarity=data.get('rarity', 'Unknown Tier'),
            powder_slots=data.get('powderSlots', 0),
            item_type=item_type,
            item_subtype=item_subtype,
            drop_restriction=data.get('dropRestriction', 'Unknown'),
            base=base,
            identifications=identifications,
            requirements=requirements,
            drop_meta=data.get('dropMeta', {}),
            lore=data.get('lore', None)
        )

    def to_dict(self):
        return {
            'name': self.name,
            'rarity': self.rarity,
            'powder_slots': self.powder_slots,
            'item_type': self.item_type.value,
            'item_subtype': self.item_subtype,
            'drop_restriction': self.drop_restriction,
            'base': self.base.to_dict(),
            'identifications': {k: v.to_dict() for k, v in self.identifications.items()},
            'requirements': self.requirements,
            'drop_meta': self.drop_meta,
            'lore': self.lore,
            'icon': map_local_icons(self.item_subtype.lower().replace(' ', '_') + ".png") 
        }