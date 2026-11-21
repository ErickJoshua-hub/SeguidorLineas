from Motores import Motores
from time import sleep

# Ajustar los pines según la PCB
motores = Motores(8, 9, 10, 13, 12, 11)
motores.setVelocidad(0, 0)

while True:
    mizq = int(input("Ingrese la velocidad del motor izquierdo (-1023 a 1023): "))
    mder = int(input("Ingrese la velocidad del motor derecho (-1023 a 1023): "))
    motores.setVelocidad(mizq, mder)
