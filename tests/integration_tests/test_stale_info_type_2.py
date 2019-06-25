"""
Tests that the system recovers from a stale information of type 2

This is done by launching the system and letting it run for 10 seconds, before
injecting a different configuration at one node which should trigger a brute
force reconfiguration.
"""

# standard
import asyncio
import logging
import time

# local
from . import helpers
from .abstract_integration_test import AbstractIntegrationTest

logger = logging.getLogger(__name__)

class TestStaleInformationType1(AbstractIntegrationTest):
    """Tests that the system can recover from stale information type 1."""

    async def bootstrap(self):
        """Sets up the system for the test."""
        return await helpers.launch_system(__name__)

    async def inject_stale_info(self):
        """Injects stale information of type 1 in the system."""
        res = await helpers.GET(0, "/data")
        conf = res["data"]["RECSA_MODULE"]["config"]["0"]
        new_conf = conf[1:]
        await helpers.POST(0, "/inject_conf", data={ "conf": new_conf })

    async def validate(self):
        """Validates response from / endpoint on all nodes
        
        This method runs for at most helpers.MAX_NODE_CALLS times, then it
        will fail the test if target state is not reached.
        """
        calls_left = helpers.MAX_NODE_CALLS
        test_result = False

        while calls_left > 0:
            aws = [helpers.GET(i, "/data") for i in helpers.get_nodes()]
            checks = []
            last_check = calls_left == 1

            # waits for all health check calls to complete
            # TODO express target state appropriately
            for a in asyncio.as_completed(aws):
                result = await a
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
        time.sleep(10)
        helpers.run_coro(self.inject_stale_info())
        
        super().set_pids(pids)

        helpers.run_coro(self.validate())
        logger.info(f"{__name__} finished")

    def tearDown(self):
        helpers.kill(super().get_pids())
        helpers.cleanup()

if __name__ == '__main__':
    asyncio.run(unittest.main())