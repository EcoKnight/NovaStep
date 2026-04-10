NovaStep 🤖
Plataforma de Robótica Móvil con Estimación de Estado y Control Distribuido.
🚀 Descripción del ProyectoNovaBot es un robot diferencial avanzado que integra técnicas de Sensor Fusion y Sistemas de Tiempo Real (RTOS) para lograr una navegación precisa. El sistema separa las tareas críticas (control de motores y lectura de sensores) en el microcontrolador ESP32, mientras que el procesamiento de datos y la interfaz de usuario se gestionan de forma remota vía TCP/IP.

🛠️ Arquitectura de Software (Firmware)
El firmware está desarrollado sobre FreeRTOS, permitiendo la ejecución concurrente de tareas:
Core 0 (NetworkTask): Gestión del servidor TCP, comunicación inalámbrica y parseo de comandos.
Core 1 (Main Loop & UltrasonicTask): Ejecución del ciclo de control (50Hz) y filtrado del sensor ultrasónico.

Estimación de Estado (EKF & Fused Odometry)Para mitigar el error acumulado de la odometría, se implementaron dos niveles de filtrado:
  Filtro Complementario: Fusión de los Encoders AS5600 con el Giroscopio de la IMU MPU6050 para obtener un Yaw ($\theta$) estable.
  Filtro de Kalman Extendido (EKF): Utilizando la librería BasicLinearAlgebra, se calcula la posición $(x, y)$ y la orientación mediante un modelo de predicción cinemático y una matriz de corrección basada en la observación del sensor.

Control de Movimiento
Control PD de Velocidad: Cada rueda cuenta con un controlador Proporcional-Derivativo que ajusta el PWM para igualar la velocidad medida por los encoders con la referencia enviada por el usuario.

Manejo de Zona Muerta: Algoritmo de compensación de fricción estática para movimientos suaves a baja velocidad.

Seguridad: Implementación de un Software Watchdog que detiene el robot automáticamente ante una pérdida de conexión mayor a 1 segundo.

📡 Protocolo de Telemetría
El robot envía una cadena de datos cada 100ms con el estado completo del sistema:
POS_X, POS_Y, THETA             (Odometría pura vs EKF).
ROLL, PITCH, YAW                (Orientación absoluta).
US_DIST                         (Distancia a obstáculos filtrada).
CMD_L, CMD_R                    (Comandos enviados vs PWM aplicado).

🔌Conexiones y Hardware
Encoders: AS5600 (Dual I2C: Wire y Wire1 para evitar colisión de direcciones).
Drivers: Puente H para motores DC (PWM @ 20kHz para reducir ruido auditivo).
IMU: MPU6050 vía I2C.
Sensor de Distancia: HC-SR04 utilizando la librería NewPing.
