from gpiozero import Button

def init_sensor():
    sensor = Button(17)  # BCM GPIO 17 (Pin 11)
    sensor.when_pressed = sensor_ausgeloest
    print("Magnetsensor ist aktiv.")

def sensor_ausgeloest():
    print("🚪 Tür wurde geöffnet – Sensor ausgelöst!")
    # Später: Foto aufnehmen & speichern
