import datetime
import os
from picamera import PiCamera

class CameraHandler:
    def __init__(self, save_dir="photos"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def take_picture(self):
        filename = self._generate_filename()
        camera = PiCamera()
        try:
            camera.capture(filename)
            print(f"Foto aufgenommen: {filename}")
        finally:
            camera.close()

    def _generate_filename(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.save_dir, f"photo_{timestamp}.jpg")
