"""Release 10.31 regression gates."""
import inspect
import unittest
from PIL import Image, ImageDraw
from maha_id_studio import application as app


class Release1027Tests(unittest.TestCase):
    def test_strong_dark_and_light_border_detector_contract(self):
        image=Image.new("RGB",(1200,800),(232,232,232));draw=ImageDraw.Draw(image)
        front=(20,20,1180,760);draw.rectangle((100,150,390,570),fill=(95,95,95),outline=(10,10,10),width=8)
        box,confidence=app.refine_photo_box_with_confidence(image,front)
        self.assertEqual(len(box),4);self.assertTrue(all(isinstance(v,int) for v in box))
        self.assertGreaterEqual(confidence,0);self.assertLessEqual(confidence,100)
        self.assertGreaterEqual(box[0],front[0]);self.assertLessEqual(box[2],front[2])

    def test_professional_grouped_ui_contract(self):
        source=inspect.getsource(app)
        for required in ("EDIT & ENHANCEMENT","PREVIEW & NAVIGATION","CARD POSITION & ROTATION",
                         "PHOTO NEEDS REVIEW","SAVE PRESET","LOAD PRESET","SAVE CHANGES",
                         "EXIT WITHOUT SAVING","PHOTO AUTO DETECTED","RE-DETECT PHOTO","RE-DETECT FRONT","RESET ALL SETTINGS","EXPORT QUALITY SETTINGS"):
            self.assertIn(required,source)

    def test_navigation_and_help_are_separate(self):
        source=inspect.getsource(app.BatchReview)
        self.assertIn("PREVIOUS",source)
        self.assertIn("NEXT",source)
        self.assertIn("SAVE FINAL OUTPUT",source)
        self.assertNotIn("PRINT SELECTED\\nSelected card print",source)

    def test_package_brand(self):
        self.assertIn("APP_VERSION",inspect.getsource(app.MahaIDApp))


if __name__=="__main__":unittest.main()
