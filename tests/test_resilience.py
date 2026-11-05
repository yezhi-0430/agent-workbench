import io, json, os, ssl, unittest
from unittest.mock import patch
from urllib.error import URLError, HTTPError
from agent import openrouter, TOOLS

class ResilienceTests(unittest.TestCase):
 def test_connection_failure_retried(self):
  response=io.BytesIO(json.dumps({'choices':[{'message':{'content':'ok'}}]}).encode())
  with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test'}), patch('urllib.request.urlopen',side_effect=[URLError(ssl.SSLEOFError('EOF')),response]) as call, patch('time.sleep'):
   self.assertEqual(openrouter([],[])['content'],'ok'); self.assertEqual(call.call_count,2)
 def test_auth_error_not_retried(self):
  err=HTTPError('https://example.invalid',401,'unauthorized',{},None)
  with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test'}), patch('urllib.request.urlopen',side_effect=err) as call, patch('time.sleep'):
   with self.assertRaises(HTTPError): openrouter([],[])
   self.assertEqual(call.call_count,1)
 def test_todo_tool_spec_distinguishes_memory(self):
  description=next(t['function']['description'] for t in TOOLS if t['function']['name']=='todo')
  self.assertIn('不是',description)
if __name__=='__main__': unittest.main()
