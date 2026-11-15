
def asteroid_collision(ship):
    """
    Событие столкновения с астероидом.

    Последствия:
    - повреждение корпуса;
    - потеря энергии;
    - повреждение системы жизнеобеспечения;
    - изменение температуры;
    - ухудшение состояния экипажа.
    """

    print("\n!!! ASTEROID COLLISION !!!")

    ship.damage_hull(25)
    ship.consume_energy(15)
    ship.change_temperature(5)

    ship.set_module_status(
        "life_support",
        "DAMAGED"
    )

    ship.set_module_status(
        "navigation",
        "DAMAGED"
    )

    ship.update_crew_environment()

    print("Hull integrity:", ship.hull_integrity)
    print("Energy:", ship.energy)
    print("Temperature:", ship.temperature)
    print("Collision event completed.")

    return {
        "event": "ASTEROID_COLLISION",
        "message": "Asteroid impact detected!",
        "effects": {
            "hull_damage": 25,
            "energy_loss": 15,
            "temperature_change": 5,
            "damaged_modules": [
                "life_support",
                "navigation"
            ]
        }
    }


def solar_flare(ship):
    """Солнечная вспышка нарушает работу связи."""

    ship.consume_energy(15)
    ship.set_module_status("communications", "DAMAGED")
    ship.change_temperature(3)

    return {
        "event": "SOLAR_FLARE",
        "message": "Solar flare detected! Communications disrupted.",
        "effects": {
            "energy_loss": 15,
            "temperature_change": 3,
            "damaged_modules": ["communications"]
        }
    }


def radiation_exposure(ship):
    """Воздействие радиационного пояса на экипаж."""

    for member_id in ship.crew:
        ship.damage_crew(member_id, 10)
        ship.set_heart_rate(
            member_id,
            ship.crew[member_id]["heart_rate"] + 15
        )

    ship.consume_energy(10)

    return {
        "event": "RADIATION_EXPOSURE",
        "message": "Radiation levels are dangerously high!",
        "effects": {
            "crew_health_loss": 10,
            "energy_loss": 10
        }
    }


def solar_particle_event(ship):
    """Поток солнечных частиц угрожает экипажу и системам."""

    ship.consume_energy(20)
    ship.change_temperature(5)

    for member_id in ship.crew:
        ship.damage_crew(member_id, 15)
        ship.set_heart_rate(
            member_id,
            ship.crew[member_id]["heart_rate"] + 20
        )

    return {
        "event": "SOLAR_PARTICLE_EVENT",
        "message": "Solar particle event detected! Crew exposure risk!",
        "effects": {
            "energy_loss": 20,
            "temperature_change": 5,
            "crew_health_loss": 15
        }
    }


def coronal_mass_ejection(ship):
    """Корональный выброс массы нарушает энергосистему."""

    ship.consume_energy(25)
    ship.change_temperature(8)
    ship.set_module_status("navigation", "DAMAGED")

    return {
        "event": "CORONAL_MASS_EJECTION",
        "message": "Coronal mass ejection detected! Power systems unstable.",
        "effects": {
            "energy_loss": 25,
            "temperature_change": 8,
            "damaged_modules": ["navigation"]
        }
    }
