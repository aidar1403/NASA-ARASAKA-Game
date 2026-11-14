
import socketserver
import json
import threading

from game.ship import Spaceship
from game.events import asteroid_collision

HOST = "0.0.0.0"
PORT = 5000


class MissionServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.game_lock = threading.Lock()

        # Единственное состояние корабля на сервере
        self.ship = Spaceship()
        self.pending_order = None

    def register(self, role, handler):
        with self.clients_lock:
            if role in self.clients:
                return False

            self.clients[role] = handler
            return True

    def unregister(self, role, handler):
        with self.clients_lock:
            if self.clients.get(role) is handler:
                del self.clients[role]
            else:
                return

        self.broadcast({
            "type": "PLAYER_LEFT",
            "role": role
        })

    def send_to_role(self, role, message):
        with self.clients_lock:
            handler = self.clients.get(role)

        if handler:
            try:
                handler.send_message(message)
            except OSError:
                pass

    def broadcast(self, message):
        with self.clients_lock:
            handlers = list(self.clients.values())

        for handler in handlers:
            try:
                handler.send_message(message)
            except OSError:
                pass

    def send_telemetry(self):
        with self.game_lock:
            status = self.ship.get_status()

            # Полная телеметрия для центра управления
            mission_control_data = status.copy()

            # Ограниченная информация для экипажа
            crew_data = {
                "oxygen": status["oxygen"],
                "energy": status["energy"],
                "temperature": status["temperature"],
                "modules": status["modules"].copy()
            }

        self.send_to_role("mission_control", {
            "type": "TELEMETRY",
            "data": mission_control_data
        })

        self.send_to_role("onboard_commander", {
            "type": "TELEMETRY",
            "data": crew_data
        })

    def trigger_collision(self):
        with self.game_lock:
            asteroid_collision(self.ship)

        self.broadcast({
            "type": "ALERT",
            "message": "ASTEROID COLLISION DETECTED!"
        })

        self.send_telemetry()

    def issue_order(self, module):
        if module not in ("life_support", "engine",
                          "navigation", "communications"):
            return False

        self.pending_order = {
            "action": "ISOLATE_MODULE",
            "module": module
        }

        self.send_to_role("onboard_commander", {
            "type": "ORDER",
            "data": self.pending_order
        })

        return True

    def execute_order(self):
        if not self.pending_order:
            return False

        order = self.pending_order

        with self.game_lock:
            self.ship.set_module_status(
                order["module"],
                "OFFLINE"
            )

        self.pending_order = None

        self.broadcast({
            "type": "ACTION_RESULT",
            "message": f"Module {order['module']} isolated."
        })

        self.send_telemetry()
        return True


class ClientHandler(socketserver.StreamRequestHandler):

    def setup(self):
        super().setup()
        self.send_lock = threading.Lock()
        self.role = None

    def send_message(self, message):
        data = json.dumps(message).encode("utf-8") + b"\n"

        with self.send_lock:
            self.wfile.write(data)
            self.wfile.flush()

    def handle(self):
        print(f"Connection: {self.client_address}")

        try:
            first_line = self.rfile.readline()

            if not first_line:
                return

            join_data = json.loads(first_line.decode("utf-8"))

            if join_data.get("type") != "JOIN":
                self.send_message({
                    "type": "ERROR",
                    "message": "JOIN required"
                })
                return

            role = join_data.get("role")

            if role not in ("mission_control", "onboard_commander"):
                self.send_message({
                    "type": "ERROR",
                    "message": "Invalid role"
                })
                return

            if not self.server.register(role, self):
                self.send_message({
                    "type": "ERROR",
                    "message": "Role already occupied"
                })
                return

            self.role = role

            self.send_message({
                "type": "WELCOME",
                "role": role
            })

            print(f"Player joined: {role}")

            self.server.broadcast({
                "type": "PLAYER_JOINED",
                "role": role
            })

            self.server.send_telemetry()

            while True:
                line = self.rfile.readline()

                if not line:
                    break

                message = json.loads(line.decode("utf-8"))
                message_type = message.get("type")

                if message_type == "CHAT":
                    self.server.broadcast({
                        "type": "CHAT",
                        "from": self.role,
                        "text": message.get("text", "")[:500]
                    })

                elif message_type == "TRIGGER_COLLISION":
                    if self.role == "mission_control":
                        self.server.trigger_collision()

                elif message_type == "ORDER":
                    if self.role == "mission_control":
                        module = message.get("module")

                        if not self.server.issue_order(module):
                            self.send_message({
                                "type": "ERROR",
                                "message": "Invalid module"
                            })

                elif message_type == "EXECUTE_ORDER":
                    if self.role == "onboard_commander":
                        if not self.server.execute_order():
                            self.send_message({
                                "type": "ERROR",
                                "message": "No pending order"
                            })

        except (ConnectionError, OSError, json.JSONDecodeError) as error:
            print(f"Client error: {error}")

        finally:
            if self.role:
                self.server.unregister(self.role, self)


if __name__ == "__main__":
    with MissionServer((HOST, PORT), ClientHandler) as server:
        print(f"MISSION SERVER RUNNING ON {HOST}:{PORT}")
        print("Waiting for players...")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
