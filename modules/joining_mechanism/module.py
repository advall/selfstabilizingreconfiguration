"""Contains code related to the Joining Mechanism module."""

# standard
import logging
import time
import datetime

# local
from modules.constants import RUN_SLEEP, BOTTOM, NOT_PARTICIPANT
import modules.constants as constants
from resolve.enums import MessageType

# globals
logger = logging.getLogger(__name__)


class JoiningMechanismModule:
    """Joining Mechanism module"""

    def __init__(self, id, resolver, n):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.msgs_sent = 0

        # Algorithm variables:
        self.state = {}  # Dict where key is id and value is an application state
        self.passs = {}  # Dict where key is id and value is bool

    def reset_vars(self):
        """Initializes all variables related to the application based on default values."""
        logger.debug("reset_vars() was called. Not implemented yet.")
        # TODO: Implement

    def init_vars(self):
        """Initializes all variables related to the application based on the
        states exchanged with the configuration members."""
        logger.debug("init_vars() was called. Not implemented yet.")
        # TODO: Implement

    def pass_query(self):
        return True
        # TODO: Specific application needs should decide whether or not to accept new participant.
        #       (Either the application layer should expose an interface function that we should call from here,
        #       or the logic should be implemented here based on application needs.)

    def run(self, testing=False):
        """The main loop of the Joining Mechanism module."""

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        self.passs = {}
        for j in self.resolver.recsa_get_fd_j(self.id):
            self.passs[j] = False

        while True:
            # Algorithm 3.3 in the technical report
            if self.id not in self.resolver.recsa_get_fd_part_j(self.id):
                self.reset_vars()
                while self.id not in self.resolver.recsa_get_fd_part_j(self.id):
                    com_conf = self.resolver.recsa_get_config()
                    if com_conf in [NOT_PARTICIPANT, BOTTOM]:
                        com_conf = {}
                    num_trusted_member_passes = len(
                        [j for j in com_conf if j in self.resolver.recsa_get_fd_j(self.id) and self.passs[j] == True])
                    if self.resolver.recsa_allow_reco() and num_trusted_member_passes > (len(com_conf) / 2):
                        self.init_vars()
                        logger.info("Calling participate()")
                        self.resolver.recsa_participate()
                    for j in com_conf:
                        self.send_join_request(j)
                    time.sleep(RUN_SLEEP)
            time.sleep(RUN_SLEEP)

    def receive_msg(self, msg):
        """Called whenever a message is received from another processor."""
        processor_j = msg["sender"]
        data = msg["data"]
        if data == "JOIN":
            self.receive_join_request(processor_j)
        else:
            self.receive_response(processor_j, data)

    def receive_join_request(self, sender):
        """Called whenever a received message is a join request."""
        if sender not in self.resolver.recsa_get_fd_j(self.id):
            return
        if sender in self.resolver.recsa_get_fd_part_j(self.id):
            return
        if (self.id in self.resolver.recsa_get_config()) and self.resolver.recsa_allow_reco() == True:
            self.send_response(sender)

    def receive_response(self, sender, data):
        """Called whenever a received message is a response to a join request."""
        self.passs[sender] = data["pass"]
        self.state[sender] = data["state"]
        logger.debug(sender, data)

    def send_join_request(self, receiver):
        """Sends a join request to another processor."""

        # don't send to self
        if receiver == self.id:
            return

        # construct msg and send to other processor through resolver
        msg = {
            "type": MessageType.JOINING_MECHANISM_MESSAGE,
            "sender": self.id,
            "data": "JOIN"
        }
        self.resolver.send_to_node(receiver, msg)
        self.msgs_sent += 1

    def send_response(self, receiver):
        """Sends a response to a join request from another processor."""

        # construct msg and send to other processor through resolver
        msg = {
            "type": MessageType.JOINING_MECHANISM_MESSAGE,
            "sender": self.id,
            "data": {
                "pass": self.pass_query(),
                "state": self.state[self.id]
            }
        }
        self.resolver.send_to_node(receiver, msg)
        self.msgs_sent += 1

    def get_data(self):
        """Called by the API, used to expose data to 3rd party services."""
        return {
            "pass": self.passs,
            "state": self.state
        }
