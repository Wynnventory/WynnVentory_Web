class Base:
    def __init__(self, health=None, air_defence=None, air_damage=None, thunder_defence=None, thunder_damage=None,
                 fire_defence=None, fire_damage=None, water_defence=None, water_damage=None, earth_defence=None,
                 earth_damage=None,
                 base_damage=None, average_dps=None):
        self.health = health
        self.fire_damage = fire_damage
        self.fire_defence = fire_defence
        self.water_defence = water_defence
        self.water_damage = water_damage
        self.air_defence = air_defence
        self.air_damage = air_damage
        self.thunder_defence = thunder_defence
        self.thunder_damage = thunder_damage
        self.earth_defence = earth_defence
        self.earth_damage = earth_damage
        self.base_damage = base_damage
        self.average_dps = average_dps

    @staticmethod
    def from_dict(data, average_dps=None):
        return Base(
            health=data.get('baseHealth'),
            air_defence=data.get('baseAirDefence'),
            thunder_defence=data.get('baseThunderDefence'),
            earth_defence=data.get('baseEarthDefence'),
            fire_defence=data.get('baseFireDefence'),
            water_defence=data.get('baseWaterDefence'),
            fire_damage=data.get('baseFireDamage'),
            water_damage=data.get('baseWaterDamage'),
            air_damage=data.get('baseAirDamage'),
            thunder_damage=data.get('baseThunderDamage'),
            earth_damage=data.get('baseEarthDamage'),
            base_damage=data.get('baseDamage'),
            average_dps=average_dps
        )

    def to_dict(self):
        return {
            'health': self.health,
            'air_defence': self.air_defence,
            'thunder_defence': self.thunder_defence,
            'earth_defence': self.earth_defence,
            'fire_defence': self.fire_defence,
            'water_defence': self.water_defence,
            'fire_damage': self.fire_damage,
            'water_damage': self.water_damage,
            'air_damage': self.air_damage,
            'thunder_damage': self.thunder_damage,
            'earth_damage': self.earth_damage,
            'base_damage': self.base_damage,
            'average_dps': self.average_dps  # Include averageDps in the output
        }
