def create_data_packet(ctrl, origem, destino, crc, msg):
    return f"7777:{ctrl};{origem};{destino};{crc};{msg}"

def parse_packet(packet):
    content = packet.split("7777:")[1]
    return content.split(";")