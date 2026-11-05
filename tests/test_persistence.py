import tempfile, unittest
from pathlib import Path
from agent import Store, Agent
class PersistenceTests(unittest.TestCase):
 def test_reopen_and_follow_up(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'db.sqlite'); s=Store(path); sid=s.create(); s.todo(sid,'add','写周报'); s.add(sid,{'role':'user','content':'我叫小明'}); s.db.close()
   s=Store(path); seen=[]
   def model(messages, tools):
    seen.extend(messages); return {'content':'小明'}
   self.assertEqual(s.todo(sid,'list')[0]['text'],'写周报')
   self.assertEqual(list(Agent(s,model).run(sid,'我叫什么？'))[-1]['content'],'小明')
   self.assertTrue(any(m.get('content')=='我叫小明' for m in seen)); s.db.close()
 def test_compression_preserves_recent_turns(self):
  s=Store(':memory:'); self.addCleanup(s.db.close); sid=s.create()
  for i in range(10): s.add(sid,{'role':'user','content':f'历史{i}'}); s.add(sid,{'role':'assistant','content':f'回答{i}'})
  seen=[]
  def model(messages,tools): seen.extend(messages); return {'content':'ok'}
  list(Agent(s,model).run(sid,'继续'))
  self.assertIn('历史0',seen[1]['content']); self.assertTrue(any(m.get('content')=='历史9' for m in seen)); self.assertEqual(seen[-1]['content'],'继续')
if __name__=='__main__': unittest.main()
