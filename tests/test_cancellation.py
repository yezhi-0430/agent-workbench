import json, unittest
from agent import Store, Agent

class CancellationTests(unittest.TestCase):
 def test_cancel_before_tool_does_not_execute_and_history_stays_valid(self):
  s=Store(':memory:'); sid=s.create()
  def model(messages,tools):
   return {'tool_calls':[{'id':'one','type':'function','function':{'name':'todo','arguments':json.dumps({'action':'add','text':'should not exist'})}}]}
  events=list(Agent(s,model,should_cancel=lambda: True).run(sid,'cancel'))
  self.assertEqual(s.todo(sid,'list'),[])
  self.assertEqual(events[-1]['type'],'error')
  history=s.messages(sid)
  for msg in history:
   if msg.get('tool_calls'):
    for call in msg['tool_calls']:
     self.assertTrue(any(m.get('tool_call_id')==call['id'] for m in history))
  s.db.close()
 def test_cancel_between_tools_records_unexecuted_result(self):
  s=Store(':memory:'); sid=s.create(); stopped=[False]
  def model(messages,tools):
   return {'tool_calls':[{'id':str(i),'type':'function','function':{'name':'todo','arguments':json.dumps({'action':'add','text':str(i)})}} for i in range(2)]}
  it=Agent(s,model,should_cancel=lambda: stopped[0]).run(sid,'run')
  next(it); stopped[0]=True; events=list(it)
  self.assertEqual([x['text'] for x in s.todo(sid,'list')],['0'])
  self.assertEqual(events[-1]['type'],'error')
  self.assertEqual(len([m for m in s.messages(sid) if m['role']=='tool']),2)
  s.db.close()
