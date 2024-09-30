# client.py
import os
import socket
import threading
import json
import hashlib
import sys

TARGET_HASH = 'EC9C0F7EDCC18A98B1F31853B1813301'.upper()


def worker(start, end, found_event, result):
    for number in range(start, end + 1):
        if found_event.is_set():
            break
        num_str = f"{number:010d}"
        hash_result = hashlib.md5(num_str.encode()).hexdigest().upper()
        if hash_result == TARGET_HASH:
            result.append(num_str)
            found_event.set()
            break


def send_message(conn, message):
    try:
        message_str = json.dumps(message) + '\n'
        conn.sendall(message_str.encode())
    except Exception as e:
        print(f"Error sending message: {e}")


def process_work(server_host, server_port, cores):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        register_message = {'type': 'register', 'cores': cores}
        send_message(s, register_message)

        buffer = ""
        while True:
            request = {'type': 'request_work', 'cores': cores}
            send_message(s, request)

            data = s.recv(4096).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                message_str, buffer = buffer.split('\n', 1)
                try:
                    message = json.loads(message_str)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error from server: {e}")
                    continue

                if message['type'] == 'work':
                    start = message['start']
                    end = message['end']
                    print(f"Received work: {start} - {end}")

                    total = end - start + 1
                    per_thread = total // cores
                    threads_list = []
                    found_event = threading.Event()
                    result = []

                    for i in range(cores):
                        thread_start = start + i * per_thread
                        thread_end = start + (i + 1) * per_thread - 1 if i < cores - 1 else end
                        t = threading.Thread(target=worker, args=(thread_start, thread_end, found_event, result))
                        threads_list.append(t)
                        t.start()

                    for t in threads_list:
                        t.join()

                    if result:
                        found_number = result[0]
                        found_message = {'type': 'found', 'number': found_number}
                        send_message(s, found_message)
                        print(f"Found the number: {found_number}")
                        return

                elif message['type'] == 'stop':
                    print("Received stop signal from server.")
                    return
                elif message['type'] == 'no_work':
                    print("No more work available. Exiting.")
                    return


def get_cpu_cores():
    return os.cpu_count()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py [server_host] [server_port]")
        sys.exit(1)
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    cores = get_cpu_cores()
    process_work(server_host, server_port, cores)
