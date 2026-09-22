"""Behavioral regression gates for the verified 10.31 release."""
import inspect
import unittest
from PIL import Image
from maha_id_studio import application as app


class Release1031Tests(unittest.TestCase):
    def test_splash_preserves_aspect_ratio_without_borders(self):
        source=Image.new("RGB",(1600,900),"red")
        rendered=app.cinematic_splash(source,(1200,700))
        self.assertEqual(rendered.size,(1200,700))
        self.assertEqual(rendered.getpixel((0,0))[:3],(255,0,0))
        self.assertIn("ImageOps.fit",inspect.getsource(app.cinematic_splash))

    def test_review_dialog_has_scroll_and_fixed_actions(self):
        source=inspect.getsource(app.photo_review_dialog)
        for text in ("Scrollbar","FIX SELECTED PHOTO","CONFIRM PHOTO BOUNDARY","REVIEW ALL","CONTINUE WITHOUT FIXING","CANCEL","<Escape>","<Return>"):
            self.assertIn(text,source)

    def test_final_output_dialog_has_required_formats(self):
        source=inspect.getsource(app.final_output_dialog)
        for text in ("FILE NAME","OUTPUT FOLDER","JPG","JPEG","PNG","TIFF","BMP","WEBP","PDF","SAVE OUTPUT","OPEN OUTPUT FOLDER","CANCEL"):
            self.assertIn(text,source)

    def test_card_refinement_rejects_oversized_neighbor_contour(self):
        source=inspect.getsource(app.refine_card_box)
        self.assertIn("bw>sw*1.16",source)
        self.assertIn("bh>sh*1.16",source)
        self.assertIn("distance>.34",source)

    def test_raster_save_is_verified_and_atomic(self):
        source=inspect.getsource(app.save_image_max)
        self.assertIn(".partial",source)
        self.assertIn("check.verify()",source)
        self.assertIn("os.replace",source)

    def test_crop_window_has_fixed_commit_exit_and_apply_all_photos(self):
        source=inspect.getsource(app.FastCropWindow)
        for text in ("APPLY CHANGES & EXIT","EXIT WITHOUT CHANGES","APPLY TO ALL PHOTOS","def apply_to_all_photos"):
            self.assertIn(text,source)
        method=inspect.getsource(app.FastCropWindow.apply_to_all_photos)
        self.assertIn('["photo"]',method)
        self.assertNotIn('target["boxes"]',method)

    def test_photo_box_maps_proportionally_to_selected_cards(self):
        self.assertEqual(app.map_relative_box((20,30,60,90),(0,0,100,120),(100,200,300,440)),(140,260,220,380))
        with self.assertRaises(ValueError):app.map_relative_box((-1,30,60,90),(0,0,100,120),(0,0,200,240))
        source=inspect.getsource(app.FastCropWindow.apply_photo_box_to_all)
        self.assertIn("photo_box_batch_preview_dialog",source)
        self.assertIn("photo_box_manual",source)

    def test_photo_box_batch_safety_workflow(self):
        image=Image.new("RGB",(400,250),"white")
        source={"page":image,"boxes":{"front":(10,10,310,200)}}
        matching={"page":image.copy(),"boxes":{"front":(20,20,320,210)}}
        wrong={"page":image.copy(),"boxes":{"front":(20,20,190,210)}}
        self.assertTrue(app.matching_photo_layout(source,matching))
        self.assertFalse(app.matching_photo_layout(source,wrong))
        preview=inspect.getsource(app.photo_box_batch_preview_dialog)
        for text in ("PREVIEW BEFORE APPLY","Scrollbar","APPLY TO MATCHING CARDS","Different Layout Card(s) Skip Honge"):
            self.assertIn(text,preview)
        crop=inspect.getsource(app.FastCropWindow)
        for text in ("SAVE PHOTO BOX PRESET","LOAD PHOTO BOX PRESET","UNDO APPLY TO ALL","photo_box_presets","bulk_photo_box_undo"):
            self.assertIn(text,crop)


if __name__=="__main__":unittest.main()
