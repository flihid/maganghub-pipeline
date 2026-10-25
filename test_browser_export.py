import json
import tempfile
import unittest
from pathlib import Path

import config
from import_browser_export import import_export


class ImportTests(unittest.TestCase):
    def fixture(self):
        return {'schema':'maganghub-x-export-v1', 'exportedAt':'2026-10-25T00:00:00Z',
                'state':{'config':{'phases':[dict(name=k,since=s,until=u) for k,(s,u) in config.JENDELA_WAKTU.items()]}, 'logs':[]},
                'posts':[{'tweet_id':'1000000000000000001','username':'synthetic_fixture',
                          'text':'Data sintetis pengujian, bukan hasil penelitian.',
                          'created_at':'2026-09-20T17:30:00Z','fase':'fase1_pengumuman'}]}

    def test_import_idempotent_and_phase_uses_wib(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'raw'; file=Path(d)/'export.json'; data=self.fixture()
            data['posts']*=2
            file.write_text(json.dumps(data),encoding='utf-8')
            self.assertEqual(import_export(file,root)['added'],1)
            self.assertEqual(import_export(file,root)['added'],0)
            rows=(root/'x_fase3_penempatan.jsonl').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(rows),1)
            self.assertEqual(json.loads(rows[0])['fase'],'fase3_penempatan')

    def test_reject_numeric_id_before_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'raw'; file=Path(d)/'export.json'; data=self.fixture()
            data['posts'][0]['tweet_id']=1000000000000000001
            file.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError):import_export(file,root)
            self.assertFalse(root.exists())

    def test_reject_different_study_period(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'raw'; file=Path(d)/'export.json'; data=self.fixture()
            data['state']['config']['phases'][0]['since']='2025-01-01'
            file.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(ValueError):import_export(file,root)
            self.assertFalse(root.exists())


if __name__=='__main__':unittest.main()
