from gpiozero import Button
from gpiozero.pins.pigpio import PiGPIOFactory
import time

factory = PiGPIOFactory()
button = Button(17, pin_factory=factory)

print("Starte Test - bitte Taste drücken")

try:
    button.wait_for_press()
    print("Taste gedrückt!")
    time.sleep(1)  # Warte, um 'held' Event auszulösen (falls genutzt)
except KeyboardInterrupt:
    print("Abbruch")

