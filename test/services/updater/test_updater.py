import os
import time
from threading import Thread, Event
from unittest.mock import Mock

from weavelib.rpc import RPCClient
from weaveserver.core.services import ServiceManager
from weaveserver.services.updater.service import UpdaterService, UpdateScanner


AUTH = {
    "auth1": {
        "type": "SYSTEM",
        "appid": "appmgr",
        "package": "p",
    },
    "auth2": {
        "appid": "appid2"
    }
}


class TestUpdateScanner(object):
    def setup_method(self):
        self.update_check_freq_backup = UpdateScanner.UPDATE_CHECK_FREQ
        UpdateScanner.UPDATE_CHECK_FREQ = 5

        os.environ["USE_FAKE_REDIS"] = "TRUE"
        self.service_manager = ServiceManager()
        self.service_manager.apps.update(AUTH)
        self.service_manager.start_services(["messaging", "appmanager"])

    def teardown_method(self):
        del os.environ["USE_FAKE_REDIS"]
        self.service_manager.stop()

    def test_simple_update(self):
        mock_repo = Mock()
        mock_repo.needs_pull = Mock(return_value=False)
        UpdateScanner.list_repos = lambda x, y: ["dir"]
        UpdateScanner.get_repo = lambda x, y: mock_repo

        started = Event()
        service = UpdaterService("auth1", None)
        service.before_service_start()
        service.notify_start = started.set
        Thread(target=service.on_service_start).start()

        started.wait()

        while service.get_status() != "No updates available.":
            time.sleep(1)

        mock_repo.asssert_called_with("dir")

        mock_repo.needs_pull = Mock(return_value=True)
        time.sleep(8)
        assert service.get_status() == "Updates available."

        service.on_service_stop()

    def test_trigger_update_when_no_update(self):
        UpdateScanner.UPDATE_CHECK_FREQ = 1000

        mock_repo = Mock()
        mock_repo.needs_pull = Mock(return_value=False)
        UpdateScanner.list_repos = lambda x, y: ["dir"]
        UpdateScanner.get_repo = lambda x, y: mock_repo

        started = Event()
        service = UpdaterService("auth1", None)
        service.before_service_start()
        service.notify_start = started.set
        Thread(target=service.on_service_start).start()

        started.wait()

        service.update_status("dummy")

        rpc = RPCClient(service.rpc.info_message)
        rpc.start()

        print("RPC:", rpc["perform_upgrade"](_block=True))

        assert service.get_status() == "No updates available."

        service.on_service_stop()
