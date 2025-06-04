import random

def maybe_corrupt(packet, prob=0.1):
    if random.random() < prob:
        return packet.replace(packet[0], "dnfnfk", 1)
    return packet
