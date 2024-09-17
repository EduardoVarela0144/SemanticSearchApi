import socket
import fcntl
import struct

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915, 
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])

ip_address = get_ip_address('eth0')

bind = f"{ip_address}:5000"
workers = 2
timeout = 1000