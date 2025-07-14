from gpiozero import Button

DoorSensor = Button(17)  # BCM GPIO 17 (Pin 11)

def init_sensor():
    global DoorSensor
    DoorSensor = Button(17)
    DoorSensor.when_pressed = sensor_ausgeloest
    print("Magnetsensor ist aktiv.")

def sensor_ausgeloest():
    print("🚪 Tür wurde geöffnet – Sensor ausgelöst!")
    # Später: Foto aufnehmen & speichern

