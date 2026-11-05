import json, unittest
from agent import Agent, Store
class RecoveryTests(unittest.TestCase):
 def test_incomplete_call_repaired_without_reexecuting(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  s.add(sid,{'role':'user','content':'add task'})
  s.add(sid,{'role':'assistant','content':None,'tool_calls':[{'id':'lost','type':'function','function':{'name':'todo','arguments':json.dumps({'action':'add','text':'do not duplicate'})}}]})
  seen=[]
  def model(messages,tools): seen.extend(messages);return {'content':'ok'}
  list(Agent(s,model).run(sid,'continue'))
  pos=next(i for i,m in enumerate(seen) if m.get('tool_calls'))
  self.assertEqual(seen[pos+1]['tool_call_id'],'lost')
  self.assertIn('unknown',seen[pos+1]['content'].lower())
  self.assertEqual(s.todo(sid,'list'),[])
 def test_old_missing_result_is_repaired_before_later_user(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  s.add(sid,{'role':'assistant','content':None,'tool_calls':[{'id':'lost','type':'function','function':{'name':'calculator','arguments':'{}'}}]})
  s.add(sid,{'role':'user','content':'earlier followup'})
  seen=[]
  def model(messages,tools):seen.extend(messages);return {'content':'ok'}
  list(Agent(s,model).run(sid,'now'))
  pos=next(i for i,m in enumerate(seen) if m.get('tool_calls'))
  self.assertEqual(seen[pos+1]['tool_call_id'],'lost')
