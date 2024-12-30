# -*- coding:utf-8 -*-

import time
import math
from machine import Pin, I2C

INI_PIN = 1

ADDR = 0x29

COMMAND_BIT = 0xA0
# Register (0x00)
ENABLE_REGISTER = 0x00
ENABLE_POWERON = 0x01
ENABLE_POWEROFF = 0x00
ENABLE_AEN = 0x02
ENABLE_AIEN = 0x10
ENABLE_SAI = 0x40
ENABLE_NPIEN = 0x80

CONTROL_REGISTER = 0x01
SRESET = 0x80
# AGAIN
LOW_AGAIN = 0x00  # Low gain (1x)
MEDIUM_AGAIN = 0x10  # Medium gain (25x)
HIGH_AGAIN = 0x20  # High gain (428x)
MAX_AGAIN = 0x30  # Max gain (9876x)

# ATIME
ATIME_100MS = 0x00  # 100 millis # MAX COUNT 36863
ATIME_200MS = 0x01  # 200 millis # MAX COUNT 65535
ATIME_300MS = 0x02  # 300 millis # MAX COUNT 65535
ATIME_400MS = 0x03  # 400 millis # MAX COUNT 65535
ATIME_500MS = 0x04  # 500 millis # MAX COUNT 65535
ATIME_600MS = 0x05  # 600 millis # MAX COUNT 65535

AILTL_REGISTER = 0x04
AILTH_REGISTER = 0x05
AIHTL_REGISTER = 0x06
AIHTH_REGISTER = 0x07
NPAILTL_REGISTER = 0x08
NPAILTH_REGISTER = 0x09
NPAIHTL_REGISTER = 0x0A
NPAIHTH_REGISTER = 0x0B

PERSIST_REGISTER = 0x0C

ID_REGISTER = 0x12

STATUS_REGISTER = 0x13  # read only

CHAN0_LOW = 0x14
CHAN0_HIGH = 0x15
CHAN1_LOW = 0x16
CHAN1_HIGH = 0x14

# LUX_DF = GA * 53   GA is the Glass Attenuation factor 
LUX_DF = 762.0
MAX_COUNT_100MS = 36863  # 0x8FFF
MAX_COUNT = 65535  # 0xFFFF

class TSL2591:
    def __init__(self, i2c, address=ADDR):
        self.i2c = i2c  # 使用外部传入的 I2C 对象
        self.address = address
        
        self.pin = Pin(INI_PIN, Pin.IN)
        
        self.ID = self.Read_Byte(ID_REGISTER)
        if self.ID != 0x50:
            print("ID = 0x%x" % self.ID)
            raise Exception("Device not found")
        
        self.Enable()
        self.Set_Gain(MEDIUM_AGAIN)
        self.Set_IntegralTime(ATIME_100MS)
        self.Write_Byte(PERSIST_REGISTER, 0x01)
        self.Disable()

    def Read_Byte(self, Addr):
        Addr = (COMMAND_BIT | Addr) & 0xFF
        result = self.i2c.readfrom_mem(self.address, Addr, 1)
        return result[0]  # 返回字节值

    def Read_Word(self, Addr):
        Addr = (COMMAND_BIT | Addr) & 0xFF
        result = self.i2c.readfrom_mem(self.address, Addr, 2)
        return int.from_bytes(result, 'little')

    def Write_Byte(self, Addr, val):
        Addr = (COMMAND_BIT | Addr) & 0xFF
        self.i2c.writeto_mem(self.address, Addr, bytearray([val & 0xFF]))

    def Enable(self):
        self.Write_Byte(ENABLE_REGISTER, ENABLE_AIEN | ENABLE_POWERON | ENABLE_AEN | ENABLE_NPIEN)

    def Disable(self):
        self.Write_Byte(ENABLE_REGISTER, ENABLE_POWEROFF)

    def Get_Gain(self):
        data = self.Read_Byte(CONTROL_REGISTER)
        return data & 0b00110000

    def Set_Gain(self, Val):
        if Val in [LOW_AGAIN, MEDIUM_AGAIN, HIGH_AGAIN, MAX_AGAIN]:
            control = self.Read_Byte(CONTROL_REGISTER)
            control &= 0b11001111
            control |= Val
            self.Write_Byte(CONTROL_REGISTER, control)
            self.Gain = Val
        else:
            print("Gain Parameter Error")

    def Get_IntegralTime(self):
        control = self.Read_Byte(CONTROL_REGISTER)
        return control & 0b00000111

    def Set_IntegralTime(self, val):
        if val & 0x07 < 0x06:
            control = self.Read_Byte(CONTROL_REGISTER)
            control &= 0b11111000
            control |= val
            self.Write_Byte(CONTROL_REGISTER, control)
            self.IntegralTime = val
        else:
            print("Integral Time Parameter Error")

    def Read_CHAN0(self):
        return self.Read_Word(CHAN0_LOW)
    
    def Read_CHAN1(self):
        return self.Read_Word(CHAN1_LOW)
    
    @property
    def Read_FullSpectrum(self):
        """Read the full spectrum (IR + visible) light and return its value"""
        self.Enable()
        data = (self.Read_CHAN1() << 16) | self.Read_CHAN0()
        self.Disable()
        return data

    @property   
    def Read_Infrared(self):
        '''Read the infrared light and return its value as a 16-bit unsigned number'''
        self.Enable()
        data = self.Read_CHAN0()
        self.Disable()
        return data
    
    @property
    def Read_Visible(self):
        '''Read the visible light'''
        self.Enable()
        Ch1 = self.Read_CHAN1()
        Ch0 = self.Read_CHAN0()
        self.Disable()
        full = (Ch1 << 16) | Ch0
        return full - Ch1
    
    @property
    def Lux(self):
        self.Enable()
        time.sleep(0.1)  # Simulate time for integration
        if self.pin.value() == 1:
            print('INT 0')
        else:
            print('INT 1')
        channel_0 = self.Read_CHAN0()
        channel_1 = self.Read_CHAN1()
        self.Disable()

        self.Enable()
        self.Write_Byte(0xE7, 0x13)  # Clear interrupt flag
        self.Disable()

        atime = 100.0 * self.IntegralTime + 100.0
        max_counts = MAX_COUNT_100MS if self.IntegralTime == ATIME_100MS else MAX_COUNT

        if channel_0 >= max_counts or channel_1 >= max_counts:
            gain_t = self.Get_Gain()
            if gain_t != LOW_AGAIN:
                gain_t = ((gain_t >> 4) - 1) << 4
                self.Set_Gain(gain_t)
                channel_0 = channel_1 = 0
                while channel_0 <= 0 and channel_1 <= 0:
                    channel_0 = self.Read_CHAN0()
                    channel_1 = self.Read_CHAN1()
                    time.sleep(0.1)
            else:
                raise RuntimeError('Numerical overflow!')

        again = 1.0
        if self.Gain == MEDIUM_AGAIN:
            again = 25.0
        elif self.Gain == HIGH_AGAIN:
            again = 428.0
        elif self.Gain == MAX_AGAIN:
            again = 9876.0

        Cpl = (atime * again) / LUX_DF
        lux1 = (channel_0 - (2 * channel_1)) / Cpl
        return max(int(lux1), 0)
    
    def SET_InterruptThreshold(self, HIGH, LOW):
        self.Enable()
        self.Write_Byte(AILTL_REGISTER, LOW & 0xFF)
        self.Write_Byte(AILTH_REGISTER, LOW >> 8)
        
        self.Write_Byte(AIHTL_REGISTER, HIGH & 0xFF)
        self.Write_Byte(AIHTH_REGISTER, HIGH >> 8)
        
        self.Write_Byte(NPAILTL_REGISTER, 0)
        self.Write_Byte(NPAILTH_REGISTER, 0)
        
        self.Write_Byte(NPAIHTL_REGISTER, 0xff)
        self.Write_Byte(NPAIHTH_REGISTER, 0xff)
        self.Disable()
        
    def TSL2591_SET_LuxInterrupt(self, SET_LOW, SET_HIGH):
        atime = 100 * self.IntegralTime + 100
        again = 1.0
        if self.Gain == MEDIUM_AGAIN:
            again = 25.0
        elif self.Gain == HIGH_AGAIN:
            again = 428.0
        elif self.Gain == MAX_AGAIN:
            again = 9876.0
        
        Cpl = (atime * again) / LUX_DF
        channel_1 = self.Read_CHAN1()
        
        SET_HIGH = int(Cpl * SET_HIGH) + 2 * channel_1 - 1
        SET_LOW = int(Cpl * SET_LOW) + 2 * channel_1 + 1
        
        self.Enable()
        self.Write_Byte(AILTL_REGISTER, SET_LOW & 0xFF)
        self.Write_Byte(AILTH_REGISTER, SET_LOW >> 8)
        
        self.Write_Byte(AIHTL_REGISTER, SET_HIGH & 0xFF)
        self.Write_Byte(AIHTH_REGISTER, SET_HIGH >> 8)
        
        self.Write_Byte(NPAILTL_REGISTER, 0)
        self.Write_Byte(NPAILTH_REGISTER, 0)
        
        self.Write_Byte(NPAIHTL_REGISTER, 0xff)
        self.Write_Byte(NPAIHTH_REGISTER, 0xff)
        self.Disable()
  
