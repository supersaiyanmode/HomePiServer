import threading

from app.views import SimpleBackgroundView


class BaseService(object):
    def __init__(self, **kwargs):
        self.name =  kwargs.pop("name", self.__class__.__name__)
        super().__init__(**kwargs)

    def view(self):
        return SimpleBackgroundView()

    def service_stop(self):
        pass

class BlockingServiceStart(object):
    def __init__(self, **kwargs):
        self.target = kwargs.pop("target", self.on_service_start)
        self.target_args = kwargs.pop("target_args",  ())
        self.target_kwargs = kwargs.pop("target_kwargs", {})
        super().__init__(**kwargs)

    def service_start(self):
        try:
            return self.target(*self.target_args, **self.target_kwargs)
        except (FileNotFoundError,):
            return None

class BackgroundServiceStart(object):
    def __init__(self, **kwargs):
        self.target = kwargs.get("target") or self.on_service_start
        self.target_args = kwargs.get("target_args") or ()
        self.target_kwargs = kwargs.get("target_kwargs") or {}
        super().__init__(**kwargs)

    def service_start(self):
        t = threading.Thread(target=self.target, args=self.target_args,
                kwargs=self.target_kwargs)
        t.start()

