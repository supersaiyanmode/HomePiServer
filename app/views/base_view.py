"""
Contains BaseView that acts as a base class for all websocket based views.
"""
import os.path
from threading import RLock
import logging

from flask_socketio import Namespace
from flask import request


logger = logging.getLogger(__name__)


class ClientSocket(object): #pylint: disable=R0903
    """Represents one websocket client"""
    def __init__(self, channel, sid, namespace):
        """
        Args:
            channel: socketio inamespacetance that encaspsulates flask app.
            sid: Session id present in request.sid
            namespace: namespace
        """
        self.sid = sid
        self.namespace = namespace
        self.channel = channel

    def send_message(self, key, data):
        self.channel.emit(key, data, namespace=self.namespace, room=self.sid)


class BaseViewWebSocket(Namespace):
    """Manages all the clients and responds with latest view in self.display"""

    def __init__(self, view, namespace, socketio):
        """
        Args:
            namespace: Namespace of communication
            socketio: socketio inamespacetance that encaspsulates flask app
        """
        self.client_dict_lock = RLock()
        self.socketio = socketio
        self.namespace = namespace
        self.view = view
        self.clients = {}

        super(BaseViewWebSocket, self).__init__(namespace)

    def on_connect(self):
        sock = ClientSocket(self.socketio, request.sid, self.namespace)
        with self.client_dict_lock:
            self.clients[request.sid] = sock

    def on_disconnect(self):
        with self.client_dict_lock:
            del self.clients[request.sid]

    def on_request_view(self, *_):
        """ Responds to the client with the latest HTML view."""
        with self.client_dict_lock:
            sock = self.clients[request.sid]
        sock.send_message('view', self.create_full_data())

    def create_full_data(self):
        return {
            "html": self.view.html(),
            "args": self.view.args(),
            "innerViews": self.view.inner_views()
        }

    def create_update_data(self):
        return {"args": self.view.args()}

    def notify_updates(self):
        """ Informs all connected clients about change in the view. """
        with self.client_dict_lock:
            items = list(self.clients.items())
        for _, sock in items:
            sock.send_message('view', self.create_update_data())


class BaseView(object):
    """
    Base class for all the views.
    """
    HTML = "simple.html"
    HTML_BASE_PATH = "templates"

    def __init__(self, main_socket):
        self.view_args = {}
        self.sockets = []
        self.nested_views = {}
        self.main_socket = main_socket
        if main_socket:
            self.sockets.append(main_socket)

    def html(self):
        """
        Reads the file in HTML within HTML_BASE_PATH returns it.
        """
        with open(os.path.join(self.HTML_BASE_PATH, self.HTML)) as html:
            return html.read()

    def args(self):
        return self.view_args

    def inner_views(self):
        res = {}
        for name, view in self.nested_views.items():
            res[name] = {
                "namespace": view.get_namespace()
            }
        return res

    def notify_updates(self):
        if self.main_socket:
            self.main_socket.notify_updates()

    def add_inner_view(self, name, view):
        self.nested_views[name] = view
        for sock in view.get_sockets():
            self.sockets.append(sock)

    def get_sockets(self):
        """
        Returns a list of sockets (more of channels) to register/un-register
        when the view is active/inactive
        """
        return self.sockets

    def get_namespace(self):
        """
        Returns the namespace of the main_socket.
        """
        return self.main_socket.namespace