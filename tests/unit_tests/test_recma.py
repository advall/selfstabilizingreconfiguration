"""Unit tests covering the RecMA module."""

import unittest
from unittest.mock import Mock, MagicMock, call
from resolve.resolver import Resolver
from modules.recma.module import RecMAModule

class TestRecMAModule(unittest.TestCase):
    def setUp(self):
        self.resolver = Resolver(testing=True)
        self.n = 6
        self.mod = RecMAModule(0, self.resolver, self.n)

    # macros
    def test_core(self):
        mocked_responses = [
            [1,2,3],
            [1,2,3],
            [1,2,3,4],
            [0,1,2]
        ]
        mocked_method = Mock()
        mocked_method.side_effect = mocked_responses
        self.resolver.recsa_get_fd_part_j = mocked_method
        core = self.mod.core()
        self.assertEqual(core, [1,2])
        pass
    
    def test_flush_flags(self):
        for i in range(2):
            self.mod.need_reconf[i] = True
            self.mod.no_maj[i] = True

        self.resolver.recsa_get_fd_j = MagicMock(return_value=[1,2,3])
        self.mod.flush_flags()

        # Should set all vals to False for ids 1,2 and 3
        self.assertEqual(self.mod.need_reconf, {0: True, 1: False, 2: False, 3: False})
        self.assertEqual(self.mod.no_maj, {0: True, 1: False, 2: False, 3: False})

if __name__ == '__main__':
    unittest.main()
