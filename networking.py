import network
import socket
from machine import Timer
import machine
from time import sleep
import time, utime
import struct

ssid = 'MayzieNet'
password = 'Alexander5'
ip_str = ""
rtc = machine.RTC()

def getTimeDateStr():
    t = rtc.datetime()
    return "%04d-%02d-%02d %02d:%02d:%02d"%(t[0:3] + t[4:7])

def getTimeStr():
    t = rtc.datetime()
    return "%02d:%02d:%02d"%(t[4:7])

# connect to an NTP server, obtain the current time and set our clock to that time
def set_clock_from_ntp():
    NTP_EST_ADJUST = 4 * 60 * 60
    NTP_DELTA = 2208988800 + NTP_EST_ADJUST
    host = "pool.ntp.org"
    
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(15)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
        
        val = struct.unpack("!I", msg[40:44])[0]
        t = val - NTP_DELTA    
        tm = time.gmtime(t)
        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        print("Clock set from NTP at ", host, " time is: ", getTimeStr())
        
    except:
        print("Unable to get time from NTP server")
            
    finally:
        s.close()

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    global ip_str
    ip_str = str(ip)
    print(f'Connected on address: {ip}')

    return ip
   
def open_socket(ip):
    # Open a socket
    address = (ip, 80)
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    connection.bind(address)
    connection.listen(1)
    return connection

