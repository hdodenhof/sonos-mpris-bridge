import logging
import threading
from Queue import Empty, Queue

import soco

logger = logging.getLogger(__name__)

class SonosAPI:

    STATE_PLAYING = 'PLAYING'
    STATE_PAUSED = 'PAUSED_PLAYBACK'
    STATE_TRANSITIONING = 'TRANSITIONING'

    def __init__(self):
        self.players = soco.discover()
        self.listener = None

        for player in self.players:
            if player.is_coordinator:
                self.coordinator = player

        self.avTransport = None

        self.eventReceiver = EventReceiver(self.coordinator, self._on_state_change)
        self.eventReceiver.start()

    def disconnect(self):
        pass

    def is_playing(self):
        return self.avTransport.transport_state == self.STATE_PLAYING

    def play(self):
        self.coordinator.play()

    def pause(self):
        self.coordinator.pause()

    def next(self):
        self.coordinator.next()

    def prev(self):
        self.coordinator.previous()

    def current_track(self):
        if self.avTransport is not None:
            return self.avTransport.current_track_meta_data
        else:
            return None

    def position(self):
        return self.coordinator.get_current_track_info()['position']

    def set_listener(self, listener):
        self.listener = listener

    def _on_state_change(self, transport_state):
        self.avTransport = transport_state
        if self.listener is not None:
            self.listener()


class EventReceiver(threading.Thread):

    def __init__(self, coordinator, transport_callback):
        super(EventReceiver, self).__init__(name="EventReceiver")
        self.daemon = True

        self.event_handler = EventHandler()
        self.event_handler.start()

        self.subscription = coordinator.avTransport.subscribe(auto_renew=True)
        self.transport_callback = transport_callback

    def run(self):
        while True:
            try:
                event = self.subscription.events.get(timeout=0.5)
                self.event_handler.execute(self.transport_callback, event)
            except Empty:
                pass


class EventHandler(threading.Thread):

    def __init__(self):
        super(EventHandler, self).__init__(name="EventHandler")
        self.daemon = True

        self.queue = Queue()

    def run(self):
        while True:
            try:
                function, args, kwargs = self.queue.get(timeout=0.5)
                function(*args, **kwargs)
            except Empty:
                pass
            except Exception as e: # Do not break if function invocation fails
                logging.exception('Function invocation failed')

    def execute(self, function, *args, **kwargs):
        self.queue.put((function, args, kwargs))