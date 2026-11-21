from Barra import Barra
from time import sleep
#Ajustar los pines segun la PCB
sb=Barra(5, 4, 3, 2, 1)

#calibrar el sensor
sb.calibrar(5000)
#obtener la posicion del sensor
while True:
    pos = sb.posicion()
    print(pos)
    sleep(0.2)

 