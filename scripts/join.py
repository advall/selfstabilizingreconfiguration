"""Script used to start up a new node and let other nodes know about it.

When the system is currently running, in order to have a new node join the
network simply run this script such as

python scripts.py http://NODE_IP:400{NODE_ID}

where NODE is an existing, runnning node.

"""

import logging
import sys
import requests
import json
import subprocess
import os
import psutil
import time
import signal
import threading

FORMAT = "[%(levelname)s] : %(message)s"
level = logging.INFO
logging.basicConfig(format=FORMAT, level=level)
logger = logging.getLogger(__name__)
processes = []

def get_nodes_in_system(url):
    logger.info(f"Fetching nodes list from {url}")
    nodes = requests.get(f"{url}/nodes").json()
    return nodes

def get_node_details(n_id):
    return { "hostname": "localhost", "id": n_id, "ip": "127.0.0.1", "port": 5000 + n_id }

def publish(existing_nodes, new_node):
    logger.info(f"Publishing node with ID {new_node['id']} in the system")
    for n in existing_nodes.values():
        r = requests.post(f"http://{n['hostname']}:{4000+n['id']}/publish_node",
                          json=new_node)

def on_sig_term(signal, frame):
    logger.info(f"SIGTERM called, killing subprocess")
    for p in processes:
        process = psutil.Process(p.pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()
    sys.exit(0)


def launch(node, node_count):
    cmd = "source env/bin/activate && python main.py"
    cwd = "."
    env = os.environ.copy()
    node_id = node['id']

    env["ID"] = str(node_id)
    env["API_PORT"] = str(4000 + node_id)
    env["NUMBER_OF_NODES"] = str(node_count)
    env["WERKZEUG_RUN_MAIN"] = "true"  # no Flask output
    env["NUMBER_OF_CLIENTS"] = "1"

    logger.info(f"Launching node {node_id}")
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, env=env)
    processes.append(p)

if __name__ == "__main__":
    os.setpgrp()
    args = sys.argv
    if len(args) != 2:
        logger.error("Run as join.py API_URL")
        sys.exit(1)
    url = sys.argv[1]

    existing_nodes = get_nodes_in_system(url)
    node_id = len(existing_nodes)
    logger.info(f"Initiating joining for new node with ID {node_id}")
    new_node = get_node_details(node_id)

    publish(existing_nodes, new_node)
    time.sleep(3)
    launch(new_node, len(existing_nodes) + 1)

    signal.signal(signal.SIGINT, on_sig_term)
    forever = threading.Event()
    forever.wait()