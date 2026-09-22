import tempfile, unittest, threading
from pathlib import Path
from unittest.mock import patch
from maha_id_studio import removal as r, application as app

class RemovalSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.folder=self.base/'Maha ID Studio 10.35';self.folder.mkdir()
        self.exe=self.folder/'MAHA ID SOFTWARE 10.35.exe';self.exe.write_bytes(b'test app')
        self.target=r.Installation('10.35',self.folder,self.exe)
        self.registry=patch.object(r,'registry_candidates',return_value=[]);self.registry.start();self.addCleanup(self.registry.stop)
        self.backup=patch.object(r,'backup_registry',return_value=[]);self.backup.start();self.addCleanup(self.backup.stop)
    def test_only_selected_version_and_personal_files_preserved(self):
        old=self.folder/'MAHA ID SOFTWARE 10.33.exe';old.write_bytes(b'original')
        photo=self.folder/'customer.jpg';photo.write_bytes(b'personal')
        export=self.folder/'Seema Digital Print Output';export.mkdir();(export/'card.pdf').write_bytes(b'output')
        items,notes=r.scan(self.target,'Advanced');self.assertEqual([x.path for x in items],[str(self.exe)])
        result=r.delete_selected(self.target,items,'Advanced',False,False,self.base/'reports')
        self.assertEqual(len(result['removed']),1);self.assertFalse(self.exe.exists());self.assertTrue(old.exists());self.assertTrue(photo.exists());self.assertTrue((export/'card.pdf').exists())
    def test_arbitrary_candidate_is_rejected(self):
        victim=self.base/'unrelated.txt';victim.write_text('keep')
        with self.assertRaises(ValueError):r.delete_selected(self.target,[r.Candidate('File',str(victim))],'Safe',False,False,self.base)
        self.assertEqual(victim.read_text(),'keep')
    def test_changed_file_requires_rescan(self):
        items,_=r.scan(self.target);self.exe.write_bytes(b'changed file longer')
        with self.assertRaises(ValueError):r.delete_selected(self.target,items,'Safe',False,False,self.base)
    def test_zero_selection_deletes_nothing(self):
        result=r.delete_selected(self.target,[],'Safe',False,False,self.base)
        self.assertTrue(self.exe.exists());self.assertEqual(result['removed'],[])
    def test_scan_cancel_is_explicit(self):
        stop=threading.Event();stop.set();items,notes=r.scan(self.target,cancelled=stop)
        self.assertEqual(items,[]);self.assertIn('cancelled',' '.join(notes))
    def test_parent_and_sibling_paths_rejected(self):
        self.assertFalse(r.safe_child(self.folder,self.folder));self.assertFalse(r.safe_child(self.folder,self.base/'other.exe'))
        self.assertFalse(r.safe_child(self.folder,self.folder/'..'/'other.exe'));self.assertTrue(r.safe_child(self.folder,self.exe))
    def test_legacy_settings_are_never_auto_removed(self):
        old=r.Installation('10.33',self.folder,self.folder/'MAHA ID SOFTWARE 10.33.exe')
        self.assertEqual(r.settings_files(old),[]);self.assertEqual(r.shortcut_files(old),[])
    def test_uninstaller_outside_install_is_rejected(self):
        target=r.Installation('10.35',self.folder,self.exe,uninstaller='"C:\\Windows\\cmd.exe" /c anything')
        self.assertIsNone(r.built_in_uninstaller(target))
    def test_portable_selection_requires_named_exe(self):
        self.assertEqual(r.portable(self.exe).version,'10.35')
        with self.assertRaises(ValueError):r.portable(self.base/'unrelated.exe')
    def test_installer_and_settings_are_isolated(self):
        root=Path(app.APP_DIR);setup=(root/'installer/Maha_ID_Studio.iss').read_text(encoding='utf-8')
        self.assertIn('281D2A77-F8D9-45F3-A579-10350000C0DE',setup)
        self.assertIn('Maha ID Studio 10.35',setup)
        self.assertNotEqual(app.MahaIDApp.get_config_path(None).name,'Maha id settings.json')

if __name__=='__main__':unittest.main()
