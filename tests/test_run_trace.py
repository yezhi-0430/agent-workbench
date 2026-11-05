import json,threading,unittest,urllib.request
from unittest.mock import patch
import server
from storage import Store
class RunTraceTests(unittest.TestCase):
 def setUp(self):
  self.test_store=Store(':memory:'); patcher=patch.object(server,'store',self.test_store); patcher.start()
  self.addCleanup(self.test_store.db.close); self.addCleanup(patcher.stop)
 def test_each_run_has_consistent_unique_id_and_terminal_event(self):
  class FakeAgent:
   def __init__(self,store,should_cancel):pass
   def run(self,sid,text):
    yield {'type':'model','model':'fake','duration_ms':1,'retries':0}
    yield {'type':'answer','content':'ok'}
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);t=threading.Thread(target=http.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(http.server_address[1]);op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  def post(path,data):
   req=urllib.request.Request(base+path,json.dumps(data).encode(),{'Content-Type':'application/json'})
   with op.open(req,timeout=5) as f:return f.read().decode()
  try:
   sid=json.loads(post('/api/sessions',{}))['id']
   with patch.object(server,'Agent',FakeAgent):
    first=[json.loads(x) for x in post('/api/chat',{'session_id':sid,'text':'a'}).splitlines()]
    second=[json.loads(x) for x in post('/api/chat',{'session_id':sid,'text':'b'}).splitlines()]
   self.assertEqual(len({e['run_id'] for e in first}),1)
   self.assertNotEqual(first[0]['run_id'],second[0]['run_id'])
   self.assertTrue(any(e['type']=='run_end' and e['status']=='completed' for e in first))
  finally:http.shutdown();http.server_close();t.join(5)
