class Identification:
    def __init__(self, name, min_value=None, max_value=None, raw=None):
        self.min_value = min_value
        self.max_value = max_value
        self.raw = raw
        self.name = name
        self.readable_name = self.format_name(name)
        self.min_value_readable = self.format_value(min_value)
        self.max_value_readable = self.format_value(max_value)
        self.raw_readable = self.format_value(raw)

    @staticmethod
    def from_dict(name, data):
        if isinstance(data, dict):
            return Identification(
                name=name,
                min_value=data.get('min'),
                max_value=data.get('max'),
                raw=data.get('raw')
            )
        else:
            return Identification(name=name, raw=data)

    def to_dict(self):
        return {
            'readable_name': self.readable_name,
            'name': self.name,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'raw': self.raw,
            'min_value_readable': self.min_value_readable,
            'max_value_readable': self.max_value_readable,
            'raw_readable': self.raw_readable
        }

    @staticmethod
    def format_name(name):
        mapping = {
            "mainAttackDamage": "Main Attack Damage",
            "rawDexterity": "Dexterity",
            "rawIntelligence": "Intelligence",
            "rawStrength": "Strength",
            "rawAgility": "Agility",
            "rawDefence": "Defence",
            "xpBonus": "XP Bonus",
            "walkSpeed": "Walk Speed",
            "spellCost": "Spell Cost",
            "manaRegen": "Mana Regen",
            "thunderDamage": "Thunder Damage",
            "thunderDefence": "Thunder Defence",
            "waterDamage": "Water Damage",
            "waterDefence": "Water Defence",
            "fireDamage": "Fire Damage",
            "fireDefence": "Fire Defence",
            "airDamage": "Air Damage",
            "airDefence": "Air Defence",
            "earthDamage": "Earth Damage",
            "earthDefence": "Earth Defence",
            "rawHealth": "Health",
            "healthRegen": "Health Regen",
            "manaSteal": "Mana Steal",
            "spellDamage": "Spell Damage",
            "1stSpellCost": "1st Spell Cost",
            "raw1stSpellCost": "1st Spell Cost",
            "2ndSpellCost": "2nd Spell Cost",
            "raw2ndSpellCost": "2nd Spell Cost",
            "3rdSpellCost": "3rd Spell Cost",
            "raw3rdSpellCost": "3rd Spell Cost",
            "4thSpellCost": "4th Spell Cost",
            "raw4thSpellCost": "4th Spell Cost",
            "rawSpellDamage": "Spell Damage",
            "healingEfficiency": "Healing Efficiency",
            "soulPointRegen": "Soul Point Regen",
            "lifeSteal": "Life Steal",
            "rawAttackSpeed": "Attack Speed",
            "rawMainAttackDamage": "Main Attack Damage",
            "rawThunderSpellDamage": "Thunder Spell Damage",
            "rawWaterSpellDamage": "Water Spell Damage",
            "rawFireSpellDamage": "Fire Spell Damage",
            "rawAirSpellDamage": "Air Spell Damage",
            "rawEarthSpellDamage": "Earth Spell Damage",
            "healthRegenRaw": "Health Regen",
            "airSpellDamage": "Air Spell Damage",
            "fireSpellDamage": "Fire Spell Damage",
            "earthSpellDamage": "Earth Spell Damage",
            "waterSpellDamage": "Water Spell Damage",
            "thunderSpellDamage": "Thunder Spell Damage",
            "lootBonus": "Loot Bonus",
            "slowEnemy": "Slow Enemy",
            "sprintRegen": "Sprint Regen",
            "exploding": "Exploding",
            "reflection": "Reflection",
            "thorns": "Thorns",
            "poison": "Poison",
            "stealing": "Stealing",
            "sprint": "Sprint",
            "elementalDamage": "Elemental Damage",
            "elementalDefence": "Elemental Defence",
            "weakenEnemy": "Weaken Enemy",
            "earthMainAttackDamage": "Earth Main Attack Damage",
            "rawEarthMainAttackDamage": "Earth Main Attack Damage",
            "airMainAttackDamage": "Air Main Attack Damage",
            "rawAirMainAttackDamage": "Air Main Attack Damage",
            "fireMainAttackDamage": "Fire Main Attack Damage",
            "rawFireMainAttackDamage": "Fire Main Attack Damage",
            "waterMainAttackDamage": "Water Main Attack Damage",
            "rawWaterMainAttackDamage": "Water Main Attack Damage",
            "thunderMainAttackDamage": "Thunder Main Attack Damage",
            "rawThunderMainAttackDamage": "Thunder Main Attack Damage",
            "jumpHeight": "Jump Height",
            "neutralDamage": "Neutral Damage",
            "rawNeutralDamage": "Neutral Damage",
            "rawDamage": "Damage",
            "elementalSpellDamage": "Elemental Spell Damage",
            "knockback": "Knockback",
            "rawAirDamage": "Air Damage",
            "rawElementalSpellDamage": "Elemental Spell Damage",
            "damage": "Damage",
        }
        readable_name = mapping.get(name, name)
        return readable_name

    def format_value(self, value):
        suffixes = {
            "manaRegen": "/5s",
            "manaSteal": "/3s",
            "rawHealth": "",
            "rawDexterity": "",
            "rawIntelligence": "",
            "rawStrength": "",
            "rawAgility": "",
            "rawDefence": "",
            "raw1stSpellCost": "",
            "raw2ndSpellCost": "",
            "raw3rdSpellCost": "",
            "raw4thSpellCost": "",
            "rawSpellDamage": "",
            "lifeSteal": "/3s",
            "rawAttackSpeed": " tier",
            "rawMainAttackDamage": "",
            "rawThunderSpellDamage": "",
            "rawWaterSpellDamage": "",
            "rawFireSpellDamage": "",
            "rawAirSpellDamage": "",
            "rawEarthSpellDamage": "",
            "healthRegenRaw": "",
            "rawEarthMainAttackDamage": "",
            "jumpHeight": "",
            "rawNeutralDamage": "",
            "rawDamage": "",
            "rawAirDamage": "",
            "rawElementalSpellDamage": "",
            "poison": "/3s",
        }

        # Determine suffix based on name
        suffix = suffixes.get(self.name, "%")

        if value is not None:
            return f"{value}{suffix}"
        return None
