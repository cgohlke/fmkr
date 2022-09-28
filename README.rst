Access FileMaker(tm) Server Databases
=====================================

Fmkr is a Python library to access FileMaker(tm) Server 8 Advanced databases
via the XML publishing interface.

"FileMaker" is a registered trademark of Claris International Inc.

:Author: `Christoph Gohlke <https://www.cgohlke.com>`_
:License: BSD 3-Clause
:Version: 2022.9.28

Requirements
------------

This release has been tested with the following requirements and dependencies
(other versions may work):

- `CPython 3.8.10, 3.9.13, 3.10.7, 3.11.0rc2 <https://www.python.org>`_
- `Lxml 4.9.1 <https://pypi.org/project/lxml/>`_
- `FileMaker(tm) Server 8 Advanced <https://www.claris.com/filemaker/>`_

Revisions
---------

2022.9.28

- Convert docstrings to Google style with Sphinx directives.

2022.3.24

- Add type hints.
- Improve string representations of objects.
- Add immutable sequence interface to FMPXMLResult.
- Remove support for Python 3.6 and 3.7 (NEP 29).

2021.3.6

- Update copyright and formatting.

2020.1.1

- Remove support for Python 3.5.
- Update copyright.

2018.8.15

- Move fmkr.py into fmkr package.

2018.5.25

- Use lxml instead of minidom to parse FMPXMLResult.
- Improve string representations of FMPXMLResult and FMField.
- Update error codes.
- Remove support for Python 2.

2006.10.30

- Initial release.

References
----------

1. http://www.filemaker.com/downloads/documentation/fmsa8_custom_web_guide.pdf

Examples
--------

>>> from fmkr import FM, FMError
>>> fmi = FM('filemaker.domain.com', 80, 'http')
>>> fmi.set_db_data('database', 'layout', maxret=5)
>>> fmi.set_db_password('fmuser', 'password')
>>> # create a new record
>>> fmi.add_db_param('FIRST', 'John')
>>> fmi.add_db_param('LAST', 'Doe')
>>> fmi.fm_new()
>>> # find and sort records
>>> fmi.add_db_param('LAST', 'Doe', 'bw')
>>> fmi.add_sort_param('LAST', 'ascend', 1)
>>> fmi.add_sort_param('FIRST', 'ascend', 2)
>>> result = fmi.fm_find()
>>> for record in result:
...     print(record['FIRST'], record['LAST'])
John Doe
>>> # delete record
>>> recid = result[0]['RECORDID']
>>> fmi.set_record_id(recid)
>>> fmi.fm_delete()
>>> # catch an exception
>>> try:
...    fmi.add_db_param('LAST', 'Doe', 'cn')
...    fmi.fm_find()
... except FMError as exc:
...    print(exc)
FileMaker Error 401: No records match the request
