"""Communicate with Onkyo receivers via ISCP."""

import struct
import uuid

from eiscp import core
from twisted.internet import protocol
from twisted.protocols import basic
from twisted.python import log
from zope import interface

from . import interfaces


def command_to_packet(cmd):
    if isinstance(cmd, bytes):
        cmd = cmd.decode('utf-8')
    return core.eISCPPacket('!1{}\x1a'.format(cmd))


# noinspection PyPep8Naming
@interface.implementer(interfaces.IISCPDevice)
class ISCP(basic.LineOnlyReceiver):
    """Onkyo ISCP Protocol over Serial.

    The receiver will issue updates spontaneously, so the protocol
    maintains this known state internally, although nothing is done
    with it yet.

    To use, send human friendly or raw ISCP commands with command()::

        iscp_protocol.command('master-volume=50')
        iscp_protocol.command('!1MVL32')
        iscp_protocol.command('MVL20')

    To receive responses, register a callback with add_cb(), this gets invoked
    for every valid response from the receiver.

    If connecting to an actual receiver, the settings are generally

    9600 baud 8 data bits 1 stop bit no parity, no flow control

    9 pin female D type connector.

    Pins::

        2 - Transmit
        3 - Receive
        5 - Ground

    """
    delimiter = b'\x1a'
    send_delimiter = b'\n'

    def __init__(self):
        self.state = {}
        self.cb = {}

    def connectionMade(self):
        """Query the system power state initially."""
        self.command('system-power=query')

    def command(self, cmd):
        """Issue an ISCP command based on the onkyo-eiscp command mappings.

        Args:
            cmd: Command to execute.
        """
        if isinstance(cmd, bytes):
            cmd = cmd.decode('utf-8')
        if cmd.startswith('!1'):
            cmd = cmd[2:]
        try:
            cmd = '!1{}'.format(core.command_to_iscp(cmd))
        except ValueError:
            core.iscp_to_command(cmd)
            cmd = '!1{}'.format(cmd)
        self.sendLine(cmd.encode('utf-8'))

    def lineReceived(self, line):
        """Handle incoming line of text from the receiver.

        Args:
            line: the line of text to process.
        """
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        # Seen some odd characters turn up at the start of serial communications.
        # None of these characters are part of the protocol.
        line = ''.join([x for x in line if 128 > ord(x) > 32])

        if line[0:2] == '!1':
            cmd = core.iscp_to_command((line[2:].strip()))
            self.state[cmd[0]] = cmd[1]
            for inst in self.cb:
                self.cb[inst](line[2:].strip())
        else:
            log.msg('invalid line ')
            log.msg(line)

    def sendLine(self, line):
        """Send a line of text to the receiver.

        Args:
            line (bytes): Line of text to send.
        """
        if isinstance(line, str):
            line = line.encode('utf-8')
        return self.transport.write(line + self.send_delimiter)

    def add_cb(self, inst, cb):
        """Add a callback to be called for every response received.

        Args:
            inst (object): A hashable, unique identifier to refer to this callback by.
            cb (callable): callable to call for every response received from the receiver.
                It should accept one argument (the command response received).
        """
        self.cb[inst] = cb

    def remove_cb(self, inst):
        """Remove a callback.

        Args:
            inst (object): The unique identifier used when the callback was added.
        """
        if inst in self.cb:
            del self.cb[inst]


ISCPHeader = struct.Struct('!4s2ib3c')


class ISCPClientFactory(protocol.ReconnectingClientFactory,
                        interfaces.ISCPProxyMixin):
    """Client factory for an ISCP communication link."""
    protocol = ISCP
    maxDelay = 10

    def __init__(self):
        interfaces.ISCPProxyMixin.__init__(self)
        if not interfaces.IISCPDevice.implementedBy(self.protocol):
            raise TypeError('protocol must implement {!s}'.format(
                interfaces.IISCPDevice))
        self._onkyo = None

    def clientConnectionLost(self, connector, reason):
        log.msg('Lost connection')
        del self._onkyo
        self._onkyo = None
        protocol.ReconnectingClientFactory.clientConnectionLost(
            self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg('Connection failed {}'.format(reason))
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    # noinspection PyUnusedLocal
    def buildProtocol(self, addr=None):
        if self._onkyo is not None:
            raise RuntimeError('ISCP device already exists.')
        p = self.protocol()
        self.resetDelay()
        p.factory = self
        self._onkyo = p
        self._process_backlog(self._onkyo)
        return p


class eISCPMixin(object):
    """Mixin to handle all the actual eISCPBridge protocol decoding.

     This maintains internal state regarding the state of decoding.

     Re-initialize the state with :py:meth:`eISCPMixin.reset`

     Feed it data with :py:meth:`eISCPMixin._processData`

     When it successfully decodes a command, it invokes :py:meth:'doCmd`
        where cmd is the actual ISCP command, starting with the start
        character ! but lacking the end character. So you should implement
        this in your subclass.

    Lots stolen shamelessly from https://github.com/miracle2k/onkyo-eiscp
    """

    def __init__(self):
        self.header = {
            'data': b'',
            'length': 0
        }
        self.cmd = self.init_cmd(0)

    @staticmethod
    def init_cmd(length):
        """Return a fresh command dictionary with no content.
        Args:
            length: length of the packet.
        """
        return {
            'data': b'',
            'length': length,
            'cur_length': 0
        }

    def reset(self):
        """Reset the current command being processed."""
        self.cmd = self.init_cmd(0)
        self.header = {'data': b'', 'length': 0}

    def _headerStart(self):
        data = self.header['data']
        i = data.find(b'I')
        if i != -1:
            data = data[i:]
        else:
            data = b''
        self.header['data'] = data

    def _processData(self, data):
        log.msg(data)
        if isinstance(data, str):
            data = data.encode('utf-8')
            print(data)
        while data:
            if self.header['length'] < 16:
                self.header['data'] += data
                data = b''
                self.header['length'] = len(self.header['data'])
                if self.header['length'] >= 4:
                    while not self._isHeaderStart():
                        self._headerStart()
                if self.header['length'] >= 16:
                    data = self.header['data'][16:]
                    self.header['data'] = self.header['data'][:16]
                    try:
                        (_, _, length, _, _, _, _) = ISCPHeader.unpack(self.header['data'])
                        self.cmd = self.init_cmd(length)
                    except struct.error:
                        self.reset()

            self.cmd['data'] += data
            self.cmd['cur_length'] = len(self.cmd['data'])
            if self.cmd['cur_length'] >= self.cmd['length']:
                end = self.cmd['data'].find(b'\x1a')
                self.doCmd(self.cmd['data'][:end])
                data = self.cmd['data'][self.cmd['length']:]
                self.reset()

    def _isHeaderStart(self):
        data = self.header['data']
        if data.startswith(b'ISCP'):
            return True
        if len(data) > 3:
            return False
        if len(data) == 3 and data.startswith(b'ISC'):
            return True
        if len(data) == 2 and data.startswith(b'IS'):
            return True
        if len(data) == 1 and data.startswith(b'I'):
            return True
        if len(data) == 0:
            return True

        return False

    def doCmd(self, cmd):
        """Execute an ISCP command.

        Args:
            cmd: ISCP Command to execute.
        """
        raise NotImplementedError


class eISCPBridge(protocol.Protocol, eISCPMixin):
    """Twisted protocol to bridge eISCP and ISCP.

    Basically parses inbound eISCP, pulls out the ISCP
    commands, and passes them on to the ISCP protocol to be executed.

    Likewise it registers a callback with the ISCP end of the bridge, and
    for each response encapsulates it in an eISCP packet and sends it.

    Typically lives on TCP port 60128.
    """

    def connectionMade(self):
        def eiscp_callback(cmd):
            self.transport.write(command_to_packet(cmd))

        self.factory.add_cb(self, eiscp_callback)

    # noinspection PyUnusedLocal
    def connectionLost(self, reason=protocol.connectionDone):
        self.factory.remove_cb(self)

    def dataReceived(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._processData(data)

    def doCmd(self, cmd):
        self.factory.command(cmd)


class eISCPFactory(protocol.Factory, interfaces.ISCPProxyMixin):
    """Factory class for `eISCPBridge`."""

    protocol = eISCPBridge

    def __init__(self, iscp_device):
        """
        Args:
            iscp_device (:py:class:`interfaces.IISCPDevice`): ISCP device to
                read/write.
        """
        interfaces.ISCPProxyMixin.__init__(self)
        self._onkyo = iscp_device


class eISCPDiscovery(protocol.DatagramProtocol):
    """Twisted protocol for the Onkyo eISCP discovery protocol.

    This only involves a single command (query) and lives on UDP port 60128.
    Requests are typically broadcast, the response includes the port and an
    identifier (mac address) of the actual eISCPBridge server.

    You should override the model to something vaguely appropriate, since
    software will typically show you compatible feature-sets.

    Region is one of:
        DX: North America model
        XX: Europe or Asian model
        JJ: Japanese model.
    """
    model = 'TX-NR609'
    region = 'XX'

    def __init__(self, eiscp_port=60128):
        """

        Args:
                eiscp_port (int): port to listen for eISCP discovery on.
        """
        self.mac = self._getMac()
        self.eiscp_port = eiscp_port

    @staticmethod
    def _getMac():
        """Get our machines mac address and format it for the packet."""
        return '{:0>12X}'.format(uuid.getnode())

    def startProtocol(self):
        self.transport.setBroadcastAllowed(True)

    def datagramReceived(self, datagram, addr):
        """Process incoming datagrams.

        Look for eISCP discovery commands in received datagram, and reply
        if a valid one is found.

        We assume no fragmentation. If your local network is fragmenting
        25 byte UDP packets...

        Args:
            datagram: datagram to parse
            addr: Address received from
        """

        try:
            cmd = core.eISCPPacket.parse(datagram)
        except ValueError as e:
            log.err(e)
            return
        if cmd.startswith('!xECNQSTN'):
            response = 'ECN{model}/{port}/{region}/{mac}'.format(
                model=self.model, port=self.eiscp_port, region=self.region,
                mac=self.mac)
            self.transport.write(command_to_packet(response), addr)
        else:
            log.msg('Unknown command %s', cmd)


class eISCPDiscoveryFactory(protocol.Factory):
    """Factory class for `eISCPDiscovery`"""
    protocol = eISCPDiscovery

    def __init__(self, eiscp_port=60128):
        """

        Args:
            eiscp_port (int): UDP port to listen for discovery requests on.
        """
        protocol.Factory.__init__(self)
        self.eiscp_port = eiscp_port
