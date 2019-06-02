"""Enums related to the resolver and inter-module communication."""
from enum import Enum, IntEnum


class SystemStatus(IntEnum):
    """Represents system status."""

    BOOTING = 1
    READY = 2
    RUNNING = 3


class Module(Enum):
    """Represents a module."""

    RECMA_MODULE = 1
    RECSA_MODULE = 2
    FAILURE_DETECTOR_MODULE = 3
    JOINING_MECHANISM_MODULE = 4


class Function(Enum):
    """Represents an interface function in a module."""

    FOO = 1


class MessageType(IntEnum):
    """Represents a message type sent between nodes."""

    RECMA_MESSAGE = 1
    RECSA_MESSAGE = 2
    FAILURE_DETECTOR_MESSAGE = 3
    JOINING_MECHANISM_MESSAGE = 4
