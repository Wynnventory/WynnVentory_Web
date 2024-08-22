from .item import Item
from .item_types import ItemType

class Armour(Item):
    CLASS_REQUIREMENT_MAPPING = {
        'archer': 'Archer/Hunter',
        'warrior': 'Warrior/Knight',
        'mage': 'Mage/Dark Wizard',
        'assassin': 'Assassin/Ninja',
        'shaman': 'Shaman/Skyseer'
    }

    def __init__(self, name, rarity, powder_slots, item_subtype, drop_restriction, base, identifications, requirements, armor_material, drop_meta=None, lore=None):
        super().__init__(name, rarity, powder_slots, ItemType.ARMOR.value, item_subtype, drop_restriction, base, identifications, requirements, drop_meta, lore)
        self.armor_material = armor_material
        if 'Classrequirement' in self.requirements:
            class_req_key = self.requirements.pop('Classrequirement')
            self.requirements['class_req'] = Armour.CLASS_REQUIREMENT_MAPPING.get(class_req_key, class_req_key)

    @staticmethod
    def from_dict(data):
        item = Item.from_dict(data, ItemType.ARMOR.value)
        requirements = item.requirements

        return Armour(
            name=item.name,
            rarity=item.rarity,
            powder_slots=item.powder_slots,
            item_subtype=data.get('armourType', 'Unknown Subtype'),  # Adjusted to use 'armourType' from JSON
            drop_restriction=item.drop_restriction,
            base=item.base,
            identifications=item.identifications,
            requirements=requirements,
            armor_material=data.get('armourMaterial', 'Unknown Material'),  # New field for armor material
            drop_meta=item.drop_meta,
            lore=item.lore
        )

    def to_dict(self):
        data = super().to_dict()
        data['armor_material'] = self.armor_material  # Add armor material to the dictionary
        return data