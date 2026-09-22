from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"maha_id_studio/application.py").read_text(encoding="utf-8")
REMOVER=(ROOT/"remover.py").read_text(encoding="utf-8")

class Release1030Tests(unittest.TestCase):
    def test_final_home_tile_contract(self):
        for value in ("SINGLE 4×6","Ek Maha ID Ka Front Aur Back","MULTIPLE 4×6","Ek Se Zyada Front-Back Cards Alag 4×6 Pages Par","A4 ME 4 COMPLETE CARDS","4 Complete Front-Back Cards Ek A4 Page Par","A4 ME 5 COMPLETE CARDS","5 Complete Front-Back Cards Ek A4 Page Par","A4 ME 10 CARD — ONLY FRONT","10 Front Cards Ek A4 Page Par","A4 ME 10 CARD — ONLY BACK","10 Back Cards Ek A4 Page Par"):
            self.assertIn(value,APP)

    def test_startup_does_not_show_root_before_splash(self):
        self.assertIn("root.withdraw();full_screen(root)",APP)
        self.assertIn("splash=Toplevel(self.root);splash.withdraw()",APP)
        self.assertIn('label="STARTING"',APP);self.assertIn('"LOADING PRESETS"',APP);self.assertIn('"READY"',APP)
        self.assertIn("step<60:splash.after(35",APP);self.assertNotIn("step<100:splash.after(100",APP)

    def test_home_background_is_low_cost_and_cached(self):
        section=APP[APP.index("def home_background"):APP.index("def action_group")]
        self.assertIn("_HOME_BACKGROUND_CACHE={}",APP);self.assertIn("gw,gh=min(w,320),min(h,180)",APP);self.assertNotIn("for y in range(h):",section)

    def test_batch_uses_refined_card_crop(self):
        batch=APP[APP.index("def _process_source_path"):APP.index("def load_paths_async")]
        self.assertIn("refine_card_box(page,front_seed)",batch);self.assertIn("refine_card_box(page,back_seed)",batch)

    def test_review_blocks_low_confidence_output(self):
        self.assertIn("def review_blocked",APP);self.assertIn("PHOTO REVIEW REQUIRED",APP)
        self.assertIn("if self.review_blocked(chosen):return",APP);self.assertIn("if self.review_blocked():return",APP)

    def test_front_only_export_does_not_generate_back_pages(self):
        start=APP.index('elif mode=="a4":',APP.index("def export_async"));end=APP.index("\n                else:",start);branch=APP[start:end]
        self.assertIn("A4_FRONT",branch);self.assertNotIn("A4_BACK",branch)

    def test_remover_has_explicit_version_and_background_queue(self):
        for value in ('master=root,value=False','self.events=queue.Queue()','engine.scan','Delete Selected','Skip leftovers?'):
            self.assertIn(value,REMOVER)

if __name__=="__main__":unittest.main()
