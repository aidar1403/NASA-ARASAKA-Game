
import sys
import socket
import json
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPlainTextEdit, QLineEdit, QComboBox, QScrollArea,
    QMessageBox
)

HOST = "127.0.0.1"
PORT = 5000

CREW_NAMES = {
    "commander": ("Alex Morgan", "COMMANDER"),
    "engineer": ("Daniel Carter", "ENGINEER"),
    "medical": ("Sarah Wilson", "MEDICAL OFFICER"),
    "pilot": ("James Anderson", "PILOT")
}

MODULES = {
    "life_support": "LIFE SUPPORT",
    "engine": "ENGINE",
    "navigation": "NAVIGATION",
    "communications": "COMMUNICATIONS"
}


class CrewInterface(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NASA ARASAKA | Onboard Commander")
        self.setMinimumSize(1360, 850)
        self.resize(1600, 1000)

        self.connection = None
        self.buffer = b""
        self.pending_order = None
        self.game_over = False

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #08111f;
                color: #e8f0fb;
                font-family: Segoe UI;
                font-size: 13px;
            }

            QFrame#sidebar {
                background: #0c192b;
                border-right: 1px solid #203650;
            }

            QFrame#panel, QFrame#card {
                background: #101f33;
                border: 1px solid #203650;
                border-radius: 12px;
            }

            QLabel#brand {
                font-size: 19px;
                font-weight: 900;
            }

            QLabel#title {
                font-size: 27px;
                font-weight: 900;
            }

            QLabel#section {
                font-size: 15px;
                font-weight: 800;
            }

            QLabel#muted {
                color: #8ba0ba;
            }

            QLabel#value {
                font-size: 28px;
                font-weight: 900;
            }

            QPushButton {
                background: #183653;
                border: 1px solid #2a4b6c;
                border-radius: 8px;
                padding: 10px;
                color: #edf5ff;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #21496f;
            }

            QPushButton#primary {
                background: #147d75;
                border-color: #1a9a8e;
            }

            QPushButton#danger {
                background: #702f3b;
                border-color: #a34655;
            }

            QPushButton:disabled {
                background: #172638;
                color: #61758d;
            }

            QPlainTextEdit, QLineEdit, QComboBox {
                background: #091625;
                border: 1px solid #29415d;
                border-radius: 8px;
                padding: 8px;
                color: #e8f0fb;
            }

            QScrollArea {
                border: none;
            }
        """)

        self.build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_server)
        self.timer.start(50)

        self.connect_server()

    # =====================================
    # UI
    # =====================================

    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 25, 20, 20)

        brand = QLabel("✦ NASA ARASAKA")
        brand.setObjectName("brand")
        side.addWidget(brand)

        subtitle = QLabel("ONBOARD COMMANDER")
        subtitle.setObjectName("muted")
        side.addWidget(subtitle)

        side.addSpacing(30)

        for item in [
            "◈  Flight Deck",
            "▣  Ship Systems",
            "♥  Crew Health",
            "⌁  Mission Orders",
            "◉  Communications"
        ]:
            label = QLabel(item)
            label.setStyleSheet("padding:13px;")
            side.addWidget(label)

        side.addStretch()

        self.connection_label = QLabel("● DISCONNECTED")
        self.connection_label.setStyleSheet(
            "color:#ff6577; font-weight:900;"
        )
        side.addWidget(self.connection_label)

        reconnect = QPushButton("Reconnect")
        reconnect.clicked.connect(self.connect_server)
        side.addWidget(reconnect)

        side.addWidget(QLabel("MISSION BUILD 0.5"))

        outer.addWidget(sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        self.main = QVBoxLayout(content)
        self.main.setContentsMargins(25, 22, 25, 25)
        self.main.setSpacing(16)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self.create_header()
        self.create_telemetry()
        self.create_crew_panel()
        self.create_systems_and_orders()
        self.create_proposals()
        self.create_communication()

    def create_header(self):
        row = QHBoxLayout()

        title = QLabel("ONBOARD FLIGHT DECK")
        title.setObjectName("title")

        self.mission_status = QLabel("● WAITING FOR SERVER")
        self.mission_status.setStyleSheet(
            "color:#f0b45c; font-weight:900;"
        )

        row.addWidget(title)
        row.addStretch()
        row.addWidget(self.mission_status)

        self.main.addLayout(row)

        subtitle = QLabel(
            "Monitor spacecraft systems, crew condition "
            "and incoming mission orders."
        )
        subtitle.setObjectName("muted")
        self.main.addWidget(subtitle)

    def create_telemetry(self):
        grid = QGridLayout()
        grid.setSpacing(12)

        self.metric_values = {}

        specs = [
            ("OXYGEN", "oxygen", "%"),
            ("ENERGY", "energy", "%"),
            ("HULL INTEGRITY", "hull_integrity", "%"),
            ("CABIN TEMPERATURE", "temperature", "°C")
        ]

        for index, (name, key, unit) in enumerate(specs):
            card = QFrame()
            card.setObjectName("card")

            box = QVBoxLayout(card)

            caption = QLabel(name)
            caption.setObjectName("muted")

            value = QLabel("--")
            value.setObjectName("value")

            state = QLabel("AWAITING TELEMETRY")
            state.setObjectName("muted")

            box.addWidget(caption)
            box.addWidget(value)
            box.addWidget(state)

            grid.addWidget(card, 0, index)
            self.metric_values[key] = (value, state, unit)

        self.main.addLayout(grid)

    # =====================================
    # PRIVATE CREW STATUS
    # =====================================

    def create_crew_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("♥ PRIVATE CREW CONDITION")
        title.setObjectName("section")
        layout.addWidget(title)

        hint = QLabel(
            "Personnel health and heart-rate simulation. "
            "Visible only to onboard crew."
        )
        hint.setObjectName("muted")
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.crew_cards = {}

        for index, (member_id, (name, role)) in enumerate(
            CREW_NAMES.items()
        ):
            card = QFrame()
            card.setObjectName("card")

            box = QVBoxLayout(card)
            box.setContentsMargins(15, 14, 15, 14)

            role_label = QLabel(role)
            role_label.setObjectName("muted")

            name_label = QLabel(name)
            name_label.setStyleSheet(
                "font-size:16px; font-weight:800;"
            )

            health = QLabel("--%")
            health.setObjectName("value")

            pulse = QLabel("♥ -- BPM")
            pulse.setStyleSheet(
                "color:#42d6a0; font-weight:800;"
            )

            condition = QLabel("AWAITING DATA")
            condition.setObjectName("muted")

            box.addWidget(role_label)
            box.addWidget(name_label)
            box.addWidget(health)
            box.addWidget(pulse)
            box.addWidget(condition)

            grid.addWidget(card, 0, index)

            self.crew_cards[member_id] = {
                "health": health,
                "pulse": pulse,
                "condition": condition
            }

        layout.addLayout(grid)
        self.main.addWidget(panel)

    def update_crew_status(self, crew):
        for member_id, member in crew.items():
            if member_id not in self.crew_cards:
                continue

            labels = self.crew_cards[member_id]

            health = int(member.get("health", 100))
            bpm = int(member.get("heart_rate", 72))

            labels["health"].setText(f"{health}%")
            labels["pulse"].setText(f"♥ {bpm} BPM")

            if health <= 0:
                condition = "INCAPACITATED"
                color = "#ff6577"
            elif health <= 30:
                condition = "CRITICAL"
                color = "#ff6577"
            elif health <= 60:
                condition = "INJURED"
                color = "#f0b45c"
            else:
                condition = "NOMINAL"
                color = "#42d6a0"

            labels["condition"].setText(condition)
            labels["condition"].setStyleSheet(
                f"color:{color}; font-weight:800;"
            )
            labels["health"].setStyleSheet(
                f"color:{color}; font-size:28px; font-weight:900;"
            )

            if bpm >= 130:
                labels["pulse"].setStyleSheet(
                    "color:#ff6577; font-weight:900;"
                )
            elif bpm >= 100:
                labels["pulse"].setStyleSheet(
                    "color:#f0b45c; font-weight:900;"
                )
            else:
                labels["pulse"].setStyleSheet(
                    "color:#42d6a0; font-weight:900;"
                )

    # =====================================
    # SYSTEMS AND ORDERS
    # =====================================

    def create_systems_and_orders(self):
        row = QHBoxLayout()

        systems = QFrame()
        systems.setObjectName("panel")

        system_layout = QVBoxLayout(systems)
        system_layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("SHIP SYSTEMS")
        title.setObjectName("section")
        system_layout.addWidget(title)

        self.module_labels = {}

        for module, name in MODULES.items():
            line = QHBoxLayout()

            label = QLabel(name)
            status = QLabel("● UNKNOWN")
            status.setStyleSheet("color:#8ba0ba; font-weight:800;")

            line.addWidget(label)
            line.addStretch()
            line.addWidget(status)

            system_layout.addLayout(line)
            self.module_labels[module] = status

        row.addWidget(systems, 1)

        orders = QFrame()
        orders.setObjectName("panel")

        order_layout = QVBoxLayout(orders)
        order_layout.setContentsMargins(18, 16, 18, 16)

        order_title = QLabel("MISSION CONTROL ORDERS")
        order_title.setObjectName("section")
        order_layout.addWidget(order_title)

        self.order_status = QLabel("NO ACTIVE ORDERS")
        self.order_status.setObjectName("muted")
        order_layout.addWidget(self.order_status)

        self.order_text = QLabel(
            "Waiting for instructions from Mission Control."
        )
        self.order_text.setWordWrap(True)
        self.order_text.setStyleSheet(
            "font-size:17px; font-weight:800;"
        )
        self.order_text.setMinimumHeight(80)
        order_layout.addWidget(self.order_text)

        self.execute_button = QPushButton(
            "✓ CONFIRM AND EXECUTE"
        )
        self.execute_button.setObjectName("primary")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.execute_order)

        order_layout.addWidget(self.execute_button)
        row.addWidget(orders, 1)

        self.main.addLayout(row)

    # =====================================
    # CREW PROPOSALS
    # =====================================

    def create_proposals(self):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("SEND PROPOSAL TO MISSION CONTROL")
        title.setObjectName("section")
        layout.addWidget(title)

        self.proposal_input = QLineEdit()
        self.proposal_input.setPlaceholderText(
            "Describe your proposed solution..."
        )
        layout.addWidget(self.proposal_input)

        row = QHBoxLayout()

        self.proposal_module = QComboBox()
        self.proposal_module.addItem(
            "No specific module", None
        )

        for module, name in MODULES.items():
            self.proposal_module.addItem(name, module)

        row.addWidget(self.proposal_module, 1)

        send = QPushButton("SEND PROPOSAL")
        send.clicked.connect(self.send_proposal)
        row.addWidget(send)

        layout.addLayout(row)
        self.main.addWidget(panel)

    def send_proposal(self):
        text = self.proposal_input.text().strip()

        if not text:
            self.add_alert("Write a proposal first.")
            return

        module = self.proposal_module.currentData()

        if self.send_message({
            "type": "PROPOSAL",
            "text": text,
            "module": module
        }):
            self.add_alert("Proposal sent to Mission Control.")
            self.proposal_input.clear()

    # =====================================
    # COMMUNICATION
    # =====================================

    def create_communication(self):
        panel = QFrame()
        panel.setObjectName("panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("DIRECT COMMUNICATION")
        title.setObjectName("section")
        layout.addWidget(title)

        self.chat_log = QPlainTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(160)
        layout.addWidget(self.chat_log)

        row = QHBoxLayout()

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            "Send a message to Mission Control..."
        )
        self.chat_input.returnPressed.connect(self.send_chat)

        send = QPushButton("SEND")
        send.clicked.connect(self.send_chat)

        row.addWidget(self.chat_input, 1)
        row.addWidget(send)

        layout.addLayout(row)
        self.main.addWidget(panel)

        alert_title = QLabel("MISSION ALERTS")
        alert_title.setObjectName("section")
        self.main.addWidget(alert_title)

        self.alert_log = QPlainTextEdit()
        self.alert_log.setReadOnly(True)
        self.alert_log.setMaximumHeight(150)
        self.main.addWidget(self.alert_log)

    # =====================================
    # NETWORK
    # =====================================

    def connect_server(self):
        if self.connection:
            return

        try:
            self.connection = socket.create_connection(
                (HOST, PORT), timeout=2
            )
            self.connection.setblocking(False)
            self.buffer = b""

            self.send_message({
                "type": "JOIN",
                "role": "onboard_commander"
            })

            self.add_alert("Connecting to mission server...")

        except OSError as error:
            self.connection = None
            self.add_alert(f"Connection failed: {error}")

    def send_message(self, data):
        if not self.connection:
            self.add_alert("Server is disconnected.")
            return False

        try:
            packet = json.dumps(
                data, ensure_ascii=False
            ).encode("utf-8") + b"\n"

            self.connection.sendall(packet)
            return True

        except OSError:
            self.disconnect_server()
            return False

    def poll_server(self):
        if not self.connection:
            return

        try:
            while True:
                try:
                    chunk = self.connection.recv(4096)
                except BlockingIOError:
                    break

                if not chunk:
                    self.disconnect_server()
                    return

                self.buffer += chunk

            while b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)

                if line.strip():
                    message = json.loads(line.decode("utf-8"))
                    self.handle_message(message)

        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.add_alert(f"Network error: {error}")
            self.disconnect_server()

    # =====================================
    # SERVER MESSAGES
    # =====================================

    def handle_message(self, message):
        kind = message.get("type")

        if kind == "WELCOME":
            self.connection_label.setText("● CONNECTED")
            self.connection_label.setStyleSheet(
                "color:#42d6a0; font-weight:900;"
            )
            self.mission_status.setText("● MISSION ONLINE")
            self.mission_status.setStyleSheet(
                "color:#42d6a0; font-weight:900;"
            )
            self.add_alert("Connected to Mission Control network.")

        elif kind == "TELEMETRY":
            self.update_telemetry(message.get("data", {}))

        elif kind == "ORDER":
            self.set_order(message.get("data", {}))

        elif kind == "ACTION_RESULT":
            self.add_alert(message.get("message", "Action completed."))
            self.clear_order()

        elif kind == "ALERT":
            self.add_alert(message.get("message", "Unknown alert"))

        elif kind == "CHAT":
            sender = message.get("from", message.get("sender", "MISSION CONTROL"))
            text = message.get("text", message.get("message", ""))
            self.log_chat(f"{sender}: {text}")

        elif kind == "PROPOSAL_SENT":
            self.add_alert("Proposal successfully delivered.")

        elif kind == "PROPOSAL_RESPONSE":
            self.add_alert(message.get("message", "Proposal reviewed."))

        elif kind == "GAME_OVER":
            self.game_over = True
            reason = message.get("reason", "Mission failed.")

            self.mission_status.setText("● MISSION FAILED")
            self.mission_status.setStyleSheet(
                "color:#ff6577; font-weight:900;"
            )

            self.execute_button.setEnabled(False)
            self.add_alert("GAME OVER: " + reason)

            QMessageBox.critical(self, "MISSION FAILED", reason)

        elif kind == "PLAYER_JOINED":
            self.add_alert(
                message.get("role", "Player") + " connected."
            )

        elif kind == "PLAYER_LEFT":
            self.add_alert(
                message.get("role", "Player") + " disconnected."
            )

        elif kind == "ERROR":
            self.add_alert(
                "SERVER ERROR: " + message.get("message", "")
            )

    # =====================================
    # TELEMETRY UPDATES
    # =====================================

    def update_telemetry(self, data):
        for key, (value_label, state_label, unit) in self.metric_values.items():
            if key not in data:
                continue

            value = data[key]
            value_label.setText(f"{value}{unit}")

            if key == "temperature":
                critical = value <= 0 or value >= 50
                warning = value <= 5 or value >= 35
            else:
                critical = value <= 25
                warning = value <= 50

            if critical:
                state = "CRITICAL"
                color = "#ff6577"
            elif warning:
                state = "WARNING"
                color = "#f0b45c"
            else:
                state = "NOMINAL"
                color = "#42d6a0"

            state_label.setText(state)
            state_label.setStyleSheet(
                f"color:{color}; font-weight:800;"
            )

        modules = data.get("modules", {})

        for module, label in self.module_labels.items():
            status = modules.get(module, "UNKNOWN")

            colors = {
                "ONLINE": "#42d6a0",
                "DAMAGED": "#f0b45c",
                "OFFLINE": "#ff6577"
            }

            label.setText("● " + status)
            label.setStyleSheet(
                f"color:{colors.get(status, '#8ba0ba')};"
                "font-weight:800;"
            )

        # Crew biometrics are accepted only on this interface.
        crew = data.get("crew", {})

        if isinstance(crew, dict):
            self.update_crew_status(crew)

    # =====================================
    # ORDERS
    # =====================================

    def set_order(self, order):
        if self.game_over:
            return

        self.pending_order = order

        module = order.get("module", "unknown module")
        action = order.get("action", "ACTION")

        self.order_status.setText("● NEW ORDER RECEIVED")
        self.order_status.setStyleSheet(
            "color:#f0b45c; font-weight:900;"
        )

        self.order_text.setText(
            f"{action}\nTarget: {module}"
        )

        self.execute_button.setEnabled(True)
        self.add_alert("New order received from Mission Control.")

    def execute_order(self):
        if not self.pending_order or self.game_over:
            return

        order_id = self.pending_order.get("order_id")

        payload = {"type": "EXECUTE_ORDER"}

        if order_id:
            payload["order_id"] = order_id

        if self.send_message(payload):
            self.execute_button.setEnabled(False)
            self.order_status.setText("● EXECUTION REQUEST SENT")

    def clear_order(self):
        self.pending_order = None
        self.order_status.setText("NO ACTIVE ORDERS")
        self.order_text.setText(
            "Waiting for instructions from Mission Control."
        )
        self.execute_button.setEnabled(False)

    # =====================================
    # CHAT AND ALERTS
    # =====================================

    def send_chat(self):
        text = self.chat_input.text().strip()

        if not text:
            return

        if self.send_message({
            "type": "CHAT",
            "text": text
        }):
            self.log_chat("YOU: " + text)
            self.chat_input.clear()

    def log_chat(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.chat_log.appendPlainText(f"[{stamp}] {text}")

    def add_alert(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.alert_log.appendPlainText(f"[{stamp}] {text}")

    # =====================================
    # DISCONNECT
    # =====================================

    def disconnect_server(self):
        if self.connection:
            try:
                self.connection.close()
            except OSError:
                pass

        self.connection = None
        self.connection_label.setText("● DISCONNECTED")
        self.connection_label.setStyleSheet(
            "color:#ff6577; font-weight:900;"
        )

    def closeEvent(self, event):
        if self.connection:
            self.connection.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CrewInterface()
    window.show()
    sys.exit(app.exec_())
