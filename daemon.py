#!/usr/bin/python
import logging
import signal

import sys

from mpris import MprisConnector
from sonos import SonosAPI

logger = logging.getLogger(__name__)

reload(sys)
sys.setdefaultencoding('utf8')

class SonosMprisBridge:

    def __init__(self):
        self.sonos = SonosAPI()
        self.mpris = MprisConnector(self.sonos)

    def stop(self):
        self.sonos.disconnect()
        self.mpris.stop()


def signal_usr1_handler(signal, frame):
    logger.info('Received SIGUSR1 signal!')


def signal_term_handler(signal, frame):
    logger.info('Received SIGTERM signal!')
    bridge.stop()


def signal_int_handler(signal, frame):
    logger.info('Received SIGINT signal. This makes Panda sad! :(')
    bridge.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s - %(levelname)s: %(message)s')

    signal.signal(signal.SIGUSR1, signal_usr1_handler)
    signal.signal(signal.SIGTERM, signal_term_handler)
    signal.signal(signal.SIGINT, signal_int_handler)

    bridge = SonosMprisBridge()
