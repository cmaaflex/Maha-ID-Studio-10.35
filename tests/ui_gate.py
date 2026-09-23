"""Instrumented Tk gate: no Windows settings or real printer jobs are changed."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
import time
from tkinter import Tk
from unittest.mock import patch
from maha_id_studio import application as app
from maha_id_studio.printing import print_dialog
from test_release_10_34 import item


def run():
    failures=[]
    with tempfile.TemporaryDirectory() as folder:
        configurations=[(scale,size) for size in ('1366x768','1920x1080','2560x1440') for scale in (1.,1.25,1.5,1.75,2.)]
        for index,(scale,size) in enumerate(configurations):
            print(f'Checking {size} at {scale*100:g}%',flush=True)
            root=Tk();root.withdraw();root.tk.call('tk','scaling',scale*96/72)
            root.report_callback_exception=lambda *args:failures.append(str(args[1]))
            with patch.object(app.MahaIDApp,'show_splash',lambda self:None),patch.object(app.MahaIDApp,'get_config_path',lambda self:Path(folder)/'settings.json'):
                instance=app.MahaIDApp(root)
            root.state('normal');root.geometry(size+'+0+0');root.deiconify();root.update()
            instance._render_premium_home();root.update()
            assert instance._premium_scale>0
            cards=[item(),item()]
            review=app.BatchReview(instance,cards,('4x6','a4','a4back','a4pair4','a4pair5')[index%5])
            review.window.state('normal');review.window.geometry(size+'+0+0');root.update()
            assert review.selected_indices()==(0,) and review.has_selection
            review.step(1);root.update();review.draw();root.update()
            assert review.selected_indices()==(1,)
            for button in review.selection_buttons:
                if button.winfo_ismapped():
                    assert button.winfo_width()>40 and button.winfo_height()>10
                    assert button.winfo_rooty()+button.winfo_height()<=review.window.winfo_rooty()+review.window.winfo_height()
            review.clear_selection();root.update();assert review.selected_indices()==()
            crop=app.FastCropWindow(instance,cards[0],lambda:None,parent=review.window)
            crop.window.state('normal');crop.window.geometry(size+'+0+0');root.update()
            crop.fit_view();crop.scale=4.;crop.render_page();root.update()
            assert crop.photo.width()<=crop.canvas.winfo_width()+370
            assert crop.photo.height()<=crop.canvas.winfo_height()+370
            crop.boxes['photo']=(55,95,215,325);crop.confirm_photo_boundary();crop.apply()
            until=time.monotonic()+10
            while crop.window.winfo_exists() and time.monotonic()<until:root.update();time.sleep(.02)
            assert not crop.window.winfo_exists(),'Crop processing did not finish'
            assert not app.needs_photo_review(cards[0])
            with patch.object(app,'available_windows_printers',lambda:[]):
                print_dialog(instance,review.window,[app.make_4x6(cards[0]['front'],cards[0]['back'])])
                root.update()
            dialogs=[w for w in review.window.winfo_children() if w.winfo_class()=='Toplevel']
            assert dialogs and dialogs[-1].winfo_height()>200
            dialogs[-1].destroy()
            for token in root.tk.splitlist(root.tk.call('after','info')):root.tk.call('after','cancel',token)
            root.destroy()
    assert not failures,failures
    print('UI gate passed: 1366x768, 1920x1080, 2560x1440 at 100/125/150/175/200% Tk scaling; five layouts, empty selection, crop confirmation, 400% zoom, async apply and print dialog.')


if __name__=='__main__':run()
