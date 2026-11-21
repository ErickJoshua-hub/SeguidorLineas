from machine import Pin, ADC

# LUT de posiciones (precomputado, evita 16 multiplicaciones por getPos)
_POS = (500, 1000, 1500, 2000, 2500, 3000, 3500, 4000,
        4500, 5000, 5500, 6000, 6500, 7000, 7500, 8000)

class Barra16:

    def __init__(self, s3, s2, s1, s0, out):
        self._s0 = Pin(s0, Pin.OUT)
        self._s1 = Pin(s1, Pin.OUT)
        self._s2 = Pin(s2, Pin.OUT)
        self._s3 = Pin(s3, Pin.OUT)
        self._out = ADC(Pin(out), atten=ADC.ATTN_11DB)
        self._umbral = [0] * 16
        self._raw = [0] * 16
        self._lastPos = -1

    # --- LECTURA DE UN CANAL (single underscore evita name mangling) ----------
    def _read(self, x):
        self._s0.value(x & 1)
        self._s1.value((x >> 1) & 1)
        self._s2.value((x >> 2) & 1)
        self._s3.value((x >> 3) & 1)
        return self._out.read_u16()

    # --- POSICIÓN PONDERADA ---------------------------------------------------
    def getPos(self, fitted=None):
        pos = 0
        sen = 0
        for x in range(16):
            if self._read(x) > self._umbral[x]:
                sen += 1
                pos += _POS[x]
        if sen:
            p = pos / sen
            if fitted is None:
                self._lastPos = p - 4250
            else:
                self._lastPos = (p - 4250) * fitted / 3750
        return self._lastPos

    # --- LECTURA CRUDA DE LOS 16 SENSORES ------------------------------------
    def getRaw(self):
        for x in range(16):
            self._raw[x] = self._read(x)
        return self._raw

    # --- CALIBRACIÓN (encuentra el umbral óptimo de cada sensor) --------------
    def calibrar(self, veces=10000):
        _mx = [0] * 16
        _mn = [65535] * 16
        for _ in range(veces):
            for x in range(16):
                v = self._read(x)
                if v < _mn[x]:
                    _mn[x] = v
                if v > _mx[x]:
                    _mx[x] = v
        for x in range(16):
            self._umbral[x] = (_mx[x] + _mn[x]) >> 1