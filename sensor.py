from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory

# Setze die Pin-Factory global auf PiGPIOFactory (benötigt laufenden pigpiod)
Device.pin_factory = PiGPIOFactory()

def sensor_ausgeloest():
    print("🚪 Tür wurde geöffnet – Sensor ausgelöst!")

def init_sensor():
    sensor = Button(17)
    sensor.when_pressed = sensor_ausgeloest
    print("Magnetsensor ist aktiv.")
    return sensor  # ✅ Wichtig: Sensorinstanz zurückgeben
