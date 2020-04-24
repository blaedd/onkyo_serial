"""Relay LIRC events to an ISCP device."""

# cribbed from https://github.com/proquar/twisted-stuff/blob/master/lirc/LircReceiver.py

import os
import pylirc

from twisted.application import service
from twisted.internet import abstract
from twisted.internet import defer
from twisted.internet import endpoints
from twisted.internet import interfaces
from twisted.python import log
from zope import interface

# Default mapping of Remote key to ISCP commands
KEYMAP = {
    'KEY_DVD': 'input-selector=dvd',
    'KEY_BRIGHTNESSDOWN': 'dimmer-level=dim',
    'KEY_VCR': 'input-selector=vcr',
    'KEY_SAT': 'input-selector=sat',
    'KEY_TV': 'input-selector=game',
    'KEY_AUX': 'input-selector=aux1',
    'KEY_AUX2': 'input-selector=aux2',
    'KEY_TAPE': 'input-selector=tape',
    'KEY_TUNER': 'input-selector=fm',
    'KEY_CD': 'input-selector=cd',
    'KEY_VOLUMEUP': 'master-volume=level-up',
    'KEY_VOLUMEDOWN': 'master-volume=level-down',
    'KEY_SETUP': 'setup=menu',
    'KEY_UP': 'setup=up',
    'KEY_DOWN': 'setup=down',
    'KEY_LEFT': 'setup=left',
    'KEY_RIGHT': 'setup=right',
    'BTN_BACK': 'setup=exit',
    'KEY_MUTE': 'audio-muting=toggle',
    'KEY_POWER': 'system-power=on',
    'KEY_POWER2': 'system-power=standby',
    'KEY_LISTENMODE_STEREO': '!1LMD00',
    'KEY_LISTENMODE_SURR': '!1LMD02',
    'KEY_LISTENMODE_LEFT': '!1LMDDOWN',
    'KEY_LISTENMODE_RIGHT': '!1LMDUP',
    'KEY_LISTENMODE_PUREAUDIO': '!1LMD11',
    'KEY_LISTENMODE_DIRECT': '!1LMD01',
    'KEY_LISTENMODE_THX': '!1LMD04',
    'KEY_LISTENMODE_ALLSTEREO': '!1LMD0C',
    'KEY_TESTTONE': 'speaker-level-calibration=test',
    'KEY_CHANNEL_SELECT': 'speaker-level-calibration=chsel',
    'KEY_LEVELDOWN': 'speaker-level-calibration=down',
    'KEY_LEVELUP': 'speaker-level-calibration=up',
    'KEY_AUDIOSELECT': 'audio-selector=up',
    'KEY_LATENIGHT': '!1LTNUP',
    'KEY_REEQ': '!1RASUP',

}


def write_default_config(path, program, remote='*'):
    """Create a default lircrc.

    Args:
        remote: Remote to listen for. Defaults to * (all)
        path: path to write the lirc configuration file to.
        program: program name to use in the lirc config.
    """
    command_template = """
begin
    prog = {}
    remote = {}
    button = {}
    config = {}
end
"""
    header = """
# Default lirc configuration for onkyo_serial
# config may either be a raw ISCP command (with the ! prefix) or a friendly
# command understood by the onkyo_eiscp library.
"""
    with open(path, 'w') as cfg:
        cfg.write(header)
        for key in KEYMAP:
            cfg.write(command_template.format(program, remote, key, KEYMAP[key]))


# noinspection PyAbstractClass
class LircReader(abstract.FileDescriptor):
    """A transport to read from the lirc control socket."""
    interface.implements(interfaces.IReadDescriptor)

    def __init__(self, program_name, lirc_config=None, reactor=None):
        """

        Args:
            program_name (str): Program name as used in the lircrc
            lirc_config (str): Path to the lircrc to use.
            reactor (:twisted:`twisted.internet.reactor`): twisted reactor

        """
        abstract.FileDescriptor.__init__(self, reactor)
        self._fd = -1
        self._lirc_config = lirc_config
        self._program_name = program_name

    def startReading(self):
        if self._fd != -1:
            try:
                os.fstat(self.fileno())
                abstract.FileDescriptor.startReading(self)
                return
            except OSError:
                pass
        if self._lirc_config is not None:
            self._fd = pylirc.init(self._program_name, self._lirc_config)
        else:
            self._fd = pylirc.init(self._program_name)
        pylirc.blocking(0)
        self.protocol.connectionMade()
        abstract.FileDescriptor.startReading(self)

    def doWrite(self):
        return

    def doRead(self):
        codes = pylirc.nextcode()
        output = []
        while codes:
            output.extend(codes)
            codes = pylirc.nextcode()
        if output:
            output.append('')
            self.protocol.dataReceived('\r\n'.join(output))

    def fileno(self):
        return self._fd

    def connectionLost(self, reason):
        abstract.FileDescriptor.connectionLost(self, reason)
        self.protocol.connectionLost(reason)


class LircEndPoint(object):
    """Lirc client endpoint for use with :twisted:`twisted.internet.endpoints`."""

    def __init__(self, reactor, program_name, lirc_config=None):
        self._reactor = reactor
        self._program_name = program_name
        self._lirc_config = lirc_config

    # noinspection PyProtectedMember
    def connect(self, protocolFactory):
        # noinspection PyBroadException
        try:
            wf = endpoints._WrappingFactory(protocolFactory)
            reader = LircReader(self._program_name, self._lirc_config,
                                self._reactor)
            reader.protocol = wf.buildProtocol(None)
            reader.protocol.transport = reader
            reader.startReading()
            return wf._onConnection
        except:
            return defer.fail()


class LircClientService(service.Service):
    """A service wrapper for lirc."""
    _factory = None

    def __init__(self, endpoint, factory_klass):
        """

        Args:
            endpoint (LircEndPoint):  endpoint for the service.
            factory_klass (:twisted:`twisted.internet.protocol.Factory`):
                Protocol factory class used to send data from the endpoint to.
        """
        self._endpoint = endpoint
        self._factory_klass = factory_klass

    def startService(self):
        from twisted.internet import reactor
        service.Service.startService(self)

        def failure(err):
            log.err(err, _why='Could not connect to lirc')
            reactor.stop()

        factory = self._factory_klass()
        client = self._endpoint.connect(factory)
        client.addErrback(failure)
