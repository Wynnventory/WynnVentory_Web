from .item import Item
from .item_types import ItemType, WeaponType

class Weapon(Item):
    WEAPON_CLASS_REQUIREMENTS = {
        WeaponType.DAGGER.value: 'Assassin/Ninja',
        WeaponType.RELIK.value: 'Shaman/Skyseer',
        WeaponType.SPEAR.value: 'Warrior/Knight',
        WeaponType.BOW.value: 'Archer/Hunter',
        WeaponType.WAND.value: 'Mage/Dark Wizard'
    }

    def __init__(self, name, rarity, powder_slots, item_subtype, drop_restriction, attack_speed, base, identifications, requirements, drop_meta=None, lore=None):
        super().__init__(name, rarity, powder_slots, ItemType.WEAPON.value, item_subtype, drop_restriction, base, identifications, requirements, drop_meta, lore)
        self.attack_speed = ' '.join(word.capitalize() for word in attack_speed.replace('_', ' ').split())
        # self.average_dps = average_dps
        self.class_req = self.WEAPON_CLASS_REQUIREMENTS.get(self.item_subtype, 'Unknown Class')

    @staticmethod
    def from_dict(data):
        # Process the base item data using the from_dict method from the Item class
        item = Item.from_dict(data, ItemType.WEAPON.value)

        # Handle the specific fields for the Weapon class
        return Weapon(
            name=item.name,
            rarity=item.rarity,
            powder_slots=item.powder_slots,
            item_subtype=data.get('weaponType', 'Unknown Subtype'),  # Use 'weaponType' as per the new structure
            drop_restriction=item.drop_restriction,
            attack_speed=data.get('attackSpeed', 'Unknown Speed'),
            # average_dps=data.get('averageDps'),
            base=item.base,
            identifications=item.identifications,
            requirements=item.requirements,
            drop_meta=item.drop_meta,
            lore=item.lore
        )

    def to_dict(self):
        data = super().to_dict()
        data['attack_speed'] = self.attack_speed
        # data['average_dps'] = self.average_dps
        data['class_req'] = self.class_req
        return data