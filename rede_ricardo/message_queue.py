from collections import deque

class MessageQueue:
    def __init__(self):
        self.queue = deque(maxlen=10)
        self.current = None

    def add_message(self, message, dest):
        self.queue.append((message, dest))

    def get_message(self):
        self.current = self.queue[0]
        return self.current

    def confirm_delivery(self):
        if self.current:
            self.queue.popleft()
            self.current = None

    def requeue_message(self):
        pass

    def is_empty(self):
        return len(self.queue) == 0
