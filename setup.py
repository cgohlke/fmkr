# fmkr/setup.py

import sys
import re

from setuptools import setup

with open('fmkr/fmkr.py') as fh:
    code = fh.read()

version = re.search(r"__version__ = '(.*?)'", code).groups()[0]
description = re.search(r'"""(.*)\.\n', code).groups()[0]
readme = re.search(r'[\r\n?|\n]{2}"""(.*)"""[\r\n?|\n]{2}import', code,
                   re.MULTILINE | re.DOTALL).groups()[0]
license = re.search(r'(# Copyright.*?[\r\n?|\n])[\r\n?|\n]+""', code,
                    re.MULTILINE | re.DOTALL).groups()[0]

readme = '\n'.join([description, '=' * len(description)]
                   + readme.splitlines()[1:])
license = license.replace('# ', '').replace('#', '')

if 'sdist' in sys.argv:
    with open('LICENSE', 'w') as fh:
        fh.write(license)
    with open('README.rst', 'w') as fh:
        fh.write(readme)

setup(
    name='fmkr',
    version=version,
    description=description,
    long_description=readme,
    author='Christoph Gohlke',
    author_email='cgohlke@uci.edu',
    url='https://www.lfd.uci.edu/~gohlke/',
    packages=['fmkr'],
    install_requires=['lxml>=4.2'],
    license='BSD',
    zip_safe=True,
    platforms=['any'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Topic :: Database',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        ],
)
