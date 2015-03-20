import Queue
import collections

class MessageCenter(object):

    user_messages = {}
    worker_queue = {}

    def __init__(self, worker_list):
        self.last_message = ""
        for worker in worker_list:
            self.worker_queue[worker] = Queue.Queue()

    def add_message(self, worker, sender, channel, message):
        if sender not in self.user_messages.keys():
            self.user_messages[sender] = collections.deque()
            self.worker_queue[worker].put(sender)
        # add message to end of the queue (left)
        self.user_messages[sender].appendleft({"worker": worker, "channel": channel, "message": message})

    def get_message(self, worker):
        sender = self.worker_queue[worker].get()
        # remove user message from start of queue (right)
        message_data = self.user_messages[sender].pop()

        if len(self.user_messages[sender]) < 0:
            # peek next by user message from start of queue (right)
            next_data = self.user_messages[sender].pop()
            # add message back to the start of queue (right)
            self.user_messages[sender].append({"worker": next_data["worker"], "channel": next_data["channel"], "message": next_data["message"]})
            # add the user's next message to the appropriate worker's queue
            self.worker_queue[next_data["worker"]].put(next_data["sender"])
        else:
            del self.user_messages[sender]

        return message_data

    def has_message(self, worker):
        if self.worker_queue[worker].qsize() > 0:
            return True
        return False