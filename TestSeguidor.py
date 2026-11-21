import machine
import time
from machine import Pin
from neopixel import NeoPixel

from Barra1 import Barra16
from Motores import Motores

machine.freq(240000000)

neo = NeoPixel(Pin(21, Pin.OUT), 1)

sb = Barra16(5, 4, 3, 2, 1)
drv = Motores(8,9,10,13,12,11)
drv.setVelocidad(0, 0)

btn_calibrar = Pin(6, Pin.IN, Pin.PULL_UP)
btn_inicio = Pin(7, Pin.IN, Pin.PULL_UP)

SENSOR_RANGE = 255
U_MAX = 1023.0
I_MAX = 200.0
E_I_ON = 80.0
FC_D = 25.0
TAU_D = 1.0 / (6.2831853 * FC_D)
DEBOUNCE_MS = 50


class Boton:
    def __init__(self, pin):
        self.pin = pin
        self._raw_anterior = pin.value()
        self._estado_estable = self._raw_anterior
        self._cambio_ms = time.ticks_ms()

    def presionado(self):
        raw = self.pin.value()
        ahora = time.ticks_ms()

        if raw != self._raw_anterior:
            self._raw_anterior = raw
            self._cambio_ms = ahora

        if (raw != self._estado_estable and
                time.ticks_diff(ahora, self._cambio_ms) >= DEBOUNCE_MS):
            self._estado_estable = raw
            return self._estado_estable == 1

        return False


def indicar_color(color):
    neo.fill(color)
    neo.write()


def main():
    # Parámetros editables del seguidor: P, I, D, velocidad, KF y KB.
    kp = 2.4
    ki = 0.4
    kd = 0.08
    vm = 300
    kf = 0.6
    kb = 0.8

    Iacc = 0.0
    d_filt = 0.0
    e_prev = 0.0
    t_prev_us = time.ticks_us()

    boton_calibrar = Boton(btn_calibrar)
    boton_inicio = Boton(btn_inicio)
    calibrada = False
    ejecutando = False

    # Ámbar: esperando calibración.
    indicar_color((20, 10, 0))

    while True:
        if boton_calibrar.presionado():
            drv.setVelocidad(0, 0)
            ejecutando = False
            indicar_color((15, 35, 0))
            sb.calibrar(veces=5000)
            calibrada = True
            indicar_color((0, 30, 0))

        if boton_inicio.presionado():
            if ejecutando:
                ejecutando = False
                drv.setVelocidad(0, 0)
                indicar_color((0, 30, 0))
            elif calibrada:
                ejecutando = True
                indicar_color((0, 0, 30))
            else:
                indicar_color((20, 10, 0))

        if ejecutando:
            # 1) Calcular dt ─────────────────────────────────────
            t_now = time.ticks_us()
            dt = time.ticks_diff(t_now, t_prev_us) * 1e-6
            t_prev_us = t_now

            if dt < 0.0005:
                dt = 0.0005
            elif dt > 0.02:
                dt = 0.02

            # 2) Leer posición y definir error ────────────────────
            pos = sb.getPos(SENSOR_RANGE)
            pos = max(-255, min(pos, 255))
            e = float(pos)

            # 3) Derivada filtrada (band-limited) ─────────────────
            d_raw = (e - e_prev) / dt
            alpha_d = dt / (TAU_D + dt)
            d_filt += alpha_d * (d_raw - d_filt)

            e_prev = e

            # 4) Integral con anti-windup ─────────────────────────
            enable_I = abs(e) < E_I_ON
            if enable_I:
                Iacc = Iacc + (e * dt)
                if Iacc > I_MAX:
                    Iacc = I_MAX
                if Iacc < -I_MAX:
                    Iacc = -I_MAX
            else:
                Iacc = Iacc * 0.995

            # 8) PID + saturación ─────────────────────────────────
            u = kp * e + ki * Iacc + kd * d_filt

            if u > U_MAX:
                u = U_MAX
            if u < - U_MAX:
                u = - U_MAX

            # 9) Freno dinámico (como en Arduino) y derivativo ────
            pot = e / 10.0
            pot = pot * pot
            base = vm - abs(kf * pot) - abs(kb * 0.1 * d_filt)

            pid_val = int(round(u))
            velFin = int(round(base))

            # 10) Actualización de motores ────────────────────────
            mot_izq = velFin - pid_val
            mot_der = velFin + pid_val

            drv.setVelocidad(mot_izq, mot_der)
        else:
            time.sleep_ms(10)


if __name__ == '__main__':
    main()