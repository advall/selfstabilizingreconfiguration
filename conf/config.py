"""Module handling config related actions."""

# standard
import os
import logging
import jsonpickle

# local
from communication.zeromq.node import Node

# globals
logger = logging.getLogger(__name__)


def get_nodes(hosts_path="conf/hosts.txt"):
    """Parses nodes file to a dict of nodes such that dct[id] = node.

    Can be overridden by specifying the environment variable HOSTS_PATH, which
    corresponds to the absolute path to the desired hosts file.
    """
    if os.getenv("HOSTS_PATH"):
        hosts_path = os.getenv("HOSTS_PATH")
    try:
        with open(hosts_path) as f:
            lines = [x.strip().split(",") for x in f.readlines()]
            nodes = {}
            for l in lines:
                nodes[int(l[0])] = Node(id=l[0], hostname=l[1], ip=l[2],
                                        port=l[3])
            return nodes
    except FileNotFoundError as e:
        logger.error(e)


def get_other_nodes():
    """Helper that returns all other nodes in the system."""
    all_nodes = get_nodes()
    own_id = int(os.getenv("ID"))
    all_nodes.pop(own_id)
    return all_nodes


def get_start_state():
    """Gets start state for this node."""
    path = os.path.abspath("./conf/start_state.json")
    try:
        with open(path) as f:
            decoded = f.read().replace('\n', '')
            data = jsonpickle.decode(decoded)
            return data
    except FileNotFoundError:
        return {}

def add_node_to_hosts_file(new_node):
    """Writes a line representing new node to the hosts file.

    If running locally, only node 0 writes this file (avoid race cond).
    """
    n = get_nodes()[0]
    _id = int(os.getenv("ID"))
    if n.hostname == 'localhost':
        if _id != 0:
            return
    hosts_path = os.getenv("HOSTS_PATH", "conf/hosts.txt")
    logger.info(f"Writing new node {new_node} to hosts file")
    with open(hosts_path, "a") as f:
        f.write(f"{new_node.id},{new_node.hostname},{new_node.ip}, {new_node.port}\n")
