import datetime
import os
from picamera import PiCamera

class CameraHandler:
    def __init__(self, save_dir="photos"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def take_picture(self):
         camera = PiCamera()
         filename = self._generate_filename()
         camera.capture(filename)
         camera.close()

        filename = self._generate_filename()
        print(f"Foto aufgenommen: {filename}")
        # Simuliere Fotoaufnahme durch eine leere Datei:
        with open(filename, "w") as f:
            f.write("Simuliertes Foto\n")

    def _generate_filename(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.save_dir, f"photo_{timestamp}.jpg")
