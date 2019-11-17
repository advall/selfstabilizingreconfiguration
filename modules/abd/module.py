"""Contains code related to the ABD module."""

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


class ABDModule:
    """ABD module
    
    Implements SingleWriterMultiReader with read/write operations both using
    communicate procedure as developed by Attiya et al. Value and label is
    considered the same in this algorithm and it should be noted that the
    writes are (for now) only incrementing the value in the register.
    """

    def __init__(self, id, resolver, n):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n

        # Algorithm variables
        self.label = 0
        self.status = {}
        self.info = {}
        self.no_acks = 0
        self.communicate_msg = None
        self.communicating = False

    def run(self, testing=False):
        """The main loop of the Joining Mechanism module."""

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        # busy-wait forever
        while True:
            time.sleep(RUN_SLEEP)

    def read(self):
        # request labels from all nodes in system
        msg = { "type": constants.READ_REQUEST }
        self.communicate(msg)

        # get highest label
        label = -1
        for j in self.resolver.recsa_get_config_app():
            if isinstance(self.info.get(j, -1), int) and (self.info.get(j, -1) > label):
                label = self.info[j]
        self.label = label
        
        # confirm read of label
        msg = { "type": constants.READ_CONFIRM, "label": self.label }
        self.communicate(msg)

        # finish up read and return register
        logger.info(f"Read value/label {self.label} in register")
        return { "value": self.label, "label": self.label }
    
    def write(self):
        # increment label (and value)
        self.label += 1
        
        # notify all other nodes of writing label/value
        msg = { "type": constants.WRITE, "label": self.label }
        self.communicate(msg)

        # finish up write and return register
        logger.info(f"Wrote value/label {self.label} to register")
        return { "value": self.label, "label": self.label }

    def communicate(self, msg):
        self.communicating = True
        self.no_acks = 0
        self.communicate_msg = msg
        logger.info(f"Communicating msg {msg} to other nodes")

        for j in self.resolver.recsa_get_config_app():
            self.status[j] = constants.NOT_ACKED
            self.info[j] = constants.BOT
            self.send_msg(msg, j)
        
        # busy-wait until no_acks > (n + 1) / 2
        while self.no_acks < (len(self.resolver.recsa_get_config_app()) + 1) / 2:
            time.sleep(1)
        self.communicating = False

    def receive_msg(self, msg):
        """Called whenever a message is received from another processor."""
        j = msg["sender"]
        data = msg["data"]

        if j not in self.resolver.recsa_get_config_app():
            return

        msg_type = data["type"]
        if msg_type == constants.WRITE:
            self.label = max(data["label"], self.label)
            _msg = { "type": constants.WRITE_ACK }
            self.send_msg(_msg, j)
        elif msg_type == constants.READ_REQUEST:
            _msg = { "type": constants.READ_REQUEST_ACK, "label": self.label }
            self.send_msg(_msg, j)
        elif msg_type == constants.READ_CONFIRM:
            self.label = max(data["label"], self.label)
            _msg = { "type": constants.READ_CONFIRM_ACK }
            self.send_msg(_msg, j)

        if self.communicating:
            if msg_type == constants.READ_REQUEST_ACK:
                if self.status[j] == constants.NOT_ACKED:
                    self.status[j] = constants.ACKED
                    self.info[j] = msg["data"]["label"]
            self.no_acks += 1
    
    def send_msg(self, data, j):
        msg = {
            "type": MessageType.ABD_MESSAGE,
            "sender": self.id,
            "data": data
        }
        self.resolver.send_to_node(j, msg)
    
    def get_data(self):
        return {
            "is_writer": self.id == 0,
            "value": self.label,
            "label": self.label,
            "info": self.info,
            "status": self.status
        }