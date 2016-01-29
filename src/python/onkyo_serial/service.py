"""Service wrappers."""

import logging

from twisted.application import service
from twisted.internet import endpoints, error, serialport, defer, task
from twisted.python import log

from . import iscp

__author__ = 'blaedd@gmail.com'


class OnkyoService(service.Service):
    """A basic service for protocols that relay commands to an ISCP device."""

    _factory = None

    def __init__(self, endpoint, factory_klass):
        """

        Args:
            endpoint (str): an endpoint url to listen on.
            factory_klass (:twisted:`twisted.internet.protocol.Factory`): factory class
                for the protocol.
        """
        self._endpoint = endpoint
        self._port = None
        self._factory_klass = factory_klass

    def startService(self):
        """Construct server and bind."""
        from twisted.internet import reactor
        service.Service.startService(self)

        def connected(port):
            self._port = port

        # noinspection PyUnresolvedReferences
        def failure(err):
            log.err(err, _why='Could not bind to port')
            reactor.stop()

        factory = self._factory_klass()
        server = endpoints.serverFromString(reactor, self._endpoint)

        d = server.listen(factory)
        d.addCallbacks(connected, failure)
        return d

    def stopService(self):
        """Stop server."""
        service.Service.stopService(self)
        if self._port is not None:
            d = self._port.stopListening()
            del self._port
            return d

    def _onListen(self, port):
        self._port = port


# noinspection PyTypeChecker
class SerialISCPService(service.MultiService):
    """Service for an ISCP device, which also serves as a container.
    """

    def __init__(self, device, baudrate=9600):
        """

        Args:
            device(str): serial device to connect to
            baudrate(int): baudrate to use with device.
        """
        service.MultiService.__init__(self)
        self._iscp = iscp.ISCP()
        self._device = device
        self._baudrate = baudrate
        self._serial = None

    def startService(self):
        from twisted.internet import reactor
        service.Service.startService(self)
        self._serial = serialport.SerialPort(self._iscp, self._device, reactor, baudrate=self._baudrate)
        for svc in self:
            svc.startService()

    def stopService(self):
        service.Service.stopService(self)
        l = []
        for svc in reversed(list(self)):
            l.append(defer.maybeDeferred(svc.stopService))
        if l:
            l = defer.DeferredList(l)
            l.addCallback(self._serial.connectionLost, error.ConnectionDone())
        else:
            self._serial.connectionLost(error.ConnectionDone())
        return l

    def getProtocol(self):
        """Returns the `onkyo_serial.iscp.ISCP` for this service."""
        return self._iscp


# noinspection PyTypeChecker,PyTypeChecker,PyTypeChecker,PyTypeChecker
class ISCPClientService(service.MultiService):
    """ISCP over an endpoint (likely a raw tcp connection from a console server)"""

    def __init__(self, connectMethod, *args, **kwargs):
        service.MultiService.__init__(self)
        self._connectMethod = connectMethod
        self._args = args
        self._kwargs = kwargs
        self._connector = None
        self._factory = iscp.ISCPClientFactory()

    def startService(self):
        service.Service.startService(self)
        self._connector = self._connectMethod(*self._args, factory=self._factory, **self._kwargs)

        def waitForConnect():
            if self._connector.state == 'connected':
                log.msg('Starting child services now.', level=logging.DEBUG)
                # noinspection PyTypeChecker
                for svc in self:
                    svc.startService()
            else:
                from twisted.internet import reactor
                task.deferLater(reactor, 1, waitForConnect)

        waitForConnect()

    def stopService(self):
        def stop_cb():
            if self._connector is not None:
                self._connector.disconnect()
                del self._connector

        service.Service.stopService(self)
        l = []
        for svc in reversed(list(self)):
            l.append(defer.maybeDeferred(svc.stopService))
        if l:
            l = defer.DeferredList(l)
            l.addCallback(stop_cb)
        else:
            stop_cb()
        return l

    def getProtocol(self):
        return self._factory


# noinspection PyUnresolvedReferences
def ISCPTCPService(host, port):
    """Create an ISCP client service over TCP

    Args:
        host(str): Host to connect to.
        port(int): port to connect to.

    Returns:
        `ISCPClientService`
    """
    from twisted.internet import reactor
    return ISCPClientService(reactor.connectTCP, host, port)
