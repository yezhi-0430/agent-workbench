import tempfile, unittest
from pathlib import Path
from agent import Store
class TraceStorageTests(unittest.TestCase):
 def test_trace_survives_restart_and_is_scoped_to_session(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'db');s=Store(path);a=s.create();b=s.create()
   event={'type':'model','model':'test-model','duration_ms':12,'retries':1};s.add_trace(a,event);s.db.close()
   s=Store(path);self.assertEqual(s.traces(a),[event]);self.assertEqual(s.traces(b),[]);s.db.close()
