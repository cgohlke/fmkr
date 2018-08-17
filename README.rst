Access FileMaker(tm) Server Databases
=====================================

Access FileMaker(tm) Server 8 Advanced databases via XML publishing interface.

FileMaker is a registered trademark of FileMaker Inc.

:Author:
  `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:Organization:
  Laboratory for Fluorescence Dynamics. University of California, Irvine

:Version: 2018.8.15

Requirements
------------
* `CPython 3.5+ <https://www.python.org>`_
* `FileMaker(tm) Server 8 Advanced <https://www.filemaker.com>`_
* `lxml 4.2 <https://github.com/lxml/lxml>`_

Revisions
---------
2018.8.15
    Move module into fmkr package.
2018.5.25
    Use lxml instead of minidom to parse FMPXMLResult.
    Improve string representations of FMPXMLResult and FMField.
    Update error codes.
    Drop support for Python 2.
2006.10.30
    Initial release.

References
----------
(1) http://www.filemaker.com/downloads/documentation/fmsa8_custom_web_guide.pdf

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
>>> for record in result.resultset:
...     print(record['FIRST'], record['LAST'])
John Doe
>>> # delete record
>>> recid = result.resultset[0]['RECORDID']
>>> fmi.set_record_id(recid)
>>> fmi.fm_delete()
>>> # catch an exception
>>> try:
...    fmi.add_db_param('LAST', 'Doe', 'cn')
...    fmi.fm_find()
... except FMError as e:
...    print(e)
FileMaker Error 401: No records match the request
