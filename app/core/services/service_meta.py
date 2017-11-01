import logging
from copy import deepcopy
from inspect import signature
from threading import Thread, RLock
from uuid import uuid4

from jsonschema import validate, ValidationError

from app.core.messaging import Message, Creator, Receiver, Sender


logger = logging.getLogger(__name__)


def create_capabilities_queue(queue_name):
    queue_info = {
        "queue_name": queue_name,
        "queue_type": "keyedsticky",
        "request_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "params": {"type": "object"},
                "id": {"type": "string"},
            }
        }
    }
    creator = Creator()
    creator.start()
    creator.create(queue_info)

def check_handler_param(params, handler):
    schema_args = set(params.keys())
    handler_args = set(signature(handler).parameters.keys())
    if schema_args != handler_args:
        raise TypeError("Parameter mismatch between Schema and Handler args.")


class Capability(Message):
    def __init__(self, name, description, params, queue_template):
        self.uuid = str(uuid4())
        self.params = deepcopy(params)
        self.name = name
        self.queue = queue_template.format(self.uuid)
        obj = {
            "name": name,
            "description": description,
            "params": self.params,
            "id": self.uuid,
            "queue": self.queue
        }
        super().__init__("enqueue", obj)

    @property
    def unique_id(self):
        return self.uuid

    @property
    def schema(self):
        return {
            "type": "object",
            "properties": self.params,
            "required": list(self.params.keys())
        }


class EventReceiver(Receiver):
    def __init__(self, queue_name, capability, handler):
        super().__init__(queue_name)
        self.capability = capability
        self.handler = handler

    def start(self):
        super().start()
        logger.info("Started listening for event: %s", self.capability.name)

    def on_message(self, msg):
        self.handler(**msg)


class EventDrivenService(object):
    def on_service_start(self, *args, **kwargs):
        create_capabilities_queue(self.get_service_queue_name("capabilities"))
        self.capabilities_queue_map = {}
        self.capabilities_queue_lock = RLock()
        super().on_service_start(*args, **kwargs)

    def express_capability(self, name, description, params, handler):
        check_handler_param(params, handler)
        queue_template = self.get_service_queue_name("capability/{}")
        capability = Capability(name, description, params, queue_template)
        queue_name = self.get_service_queue_name("capabilities")
        capability_sender = Sender(queue_name)
        capability_sender.start()
        headers = {"KEY": capability.unique_id}
        capability_sender.send(capability, headers=headers)

        self.create_event_queue(capability)
        thread, receiver = self.start_event_receiver(capability, handler)
        with self.capabilities_queue_lock:
            self.capabilities_queue_map[capability.unique_id] = (thread,
                                                                 receiver)

    def create_event_queue(self, capability):
        qid = capability.unique_id
        queue_name = self.get_service_queue_name("capability/" + qid)
        queue_info = {
            "queue_name": queue_name,
            "request_schema": capability.schema
        }
        creator = Creator()
        creator.start()
        creator.create(queue_info)

    def start_event_receiver(self, capability, handler):
        qid = capability.unique_id
        queue_name = capability.queue
        receiver = EventReceiver(queue_name, capability, handler)
        receiver.start()
        thread = Thread(target=receiver.run)
        thread.start()
        return thread, receiver

    def run_event_receiver(self, receiver):
        receiver.run()

    def get_service_queue_name(self, queue_name):
        service_name = self.get_component_name()
        return "/services/{}/{}".format(service_name, queue_name)

    def on_service_stop(self):
        with self.capabilities_queue_lock:
            for _, (thread, receiver) in self.capabilities_queue_map.items():
                logger.info("stopping receiver..")
                receiver.stop()
                thread.join()
        super().on_service_stop()
