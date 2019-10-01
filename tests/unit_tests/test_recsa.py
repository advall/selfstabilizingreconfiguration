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
    
    def test_get_fd_j(self):
        trusted = [1,2,3]
        self.resolver.fd_get_trusted = MagicMock(return_value=trusted)
        self.mod.fd = {1: [1,2]}
        fd = self.mod.get_fd_j(self.mod.id)
        self.assertEqual(fd, trusted)
        self.resolver.fd_get_trusted.assert_called_once()
        fd = self.mod.get_fd_j(1)
        self.assertEqual(fd, [1,2])
        fd = self.mod.get_fd_j(4)
        self.assertEqual(fd, [])
        self.resolver.fd_get_trusted.assert_called_once()

    def test_get_fd_part_j(self):
        self.mod.fd = {}
        self.mod.fd_part = {0: [0,1,2], 1: [2,3,4]}
        
        self.assertEqual(self.mod.get_fd_part_j(1), [2,3,4])
        self.assertEqual(self.mod.get_fd_part_j(2), [])

        # TODO test get_fd_part_j(0) (mod.id)
    
    def test_get_echo_part_j(self):
        part = [0,1,2]
        self.mod.echo_part = {1: [1,2,3]}
        self.mod.get_fd_part_j = MagicMock(return_value=part)
        echo_part = self.mod.get_echo_part_j(self.mod.id)
        self.mod.get_fd_part_j.assert_called_once()
        self.assertEqual(echo_part, part)
        echo_part = self.mod.get_echo_part_j(1)
        self.assertEqual(echo_part, [1,2,3])
        echo_part = self.mod.get_echo_part_j(2)
        self.assertEqual(echo_part, [])
    
    def get_echo_prp_j(self):
        prp = (0, [1,2])
        self.mod.get_prp_j = MagicMock(return_value=prp)
        self.mod.echo_prp = {1: (1, [1,2,3])}
        echo_prp = self.mod.get_echo_prp_j(self.mod.id)
        self.mod.get_prp_j.assert_called_once()
        self.assertEqual(echo_prp, prp)

        echo_prp = self.mod.get_echo_prp_j(1)
        self.assertEqual(echo_prp, [1,2,3])
        echo_prp = self.mod.get_echo_prp_j(2)
        self.assertEqual(echo_prp, [])
    
    def test_get_echo_all_j(self):
        self.mod.echo_all = {1: True}
        self.mod.get_all_j = MagicMock(return_value=True)
        self.assertTrue(self.mod.get_echo_all_j(self.mod.id))
        self.mod.get_all_j.assert_called_once()
        self.assertTrue(self.mod.get_echo_all_j(1))
        self.assertFalse(self.mod.get_echo_all_j(2))
    
    def test_get_prp_j(self):
        self.mod.prp = {0: (1, [1,2,3])}
        self.assertEqual(self.mod.get_prp_j(self.mod.id), (1, [1,2,3]))
        self.assertEqual(self.mod.get_prp_j(1), constants.DFLT_NTF)
    
    def test_get_all_j(self):
        self.mod.alll = {0: True, 1: False}
        self.assertTrue(self.mod.get_all_j(self.mod.id))
        self.assertFalse(self.mod.get_all_j(1))
        self.assertFalse(self.mod.get_all_j(2))

    # interface functions
    def test_get_config(self):
        self.mod.chs_config = MagicMock(return_value=[0,1,2])

        # should call chs_config() and return whenever allow_reco is True
        self.mod.allow_reco = MagicMock(return_value=True)
        conf = self.mod.get_config()
        self.assertEqual(conf, [0,1,2])
        self.mod.chs_config.assert_called_once()

        # should return config[i] when allow_reco is False
        self.mod.config[self.mod.id] = [1]
        self.mod.allow_reco = MagicMock(return_value=False)
        conf = self.mod.get_config()
        self.assertEqual(conf, [1])
        # should not have been called again
        self.mod.chs_config.assert_called_once()

    
    def test_get_config_app(self):
        conf = [1,2,3]
        self.mod.config[self.mod.id] = conf
        self.mod.degree = MagicMock(return_value=1)
        # when degree = 0,1 or 2, should return conf
        conf_app = self.mod.get_config_app()
        self.assertEqual(conf_app, conf)
        self.mod.degree.assert_called_once()

        # otherwise, return union of current conf and proposed set
        self.mod.config[self.mod.id] = [1,2]
        self.mod.prp[self.mod.id] = (0, [0,1])
        # self.mod.get_config_j = MagicMock(return_value=[1,2])
        self.mod.degree = MagicMock(return_value=-1)
        conf_app = self.mod.get_config_app()
        self.assertEqual(conf_app, [0,1,2])

    
    def test_allow_reco(self):
        # TODO
        pass
    
    def test_estab(self):
        self.mod.config[self.id] = [0,1]
        self.mod.prp[self.mod.id] = constants.DFLT_NTF
        self.mod.allow_reco = MagicMock(return_value=True)
        # can't establish empty set, prp[i] should = (0, BOTTOM)
        s = constants.BOTTOM
        self.mod.estab(s)
        self.assertEqual(self.mod.prp[self.mod.id], constants.DFLT_NTF)
        # establish [0,1], should succeed since prp[i] = (0, BOTTOM)
        s = [0,1]
        self.mod.estab(s)
        self.assertEqual(self.mod.prp[self.mod.id], (1, [0,1]))
        # should have been called twice
        self.assertEqual(self.mod.allow_reco.call_count, 2)
    
    def test_participate(self):
        chs_conf = [1,2,3]
        self.mod.allow_reco = MagicMock(return_value=True)
        self.mod.chs_config = MagicMock(return_value=chs_conf)
        self.mod.config[self.mod.id] = constants.BOTTOM
        self.mod.participate()
        self.assertEqual(self.mod.config[self.mod.id], chs_conf)

    # macros
    def test_chs_config(self):
        self.resolver.fd_get_trusted = MagicMock(return_value=[0,2])
        self.mod.config = {0: constants.NOT_PARTICIPANT, 1: constants.NOT_PARTICIPANT}

        # should return BOTTOM if no participants 
        conf = self.mod.chs_config()
        self.assertEqual(conf, constants.BOTTOM)
        self.mod.config = {0: [0,1], 1: [1,2,3], 2: [1,5]}

        # should return union of all config for ids in mod.fd (0 and 2)
        conf = self.mod.chs_config()
        self.assertEqual(conf, [0,1,5])
    
    def test_my_all(self):
        self.mod.alll = {0: True, 1: False}
        self.mod.prp = {0: (0, [1,2]), 2: (0, [2,3,4])}
        # should return True since mod.alll[0] = true
        self.assertTrue(self.mod.my_alll(self.mod.id))
        self.mod.alll[0] = False
        self.mod.prp[2] = (1, [2,3,4])
        self.mod.all_seen = {0,2}
        # should return True since k = mod.id and 2 in mod.all_seen and mod.prp[2].phase = mod.prp[id] + 1
        self.assertTrue(self.mod.my_alll(self.mod.id))
        # 2 now in phase 0, should return False
        self.mod.prp[2] = (0, [2,3,4])
        self.assertFalse(self.mod.my_alll(self.mod.id))
    
    def test_degree(self):
        self.mod.prp[1] = (1, constants.BOTTOM)
        self.mod.my_alll = MagicMock(return_value=True)
        # should return 2*prp[1].phase + 1 = 3
        self.assertEqual(self.mod.degree(1), 3)
        self.mod.my_alll.assert_called_once()
        self.mod.my_alll = MagicMock(return_value=False)
        # should return 2*prp[1].phase + 0 = 2
        self.assertEqual(self.mod.degree(1), 2)
        self.mod.my_alll.assert_called_once()
    
    def test_corr_deg(self):
        k = 1
        k_prim = 2
        self.mod.degree = Mock()
        # 3 and 4 are <= 1 apart, should return True
        self.mod.degree.side_effect = [3,4]
        self.assertTrue(self.mod.corr_deg(k, k_prim))
        # 3 and 5 are more than 1 apart, should return False
        self.mod.degree.side_effect = [3,5]
        self.assertFalse(self.mod.corr_deg(k, k_prim))
    
    def test_echo_no_all(self):
        self.mod.get_fd_part_j = MagicMock(return_value=[1,2,3])
        self.mod.echo_part[1] = [1,2,3]
        self.mod.echo_prp[1] = (1, [1,2,3])
        self.mod.prp[0] = (1, [1,2,3])
        self.assertTrue(self.mod.echo_no_all(1))
    
    def test_echo_fun(self):
        self.mod.echo_all[1] = True
        self.mod.alll[0] = False
        self.assertFalse(self.mod.echo_fun(1))
        self.mod.alll[0] = True
        self.assertFalse(self.mod.echo_fun(1))

        self.mod.degree = MagicMock(return_value=1)
        self.mod.degree = MagicMock(return_value=1)
        self.assertTrue(self.mod.echo_fun(1))
    
    def test_config_set(self):
        # set all configs to BOTTOM
        for i in range(self.n):
            self.mod.config[i] = constants.BOTTOM
        # use wrapper to set [1,2] as config
        self.mod.config_set([1,2])
        # validate config_set
        for j in self.mod.config:
            self.assertEqual(self.mod.config[j], [1,2])
            self.assertEqual(self.mod.prp[j], constants.DFLT_NTF)
            
    def test_increment(self):
        # test transition from 1 to 2
        prp = (1, [1,2])
        self.assertEqual(self.mod.increment(prp), ((2, [1,2]), False))
        # test transition from 2 to 0
        prp = (2, [1,2])
        self.assertEqual(self.mod.increment(prp), (constants.DFLT_NTF, False))

        # catch-all clause in increment
        self.mod.alll[self.mod.id] = True
        self.mod.prp[self.mod.id] = (0, [2,3])
        prp = (0, [1,2])
        # should return its own prp as new_prp and alll[i] as ret
        new_prp, ret = self.mod.increment(prp)
        self.assertEqual((0, [2,3]), new_prp)
        self.assertTrue(ret)

    
    def test_all_seen_fun(self):
        # alll[i] is False, all_seen should return False
        self.mod.alll[self.mod.id] = False
        self.assertFalse(self.mod.all_seen_fun())

        # active participants not part of all_seen, should return False
        self.mod.get_fd_part_j = MagicMock(return_value=[2,3])
        self.mod.all_seen = [0,1]
        self.assertFalse(self.mod.all_seen_fun())

        # valid, should return True
        self.mod.get_fd_part_j = MagicMock(return_value=[0,1])
        self.mod.all_seen = {1,2,3}
        self.mod.alll[self.mod.id] = True
        self.assertTrue(self.mod.all_seen_fun())

    
    def test_mod_max(self):
        # TODO
        pass
    
    def test_max_ntf(self):
        # TODO
        pass
    
    # do-forever loop
    

if __name__ == '__main__':
    unittest.main()