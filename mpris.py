#!/usr/bin/python
import dbus
import dbus.service
import glib
import gobject
import logging
import uuid
from dbus.mainloop.glib import DBusGMainLoop
from pprint import pprint

gobject.threads_init()

logger = logging.getLogger(__name__)

IDENTITY = 'Sonos'

BUS_NAME = 'org.mpris.MediaPlayer2.' + IDENTITY
ROOT_IFACE = 'org.mpris.MediaPlayer2'
PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
MPRIS_PATH = '/org/mpris/MediaPlayer2'

class MprisConnector(dbus.service.Object):

    # noinspection PyMissingConstructor
    def __init__(self, sonos):
        self.sonos = sonos
        self.sonos.set_listener(self.sonos_listener)

        self.main_loop = glib.MainLoop()

        self.bus = dbus.SessionBus(mainloop=DBusGMainLoop())
        self.bus.request_name(BUS_NAME)

        self.properties = {
            ROOT_IFACE: self._get_root_iface_properties(),
            PLAYER_IFACE: self._get_player_iface_properties()
        }

        dbus.service.Object.__init__(self, self.bus, MPRIS_PATH)

        try:
            self.main_loop.run()
        except KeyboardInterrupt:
            pass

    def stop(self):
        self.main_loop.quit()
        self.bus.release_name(BUS_NAME)
        self.bus.close()

    def sonos_listener(self):
        self.PropertiesChanged(PLAYER_IFACE, { 'PlaybackStatus': self.get_PlaybackStatus(),
                                               'Metadata': self.get_Metadata() }, [])

    def _get_root_iface_properties(self):
        return {
            'CanQuit': (False, None),
            'Fullscreen': (False, None),
            'CanSetFullscreen': (False, None),
            'CanRaise': (False, None),
            'HasTrackList': (False, None),
            'Identity': (IDENTITY, None),
            'SupportedUriSchemes': (dbus.Array([], signature='s'), None),
            'SupportedMimeTypes': (dbus.Array([], signature='s'), None),
        }

    def _get_player_iface_properties(self):
        return {
            'PlaybackStatus': (self.get_PlaybackStatus, None),
            'LoopStatus': (self.get_LoopStatus, self.set_LoopStatus),
            'Rate': (1.0, self.set_Rate),
            'Shuffle': (self.get_Shuffle, self.set_Shuffle),
            'Metadata': (self.get_Metadata, None),
            'Volume': (self.get_Volume, self.set_Volume),
            'Position': (self.get_Position, None),
            'MinimumRate': (1.0, None),
            'MaximumRate': (1.0, None),
            'CanGoNext': (self.get_CanGoNext, None),
            'CanGoPrevious': (self.get_CanGoPrevious, None),
            'CanPlay': (self.get_CanPlay, None),
            'CanPause': (True, None),
            'CanSeek': (True, None),
            'CanControl': (True, None),
        }

    #
    # Properties
    #

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        logger.debug('%s.Get(%s, %s) called', dbus.PROPERTIES_IFACE, repr(interface), repr(prop))
        (getter, _) = self.properties[interface][prop]
        if callable(getter):
            return getter()
        else:
            return getter

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        logger.debug('%s.GetAll(%s) called', dbus.PROPERTIES_IFACE, repr(interface))
        getters = {}
        for key, (getter, _) in self.properties[interface].iteritems():
            getters[key] = getter() if callable(getter) else getter
        return getters

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE, in_signature='ssv', out_signature='')
    def Set(self, interface, prop, value):
        logger.debug('%s.Set(%s, %s, %s) called', dbus.PROPERTIES_IFACE, repr(interface), repr(prop), repr(value))
        _, setter = self.properties[interface][prop]
        if setter is not None:
            setter(value)
            self.PropertiesChanged(interface, {prop: self.Get(interface, prop)}, [])

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties, invalidated_properties):
        logger.debug('%s.PropertiesChanged(%s, %s, %s) signaled', dbus.PROPERTIES_IFACE, interface, changed_properties, invalidated_properties)

    #
    # org.mpris.MediaPlayer2
    #

    @dbus.service.method(dbus_interface=ROOT_IFACE)
    def Raise(self):
        logger.debug('%s.Raise called', ROOT_IFACE)

    @dbus.service.method(dbus_interface=ROOT_IFACE)
    def Quit(self):
        logger.debug('%s.Quit called', ROOT_IFACE)

    #
    # org.mpris.MediaPlayer2.Player
    #

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Next(self):
        logger.debug('%s.Next called', PLAYER_IFACE)
        if not self.get_CanGoNext():
            logger.debug('%s.Next not allowed', PLAYER_IFACE)
            return
        self.sonos.next()

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Previous(self):
        logger.debug('%s.Previous called', PLAYER_IFACE)
        if not self.get_CanGoPrevious():
            logger.debug('%s.Previous not allowed', PLAYER_IFACE)
            return
        self.sonos.prev()

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Pause(self):
        logger.debug('%s.Pause called', PLAYER_IFACE)
        self.sonos.pause()

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def PlayPause(self):
        logger.debug('%s.PlayPause called', PLAYER_IFACE)
        if self.sonos.is_playing():
            self.sonos.pause()
        else:
            self.sonos.play()

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Stop(self):
        logger.debug('%s.Stop called', PLAYER_IFACE)

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Play(self):
        logger.debug('%s.Play called', PLAYER_IFACE)
        if not self.get_CanPlay():
            logger.debug('%s.Play not allowed', PLAYER_IFACE)
            return
        self.sonos.play()

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def Seek(self, offset):
        logger.debug('%s.Seek called', PLAYER_IFACE)
        #offset_in_milliseconds = offset // 1000
        #current_position = self.core.playback.time_position.get()
        #new_position = current_position + offset_in_milliseconds
        #if new_position < 0:
        #    new_position = 0
        #self.core.playback.seek(new_position)

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def SetPosition(self, track_id, position):
        logger.debug('%s.SetPosition called', PLAYER_IFACE)
        #position = position // 1000
        #current_tl_track = self.core.playback.current_tl_track.get()
        #if current_tl_track is None:
        #    return
        #if track_id != self.get_track_id(current_tl_track):
        #    return
        #if position < 0:
        #    return
        #if current_tl_track.track.length < position:
        #    return
        #self.core.playback.seek(position)

    @dbus.service.method(dbus_interface=PLAYER_IFACE)
    def OpenUri(self, uri):
        logger.debug('%s.OpenUri called', PLAYER_IFACE)

    #
    # org.mpris.MediaPlayer2.Player signals
    #

    @dbus.service.signal(dbus_interface=PLAYER_IFACE, signature='x')
    def Seeked(self, position):
        logger.debug('%s.Seeked signaled', PLAYER_IFACE)

    #
    # org.mpris.MediaPlayer2.Player properties
    #

    def get_PlaybackStatus(self):
        if self.sonos.is_playing():
            return 'Playing'
        else:
            return 'Paused'
        # TODO: stopped

    def get_LoopStatus(self):
        return 'None'
        #repeat = self.core.tracklist.repeat.get()
        #single = self.core.tracklist.single.get()
        #if not repeat:
        #    return 'None'
        #else:
        #    if single:
        #        return 'Track'
        #    else:
        #        return 'Playlist'

    def set_LoopStatus(self, value):
        pass
        #if value == 'None':
        #    self.core.tracklist.repeat = False
        #    self.core.tracklist.single = False
        #elif value == 'Track':
        #    self.core.tracklist.repeat = True
        #    self.core.tracklist.single = True
        #elif value == 'Playlist':
        #    self.core.tracklist.repeat = True
        #    self.core.tracklist.single = False

    def set_Rate(self, value):
        pass

    def get_Shuffle(self):
        return False

    def set_Shuffle(self, value):
        pass
        #if value:
        #    self.core.tracklist.random = True
        #else:
        #    self.core.tracklist.random = False

    def get_Metadata(self):
        current_track = self.sonos.current_track()
        if current_track is None:
            return dbus.Dictionary({'mpris:trackid': ''}, signature='sv')
        else:
            metadata = {'mpris:trackid': 'sonos/' + str(uuid.uuid4())}

            metadata['mpris:length'] = dbus.Int64(self._runtime_from_duration(current_track.to_dict()['resources'][0]['duration']) * 1000 * 1000)
            metadata['xesam:title'] = current_track.title
            metadata['xesam:artist'] = dbus.Array([current_track.to_dict()['creator']], signature='s')
            metadata['xesam:album'] = current_track.to_dict()['album']
            metadata['mpris:artUrl'] = 'http://192.168.178.23:1400' + current_track.album_art_uri # TODO

            return dbus.Dictionary(metadata, signature='sv')

    def _runtime_from_duration(self, duration):
        duration_components = duration.split(':')
        return int(duration_components[0]) * 60 * 60 + int(duration_components[1]) * 60 + int(duration_components[2])

    def get_Volume(self):
        return 0

    def set_Volume(self, value):
        pass

    def get_Position(self):
        pos = self.sonos.position()
        logger.debug(pos)
        runtime = self._runtime_from_duration(pos)
        logger.debug(runtime)
        retval = long(runtime) * 1000 * 1000
        logger.debug(retval)
        return retval

    #'current_transport_actions': 'Set, Stop, Pause, Play, X_DLNA_SeekTime, Next, Previous, X_DLNA_SeekTrackNr',

    def get_CanGoNext(self):
        return True
        #current_tl_track = self.core.playback.current_tl_track.get()
        #next_tl_track = self.core.tracklist.next_track(current_tl_track).get()
        #return next_tl_track != current_tl_track

    def get_CanGoPrevious(self):
        return True
        #current_tl_track = self.core.playback.current_tl_track.get()
        #previous_tl_track = (self.core.tracklist.previous_track(current_tl_track).get())
        #return previous_tl_track != current_tl_track

    def get_CanPlay(self):
        return True
        #current_tl_track = self.core.playback.current_tl_track.get()
        #next_tl_track = self.core.tracklist.next_track(current_tl_track).get()
        #return current_tl_track is not None or next_tl_track is not None
