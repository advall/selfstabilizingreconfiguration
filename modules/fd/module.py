"""Contains code related to the Primary Monitoring module."""

# standard
import logging
from copy import deepcopy
import time
import os

# local
from resolve.enums import Function, Module
from modules.constants import CNT_THRESHOLD, BEAT_THRESHOLD
from resolve.enums import MessageType
from queue import Queue
import conf.config as conf
from communication.zeromq.rate_limiter import throttle
import modules.byzantine as byz

# globals
logger = logging.getLogger(__name__)


class FDModule:
    """Models the (N, THETA) failure detector."""

    first_run = True

    def __init__(self, id, resolver, n):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.beat = [0 for i in range(n)]
        self.monitor = [0 for i in range(n)]
        self.cnt = 0
        self.cur_check_req = []
        self.fd_set = set()
        self.prim = -1
        self.msg_queue = Queue()
        self.was_unresponsive = False

        if os.getenv("INTEGRATION_TEST") or os.getenv("INJECT_START_STATE"):
            start_state = conf.get_start_state()
            if (start_state is not {} and str(self.id) in start_state and
               "FAILURE_DETECTOR_MODULE" in start_state[str(self.id)]):
                data = start_state[str(self.id)]["FAILURE_DETECTOR_MODULE"]
                if data is not None:
                    logger.warning("Injecting start state")
                    if "beat" in data:
                        self.beat = deepcopy(data["beat"])
                    if "cnt" in data:
                        self.cnt = deepcopy(data["cnt"])
                    if "cur_check_req" in data:
                        self.cur_check_req = deepcopy(data["cur_check_req"])
                    if "prim" in data:
                        self.prim = deepcopy(data["prim"])

    def run(self, testing=False):
        """Called whenever the module is launched in a separate thread."""
        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            if self.msg_queue.empty():
                time.sleep(0.1)
            else:
                msg = self.msg_queue.get()
                processor_j = msg["sender"]
                self.upon_token_from_pj(processor_j)
                self.send_msg(processor_j)

            if testing:
                break

            if self.first_run:
                nodes = conf.get_nodes()
                for node_j, _ in nodes.items():
                    if node_j != self.id:
                        self.send_msg(node_j)
                self.first_run = False

            throttle()

    def upon_token_from_pj(self, processor_j):
        """Checks responsiveness and liveness of processor j."""
        self.beat[processor_j] = 0
        self.beat[self.id] = 0

        self.monitor[processor_j] = min(self.monitor[processor_j] + 1, 3)
        self.monitor[self.id] = min(self.monitor[processor_j] + 1, 3)

        new_fd_set = {processor_j, self.id}
        for other_processor in range(self.number_of_nodes):
            if other_processor == self.id or other_processor == processor_j:
                continue
            self.beat[other_processor] += 1
            if self.beat[other_processor] < BEAT_THRESHOLD:
                new_fd_set.add(other_processor)
        self.fd_set = deepcopy(new_fd_set)

    # Macros
    def reset(self):
        """Resets local variables."""
        logger.debug("Reset Failure Detector")
        self.beat = [0 for i in range(self.number_of_nodes)]
        self.monitor = [0 for i in range(self.number_of_nodes)]
        self.cnt = 0
        self.cur_check_req = []

    # Interface functions
    def get_trusted(self):
        """Returns the set of trusted processors."""
        return self.fd_set

    def reset_monitor(self, processor_j):
        """Resets the FD monitor counter for a specified processor"""
        self.monitor[processor_j] = 0

    def stable_monitor(self, processor_j):
        return self.monitor[processor_j] == 3

    # Functions to send messages to other nodes
    def send_msg(self, processor_j):
        """Method description.

        Calls the Resolver to send a message containing the vcm of processor i
        to processor_j
        """
        msg = {
            "type": MessageType.FAILURE_DETECTOR_MESSAGE,
            "sender": self.id
        }
        self.resolver.send_to_node(processor_j, msg, fd_msg=True)

    def receive_msg(self, msg):
        """Method description.

        Called by the Resolver to recieve a message containing the vcm of
        processor j
        """
        self.msg_queue.put(msg)

    # Function to extract data
    def get_data(self):
        """Returns current values on local variables."""
        return {
            "id": self.id,
            "beat": deepcopy(self.beat),
            "cnt": deepcopy(self.cnt),
            "cur_check_req": deepcopy(self.cur_check_req),
            "prim_fd": deepcopy(self.prim)
        }
