from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory

# Setze die Pin-Factory global auf PiGPIOFactory (benötigt pigpiod)
Device.pin_factory = PiGPIOFactory()

DoorSensor = None  # Globale Variable initialisieren

def sensor_ausgeloest():
    print("🚪 Tür wurde geöffnet – Sensor ausgelöst!")
    # Später: Foto aufnehmen & speichern

def init_sensor():
    global DoorSensor
    # Button mit der definierten Factory initialisieren
    DoorSensor = Button(17)
    DoorSensor.when_pressed = sensor_ausgeloest
    print("Magnetsensor ist aktiv.")
