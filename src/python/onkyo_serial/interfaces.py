"""Interfaces for onkyo_serial."""

from zope import interface


# noinspection PyMethodMayBeStatic,PyMethodParameters
class IISCPDevice(interface.Interface):
    """Interface that represents an ISCP device."""

    def command(line):
        """Send a command to the ISCP device.

        This can either be in human readable form::
            system-power=standby

        or as a raw ISCP command with or without the !1 prefix::
            !1PWR00
            PWR00

        Args:
            line (str): Command to send to the device.
        """

    def add_cb(inst, cb):
        """Add a callback to the ISCP device.

        The callback should have a signature of cb(resp), where resp
        is a raw ISCP message sent by the receiver.

        Args:
            inst (object): a unique hashable identifier for this callback.
            cb (callable): the callback to add.
        """

    def remove_cb(inst):
        """Remove a callback from the ISCP device.

        Args:
            inst (object): the unique identifier for the callback we wish to
                remove.
        """


@interface.implementer(IISCPDevice)
class ISCPProxyMixin(object):
    _proxyMethods = ['command', 'add_cb', 'remove_cb']
    _proxyDeviceAttr = '_onkyo'

    def __init__(self):
        self._add_cb_queue = {}
        self._remove_cb_queue = {}

    def _process_backlog(self, proxy):
        while self._add_cb_queue:
            proxy.add_cb(*self._add_cb_queue.popitem())
        while self._remove_cb_queue:
            proxy.add_cb(*self._remove_cb_queue.popitem())

    def command(self, line):
        proxy = getattr(self, self._proxyDeviceAttr)
        if proxy is not None:
            self._process_backlog(proxy)
            proxy.command(line)

    def add_cb(self, inst, cb):
        proxy = getattr(self, self._proxyDeviceAttr)
        if proxy is not None:
            self._process_backlog(proxy)
            proxy.add_cb(inst, cb)
        else:
            if inst in self._remove_cb_queue:
                del self._remove_cb_queue[inst]
            self._add_cb_queue[inst] = cb

    def remove_cb(self, inst):
        proxy = getattr(self, self._proxyDeviceAttr)
        if proxy is not None:
            self._process_backlog(proxy)
            proxy.remove_cb(inst)
        else:
            if inst in self._add_cb_queue:
                del self._add_cb_queue[inst]
