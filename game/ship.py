
class Spaceship:
    def __init__(self):
        self.oxygen = 100
        self.energy = 100
        self.temperature = 22
        self.hull_integrity = 100

        self.modules = {
            "life_support": "ONLINE",
            "engine": "ONLINE",
            "navigation": "ONLINE",
            "communications": "ONLINE"
        }

    def get_status(self):
        return {
            "oxygen": self.oxygen,
            "energy": self.energy,
            "temperature": self.temperature,
            "hull_integrity": self.hull_integrity,
            "modules": self.modules.copy()
        }

    def damage_hull(self, amount):
        if amount < 0:
            raise ValueError("Damage cannot be negative")

        self.hull_integrity = max(0, self.hull_integrity - amount)

    def consume_energy(self, amount):
        if amount < 0:
            raise ValueError("Energy consumption cannot be negative")

        self.energy = max(0, self.energy - amount)

    def set_module_status(self, module_name, status):
        if module_name not in self.modules:
            raise ValueError(f"Unknown module: {module_name}")

        allowed_statuses = ("ONLINE", "OFFLINE", "DAMAGED")

        if status not in allowed_statuses:
            raise ValueError(f"Invalid module status: {status}")

        self.modules[module_name] = status
