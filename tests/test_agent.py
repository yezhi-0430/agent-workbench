import unittest
from agent import Store, calculator, Agent

class Tests(unittest.TestCase):
 def test_calculator(self):
  self.assertEqual(calculator('2*(3+4)'),14)
  with self.assertRaises(ValueError): calculator('__import__("os")')
 def test_session_isolation(self):
  s=Store(':memory:'); self.addCleanup(s.db.close); a=s.create(); b=s.create(); s.todo(a,'add','one'); self.assertEqual(len(s.todo(b,'list')),0)
 def test_loop(self):
  s=Store(':memory:'); self.addCleanup(s.db.close); a=s.create(); calls=[]
  def model(messages, tools):
   calls.append(messages.copy())
   return {'tool_calls':[{'id':'1','type':'function','function':{'name':'calculator','arguments':'{"expression":"2+3"}'}}]} if len(calls)==1 else {'content':'5'}
  events=list(Agent(s,model).run(a,'calculate'))
  self.assertEqual(events[-1]['content'],'5'); self.assertTrue(any(e['type']=='tool' for e in events))
 def test_limit(self):
  s=Store(':memory:'); self.addCleanup(s.db.close); a=s.create()
  def model(messages,tools): return {'tool_calls':[{'id':'1','type':'function','function':{'name':'missing','arguments':'{}'}}]}
  self.assertEqual(list(Agent(s,model,max_steps=2).run(a,'x'))[-1]['type'],'error')
if __name__=='__main__': unittest.main()
