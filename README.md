# Onkyo Serial library and Bridge

This library is designed for communicating with Onkyo HT receivers
via serial (either direct connection, or via TCP). Newer receivers have
native network support, however older ones are limited to the serial
connection.

This library relies heavily on the [onkyo-eiscp](https://github.com/miracle2k/onkyo-eiscp) library.

## eiscp_bridge

This is the main executable provided by the library. There are two commands
currently supported.

### lirc_config

This command generates a default lircrc to use with the run
command. It overwrites the target file, so be careful!

```
Usage: eiscp_bridge.pex [options] lirc_config [options]
Options:
  -n, --program_name=  Program name to use for lirc [default: onkyo_serial]
  -r, --remote=        Remote to listen for. [default: RC-690M]
  -p, --path=          Path to (over)write a default lircrc to.
      --version        Display Twisted version and exit.
      --help           Display this help and exit.
```

### run

Run the bridge. You must specify the address of your ISCP device with the
`--iscp_type` and `--iscp_device` options.

You can select what types of protocols to bridge to the ISCP device with the
`--listen` option. Currently valid options are command, eiscp and lirc.


```
Usage: eiscp_bridge.pex [options] run [options]
Options:
  -n, --program_name=  Program name to use for lirc [default: onkyo_serial]
  -r, --remote=        Remote to listen for. [default: RC-690M]
  -p, --eiscp=         eISCP listen port [default: 60128]
  -l, --listen=        Type of ports to listen on. Valid types are:
                       command,eiscp,lirc [default: eiscp,lirc]
  -t, --iscp_type=     Type of ISCP device, serial, tcp [default: serial]
  -d, --iscp_device=   Device (or host:port) for the ISCP device [default:
                       /dev/ttyUSB1]
  -c, --command_port=  Command port to listen on [default: 60129]
      --lirc_config=   Path to a custom lirc configuration file.
      --version        Display Twisted version and exit.
      --help           Display this help and exit.
```
#### Using with lirc
The program name you supply via `--program_name` must match the one in your
configuration file. Likewise your remote name must match the one you provide
with the `--remote` option.

You *must* specify the path to your lircrc with the `--lirc_config` option.
There is no default.

