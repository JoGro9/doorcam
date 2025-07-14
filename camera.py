# camera.py
from picamera import PiCamera
from datetime import datetime
from time import sleep
import os

class CameraHandler:
    def __init__(self):
        self.camera = PiCamera()
        self.camera.resolution = (1024, 768)
        self.image_dir = "/home/toodles999/doorcam/images"
        os.makedirs(self.image_dir, exist_ok=True)

    def take_picture(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        image_path = os.path.join(self.image_dir, f"doorcam_{timestamp}.jpg")
        self.camera.start_preview()
        sleep(2)  # Kamera braucht Zeit zum „warmwerden“
        self.camera.capture(image_path)
        self.camera.stop_preview()
        print(f"📸 Bild aufgenommen: {image_path}")
        return image_path
