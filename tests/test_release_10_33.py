"""SEEMA DIGITAL MAHA ID SOFTWARE 10.35 acceptance gates."""
from pathlib import Path
import inspect, math, unittest
from maha_id_studio import application as app
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'maha_id_studio/application.py').read_text(encoding='utf-8')
class Release1033Tests(unittest.TestCase):
    def test_version(self): self.assertEqual(app.APP_VERSION,'10.35')
    def test_exact_a4_grid_geometry(self):
        pos=app.a4_grid_positions(10)
        self.assertEqual(len(pos),10)
        self.assertAlmostEqual(pos[0][0]/app.PX_PER_MM,10,delta=.08)
        self.assertAlmostEqual((pos[1][0]-pos[0][0]-app.CARD_SIZE[0])/app.PX_PER_MM,10,delta=.08)
        self.assertAlmostEqual(pos[0][1]/app.PX_PER_MM,3,delta=.08)
        self.assertAlmostEqual((pos[2][1]-pos[0][1]-app.CARD_SIZE[1])/app.PX_PER_MM,1.5,delta=.08)
    def test_pdf_uses_physical_a4(self):
        code=inspect.getsource(app.MahaIDApp.save_pdf_async)
        self.assertIn('210.0*72/25.4',code);self.assertIn('297.0*72/25.4',code)
        self.assertIn('image.size==A4_SIZE',code)
    def test_home_is_aspect_safe_contain(self):
        code=inspect.getsource(app.MahaIDApp._render_premium_home)
        self.assertIn('min(usable_w/base.width,usable_h/base.height)',code)
        self.assertIn('safe_x',code);self.assertIn('safe_y',code)
    def test_photo_review_gate(self):
        self.assertIn('"photo_review":photo_confidence<85',SOURCE)
        self.assertIn('REVIEW PHOTO',SOURCE)
if __name__=='__main__': unittest.main()
