import functools, json, sqlite3, threading, uuid

def synchronized(method):
 @functools.wraps(method)
 def wrapper(self,*args,**kwargs):
  with self.lock: return method(self,*args,**kwargs)
 return wrapper

class Store:
 def __init__(self,path='agent.db'):
  self.lock=threading.RLock()
  self.db=sqlite3.connect(path,check_same_thread=False)
  self.db.executescript('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY,title TEXT,summary TEXT DEFAULT ""); CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY,session_id TEXT,data TEXT); CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY,session_id TEXT,text TEXT,done INTEGER DEFAULT 0);'); self.db.commit()
  self.db.execute('CREATE TABLE IF NOT EXISTS trace_events (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, data TEXT NOT NULL)'); self.db.commit()
  if 'summary_count' not in [r[1] for r in self.db.execute('PRAGMA table_info(sessions)')]:
   self.db.execute('ALTER TABLE sessions ADD COLUMN summary_count INTEGER DEFAULT 0'); self.db.commit()
 @synchronized
 def create(self):
  sid=uuid.uuid4().hex; self.db.execute('INSERT INTO sessions(id,title) VALUES (?,?)',(sid,'新会话')); self.db.commit(); return sid
 @synchronized
 def sessions(self): return [{'id':r[0],'title':r[1]} for r in self.db.execute('SELECT id,title FROM sessions ORDER BY rowid DESC')]
 @synchronized
 def exists(self,sid): return self.db.execute('SELECT 1 FROM sessions WHERE id=?',(sid,)).fetchone() is not None
 @synchronized
 def messages(self,sid): return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM messages WHERE session_id=? ORDER BY id',(sid,))]
 @synchronized
 def add(self,sid,msg):
  self.db.execute('INSERT INTO messages(session_id,data) VALUES (?,?)',(sid,json.dumps(msg,ensure_ascii=False)))
  if msg.get('role')=='user': self.db.execute("UPDATE sessions SET title=? WHERE id=? AND title='新会话'",(msg['content'][:24],sid))
  self.db.commit()
 @synchronized
 def add_trace(self,sid,event):
  self.db.execute('INSERT INTO trace_events(session_id,data) VALUES (?,?)',(sid,json.dumps(event,ensure_ascii=False))); self.db.commit()
 @synchronized
 def traces(self,sid):
  return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM trace_events WHERE session_id=? ORDER BY id',(sid,))]
 @synchronized
 def summary(self,sid):
  row=self.db.execute('SELECT summary,summary_count FROM sessions WHERE id=?',(sid,)).fetchone()
  return (row[0] or '',row[1] or 0)
 @synchronized
 def save_summary(self,sid,summary,count):
  self.db.execute('UPDATE sessions SET summary=?, summary_count=? WHERE id=?',(summary,count,sid)); self.db.commit()
 @synchronized
 def todo(self,sid,action,text='',id=None):
  if action=='add':
   if not text.strip(): raise ValueError('text is required')
   self.db.execute('INSERT INTO todos(session_id,text) VALUES (?,?)',(sid,text))
  elif action=='complete':
   c=self.db.execute('UPDATE todos SET done=1 WHERE session_id=? AND id=?',(sid,id))
   if not c.rowcount: raise ValueError('Todo not found')
  elif action!='list': raise ValueError('Unknown action')
  self.db.commit(); return [{'id':r[0],'text':r[1],'done':bool(r[2])} for r in self.db.execute('SELECT id,text,done FROM todos WHERE session_id=?',(sid,))]

