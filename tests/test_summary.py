import unittest
from agent import Agent, Store
class SummaryTests(unittest.TestCase):
 def test_summary_generated_and_reused_with_recent_turns(self):
  s=Store(':memory:'); sid=s.create()
  for i in range(10):
   s.add(sid,{'role':'user','content':f'message {i}'});s.add(sid,{'role':'assistant','content':f'answer {i}'})
  summary_calls=[]; requests=[]
  def model(messages, tools):
   if not tools:
    summary_calls.append(messages);return {'content':'User prefers concise answers.'}
   requests.append(messages);return {'content':'ok'}
  events=list(Agent(s,model).run(sid,'continue'))
  self.assertEqual(len(summary_calls),1)
  self.assertTrue(any('User prefers concise answers.' in m.get('content','') for m in requests[0]))
  self.assertTrue(any(e['type']=='context' for e in events))
  self.assertEqual(s.summary(sid)[0],'User prefers concise answers.')
  s.db.close()
