python_tests(name='app',
    dependencies=[
        '//src/python/onkyo_serial:onkyo_serial',
        '//3rdparty/python:mock',
    ],
    sources=['test_app.py'])

python_tests(name='command',
    dependencies=[
        '//src/python/onkyo_serial:onkyo_serial',
        '//3rdparty/python:mock',
    ],
    sources=['test_command.py'])

python_tests(name='iscp',
    dependencies=[
        '//src/python/onkyo_serial:onkyo_serial',
        '//3rdparty/python:mock',
    ],
    sources=['test_iscp.py'])

python_tests(name='lirc',
    dependencies=[
        '//src/python/onkyo_serial:onkyo_serial',
        '//3rdparty/python:mock',
    ],
   sources=['test_lirc.py'])

python_tests(name='service',
    dependencies=[
        '//src/python/onkyo_serial:onkyo_serial',
        '//3rdparty/python:mock',
    ],
    sources=['test_service.py'])

python_tests(name='all',
    dependencies=[
        ':app',
        ':command',
        ':iscp',
        ':lirc',
        ':service',
    ]
    )

