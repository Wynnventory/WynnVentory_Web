from .item import Item
from .item_types import ItemType

class Accessory(Item):
    def __init__(self, name, rarity, item_subtype, drop_restriction, base, identifications, requirements, drop_meta=None, lore=None):
        super().__init__(name, rarity, 0, ItemType.ACCESSORY.value, item_subtype, drop_restriction, base, identifications, requirements, drop_meta, lore)

    @staticmethod
    def from_dict(data):
        item = Item.from_dict(data, ItemType.ACCESSORY.value)
        return Accessory(
            name=item.name,
            rarity=item.rarity,
            item_subtype=data.get('accessoryType', 'Unknown Subtype'),
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