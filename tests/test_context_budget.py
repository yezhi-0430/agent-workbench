import unittest
from agent import Agent,Store
class ContextBudgetTests(unittest.TestCase):
 def test_large_history_is_chunked_without_losing_beginning(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  s.add(sid,{'role':'user','content':'KEY-START '+('a'*18000)+' KEY-END'});s.add(sid,{'role':'assistant','content':'ok'})
  for i in range(8):s.add(sid,{'role':'user','content':f'round{i}'});s.add(sid,{'role':'assistant','content':'ok'})
  inputs=[]
  def model(messages,tools):
   if not tools: inputs.append(messages[-1]['content']);return {'content':'summary'}
   return {'content':'ok'}
  list(Agent(s,model).run(sid,'question'))
  joined=''.join(inputs)
  self.assertIn('KEY-START',joined);self.assertIn('KEY-END',joined)
  self.assertGreater(len(inputs),1)
 def test_big_recent_context_triggers_summary_before_eight_turns(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  for i in range(5):s.add(sid,{'role':'user','content':f'{i}'+('x'*7000)});s.add(sid,{'role':'assistant','content':'ok'})
  summary=[]
  def model(messages,tools):
   if not tools:summary.append(True)
   return {'content':'summary' if not tools else 'ok'}
  list(Agent(s,model).run(sid,'next'))
  self.assertTrue(summary)
 def test_summary_failure_does_not_advance_cursor(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create()
  for i in range(9):s.add(sid,{'role':'user','content':str(i)});s.add(sid,{'role':'assistant','content':'ok'})
  def model(messages,tools):
   if not tools:raise RuntimeError('summary failed')
   return {'content':'ok'}
  events=list(Agent(s,model).run(sid,'next'))
  self.assertEqual(s.summary(sid)[1],0)
  self.assertEqual(events[-1]['type'],'error')
