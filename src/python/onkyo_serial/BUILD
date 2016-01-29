python_library(name='onkyo_serial',
    sources=globs('*.py'),
    dependencies=[
        '3rdparty/python:onkyo-eiscp',
        '3rdparty/python:pyserial',
        '3rdparty/python:pyxdg',
        '3rdparty/python:Twisted',
        '3rdparty/python:zope.interface',
        '3rdparty/python:wheel',
        '3rdparty/python:pylirc2',
    ],
    provides=setup_py(
        name='onkyo_serial',
        version='0.0.1',
        description='Library for communicating with Onkyo HT receivers over serial.',
        long_description=\
'''Library for communicationg with Onkyo HT receivers over serial (ISCP).

Also includes code to bridge the receiver with other protocols,
which currently include:

    - lirc
    - EISCP (including discovery packets)
    - Text based TCP command port
''',
        url='https://github.com/blaedd/onkyo_serial',
        license='MIT',
        entry_points = {
            'console_scripts': [
                'eiscp_bridge = onkyo_serial.app:start',
            ],
        }
   )
)

python_binary(name='eiscp_bridge',
    entry_point='onkyo_serial.app:start',
    dependencies=['src/python/onkyo_serial:onkyo_serial'],
)