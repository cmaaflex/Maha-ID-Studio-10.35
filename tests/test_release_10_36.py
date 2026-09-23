import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf
from maha_id_studio import application as app


class Release1036Tests(unittest.TestCase):
    def test_pdf_cancel_stops_before_next_page(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pages.pdf'
            doc=pymupdf.open()
            for _ in range(3):doc.new_page(width=72,height=72)
            doc.save(path);doc.close()
            stop=threading.Event();progress=[]
            def report(page,total):
                progress.append((page,total));stop.set()
            pages=app.render_source_pages(path,cancel_event=stop,progress=report)
            self.assertEqual(len(pages),1)
            self.assertEqual(progress,[(1,3)])

    def test_enhancements_and_recovery_survive_new_instance(self):
        with tempfile.TemporaryDirectory() as folder:
            first=app.MahaIDApp.__new__(app.MahaIDApp)
            first.config_path=Path(folder)/'settings.json'
            data={'enhancement_presets':{'Photo':{'Brightness':12}},'recovery':{'mode':'a4','items':[]}}
            self.assertTrue(first.write_settings(data))
            second=app.MahaIDApp.__new__(app.MahaIDApp);second.config_path=first.config_path
            self.assertEqual(second.read_settings(),data)

    def test_version(self):
        self.assertEqual(app.APP_VERSION,'10.36')


if __name__=='__main__':unittest.main()
