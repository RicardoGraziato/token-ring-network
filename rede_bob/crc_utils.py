import zlib

def compute_crc32(data):
    return zlib.crc32(data.encode())

def verify_crc32(data, expected_crc):
    return compute_crc32(data) == int(expected_crc)
