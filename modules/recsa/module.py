"""Contains code related to the RecMA module."""

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


class RecSAModule:
    """RecSA module"""

    def __init__(self, id, resolver, n, init_config=None):
        """Initializes the module."""
        self.resolver = resolver
        self.id = id
        self.number_of_nodes = n
        self.msgs_sent = 0

        # fallback to set init_config to node not being a participant
        # if init_config is None:
        # TODO port the whole first_booter logic to this setup
        init_config = {self.id: constants.BOTTOM}

        # Algorithm variables:
        self.config = init_config  # Dictionary where key is an id and value is a config (list)
        self.fd = {self.id: self.resolver.fd_get_trusted()}  # Dictionary where key is an id and value is a list of trusted ids
        self.fd_part = {self.id: []}  # Dictionary where key is an id and value is a list of trusted participants
        self.echo_part = {}
        self.echo_prp = {}
        self.echo_all = {}
        self.prp = {}  # Dictionary where key is an id and value is tuple (phase, set). set='BOTTOM' indicates 'no proposal'
        self.alll = {}  # Dictionary where key is an id and value is a Boolean
        self.all_seen = set()  # Set of id k for which p_i received the alll[k] indication

    # GETTERS for safe access to local dictionary variables:

    def get_config_j(self, j):
        return self.config[j] if j in self.config.keys() else []

    def get_fd_j(self, j):
        if j == self.id:
            return self.resolver.fd_get_trusted()
        else:
            return self.fd[j] if j in self.fd.keys() else []

    def get_fd_part_j(self, j):
        if j == self.id:
            fd_part_i = []
            for pj in self.get_fd_j(self.id):
                if pj in self.config.keys():
                    if self.get_config_j(pj) != constants.NOT_PARTICIPANT:
                        fd_part_i.append(pj)
            return fd_part_i
        else:
            return self.fd_part[j] if j in self.fd_part.keys() else []

    def get_echo_part_j(self, j):
        if j == self.id:
            return self.get_fd_part_j(self.id)
        else:
            return self.echo_part[j] if j in self.echo_part.keys() else []

    def get_echo_prp_j(self, j):
        if j == self.id:
            return self.get_prp_j(self.id)
        else:
            return self.echo_prp[j] if j in self.echo_prp.keys() else constants.DFLT_NTF

    def get_echo_all_j(self, j):
        if j == self.id:
            return self.get_all_j(self.id)
        else:
            return self.echo_all[j] if j in self.echo_all.keys() else False
            # Assumption: a non-reported all[] value should be treated as False.

    def get_prp_j(self, j):
        return self.prp[j] if j in self.prp.keys() else constants.DFLT_NTF

    def get_all_j(self, j):
        return self.alll[j] if j in self.alll.keys() else False
        # Assumption: a non-reported all[] value should be treated as False.

    # INTERFACE FUNCTIONS:
    def get_config(self):
        """Returns the current quorum configuration, i.e. config[i]
        
        May return # if p_i is not a participant or BOTTOM during the process
        of a configuration reset
        """
        if self.allow_reco():
            return self.chs_config()
        else:
            return self.get_config_j(self.id)

    def get_config_app(self):
        """Returns the current quorum configuration (config[i]) to application

        Returns config[i] when no reconfiguration occurs or no agreement on
        proposal. Once participants agree on proposal, returns proposal set U
        current configuration.
        """
        if self.degree(self.id) in [0, 1, 2]:
            return self.get_config_j(self.id)
        else:
            return list(set(self.get_config_j(self.id)) | set(self.get_prp_j(self.id)[1]))

    def allow_reco(self):
        fd_of_trusted = []
        part_of_trusted = [set(self.get_fd_part_j(self.id))]
        no_reset = True
        all_dflt_ntf = True
        for j in self.get_fd_j(self.id):
            if j != self.id:
                fd_of_trusted.append(set(self.get_fd_j(j)))
                part_of_j = set(self.get_fd_part_j(j)).union(set(self.get_echo_part_j(j)))
                if part_of_j not in part_of_trusted:
                    part_of_trusted.append(part_of_trusted)
            if self.get_config_j(j) == constants.BOTTOM:
                no_reset = False
            if (self.get_prp_j(j) != constants.DFLT_NTF) or \
                  (not self.get_all_j(j)):
                all_dflt_ntf = False
        trusted_by_trusted = False if fd_of_trusted == [] \
            else self.id in set.intersection(*fd_of_trusted)
        part_stabilized = len(part_of_trusted) == 1
        all_part_echo = True
        for k in self.get_fd_part_j(self.id):
            if not self.echo_fun(k):
                all_part_echo = False
        return (not self.config_conflict()) and self.all_seen_fun() and \
               all_part_echo and trusted_by_trusted and part_stabilized and \
               no_reset and all_dflt_ntf

    def estab(self, s):
        """Interface for RecMA to request configuration update

        Used to replace the configuration by the RecMA module. Proposed set
        must be non-empty and not the same as current conf.
        """
        logger.info("Running estab(set) with set:", s)
        if self.allow_reco() and (set(s) not in [set(), set(self.get_config_j(self.id))]):
            logger.info("estab() allowed!")
            self.prp[self.id] = (1, s)
            self.alll[self.id] = False
            self.all_seen = set()

    def participate(self):
        """Interface for Joining mechanism to request a join for p_i."""
        if self.allow_reco():
            self.config[self.id] = self.chs_config()

    # MACROS:
    def chs_config(self):
        """Returns config whenever there is a single such non-# value.

        Returns BOTTOM if no config exists.
        """
        conf = set()
        for j in self.get_fd_j(self.id):
            if self.get_config_j(j) != constants.NOT_PARTICIPANT:
                conf |= set(self.get_config_j(j))
        if conf == set():
            return constants.BOTTOM
        else:
            return list(conf)

    def my_alll(self, k):
        """Returns either the value stored in all[k] or if k == i,
        whether there exists p_l one phase "ahead" of p_i
        """
        all_k = self.get_all_j(k)
        exists_pl_ahead = False
        ahead = (self.get_prp_j(self.id)[0] + 1) % 3
        for l in self.all_seen:
            if self.get_prp_j(l)[0] == ahead:
                exists_pl_ahead = True
        return all_k or ((k == self.id) and exists_pl_ahead)

    def degree(self, k):
        """Calculates the degree of p_k's most recently received notification

        Calculated as twice the notification phase plus one whenever all
        participants are using the same notification (0 otherwise), where each
        notification is a configuration replacement proposal.
        """
        one_if_my_all_k = 1 if self.my_alll(k) else 0
        return (2 * self.get_prp_j(k)[0]) + one_if_my_all_k

    def corr_deg(self, k, k_prime):
        """Tests whether p_k and p_k' have degrees that differ by <= 1

        Used when considering operations in mod 6
        """
        ok_deg_tups = [{0, 5}, {5, 5}]
        for x in range(0, 5):
            ok_deg_tups.append({x, x+1})
            ok_deg_tups.append({x, x})
        return {self.degree(k), self.degree(k_prime)} in ok_deg_tups

    def echo_no_all(self, k):
        """Tests whether p_i was acked by all participants for the values it has sent.
        
        Considers just the fields that are related to its own participant set
        and notification.
        """
        same_fd_part = set(self.get_fd_part_j(self.id)) == set(self.get_echo_part_j(k))
        (phase_i, set_i) = self.get_prp_j(self.id)
        (phase_k, set_k) = self.get_echo_prp_j(k)
        same_prp = (phase_i == phase_k) and (set(set_i) == set(set_k))
        return same_fd_part and same_prp

    def echo_fun(self, k):
        """Tests whether p_k was acked by all participants for the values it has sent.
        
        Considers the fields that are related to its own participant set
        and notification as well as all[].
        """
        same_all = self.my_alll(self.id) == self.get_echo_all_j(k)
        ok_deg = ((self.degree(k) - self.degree(self.id)) % 6) in {0, 1}
        return self.echo_no_all(k) and same_all and ok_deg

    def config_set(self, val):
        """Wrapper to modify config of this processor.

        Acts as a wrapper function for accessing pi’s local copies of the field config.
        This macro also makes sure that there are no (local) active notifications.
        """
        for k in range(self.number_of_nodes):
            self.config[k] = val
            self.prp[k] = constants.DFLT_NTF
        logger.info(f"Set config to {self.config}")

    def increment(self, prp):
        """Performs the transition between phases of the delicate reconfiguration."""
        (prp_phase, prp_set) = prp
        if prp_phase == 1:
            return ((2, prp_set), False)
        elif prp_phase == 2:
            return (constants.DFLT_NTF, False)
        else:
            return (self.get_prp_j(self.id), self.get_all_j(self.id))

    def all_seen_fun(self):
        """Tests whether all active participants have noticed that all other participants
        have finished the current phase.
        """
        return self.get_all_j(self.id) and \
               (set(self.get_fd_part_j(self.id)) <= (self.all_seen | {self.id}))

    def mod_max(self):
        """Returns maximum phase value of two processors considering mod 3 operations.

        Assumes that no two processors in FD[i].part have two notifications that p_i
        stores for which the degree differs by more than one.
        """
        phs = set()
        for k in self.get_fd_part_j(self.id):
            phs.add(self.get_prp_j(k)[0])
        if (1 in phs) and (2 not in phs) and (self.get_prp_j(self.id)[0] != max(phs)):
            self.all_seen = set()
            return max(phs)
        else:
            return self.get_prp_j(self.id)[0]

    def max_ntf(self):
        """Selects notification with maximal lexicographical value.
        
        Returns BOTTOM in the absence of notification that is not phase 0 notification.
        """
        deg_diffs = set()
        for k in self.get_fd_part_j(self.id):
            deg_diff = (self.degree(k) - self.degree(self.id)) % 6
            deg_diffs.add(deg_diff)
        if not (deg_diffs <= {0, 1}):
            return self.get_prp_j(self.id)
        else:
            max_lex_set = constants.BOTTOM
            for k in self.get_fd_part_j(self.id):
                max_lex_set = self.max_lex(max_lex_set, self.get_prp_j(k)[1])
            return (self.mod_max(), max_lex_set)

    def run(self, testing=False):
        """The main loop of the Reconfiguration Stability Assurance module"""

        # block until system is ready
        while not testing and not self.resolver.system_running():
            time.sleep(0.1)

        while True:
            # Update some local variables
            # self.fd[self.id] = self.get_fd_j(self.id)

            # Algorithm 3.1 in the technical report
            # line 22:
            trusted = self.get_fd_part_j(self.id)
            for k in range(self.number_of_nodes):
                if k not in trusted:
                    self.config[k] = constants.NOT_PARTICIPANT
                    self.prp[k] = constants.DFLT_NTF

            # line 23:
            self.prp[self.id] = self.max_ntf()

            # line 25:
            all_no_all = True
            for k in self.get_fd_part_j(self.id):
                if not self.echo_no_all(k):
                    all_no_all = False
            self.alll[self.id] = all_no_all

            # line 26:
            for k in self.get_fd_part_j(self.id):
                if self.get_all_j(k):
                    self.all_seen.add(k)

            # line 24:
            if self.stale_info_type_1() or \
                self.stale_info_type_2() or \
                self.stale_info_type_3() or \
                self.stale_info_type_4():
                self.config_set(constants.BOTTOM)

            # lines 27-32:
            if self.no_ntf_arrived():
                if self.config_conflict():
                    logger.debug("Stale info (config conflict) found!")
                    self.config_set(constants.BOTTOM)
                if (self.get_config_j(self.id) == constants.BOTTOM) and self.fds_stabilized():
                    self.config_set(self.get_fd_j(self.id))
            else:
                if (self.get_prp_j(self.id)[0] == 2) and self.get_all_j(self.id):
                    self.config[self.id] = self.get_prp_j(self.id)[1]
                if self.all_seen_fun():
                    echo_fun_all = True
                    for k in self.get_fd_part_j(self.id):
                        if not self.echo_fun(k):
                            echo_fun_all = False
                    if echo_fun_all:
                        (self.prp[self.id], self.alll[self.id]) = self.increment(self.get_prp_j(self.id))
                        self.all_seen = set()

            # line 33:
            if self.get_config_j(self.id) != constants.NOT_PARTICIPANT:
                for j in self.get_fd_j(self.id):
                    self.send_state(j)
            else:
                logger.debug(f"Node not a participant, not sending state")

            logger.info(f"Another iteration of main RecSA loop completed") 
            time.sleep(RUN_SLEEP)


    # HELPER FUNCTIONS:

    def stale_info_type_1(self):
        """Stale info check - type 1
        
        Tests that all notifications of configuration proposals are valid.
        """
        for k in self.prp.keys():
            if (self.get_prp_j(k)[0] == 0) and (self.get_prp_j(k)[1] != constants.BOTTOM):
                logger.debug("Stale info (type 1) found!")
                return True
        return False

    def stale_info_type_2(self):
        """Stale info check - type 2
        
        Tests that there are no configuration conflicts or an active reset
        process
        """
        config_values = self.config.values()
        bot_exists = constants.BOTTOM in config_values
        empty_exists = [] in config_values
        if bot_exists or empty_exists:
            logger.debug(f"Stale info (type 2) found! Current config: {self.config}")
        return bot_exists or empty_exists

    def stale_info_type_3(self):
        """Stale info check - type 3

        Tests that the phase information, including all_seen, are not out of
        synch
        """
        type_3_a = False
        type_3_b_set = set()
        prp_sets = []
        exists_phase_2 = False
        for k in self.get_fd_part_j(self.id):
            if not self.corr_deg(self.id, k):
                type_3_a = True
            if self.get_prp_j(k)[0] == ((self.get_prp_j(self.id)[0] + 1) % 3):
                type_3_b_set.add(k)
            prp_k_set = self.get_prp_j(k)[1]
            if (prp_k_set != constants.BOTTOM) and \
                  (set(prp_k_set) not in prp_sets):
                prp_sets.append(set(prp_k_set))
            if self.get_prp_j(k)[0] == 2:
                exists_phase_2 = True
        type_3_b = not (type_3_b_set <= self.all_seen)
        type_3_c = exists_phase_2 and (len(prp_sets) > 1)
        type_3 = type_3_a or type_3_b or type_3_c
        if type_3:
            logger.debug("Stale info (type 3) found!")
        return type_3

    def stale_info_type_4(self):
        """Stale info check - type 4

        Tests that there are active participants in the config
        """
        if self.get_fd_part_j(self.id) == []:
            type_4_a = False
        else:
            type_4_a = True
            for k in self.get_fd_part_j(self.id):
                different_fd = self.get_fd_j(self.id) != self.get_fd_j(k)
                different_fd_part = self.get_fd_part_j(self.id) != self.get_fd_part_j(k)
                if different_fd or different_fd_part:
                    type_4_a = False
        type_4_b = self.get_config_j(self.id) != constants.BOTTOM
        if self.get_config_j(self.id) in [constants.BOTTOM, constants.NOT_PARTICIPANT]:
            type_4_c = True
        else:
            type_4_c = True
            for k in self.get_fd_part_j(self.id):
                if k in self.get_config_j(self.id):
                    type_4_c = False
        type_4 = type_4_a and type_4_b and type_4_c
        if type_4:
            logger.debug("Stale info (type 4) found!")
        return type_4

    def no_ntf_arrived(self):
        ntf_arrived = False
        for k in self.get_fd_part_j(self.id):
            if self.get_prp_j(k)[0] != 0:
                ntf_arrived = True
        return not ntf_arrived

    def config_conflict(self):
        real_configs_found = []
        for k in self.get_fd_j(self.id):
            if self.get_config_j(k) not in [constants.BOTTOM, constants.NOT_PARTICIPANT]:
                config_k = set(self.get_config_j(k))
                if config_k not in real_configs_found:
                    real_configs_found.append(config_k)
        return len(real_configs_found) > 1

    def fds_stabilized(self):
        fd_i = set(self.get_fd_j(self.id))
        for j in self.get_fd_j(self.id):
            if set(self.fd.get(j, [])) != fd_i:
                logger.debug("FDs have not stabilized")
                return False
        logger.debug("FDs have stabilized!")
        return True

    def max_lex(self, s1, s2):
        if s1 == constants.BOTTOM:
            return s2
        if s2 == constants.BOTTOM:
            return s1
        s1_sorted = sorted(s1)
        s2_sorted = sorted(s2)
        return max(s1_sorted, s2_sorted)

    def receive_msg(self, msg):
        """Called whenever a message is received from another processor."""
        self.fd[self.id] = self.get_fd_j(self.id)

        # Update state values
        j = int(msg["sender"])
        data = msg["data"]
        self.fd[j] = data["fd"]
        self.fd_part[j] = data["fd_part"]
        self.config[j] = data["config"]
        self.prp[j] = data["prp"]
        self.alll[j] = data["alll"]
        self.echo_part[j] = data["echo_fd_part"]
        self.echo_prp[j] = data["echo_prp"]
        self.echo_all[j] = data["echo_all"]
    
    def send_state(self, receiver):
        data = {
            "fd": self.get_fd_j(self.id),
            "fd_part": self.get_fd_part_j(self.id),
            "config": self.get_config_j(self.id),
            "prp": self.get_prp_j(self.id),
            "alll": self.my_alll(self.id),
            "echo_fd_part": self.get_fd_part_j(receiver),
            "echo_prp": self.get_prp_j(receiver),
            "echo_all": self.get_all_j(receiver)
        }
        msg = {
            "type": MessageType.RECSA_MESSAGE,
            "sender": self.id,
            "data": data
        }
        self.resolver.send_to_node(receiver, msg)

    def get_data(self):
        """Called by the API, used to expose data to 3rd party services."""
        return {
            "fd": self.get_fd_j(self.id),
            "fd_part": self.get_fd_part_j(self.id),
            "config": self.config,
            # "config": self.get_config_j(self.id),
            "prp": self.get_prp_j(self.id),
            "alll": self.my_alll(self.id)
        }
