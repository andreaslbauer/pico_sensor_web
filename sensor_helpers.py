from ssd1306 import SSD1306_I2C
from machine import Pin, I2C, ADC
from picozero import pico_temp_sensor
import onewire, ds18x20

# helper class for the OLED display with 1306 chip
class oled_display:
    
    def __init__(self, i2c_id, sda_pin, scl_pin):
        self.i2c_id = i2c_id
        self.sda_pin = sda_pin
        self.scl_pin = scl_pin
        self.i2c = None
        self.oled = None        

        try:
            self.i2c = I2C(self.i2c_id, sda = Pin(self.sda_pin), scl = Pin(self.scl_pin), freq = 400000)
            self.oled = SSD1306_I2C(128, 64, self.i2c)
            print("OLED 1306 display found and initialized")
            self.oled.text("OLED1306", 0, 0)
            self.oled.text("Found and", 0, 16)
            self.oled.text("initilized", 0, 32)
            self.oled.show()

        except:
            print("Unable to access OLED 1306 display")

    # print a string at the given row (0 through 5)
    def print(self, s, row):
        if (self.oled != None):
            #print("OLED: ", s)
            offset = 0
            if row > 0:
                offset = (row - 1) * 12 + 16
            self.oled.text(s, 0, offset)
            self.oled.show()

    # clear the display
    def clear(self):
        if (self.oled != None):
            self.oled.fill(0)
            
# helper class for the DS18B20 temperature sensor
class ds18b20:
    
    def __init__(self, pin_id):
        self.sensor_pin = Pin(pin_id, Pin.IN)
        self.sensor = ds18x20.DS18X20(onewire.OneWire(self.sensor_pin))
        self.roms = self.sensor.scan()
        print ("DS18B20 Sensors found: ", self.roms)
        
    def sensor_count(self):
        return len(self.roms)
    
    def sensor(self):
        return self.sensor
    
    def roms(self):
        return self.roms

class cap_soil_moisture:
    
    def __init__ (self, pin_id):
        self.pin_id = pin_id
        self.moisture_adc = ADC(Pin(self.pin_id))
        # Calibraton values
        self.min_moisture=0
        self.max_moisture=65535
        
    def getValue(self):
        return round((self.max_moisture - self.moisture_adc.read_u16()) * 100 /
                     (self.max_moisture - self.min_moisture), 2)

   
