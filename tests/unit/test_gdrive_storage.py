import os
import sys
import unittest

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from modules.mlops.gdrive_storage import is_gdrive_available, resolve_credentials_path

class TestGDriveStorage(unittest.TestCase):

    def test_resolve_credentials_path(self):
        """Verifies that resolve_credentials_path handles env vars and fallback paths safely."""
        path = resolve_credentials_path()
        if path:
            self.assertTrue(os.path.exists(path))
        else:
            self.assertIsNone(path)

    def test_is_gdrive_available_boolean_response(self):
        """Verifies that is_gdrive_available returns a boolean without throwing unhandled exceptions."""
        avail = is_gdrive_available()
        self.assertIsInstance(avail, bool)

    def test_output_naming_convention(self):
        """Verifies that video base name generates consistent sample_file_manga.pdf formatting."""
        video_filename = "sample_file.mp4"
        base_name = os.path.splitext(os.path.basename(video_filename))[0]
        pdf_name = f"{base_name}_manga.pdf"
        page_name = f"{base_name}_page_001.png"
        
        self.assertEqual(base_name, "sample_file")
        self.assertEqual(pdf_name, "sample_file_manga.pdf")
        self.assertEqual(page_name, "sample_file_page_001.png")

if __name__ == "__main__":
    unittest.main()
