import unittest
from agent import Agent, Store
class SummaryIntegrityTests(unittest.TestCase):
 def test_oversized_summary_is_not_silently_stored(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  for i in range(9):s.add(sid,{'role':'user','content':str(i)});s.add(sid,{'role':'assistant','content':'ok'})
  def model(messages,tools):return {'content':('x'*6001) if not tools else 'ok'}
  events=list(Agent(s,model).run(sid,'continue'))
  self.assertEqual(events[-1]['type'],'error');self.assertEqual(s.summary(sid),('',0))
