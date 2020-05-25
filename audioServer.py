import socket

BufferSize = 4096
addresses = set()
server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
server.bind(('',666))

while True:
    data, addr = server.recvfrom(BufferSize)
    print(data)
    addresses.add(addr)
    for ad in addresses:
        if ad != addr:
            server.sendto(data,ad)
