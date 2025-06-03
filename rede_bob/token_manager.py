import time

class TokenManager:
    def __init__(self, timeout, is_token_gen, send_token_callback):
        self.timeout = timeout
        self.is_token_gen = is_token_gen
        self.send_token = send_token_callback

    def start(self):
        while True:
            time.sleep(self.timeout + 5)
            print("[Controle] Token não passou recentemente. Gerando novo token.")
            self.send_token()
