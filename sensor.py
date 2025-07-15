from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory

Device.pin_factory = PiGPIOFactory()

def sensor_ausgeloest():
    print("Tür wurde geöffnet – Sensor ausgelöst.")

def sensor_geschlossen():
    print("Tür wurde geschlossen – Sensor verbunden.")

def init_sensor():
    sensor = Button(17, pull_up=True, bounce_time=0.3)  # Entprellzeit 300 ms
    sensor.when_released = sensor_ausgeloest
    sensor.when_pressed = sensor_geschlossen
    print("Magnetsensor ist aktiv.")
    return sensor

