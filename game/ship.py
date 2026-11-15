
class Spaceship:
    """Единое серверное состояние корабля и экипажа."""

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

        self.crew = {
            "commander": {
                "name": "Alex Morgan",
                "role": "Commander",
                "health": 100,
                "heart_rate": 72
            },
            "engineer": {
                "name": "Daniel Carter",
                "role": "Engineer",
                "health": 100,
                "heart_rate": 76
            },
            "medical": {
                "name": "Sarah Wilson",
                "role": "Medical Officer",
                "health": 100,
                "heart_rate": 70
            },
            "pilot": {
                "name": "James Anderson",
                "role": "Pilot",
                "health": 100,
                "heart_rate": 74
            }
        }

        # Текущий игровой сценарий
        self.current_scenario = None
        self.scenario_completed = False

    # =====================================
    # HELPERS
    # =====================================

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    # =====================================
    # SHIP STATUS
    # =====================================

    def get_status(self):
        """Публичная телеметрия корабля."""

        return {
            "oxygen": self.oxygen,
            "energy": self.energy,
            "temperature": self.temperature,
            "hull_integrity": self.hull_integrity,
            "modules": self.modules.copy(),
            "current_scenario": self.current_scenario,
            "scenario_completed": self.scenario_completed
        }

    def get_crew_status(self):
        """Приватные показатели экипажа."""

        return {
            member_id: member.copy()
            for member_id, member in self.crew.items()
        }

    # =====================================
    # SHIP PARAMETERS
    # =====================================

    def damage_hull(self, amount):
        if amount < 0:
            raise ValueError("Damage cannot be negative")

        self.hull_integrity = self.clamp(
            self.hull_integrity - amount, 0, 100
        )

    def consume_energy(self, amount):
        if amount < 0:
            raise ValueError("Energy consumption cannot be negative")

        self.energy = self.clamp(
            self.energy - amount, 0, 100
        )

    def consume_oxygen(self, amount):
        if amount < 0:
            raise ValueError("Oxygen consumption cannot be negative")

        self.oxygen = self.clamp(
            self.oxygen - amount, 0, 100
        )

    def change_temperature(self, amount):
        self.temperature = self.clamp(
            self.temperature + amount, -100, 100
        )

    def restore_oxygen(self, amount):
        if amount < 0:
            raise ValueError("Restoration cannot be negative")

        self.oxygen = self.clamp(
            self.oxygen + amount, 0, 100
        )

    def restore_energy(self, amount):
        if amount < 0:
            raise ValueError("Restoration cannot be negative")

        self.energy = self.clamp(
            self.energy + amount, 0, 100
        )

    def repair_hull(self, amount):
        if amount < 0:
            raise ValueError("Repair cannot be negative")

        self.hull_integrity = self.clamp(
            self.hull_integrity + amount, 0, 100
        )

    # =====================================
    # MODULES
    # =====================================

    def set_module_status(self, module_name, status):
        if module_name not in self.modules:
            raise ValueError(f"Unknown module: {module_name}")

        allowed_statuses = ("ONLINE", "OFFLINE", "DAMAGED")

        if status not in allowed_statuses:
            raise ValueError(f"Invalid module status: {status}")

        self.modules[module_name] = status

    # =====================================
    # CREW MANAGEMENT
    # =====================================

    def damage_crew(self, member_id, amount):
        if member_id not in self.crew:
            raise ValueError(f"Unknown crew member: {member_id}")

        if amount < 0:
            raise ValueError("Damage cannot be negative")

        member = self.crew[member_id]

        member["health"] = self.clamp(
            member["health"] - amount, 0, 100
        )

    def heal_crew(self, member_id, amount):
        if member_id not in self.crew:
            raise ValueError(f"Unknown crew member: {member_id}")

        if amount < 0:
            raise ValueError("Healing cannot be negative")

        member = self.crew[member_id]

        member["health"] = self.clamp(
            member["health"] + amount, 0, 100
        )

    def set_heart_rate(self, member_id, bpm):
        if member_id not in self.crew:
            raise ValueError(f"Unknown crew member: {member_id}")

        self.crew[member_id]["heart_rate"] = self.clamp(
            bpm, 0, 220
        )

    def update_crew_environment(self):
        """Игровая реакция экипажа на опасные условия."""

        for member in self.crew.values():

            if member["health"] <= 0:
                continue

            # Нехватка кислорода
            if self.oxygen <= 20:
                member["heart_rate"] = self.clamp(
                    member["heart_rate"] + 15, 0, 220
                )

                member["health"] = self.clamp(
                    member["health"] - 5, 0, 100
                )

            # Опасная температура
            if self.temperature < 10 or self.temperature > 35:
                member["heart_rate"] = self.clamp(
                    member["heart_rate"] + 10, 0, 220
                )

                member["health"] = self.clamp(
                    member["health"] - 5, 0, 100
                )

    # =====================================
    # SCENARIO MANAGEMENT
    # =====================================

    def start_scenario(self, scenario_id):
        """Устанавливает текущий игровой сценарий."""

        self.current_scenario = scenario_id
        self.scenario_completed = False

    def complete_scenario(self):
        self.scenario_completed = True

    def reset(self):
        """Полностью восстанавливает корабль и экипаж."""

        self.__init__()
