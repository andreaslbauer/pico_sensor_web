from machine import Pin, Timer, I2C, ADC
from ssd1306 import SSD1306_I2C
import time, utime

# use variables instead of numbers:
soil = ADC(Pin(28)) # Connect Soil moisture sensor data to Raspberry pi pico GP26 
 
#Calibraton values
min_moisture=0
max_moisture=65535
 
led = Pin("LED", machine.Pin.OUT)
led_pin = Pin(15, Pin.OUT)
timer = Timer()
   
# initialize the OLD display
i2c = None
oled = None
try:
    i2c = I2C(1, sda=Pin(14), scl=Pin(15), freq=400000)
    oled = SSD1306_I2C(128, 64, i2c)
    print("OLED 1306 display found and initialized")
    oled.text("OLED1306", 0, 0)
    oled.text("Found and", 0, 16)
    oled.text("initilized", 0, 32)
    oled.show()

except:
    print("Unable to access OLED 1306 display")

def oprint(s, row):
    global oled
    if (oled != None):
        #print("OLED: ", s)
        offset = 0
        if row > 0:
            offset = (row - 1) * 12 + 16
        oled.text(s, 0, offset)
        oled.show()

import network
import socket
from time import sleep
from picozero import pico_temp_sensor, pico_led
import machine
import onewire, ds18x20
import _thread
import struct

ssid = 'MayzieNet'
password = 'Alexander5'
ip_str = ""
sensor_pin = Pin(18, Pin.IN)
sensor = ds18x20.DS18X20(onewire.OneWire(sensor_pin))
roms = sensor.scan()

# number of sensors is temp sensors detected, plus the moisture sensor
sensor_count = len(roms) + 1
print ("DS18B20 Sensors found: ", roms)
lock = _thread.allocate_lock()
rtc = machine.RTC()
 
def toggle_led(timer):
    global led_pin
    led_pin.toggle()

temps = [0, 0]
temps_ring_buffer_len = 10
temps_ring_buffer = [None] * temps_ring_buffer_len
temps_ring_buffer_idx = 0
temps_interleave = 20
temps_interleave_count = 0

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
    finally:
        s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    t = val - NTP_DELTA    
    tm = time.gmtime(t)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
    print("Clock set from NTP at ", host, " time is: ", getTimeStr())
    oprint(getTimeStr(), 1)

def getTemps():
    list = []
    sensor.convert_temp()
    time.sleep(2)
    i = 0
    if (oled != None):
        oled.fill(0)
    oprint("At: " + getTimeStr(), 0)
    oprint(ip_str, 4)
    for rom in roms:
        temperature = round(sensor.read_temp(rom), 2)
        list.append(temperature)
        oprint("T" + str(i + 1) + ": " + str(temperature), 1 + i)
        i += 1
        
    moisture = round((max_moisture-soil.read_u16()) * 100 / (max_moisture-min_moisture), 2)
    # print values
    #print("moisture: " + "%.2f" % moisture +"% (adc: "+str(soil.read_u16())+")")
    oprint("M: " + str(moisture), i + 1)
    list.append(moisture)
    
    return list

def core2TaskGetTemp():
    while True:
        t = getTemps()
        #print("Got temps: ", t, " at ", getTimeStr())
        global temps
        temps_ring_buffer
        global temps_ring_buffer_idx
        global temps_interleave_count
        global temps_interleave
        lock.acquire()
        temps = t
        
        # every so often record the temperature in our ring buffer
        if temps_interleave_count == 0:   
            temp_record = {
                'datetime': getTimeStr(),
                'temps': t
                }
            temps_ring_buffer[temps_ring_buffer_idx] = temp_record
            temps_ring_buffer_idx += 1
            if (temps_ring_buffer_idx >= temps_ring_buffer_len):
                temps_ring_buffer_idx = 0
            #print ("Ring Buffer: ", temps_ring_buffer, temps_ring_buffer_idx)

        temps_interleave_count += 1
        if temps_interleave_count >= temps_interleave:
            temps_interleave_count = 0

        lock.release()
        time.sleep(3)

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

def temperatureTableHTML():
    global sensor_count
    html = """
<table class="table table-striped">
  <thead class="thead-dark">
    <tr>
      <th scope="col">Line</th>  
      <th scope="col">Time</th>
"""
    for i in range(sensor_count):
        html += '<th scope="col">Sensor ' + str(i) + '</th>'
    html += """
    </tr>
  </thead>
  <tbody>
"""
    global temps
    html += "<tr><td>Current</td><td>" + getTimeStr() + "</td>"
    for col_idx in range(0, sensor_count ):
        html += "<td>" + str(temps[col_idx]) + "</td>"
    html += "</tr>"
    
    global temps_ring_buffer_len
    global temps_ring_buffer
    global temps_ring_buffer_idx
    item_count = 0
    item_index = temps_ring_buffer_idx
    if item_index >= temps_ring_buffer_len:
            item_index = 0
    averages = [0,0]
            
    while item_count < temps_ring_buffer_len:
        row = temps_ring_buffer[item_index]
        item_index += 1
        if item_index >= temps_ring_buffer_len:
            item_index = 0
        item_count += 1
        if row != None:
            html += "<tr>"
            html += "<td>" + str(item_count) + "</td>"
            html += "<td>" + row['datetime'] + "</td>"
            col_idx = 0
            for col in row['temps']:
                html += "<td>" + str(col) + "</td>"
                col_idx += 1
                if col_idx >= sensor_count:
                    col_idx = 0
                averages[col_idx] += col
            html += "</tr>"
    html += "<tr><td>Avg</td><td></td>"
    for col_idx in range(0, sensor_count):
        html += "<td>" + str(averages[col_idx] / temps_ring_buffer_len) + "</td>"
    html += "</tr>"
    html += """
</tbody>
</tr>
</table>
"""
    return html

def webpage(temperature, state):
    lock.acquire()
    t1 = temps[0]
    t2 = temps[1]
    lock.release()
    timestr = getTimeStr()
    #Template HTML
    html = f"""
<!DOCTYPE html>
<html>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-GLhlTQ8iRABdZLl6O3oVMWSktQOp6b7In1Zl3/Jr59b6EGGoI1aFkw7cmDA6j6gD" crossorigin="anonymous">
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <a class="navbar-brand" href="#"><div id="hostname"></div></a>

  <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
    <span class="navbar-toggler-icon"></span>
  </button>

  <div class="collapse navbar-collapse" id="navbarSupportedContent">
    <ul class="navbar-nav mr-auto">
      <li class="nav-item active">
        <a class="nav-link" href="/">Home <span class="sr-only">(current)</span></a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/changes">Table</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="/detailedcharts">Chart</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="http://pifour:5000">PiFour</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="http://pished:5000">PiShed</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="http://pibrew:5000">PiBrew</a>
      </li>
      <li class="nav-item">
        <a class="nav-link" href="http://picam:5000">PiCam</a>
      </li>
    </ul>
  </div>
</nav>
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
""" + temperatureTableHTML() + """
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
        print(ip)
        request = str(request)
        pico_led.on()
        
        try:
            request = request.split()[1]
        except IndexError:
            pass
       
        print("Got request for: ", request)
        if (request != "/favicon.ico"):
            if (oled != None):
                oled.fill(0)
                oprint("Request", 0)
                oprint("At: " + getTimeStr(), 1)
                oprint(request, 2)
       
        if request == '/':
            led_pin.low()
            state = 'OFF'
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)  
        elif request == '/lighton?':
            led_pin.high()
            state = 'ON'
            temperature = pico_temp_sensor.temp
            html = webpage(temperature, state)
        elif request =='/lightoff?':
            led_pin.low()
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
        pico_led.off()


connection = None
try:
    ip = connect()
    oled.fill(0)
    oprint("Starting...", 0)
    oprint(ip_str, 1)
    set_clock_from_ntp()
    oprint(getTimeStr(), 2)
    _thread.start_new_thread(core2TaskGetTemp, ())
    connection = open_socket(ip)
    timer.deinit()
    led_pin.low()
    serve(connection)
   
except KeyboardInterrupt:
    print("Keyboard interupt - reset machine")
    if (connection != None):
        connection.close()
        print("Connection closed")
    else:
        print("No connection to close")
    sleep(1)
    machine.reset()
   
finally:
    if (connection != None):
        connection.close()
        print("Connection closed")

   



