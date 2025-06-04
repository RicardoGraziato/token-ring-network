import random

def maybe_corrupt(packet, prob=0.7):
    if random.random() < prob:
        return packet.replace("a", "x", 1)
    return packet
