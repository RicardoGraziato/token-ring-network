import random

def maybe_corrupt(packet, prob=0.1):
    if random.random() < prob:
        return packet.replace("a", "x", 1)
    return packet
