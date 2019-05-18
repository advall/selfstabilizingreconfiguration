"""Metrics related to messages."""

from prometheus_client import Counter, Gauge

msgs_sent = Counter("msg_sent",
                    "Number of messages sent by a node node",
                    ["node_id"])

msgs_in_queue = Gauge("msgs_in_queue",
                      "The amount of messages waiting to be sent over channel",
                      ["node_id", "receiver_id", "receiver_hostname"])
