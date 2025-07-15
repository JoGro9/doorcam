from gpiozero import Device, Button
from gpiozero.pins.pigpio import PiGPIOFactory

Device.pin_factory = PiGPIOFactory()

def sensor_ausgeloest():
    print("Tür wurde geöffnet – Sensor ausgelöst.")


def sensor_geschlossen():
    print("Tür wurde geschlossen – Sensor verbunden.")

def init_sensor():
    sensor = Button(17, pull_up=True)

    def check_status():
        # Wurde Tür gerade geöffnett?
        if not sensor.is_pressed:
            print("Tür geöffnet")
            mache_fotos_und_erkenne_gesicht()
        else:
            print("Tür geschlossen")

    sensor.when_pressed = check_status  # Tür zu
    sensor.when_released = check_status  # Tür auf
    print("Magnetsensor ist aktiv.")
    return sensor
