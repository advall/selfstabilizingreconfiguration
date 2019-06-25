"""Contains code related to the module resolver."""

# standard
import logging
from threading import Thread
import os
import requests
import time
import asyncio

# local
from resolve.enums import Module, MessageType, SystemStatus
from conf.config import get_nodes
from communication.zeromq import rate_limiter
from metrics.messages import msgs_sent
from communication.zeromq.sender import Sender
from communication.udp.sender import Sender as FDSender

# globals
logger = logging.getLogger(__name__)


class Resolver:
    """Module resolver that facilitates communication between modules."""

    def __init__(self, testing=False):
        """Initializes the resolver."""
        self.modules = None
        self.senders = {}
        self.fd_senders = {}
        self.receiver = None
        self.fd_receiver = None
        self.nodes = get_nodes()
        self.id = int(os.getenv("ID", 0))

        self.own_comm_ready = False
        self.other_comm_ready = False
        self.system_status = SystemStatus.BOOTING

        # check other nodes for system ready before starting system
        if not testing:
            t = Thread(target=self.wait_for_other_nodes)
            t.start()

        # inject resolver in rate limiter module
        rate_limiter.resolver = self

        # Support non-self-stabilizing mode
        self.self_stab = os.getenv("NON_SELF_STAB") is None

    def wait_for_other_nodes(self):
        """Write me."""
        if len(self.nodes) == 1:
            self.other_comm_ready = True
            return

        system_ready = False
        while not system_ready:
            nodes_ready = []
            for n_id, node in self.nodes.items():
                try:
                    r = requests.get(f"http://{node.hostname}:{4000 + n_id}")
                    is_ready = (r.status_code == 200 and
                                r.json()["status"] !=
                                SystemStatus.BOOTING.name)
                    nodes_ready.append(is_ready)
                except Exception:
                    nodes_ready.append(False)
            system_ready = all(nodes_ready)
            if not system_ready:
                time.sleep(0.1)
        self.system_status = SystemStatus.RUNNING
        logger.info(f"System running at UNIX time {time.time()}")

    # Interface functions
    def fd_get_trusted(self):
        if self.system_running():
            return self.modules[Module.FAILURE_DETECTOR_MODULE].get_trusted()
        return []
    
    def recsa_get_fd_j(self, j):
        return self.modules[Module.RECSA_MODULE].get_fd_j(j)

    def recsa_get_fd_part_j(self, j):
        return self.modules[Module.RECSA_MODULE].get_fd_part_j(j)
    
    def recsa_get_config(self):
        return self.modules[Module.RECSA_MODULE].get_config()
    
    def recsa_estab(self, s):
        return self.modules[Module.RECSA_MODULE].estab(s)
    
    def recsa_allow_reco(self):
        return self.modules[Module.RECSA_MODULE].allow_reco()

    def recsa_participate(self):
        return self.modules[Module.RECSA_MODULE].participate()
    
    # Helpers

    def system_running(self):
        """Return True if the system as a whole i running."""
        return self.system_status == SystemStatus.RUNNING

    def set_modules(self, modules):
        """Sets the modules dict of the resolver."""
        self.modules = modules

    # inter-node communication methods
    def send_to_node(self, node_id, msg_dct, fd_msg=False):
        """Sends a message to a given node.

        Message should be a dictionary, which will be serialized to json
        and converted to a byte object before sent over the links to
        the other node.
        """
        if node_id == self.id:
            return

        if node_id not in self.senders and node_id not in self.fd_senders:
            logger.error(f"Non-existing sender for node {node_id}")

        sender = (self.senders[node_id] if not fd_msg else
                  self.fd_senders[node_id])
        try:
            sender.add_msg_to_queue(msg_dct)
        except Exception as e:
            logger.error(f"Something went wrong when sending msg {msg_dct} " +
                         f"to node {node_id}. Error: {e}")

    def broadcast(self, msg_dct):
        """Broadcasts a message to all nodes."""
        for node_id, _ in self.senders.items():
            self.send_to_node(node_id, msg_dct)

    def dispatch_msg(self, msg):
        """Routes received message to the correct module."""
        msg_type = msg["type"]
        if msg_type == MessageType.RECMA_MESSAGE:
            self.modules[Module.RECMA_MODULE].receive_msg(msg)
        elif msg_type == MessageType.RECSA_MESSAGE:
            self.modules[Module.RECSA_MODULE].receive_msg(msg)
        elif msg_type == MessageType.FAILURE_DETECTOR_MESSAGE:
            self.modules[Module.FAILURE_DETECTOR_MODULE].receive_msg(msg)
        elif msg_type == MessageType.JOINING_MECHANISM_MESSAGE:
            self.modules[Module.JOINING_MECHANISM_MODULE].receive_msg(msg)
        else:
            logger.error(f"Message with invalid type {msg_type} cannot be" +
                         " dispatched")

    def on_message_sent(self, msg={}, metric_data={}):
        """Callback function when a communication module has sent the message.

        Used for metrics.
        """
        id = int(os.getenv("ID"))
        # emit message sent message
        msgs_sent.labels(id).inc()

    def get_recsa_module_data(self):
        return self.modules[Module.RECSA_MODULE].get_data()

    def get_recma_module_data(self):
        return self.modules[Module.RECMA_MODULE].get_data()

    def get_joining_mechanism_module_data(self):
        return self.modules[Module.JOINING_MECHANISM_MODULE].get_data()
    
    def run_sender_in_new_thread(self, new_node):
        # set up new sender
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.senders[new_node.id] = Sender(id, new_node, self.on_message_sent)
        loop.create_task(self.senders[new_node.id].start())
        loop.run_forever()
        loop.close()
    
    def refresh(self, new_node):
        """Called by API when a new node has been added to the system.
        
        Sets up communication channels etc.
        """
        self.nodes = get_nodes()

        # update modules
        self.modules[Module.RECMA_MODULE].number_of_nodes = len(self.nodes)
        self.modules[Module.RECSA_MODULE].number_of_nodes = len(self.nodes)
        self.modules[Module.FAILURE_DETECTOR_MODULE].number_of_nodes = len(self.nodes)
        self.modules[Module.FAILURE_DETECTOR_MODULE].beat += [0]
        self.modules[Module.JOINING_MECHANISM_MODULE].number_of_nodes = len(self.nodes)

        Thread(target=self.run_sender_in_new_thread, args=(new_node,)).start()

        # set up new fd sender
        new_fd_sender = FDSender(id, (new_node.hostname, 7000 + new_node.id),
                              check_ready=self.system_running,
                              on_message_sent=self.on_message_sent)
        self.fd_senders[new_node.id] = new_fd_sender
        Thread(target=self.fd_senders[new_node.id].start).start()

        logger.info(f"System refreshed, now {len(self.nodes)} nodes in system")
    
    def inject_conf(self, new_conf):
        """Helper used to inject a configuration in the RecSA module."""
        return self.modules[Module.RECSA_MODULE].config_set(new_conf)

    def inject_prp(self, new_prp):
        """Helper used to inject a proposal in the RecSA module."""
        return self.modules[Module.RECSA_MODULE].prp_set(new_prp)
