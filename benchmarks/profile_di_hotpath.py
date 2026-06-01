import cProfile
import pstats
from io import StringIO

from muscles.core.core import Dependency, inject


class EventsStorageInterface:
    def touch(self):
        return True


class EventsStorage(EventsStorageInterface):
    def touch(self):
        return True


Dependency(EventsStorageInterface, EventsStorage)


@inject(EventsStorageInterface)
def handle_request(event_storage: EventsStorageInterface):
    return event_storage.touch()


def run(iterations: int = 10_000) -> dict:
    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(iterations):
        handle_request()
    profiler.disable()

    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats("inspect.signature")
    text = stream.getvalue()
    signature_hits = 0 if "inspect.signature" not in text else 1
    return {"iterations": iterations, "inspect_signature_in_profile": signature_hits}


if __name__ == "__main__":
    print(run())

