import mock
from eiscp import core
from twisted.internet import protocol
from twisted.test import proto_helpers
from twisted.trial import unittest

from .. import iscp


class ISCPTestCase(unittest.TestCase):
    def setUp(self):
        factory = protocol.Factory()
        factory.protocol = iscp.ISCP
        self.proto = factory.buildProtocol('/dev/ttyUSB0')
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)
        self.tr.clear()

    def testCommand(self):
        self.proto.command('system-power=query')
        self.assertEqual('!1PWRQSTN'.encode('utf-8') + self.proto.send_delimiter,
                         self.tr.value())
        self.tr.clear()
        self.proto.command('!1PWR01')
        self.assertEqual('!1PWR01'.encode('utf-8') + self.proto.send_delimiter,
                         self.tr.value())
        self.tr.clear()
        self.proto.command('PWR01')
        self.assertEqual('!1PWR01'.encode('utf-8') + self.proto.send_delimiter,
                         self.tr.value())

    def testLineReceived(self):
        cb = mock.MagicMock()
        self.proto.add_cb('mock', cb)
        self.proto.lineReceived('!1PWR00\x1a')
        self.assertTrue(cb.called)
        self.assertEqual(cb.call_args, mock.call('PWR00'))

    def testremoveCb(self):
        cb = mock.MagicMock()
        self.proto.add_cb('mock', cb)
        self.proto.lineReceived('!1PWR00\x1a')
        self.assertTrue(cb.called)
        self.proto.remove_cb('mock')
        cb.reset_mock()
        self.proto.lineReceived('!1PWR00\x1a')
        self.assertFalse(cb.called)

    def testISCPMixin(self):
        packet = str(core.eISCPPacket('!1PWR01\x1a'))
        mixin = iscp.eISCPMixin()
        mixin.doCmd = mock.MagicMock()
        mixin._processData(packet.encode('utf-8'))
        self.assertTrue(mixin.doCmd.called)
        self.assertEqual(mixin.doCmd.call_args,
                         mock.call(b'!1PWR01'))


class MockProtocol(object):
    """Mock protocol."""


class ISCPClientFactoryTestCase(unittest.TestCase):
    def setUp(self):
        pass

    @mock.patch.object(iscp.ISCPClientFactory, 'protocol', MockProtocol)
    def testIISCPDevice(self):
        self.assertRaises(TypeError, iscp.ISCPClientFactory)

    @mock.patch.object(iscp.ISCPClientFactory, 'resetDelay')
    def testBuildProtocol(self, resetDelay):
        clientFactory = iscp.ISCPClientFactory()
        p = clientFactory.buildProtocol(None)
        self.assertIsInstance(p, iscp.ISCP)
        self.assertIs(clientFactory, p.factory)
        self.assertTrue(resetDelay.called)

    def testclientConnectionLost(self):
        clientFactory = iscp.ISCPClientFactory()
        p = clientFactory.buildProtocol(None)
