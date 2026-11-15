NASA ARASAKA — Mission Control & Onboard Commander

Real-time multiplayer space mission simulation built with Python. Two players cooperate over a network: one acts as Mission Control on the ground, the other as the Onboard Commander aboard the spacecraft. Both must coordinate to survive space-weather emergencies.
Overview

NASA ARASAKA is an educational simulation inspired by real NASA space-weather data (DONKI). Players face scenarios based on actual categories of space-weather events — Radiation Belt Enhancements, Solar Flares, Solar Energetic Particles, and Coronal Mass Ejections — and must make decisions that affect the ship's systems and the crew's health.

The project demonstrates:

    Client–server architecture over TCP sockets

    Real-time state synchronization between two roles

    Role-based information asymmetry (Mission Control sees telemetry, Onboard Commander sees crew health)

    Turn-based scenario resolution with consequences

Features

    Two-player cooperative gameplay over a local network or the internet

    Four educational scenarios based on real NASA DONKI event categories

    Live telemetry: oxygen, energy, hull integrity, cabin temperature

    Crew health simulation: individual health and heart rate for four crew members

    Module status tracking: life support, engine, navigation, communications

    Asteroid collision event for testing damage propagation

    Mission orders: Mission Control issues commands, Onboard Commander executes

    Crew proposals: Onboard Commander suggests actions, Mission Control approves

    In-game chat between the two roles

    Game-over conditions: oxygen depletion, energy depletion, hull destruction, temperature extremes, crew incapacitation

Project Structure
text

project/
├── server.py                  # Game server (TCP, port 5000)
├── game/
│   ├── __init__.py
│   ├── ship.py                # Spaceship state, crew, modules
│   └── events.py              # Asteroid collision and event handlers
├── mission_control.py         # Mission Control GUI (PyQt5)
├── onboard_commander.py       # Onboard Commander GUI (PyQt5)
└── README.md

Requirements

    Python 3.8+

    PyQt5 (for the two GUI clients)

Install dependencies:
bash

pip install PyQt5

The server has no external dependencies — only Python's standard library.
Quick Start (Single Machine)

Open three terminals in the project folder.

Terminal 1 — Server:
bash

python server.py

Expected output:
text

=============================================
       NASA ARASAKA MISSION SERVER
=============================================
[SERVER] Running on 0.0.0.0:5000
[SERVER] Waiting for clients...

Terminal 2 — Mission Control:
bash

python mission_control.py

Terminal 3 — Onboard Commander:
bash

python onboard_commander.py

Both clients should show ● CONNECTED in their sidebars.
Playing Across Two Computers

By default, the server listens on 0.0.0.0 and clients connect to 127.0.0.1. To play across two machines:
1. Find the server's LAN IP

Windows:
cmd

ipconfig

Look for IPv4 Address (e.g. 192.168.1.42).

macOS / Linux:
bash

hostname -I

2. Update the client configuration

In both mission_control.py and onboard_commander.py, change:
python

SERVER_HOST = "127.0.0.1"

to the server's LAN IP:
python

SERVER_HOST = "192.168.1.42"

3. Open the firewall port

Windows (run as Administrator):
cmd

netsh advfirewall firewall add rule name="NASA Server 5000" dir=in action=allow protocol=TCP localport=5000

Linux:
bash

sudo ufw allow 5000/tcp

macOS: allow incoming connections when prompted.
4. Verify connectivity

From the client machine:
bash

ping 192.168.1.42

Then check the port:

Windows:
cmd

Test-NetConnection 192.168.1.42 -Port 5000

macOS / Linux:
bash

nc -zv 192.168.1.42 5000

If both checks succeed, launch the clients.
5. Play

    Computer A: run server.py, then mission_control.py

    Computer B: run onboard_commander.py with SERVER_HOST set to Computer A's IP

Playing Across Different Networks

If the two computers are not on the same LAN, use a tunnel:

Option A — ngrok (fastest):
bash

ngrok tcp 5000

Copy the resulting address (e.g. tcp://2.tcp.ngrok.io:12345) and set:
python

SERVER_HOST = "2.tcp.ngrok.io"
SERVER_PORT = 12345

Option B — Tailscale or ZeroTier: install on both machines and use the assigned virtual IP.

Option C — Cloud VPS: run server.py on the VPS and open port 5000 in the provider's firewall.
How to Play
Mission Control (Ground)

    Telemetry panel: monitors oxygen, energy, hull integrity, temperature

    Load Scenario: select one of four scenarios and load it

    Simulate Asteroid Collision: triggers a damage event

    Issue Orders: send a command to the Onboard Commander

    Review Proposals: approve or reject crew suggestions

    Chat: communicate with the crew

Onboard Commander (Spacecraft)

    Telemetry panel: same ship status, plus crew health and heart rate

    Crew panel: private view of each crew member's condition

    Mission Orders: confirm and execute orders from Mission Control

    Send Proposals: suggest an action to Mission Control

    Chat: communicate with the ground

Scenario Flow

    Mission Control loads a scenario.

    The server applies initial damage to ship systems and crew.

    Both clients receive the alert.

    Mission Control chooses a response (three options per scenario).

    The server applies the consequences and broadcasts the outcome.

    Both clients see updated telemetry and crew status.

Scenarios and Scientific Basis

All four scenarios are educational simulations based on real NASA space-weather categories (NASA DONKI). The physical phenomena, event categories, and referenced data are real; the specific mission narrative and numerical damage values are game design.
Scenario	Scientific Basis
Radiation Belt Alert	Radiation Belt Enhancement (RBE) events — real DONKI category, e.g. event 2025-04-15T11:10:00-RBE-001
Communications Alert	Solar Flare (FLR) events — real DONKI category with class and location
Solar Particle Event	Solar Energetic Particles (SEP) — real events, e.g. 2016-01-02T02:48:00-SEP-001
Lunar Approach	Coronal Mass Ejection (CME) — real DONKI category, e.g. 2016-01-15T00:00:00-CME-001; Shackleton Crater is a real lunar feature (NASA LRO)
What is real vs. simulated

    Real: the space-weather phenomena, the DONKI event categories, the referenced event IDs, Shackleton Crater's location and properties

    Simulated: ship damage, crew injuries, decision outcomes, and all numerical values

    Not based on any real accident: the asteroid-collision event is a pure training scenario

Reference: NASA CCMC DONKI
Game Over Conditions

The mission ends if any of the following occurs:
Reason	Trigger
OXYGEN_DEPLETED	Oxygen ≤ 0
ENERGY_DEPLETED	Energy ≤ 0
HULL_DESTROYED	Hull integrity ≤ 0
TEMPERATURE_CRITICAL_LOW	Temperature ≤ 0 °C
TEMPERATURE_CRITICAL_HIGH	Temperature ≥ 50 °C
CREW_INCAPACITATED	All crew members at 0 HP
Network Protocol

Messages are newline-delimited JSON over TCP.
Client → Server
Type	Fields	Role
JOIN	role (mission_control / onboard_commander)	any
CHAT	text	both
TRIGGER_COLLISION	—	mission_control
ORDER	module	mission_control
EXECUTE_ORDER	order_id	onboard_commander
PROPOSAL	text, module	onboard_commander
PROPOSAL_RESPONSE	proposal_id, approved	mission_control
LOAD_SCENARIO	scenario_id	mission_control
SCENARIO_CHOICE	scenario_id, choice_index	mission_control
PING	—	any
Server → Client
Type	Purpose
WELCOME	Confirms successful join
TELEMETRY	Ship status (crew included only for onboard_commander)
ALERT	Emergency or informational message
ORDER	Pending order for the crew
ORDER_ISSUED	Broadcast order for everyone
ACTION_RESULT	Order execution result
PROPOSAL	New crew proposal for Mission Control
PROPOSAL_SENT	Confirmation to the crew
PROPOSAL_RESPONSE	Mission Control's verdict
SCENARIO_ALERT	Scenario briefing for the crew
SCENARIO_STARTED	Scenario broadcast to both roles
SCENARIO_OUTCOME	Scenario resolution with new crew/telemetry
EVENT	Asteroid collision event
GAME_OVER	Mission failed
PLAYER_JOINED / PLAYER_LEFT	Connection notifications
ERROR	Invalid message
PONG	Response to PING
Troubleshooting
Symptom	Cause	Fix
Connection refused	Server not running or wrong IP	Start server.py, check SERVER_HOST
Connection timed out	Firewall or different networks	Open port 5000; see "Playing Across Different Networks"
Client connects but immediately disconnects	Same role used on two clients	Use one Mission Control and one Onboard Commander
OSError: [WinError 10048]	Port 5000 already in use	Kill the old process or change PORT (and clients' SERVER_PORT)
ALERT messages don't show	Outdated client code	Update both clients to read message from the top level
Crew HP does not decrease	Outdated game/ship.py	Replace with the version that has apply_crew_delta and the improved update_crew_environment
Credits

    Scenario framework inspired by NASA CCMC DONKI

    Lunar feature data from NASA Lunar Reconnaissance Orbiter

    Crew radiation reference: NASA Human Research Program

    Built with PyQt5

