from machine import Pin, Timer
import time

led = Pin("LED", machine.Pin.OUT)
led_pin = Pin(15, Pin.OUT)
timer = Timer()
    
import network
import socket
from time import sleep
from picozero import pico_temp_sensor, pico_led
import machine
import onewire, ds18x20
import _thread

ssid = 'MayzieNet'
password = 'Alexander5'
sensor_pin = Pin(26, Pin.IN)
sensor = ds18x20.DS18X20(onewire.OneWire(sensor_pin))
roms = sensor.scan()
print ("DS18B20 Sensors found: ", roms)
lock = _thread.allocate_lock()
rtc=machine.RTC()

temps = [0, 0]
temps_history = []

def getTemps():
    list = []
    sensor.convert_temp()
    time.sleep(2)
    for rom in roms:
        temperature = round(sensor.read_temp(rom), 2)
        list.append(temperature)
    
    return list

def getTimeStr():
    t = rtc.datetime()
    return "%04d-%02d-%02d %02d:%02d:%02d"%(t[0:3] + t[4:7])

def core2TaskGetTemp():
    while True:
        t = getTemps()
        print("Got temps: ", t, " at ", getTimeStr())
        global temps
        lock.acquire()
        temps = t
        temps_history.append(t)
        lock.release()
        time.sleep(10)

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
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

def webpage(temperature, state):
    lock.acquire()
    t1 = temps[0]
    t2 = 0
    lock.release()
    timestr = getTimeStr()
    #Template HTML
    html = f"""
<!DOCTYPE html>
<html>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-GLhlTQ8iRABdZLl6O3oVMWSktQOp6b7In1Zl3/Jr59b6EGGoI1aFkw7cmDA6j6gD" crossorigin="anonymous">
<body>
<div class="container">
<div class="row">
<div class="form-inline">
<div class="col-sm">
<form action="./lighton">
<input type="submit" class="btn btn-primary" value="Light on" />
</form>
</div>
<div class="col-sm">
<form action="./lightoff">
<input type="submit" class="btn btn-primary" value="Light off" />
</form>
</div>
</div>
<div class="row">
<p>LED is {state}</p>
<table class="table table-striped">
  <thead class="thead-dark">
    <tr>
      <th scope="col">Sensor</th>
      <th scope="col">Time</th>
      <th scope="col">Value</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>0</td><td>{timestr}</td><td>{temperature}</td></tr>
    <tr><td>1</td><td>{timestr}</td><td>{t1}</td></tr>
    <tr><td>2</td><td>{timestr}</td><td>{t2}</td></tr>
  </tbody>
</tr>
</table>
</div>
</div>
</body>
</html>
"""
    return str(html)

def serve(connection):
    #Start a web server
    state = 'OFF'
    pico_led.off()
    temperature = 0
    while True:
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        led_pin.high()
        try:
            request = request.split()[1]
        except IndexError:
            pass
        
        print("Got request for: ", request)
        
        if request == '/':
            pico_led.off()
            state = 'OFF'
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)   
        elif request == '/lighton?':
            pico_led.on()
            state = 'ON'
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)
        elif request =='/lightoff?':
            pico_led.off()
            state = 'OFF'
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)
        elif request == '/temps':
            lock.acquire()
            global temps
            tempslist = temps
            lock.release()
            index = 1
            length = len(tempslist)
            html = "["
            for t in tempslist:
                html += str(t)
                if index < length:
                    html += ', '
                index += 1
            html += "]"
        elif request == '/tempsall':
            lock.acquire()
            global temps
            temps_history_list = temps_history
            lock.release()
            index = 1
            length = len(tempslist)
            html = "["
            for t in tempslist:
                html += str(t)
                if index < length:
                    html += ', '
                index += 1
            html += "]"
        elif request == '/favicon.ico':
            html = ''
        else:
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)             
        
        client.send(html)
        client.close()
        led_pin.low()


connection = None
try:
    _thread.start_new_thread(core2TaskGetTemp, ())

    ip = connect()
    connection = open_socket(ip)
    serve(connection)
    
except KeyboardInterrupt:
    print("Keyboard interupt - reset machine")
    machine.reset()
    
finally:
    if (connection != None):
        connection.close()
    print("Connection closed")
    

    
