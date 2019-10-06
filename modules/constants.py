"""Constant values for the modules"""

# system constants
APP_NAME = "SelfStabilizingReconfiguration"
RUN_SLEEP = 1
INTEGRATION_RUN_SLEEP = 0.05
FD_SLEEP = 0.25
FD_TIMEOUT = 5
MAX_QUEUE_SIZE = 10  # Max allowed amount of messages in send queue

# FD
BEAT_THRESHOLD = 30  # Threshold for liveness, beat-variable
CNT_THRESHOLD = 20  # Threshold for progress, cnt-variable

NOT_PARTICIPANT = 'NOT_PARTICIPANT'
BOTTOM = 'BOTTOM'
DFLT_NTF = (0, BOTTOM)
RECSA_MSG_TYPE = 2
RECMA_MSG_TYPE = 3

# ABD
READ_REQUEST = "READ_REQUEST"
READ_CONFIRM = "READ_CONFIRM"
WRITE = "WRITE"
BOT = -1
NOT_SENT = "NOT_SENT"
NOT_ACKED = "NOT_ACKED"
ACKED = "ACKED"
WRITE_ACK = "WRITE_ACK"
READ_CONFIRM_ACK = "READ_CONFIRM_ACK"
READ_REQUEST_ACK = "READ_REQUEST_ACK"