"""Unit tests covering the RecSA module."""

import unittest
from unittest.mock import Mock, MagicMock, call
from resolve.resolver import Resolver
from modules.recsa.module import RecSAModule
from modules import constants

class TestRecSAModule(unittest.TestCase):
    def setUp(self):
        self.resolver = Resolver(testing=True)
        self.n = 6
        self.mod = RecSAModule(0, self.resolver, self.n)
    
    # getters
    def test_get_config_j(self):
        self.mod.config = {0: [0,1], 1: [1,2]}
        self.assertEqual(self.mod.get_config_j(0), [0,1])
        self.assertEqual(self.mod.get_config_j(2), [])
    

if __name__ == '__main__':
    unittest.main()
