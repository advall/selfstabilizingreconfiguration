"""Main script for application."""

# standard
import asyncio
import os
import logging
from threading import Thread

# external
from prometheus_client import start_http_server

# local
from communication.zeromq.sender import Sender
from communication.zeromq.receiver import Receiver
from communication.udp.sender import Sender as FDSender
from communication.udp.receiver import Receiver as FDReceiver
import conf.config as config
from api.server import start_server
from modules.recma.module import RecMAModule
from modules.recsa.module import RecSAModule
from modules.fd.module import FDModule
from modules.joining_mechanism.module import JoiningMechanismModule
from modules.abd.module import ABDModule
from resolve.enums import Module, SystemStatus
from resolve.resolver import Resolver
from metrics.latency_monitor import monitor_node_latencies

# globals
id = int(os.getenv("ID", 0))
logger = logging.getLogger(__name__)
app_name = "SelfStabilizingReconfiguration"


def start_api(resolver):
    """Starts API in a separate thread."""
    thread = Thread(target=start_server, args=(resolver,))
    thread.start()


def start_modules(resolver):
    """Starts all modules in separate threads."""
    n = int(os.getenv("NUMBER_OF_NODES", 0))
    f = int(os.getenv("NUMBER_OF_BYZANTINE", 0))
    k = int(os.getenv("NUMBER_OF_CLIENTS", 0))

    if n == 0:
        logger.warning("Env var NUMBER_OF_NODES not set or set to 0")
    if f == 0:
        logger.warning("Env var NUMBER_OF_BYZANTINE not set or set to 0")
    if k == 0:
        logger.warning("Env var NUMBER_OF_CLIENTS not set or set to 0")

    if os.getenv("INJECT_START_STATE"):
        logger.warning("Node will load state from conf/start_state.json")

    modules = {
        Module.RECMA_MODULE: RecMAModule(id, resolver, n),
        Module.RECSA_MODULE: RecSAModule(id, resolver, n),
        Module.FAILURE_DETECTOR_MODULE: FDModule(id, resolver, n),
        Module.JOINING_MECHANISM_MODULE: JoiningMechanismModule(id, resolver, n),
        Module.ABD_MODULE: ABDModule(id, resolver, n)
    }

    resolver.set_modules(modules)

    # start threads and attach to resolver
    for m in modules.values():
        t = Thread(target=m.run)
        t.start()


def setup_communication(resolver):
    """Sets up the communication using asyncio event loop."""
    nodes = config.get_nodes()

    # setup receiver to receiver channel messages from other nodes
    receiver = Receiver(id, nodes[id].ip, nodes[id].port, resolver,
                        resolver.on_message_sent)
    t = Thread(target=receiver.start)
    t.start()

    # setup sender channel to other nodes
    senders = {}
    for _, node in nodes.items():
        if id != node.id:
            sender = Sender(id, node, resolver.on_message_sent)
            senders[node.id] = sender
    logger.info("All senders connected")

    resolver.senders = senders
    resolver.receiver = receiver

    loop = asyncio.get_event_loop()
    for i in senders:
        loop.create_task(senders[i].start())

    resolver.system_status = SystemStatus.READY

    loop.run_forever()
    loop.close()


def setup_metrics():
    """Starts metrics server for Prometheus scraper on port 300{ID}."""
    try:
        port = 3000 + id
        start_http_server(port, addr="0.0.0.0")
        logger.info(f"Metrics server setup on port {port}")
    except Exception as e:
        logger.error(f"Could not setup metrics. Got error: {e}")

    # start latency monitor in other thread
    Thread(target=monitor_node_latencies).start()


def setup_logging():
    """Sets up logging for application."""
    colors = ["\033[95m", "\033[94m", "\033[92m", "\033[93m",
              "\033[91m", "\033[0m"]
    node_color = colors[id % len(colors)]
    end_color = colors[len(colors) - 1]

    FORMAT = f"{node_color}{app_name}.%(name)s : Node {id}" + " ==> " + \
             "[%(levelname)s] : %(message)s" + f"{end_color}"
    level = logging.DEBUG if os.getenv("DEBUG") is not None else logging.INFO
    logging.basicConfig(format=FORMAT, level=level)

    # only log ERROR messages from external loggers
    externals = ["werkzeug", "asyncio, engineio", "engineio.client",
                 "engineio.server", "socketio.client", "socketio.server",
                 "urllib3.connectionpool"]
    for e in externals:
        logging.getLogger(e).setLevel(logging.FATAL)
    # for some reason asyncio logger needs to be silenced twice
    logging.getLogger("asyncio").setLevel(logging.FATAL)

    logger.info("Logging configured")


def setup_fd_communication(resolver):
    """Sets up the self-stabilizing communication for the failure detectors."""
    nodes = config.get_nodes()

    # setup self-stabilizing receiver channel for failure detectors on
    # other nodes
    receiver = FDReceiver(("0.0.0.0", 7000 + id),
                          on_message_recv=resolver.dispatch_msg)
    t = Thread(target=receiver.listen)
    t.start()

    # setup self-stabilizing sender channels for failure detectors for
    # other nodes
    senders = {}
    for _, node in nodes.items():
        if id != node.id:
            sender = FDSender(id, (node.hostname, 7000 + node.id),
                              check_ready=resolver.system_running,
                              on_message_sent=resolver.on_message_sent)
            senders[node.id] = sender
            t = Thread(target=sender.start)
            t.start()

    # inject to resolver
    resolver.fd_senders = senders
    resolver.fd_receiver = receiver
    logger.info("All self-stab UDP senders connected")


if __name__ == "__main__":
    resolver = Resolver()

    setup_logging()
    setup_metrics()
    start_modules(resolver)
    start_api(resolver)
    setup_fd_communication(resolver)
    setup_communication(resolver)
