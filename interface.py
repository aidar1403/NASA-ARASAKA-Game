import sys
import socket
import json
import math

from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import (
    QPen,
    QBrush,
    QColor,
    QPolygonF,
    QPainter
)
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QPlainTextEdit,
    QGraphicsView,
    QGraphicsScene,
    QComboBox,
    QDialog,
    QRadioButton,
    QButtonGroup
)


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


class OrbitTrackApp(QMainWindow):
    def animate_flight(self):
        self.flight_phase += 1

        for star in self.animated_stars:
            star.moveBy(-1.5, 0)

            if star.pos().x() < -5:
                star.setPos(800, star.pos().y())

        # 2. Пульсация двигателей
        pulse = (math.sin(self.flight_phase / 4) + 1) / 2

        flame_length = 30 + pulse * 25
        flame_alpha = int(150 + pulse * 105)

        self.engine_flame_outer.setPolygon(
            QPolygonF([
                QPointF(615, 165),
                QPointF(615 + flame_length, 180),
                QPointF(615, 195)
            ])
        )

        self.engine_flame_inner.setPolygon(
            QPolygonF([
                QPointF(615, 173),
                QPointF(615 + flame_length * 0.6, 180),
                QPointF(615, 187)
            ])
        )

        self.engine_flame_outer.setBrush(
            QBrush(QColor(255, 100, 25, flame_alpha))
        )

        if self.impact_flash_opacity > 0:
            self.impact_flash_opacity = max(
                0,
                self.impact_flash_opacity - 0.045
            )

            self.impact_overlay.setOpacity(
                self.impact_flash_opacity
            )

    def trigger_impact_effect(self):
        self.impact_flash_opacity = 0.65
        self.impact_overlay.setOpacity(
            self.impact_flash_opacity
        )

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NASA ARASAKA - Mission Control")
        self.setMinimumSize(1200, 750)
        self.resize(1450, 900)

        # Network
        self.connection = None
        self.receive_buffer = b""

        # Telemetry
        self.telemetry_labels = {}
        self.telemetry_descriptions = {}

        # Ship systems
        self.ship_parts = {}
        self.module_labels = {}
        self.module_statuses = {}

        # Emergency animation
        self.warning_active = False
        self.blink_on = False
        self.active_scenario = None
        self.simulated_telemetry = {
            "oxygen": 100, "energy": 100,
            "hull_integrity": 100, "temperature": 22
        }
        self.scenario_resolved = False

        self.setStyleSheet(self.get_stylesheet())

        self.create_interface()

        # Network polling
        self.network_timer = QTimer(self)
        self.network_timer.timeout.connect(self.poll_server)
        self.network_timer.start(50)

        # Emergency blinking
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.update_blink)
        self.blink_timer.start(500)

        # Flight animation
        self.flight_phase = 0
        self.impact_flash_opacity = 0

        self.flight_timer = QTimer(self)
        self.flight_timer.timeout.connect(self.animate_flight)
        self.flight_timer.start(50)

        self.connect_to_server()


    def create_interface(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.create_sidebar())
        main_layout.addWidget(self.create_main_content(), 1)

    # ==========================================
    # SIDEBAR
    # ==========================================

    def create_sidebar(self):

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(10)

        logo = QLabel("✦ NASA ARASAKA")
        logo.setObjectName("logo")
        layout.addWidget(logo)

        subtitle = QLabel("MISSION CONTROL")
        subtitle.setObjectName("sidebarSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(25)

        buttons = [
            ("◈", "Dashboard"),
            ("▣", "Ship Systems"),
            ("◎", "Crew Status"),
            ("⌁", "Live Mission"),
            ("◉", "Communication"),
            ("⚡", "Emergency Alerts"),
            ("≡", "Mission Log")
        ]

        for index, (icon, name) in enumerate(buttons):

            button = QPushButton(f"{icon}    {name}")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(46)

            if index == 0:
                button.setObjectName("activeNav")
            else:
                button.setObjectName("navButton")

            layout.addWidget(button)

        layout.addStretch()

        self.connection_label = QLabel("● SERVER DISCONNECTED")
        self.connection_label.setObjectName("connectionStatus")
        layout.addWidget(self.connection_label)

        self.reconnect_button = QPushButton("Reconnect to server")
        self.reconnect_button.setObjectName("reconnectButton")
        self.reconnect_button.clicked.connect(self.connect_to_server)
        layout.addWidget(self.reconnect_button)

        version = QLabel("NASA ARASAKA v0.3")
        version.setObjectName("versionLabel")
        layout.addWidget(version)

        return sidebar

    # ==========================================
    # MAIN CONTENT
    # ==========================================

    def create_main_content(self):

        content = QWidget()
        layout = QVBoxLayout(content)

        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()

        title = QLabel("Mission Control")
        title.setObjectName("pageTitle")

        self.mission_status = QLabel("● WAITING FOR CONNECTION")
        self.mission_status.setObjectName("missionStatus")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.mission_status)

        layout.addLayout(header)

        welcome = QLabel(
            "Welcome, Commander. Monitor your spacecraft and respond to emergencies."
        )
        welcome.setObjectName("welcomeText")
        layout.addWidget(welcome)

        # Telemetry cards
        telemetry_layout = QHBoxLayout()
        telemetry_layout.setSpacing(12)

        telemetry_data = [
            ("OXYGEN", "oxygen", "%"),
            ("ENERGY", "energy", "%"),
            ("HULL INTEGRITY", "hull_integrity", "%"),
            ("TEMPERATURE", "temperature", "°C")
        ]

        for name, key, unit in telemetry_data:
            telemetry_layout.addWidget(
                self.create_telemetry_card(name, key, unit)
            )

        layout.addLayout(telemetry_layout)

        # Mission view
        mission_frame = QFrame()
        mission_frame.setObjectName("missionFrame")

        mission_layout = QVBoxLayout(mission_frame)
        mission_layout.setContentsMargins(16, 14, 16, 14)
        mission_layout.setSpacing(10)

        mission_title = QLabel("LIVE SPACECRAFT BLUEPRINT")
        mission_title.setObjectName("sectionTitle")
        mission_layout.addWidget(mission_title)

        # Warning banner
        self.warning_banner = QLabel(
            "⚠ SPACECRAFT DAMAGE DETECTED"
        )
        self.warning_banner.setObjectName("warningBanner")
        self.warning_banner.setAlignment(Qt.AlignCenter)
        self.warning_banner.hide()

        mission_layout.addWidget(self.warning_banner)

        # Blueprint
        self.ship_scene = QGraphicsScene(self)

        self.ship_view = QGraphicsView(self.ship_scene)
        self.ship_view.setObjectName("shipView")
        self.ship_view.setRenderHint(QPainter.Antialiasing)
        self.ship_view.setSceneRect(0, 0, 650, 340)
        self.ship_view.setMinimumHeight(300)

        mission_layout.addWidget(self.ship_view, 1)

        self.create_ship_blueprint()

        # Systems
        systems_title = QLabel("SPACECRAFT SYSTEMS")
        systems_title.setObjectName("sectionTitle")
        mission_layout.addWidget(systems_title)

        modules_layout = QHBoxLayout()
        modules_layout.setSpacing(10)

        modules = [
            ("life_support", "LIFE SUPPORT"),
            ("engine", "ENGINE"),
            ("navigation", "NAVIGATION"),
            ("communications", "COMMUNICATIONS")
        ]

        for module_id, module_name in modules:

            card = QFrame()
            card.setObjectName("moduleCard")

            card_layout = QVBoxLayout(card)

            name_label = QLabel(module_name)
            name_label.setObjectName("moduleName")
            name_label.setAlignment(Qt.AlignCenter)

            status_label = QLabel("● WAITING")
            status_label.setObjectName("moduleStatus")
            status_label.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(name_label)
            card_layout.addWidget(status_label)

            modules_layout.addWidget(card)

            self.module_labels[module_id] = status_label

        mission_layout.addLayout(modules_layout)

        layout.addWidget(mission_frame, 1)

        # Educational emergency scenarios (works offline)
        scenario_row = QHBoxLayout()
        scenario_row.setSpacing(8)

        self.scenario_selector = QComboBox()
        self.scenario_selector.addItems([
            "1. Earth orbit — Radiation belt",
            "2. Deep space — Solar flare / communication",
            "3. Deep space — Solar particle storm",
            "4. Moon approach — CME / landing"
        ])
        self.scenario_selector.setMinimumHeight(40)
        self.scenario_selector.setObjectName("scenarioSelector")

        self.load_scenario_button = QPushButton("LOAD SCENARIO")
        self.load_scenario_button.setObjectName("scenarioButton")
        self.load_scenario_button.setMinimumHeight(40)
        self.load_scenario_button.clicked.connect(self.load_selected_scenario)

        scenario_row.addWidget(self.scenario_selector, 1)
        scenario_row.addWidget(self.load_scenario_button)
        layout.addLayout(scenario_row)

        # Emergency controls
        self.collision_button = QPushButton(
            "⚠  SIMULATE ASTEROID COLLISION"
        )
        self.collision_button.setObjectName("dangerButton")
        self.collision_button.setMinimumHeight(50)
        self.collision_button.setCursor(Qt.PointingHandCursor)
        self.collision_button.clicked.connect(self.trigger_collision)

        layout.addWidget(self.collision_button)

        # Mission log
        log_title = QLabel("MISSION LOG")
        log_title.setObjectName("sectionTitle")
        layout.addWidget(log_title)

        self.mission_log = QPlainTextEdit()
        self.mission_log.setObjectName("missionLog")
        self.mission_log.setReadOnly(True)
        self.mission_log.setMaximumHeight(95)

        layout.addWidget(self.mission_log)

        return content

    # ==========================================
    # TELEMETRY CARDS
    # ==========================================

    def create_telemetry_card(self, name, key, unit):

        card = QFrame()
        card.setObjectName("telemetryCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        name_label = QLabel(name)
        name_label.setObjectName("telemetryName")

        value_label = QLabel("--")
        value_label.setObjectName("telemetryValue")

        description_label = QLabel("Waiting for data")
        description_label.setObjectName("telemetryDescription")

        layout.addWidget(name_label)
        layout.addWidget(value_label)
        layout.addWidget(description_label)

        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        self.telemetry_labels[key] = (value_label, unit)
        self.telemetry_descriptions[key] = description_label

        return card

    # ==========================================
    # SPACECRAFT BLUEPRINT
    # ==========================================

    def create_ship_blueprint(self):
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, 800, 420)

        self.ship_view.setScene(self.scene)
        self.ship_view.setRenderHint(QPainter.Antialiasing)

        # Цвета чертежа
        cyan = QColor("#35D9F5")
        dark_cyan = QColor("#147C9A")
        blue = QColor("#123B55")
        light_blue = QColor("#1A526D")
        white = QColor("#BCEFFF")

        main_pen = QPen(cyan, 2)
        detail_pen = QPen(dark_cyan, 1)
        glass_brush = QBrush(QColor("#55CBEA"))

        # Космический фон: звёзды и координатная сетка
        for x in range(0, 800, 40):
            self.scene.addLine(x, 0, x, 420, QPen(QColor("#102B40"), 1))

        for y in range(0, 420, 40):
            self.scene.addLine(0, y, 800, y, QPen(QColor("#102B40"), 1))

        self.animated_stars = []

        stars = [
            (50, 55), (120, 90), (220, 45), (310, 330),
            (420, 75), (530, 350), (680, 55), (750, 280),
            (90, 350), (720, 100), (390, 380), (600, 40)
        ]

        for x, y in stars:
            star = self.scene.addEllipse(
                0, 0, 2, 2,
                QPen(Qt.NoPen),
                QBrush(QColor("#BCEFFF"))
            )
            star.setPos(x, y)
            self.animated_stars.append(star)
        # -----------------------------
        # СОЛНЕЧНЫЕ ПАНЕЛИ
        # -----------------------------

        # Верхняя опора
        self.solar_array_items = []
        self.scene.addLine(300, 140, 300, 100, detail_pen)
        self.scene.addLine(450, 140, 450, 100, detail_pen)

        # Верхняя панель
        top_solar_panel = self.scene.addRect(
            230, 65, 300, 35,
            main_pen,
            QBrush(QColor("#0C3048"))
        )
        self.solar_array_items.append(top_solar_panel)

        for x in range(245, 530, 30):
            self.scene.addLine(x, 65, x, 100, detail_pen)

        self.scene.addLine(230, 82, 530, 82, detail_pen)

        # Нижняя опора
        self.scene.addLine(300, 220, 300, 260, detail_pen)
        self.scene.addLine(450, 220, 450, 260, detail_pen)

        # Нижняя панель
        bottom_solar_panel = self.scene.addRect(
            230, 260, 300, 35,
            main_pen,
            QBrush(QColor("#0C3048"))
        )
        self.solar_array_items.append(bottom_solar_panel)

        for x in range(245, 530, 30):
            self.scene.addLine(x, 260, x, 295, detail_pen)

        self.scene.addLine(230, 277, 530, 277, detail_pen)

        # -----------------------------
        # КОРПУС РАКЕТЫ
        # -----------------------------

        self.ship_parts = {}

        # Носовой обтекатель — NAVIGATION
        navigation = self.scene.addPolygon(
            QPolygonF([
                QPointF(85, 180),
                QPointF(175, 140),
                QPointF(175, 220)
            ]),
            main_pen,
            QBrush(blue)
        )

        self.ship_parts["navigation"] = navigation

        # Основной жилой модуль — LIFE SUPPORT
        life_support = self.scene.addPolygon(
            QPolygonF([
                QPointF(175, 140),
                QPointF(355, 140),
                QPointF(355, 220),
                QPointF(175, 220)
            ]),
            main_pen,
            QBrush(light_blue)
        )

        self.ship_parts["life_support"] = life_support

        # Командный и коммуникационный модуль
        communications = self.scene.addPolygon(
            QPolygonF([
                QPointF(355, 140),
                QPointF(475, 140),
                QPointF(475, 220),
                QPointF(355, 220)
            ]),
            main_pen,
            QBrush(blue)
        )

        self.ship_parts["communications"] = communications

        # Двигательный отсек
        engine = self.scene.addPolygon(
            QPolygonF([
                QPointF(475, 140),
                QPointF(565, 155),
                QPointF(565, 205),
                QPointF(475, 220)
            ]),
            main_pen,
            QBrush(light_blue)
        )

        self.ship_parts["engine"] = engine

        # -----------------------------
        # ИЛЛЮМИНАТОРЫ
        # -----------------------------

        for x in [200, 230, 260, 290, 320]:
            self.scene.addEllipse(
                x, 165, 17, 17,
                detail_pen,
                glass_brush
            )

        for x in [380, 410, 440]:
            self.scene.addEllipse(
                x, 165, 17, 17,
                detail_pen,
                glass_brush
            )

        # -----------------------------
        # АНТЕННА
        # -----------------------------

        self.scene.addLine(415, 140, 415, 115, main_pen)
        self.scene.addEllipse(
            407, 105, 16, 10,
            main_pen,
            QBrush(QColor("#0B2438"))
        )

        self.scene.addLine(415, 115, 435, 105, detail_pen)
        self.scene.addLine(415, 115, 395, 105, detail_pen)

        # -----------------------------
        # ДВИГАТЕЛИ
        # -----------------------------

        # Верхнее сопло
        self.scene.addPolygon(
            QPolygonF([
                QPointF(565, 155),
                QPointF(615, 165),
                QPointF(615, 180),
                QPointF(565, 180)
            ]),
            main_pen,
            QBrush(QColor("#234D63"))
        )

        # Нижнее сопло
        self.scene.addPolygon(
            QPolygonF([
                QPointF(565, 180),
                QPointF(615, 180),
                QPointF(615, 195),
                QPointF(565, 205)
            ]),
            main_pen,
            QBrush(QColor("#234D63"))
        )

        # Внутренние детали двигателей
        self.scene.addLine(585, 165, 585, 195, detail_pen)
        self.scene.addLine(600, 168, 600, 192, detail_pen)

        # Внешнее пламя двигателя
        self.engine_flame_outer = self.scene.addPolygon(
            QPolygonF([
                QPointF(615, 165),
                QPointF(655, 180),
                QPointF(615, 195)
            ]),
            QPen(QColor("#FF9D42"), 1),
            QBrush(QColor("#FF7B24"))
        )

        # Внутреннее свечение
        self.engine_flame_inner = self.scene.addPolygon(
            QPolygonF([
                QPointF(615, 173),
                QPointF(640, 180),
                QPointF(615, 187)
            ]),
            QPen(Qt.NoPen),
            QBrush(QColor("#FFE58A"))
        )

        # Вспышка при столкновении
        self.impact_overlay = self.scene.addRect(
            0, 0, 800, 420,
            QPen(Qt.NoPen),
            QBrush(QColor(255, 30, 30, 110))
        )

        self.impact_overlay.setZValue(100)
        self.impact_overlay.setOpacity(0)

        # -----------------------------
        # СИСТЕМА НАВИГАЦИИ
        # -----------------------------

        self.scene.addLine(115, 180, 145, 180, detail_pen)
        self.scene.addLine(145, 180, 165, 160, detail_pen)
        self.scene.addLine(145, 180, 165, 200, detail_pen)

        # Небольшие внешние стабилизаторы
        self.scene.addPolygon(
            QPolygonF([
                QPointF(280, 140),
                QPointF(320, 115),
                QPointF(350, 140)
            ]),
            detail_pen,
            QBrush(QColor("#123B55"))
        )

        self.scene.addPolygon(
            QPolygonF([
                QPointF(280, 220),
                QPointF(320, 245),
                QPointF(350, 220)
            ]),
            detail_pen,
            QBrush(QColor("#123B55"))
        )

        # -----------------------------
        # ПОДПИСИ МОДУЛЕЙ
        # -----------------------------

        labels = [
            ("NAVIGATION", 90, 235),
            ("LIFE SUPPORT", 205, 235),
            ("COMMUNICATION", 355, 235),
            ("ENGINE", 495, 235)
        ]

        for text, x, y in labels:
            label = self.scene.addText(text)
            label.setDefaultTextColor(cyan)
            label.setPos(x, y)

        # Направление движения
        direction = self.scene.addText("FLIGHT DIRECTION  >>>")
        direction.setDefaultTextColor(QColor("#4B91A8"))
        direction.setPos(560, 330)

        # Начальные статусы
        self.module_statuses = {
            "navigation": "ONLINE",
            "life_support": "ONLINE",
            "communications": "ONLINE",
            "engine": "ONLINE"
        }

    # ==========================================
    # EDUCATIONAL EMERGENCY SCENARIOS
    # ==========================================

    def scenario_data(self):
        return [
            {
                "title": "RADIATION BELT ALERT",
                "alert": "⚠ WARNING: The spacecraft is entering a Radiation Belt Enhancement (RBE) region in the Van Allen belts. Energetic electron flux is elevated. Choose a protection protocol!",
                "terms": {
                    "Radiation Belt Enhancement (RBE)": (
                        "Radiation Belt Enhancement (RBE)",
                        "Earth is surrounded by invisible regions where its magnetic field traps energetic particles. During an enhancement, the number of energetic particles in a belt rises. Too much radiation can affect spacecraft electronics and, depending on the orbit and shielding, crew safety.",
                        "NASA DONKI recorded an RBE beginning 2 January 2016 at 12:25 UTC. GOES-13 (SEM/EPS) measured electrons above 0.8 MeV. DONKI links the event to a CME observed on 28 December 2015. Event ID: 2016-01-02T12:25:00-RBE-001.",
                        "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/RBE/9969/2"
                    ),
                    "Van Allen belts": (
                        "Van Allen radiation belts",
                        "Imagine two giant invisible rings around Earth. Earth's magnetic field traps some fast particles there. A spacecraft passing through these regions may need extra shielding and a carefully planned route.",
                        "The RBE event in NASA DONKI on 2 January 2016 was observed in Earth's outer radiation belt by GOES-13.",
                        "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/RBE/9969/2"
                    )
                },
                "action": "PROTECTION PROTOCOL: Move the crew to the best-shielded compartment, reduce non-essential activity, and monitor radiation readings.",
                "source": "NASA CCMC DONKI — RBE event 2016-01-02T12:25:00-RBE-001"
            },
            {
                "title": "COMMUNICATIONS ALERT",
                "alert": "⚠ COMMUNICATIONS ALERT: A powerful solar flare (FLR) has been detected. Increased ionization may disturb radio links. Earth Telemetry is intermittent. Choose a backup communication method!",
                "terms": {
                    "Solar flare (FLR)": (
                        "Solar flare (FLR)",
                        "A solar flare is a sudden, powerful burst of light and energy from the Sun. Its radiation can disturb Earth's upper atmosphere and make some radio signals harder to receive.",
                        "NASA's DONKI database catalogs solar flares by their start time and class (including M and X classes). This game scenario is a training simulation, not a claim that one particular January 2016 flare caused this exact onboard failure.",
                        "https://api.nasa.gov/DONKI/FLR?startDate=2016-01-01&endDate=2016-01-31&api_key=DEMO_KEY"
                    ),
                    "Ionization": (
                        "Ionization",
                        "When strong energy knocks electrons away from atoms, the air or gas becomes full of charged particles. In Earth's upper atmosphere, this can change how radio waves travel and sometimes disrupt radio communication.",
                        "NASA DONKI provides historical solar-flare records. The radio disruption shown here is a simplified educational simulation of possible space-weather effects.",
                        "https://api.nasa.gov/DONKI/FLR?startDate=2016-01-01&endDate=2016-01-31&api_key=DEMO_KEY"
                    ),
                    "Telemetry": (
                        "Telemetry",
                        "Telemetry is the stream of information a spacecraft sends to Mission Control: oxygen level, battery power, temperature, position, and equipment status. It is like the ship sending its health report.",
                        "Telemetry is a standard spacecraft operations concept. In this prototype, the displayed values are generated by the game simulation.",
                        "https://www.nasa.gov/"
                    )
                },
                "action": "BACKUP LINK: Switch to the backup antenna, reduce non-essential transmissions, and continue logging onboard measurements until the link is stable.",
                "source": "NASA CCMC DONKI — Solar Flare (FLR) catalog"
            },
            {
                "title": "SOLAR PARTICLE EVENT",
                "alert": "⚠ RADIATION WARNING: A stream of Solar Energetic Particles (SEP) is approaching. Dosimeters show a rising absorbed dose estimate. Crew, move to the storm shelter!",
                "terms": {
                    "Solar Energetic Particles (SEP)": (
                        "Solar Energetic Particles (SEP)",
                        "During some solar eruptions, tiny particles—especially protons—are accelerated to very high speeds and travel through space. A strong particle event can increase radiation exposure for astronauts and spacecraft.",
                        "NASA DONKI maintains a historical catalog of Solar Energetic Particle events. The rising crew exposure and shelter procedure in this mission are simulated training values, not a measurement from a real crew in January 2016.",
                        "https://api.nasa.gov/DONKI/SEP?startDate=2016-01-01&endDate=2016-01-31&api_key=DEMO_KEY"
                    ),
                    "Absorbed dose": (
                        "Absorbed dose",
                        "Absorbed dose tells us how much radiation energy is deposited in a material or body. It is measured in grays (Gy). For people, scientists also consider the type of radiation and which body parts are exposed.",
                        "Radiation exposure limits and astronaut risk assessments are studied by NASA's Human Research Program. The dose values in this game are illustrative, not medical advice or real crew measurements.",
                        "https://www.nasa.gov/hrp/"
                    ),
                    "Dosimeter": (
                        "Dosimeter",
                        "A dosimeter is a small device that measures or estimates how much radiation a person has received. It works like a radiation warning counter.",
                        "Space radiation monitoring is part of astronaut safety research. This scenario uses a simplified simulated reading.",
                        "https://www.nasa.gov/hrp/"
                    )
                },
                "action": "CREW SAFETY: Move everyone into the most shielded area, place water and supplies around the shelter where possible, and keep monitoring exposure.",
                "source": "NASA CCMC DONKI — Solar Energetic Particle (SEP) catalog; NASA Human Research Program"
            },
            {
                "title": "LUNAR APPROACH — POWER ALERT",
                "alert": "⚠ CRITICAL POWER ALERT: A Coronal Mass Ejection (CME) has been detected. The spacecraft's power system is unstable. Prepare for lunar approach and select a safe landing zone near Shackleton crater!",
                "terms": {
                    "Coronal Mass Ejection (CME)": (
                        "Coronal Mass Ejection (CME)",
                        "A CME is a huge cloud of charged gas (plasma) launched from the Sun. If it reaches a spacecraft or Earth, it can disturb magnetic and electrical systems. The actual danger depends on the event and the spacecraft's protection.",
                        "NASA DONKI catalogs CME events and their measured or estimated properties. The power-system failure in this mission is a simulated consequence, not a claim that a specific CME damaged a real spacecraft.",
                        "https://api.nasa.gov/DONKI/CME?startDate=2017-01-01&endDate=2017-01-07&api_key=DEMO_KEY"
                    ),
                    "Shackleton crater": (
                        "Shackleton crater",
                        "Shackleton is a crater near the Moon's south pole. Some places around its rim receive sunlight for long periods, while parts of its deep interior remain in shadow. Scientists study permanently shadowed areas because they may contain water ice.",
                        "NASA's Lunar Reconnaissance Orbiter (LRO) has mapped the lunar south polar region, including Shackleton crater. The landing-site choice in this game is a simplified mission-planning exercise.",
                        "https://science.nasa.gov/moon/"
                    )
                },
                "action": "POWER-SAVING LANDING: Shut down non-essential systems, preserve reserve power, and choose a landing site with a clear approach and reliable sunlight for later power generation.",
                "source": "NASA CCMC DONKI — CME catalog; NASA Lunar Reconnaissance Orbiter (LRO)"
            }
        ]

    def scenario_profiles(self):
        """Illustrative game-balance values; not real spacecraft engineering data."""
        return {
            "RADIATION BELT ALERT": {
                "initial": {"oxygen": -20, "energy": -8, "hull_integrity": -3, "temperature": 2},
                "modules": {"life_support": "DAMAGED"},
                "choices": [
                    {"text": "Move the crew to the shielded compartment and monitor radiation.",
                     "delta": {"oxygen": 4, "energy": -12, "hull_integrity": 0, "temperature": -1},
                     "modules": {"life_support": "DAMAGED"},
                     "outcome": "The crew reached the shielded compartment. Radiation exposure is reduced, but the shelter systems consume reserve power."},
                    {"text": "Turn off the oxygen system to save power.",
                     "delta": {"oxygen": -18, "energy": 8, "hull_integrity": 0, "temperature": 1},
                     "modules": {"life_support": "OFFLINE"},
                     "outcome": "Power was conserved, but shutting down life support caused a dangerous oxygen drop. The crew remains at risk."},
                    {"text": "Open the outer airlock to release the radiation.",
                     "delta": {"oxygen": -25, "energy": -5, "hull_integrity": -8, "temperature": 2},
                     "modules": {"life_support": "OFFLINE", "navigation": "DAMAGED"},
                     "outcome": "Opening the airlock did not remove the radiation threat. The cabin lost pressure and the hull was further compromised."}
                ]
            },
            "COMMUNICATIONS ALERT": {
                "initial": {"oxygen": 0, "energy": -12, "hull_integrity": -4, "temperature": 3},
                "modules": {"communications": "DAMAGED"},
                "choices": [
                    {"text": "Switch to the backup antenna and keep recording onboard telemetry.",
                     "delta": {"oxygen": 0, "energy": -8, "hull_integrity": 0, "temperature": -1},
                     "modules": {"communications": "ONLINE"},
                     "outcome": "The backup antenna restored a stable link. Mission Control can receive telemetry again, but the antenna repair used reserve power."},
                    {"text": "Shut down all navigation instruments.",
                     "delta": {"oxygen": 0, "energy": 5, "hull_integrity": 0, "temperature": 1},
                     "modules": {"navigation": "OFFLINE", "communications": "DAMAGED"},
                     "outcome": "Some power was saved, but navigation instruments went offline. The spacecraft can no longer safely verify its route."},
                    {"text": "Ignore the lost signal and continue without status checks.",
                     "delta": {"oxygen": -3, "energy": -10, "hull_integrity": -8, "temperature": 3},
                     "modules": {"communications": "OFFLINE"},
                     "outcome": "The crew continued without telemetry. A secondary fault went unnoticed and damaged additional systems."}
                ]
            },
            "SOLAR PARTICLE EVENT": {
                "initial": {"oxygen": -10, "energy": -10, "hull_integrity": -2, "temperature": 5},
                "modules": {"life_support": "DAMAGED"},
                "choices": [
                    {"text": "Move the crew to the most shielded area and monitor exposure.",
                     "delta": {"oxygen": -2, "energy": -8, "hull_integrity": 0, "temperature": -2},
                     "modules": {"life_support": "DAMAGED"},
                     "outcome": "The crew entered the storm shelter and exposure risk decreased. Life-support reserves were used to maintain the shelter."},
                    {"text": "Send the crew outside to inspect the hull.",
                     "delta": {"oxygen": -8, "energy": -5, "hull_integrity": -10, "temperature": 2},
                     "modules": {"life_support": "DAMAGED", "navigation": "DAMAGED"},
                     "outcome": "The crew was exposed during the particle event. The inspection did not solve the problem and the hull suffered additional damage."},
                    {"text": "Turn off all radiation sensors.",
                     "delta": {"oxygen": -5, "energy": 3, "hull_integrity": 0, "temperature": 2},
                     "modules": {"communications": "DAMAGED"},
                     "outcome": "The warning instruments stopped reporting. Power was saved, but the crew lost the information needed to track radiation exposure."}
                ]
            },
            "LUNAR APPROACH — POWER ALERT": {
                "initial": {"oxygen": 0, "energy": -25, "hull_integrity": -5, "temperature": 3},
                "modules": {"engine": "DAMAGED"},
                "choices": [
                    {"text": "Save reserve power, disable non-essential systems, and assess the landing site.",
                     "delta": {"oxygen": 0, "energy": 8, "hull_integrity": 0, "temperature": -1},
                     "modules": {"engine": "DAMAGED", "navigation": "ONLINE"},
                     "outcome": "The crew preserved reserve power and completed a safer landing-site assessment. The engine remains damaged, so the next maneuver will be limited."},
                    {"text": "Use all remaining power on non-essential systems.",
                     "delta": {"oxygen": 0, "energy": -20, "hull_integrity": 0, "temperature": 2},
                     "modules": {"engine": "DAMAGED", "navigation": "DAMAGED"},
                     "outcome": "Non-essential systems consumed the remaining reserve. Navigation checks are now unreliable and the landing window is at risk."},
                    {"text": "Land immediately without checking the approach.",
                     "delta": {"oxygen": -2, "energy": -12, "hull_integrity": -15, "temperature": 4},
                     "modules": {"engine": "OFFLINE", "navigation": "OFFLINE"},
                     "outcome": "The rushed landing caused a hard impact. The engine and navigation systems went offline, leaving the spacecraft stranded."}
                ]
            }
        }

    def apply_simulated_state(self):
        """Refresh telemetry and make damaged spacecraft sections visibly fade."""
        self.update_telemetry(self.simulated_telemetry)
        for module_id, part in self.ship_parts.items():
            status = self.module_statuses.get(module_id, "ONLINE")
            if status == "OFFLINE":
                part.setOpacity(0.18)
                part.setBrush(QBrush(QColor("#111827")))
                part.setPen(QPen(QColor("#536174"), 2))
            elif status == "DAMAGED":
                part.setOpacity(0.55)
                part.setBrush(QBrush(QColor("#4B2930")))
                part.setPen(QPen(QColor("#FF765F"), 3))
            else:
                part.setOpacity(1.0)
                part.setBrush(QBrush(QColor("#1A526D")))
                part.setPen(QPen(QColor("#35D9F5"), 2))
        for module_id, status_label in self.module_labels.items():
            status = self.module_statuses.get(module_id, "ONLINE")
            status_label.setText("● " + status)
            color = "#48DDA5" if status == "ONLINE" else ("#FFAA45" if status == "DAMAGED" else "#FF5555")
            status_label.setStyleSheet(f"color:{color}; font-weight:bold; font-size:13px;")

        # Low energy also dims the solar arrays and engine flame.
        energy = self.simulated_telemetry["energy"]
        array_opacity = max(0.15, energy / 100.0)
        for item in getattr(self, "solar_array_items", []):
            item.setOpacity(array_opacity)
        flame_opacity = max(0.08, energy / 100.0)
        self.engine_flame_outer.setOpacity(flame_opacity)
        self.engine_flame_inner.setOpacity(flame_opacity)
        self.warning_active = any(v in ("DAMAGED", "OFFLINE") for v in self.module_statuses.values())
        self.update_blink()

    def apply_delta(self, delta):
        for key, amount in delta.items():
            self.simulated_telemetry[key] += amount
            if key != "temperature":
                self.simulated_telemetry[key] = max(0, min(100, self.simulated_telemetry[key]))
            else:
                self.simulated_telemetry[key] = max(-20, min(80, self.simulated_telemetry[key]))

    def load_selected_scenario(self):
        index = self.scenario_selector.currentIndex()
        scenarios = self.scenario_data()
        self.active_scenario = scenarios[index]
        self.scenario_resolved = False
        self.simulated_telemetry = {"oxygen": 100, "energy": 100, "hull_integrity": 100, "temperature": 22}
        self.module_statuses = {"navigation": "ONLINE", "life_support": "ONLINE", "communications": "ONLINE", "engine": "ONLINE"}
        profile = self.scenario_profiles()[self.active_scenario["title"]]
        self.apply_delta(profile["initial"])
        self.module_statuses.update(profile["modules"])
        self.apply_simulated_state()

        self.warning_banner.setText(self.build_alert_html(self.active_scenario))
        self.warning_banner.setTextFormat(Qt.RichText)
        self.warning_banner.setTextInteractionFlags(Qt.TextBrowserInteraction)
        try:
            self.warning_banner.linkActivated.disconnect(self.show_term_card)
        except TypeError:
            pass
        self.warning_banner.linkActivated.connect(self.show_term_card)
        self.warning_banner.show()
        self.mission_status.setText("● INCIDENT IN PROGRESS — DAMAGE ASSESSED")
        self.trigger_impact_effect()
        self.add_log(f"INCIDENT: {self.active_scenario['title']}")
        self.add_log("DAMAGE REPORT: " + ", ".join(f"{k.replace('_',' ').upper()} {v:+}" for k, v in profile["initial"].items()))
        self.show_incident_dialog(self.active_scenario, profile)

    def show_incident_dialog(self, scenario, profile):
        dialog = QDialog(self)
        dialog.setWindowTitle("INCOMING INCIDENT REPORT")
        dialog.setMinimumSize(820, 570)
        dialog.resize(900, 650)
        dialog.setStyleSheet("QDialog { background:#0D192B; color:#E8F1FF; } QLabel { color:#E8F1FF; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        heading = QLabel("⚠  INCIDENT DETECTED")
        heading.setStyleSheet("font-size:28px; font-weight:900; color:#FF7777;")
        layout.addWidget(heading)
        title = QLabel(scenario["title"])
        title.setStyleSheet("font-size:21px; font-weight:bold; color:#70E8FF;")
        layout.addWidget(title)
        description = QLabel(scenario["alert"])
        description.setWordWrap(True)
        description.setStyleSheet("font-size:17px; line-height:1.4; padding:16px; background:#142943; border:1px solid #315477; border-radius:10px;")
        layout.addWidget(description)
        damage_title = QLabel("INITIAL DAMAGE — BEFORE YOUR DECISION")
        damage_title.setStyleSheet("font-size:17px; font-weight:bold; color:#FFB36B;")
        layout.addWidget(damage_title)
        damage = QLabel("\n".join(f"{k.replace('_',' ').upper()}: {v:+}" + ("%" if k != "temperature" else "°C") for k, v in profile["initial"].items()))
        damage.setStyleSheet("font-size:19px; font-weight:bold; padding:15px; background:#241D2B; border:1px solid #75404A; border-radius:10px;")
        layout.addWidget(damage)
        note = QLabel("Training simulation values — these are game mechanics, not real spacecraft telemetry.")
        note.setStyleSheet("font-size:13px; color:#A9BDD4;")
        layout.addWidget(note)
        layout.addStretch()
        button = QPushButton("READ SCIENCE BRIEFING  →")
        button.setMinimumHeight(58)
        button.setStyleSheet("font-size:18px; font-weight:bold; background:#14516A; border:1px solid #2B9BB7; border-radius:9px; padding:10px;")
        button.clicked.connect(lambda: self.begin_decision_after_briefing(dialog, scenario))
        layout.addWidget(button)
        dialog.exec_()

    def begin_decision_after_briefing(self, incident_dialog, scenario):
        incident_dialog.accept()
        first_term = next(iter(scenario["terms"]))
        self.show_term_card(first_term)
        self.show_scenario_briefing(scenario)

    def build_alert_html(self, scenario):
        html = scenario["alert"]
        for term in sorted(scenario["terms"], key=len, reverse=True):
            safe_term = term.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            link = (
                f'<a href="{term}" style="color:#70E8FF; '
                f'text-decoration:underline; font-weight:bold;">{safe_term}</a>'
            )
            html = html.replace(term, link)
        return html

    def show_term_card(self, term):
        if not self.active_scenario or term not in self.active_scenario["terms"]:
            return
        title, simple, history, source = self.active_scenario["terms"][term]
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(820, 620)
        dialog.resize(900, 680)
        dialog.setStyleSheet("QDialog { background:#0D192B; color:#E8F1FF; } QLabel { color:#E8F1FF; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        heading = QLabel(title)
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size:26px; font-weight:bold; color:#55DDF5;")
        layout.addWidget(heading)
        simple_label = QLabel("WHAT DOES IT MEAN?\n\n" + simple)
        simple_label.setWordWrap(True)
        simple_label.setStyleSheet("font-size:18px; padding:18px; background:#142943; border:1px solid #315477; border-radius:10px;")
        layout.addWidget(simple_label, 2)
        history_label = QLabel("REAL NASA DATA / HISTORICAL CONTEXT\n\n" + history)
        history_label.setWordWrap(True)
        history_label.setStyleSheet("font-size:16px; padding:18px; background:#102338; border:1px solid #29415F; border-radius:10px;")
        layout.addWidget(history_label, 2)
        source_label = QLabel(f'<a href="{source}" style="color:#70E8FF; font-size:16px;">OPEN NASA SOURCE</a>')
        source_label.setOpenExternalLinks(True)
        layout.addWidget(source_label)
        close_button = QPushButton("I UNDERSTAND — CONTINUE")
        close_button.setMinimumHeight(54)
        close_button.setStyleSheet("font-size:17px; font-weight:bold; padding:10px;")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec_()

    def show_scenario_briefing(self, scenario):
        profile = self.scenario_profiles()[scenario["title"]]
        choices = profile["choices"]
        dialog = QDialog(self)
        dialog.setWindowTitle("MISSION CONTROL — CHOOSE RESPONSE")
        dialog.setMinimumSize(850, 650)
        dialog.resize(940, 720)
        dialog.setStyleSheet("QDialog { background:#0D192B; color:#E8F1FF; } QRadioButton { padding:14px; color:#E8F1FF; font-size:17px; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("COMMAND DECISION")
        title.setStyleSheet("font-size:28px; font-weight:900; color:#70E8FF;")
        layout.addWidget(title)
        instruction = QLabel("Review the damage report. Choose one action. Every option changes the spacecraft condition.")
        instruction.setWordWrap(True)
        instruction.setStyleSheet("font-size:17px; color:#C5D5E8;")
        layout.addWidget(instruction)
        group = QButtonGroup(dialog)
        selected = {"index": 0}
        for index, choice in enumerate(choices):
            radio = QRadioButton(("RECOMMENDED  •  " if index == 0 else "") + choice["text"])
            radio.setMinimumHeight(74)
            radio.setStyleSheet("QRadioButton { background:#142943; border:1px solid #315477; border-radius:10px; padding:16px; } QRadioButton:checked { background:#123B55; border:2px solid #55DDF5; }")
            group.addButton(radio, index)
            layout.addWidget(radio)
            if index == 0:
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, i=index: selected.update(index=i) if checked else None)
        note = QLabel("All numerical changes are illustrative game-simulation values.")
        note.setStyleSheet("font-size:13px; color:#9DB1C9;")
        layout.addWidget(note)
        layout.addStretch()
        done = QPushButton("CONFIRM COMMAND")
        done.setMinimumHeight(60)
        done.setStyleSheet("font-size:19px; font-weight:bold; background:#14516A; border:1px solid #2B9BB7; border-radius:10px;")
        done.clicked.connect(lambda: self.confirm_scenario_response(dialog, scenario, choices[selected["index"]], selected["index"]))
        layout.addWidget(done)
        dialog.exec_()

    def confirm_scenario_response(self, dialog, scenario, choice, choice_index):
        self.apply_delta(choice["delta"])
        profile = self.scenario_profiles()[scenario["title"]]
        # Apply only the modules explicitly changed by the selected response.
        self.module_statuses.update(choice.get("modules", {}))
        self.apply_simulated_state()
        self.scenario_resolved = True
        self.mission_status.setText("● DECISION EXECUTED — OUTCOME GENERATED")
        self.add_log("COMMAND: " + choice["text"])
        self.add_log("OUTCOME: " + choice["outcome"])
        self.add_log("UPDATED TELEMETRY: " + ", ".join(f"{k.upper()} {v}{'°C' if k == 'temperature' else '%'}" for k, v in self.simulated_telemetry.items()))
        dialog.accept()
        self.show_outcome_card(scenario, choice, choice_index)

    def show_outcome_card(self, scenario, choice, choice_index):
        dialog = QDialog(self)
        dialog.setWindowTitle("MISSION OUTCOME")
        dialog.setMinimumSize(820, 600)
        dialog.resize(900, 680)
        dialog.setStyleSheet("QDialog { background:#0D192B; color:#E8F1FF; } QLabel { color:#E8F1FF; }")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        heading = QLabel("MISSION OUTCOME — " + ("SUCCESS WITH TRADE-OFFS" if choice_index == 0 else "CONSEQUENCES RECORDED"))
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size:25px; font-weight:900; color:" + ("#62E6B0" if choice_index == 0 else "#FFB36B") + ";")
        layout.addWidget(heading)
        explanation = QLabel(choice["outcome"])
        explanation.setWordWrap(True)
        explanation.setStyleSheet("font-size:18px; padding:18px; background:#142943; border:1px solid #315477; border-radius:10px;")
        layout.addWidget(explanation)
        changes_title = QLabel("CURRENT SPACECRAFT STATUS")
        changes_title.setStyleSheet("font-size:18px; font-weight:bold; color:#70E8FF;")
        layout.addWidget(changes_title)
        values = []
        for key, value in self.simulated_telemetry.items():
            unit = "°C" if key == "temperature" else "%"
            values.append(f"{key.replace('_',' ').upper()}:  {value}{unit}")
        stats = QLabel("     •     ".join(values))
        stats.setWordWrap(True)
        stats.setStyleSheet("font-size:17px; font-weight:bold; padding:18px; background:#102338; border-radius:10px;")
        layout.addWidget(stats)
        delta_lines = []
        for key, value in choice["delta"].items():
            unit = "°C" if key == "temperature" else "%"
            delta_lines.append(f"{key.replace('_',' ').upper()}: {value:+}{unit}")
        changes = QLabel("EFFECT OF YOUR COMMAND\n" + "\n".join(delta_lines))
        changes.setWordWrap(True)
        changes.setStyleSheet("font-size:16px; padding:16px; background:#241D2B; border:1px solid #75404A; border-radius:10px;")
        layout.addWidget(changes)
        note = QLabel("The ship diagram has also updated: damaged sections are dimmed and offline systems appear nearly dark.")
        note.setWordWrap(True)
        note.setStyleSheet("font-size:14px; color:#A9BDD4;")
        layout.addWidget(note)
        layout.addStretch()
        close_button = QPushButton("RETURN TO MISSION CONTROL")
        close_button.setMinimumHeight(56)
        close_button.setStyleSheet("font-size:17px; font-weight:bold;")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec_()

    # ==========================================
    # NETWORK CONNECTION
    # ==========================================

    def connect_to_server(self):

        if self.connection:
            return

        try:

            connection = socket.create_connection(
                (SERVER_HOST, SERVER_PORT),
                timeout=2
            )

            connection.setblocking(False)
            self.connection = connection

            self.send_message({
                "type": "JOIN",
                "role": "mission_control"
            })

            self.connection_label.setText("● CONNECTING...")
            self.mission_status.setText("● CONNECTING TO SERVER")

            self.add_log("Connecting to mission server...")

        except OSError as error:

            self.connection = None

            self.connection_label.setText("● SERVER DISCONNECTED")
            self.mission_status.setText("● CONNECTION FAILED")

            self.add_log(f"Connection failed: {error}")

    def send_message(self, message):

        if not self.connection:
            self.add_log("Cannot send command: server disconnected.")
            return

        try:

            data = json.dumps(message).encode("utf-8") + b"\n"
            self.connection.sendall(data)

        except OSError as error:

            self.add_log(f"Network error: {error}")
            self.disconnect_from_server()

    # ==========================================
    # RECEIVE SERVER MESSAGES
    # ==========================================

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
                    self.disconnect_from_server()
                    return

                self.receive_buffer += chunk

            while b"\n" in self.receive_buffer:

                line, self.receive_buffer = self.receive_buffer.split(
                    b"\n", 1
                )

                if not line:
                    continue

                try:

                    message = json.loads(line.decode("utf-8"))
                    self.handle_message(message)

                except (UnicodeDecodeError, json.JSONDecodeError):

                    self.add_log("Invalid server message.")

        except OSError as error:

            self.add_log(f"Network error: {error}")
            self.disconnect_from_server()

    # ==========================================
    # HANDLE SERVER MESSAGES
    # ==========================================

    def handle_message(self, message):

        message_type = message.get("type")

        if message_type == "WELCOME":

            self.connection_label.setText("● SERVER CONNECTED")
            self.mission_status.setText("● MISSION ONLINE")

            self.add_log("Connected as Mission Control.")

        elif message_type == "TELEMETRY":

            data = message.get("data", {})

            self.update_telemetry(data)

            if "modules" in data:
                self.update_module_status(data["modules"])

        elif message_type == "ALERT":

            alert = message.get("message", "Unknown emergency")
            self.trigger_impact_effect()

            self.mission_status.setText("● EMERGENCY DETECTED")

            self.add_log(f"EMERGENCY: {alert}")

        elif message_type == "ACTION_RESULT":

            result = message.get("message", "")
            self.add_log(f"SERVER: {result}")

        elif message_type == "PLAYER_JOINED":

            self.add_log(
                f"Player joined: {message.get('role', 'unknown')}"
            )

        elif message_type == "PLAYER_LEFT":

            self.add_log(
                f"Player disconnected: {message.get('role', 'unknown')}"
            )

        elif message_type == "ERROR":

            self.add_log(
                f"SERVER ERROR: {message.get('message', 'Unknown error')}"
            )

    # ==========================================
    # UPDATE TELEMETRY
    # ==========================================

    def update_telemetry(self, data):

        for key, (value_label, unit) in self.telemetry_labels.items():

            if key not in data:
                continue

            value = data[key]

            value_label.setText(f"{value}{unit}")

            description = self.telemetry_descriptions[key]

            if key in ("oxygen", "energy", "hull_integrity"):

                if value <= 25:
                    description.setText("CRITICAL")
                    description.setStyleSheet(
                        "color: #FF5555; font-weight: bold;"
                    )

                elif value <= 50:
                    description.setText("WARNING")
                    description.setStyleSheet(
                        "color: #FFAA45; font-weight: bold;"
                    )

                else:
                    description.setText("NORMAL")
                    description.setStyleSheet(
                        "color: #48DDA5; font-weight: bold;"
                    )

            elif key == "temperature":

                if value >= 35 or value <= 5:
                    description.setText("WARNING")
                    description.setStyleSheet(
                        "color: #FF5555; font-weight: bold;"
                    )

                else:
                    description.setText("NORMAL")
                    description.setStyleSheet(
                        "color: #48DDA5; font-weight: bold;"
                    )

    # ==========================================
    # UPDATE MODULE STATUS
    # ==========================================

    def update_module_status(self, modules):

        self.module_statuses = modules.copy()

        for module_id, status_label in self.module_labels.items():

            status = modules.get(module_id, "UNKNOWN")

            if status == "ONLINE":

                status_label.setText("● ONLINE")
                status_label.setStyleSheet(
                    "color: #48DDA5; font-weight: bold;"
                )

            elif status == "DAMAGED":

                status_label.setText("● DAMAGED")
                status_label.setStyleSheet(
                    "color: #FFAA45; font-weight: bold;"
                )

            elif status == "OFFLINE":

                status_label.setText("● OFFLINE")
                status_label.setStyleSheet(
                    "color: #FF5555; font-weight: bold;"
                )

            else:

                status_label.setText("● UNKNOWN")
                status_label.setStyleSheet(
                    "color: #8199B7; font-weight: bold;"
                )

        self.warning_active = any(
            status in ("DAMAGED", "OFFLINE")
            for status in modules.values()
        )

        if self.warning_active:

            self.mission_status.setText("● EMERGENCY DETECTED")

            self.warning_banner.setText(
                "⚠ SPACECRAFT DAMAGE DETECTED — CHECK SYSTEMS!"
            )

        else:

            self.mission_status.setText("● MISSION ONLINE")
            self.warning_banner.hide()

        self.update_blink()

    # ==========================================
    # BLINKING WARNING AND DAMAGED PARTS
    # ==========================================

    def update_blink(self):

        if self.active_scenario:
            self.warning_banner.show()
            return

        if not self.warning_active:

            self.warning_banner.hide()

            for item in self.ship_parts.values():

                item.setBrush(QBrush(QColor("#102D4A")))
                item.setPen(QPen(QColor("#55DDF5"), 2))

            return

        self.blink_on = not self.blink_on

        if self.blink_on:

            self.warning_banner.show()

            color = QColor("#FF3030")
            fill = QColor("#631D2A")

        else:

            self.warning_banner.hide()

            color = QColor("#A52A35")
            fill = QColor("#321A2B")

        for module_id, item in self.ship_parts.items():

            status = self.module_statuses.get(module_id)

            if status in ("DAMAGED", "OFFLINE"):

                item.setPen(QPen(color, 3))
                item.setBrush(QBrush(fill))

            else:

                item.setPen(QPen(QColor("#55DDF5"), 2))
                item.setBrush(QBrush(QColor("#102D4A")))

    # ==========================================
    # EMERGENCY ACTIONS
    # ==========================================

    def trigger_collision(self):

        if not self.connection:

            self.add_log(
                "Cannot simulate collision: server disconnected."
            )

            return

        self.send_message({
            "type": "TRIGGER_COLLISION"
        })

        self.add_log("Asteroid collision command sent.")

    # ==========================================
    # MISSION LOG
    # ==========================================

    def add_log(self, message):

        self.mission_log.appendPlainText(message)

        scrollbar = self.mission_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ==========================================
    # DISCONNECT
    # ==========================================

    def disconnect_from_server(self):

        if self.connection:

            try:
                self.connection.close()

            except OSError:
                pass

        self.connection = None
        self.receive_buffer = b""

        self.connection_label.setText("● SERVER DISCONNECTED")
        self.mission_status.setText("● CONNECTION LOST")

        self.add_log("Disconnected from mission server.")

    def closeEvent(self, event):

        self.network_timer.stop()
        self.blink_timer.stop()
        self.flight_timer.stop()

        self.disconnect_from_server()

        event.accept()

    # ==========================================
    # STYLESHEET
    # ==========================================

    def get_stylesheet(self):

        return """

        QMainWindow {
            background-color: #080F1D;
        }

        QWidget {
            font-family: 'Segoe UI';
            color: #E8F1FF;
        }

        #sidebar {
            background-color: #0D1729;
            border-right: 1px solid #1C3150;
        }

        #logo {
            color: #50DDF5;
            font-size: 21px;
            font-weight: bold;
        }

        #sidebarSubtitle {
            color: #7189A8;
            font-size: 10px;
            font-weight: bold;
        }

        QPushButton#navButton {
            background-color: transparent;
            color: #9BAFCB;
            border: 1px solid transparent;
            border-radius: 9px;
            text-align: left;
            padding-left: 14px;
            font-size: 13px;
            font-weight: 600;
        }

        QPushButton#navButton:hover {
            background-color: #192A43;
            color: white;
            border: 1px solid #294768;
        }

        QPushButton#activeNav {
            background-color: #123B55;
            color: #58E3FA;
            border: 1px solid #197B9B;
            border-radius: 9px;
            text-align: left;
            padding-left: 14px;
            font-size: 13px;
            font-weight: bold;
        }

        #connectionStatus {
            color: #48DDA5;
            font-size: 10px;
            font-weight: bold;
        }

        #reconnectButton {
            background-color: #142943;
            color: #55DDF5;
            border: 1px solid #294768;
            border-radius: 7px;
            padding: 8px;
        }

        #reconnectButton:hover {
            background-color: #1B3B5B;
        }

        #versionLabel {
            color: #526985;
            font-size: 10px;
        }

        #pageTitle {
            font-size: 28px;
            font-weight: bold;
            color: white;
        }

        #missionStatus {
            color: #48DDA5;
            font-size: 12px;
            font-weight: bold;
        }

        #welcomeText {
            color: #8FA6C4;
            font-size: 13px;
        }

        #telemetryCard {
            background-color: #111F34;
            border: 1px solid #233C5D;
            border-radius: 12px;
        }

        #telemetryName {
            color: #8199B7;
            font-size: 12px;
            font-weight: bold;
        }

        #telemetryValue {
            color: #55DDF5;
            font-size: 29px;
            font-weight: bold;
        }

        #telemetryDescription {
            color: #48DDA5;
            font-size: 12px;
        }

        #missionFrame {
            background-color: #0D192B;
            border: 1px solid #203956;
            border-radius: 14px;
        }

        #sectionTitle {
            color: #55DDF5;
            font-size: 15px;
            font-weight: bold;
        }

        #shipView {
            background-color: #06101F;
            border: 1px solid #1C4564;
            border-radius: 10px;
        }

        #warningBanner {
            background-color: #571C26;
            color: white;
            border: 1px solid #FF4545;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: bold;
        }

        QComboBox#scenarioSelector {
            background-color: #142943;
            color: #E8F1FF;
            border: 1px solid #315477;
            border-radius: 8px;
            padding: 8px;
            font-size: 12px;
        }

        QPushButton#scenarioButton {
            background-color: #14516A;
            color: #E8F1FF;
            border: 1px solid #2B9BB7;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: bold;
        }

        QPushButton#scenarioButton:hover {
            background-color: #1C6C86;
        }

        #moduleCard {
            background-color: #111F34;
            border: 1px solid #29415F;
            border-radius: 9px;
            min-height: 55px;
        }

        #moduleName {
            color: #8199B7;
            font-size: 12px;
            font-weight: bold;
        }

        #moduleStatus {
            font-size: 13px;
            font-weight: bold;
        }

        QPushButton#dangerButton {
            background-color: #9F3038;
            color: white;
            border: 1px solid #D94C55;
            border-radius: 10px;
            font-size: 13px;
            font-weight: bold;
        }

        QPushButton#dangerButton:hover {
            background-color: #C13B45;
        }

        QPushButton#dangerButton:pressed {
            background-color: #78232B;
        }

        #missionLog {
            background-color: #0D192B;
            color: #A9C1DD;
            border: 1px solid #203956;
            border-radius: 8px;
            font-size: 10px;
        }

        """


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = OrbitTrackApp()
    window.show()

    sys.exit(app.exec_())

