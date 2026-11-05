import json, threading, unittest, urllib.request
from unittest.mock import patch
import server
from storage import Store
class TraceHttpTests(unittest.TestCase):
 def setUp(self):
  self.test_store=Store(':memory:'); patcher=patch.object(server,'store',self.test_store); patcher.start()
  self.addCleanup(self.test_store.db.close); self.addCleanup(patcher.stop)
 def test_api_records_and_restores_trace_for_session(self):
  class FakeAgent:
   def __init__(self,store,should_cancel):pass
   def run(self,sid,text):
    yield {'type':'model','model':'fake','duration_ms':12,'retries':0}
    yield {'type':'answer','content':'ok'}
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);t=threading.Thread(target=http.serve_forever,daemon=True);t.start()
  base='http://127.0.0.1:'+str(http.server_address[1]);op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  def get(path,data=None):
   req=urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
   with op.open(req,timeout=5) as f:return f.read().decode()
  try:
   a=json.loads(get('/api/sessions',{}))['id'];b=json.loads(get('/api/sessions',{}))['id']
   with patch.object(server,'Agent',FakeAgent):get('/api/chat',{'session_id':a,'text':'hello'})
   traces=json.loads(get('/api/sessions/'+a+'/traces'))
   self.assertTrue(any(e.get('model')=='fake' for e in traces));self.assertEqual(json.loads(get('/api/sessions/'+b+'/traces')),[])
  finally:http.shutdown();http.server_close();t.join(5)
