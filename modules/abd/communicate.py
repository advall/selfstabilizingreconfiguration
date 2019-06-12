BOT = "BOT"
NOT_SENT = "NOT_SENT"
NOT_ACKED = "NOT_ACKED"
ACKED = "ACKED"

MSG = "HELLO WORLD"

status = {}

def communicate(n):
    for j in range(n):
        status[n] = NOT_ACKED
        info[n] = BOT
        send(MSG, j)
    

def send(msg, j):
    pass

def receive(msg, j):
    if status[j] == NOT_SENT:
        # ack of old message
        send(MSG, j)
        status[j] = NOT_ACKED
    elif status[j] == NOT_ACKED:
        status[j] = ACKED
        info[j] = msg
        no_acks += 1

