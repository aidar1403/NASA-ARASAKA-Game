def asteroid_collision(ship):
    """
    Событие столкновения с астероидом.
    """

    print("\n!!! ASTEROID COLLISION !!!")

    ship.damage_hull(25)
    ship.consume_energy(15)
    ship.change_temperature(5)

    ship.set_module_status("life_support", "DAMAGED")
    ship.set_module_status("navigation", "DAMAGED")

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
            "damaged_modules": ["life_support", "navigation"]
        },
        "crew": ship.get_crew_status(),
        "telemetry": ship.get_status()
    }


def solar_flare(ship):
    """Солнечная вспышка нарушает работу связи."""

    ship.consume_energy(15)
    ship.set_module_status("communications", "DAMAGED")
    ship.change_temperature(3)
    ship.apply_crew_delta({"health": -5, "heart_rate": 8})
    ship.update_crew_environment()

    return {
        "event": "SOLAR_FLARE",
        "message": "Solar flare detected! Communications disrupted.",
        "effects": {
            "energy_loss": 15,
            "temperature_change": 3,
            "damaged_modules": ["communications"]
        },
        "crew": ship.get_crew_status(),
        "telemetry": ship.get_status()
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
    ship.update_crew_environment()

    return {
        "event": "RADIATION_EXPOSURE",
        "message": "Radiation levels are dangerously high!",
        "effects": {
            "crew_health_loss": 10,
            "energy_loss": 10
        },
        "crew": ship.get_crew_status(),
        "telemetry": ship.get_status()
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

    ship.update_crew_environment()

    return {
        "event": "SOLAR_PARTICLE_EVENT",
        "message": "Solar particle event detected! Crew exposure risk!",
        "effects": {
            "energy_loss": 20,
            "temperature_change": 5,
            "crew_health_loss": 15
        },
        "crew": ship.get_crew_status(),
        "telemetry": ship.get_status()
    }


def coronal_mass_ejection(ship):
    """Корональный выброс массы нарушает энергосистему."""

    ship.consume_energy(25)
    ship.change_temperature(8)
    ship.set_module_status("navigation", "DAMAGED")
    ship.apply_crew_delta({"health": -5, "heart_rate": 10})
    ship.update_crew_environment()

    return {
        "event": "CORONAL_MASS_EJECTION",
        "message": "Coronal mass ejection detected! Power systems unstable.",
        "effects": {
            "energy_loss": 25,
            "temperature_change": 8,
            "damaged_modules": ["navigation"]
        },
        "crew": ship.get_crew_status(),
        "telemetry": ship.get_status()
    }