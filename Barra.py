from machine import Pin, ADC


class Barra:
    # Constructor for the Barra class.
    def __init__(self, s3,s2,s1,s0,out):
        self._s3 = Pin(s3, Pin.OUT)
        self._s2 = Pin(s2, Pin.OUT)
        self._s1 = Pin(s1, Pin.OUT)
        self._s0 = Pin(s0, Pin.OUT)
        #UMBRAL
        self._umbral=[0]*16
        #POSICION
        self._lastPos = 0
        #AMPLIAR EL RANGO DEL ADC A 3.3V
        self._out = ADC(Pin(out), atten=ADC.ATTN_11DB) 

    def _read(self,x):
        # Set the state of the select pins based on the input x.
        self._s3.value((x >> 3) & 1)
        self._s2.value((x >> 2) & 1)
        self._s1.value((x >> 1) & 1)
        self._s0.value(x & 1)
        # Read and return the value from the ADC.
        return self._out.read()

    def calibrar(self, veces=3000):
        max=[0]*16
        min=[4095]*16
        for x in range(veces):
            for i in range(16):
                valor = self._read(i)
                if min[i] > valor:
                    min[i] = valor  
                if max[i] < valor:
                    max[i] = valor
        for x in range(16):
            self._umbral[x] = (max[x] + min[x]) // 2

    def _map(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

    def posicion(self, fitted=None):
        # Initialize a variable to hold the position value.
        pos = 0
        sen=0
        for x in range(16):
            valor = self._read(x)
            sen+=1 if valor > self._umbral[x] else 0
            pos += 500 *(x+1) if valor > self._umbral[x] else 0
        if fitted is None:
                self._lastPos = (pos // sen) - 4250 if sen > 0 else self._lastPos
        else:
                self._lastPos = self._map(pos // sen, 500, 8000, -fitted, fitted) if sen > 0 else self._lastPos
        return self._lastPos