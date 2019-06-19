"""
This tests first starts the system with X number of nodes and waits a bit 
before killing Y nodes. in the absence of a brute force reconfiguration, estab()
should be called by at least one node and all nodes should move through their
phases back to dflt_ntf.

NOTE that this assumes that brute force reconfiguration is not triggered
during the test, so watch out for that.
"""

# standard
import asyncio
import logging
import time

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest

logger = logging.getLogger(__name__)

X = 5
Y = 2

class TestEstabCalledWhenNodesAreKilled(AbstractIntegrationTest):
    """Tests that estab() is called when nodes are killed, before the nodes move through their phases."""

    async def bootstrap(self):
        """Sets up the system for the test."""
        pids = await helpers.launch_system(__name__, n=X)
        await asyncio.sleep(5)
        return pids
    
    async def kill_nodes(self):
        """Kills Y nodes."""
        for i in range(X-1, X-1-Y, -1):
            await helpers.kill_node(i)

    async def validate(self):
        """Makes sure that the joining node (node 5) becomes a participant
        """
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        # TODO figure out how to check if estab() was called
        # how assert?
        while calls_left > 0:
            aws = [helpers.GET(4, "/data")]
            checks = []
            last_check = calls_left == 1

            # waits for all health check calls to complete
            for a in asyncio.as_completed(aws):
                result = await a

                # always fail for now
                checks.append(False)

            # if all checks were true, test passed
            if all(checks):
                test_result = True
                break

            # sleep for 2 seconds and then re-try
            await asyncio.sleep(2)
            calls_left -= 1
        self.assertTrue(test_result)

    @helpers.suppress_warnings
    def test(self):
        logger.info(f"{__name__} starting")
        # setup system
        pids = helpers.run_coro(self.bootstrap())

        # kill Y nodes
        helpers.run_coro(self.kill_nodes())

        super().set_pids(pids)

        # run validation method
        helpers.run_coro(self.validate())
        logger.info(f"{__name__} finished")

    def tearDown(self):
        helpers.kill(super().get_pids())
        helpers.cleanup()

if __name__ == '__main__':
    asyncio.run(unittest.main())