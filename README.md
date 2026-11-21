# Seguidor de Líneas de Competición (PID Control)

Robot autónomo diseñado para competencias a nivel federal, optimizado para seguir trayectorias a alta velocidad. El sistema integra hardware de procesamiento rápido y algoritmos de control de lazo cerrado para garantizar precisión en la lectura de sensores y respuesta de motores.

## Hardware y Arquitectura
*   **Microcontrolador:** ESP32-S3-ZERO (Seleccionado por su alto rendimiento y capacidades de procesamiento).
*   **Sensores:*Barra de sensores infrarojos, sensores de velocidad, * .
*   **Actuadores:*Motores n20 controlados gracias a un puente H (TB6612FNG).

## Lógica y Software
*   **Lenguaje:** MicroPython (Python).
*   **Control PID:** Implementación de un algoritmo Proporcional, Integral y Derivativo para calcular el error de posición en tiempo real y ajustar dinámicamente la velocidad de los motores, minimizando oscilaciones en curvas cerradas.
