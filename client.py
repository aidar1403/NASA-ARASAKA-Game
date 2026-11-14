
import socket
import json
import threading

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


def send_message(connection, message):
    data = json.dumps(message, ensure_ascii=False) + "\n"
    connection.sendall(data.encode("utf-8"))


def receive_messages(connection):
    try:
        with connection.makefile("r", encoding="utf-8") as reader:
            for line in reader:
                message = json.loads(line)
                message_type = message.get("type")

                if message_type == "WELCOME":
                    print(f"\nConnected as: {message['role']}")

                elif message_type == "TELEMETRY":
                    print("\n=== SHIP TELEMETRY ===")
                    for key, value in message["data"].items():
                        print(f"{key}: {value}")

                elif message_type == "ALERT":
                    print(f"\n!!! ALERT: {message['message']} !!!")

                elif message_type == "ORDER":
                    print("\n!!! NEW ORDER FROM MISSION CONTROL !!!")
                    print(message["data"])
                    print("Type /execute to carry out the order.")

                elif message_type == "ACTION_RESULT":
                    print(f"\nSERVER: {message['message']}")

                elif message_type == "CHAT":
                    print(
                        f"\n[{message['from']}]: "
                        f"{message['text']}"
                    )

                elif message_type == "PLAYER_JOINED":
                    print(f"\nPlayer joined: {message['role']}")

                elif message_type == "PLAYER_LEFT":
                    print(f"\nPlayer left: {message['role']}")

                elif message_type == "ERROR":
                    print(f"\nERROR: {message['message']}")

    except (ConnectionError, OSError, json.JSONDecodeError):
        print("\nConnection lost.")


def main():
    print("=== NASA ARASAKA MISSION CLIENT ===")

    role = input(
        "Choose role (mission_control / onboard_commander): "
    ).strip()

    if role not in ("mission_control", "onboard_commander"):
        print("Invalid role.")
        return

    connection = None

    try:
        connection = socket.create_connection(
            (SERVER_HOST, SERVER_PORT),
            timeout=5
        )

        connection.settimeout(None)

        send_message(connection, {
            "type": "JOIN",
            "role": role
        })

        receiver = threading.Thread(
            target=receive_messages,
            args=(connection,),
            daemon=True
        )
        receiver.start()

        print("\nCommands:")

        if role == "mission_control":
            print("/collision - simulate asteroid collision")
            print("/order life_support - isolate life support")
        else:
            print("/execute - execute received order")

        print("/exit - disconnect")
        print("Other text - send chat message\n")

        while True:
            text = input("> ").strip()

            if text == "/exit":
                break

            if role == "mission_control":
                if text == "/collision":
                    send_message(connection, {
                        "type": "TRIGGER_COLLISION"
                    })

                elif text.startswith("/order "):
                    module = text.split(" ", 1)[1]

                    send_message(connection, {
                        "type": "ORDER",
                        "module": module
                    })

                else:
                    send_message(connection, {
                        "type": "CHAT",
                        "text": text
                    })

            elif role == "onboard_commander":
                if text == "/execute":
                    send_message(connection, {
                        "type": "EXECUTE_ORDER"
                    })

                else:
                    send_message(connection, {
                        "type": "CHAT",
                        "text": text
                    })

    except ConnectionRefusedError:
        print("Cannot connect. Is the server running?")

    except OSError as error:
        print(f"Network error: {error}")

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()
