import datetime
import os
from picamera2 import Picamera2, Preview
import time

class CameraHandler:
    def __init__(self, save_dir="photos"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.picam2 = Picamera2()

        # Optional: Kamera konfigurieren
        self.picam2.configure(self.picam2.create_still_configuration())

    def take_picture(self):
        filename = self._generate_filename()
        self.picam2.start()
        time.sleep(2)  # kleine Wartezeit für Auto-Fokus/Belichtung
        self.picam2.capture_file(filename)
        self.picam2.stop()
        print(f"Foto aufgenommen: {filename}")

    def _generate_filename(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.save_dir, f"photo_{timestamp}.jpg")
