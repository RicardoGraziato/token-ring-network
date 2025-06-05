import socket
import threading
import time
import random
from message_queue import MessageQueue
from crc_utils import compute_crc32, verify_crc32
from packet_utils import create_data_packet, parse_packet
from error_injector import maybe_corrupt
import datetime

class Node:
    def __init__(self, config_file, hosts):
        self.load_config(config_file)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        self.queue = MessageQueue()
        self.own_token = self.is_token_gen
        self.awaiting_ack = False
        self.token_delay_event = threading.Event()
        self.token_delay_thread = None
        self.last_token_time = 0
        self.hosts = hosts
        if self.is_token_gen:
            self.token_check_thread = threading.Thread(target=self.monitor_token)
            self.token_check_thread.daemon = True
            self.token_check_thread.start()

    def load_config(self, filename):
        with open(filename) as f:
            lines = [line.strip() for line in f.readlines()]

        ip_port = lines[0].split(":")
        self.right_ip, self.right_port = ip_port[0], int(ip_port[1])
        self.nickname = lines[1]
        self.token_time = int(lines[2])
        self.is_token_gen = lines[3].lower() == "true"

        apelido_para_porta = {
            "Bob": 6001,
            "Cristina": 6002,
            "Ricardo": 6003,
        }

        if self.nickname not in apelido_para_porta:
            raise ValueError(f"Apelido '{self.nickname}' não está mapeado para nenhuma porta.")
        self.port = apelido_para_porta[self.nickname]

    def monitor_token(self):
        while True:
            time.sleep(self.token_time * self.hosts)  # Aguarda 3x o tempo esperado
            elapsed = time.time() - self.last_token_time
            if elapsed > self.token_time * self.hosts and self.is_token_gen:
                print(f"[{self.nickname}] Token parece perdido. Gerando novo token.")
                self.send_token()

    def run(self):
        threading.Thread(target=self.receive, daemon=True).start()

        if self.is_token_gen:
            print(f"{self.nickname} é o gerador do token. Inicializando...")
            time.sleep(2)
            self.send_token()

        while True:
            msg = input("Digite uma mensagem (destino:mensagem): ")
            if msg:
                try:
                    dest, text = msg.split(":", 1)
                    self.queue.add_message(text.strip(), dest.strip())

                    if self.own_token and not self.awaiting_ack:
                        self.token_delay_event.set()
                        if self.token_delay_thread and self.token_delay_thread.is_alive():
                            self.token_delay_thread.join()
                        self.handle_token(True)
                except ValueError:
                    print("Formato inválido. Use: destino:mensagem")

    def receive(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            msg = data.decode()

            if msg == "9000":
                if self.own_token and self.is_token_gen:
                    print(f"[{self.nickname}] ERRO: Recebi um token enquanto ainda estava com outro! Token duplicado detectado.")
                    # (opcional) descarta ou registra
                    continue
                if random.random() < 0.1:
                    print(f"[{self.nickname}] Token descartado aleatoriamente para simular falha.")
                    continue
                self.handle_token(False)
            elif msg.startswith("7777:"):
                self.handle_data_packet(msg)

    def handle_token(self, msgSent):
        if(not msgSent):
            self.last_token_time = time.time()
            print(f"[{self.nickname}] Token recebido.")
        self.own_token = True

        if not self.queue.is_empty() and not self.awaiting_ack:
            msg, dest = self.queue.get_message()
            crc = compute_crc32(msg)
            msg_to_send = maybe_corrupt(msg)
            packet = create_data_packet("naoexiste", self.nickname, dest, crc, msg_to_send)
            print(f"[{self.nickname}] Enviando pacote para {dest}: {msg}")
            self.sock.sendto(packet.encode(), (self.right_ip, self.right_port))
            self.awaiting_ack = True
        else:
            print(f"[{self.nickname}] Sem mensagens. Esperando até {self.token_time}s.")
            self.token_delay_event.clear()
            self.token_delay_thread = threading.Thread(target=self.delayed_token_send)
            self.token_delay_thread.start()

    def delayed_token_send(self):
        if not self.token_delay_event.wait(self.token_time):
            print(f"[{self.nickname}] Tempo expirado. Enviando token.")
            self.send_token()

    def handle_data_packet(self, packet_str):
        ctrl, orig, dest, crc, msg = parse_packet(packet_str)

        if orig == self.nickname:
            # A mensagem voltou para mim, sou o remetente original
            print(f"[{self.nickname}] Resposta da minha mensagem: {ctrl}")
            if ctrl == "ACK" or ctrl == "naoexiste":
                self.queue.confirm_delivery()
                self.awaiting_ack = False
            elif ctrl == "NACK":
                self.queue.requeue_message()
                self.awaiting_ack = False
            self.send_token()

        elif dest == self.nickname:
            # Sou o destinatário da mensagem
            print(f"[{self.nickname}] Pacote destinado a mim de {orig}. Verificando integridade...")
            if verify_crc32(msg, crc):
                print(f"[{self.nickname}] Mensagem recebida com sucesso: '{msg}'")
                ctrl = "ACK"
            else:
                print(f"[{self.nickname}] Erro na mensagem recebida.")
                ctrl = "NACK"
            response = create_data_packet(ctrl, orig, dest, crc, msg)
            self.sock.sendto(response.encode(), (self.right_ip, self.right_port))

        else:
            # Encaminha para o próximo
            self.sock.sendto(packet_str.encode(), (self.right_ip, self.right_port))


    def send_token(self):
        if random.random() < 0.05:
            print(f"[{self.nickname}] Duplicando token para teste.")
            self.sock.sendto("9000".encode(), (self.right_ip, self.right_port))
            time.sleep(0.1)
        print(f"[{self.nickname}] Enviando token para próximo nó.")
        self.sock.sendto("9000".encode(), (self.right_ip, self.right_port))
        self.own_token = False
