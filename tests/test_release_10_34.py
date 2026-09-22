import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image, ImageDraw
from maha_id_studio import application as app
from maha_id_studio import printing as pr
from maha_id_studio.detection import PRESETS


def device(w=210, h=297, dpi_x=600, dpi_y=600, margin=0):
    width, height = round(w*dpi_x/25.4), round(h*dpi_y/25.4)
    mx, my = round(margin*dpi_x/25.4), round(margin*dpi_y/25.4)
    return pr.Device(dpi_x,dpi_y,width,height,width-2*mx,height-2*my,mx,my)


def item():
    page=Image.new('RGB',(800,1000),'white')
    boxes={'front':(20,20,700,460),'back':(20,500,700,940),'photo':(50,90,220,330)}
    return {'page':page,'path':Path('demo.png'),'boxes':boxes,'original_boxes':copy.deepcopy(boxes),
            'front':page.crop(boxes['front']),'back':page.crop(boxes['back']),'photo':page.crop(boxes['photo']),
            'photo_confidence':40,'photo_review':True}


class PrintingTests(unittest.TestCase):
    def setUp(self):
        self.page=app.make_4x6(Image.new('RGB',app.CARD_SIZE,'red'),Image.new('RGB',app.CARD_SIZE,'blue'))

    def test_4x6_layout_on_a4_does_not_force_small_paper(self):
        d=device(margin=4)
        plan=pr.placement_plan(self.page,d)
        self.assertEqual(len(plan),2)
        self.assertGreater(plan[0][1][0],1000)
        for _,(x,y,r,b) in plan:
            self.assertAlmostEqual((r-x)*25.4/d.dpi_x,90,delta=.03)
            self.assertAlmostEqual((b-y)*25.4/d.dpi_y,57,delta=.03)

    def test_dpi_axes_and_landscape_are_independent(self):
        for dpi in ((300,300),(600,1200),(1200,600)):
            d=device(297,210,*dpi)
            for _,(x,y,r,b) in pr.placement_plan(self.page,d):
                self.assertAlmostEqual((r-x)*25.4/d.dpi_x,90,delta=.05)
                self.assertAlmostEqual((b-y)*25.4/d.dpi_y,57,delta=.05)

    def test_small_paper_warns_instead_of_shrinking(self):
        page=app.make_a4([Image.new('RGB',app.CARD_SIZE)]*10)[0]
        with self.assertRaisesRegex(ValueError,'do not fit'):
            pr.placement_plan(page,device(101.6,152.4))

    def test_nonprintable_margin_rejected(self):
        with self.assertRaisesRegex(ValueError,'do not fit'):
            pr.placement_plan(self.page,device(101.6,152.4,margin=10))

    def test_all_layouts_carry_exact_geometry(self):
        card=Image.new('RGB',app.CARD_SIZE)
        for pages,count in ((app.make_a4([card]*10),10),(app.make_a4_pairs([{'front':card,'back':card}]*4),8),(app.make_a4_five_pairs([{'front':card,'back':card}]*5),10)):
            self.assertEqual(len(pr.placement_plan(pages[0],device())),count)

    def test_calibration_checks_measurements(self):
        self.assertEqual(pr.calibration_factors(90,57),(1,1))
        self.assertAlmostEqual(pr.calibration_factors(88.5,57)[0],90/88.5)
        for bad in (0,-1,float('nan'),float('inf'),12):
            with self.assertRaises(ValueError):pr.calibration_factors(bad,57)

    def test_all_pages_validated_before_startdoc(self):
        dc=Mock()
        huge=app.make_a4([Image.new('RGB',app.CARD_SIZE)]*10)[0]
        with patch.object(pr,'configured_device',return_value=(dc,device(101.6,152.4),0)):
            with self.assertRaises(ValueError):pr.print_pages([self.page,huge],'test',None,'Portrait')
        dc.StartDoc.assert_not_called();dc.DeleteDC.assert_called_once()

    def test_job_uses_selected_settings_and_aborts_on_failure(self):
        dc=Mock();dc.StartPage.side_effect=RuntimeError('spool failed')
        paper=pr.Paper(9,'A4',210,297)
        with patch.object(pr,'configured_device',return_value=(dc,device(),0)) as configure:
            with self.assertRaisesRegex(RuntimeError,'spool failed'):pr.print_pages([self.page],'Canon',paper,'Landscape')
        configure.assert_called_once_with('Canon',paper,'Landscape')
        dc.AbortDoc.assert_called_once();dc.DeleteDC.assert_called_once()


class PhotoStateTests(unittest.TestCase):
    def test_manual_confirm_clears_low_confidence(self):
        card=item();self.assertTrue(app.needs_photo_review(card));app.confirm_photo(card)
        self.assertFalse(app.needs_photo_review(card))
        card['boxes']['photo']=(51,90,220,330)
        self.assertTrue(app.needs_photo_review(card))

    def test_redetect_reopens_verification(self):
        card=item();app.confirm_photo(card);app.invalidate_photo(card)
        self.assertTrue(app.needs_photo_review(card))

    def test_continue_without_fixing_keeps_all_cards(self):
        card=item();review=SimpleNamespace(items=[card],window=None)
        with patch.object(app,'photo_review_dialog',return_value={'value':'CONTINUE WITHOUT FIXING','index':None}):
            self.assertFalse(app.BatchReview.review_blocked(review))
        self.assertFalse(app.needs_photo_review(card))
        self.assertEqual(len(review.items),1)

    def test_invalid_confirmation_rejected(self):
        card=item();card['boxes']['photo']=(-1,20,100,200)
        with self.assertRaises(ValueError):app.confirm_photo(card)

    def test_empty_selection_never_falls_back_to_first_card(self):
        review=SimpleNamespace(index=0,list=SimpleNamespace(curselection=lambda:()),list_row_to_item={0:0})
        self.assertEqual(app.BatchReview.selected_indices(review),())

    def test_printed_photo_boundary_excludes_adjacent_text(self):
        page=Image.new('RGB',(1000,640),'#eeeeee');draw=ImageDraw.Draw(page)
        rng=np.random.default_rng(4)
        portrait=Image.fromarray(rng.integers(40,180,(270,185,3),dtype=np.uint8))
        page.paste(portrait,(60,100));draw.rectangle((60,100,244,369),outline='black',width=3)
        draw.text((265,125),'Name: Sample person',fill='black');draw.text((60,400),'DOB: 01-01-2000',fill='black')
        box,confidence=app.refine_photo_box_with_confidence(page,(0,0,1000,640))
        for actual,expected in zip(box,(60,100,245,370)):self.assertAlmostEqual(actual,expected,delta=5)
        self.assertGreaterEqual(confidence,75)

    def test_blank_photo_needs_review_and_presets_present(self):
        _,confidence=app.refine_photo_box_with_confidence(Image.new('RGB',(1000,640),'white'),(0,0,1000,640))
        self.assertLess(confidence,85);self.assertEqual(len(PRESETS),8)


if __name__=='__main__':unittest.main()
