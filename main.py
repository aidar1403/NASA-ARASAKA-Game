from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton


def create_sidebar(self):
    sidebar = QFrame()
    sidebar.setObjectName("sidebar")
    sidebar.setFixedWidth(220)

    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(14, 24, 14, 20)
    layout.setSpacing(9)

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
        btn = QPushButton(f"{icon}     {name}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(46)

        if index == 0:
            btn.setObjectName("activeNav")
        else:
            btn.setObjectName("navButton")

        layout.addWidget(btn)

    layout.addStretch()

    connection = QLabel("● SERVER CONNECTED")
    connection.setObjectName("connectionStatus")
    layout.addWidget(connection)

    version = QLabel("NASA ARASAKA v0.1")
    version.setObjectName("versionLabel")
    layout.addWidget(version)

    return sidebar
