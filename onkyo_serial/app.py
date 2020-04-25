"""Application module for the Onkyo ISCP protocol bridge."""

import functools

import sys
from twisted.application import internet
from twisted.python import log
from twisted.python import usage

from . import command
from . import iscp
# from . import lirc
from . import service

__author__ = 'blaedd@gmail.com'

PORT_TYPES = ['command', 'eiscp']


class GenericOptions(usage.Options):
    """Generic options."""
    optParameters = [
        ['remote', 'r', 'RC-690M', 'Remote to listen for.'],
    ]


class RunOptions(GenericOptions):
    """Options related to running the bridge."""
    optParameters = [
        ['eiscp', 'p', '60128', 'eISCP listen port'],
        ['listen', 'l', 'eiscp'
         'Type of ports to listen on. Valid types are: {}'.format(
                 ','.join(PORT_TYPES))
         ],
        ['iscp_type', 't', 'serial', 'Type of ISCP device, serial, tcp'],
        ['iscp_device', 'd', '/dev/ttyUSB1',
         'Device (or host:port) for the ISCP device'],
        ['command_port', 'c', '60129', 'Command port to listen on'],
    ]

    compData = usage.Completions(
            optActions={
                'iscp_type': usage.CompleteList(
                        items=['serial', 'tcp'], repeat=False),
                'listen': usage.CompleteMultiList(
                        items=[PORT_TYPES]
                )

            }
    )

    def postOptions(self):
        self.opts['listen'] = self.opts['listen'].split(',')
        port_set = set(PORT_TYPES)
        if not port_set.issuperset(self.opts['listen']):
            invalid_ports = set(self.opts['listen']) - port_set
            raise usage.UsageError(
                    'Invalid port types: {}\n Valid types: {}'.format(
                            ','.join(invalid_ports), ','.join(PORT_TYPES)))


class Options(usage.Options):
    """Options."""

    subCommands = [
        ['run', None, RunOptions, 'Run the server'],
    ]
    defaultSubCommand = 'run'


def makeService(config):
    """Create the ISCP service.

    Args:
        config (RunOptions): configuration for the service.
    """
    if config['iscp_type'] == 'serial':
        iscp_service = service.SerialISCPService(config['iscp_device'])
    else:
        host, port = config['iscp_device'].split(':', 1)
        iscp_service = service.ISCPTCPService(host, int(port))
    eiscp_port = int(config['eiscp'])
    command_port = int(config['command_port'])

    if 'eiscp' in config['listen']:
        eiscp_service = service.OnkyoService(
                'tcp:{}'.format(eiscp_port),
                functools.partial(iscp.eISCPFactory, iscp_service.getProtocol()))
        eiscp_service.setServiceParent(iscp_service)

        discovery = iscp.eISCPDiscovery(eiscp_port)
        # noinspection PyUnresolvedReferences
        discovery_service = internet.UDPServer(eiscp_port, discovery)
        discovery_service.setServiceParent(iscp_service)

    if 'command' in config['listen']:
        command_service = service.OnkyoService(
                'tcp:{}'.format(command_port),
                functools.partial(command.CommandPortFactory, iscp_service.getProtocol()))
        command_service.setServiceParent(iscp_service)

    return iscp_service


def start():
    config = Options()
    try:
        config.parseOptions()
    except usage.UsageError as errortext:
        print(('{}: {}'.format(sys.argv[0], errortext)))
        print(('{}: Try --help for usage details'.format(sys.argv[0])))
        sys.exit(1)
    elif config.subCommand == 'run':
        from twisted.internet import reactor

        observer = log.startLogging(sys.stdout)
        observer.timeFormat = ''
        log.msg('Starting...')

        # noinspection PyTypeChecker
        iscp_service = makeService(config.subOptions)
        iscp_service.startService()

        reactor.run()
    else:
        raise usage.UsageError('Unknown subcommand {}'.format(config.subCommand))


if __name__ == '__main__':
    start()