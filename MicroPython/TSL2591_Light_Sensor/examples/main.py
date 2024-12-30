from machine import Pin, I2C
import time
from waveshare_TSL2591 import TSL2591

# Initialize the I2C object and specify the SCL and SDA pins.
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000) 

sensor = TSL2591.TSL2591(i2c)
# sensor.SET_InterruptThreshold(0xff00, 0x0010)
try:
    while True:
        lux = sensor.Lux
        print('Lux: %d' % lux)
        sensor.TSL2591_SET_LuxInterrupt(50, 200)    
        infrared = sensor.Read_Infrared
        print('Infrared light: %d' % infrared) 
        visible = sensor.Read_Visible
        print('Visible light: %d' % visible)     
        full_spectrum = sensor.Read_FullSpectrum
        print('Full spectrum (IR + visible) light: %d' % full_spectrum)    
    
except KeyboardInterrupt:    
    print("Program interrupted by user.")
    sensor.Disable()
    exit()