import json, unittest
from agent import Agent,Store,Registry,spec
class ToolBudgetTests(unittest.TestCase):
 def test_large_tool_result_does_not_get_sent_over_budget(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create();reg=Registry();reg.register(spec('large','large',{},[]),lambda sid: 'x'*30000)
  calls=[]
  def model(messages,tools):
   calls.append(messages)
   return {'tool_calls':[{'id':'a','type':'function','function':{'name':'large','arguments':'{}'}}]}
  events=list(Agent(s,model,registry=reg).run(sid,'test'))
  self.assertEqual(len(calls),1)
  self.assertEqual(events[-1]['type'],'error')
