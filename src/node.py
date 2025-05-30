import socket
import threading
import time
from message_queue import MessageQueue
from token_manager import TokenManager
from crc_utils import compute_crc32, verify_crc32
from packet_utils import create_data_packet, parse_packet
from error_injector import maybe_corrupt

class Node:
    def __init__(self, config_file):
        self.load_config(config_file)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        self.queue = MessageQueue()
        self.token_manager = TokenManager(self.token_time, self.is_token_gen, self.send_token)

    def load_config(self, filename):
        with open(filename) as f:
            lines = [line.strip() for line in f.readlines()]
            ip_port = lines[0].split(":")
            self.right_ip, self.right_port = ip_port[0], int(ip_port[1])
            self.nickname = lines[1]
            self.token_time = int(lines[2])
            self.is_token_gen = lines[3].lower() == "true"
            self.port = int(ip_port[1])  # listen on same port

    def run(self):
        if self.is_token_gen:
            threading.Thread(target=self.token_manager.start).start()
        threading.Thread(target=self.receive).start()

        while True:
            msg = input("Digite uma mensagem (apelido destino:mensagem): ")
            if msg:
                parts = msg.split(":", 1)
                self.queue.add_message(parts[1], parts[0])  # mensagem, destino

    def receive(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            msg = data.decode()
            if msg == "9000":  # Token
                self.handle_token()
            elif msg.startswith("7777:"):
                self.handle_data_packet(msg)

    def send_token(self):
        self.sock.sendto("9000".encode(), (self.right_ip, self.right_port))

    def handle_token(self):
        if not self.queue.is_empty():
            msg, dest = self.queue.get_message()
            crc = compute_crc32(msg)
            packet = create_data_packet("naoexiste", self.nickname, dest, crc, msg)
            packet = maybe_corrupt(packet)
            self.sock.sendto(packet.encode(), (self.right_ip, self.right_port))
        else:
            self.send_token()

    def handle_data_packet(self, packet_str):
        ctrl, orig, dest, crc, msg = parse_packet(packet_str)
        if dest == self.nickname:
            if verify_crc32(msg, crc):
                print(f"Mensagem de {orig}: {msg}")
                ctrl = "ACK"
            else:
                ctrl = "NACK"
            new_packet = create_data_packet(ctrl, orig, dest, crc, msg)
            self.sock.sendto(new_packet.encode(), (self.right_ip, self.right_port))
        elif orig == self.nickname:
            print(f"Mensagem retornou com {ctrl}")
            if ctrl == "ACK" or ctrl == "naoexiste":
                self.queue.confirm_delivery()
            elif ctrl == "NACK":
                self.queue.requeue_message()
            self.send_token()
        else:
            self.sock.sendto(packet_str.encode(), (self.right_ip, self.right_port))
