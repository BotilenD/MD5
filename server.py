# server.py
import socket
import threading
import json

TARGET_HASH = 'EC9C0F7EDCC18A98B1F31853B1813301'.upper()
START_NUMBER = 1 * 10**9
END_NUMBER = 1 * 10**10 - 1
BLOCK_SIZE_PER_CORE = 100000

lock = threading.Lock()
current_number = START_NUMBER
found = False
found_number = None

clients = []


def handle_client(conn, addr):
    global current_number, found, found_number
    print(f"Client {addr} connected.")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                message_str, buffer = buffer.split('\n', 1)
                try:
                    message = json.loads(message_str)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error from {addr}: {e}")
                    continue

                if message['type'] == 'register':
                    cores = message['cores']
                    with lock:
                        clients.append({'conn': conn, 'cores': cores})
                    print(f"Registered client {addr} with {cores} cores.")

                elif message['type'] == 'request_work':
                    with lock:
                        if found:
                            response = {'type': 'stop'}
                            send_message(conn, response)
                            continue
                        block_size = BLOCK_SIZE_PER_CORE * message['cores']
                        start = current_number
                        end = min(current_number + block_size - 1, END_NUMBER)
                        if start > END_NUMBER:
                            response = {'type': 'no_work'}
                            send_message(conn, response)
                            continue
                        current_number = end + 1
                    response = {'type': 'work', 'start': start, 'end': end}
                    send_message(conn, response)

                elif message['type'] == 'found':
                    with lock:
                        if not found:
                            found = True
                            found_number = message['number']
                            print(f"Found number: {found_number}")
                    notify_all_clients()

    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        conn.close()
        print(f"Client {addr} disconnected.")


def notify_all_clients():
    with lock:
        for client in clients:
            try:
                response = {'type': 'stop'}
                send_message(client['conn'], response)
            except Exception as e:
                print(f"Error notifying client: {e}")


def send_message(conn, message):
    try:
        message_str = json.dumps(message) + '\n'
        conn.sendall(message_str.encode())
    except Exception as e:
        print(f"Error sending message: {e}")


def server_main(host='0.0.0.0', port=5000):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"Server listening on {host}:{port}")

    try:
        while not found and current_number <= END_NUMBER:
            conn, addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server.close()
        if found:
            print(f"Number {found_number} found. Shutting down server.")


if __name__ == "__main__":
    server_main()
