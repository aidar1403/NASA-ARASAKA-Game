import json
import socketserver
import threading
import uuid

from game.ship import Spaceship
from game.events import asteroid_collision


HOST = "127.0.0.1"
PORT = 5000

VALID_ROLES = {"mission_control", "onboard_commander"}

VALID_MODULES = {
    "life_support",
    "engine",
    "navigation",
    "communications"
}


# =========================================================
# SCENARIO DATABASE
# =========================================================

SCENARIOS = {
    "radiation_belt": {
        "title": "RADIATION BELT ALERT",
        "alert": (
            "RADIATION WARNING: The spacecraft is entering a "
            "Radiation Belt Enhancement region. Energetic electron "
            "flux is elevated. Move the crew to a protected area."
        ),
        "crew_alert": (
            "RADIATION ALERT: Elevated energetic particle levels "
            "detected. Move to the best-shielded compartment and "
            "monitor radiation exposure."
        ),
        "level": "CRITICAL",
        "initial": {
            "oxygen": -20,
            "energy": -8,
            "hull_integrity": -3,
            "temperature": 2
        },
        "crew_delta": {"health": -8, "heart_rate": 12},
        "modules": {"life_support": "DAMAGED"},
        "choices": [
            {
                "text": "Move the crew to the shielded compartment and monitor radiation.",
                "delta": {
                    "oxygen": 4, "energy": -12,
                    "hull_integrity": 0, "temperature": -1
                },
                "crew_delta": {"health": -2, "heart_rate": 3},
                "modules": {"life_support": "DAMAGED"},
                "outcome": (
                    "The crew reached the shielded compartment. "
                    "Radiation exposure is reduced, but the shelter "
                    "systems consume reserve power."
                )
            },
            {
                "text": "Turn off the oxygen system to save power.",
                "delta": {
                    "oxygen": -18, "energy": 8,
                    "hull_integrity": 0, "temperature": 1
                },
                "crew_delta": {"health": -20, "heart_rate": 25},
                "modules": {"life_support": "OFFLINE"},
                "outcome": (
                    "Power was conserved, but shutting down life "
                    "support caused a dangerous oxygen drop. "
                    "The crew remains at risk."
                )
            },
            {
                "text": "Open the outer airlock to release the radiation.",
                "delta": {
                    "oxygen": -25, "energy": -5,
                    "hull_integrity": -8, "temperature": 2
                },
                "crew_delta": {"health": -25, "heart_rate": 30},
                "modules": {
                    "life_support": "OFFLINE",
                    "navigation": "DAMAGED"
                },
                "outcome": (
                    "Opening the airlock did not remove the radiation "
                    "threat. The cabin lost pressure and the hull "
                    "was further compromised."
                )
            }
        ]
    },

    "communications": {
        "title": "COMMUNICATIONS ALERT",
        "alert": (
            "COMMUNICATIONS ALERT: A powerful solar flare has been "
            "detected. Increased ionization may disturb radio links. "
            "Earth telemetry is intermittent."
        ),
        "crew_alert": (
            "COMMUNICATIONS WARNING: Solar activity is disturbing "
            "the radio link. Switch to the backup antenna and keep "
            "recording onboard measurements."
        ),
        "level": "WARNING",
        "initial": {
            "oxygen": 0,
            "energy": -12,
            "hull_integrity": -4,
            "temperature": 3
        },
        "crew_delta": {"health": -3, "heart_rate": 5},
        "modules": {"communications": "DAMAGED"},
        "choices": [
            {
                "text": "Switch to the backup antenna and keep recording onboard telemetry.",
                "delta": {
                    "oxygen": 0, "energy": -8,
                    "hull_integrity": 0, "temperature": -1
                },
                "crew_delta": {"health": -1, "heart_rate": 2},
                "modules": {"communications": "ONLINE"},
                "outcome": (
                    "The backup antenna restored a stable link. "
                    "Mission Control can receive telemetry again, "
                    "but the antenna repair used reserve power."
                )
            },
            {
                "text": "Shut down all navigation instruments.",
                "delta": {
                    "oxygen": 0, "energy": 5,
                    "hull_integrity": 0, "temperature": 1
                },
                "crew_delta": {"health": -5, "heart_rate": 8},
                "modules": {
                    "navigation": "OFFLINE",
                    "communications": "DAMAGED"
                },
                "outcome": (
                    "Some power was saved, but navigation instruments "
                    "went offline. The spacecraft can no longer safely "
                    "verify its route."
                )
            },
            {
                "text": "Ignore the lost signal and continue without status checks.",
                "delta": {
                    "oxygen": -3, "energy": -10,
                    "hull_integrity": -8, "temperature": 3
                },
                "crew_delta": {"health": -12, "heart_rate": 15},
                "modules": {"communications": "OFFLINE"},
                "outcome": (
                    "The crew continued without telemetry. A secondary "
                    "fault went unnoticed and damaged additional systems."
                )
            }
        ]
    },

    "solar_particle": {
        "title": "SOLAR PARTICLE EVENT",
        "alert": (
            "RADIATION WARNING: A stream of Solar Energetic Particles "
            "is approaching. Dosimeters show a rising absorbed dose "
            "estimate. Crew, move to the storm shelter!"
        ),
        "crew_alert": (
            "CRITICAL RADIATION ALERT: Solar energetic particles "
            "detected. Immediately move all crew members to the "
            "most shielded area. Monitor exposure."
        ),
        "level": "CRITICAL",
        "initial": {
            "oxygen": -10,
            "energy": -10,
            "hull_integrity": -2,
            "temperature": 5
        },
        "crew_delta": {"health": -15, "heart_rate": 20},
        "modules": {"life_support": "DAMAGED"},
        "choices": [
            {
                "text": "Move the crew to the most shielded area and monitor exposure.",
                "delta": {
                    "oxygen": -2, "energy": -8,
                    "hull_integrity": 0, "temperature": -2
                },
                "crew_delta": {"health": -3, "heart_rate": 5},
                "modules": {"life_support": "DAMAGED"},
                "outcome": (
                    "The crew entered the storm shelter and exposure "
                    "risk decreased. Life-support reserves were used "
                    "to maintain the shelter."
                )
            },
            {
                "text": "Send the crew outside to inspect the hull.",
                "delta": {
                    "oxygen": -8, "energy": -5,
                    "hull_integrity": -10, "temperature": 2
                },
                "crew_delta": {"health": -30, "heart_rate": 35},
                "modules": {
                    "life_support": "DAMAGED",
                    "navigation": "DAMAGED"
                },
                "outcome": (
                    "The crew was exposed during the particle event. "
                    "The inspection did not solve the problem and "
                    "the hull suffered additional damage."
                )
            },
            {
                "text": "Turn off all radiation sensors.",
                "delta": {
                    "oxygen": -5, "energy": 3,
                    "hull_integrity": 0, "temperature": 2
                },
                "crew_delta": {"health": -10, "heart_rate": 12},
                "modules": {"communications": "DAMAGED"},
                "outcome": (
                    "The warning instruments stopped reporting. "
                    "Power was saved, but the crew lost the information "
                    "needed to track radiation exposure."
                )
            }
        ]
    },

    "lunar_approach": {
        "title": "LUNAR APPROACH — POWER ALERT",
        "alert": (
            "CRITICAL POWER ALERT: A Coronal Mass Ejection has been "
            "detected. The spacecraft power system is unstable. "
            "Prepare for lunar approach and assess the landing zone."
        ),
        "crew_alert": (
            "POWER SYSTEM WARNING: Energy reserves are falling during "
            "lunar approach. Check navigation, preserve reserve power "
            "and prepare for a controlled landing."
        ),
        "level": "CRITICAL",
        "initial": {
            "oxygen": 0,
            "energy": -25,
            "hull_integrity": -5,
            "temperature": 3
        },
        "crew_delta": {"health": -5, "heart_rate": 10},
        "modules": {"engine": "DAMAGED"},
        "choices": [
            {
                "text": "Save reserve power, disable non-essential systems, and assess the landing site.",
                "delta": {
                    "oxygen": 0, "energy": 8,
                    "hull_integrity": 0, "temperature": -1
                },
                "crew_delta": {"health": -2, "heart_rate": 3},
                "modules": {
                    "engine": "DAMAGED",
                    "navigation": "ONLINE"
                },
                "outcome": (
                    "The crew preserved reserve power and completed "
                    "a safer landing-site assessment. The engine remains "
                    "damaged, so the next maneuver will be limited."
                )
            },
            {
                "text": "Use all remaining power on non-essential systems.",
                "delta": {
                    "oxygen": 0, "energy": -20,
                    "hull_integrity": 0, "temperature": 2
                },
                "crew_delta": {"health": -10, "heart_rate": 15},
                "modules": {
                    "engine": "DAMAGED",
                    "navigation": "DAMAGED"
                },
                "outcome": (
                    "Non-essential systems consumed the remaining "
                    "reserve. Navigation checks are now unreliable "
                    "and the landing window is at risk."
                )
            },
            {
                "text": "Land immediately without checking the approach.",
                "delta": {
                    "oxygen": -2, "energy": -12,
                    "hull_integrity": -15, "temperature": 4
                },
                "crew_delta": {"health": -25, "heart_rate": 30},
                "modules": {
                    "engine": "OFFLINE",
                    "navigation": "OFFLINE"
                },
                "outcome": (
                    "The rushed landing caused a hard impact. "
                    "The engine and navigation systems went offline, "
                    "leaving the spacecraft stranded."
                )
            }
        ]
    }
}


class MissionServer(socketserver.ThreadingTCPServer):

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address):
        super().__init__(server_address, ClientHandler)

        self.ship = Spaceship()

        self.clients = {}
        self.clients_lock = threading.RLock()
        self.state_lock = threading.RLock()

        self.pending_order = None
        self.pending_proposals = {}

        self.game_over = False
        self.game_over_reason = None

    # =====================================================
    # NETWORK
    # =====================================================

    def send_to_client(self, handler, message):
        if handler is None:
            return

        try:
            payload = json.dumps(message, ensure_ascii=False) + "\n"

            with handler.send_lock:
                handler.wfile.write(payload.encode("utf-8"))
                handler.wfile.flush()

        except (OSError, BrokenPipeError, ValueError):
            self.remove_client(handler)

    def send_to_role(self, role, message):
        with self.clients_lock:
            handler = self.clients.get(role)

        if handler:
            self.send_to_client(handler, message)

    def broadcast(self, message):
        with self.clients_lock:
            handlers = list(self.clients.values())

        for handler in handlers:
            self.send_to_client(handler, message)

    def register_client(self, role, handler):
        with self.clients_lock:
            old_handler = self.clients.get(role)

            if old_handler and old_handler is not handler:
                try:
                    old_handler.request.shutdown(2)
                except OSError:
                    pass

                try:
                    old_handler.request.close()
                except OSError:
                    pass

            self.clients[role] = handler

        self.broadcast({
            "type": "PLAYER_JOINED",
            "role": role
        })

    def remove_client(self, handler):
        role = getattr(handler, "role", None)

        if not role:
            return

        removed = False

        with self.clients_lock:
            if self.clients.get(role) is handler:
                del self.clients[role]
                removed = True

        if removed:
            self.broadcast({
                "type": "PLAYER_LEFT",
                "role": role
            })

    # =====================================================
    # TELEMETRY
    # =====================================================

    def send_telemetry(self):
        with self.state_lock:
            status = self.ship.get_status()
            crew = self.ship.get_crew_status()

        self.send_to_role("mission_control", {
            "type": "TELEMETRY",
            "data": status
        })

        self.send_to_role("onboard_commander", {
            "type": "TELEMETRY",
            "data": {
                **status,
                "crew": crew
            }
        })

    # =====================================================
    # ALERTS
    # =====================================================

    def send_alert(self, message, level="WARNING", target=None):
        packet = {
            "type": "ALERT",
            "message": message,
            "level": level,
            "data": {
                "message": message,
                "level": level
            }
        }

        if target:
            self.send_to_role(target, packet)
        else:
            self.broadcast(packet)

    # =====================================================
    # GAME OVER
    # =====================================================

    def check_game_over(self):
        with self.state_lock:
            if self.game_over:
                return True

            ship = self.ship

            if ship.oxygen <= 0:
                reason = "OXYGEN_DEPLETED"
            elif ship.energy <= 0:
                reason = "ENERGY_DEPLETED"
            elif ship.hull_integrity <= 0:
                reason = "HULL_DESTROYED"
            elif ship.temperature <= 0:
                reason = "TEMPERATURE_CRITICAL_LOW"
            elif ship.temperature >= 50:
                reason = "TEMPERATURE_CRITICAL_HIGH"
            elif all(
                member["health"] <= 0
                for member in ship.crew.values()
            ):
                reason = "CREW_INCAPACITATED"
            else:
                return False

            self.game_over = True
            self.game_over_reason = reason

        reason_msg = self.get_game_over_message(reason)
        self.broadcast({
            "type": "GAME_OVER",
            "reason": reason,
            "message": reason_msg,
            "data": {
                "reason": reason,
                "message": reason_msg
            }
        })

        self.send_telemetry()
        return True

    @staticmethod
    def get_game_over_message(reason):
        messages = {
            "OXYGEN_DEPLETED": "Oxygen supply depleted. Mission failed.",
            "ENERGY_DEPLETED": "Energy reserves depleted. Mission failed.",
            "HULL_DESTROYED": "Hull integrity lost. Mission failed.",
            "TEMPERATURE_CRITICAL_LOW": "Ship temperature is critically low.",
            "TEMPERATURE_CRITICAL_HIGH": "Ship temperature is critically high.",
            "CREW_INCAPACITATED": "All crew members are incapacitated."
        }

        return messages.get(reason, "Mission failed.")

    # =====================================================
    # APPLY TELEMETRY CHANGES
    # =====================================================

    def apply_delta(self, delta):
        limits = {
            "oxygen": (0, 100),
            "energy": (0, 100),
            "hull_integrity": (0, 100),
            "temperature": (-100, 100)
        }

        for key, amount in delta.items():
            if key not in limits:
                continue

            minimum, maximum = limits[key]
            current = getattr(self.ship, key)

            value = current + amount
            value = max(minimum, min(maximum, value))

            setattr(self.ship, key, value)

    # =====================================================
    # SCENARIOS
    # =====================================================

    def load_scenario(self, scenario_id):
        if self.game_over:
            return

        scenario = SCENARIOS.get(scenario_id)

        if not scenario:
            self.send_alert(
                f"Unknown scenario: {scenario_id}",
                "WARNING",
                "mission_control"
            )
            return

        with self.state_lock:
            self.ship.reset()

            self.pending_order = None
            self.pending_proposals.clear()

            self.ship.start_scenario(scenario_id)

            self.apply_delta(scenario["initial"])
            self.ship.apply_crew_delta(scenario.get("crew_delta"))

            for module, status in scenario["modules"].items():
                self.ship.set_module_status(module, status)

            self.ship.update_crew_environment()

        self.send_alert(
            scenario["alert"],
            scenario["level"]
        )

        self.send_to_role("onboard_commander", {
            "type": "SCENARIO_ALERT",
            "data": {
                "scenario_id": scenario_id,
                "title": scenario["title"],
                "message": scenario["crew_alert"],
                "level": scenario["level"]
            }
        })

        self.broadcast({
            "type": "SCENARIO_STARTED",
            "data": {
                "scenario_id": scenario_id,
                "title": scenario["title"],
                "alert": scenario["alert"],
                "level": scenario["level"],
                "choices": [
                    choice["text"]
                    for choice in scenario["choices"]
                ],
                "source": "Educational simulation based on NASA space-weather concepts."
            }
        })

        self.check_game_over()
        self.send_telemetry()

    def choose_scenario_response(self, scenario_id, choice_index):
        if self.game_over:
            return

        with self.state_lock:
            active_id = self.ship.current_scenario

            if active_id != scenario_id:
                return

            if self.ship.scenario_completed:
                return

            scenario = SCENARIOS.get(active_id)

            if not scenario:
                return

            if not isinstance(choice_index, int):
                return

            if not 0 <= choice_index < len(scenario["choices"]):
                return

            choice = scenario["choices"][choice_index]

            self.apply_delta(choice["delta"])
            self.ship.apply_crew_delta(choice.get("crew_delta"))

            for module, status in choice.get("modules", {}).items():
                self.ship.set_module_status(module, status)

            self.ship.complete_scenario()
            self.ship.update_crew_environment()

            result = {
                "scenario_id": scenario_id,
                "choice_index": choice_index,
                "choice": choice["text"],
                "outcome": choice["outcome"],
                "delta": choice["delta"],
                "modules": choice.get("modules", {}),
                "success": choice_index == 0
            }

        self.broadcast({
            "type": "SCENARIO_OUTCOME",
            "data": {
                **result,
                "crew": self.ship.get_crew_status(),
                "telemetry": self.ship.get_status()
            }
        })

        self.send_alert(
            "Scenario decision executed: " + choice["outcome"],
            "SUCCESS" if choice_index == 0 else "WARNING"
        )

        self.check_game_over()
        self.send_telemetry()

    # =====================================================
    # ASTEROID COLLISION
    # =====================================================

    def trigger_collision(self):
        if self.game_over:
            return

        with self.state_lock:
            result = asteroid_collision(self.ship)

        self.send_alert(
            "ASTEROID COLLISION! Hull and ship systems damaged.",
            "CRITICAL"
        )

        self.broadcast({
            "type": "EVENT",
            "message": result.get("message", "Event"),
            "data": result
        })

        self.check_game_over()
        self.send_telemetry()

    # =====================================================
    # MISSION ORDERS
    # =====================================================

    def issue_order(self, module):
        if self.game_over or module not in VALID_MODULES:
            return

        with self.state_lock:
            if self.pending_order is not None:
                self.send_alert(
                    "Another mission order is still pending.",
                    "WARNING",
                    "mission_control"
                )
                return

            order = {
                "order_id": str(uuid.uuid4()),
                "module": module,
                "action": f"CHECK {module.replace('_', ' ').upper()}",
                "status": "PENDING"
            }

            self.pending_order = order

        self.send_to_role("onboard_commander", {
            "type": "ORDER",
            "data": order
        })

        self.broadcast({
            "type": "ORDER_ISSUED",
            "data": order
        })

        self.send_alert(
            f"New mission order: check {module.replace('_', ' ')}.",
            "INFO",
            "onboard_commander"
        )

    def execute_order(self, order_id=None):
        if self.game_over:
            return

        with self.state_lock:
            order = self.pending_order

            if not order:
                return

            if order_id and order["order_id"] != order_id:
                return

            module = order["module"]

            self.ship.set_module_status(module, "OFFLINE")
            self.pending_order = None
            self.ship.update_crew_environment()

        result = {
            "success": True,
            "module": module,
            "message": f"{module} has been switched OFFLINE."
        }

        self.broadcast({
            "type": "ACTION_RESULT",
            "message": result["message"],
            "data": result
        })

        self.send_alert(
            f"{module.replace('_', ' ').upper()} switched OFFLINE.",
            "WARNING"
        )

        self.check_game_over()
        self.send_telemetry()

    # =====================================================
    # CREW PROPOSALS
    # =====================================================

    def create_proposal(self, text, module=None):
        if self.game_over:
            return

        text = str(text).strip()[:500]

        if not text:
            return

        if module and module not in VALID_MODULES:
            module = None

        proposal_id = str(uuid.uuid4())

        proposal = {
            "proposal_id": proposal_id,
            "text": text,
            "module": module,
            "status": "PENDING"
        }

        with self.state_lock:
            self.pending_proposals[proposal_id] = proposal

        self.send_to_role("mission_control", {
            "type": "PROPOSAL",
            "data": proposal
        })

        self.send_to_role("onboard_commander", {
            "type": "PROPOSAL_SENT",
            "data": proposal
        })

        self.send_alert(
            "Crew submitted a new operational proposal.",
            "INFO",
            "mission_control"
        )

    def respond_to_proposal(self, proposal_id, approved):
        if self.game_over:
            return

        with self.state_lock:
            proposal = self.pending_proposals.pop(proposal_id, None)

        if not proposal:
            return

        approved = bool(approved)
        verdict = "approved" if approved else "rejected"

        self.broadcast({
            "type": "PROPOSAL_RESPONSE",
            "message": f"Proposal {verdict}: {proposal['text'][:120]}",
            "data": {
                "proposal_id": proposal_id,
                "approved": approved,
                "text": proposal["text"]
            }
        })

        if approved and proposal["module"]:
            self.issue_order(proposal["module"])

    # =====================================================
    # CHAT
    # =====================================================

    def send_chat(self, role, text):
        text = str(text).strip()[:1000]

        if not text:
            return

        sender = (
            "Mission Control"
            if role == "mission_control"
            else "Onboard Commander"
        )

        self.broadcast({
            "type": "CHAT",
            "from": role,
            "sender": sender,
            "text": text,
            "message": text
        })


# =========================================================
# CLIENT HANDLER
# =========================================================

class ClientHandler(socketserver.StreamRequestHandler):

    def setup(self):
        super().setup()
        self.role = None
        self.send_lock = threading.RLock()

    def handle(self):
        print(f"[SERVER] Connection from {self.client_address}")

        try:
            for raw_line in self.rfile:
                if not raw_line:
                    break

                try:
                    message = json.loads(raw_line.decode("utf-8").strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self.server.send_to_client(self, {
                        "type": "ERROR",
                        "message": "Invalid JSON message."
                    })
                    continue

                if not isinstance(message, dict):
                    continue

                if self.role is None:
                    self.handle_join(message)
                else:
                    self.handle_message(message)

        except (ConnectionError, OSError):
            pass

        finally:
            self.server.remove_client(self)
            print(f"[SERVER] Disconnected: {self.client_address}")

    def handle_join(self, message):
        if message.get("type") != "JOIN":
            self.server.send_to_client(self, {
                "type": "ERROR",
                "message": "Send JOIN before other messages."
            })
            return

        role = message.get("role")

        if role not in VALID_ROLES:
            self.server.send_to_client(self, {
                "type": "ERROR",
                "message": "Invalid role."
            })
            return

        self.role = role
        self.server.register_client(role, self)

        self.server.send_to_client(self, {
            "type": "WELCOME",
            "role": role,
            "message": f"Connected as {role}."
        })

        self.server.send_telemetry()

        if self.server.game_over:
            reason = self.server.game_over_reason
            msg = self.server.get_game_over_message(reason)
            self.server.send_to_client(self, {
                "type": "GAME_OVER",
                "reason": reason,
                "message": msg,
                "data": {"reason": reason, "message": msg}
            })

        with self.server.state_lock:
            order = self.server.pending_order
            active_id = self.server.ship.current_scenario
            scenario_completed = self.server.ship.scenario_completed

        if role == "onboard_commander":
            if order:
                self.server.send_to_client(self, {
                    "type": "ORDER",
                    "data": order
                })

            if active_id in SCENARIOS:
                scenario = SCENARIOS[active_id]

                self.server.send_to_client(self, {
                    "type": "SCENARIO_ALERT",
                    "data": {
                        "scenario_id": active_id,
                        "title": scenario["title"],
                        "message": scenario["crew_alert"],
                        "level": scenario["level"],
                        "completed": scenario_completed
                    }
                })

    def handle_message(self, message):
        msg_type = message.get("type")

        if msg_type == "CHAT":
            self.server.send_chat(
                self.role,
                message.get("text", "")
            )

        elif msg_type == "TRIGGER_COLLISION":
            if self.role == "mission_control":
                self.server.trigger_collision()

        elif msg_type == "ORDER":
            if self.role == "mission_control":
                self.server.issue_order(message.get("module"))

        elif msg_type == "EXECUTE_ORDER":
            if self.role == "onboard_commander":
                self.server.execute_order(message.get("order_id"))

        elif msg_type == "PROPOSAL":
            if self.role == "onboard_commander":
                self.server.create_proposal(
                    message.get("text", ""),
                    message.get("module")
                )

        elif msg_type == "PROPOSAL_RESPONSE":
            if self.role == "mission_control":
                self.server.respond_to_proposal(
                    message.get("proposal_id"),
                    message.get("approved", False)
                )

        elif msg_type == "LOAD_SCENARIO":
            if self.role == "mission_control":
                self.server.load_scenario(
                    message.get("scenario_id")
                )

        elif msg_type == "SCENARIO_CHOICE":
            if self.role == "mission_control":
                self.server.choose_scenario_response(
                    message.get("scenario_id"),
                    message.get("choice_index")
                )

        elif msg_type == "PING":
            self.server.send_to_client(self, {
                "type": "PONG"
            })

        else:
            self.server.send_to_client(self, {
                "type": "ERROR",
                "message": f"Unknown message type: {msg_type}"
            })


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if __name__ == "__main__":
    print("=" * 45)
    print("       NASA ARASAKA MISSION SERVER")
    print("=" * 45)

    try:
        with MissionServer((HOST, PORT)) as server:
            print(f"[SERVER] Running on {HOST}:{PORT}")
            print("[SERVER] Waiting for clients...")
            server.serve_forever()

    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")

    except OSError as error:
        print(f"[SERVER ERROR] {error}")