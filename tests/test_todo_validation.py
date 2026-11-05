import unittest
from agent import Store, default_registry
class TodoValidationTests(unittest.TestCase):
 def test_actions_require_correct_arguments(self):
  s=Store(':memory:');self.addCleanup(s.db.close);sid=s.create();r=default_registry(s)
  for args in ({'action':'add'}, {'action':'add','text':'  '}, {'action':'complete'}, {'action':'list','text':'ignored'}, {'action':'complete','id':1,'text':'ignored'}):
   with self.subTest(args=args), self.assertRaises(ValueError):r.execute('todo',sid,args)
  self.assertEqual(s.todo(sid,'list'),[])
