import atexit, datetime, json, threading, urllib.parse, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from agent import Store, Agent
from config import load_env
load_env()
store=Store(); atexit.register(store.db.close); locks={}; guard=threading.Lock(); cancels={}
def stream_events(writer, events, cancel):
 try:
  for event in events:
   writer.write((json.dumps(event,ensure_ascii=False)+'\n').encode()); writer.flush()
 except (BrokenPipeError,ConnectionResetError):
  cancel()
  for _ in events: pass

class Handler(BaseHTTPRequestHandler):
 def reply(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_GET(self):
  p=urllib.parse.urlparse(self.path)
  if p.path=='/api/sessions': return self.reply(store.sessions())
  if p.path.startswith('/api/sessions/'):
   sid=p.path.split('/')[3]
   if not store.exists(sid): return self.reply({'error':'Session not found'},404)
   if p.path.endswith('/traces'): return self.reply(store.traces(sid))
   if p.path.endswith('/summary'):
    summary,count=store.summary(sid); return self.reply({'summary':summary,'count':count})
   return self.reply(store.messages(sid))
  name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(p.path)
  if not name: return self.reply({'error':'Not found'},404)
  raw=(Path(__file__).parent/'static'/name).read_bytes(); self.send_response(200); self.send_header('Content-Type',{'html':'text/html','js':'text/javascript','css':'text/css'}[name.rsplit('.',1)[-1]]+'; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
 def do_POST(self):
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>65536: return self.reply({'error':'Request too large'},413)
   data=json.loads(self.rfile.read(length) or b'{}')
   if self.path=='/api/sessions': return self.reply({'id':store.create()})
   if self.path=='/api/stop':
    with guard: event=cancels.get(data.get('session_id'))
    if event: event.set()
    return self.reply({'stopping':bool(event)})
   if self.path!='/api/chat': return self.reply({'error':'Not found'},404)
   sid=data.get('session_id'); text=data.get('text','')
   if not store.exists(sid) or not isinstance(text,str) or not text.strip() or len(text)>10000: return self.reply({'error':'Invalid request'},400)
   with guard:
    lock=locks.setdefault(sid,threading.Lock())
    if not lock.acquire(False): return self.reply({'error':'Session is busy'},409)
    cancel=threading.Event(); cancels[sid]=cancel
   self.send_response(200); self.send_header('Content-Type','application/x-ndjson; charset=utf-8'); self.send_header('Cache-Control','no-cache'); self.end_headers()
   try:
    def recorded_events():
     run_id=uuid.uuid4().hex; status='interrupted'
     def record(event):
      event={**event,'run_id':run_id,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
      if event.get('type') != 'answer': store.add_trace(sid,event)
      return event
     yield record({'type':'run_start'})
     for event in Agent(store,should_cancel=cancel.is_set).run(sid,text):
      if event.get('type')=='answer': status='completed'
      elif event.get('type')=='error': status='cancelled' if cancel.is_set() else 'failed'
      yield record(event)
     if cancel.is_set() and status!='completed': status='cancelled'
     yield record({'type':'run_end','status':status})
    stream_events(self.wfile, recorded_events(), cancel.set)
   finally:
    with guard: cancels.pop(sid,None); lock.release()
  except (ValueError,TypeError,json.JSONDecodeError): self.reply({'error':'Invalid request'},400)
if __name__=='__main__':
 print('Agent Workbench: http://127.0.0.1:8765',flush=True); ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()

