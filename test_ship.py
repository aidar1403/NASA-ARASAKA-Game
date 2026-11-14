
from game.ship import Spaceship
from game.events import asteroid_collision

ship = Spaceship()

print("=== BEFORE COLLISION ===")
print(ship.get_status())

asteroid_collision(ship)

print("\n=== AFTER COLLISION ===")
print(ship.get_status())
