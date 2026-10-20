import json
import unittest
from backend.dsh_protocol import DshStream

class ProtocolTests(unittest.TestCase):
    def test_final_is_not_success_without_completed_turn(self):
        stream = DshStream()
        for item in [dict(type='session',sessionId='s'),dict(type='status',phase='turn_end',reason={'kind':'error'}),dict(type='final',text='')]:
            stream.feed(json.dumps(item))
        self.assertFalse(stream.completed(1))
        self.assertFalse(stream.completed(0))

    def test_success_checkpoint_and_usage(self):
        stream = DshStream()
        for item in [dict(type='session',sessionId='s'),dict(type='status',phase='step_end',usage={'inputTokens':10}),dict(type='status',phase='turn_end',reason={'kind':'completed'}),dict(type='final',text='report')]:
            stream.feed(json.dumps(item))
        self.assertEqual(stream.session_id,'s')
        self.assertEqual(stream.usage,[{'inputTokens':10}])
        self.assertTrue(stream.completed(0))
        with self.assertRaises(ValueError):
            stream.feed(json.dumps(dict(type='session',sessionId='other')))
