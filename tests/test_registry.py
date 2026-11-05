import json, unittest
from agent import Store, Agent, Registry, spec
class RegistryTests(unittest.TestCase):
 def test_register_and_execute_custom_tool(self):
  s=Store(':memory:'); sid=s.create(); reg=Registry()
  reg.register(spec('echo','Echo',{'text':{'type':'string'}},['text']),lambda sid, **kw: kw['text'])
  count=[0]
  def model(messages, tools):
   count[0]+=1
   if count[0]==1:
    self.assertEqual(tools[0]['function']['name'],'echo')
    return {'tool_calls':[{'id':'1','type':'function','function':{'name':'echo','arguments':'{"text":"hello"}'}}]}
   self.assertIn('hello', messages[-1]['content']); return {'content':'done'}
  events=list(Agent(s,model,registry=reg).run(sid,'x'))
  self.assertEqual(events[-1]['content'],'done');s.db.close()
 def test_schema_rejects_wrong_type_and_extra_arguments(self):
  reg=Registry();reg.register(spec('echo','Echo',{'text':{'type':'string'}},['text']),lambda sid,**kw:kw['text'])
  for args in ({'text':123},{'text':'x','extra':True},{}):
   with self.assertRaises(ValueError): reg.execute('echo','id',args)
