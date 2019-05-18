"""Unit tests covering the RecMA module."""

import unittest
from resolve.resolver import Resolver

class TestRecMAModule(unittest.TestCase):
    def setUp(self):
        self.resolver = Resolver(testing=True)

    # macros
    def test_core(self):
        pass
    
    def test_flush_flags(self):
        pass

if __name__ == '__main__':
    unittest.main()
