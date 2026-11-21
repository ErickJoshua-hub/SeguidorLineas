from machine import Pin, PWM

class Motores:
    def __init__(self, pwma, ain2, ain1, pwmb, bin2, bin1):
        self._pwma = PWM(Pin(pwma), freq=2000)
        self._ain2 = Pin(ain2, Pin.OUT)
        self._ain1 = Pin(ain1, Pin.OUT)
        self._pwmb = PWM(Pin(pwmb), freq=2000)
        self._bin2 = Pin(bin2, Pin.OUT)
        self._bin1 = Pin(bin1, Pin.OUT)

    def setVelocidad(self, mIzq, mDer):
        if mIzq > 1023:
            mIzq = 1023
        if mIzq < -1023:
            mIzq = -1023   
        if mDer > 1023:
            mDer = 1023
        if mDer < -1023:
            mDer = -1023
        if mIzq > 0:
            self._ain1.value(1)
            self._ain2.value(0)
            self._pwma.duty(int(mIzq))
        else:
            self._ain1.value(0)
            self._ain2.value(1)
            self._pwma.duty(int(-mIzq))
        if mDer > 0:
            self._bin1.value(1)
            self._bin2.value(0)
            self._pwmb.duty(int(mDer))
        else:
            self._bin1.value(0)
            self._bin2.value(1)
            self._pwmb.duty(int(-mDer))
