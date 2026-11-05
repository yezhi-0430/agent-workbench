import os, subprocess, sys, tempfile, unittest
from pathlib import Path
from agent import Agent,Store
class CrashIntegrationTests(unittest.TestCase):
 def test_process_crash_after_side_effect_does_not_repeat_tool(self):
  with tempfile.TemporaryDirectory() as d:
   db=str(Path(d)/'agent.db')
   script='''
import os,sys,json
from agent import Agent,Store
s=Store(sys.argv[1]);sid=s.create();open(sys.argv[2],'w').write(sid)
def model(messages,tools):
 return {'tool_calls':[{'id':'one','type':'function','function':{'name':'todo','arguments':json.dumps({'action':'add','text':'once'})}},{'id':'two','type':'function','function':{'name':'todo','arguments':json.dumps({'action':'add','text':'never'})}}]}
for event in Agent(s,model).run(sid,'do tasks'):
 if event['type']=='tool': os._exit(23)
'''
   sidfile=str(Path(d)/'sid'); env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parent.parent)
   result=subprocess.run([sys.executable,'-c',script,db,sidfile],env=env,timeout=15)
   self.assertEqual(result.returncode,23)
   sid=Path(sidfile).read_text();s=Store(db);seen=[]
   def model(messages,tools):seen.extend(messages);return {'content':'checked'}
   events=list(Agent(s,model).run(sid,'continue'))
   self.assertTrue(any(e['type']=='recovery' for e in events))
   self.assertEqual([t['text'] for t in s.todo(sid,'list')],['once'])
   self.assertTrue(any(m.get('tool_call_id')=='two' and 'unknown' in m['content'].lower() for m in seen));s.db.close()
