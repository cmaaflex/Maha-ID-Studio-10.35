"""Legacy and mode-specific rotation regression gates."""
import inspect
import unittest
from PIL import Image
from maha_id_studio import application as app


class Release1025Tests(unittest.TestCase):
    def test_back_rotation_is_mode_specific(self):
        source = inspect.getsource(app.make_4x6)
        self.assertIn("rotate_back=True", source)
        review = inspect.getsource(app.BatchReview)
        self.assertIn('get("rotate_back_4x6",True)', review)
        self.assertIn('get("rotate_back",False)', review)

    def test_home_uses_supplied_demo_cards(self):
        from maha_id_studio.home_art import compose_home,demo_card
        front=demo_card(app.ASSET_DIR)
        back=demo_card(app.ASSET_DIR,True)
        self.assertEqual(front.size,(900,570))
        self.assertEqual(back.getpixel((300,150)),(226,229,233))
        modes=[('Test','Demo',None)]*6
        home=compose_home(app.ASSET_DIR,modes)
        self.assertEqual(home.size,(1672,941))

    def test_auto_light_is_stronger_and_bounded(self):
        dark = Image.new("RGB", (120, 120), (35, 35, 35))
        values = app.smart_light_adjustments(dark)
        self.assertGreaterEqual(values["Brightness"], 15)
        self.assertGreaterEqual(values["Shadows"], 20)
        self.assertLessEqual(values["Highlights"], 0)

    def test_final_print_preview_and_printer_properties_exist(self):
        self.assertTrue(callable(app.final_print_preview))
        self.assertTrue(callable(app.open_windows_printer_properties))

    def test_progress_has_no_outer_frame(self):
        source = inspect.getsource(app.cinematic_progress_panel)
        self.assertNotIn("box=(5,5,width-5,height-5)", source)
        panel = app.cinematic_progress_panel(900, 100, 72, 10)
        self.assertEqual(panel.mode, "RGBA")
        self.assertEqual(panel.getpixel((0, 0))[3], 0)

    def test_card_size_remains_locked(self):
        self.assertEqual(app.CARD_SIZE, (1063, 673))
        page = app.make_4x6(Image.new("RGB",(400,250),"white"), Image.new("RGB",(400,250),"white"))
        self.assertEqual(page.size, app.SHEET_SIZE)


if __name__ == "__main__":
    unittest.main()
