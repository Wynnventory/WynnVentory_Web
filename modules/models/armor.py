from .item import Item
from .item_types import ItemType

class Armor(Item):
    def __init__(self, name, rarity, powder_slots, item_subtype, drop_restriction,base, identifications, requirements, drop_meta=None, lore=None):
        super().__init__(name, rarity, powder_slots, ItemType.ARMOR.value, item_subtype, drop_restriction, base, identifications, requirements, drop_meta, lore)

    @staticmethod
    def from_dict(data):
        item = Item.from_dict(data, ItemType.ARMOR.value)
        return Armor(
            name=item.name,
            rarity=item.rarity,
            powder_slots=item.powder_slots,
            item_subtype=data.get('type', 'Unknown Subtype'),
            drop_restriction=item.drop_restriction,
            base=item.base,
            identifications=item.identifications,
            requirements=item.requirements,
            drop_meta=item.drop_meta,
            lore=item.lore
        )

    def to_dict(self):
        data = super().to_dict()
        return data
