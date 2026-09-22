"""Customer-visible 10.34 acceptance gates."""
from pathlib import Path
import inspect,unittest
from maha_id_studio import application as app

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"maha_id_studio/application.py").read_text(encoding="utf-8")

class Release1032Tests(unittest.TestCase):
    def test_product_version_and_exact_home_copy(self):
        self.assertEqual((app.PRODUCT_NAME,app.APP_VERSION),("MAHA ID SOFTWARE","10.35"))
        for text in ("SINGLE 4×6","Ek Maha ID Ka Front Aur Back","MULTIPLE 4×6","Ek Se Zyada Front-Back Cards Alag 4×6 Pages Par","A4 ME 4 COMPLETE CARDS","4 Complete Front-Back Cards Ek A4 Page Par","A4 ME 5 COMPLETE CARDS","5 Complete Front-Back Cards Ek A4 Page Par","A4 ME 10 CARD — ONLY FRONT","10 Front Cards Ek A4 Page Par","A4 ME 10 CARD — ONLY BACK","10 Back Cards Ek A4 Page Par"):self.assertIn(text,SOURCE)
    def test_hover_geometry_is_fixed(self):
        code=inspect.getsource(app.apply_cinematic_theme)+inspect.getsource(app.select_cinematic_button)
        self.assertNotIn("bd=4",code);self.assertNotIn('relief="sunken"',code);self.assertIn("_cinematic_persistent",code)
    def test_native_printer_and_center_loader(self):
        printer=inspect.getsource(app.open_windows_printer_properties);self.assertNotIn("PrinterProperties",printer);self.assertTrue("DocumentProperties" in printer or "PrintUIEntry" in printer)
        loader=inspect.getsource(app.CenterProcessingOverlay)
        for text in ("CANCEL PROCESSING","READING PDF","DETECTING CARDS","DETECTING PHOTOS","CREATING PREVIEW","PREPARING OUTPUT","SENDING TO PRINTER"):self.assertIn(text,loader)
    def test_splash_remains_horizontal(self):
        code=inspect.getsource(app.MahaIDApp.show_splash);self.assertIn("cinematic_progress_panel",code);self.assertNotIn("CenterProcessingOverlay",code)
    def test_exact_release_filename(self):
        data="".join((ROOT/p).read_text(encoding="utf-8") for p in (".github/workflows/windows-onefile.yml","installer/Maha_ID_Studio.iss","windows_version_info.txt"))
        for text in ("MAHA ID SOFTWARE 10.35.exe","MAHA ID SOFTWARE 10.35 Setup.exe","MAHA ID SOFTWARE 10.35.zip"):self.assertIn(text,data)

if __name__=="__main__":unittest.main()
