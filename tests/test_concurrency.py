import threading, unittest
from agent import Store
class ConcurrencyTests(unittest.TestCase):
 def test_parallel_sessions_keep_own_tasks(self):
  s=Store(':memory:'); ids=[s.create() for _ in range(8)]; errors=[]
  def work(sid):
   try:
    for i in range(30): s.todo(sid,'add',str(i))
   except Exception as e: errors.append(str(e))
  threads=[threading.Thread(target=work,args=(sid,)) for sid in ids]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(errors,[])
  self.assertEqual([len(s.todo(sid,'list')) for sid in ids],[30]*8)
  s.db.close()
