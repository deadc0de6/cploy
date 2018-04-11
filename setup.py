from setuptools import setup, find_packages
from codecs import open
from os import path
import cploy

readme = 'README.md'
here = path.abspath(path.dirname(__file__))

try:
    from pypandoc import convert
    read_readme = lambda f: convert(f, 'rst')
except ImportError:
    print('\n[WARNING] pypandoc not found, could not convert \"{}\"\n'.format(readme))
    read_readme = lambda f: open(f, 'r').read()

VERSION = cploy.__version__
REQUIRES_PYTHON = '>=3.5'

setup(
    name='cploy',
    version=VERSION,

    description='The ad hoc continuous deployment solution for developers',
    long_description=read_readme(readme),
    url='https://github.com/deadc0de6/cploy',
    download_url = 'https://github.com/deadc0de6/cploy/archive/v'+VERSION+'.tar.gz',

    author='deadc0de6',
    author_email='deadc0de6@foo.bar',

    license='GPLv3',
    requires_python=REQUIRES_PYTHON,
    classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          ],

    keywords='continuous deployment cli',
    packages=find_packages(exclude=['tests*', 'design*']),
    install_requires=['docopt', 'paramiko',
                      'pyinotify', 'python-daemon'],

    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage', 'pytest', 'pytest-cov'],
    },

    entry_points={
        'console_scripts': [
            'cploy=cploy:main',
        ],
    },
)
