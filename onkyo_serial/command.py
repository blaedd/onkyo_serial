"""Handle user-friendly commands as per onkyo_eiscp."""

from eiscp import core
from twisted.internet import protocol
from twisted.protocols import basic

from . import interfaces

__author__ = 'blaedd@gmail.com'


# noinspection PyClassHasNoInit
class CommandPort(basic.LineOnlyReceiver):
    """A simple human friendly-ish command port to issue ISCP commands through.

    It uses the command mappings from the onkyo-eiscp package, but you
    can also send raw ISCP commands with the 'raw ' prefix.
    """

    def connectionMade(self):
        def mycb(cmd):
            cmd = core.iscp_to_command(cmd)
            if isinstance(cmd[0], tuple):
                cmd_name = cmd[0][0]
            else:
                cmd_name = cmd[0]
            cmdstr = '{}={}'.format(core.normalize_command(cmd_name), cmd[1])
            self.sendLine(cmdstr.encode('utf-8'))

        self.factory.add_cb(self, mycb)

    # noinspection PyUnusedLocal
    def connectionLost(self, reason=protocol.connectionDone):
        self.factory.remove_cb(self)

    def lineReceived(self, line):
        try:
            self.factory.command(line)
        except ValueError as e:
            self.sendLine(e.args[0])


class CommandPortFactory(protocol.Factory, interfaces.ISCPProxyMixin):
    """Factory for `CommandPort` protocol."""
    protocol = CommandPort

    def __init__(self, onkyo):
        """Initialize the factory.

        Args:
            onkyo (onkyo_serial.iscp.ISCP): A :twisted:`twisted.internet.protocol.Protocol`
                connected to the receiver via ISCP.

        """
        interfaces.ISCPProxyMixin.__init__(self)
        if not interfaces.IISCPDevice.providedBy(onkyo):
            raise TypeError('%{!r} does not provide {!s}', onkyo,
                            interfaces.IISCPDevice)
        self._onkyo = onkyo
