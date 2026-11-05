import json, socket, struct, threading, unittest, urllib.request
from unittest.mock import patch
import server
from storage import Store

class HttpDisconnectTests(unittest.TestCase):
 def setUp(self):
  self.test_store=Store(':memory:'); patcher=patch.object(server,'store',self.test_store); patcher.start()
  self.addCleanup(self.test_store.db.close); self.addCleanup(patcher.stop)
 def test_disconnect_triggers_cancel_and_drains_generator(self):
  first=threading.Event(); resume=threading.Event(); cleaned=threading.Event(); state={}
  class FakeAgent:
   def __init__(self,store,should_cancel): self.cancel=should_cancel
   def run(self,sid,text):
    yield {'type':'tool','content':'first'}
    first.set(); resume.wait(5)
    yield {'type':'tool','content':'x'*500000}
    state['cancelled']=self.cancel(); cleaned.set()
  http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  sid=server.store.create(); sock=socket.create_connection(http.server_address,timeout=5)
  payload=json.dumps({'session_id':sid,'text':'test'}).encode()
  request=(f'POST /api/chat HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n').encode()+payload
  try:
   with patch.object(server,'Agent',FakeAgent):
    sock.sendall(request); self.assertTrue(first.wait(5))
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));sock.close();resume.set()
    self.assertTrue(cleaned.wait(8));self.assertTrue(state['cancelled'])
  finally:
   resume.set();http.shutdown();http.server_close();thread.join(5)
