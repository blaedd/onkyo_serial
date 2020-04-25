import setuptools
import onkyo_serial

with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name='onkyo_serial-blaedd',
    version='0.0.2',
    author=onkyo_serial.__author__,
    author_email=onkyo_serial.__author_email__,
    description="Python module for Onkyo/Integra ISCP Control Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'eiscp_bridge = onkyo_serial.app:start',
        ],
    },
    install_requires=[
         'onkyo-eiscp~=1.2.7',
         'pyserial~=3.4',
         'pyxdg~=0.26',
         'Twisted~=20.3.0',
         'zope.interface~=5.1.0',
         'pytz~=2019.3',
    ],
)