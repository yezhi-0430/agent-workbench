import unittest
from agent import Agent,Store
class TraceTests(unittest.TestCase):
 def test_model_trace_reaches_event_stream(self):
  s=Store(':memory:');sid=s.create()
  def model(messages,tools):return {'content':'ok','_trace':{'model':'test-model','duration_ms':25,'retries':1}}
  events=list(Agent(s,model).run(sid,'hello'))
  traces=[e for e in events if e['type']=='model']
  self.assertEqual(traces[0]['retries'],1);self.assertEqual(traces[0]['duration_ms'],25)
  s.db.close()
