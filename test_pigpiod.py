from gpiozero import Device
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import Button
import time

Device.pin_factory = PiGPIOFactory()

button = Button(17)

print("Starte Test - bitte Taste drücken")

button.wait_for_press()
print("Taste gedrückt!")
