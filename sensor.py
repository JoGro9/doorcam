from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory

# Setze die Pin-Factory global auf PiGPIOFactory (benötigt laufenden pigpiod)
Device.pin_factory = PiGPIOFactory()

def sensor_ausgeloest():
    print("Tür wurde geöffnet – Sensor ausgelöst.")

def sensor_geschlossen():
    print("Tür wurde geschlossen – Sensor verbunden.")

def init_sensor():
    # pull_up=True: Pin ist HIGH, wenn Sensorkontakt offen ist (Tür offen)
    sensor = Button(17, pull_up=True)
    sensor.when_released = sensor_ausgeloest  # Tür geöffnet
    sensor.when_pressed = sensor_geschlossen  # Tür geschlossen
    print("Magnetsensor ist aktiv.")
    return sensor
