import json, unittest
from server import stream_events
class BrokenWriter:
 def write(self, data): raise BrokenPipeError()
 def flush(self): pass
class DisconnectTests(unittest.TestCase):
 def test_disconnect_cancels_and_finishes_generator_cleanup(self):
  state={'cancelled':False,'cleaned':False}
  def events():
   yield {'type':'tool'}
   state['cleaned']=state['cancelled']
  stream_events(BrokenWriter(), events(), lambda: state.__setitem__('cancelled',True))
  self.assertTrue(state['cleaned'])
