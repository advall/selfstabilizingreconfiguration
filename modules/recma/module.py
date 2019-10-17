"""Contains code related to the RecMA module."""

# standard
import logging
import time
import datetime

# local
from modules.constants import RUN_SLEEP, BOTTOM
from resolve.enums import MessageType

# globals
logger = logging.getLogger(__name__)


class RecMAModule:
    """RecMA module"""

    # TODO look into quorum size
    def __init__(self, id, resolver, n, quorum_size=None):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.msgs_sent = 0

        # Algorithm variables:
        self.need_reconf = {}  # Dict where key is id and value is bool
        self.no_maj = {}  # Dict where key is id and value is bool
        self.prev_config = []
        self.quorum_size = quorum_size if quorum_size is not None else (n + 1) / 2

    # GETTERS for safe access to local dictionary variables:
    def get_need_reconf_j(self, j):
        return self.need_reconf[j] if j in self.need_reconf.keys() else False

    def get_no_maj_j(self, j):
        return self.no_maj[j] if j in self.no_maj.keys() else False

    # INTERFACE FUNCTIONS:

    def eval_config(self, conf):
        """ Evaluates the current configuration (conf).
            The criteria for predicting the need of a configuration can be
            chosen based on the application and other circumstances.
            Here, we suggest a reconfiguration if a quarter of the members are
            not trusted. This criterion is suggested as a simple example by the
            paper.

        Returns:
            bool: True if a reconfiguration is suggested, False otherwise.
        """
        num_trusted = len([j for j in conf if j in self.resolver.recsa_get_fd_j(self.id)])
        num_members = len(conf)
        return num_trusted < (3 * (num_members / 4)) or (num_trusted < self.quorum_size)

    # MACROS:

    def core(self):
        """
        Returns the intersection of the FD readings that p_i has for the
        processors in its own FD.
        """
        fd_i_part = self.resolver.recsa_get_fd_part_j(self.id)
        print(fd_i_part)
        if not fd_i_part:
            return []
        else:
            core_set = set(self.resolver.recsa_get_fd_part_j(fd_i_part[0]))
            for j in fd_i_part[1:]:
                fd_j_part = set(self.resolver.recsa_get_fd_part_j(j))
                core_set = core_set & fd_j_part
            return list(core_set)

    def flush_flags(self):
        fd_i = self.resolver.recsa_get_fd_j(self.id)
        for j in fd_i:
            self.need_reconf[j] = False
            self.no_maj[j] = False

    def run(self, testing=False):
        """ The main loop of the Reconfiguration Management module """

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)
 
        # Algorithm 3.2 in the technical report
        while True:
            # line 7:
            if self.id in self.resolver.recsa_get_fd_part_j(self.id):

                # line 8:
                cur_config = self.resolver.recsa_get_config()

                # line 9:
                self.need_reconf[self.id] = False
                self.no_maj[self.id] = False

                # line 10:
                if (set(self.prev_config) != set(cur_config)) and \
                    (self.prev_config != BOTTOM):
                    self.flush_flags()

                # line 11:
                if self.resolver.recsa_allow_reco():

                    # line 12:
                    self.prev_config = cur_config

                    # line 13:
                    self.no_maj[self.id] = \
                        len([j for j in cur_config if j in self.resolver.recsa_get_fd_j(self.id)]) \
                        < ((len(cur_config) // 2) + 1)
                    if self.no_maj[self.id]:
                        logger.debug("no_maj detected! Here is everyones no_maj:",
                                self.no_maj)

                    # lines 14-16:
                    if self.get_no_maj_j(self.id) and (len(self.core()) > 1) and \
                        (len([k for k in self.core() if self.get_no_maj_j(k)]) > 0):
                        self.resolver.recsa_estab(self.resolver.recsa_get_fd_part_j(self.id))
                        self.flush_flags()

                    # lines 17-19:
                    else:
                        self.need_reconf[self.id] = self.eval_config(cur_config)
                        if self.need_reconf[self.id]:
                            logger.debug("need_reconf detected! Here is everyones need_reconf:",
                                    self.need_reconf)
                        if self.get_need_reconf_j(self.id) and \
                            (len([j for j in cur_config if
                                (j in self.resolver.recsa_get_fd_j(self.id))
                                and self.get_need_reconf_j(j)])
                            > (len(cur_config) // 2)):
                            self.resolver.recsa_estab(self.resolver.recsa_get_fd_part_j(self.id))
                            self.flush_flags()

                # line 20:
                for j in self.resolver.recsa_get_fd_part_j(self.id):
                    self.send_state(j)
            else:
                logger.debug(f"RecMA did not perform its loop because not participant. Participants: {self.resolver.recsa_get_fd_part_j(self.id)}")

            logger.debug(f"Another iteration of main RecMA loop completed") 
            time.sleep(RUN_SLEEP)

    def receive_msg(self, msg):
        """Called whenever a message is received from another processor."""
        processor_j = msg["sender"]
        self.no_maj[processor_j] = msg["data"]["no_maj"]
        self.need_reconf[processor_j] = msg["data"]["need_reconf"]

    def send_state(self, receiver):
        """Sends a token to another processor."""

        # don't send to self
        if receiver == self.id:
            return

        # construct msg and send to other processor through resolver
        msg = {
            "type": MessageType.RECMA_MESSAGE,
            "sender": self.id,
            "data": {
                "no_maj": self.get_no_maj_j(self.id),
                "need_reconf": self.get_need_reconf_j(self.id)
            }
        }
        self.resolver.send_to_node(receiver, msg)
        self.msgs_sent += 1

    def broadcast(self, msg):
        """Broadcasts a message to all other processors."""
        for processor_id in range(self.number_of_nodes):
            if processor_id != self.id:
                self.send_msg(processor_id, msg, self.id)

    def get_data(self):
        """Called by the API, used to expose data to 3rd party services."""
        return {
            "need_reconf": self.need_reconf,
            "no_maj": self.no_maj
        }
