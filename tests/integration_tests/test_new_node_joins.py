"""
This tests first starts the system with N number of nodes and waits a bit 
before launching another node. This new node is If no brute force reconfiguration
happens, this node should be able to join through participate and be a 
participant.
"""

# standard
import asyncio
import logging
import time

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest

logger = logging.getLogger(__name__)

class TestHealth(AbstractIntegrationTest):
    """Tests the joining of a node in the absence of brute force reconfiguration."""

    async def bootstrap(self):
        """Sets up the system for the test."""
        pids = await helpers.launch_system(__name__)
        await asyncio.sleep(5)
        return pids
    
    async def launch_joining_node(self):
        """Launches a new node through the joining script."""
        logger.info("Launching a joining node")
        return await helpers.launch_joining_node()

    async def validate(self):
        """Makes sure that the joining node (node 5) becomes a participant
        """
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        # TODO figure out how to check if participate() was called
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
        pids = helpers.run_coro(self.bootstrap())
        joining_node_pid = helpers.run_coro(self.launch_joining_node())
        pids = pids.append(joining_node_pid)

        super().set_pids(pids)

        helpers.run_coro(self.validate())
        logger.info(f"{__name__} finished")

    def tearDown(self):
        helpers.kill(super().get_pids())
        helpers.cleanup()

if __name__ == '__main__':
    asyncio.run(unittest.main())