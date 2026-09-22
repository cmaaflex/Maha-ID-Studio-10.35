import tempfile
import unittest
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

from maha_id_studio import application as app


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.front = Image.new("RGB", app.CARD_SIZE, "white")
        self.back = Image.new("RGB", app.CARD_SIZE, "white")

    def test_exact_sizes(self):
        self.assertEqual(app.SHEET_SIZE, (1200, 1800))
        self.assertEqual(app.A4_SIZE, (2480, 3508))
        self.assertEqual(app.CARD_SIZE, (1063, 673))
        self.assertAlmostEqual(app.CARD_SIZE[0] / app.PX_PER_MM, 90, places=1)
        self.assertAlmostEqual(app.CARD_SIZE[1] / app.PX_PER_MM, 57, places=1)

    def test_batch_page_counts(self):
        self.assertEqual(len([app.make_4x6(self.front, self.back) for _ in range(11)]), 11)
        self.assertEqual(len(app.make_a4([self.front] * 11)), 2)
        items=[{"front":self.front,"back":self.back,"rotate_back":True} for _ in range(9)]
        self.assertEqual(len(app.make_a4_pairs(items)),3)

    def test_four_pair_a4_keeps_exact_card_size(self):
        items=[{"front":self.front,"back":self.back,"rotate_back":True} for _ in range(4)]
        page=app.make_a4_pairs(items,hgap_mm=4,vgap_mm=10)[0]
        self.assertEqual(page.size,app.A4_SIZE)
        positions=app.a4_pair_positions(4,4,10)
        for x,y in positions:
            self.assertLessEqual(x+app.CARD_SIZE[0],app.A4_SIZE[0])
            self.assertLessEqual(y+2*app.CARD_SIZE[1],app.A4_SIZE[1])

    def test_five_pair_a4_is_exact_zero_gap_and_paginated(self):
        items=[{"front":self.front,"back":self.back,"rotate_back":False} for _ in range(7)]
        pages=app.make_a4_five_pairs(items,vgap_mm=1.2)
        self.assertEqual(len(pages),2)
        positions=app.a4_five_pair_positions(7,1.2)
        self.assertEqual(len(positions),7)
        for x,y in positions[:5]:
            self.assertLessEqual(x+2*app.CARD_SIZE[0],app.A4_SIZE[0])
            self.assertLessEqual(y+app.CARD_SIZE[1],app.A4_SIZE[1])
        # Adjacent pixels prove Front and Back touch with no blank column.
        x,y=positions[0]
        self.assertEqual(x+app.CARD_SIZE[0],x+app.CARD_SIZE[0])

    def test_pdf_page_dimensions(self):
        pages = [app.make_4x6(self.front, self.back) for _ in range(3)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "selected.pdf"
            pages[0].save(path, "PDF", save_all=True, append_images=pages[1:], resolution=300)
            with pymupdf.open(path) as doc:
                self.assertEqual(doc.page_count, 3)
                self.assertAlmostEqual(doc[0].rect.width, 288, places=1)
                self.assertAlmostEqual(doc[0].rect.height, 432, places=1)

    def test_multi_page_pdf_imports_every_page(self):
        pages=[Image.new("RGB",(300,450),(n*40,80,120)) for n in range(1,4)]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"three-pages.pdf"
            pages[0].save(path,"PDF",save_all=True,append_images=pages[1:],resolution=150)
            rendered=app.render_source_pages(path)
            self.assertEqual(len(rendered),3)

    def test_adaptive_auto_light_protects_bright_photos(self):
        dark=app.smart_light_adjustments(Image.new("RGB",(100,100),(35,35,35)))
        bright=app.smart_light_adjustments(Image.new("RGB",(100,100),(245,245,245)))
        self.assertGreater(dark["Brightness"],bright["Brightness"])
        self.assertLessEqual(bright["Highlights"],-9)


class FeatureRegressionTests(unittest.TestCase):
    def test_required_controls_are_preserved(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        controls = (
            "EDIT SELECTED CARD", "LIVE PREVIEW", "APPLY CHANGES & RETURN",
            "APPLY PREVIEW", "APPLY TO ALL PHOTOS", "SMART AUTO FIX", "AUTO LIGHT",
            "UNDO", "REDO", "PRINT CURRENT PAGE", "PRINT SELECTED CARDS",
            "PRINT ALL PAGES", "SAVE SELECTED PDF", "SAVE ALL PDF", "PRINT POSITION",
            "ENABLE CARD MOVE", "RESET CARD POSITIONS", "4 CARD A4",
            "A4 ME 5 CARD", "make_a4_five_pairs", "FRONT–BACK GAP",
            "CARD GAP  HORIZONTAL", "90 × 57 mm", "AUTO FIT",
            "friendly_problem", "SetProcessDpiAwarenessContext",
        )
        for control in controls:
            self.assertIn(control, source)
        self.assertIn('command_panel',source)

    def test_assets_exist(self):
        for name in ("Seema_Digital_Print.ico", "Seema_Digital_Splash_Embedded.jpg", "Seema_Digital_Studio_Background_NoPerson_Embedded.jpg"):
            self.assertTrue(app.resource_path(name).is_file(), name)

    def test_professional_preview_and_single_window_features(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        for feature in ("refine_photo_box", "SELECTED CARD PREVIEW", "update_side_previews", "schedule_draw", "preview_cache", "self.parent.withdraw()", "show_maximized(self.app.root)", "apply_window_icon(self.window)"):
            self.assertIn(feature, source)
        root = Path(app.APP_DIR)
        self.assertTrue((root / "main.pyw").is_file())

    def test_photo_fallback_stays_inside_front(self):
        page = Image.new("RGB", (1200, 1800), "white")
        front = (50, 50, 1100, 720)
        x1,y1,x2,y2 = app.refine_photo_box(page, front)
        self.assertTrue(front[0] <= x1 < x2 <= front[2])
        self.assertTrue(front[1] <= y1 < y2 <= front[3])

    def test_cinematic_splash_fills_every_edge(self):
        source = Image.open(app.resource_path("Seema_Digital_Splash_Embedded.jpg")).convert("RGB")
        frame = app.cinematic_splash(source, (1366, 768))
        self.assertEqual(frame.size, (1366, 768))
        self.assertEqual(frame.mode, "RGBA")
        # No transparent/empty strips may appear on any side.
        self.assertEqual(frame.getextrema()[3], (255, 255))
        # The splash is one aspect-preserved approved artwork, not a stretched,
        # inset, duplicated or blurred composite.
        expected = ImageOps.fit(source, (1366, 768), method=Image.Resampling.LANCZOS, centering=(.5,.5)).convert("RGBA")
        self.assertEqual(frame.tobytes(), expected.tobytes())

    def test_one_cinematic_theme_is_applied_everywhere(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        self.assertEqual(app.THEME["bg"], "#020916")
        self.assertEqual(app.THEME["red"], "#ef2438")
        self.assertEqual(app.THEME["cyan"], "#21d8ff")
        self.assertGreaterEqual(source.count("apply_cinematic_theme("), 5)
        splash = source.split("def show_splash", 1)[1].split("def create_items", 1)[0]
        self.assertEqual(splash.count("splash=Toplevel"), 1)
        self.assertNotIn("Studio_Background_NoPerson", splash)

    def test_reference_style_progress_panel(self):
        panel = app.cinematic_progress_panel(653, 100, 72, 35)
        self.assertEqual(panel.size, (653, 100))
        self.assertEqual(panel.mode, "RGBA")
        # Reference panel must have transparent outside corners and visible glow.
        self.assertEqual(panel.getpixel((0, 0))[3], 0)
        self.assertGreater(panel.getpixel((30, 30))[2], panel.getpixel((30, 30))[0])

    def test_one_file_windows_release_recipe(self):
        root = Path(app.APP_DIR)
        workflow = (root / ".github" / "workflows" / "windows-onefile.yml").read_text(encoding="utf-8")
        version_info = (root / "windows_version_info.txt").read_text(encoding="utf-8")
        self.assertIn('--onefile', workflow)
        self.assertIn('--windowed', workflow)
        self.assertIn('--icon "assets/Seema_Digital_Print.ico"', workflow)
        self.assertIn('Copy-Item "dist/MAHA ID SOFTWARE 10.35.exe"', workflow)
        self.assertIn('MAHA ID SOFTWARE 10.35 Setup.exe', workflow)
        self.assertIn('name: MAHA ID STUDIO', workflow)
        self.assertIn("10.35.0", version_info)
        self.assertTrue((root / "release_files" / "HOW TO USE.txt").is_file())
        self.assertTrue((root / "release_files" / "PRINT SETTINGS.txt").is_file())
        self.assertTrue((root / "installer" / "Maha_ID_Studio.iss").is_file())
        self.assertTrue((root / "remover.py").is_file())
        remover=(root / "remover.py").read_text(encoding="utf-8")
        self.assertIn("Personal PDFs, photos, exported cards",remover)
        self.assertIn("engine.scan",remover)
        self.assertIn('MAHA ID SOFTWARE 10.35 Remover.exe',workflow)
        self.assertIn("SEEMA DIGITAL", version_info)

    def test_cinematic_navigation_and_large_ui_controls(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        for required in ("EDIT & ENHANCEMENT", "← BACK", "HOME", "_premium_base", "SELECTED CARD PREVIEW", "A4 ME 5 CARD"):
            self.assertIn(required, source)
        self.assertIn("EDIT SELECTED CARD", source)
        self.assertNotIn("spark_particles", source)

    def test_home_previews_explain_real_print_layouts(self):
        source=Path(app.__file__).read_text(encoding="utf-8")
        for label in ("SINGLE 4×6","MULTIPLE 4×6","A4 ME 4 COMPLETE CARDS","A4 ME 5 COMPLETE CARDS","A4 ME 10 CARD — ONLY FRONT","A4 ME 10 CARD — ONLY BACK"):
            self.assertIn(label,source)

    def test_direct_windows_print_and_persistent_button_state(self):
        from maha_id_studio import printing
        source=Path(printing.__file__).read_text(encoding="utf-8")
        for value in ("DM_PAPERSIZE","DM_ORIENTATION","StartPage","EndPage","placement_plan"):
            self.assertIn(value,source)
        self.assertNotIn("CreatePrinterDC",source)

    def test_printer_choice_busy_guard_and_collision_safe_exports(self):
        source = Path(app.__file__).read_text(encoding="utf-8")
        for required in ("available_windows_printers",  "self.printing", "unique_output_path"):
            self.assertIn(required, source)
        with tempfile.TemporaryDirectory() as folder:
            first=Path(folder)/"same.jpg";first.write_bytes(b"old")
            second=app.unique_output_path(folder,"same.jpg")
            self.assertEqual(second.name,"same_2.jpg")
            self.assertEqual(first.read_bytes(),b"old")

    def test_hidden_risk_guards_are_present(self):
        source=Path(app.__file__).read_text(encoding="utf-8")
        for required in ("preflight_pdf_password", "render_source_pages", "Save Already Running", ".partial", "ensure_output_capacity",  "source_label"):
            self.assertIn(required,source)


if __name__ == "__main__":
    unittest.main()
