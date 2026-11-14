
def asteroid_collision(ship):
    """Симулирует столкновение корабля с астероидом."""

    print("\n!!! ASTEROID COLLISION !!!")

    ship.damage_hull(25)
    ship.consume_energy(15)
    ship.set_module_status("life_support", "DAMAGED")

    print("Collision event completed.")
