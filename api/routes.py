"""Contains all API routes for the external REST API."""

# standard
import os
import json
from flask import (Blueprint, jsonify, request, abort,
                   render_template, current_app as app)
from flask_cors import cross_origin
import requests
import logging
import jsonpickle

# local
import conf.config as conf
import modules.byzantine as byz
from communication.zeromq.node import Node

# globals
routes = Blueprint("routes", __name__)
logger = logging.getLogger(__name__)


@routes.route("/", methods=["GET"])
def index():
    """Return the status of the current API service."""
    _id = str(os.getenv("ID", 0))
    return jsonify({
        "status": app.resolver.system_status.name,
        "service": "SelfStabilizingReconfiguration",
        "id": _id
    })


@routes.route("/set-byz-behavior", methods=["POST"])
def set_byz_behavior():
    """Route for setting Byzantine behavior for this node at runtime."""
    data = request.get_json()
    behavior = data["behavior"]
    if not byz.is_valid_byz_behavior(behavior):
        return abort(400)

    byz.set_byz_behavior(behavior)
    return jsonify({"behavior": byz.get_byz_behavior()})


@routes.route("/byz-behaviors", methods=["GET"])
def get_byz_behaviors():
    """Returns the valid Byzantine behaviors."""
    return jsonify(byz.BYZ_BEHAVIORS)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

@routes.route("/data", methods=["GET"])
@cross_origin()
def get_modules_data():
    """Returns current values of variables in the modules."""

    data = {
        "node_id": int(os.getenv("ID")),
        "RECSA_MODULE": app.resolver.get_recsa_module_data(),
        "RECMA_MODULE": app.resolver.get_recma_module_data(),
        "ABD_MODULE": app.resolver.get_abd_module_data()
    }
    return json.dumps(data, cls=SetEncoder)

@routes.route("/kill", methods=["POST"])
def kill_node():
    """Kills this node by killing the process."""
    logger.info("/kill called, exiting")
    os._exit(0)


def fetch_data_for_all_nodes():
    """Fetches data from all nodes through their /data endpoint."""
    try:
        data = []
        for _, node in conf.get_nodes().items():
            r = requests.get(f"http://{node.ip}:{4000+node.id}/data")
            data.append({"node": node.to_dct(), "data": r.json()})
        return data
    except Exception as e:
        logger.error(f"Error when fetching data for other nodes: {e}")
        return None


def render_global_view(view="recsa"):
    """Renders the global view for a specified module."""
    nodes_data = fetch_data_for_all_nodes()
    if nodes_data is None:
        return jsonify({"STATUS": "SYSTEM_BOOT"})

    test_name = os.getenv("INTEGRATION_TEST")
    test_data = {"test_name": test_name} if test_name is not None else {}

    nss_on = os.getenv("NON_SELF_STAB")
    nss = {"nss": 1} if nss_on is not None else {}

    return render_template("view/main.html", data={
        "view": view,
        "nodes_data": nodes_data,
        "test_data": test_data,
        "nss": nss,
        "byz_behaviors": [byz.NONE] + byz.BYZ_BEHAVIORS
    })


@routes.route("/view/recsa", methods=["GET"])
def render_recsa_view():
    """Renders the global view for the RecSA module.

    This view only displays data related to the recsa module and should
    only be used when running integration test for that module.
    """
    return render_global_view("recsa")

@routes.route("/view/recma", methods=["GET"])
def render_recma_view():
    """Renders the global view for the RecMA module.

    This view only displays data related to the recma module and should
    only be used when running integration test for that module.
    """
    return render_global_view("recma")

@routes.route("/abd/read", methods=["GET"])
def abd_read():
    """Reads the ABD register and returns the its msg/label."""
    status_code, register = app.resolver.abd_read()
    return jsonify(register)

@routes.route("/abd/write", methods=["POST"])
def abd_write():
    """If sent to node 0, message is written to the register and returned."""
    status_code, data = app.resolver.abd_write()

    if status_code != 200:
        return app.response_class(
            response=data,
            status=status_code,
            mimetype="application/json"
        )
    else:
        return jsonify(data)

@routes.route("/nodes", methods=["GET"])
def get_nodes_list():
    """Returns a list of all nodes in the system.
    
    Used by joining script to have a new node join the system.
    """
    nodes = conf.get_nodes()
    ns = {}
    for n_id, n in nodes.items():
        ns[n_id] = n.to_dct()
    return jsonify(ns)

@routes.route("/publish_node", methods=["POST"])
def publish_node():
    data = request.get_json()
    new_node = Node(data['id'], data['hostname'], data['ip'], data['port'])
    conf.add_node_to_hosts_file(new_node)

    # re-fresh system to account for new, added node
    app.resolver.refresh(new_node)

    return jsonify(success=True)

@routes.route("/inject_conf", methods=["POST"])
def inject_conf():
    payload = jsonpickle.decode(request.get_json())
    conf = payload["conf"]
    app.resolver.inject_conf(conf)
    return jsonify(success=True)

@routes.route("/inject_prp", methods=["POST"])
def inject_prp():
    payload = jsonpickle.decode(request.get_json())
    phase = payload["phase"]
    st = payload["set"]
    app.resolver.inject_prp((phase, st))
    return jsonify(success=True)
