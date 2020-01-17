# fmkr.py

# Copyright (c) 2006-2020, Christoph Gohlke
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Access FileMaker(tm) Server Databases.

Fmkr is a Python library to access FileMaker(tm) Server 8 Advanced databases
via the XML publishing interface.

"FileMaker" is a registered trademark of FileMaker Inc.

:Author:
  `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:Organization:
  Laboratory for Fluorescence Dynamics. University of California, Irvine

:License: BSD 3-Clause

:Version: 2020.1.1

Requirements
------------
* `CPython >= 3.6 <https://www.python.org>`_
* `lxml 4.2 <https://github.com/lxml/lxml>`_
* `FileMaker(tm) Server 8 Advanced <https://www.filemaker.com>`_

Revisions
---------
2020.1.1
    Remove support for Python 3.5.
    Update copyright.
2018.8.15
    Move fmkr.py into fmkr package.
2018.5.25
    Use lxml instead of minidom to parse FMPXMLResult.
    Improve string representations of FMPXMLResult and FMField.
    Update error codes.
    Remove support for Python 2.
2006.10.30
    Initial release.

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
... except FMError as exc:
...    print(exc)
FileMaker Error 401: No records match the request

"""

__version__ = '2020.1.1'

__all__ = ('FM', 'FMError', 'FMField', 'FMPXMLResult')

import base64
from html import escape
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from lxml import etree


class FM:
    """FileMaker Server 8 Advanced XML publishing interface."""

    URL = '{_protocol}://{_server}:{_port}/fmi/xml/FMPXMLRESULT.xml'

    def __init__(self, server, port=80, protocol='http'):
        """Specify location of the FileMaker XML publishing interface.

        Parameters
        ----------
        server : str
            IP address or domain name of FileMaker Web server.
        port : int
            TCP/IP port number used by FileMaker Web server (default: 80).
        protocol : str
            'http' (default) or 'https'.

        """
        self._server = str(server)
        self._port = int(port)
        self._protocol = str(protocol)
        self._escrslt = False
        self._dbname = ''
        self._dbuser = ''
        self._dbpasswd = ''
        self._dbdata = []
        self._dbparams = []
        self._maxret = 50

    def set_db_data(self, name, layout, maxret=50, response=None):
        """Specify database and layout to be accessed.

        Parameters
        ----------
        name : str
            Name of database to be accessed.
        layout : str
            Name of layout to be accessed.
        maxret : str
            Optional maximum number of records returned by query.
        response : str
            Optional name of response layout.

        """
        self._dbdata = []
        self._dbdata_append(('-db', name))
        self._dbdata_append(('-lay', layout))
        if response:
            self._dbdata_append(('-lay.response', response))
        self._maxret = maxret

    def set_db_password(self, username, password):
        """Specify credentials for accessing database.

        Parameters
        ----------
        username : str
            User name for FileMaker authentication.
        password : str
            Password associated with user.

        """
        self._dbuser = str(username)
        self._dbpasswd = str(password)

    def set_script(self, name, option=None):
        """Specify script to be performed on returned data set.

        Parameters
        ----------
        name : str
            FileMaker script name.
        option : str
            Specify when script is to be executed.
            None : Execute script after find and sort (default).
            'prefind' : Execute script before find and sort.
            'presort' : Execute script after find, before sort.

        """
        key = '-script'
        if option in ('prefind', 'presort'):
            key += '.' + option
        self._dbparams_append((key, name))

    def set_record_id(self, recid):
        """Specify ID of record to be edited or deleted."""
        self._dbparams_append(('-recid', recid))

    def set_modifier_id(self, modid):
        """Specify modifier ID of record to be changed.

        Exception #306 will be raised if data being submitted is older
        than existing one.

        """
        self._dbparams_append(('-modid', modid))

    def set_logical_or(self):
        """Specify to perform logical 'or' instead of 'and' search.

        Returned records will match any, not all, of query criteria.

        """
        self._dbparams_append(("-lop", "or"))

    def set_group_size(self, maxret):
        """Specify maximum number of records to be returned."""
        self._maxret = int(maxret)

    def set_skip_records(self, skip):
        """Specify index of first record to be returned."""
        if int(skip):
            self._dbparams_append(('-skip', skip))

    def set_escape(self, value=True):
        """Specify to escape and encode all u'TEXT' types in result records."""
        self._escrslt = bool(value)

    def add_db_param(self, field, value, op=None):
        """Specify field data and query criteria. May be called multiple times.

        Parameters
        ----------
        field : str
            Name of field to update or query against.
        value : various types
            Value of field.
        op : str
            Optional operator used to compare data at field level.
            'eq' : 'equals'
            'cn' : 'contains'
            'bw' : 'begins with' (default)
            'ew' : 'ends with'
            'gt' : 'greater than'
            'gte' : 'greater than or equal to'
            'lt' : 'less than'
            'lte' : 'less than or equal to'
            'neq' : 'not equal to'

        """
        self._dbparams_append((field, value))
        if op:
            self._dbparams_append((f'{field}.op', op))

    def add_db_params(self, fieldvalues):
        """Specify multiple parameters using sequence of (field, value)."""
        for (field, value) in fieldvalues:
            self.add_db_param(field, value)

    def add_sort_param(self, field, order='ascend', priority=0):
        """Specify how found records will be sorted.

        Parameters
        ----------
        field : str
            Name of field to sort by.
        order : str
            Sort order.
            'ascend': Ascending (default).
            'descend': Descending.
            'custom': Name of a value list.
        priority : int
            Integer value to place multiple sort requests in a
            specified order (default: 0).

        """
        self._dbparams_append((f'-sortfield.{priority}', field))
        self._dbparams_append((f'-sortorder.{priority}', order))

    def fm_find(self):
        """Find records matching preset search criteria.

        Return FMPXMLResult instance containing sequence of found records.

        """
        return self._commit('find')

    def fm_find_all(self):
        """Find all records.

        Return FMPXMLResult instance containing all records.

        """
        return self._commit('findall')

    def fm_edit(self):
        """Update contents of given record with preset field data.

        Return FMPXMLResult instance containing updated record.

        """
        return self._commit("edit")

    def fm_new(self):
        """Create new record with preset field data.

        Return FMPXMLResult instance containing new record.

        """
        return self._commit('new')

    def fm_delete(self):
        """Delete given record."""
        return self._commit('delete')

    def _dbparams_append(self, arg):
        """Append arg to _dbparams."""
        self._dbparams.append((arg[0], arg[1]))

    def _dbdata_append(self, arg):
        """Append arg to _dbdata."""
        self._dbdata.append((arg[0], arg[1]))

    def _commit(self, action):
        """Submit request to FileMaker XML publishing interface.

        Return FMPXMLResult instance.

        """
        self._dbparams_append(('-max', self._maxret))

        url = FM.URL.format(**self.__dict__)
        data = urlencode(self._dbdata + self._dbparams) + '&-' + action
        self._dbparams = []
        # use POST to submit data
        request = Request(url, data.encode('ascii'))
        request.add_header('User-Agent', b'Fmkr.py')
        # authorization header
        auth = f'{self._dbuser}:{self._dbpasswd}'
        auth = b'Basic ' + base64.encodebytes(auth.encode('utf-8'))[:-1]
        request.add_header('Authorization', auth)

        try:
            fd = urlopen(request)
        except HTTPError as exc:
            raise FMError(str(exc))
        except URLError as exc:
            raise FMError(f'URL Error: {exc.reason}')

        results = FMPXMLResult()
        results.httpinfo = fd.info()
        results.url = url + '?' + data
        # hide logon information
        # if self._dbuser and self._dbpasswd:
        #     results.url = results.url.replace(
        #         "//", f"//{self._dbuser}:{self._dbpasswd}@", 1)
        root = etree.parse(fd).getroot()
        fd.close()

        # <ERRORCODE>0</ERRORCODE>
        try:
            results.errorcode = int(root[0].text)
        except Exception:
            results.errorcode = -1
        if results.errorcode != 0:
            raise FMError(results.errorcode)

        # <PRODUCT BUILD="06/14/2006" NAME="FileMaker Web Publishing Engine"
        #          VERSION="8.0.4.128"/>
        results.product.update(root[1].attrib)

        # <DATABASE DATEFORMAT="MM/dd/yyyy" LAYOUT="data entry"
        #           NAME="Test" RECORDS="68" TIMEFORMAT="HH:mm:ss"/>
        results.database.update(root[2].attrib)

        # <METADATA>
        metadata = results.metadata
        for field in root[3]:
            metadata.append(FMField(field.attrib))

        # <RESULTSET>
        escrslt = self._escrslt
        for row in root[4]:
            record = {
                'MODID': int(row.attrib['MODID']),
                'RECORDID': int(row.attrib['RECORDID'])
            }
            for md, cn in zip(metadata, row.iterchildren()):
                if escrslt and md.dtype == str:
                    convert_type = escape_unicode
                else:
                    convert_type = md.dtype
                if md.maxrepeat == 1:
                    value = cn[0].text
                    if value is not None:
                        value = convert_type(value)
                else:
                    value = []
                    for c in cn.iterchildren():
                        v = c.text
                        if v is None:
                            break
                        value.append(convert_type(v))
                record[md.name] = value
            results.resultset.append(record)

        return results


class FMPXMLResult:
    """Result of FileMaker XML publishing interface query.

    Attributes
    ----------
    resultset : list
        Sequence of records returned by FileMaker.
        Records are stored as dictionaries {'database field name': value}.
        String character encoding is UTF-8.
    errorcode : int
        Error code number as specified in FMError.CODES.
    metadata : list
        Sequence of FMField objects.
    httpinfo : str
        HTTP header string returned by FileMaker.
    database : dict
        Dictionary of FileMaker database information.
    product : dict
        Dictionary of FileMaker product information.
    url : str
        URL used to query FileMaker XML interface.

    """

    __slots__ = (
        'resultset', 'metadata', 'product', 'database', 'url', 'httpinfo',
        'errorcode'
    )

    def __init__(self):
        self.resultset = []
        self.metadata = []
        self.product = {}
        self.database = {}
        self.url = ''
        self.httpinfo = ''
        self.errorcode = 0

    def __str__(self):
        """Return string with info about FMPXMLResult."""
        return '\n\n'.join((
            'FMPXMLResult',
            'URL = {}'.format(self.url),
            'HTTPINFO =\n{}'.format(str(self.httpinfo).strip()),
            'ERRORCODE = {} <{}>'.format(
                self.errorcode, FMError.CODES[self.errorcode]),
            'PRODUCT = {}'.format(self.product),
            'DATABASE = {}'.format(self.database),
            'METADATA = [\n {}\n]'.format(
                '\n '.join(str(s) for s in self.metadata)),
            'RESULTSET = {}'.format(
                ('[\n {}\n]'.format(
                    '\n '.join(str(s) for s in self.resultset)))
                if self.resultset else '[]')))


class FMField:
    """Attributes of FileMaker metadata field.

    Attributes
    ----------
    name : str
        Field name.
    type : type
        Field type.
    emptyok : bool
        Identifies whether field may be left empty.
    maxrepeat : int
        Number of repetitions defined for field.

    """

    __slots__ = ('name', 'maxrepeat', 'emptyok', 'dtype')

    DTYPES = {  # map FileMaker(tm) to Python types
        'NUMBER': str,
        'TEXT': str,
        'DATE': str,
        'TIME': str,
        'TIMESTAMP': str,
        'CONTAINER': str,
        'CALCULATION': str,
        'SUMMARY': str,
    }

    def __init__(self, attributes):
        # <FIELD EMPTYOK="YES" MAXREPEAT="1" NAME="NAME" TYPE="TEXT"/>
        self.name = attributes['NAME']
        self.maxrepeat = int(attributes['MAXREPEAT'])
        self.emptyok = attributes['EMPTYOK'] == 'YES'
        try:
            self.dtype = FMField.DTYPES[attributes['TYPE']]
        except KeyError:
            self.dtype = str

    def __str__(self):
        return "FMField name='{}' dtype={} maxrepeat={} emptyok={}".format(
            self.name, self.dtype, self.maxrepeat, self.emptyok)

    def __repr__(self):
        return str(self)


class FMError(Exception):
    """Exception to report FileMaker problems.

    Attributes
    ----------
    message : unicode or str
        Error message.
    code : int
        Error code number.

    """

    CODES = {
        -1: 'Unknown error',
        0: 'No error',
        1: 'User canceled action',
        2: 'Memory error',
        3: 'Command is unavailable (for example, wrong operating system, '
           'wrong mode, etc.)',
        4: 'Command is unknown',
        5: 'Command is invalid (for example, a Set Field script step does '
           'not have a calculation specified)',
        6: 'File is read-only',
        7: 'Running out of memory',
        8: 'Empty result',
        9: 'Insufficient privileges',
        10: 'Requested data is missing',
        11: 'Name is not valid',
        12: 'Name already exists',
        13: 'File or object is in use',
        14: 'Out of range',
        15: 'Can\'t divide by zero',
        16: 'Operation failed, request retry (for example, a user query)',
        17: 'Attempt to convert foreign character set to UTF-16 failed',
        18: 'Client must provide account information to proceed',
        19: 'String contains characters other than A-Z, a-z, 0-9 (ASCII)',
        100: 'File is missing',
        101: 'Record is missing',
        102: 'Field is missing',
        103: 'Relationship is missing',
        104: 'Script is missing',
        105: 'Layout is missing',
        106: 'Table is missing',
        107: 'Index is missing',
        108: 'Value list is missing',
        109: 'Privilege set is missing',
        110: 'Related tables are missing',
        111: 'Field repetition is invalid',
        112: 'Window is missing',
        113: 'Function is missing',
        114: 'File reference is missing',
        130: 'Files are damaged or missing and must be reinstalled',
        131: 'Language pack files are missing (such as template files)',
        200: 'Record access is denied',
        201: 'Field cannot be modified',
        202: 'Field access is denied',
        203: 'No records in file to print, or password doesn\'t allow print '
             'access',
        204: 'No access to field(s) in sort order',
        205: 'User does not have access privileges to create new records; '
             'import will overwrite existing data',
        206: 'User does not have password change privileges, or file is '
             'not modifiable',
        207: 'User does not have sufficient privileges to change database '
             'schema, or file is not modifiable',
        208: 'Password does not contain enough characters',
        209: 'New password must be different from existing one',
        210: 'User account is inactive',
        211: 'Password has expired',
        212: 'Invalid user account and/or password. Please try again',
        213: 'User account and/or password does not exist',
        214: 'Too many login attempts',
        215: 'Administrator privileges cannot be duplicated',
        216: 'Guest account cannot be duplicated',
        217: 'User does not have sufficient privileges to modify '
             'administrator account',
        300: 'File is locked or in use',
        301: 'Record is in use by another user',
        302: 'Table is in use by another user',
        303: 'Database schema is in use by another user',
        304: 'Layout is in use by another user',
        306: 'Record modification ID does not match',
        400: 'Find criteria are empty',
        401: 'No records match the request',
        402: 'Selected field is not a match field for a lookup',
        403: 'Exceeding maximum record limit for trial version of '
             'FileMaker(tm)) Pro',
        404: 'Sort order is invalid',
        405: 'Number of records specified exceeds number of records that '
             'can be omitted',
        406: 'Replace/Reserialize criteria are invalid',
        407: 'One or both match fields are missing (invalid relationship)',
        408: 'Specified field has inappropriate data type for this operation',
        409: 'Import order is invalid',
        410: 'Export order is invalid',
        412: 'Wrong version of FileMaker(tm) Pro used to recover file',
        413: 'Specified field has inappropriate field type',
        414: 'Layout cannot display the result',
        415: 'Related Record Required',
        500: 'Date value does not meet validation entry options',
        501: 'Time value does not meet validation entry options',
        502: 'Number value does not meet validation entry options',
        503: 'Value in field is not within the range specified in '
             'validation entry options',
        504: 'Value in field is not unique as required in validation '
             'entry options',
        505: 'Value in field is not an existing value in the database '
             'file as required in validation entry options',
        506: 'Value in field is not listed on the value list specified '
             'in validation entry option',
        507: 'Value in field failed calculation test of validation entry '
             'option',
        508: 'Invalid value entered in Find mode',
        509: 'Field requires a valid value',
        510: 'Related value is empty or unavailable',
        511: 'Value in field exceeds maximum number of allowed characters',
        600: 'Print error has occurred',
        601: 'Combined header and footer exceed one page',
        602: 'Body doesn\'t fit on a page for current column setup',
        603: 'Print connection lost',
        700: 'File is of the wrong file type for import',
        706: 'EPSF file has no preview image',
        707: 'Graphic translator cannot be found',
        708: 'Can\'t import the file or need color monitor support to '
             'import file',
        709: 'QuickTime movie import failed',
        710: 'Unable to update QuickTime file reference because the '
             'database file is read-only',
        711: 'Import translator cannot be found',
        714: 'Password privileges do not allow the operation',
        715: 'Specified Excel worksheet or named range is missing',
        716: 'A SQL query using DELETE, INSERT, or UPDATE is not allowed '
             'for ODBC import',
        717: 'There is not enough XML/XSL information to proceed with the '
             'import or export',
        718: 'Error in parsing XML file (from Xerces)',
        719: 'Error in transforming XML using XSL (from Xalan)',
        720: 'Error when exporting; intended format does not support '
             'repeating fields',
        721: 'Unknown error occurred in the parser or the transformer',
        722: 'Cannot import data into a file that has no fields',
        723: 'You do not have permission to add records to or modify '
             'records in the target table',
        724: 'You do not have permission to add records to the target table',
        725: 'You do not have permission to modify records in the '
             'target table',
        726: 'There are more records in the import file than in the '
             'target table. Not all records were imported',
        727: 'There are more records in the target table than in the '
             'import file. Not all records were updated',
        729: 'Errors occurred during import. Records could not be imported',
        730: 'Unsupported Excel version. (Convert file to Excel 7.0 '
             '(Excel 95), Excel 97, 2000, or XP format and try again)',
        731: 'The file you are importing from contains no data',
        732: 'This file cannot be inserted because it contains other files',
        733: 'A table cannot be imported into itself',
        734: 'This file type cannot be displayed as a picture',
        735: 'This file type cannot be displayed as a picture. It will be '
             'inserted and displayed as a file 800 Unable to create file '
             'on disk',
        801: 'Unable to create temporary file on System disk',
        802: 'Unable to open file',
        803: 'File is single user or host cannot be found',
        804: 'File cannot be opened as read-only in its current state',
        805: 'File is damaged; use Recover command',
        806: 'File cannot be opened with this version of FileMaker(tm) Pro',
        807: 'File is not a FileMaker(tm) Pro file or is severely damaged',
        808: 'Cannot open file because access privileges are damaged',
        809: 'Disk/volume is full',
        810: 'Disk/volume is locked',
        811: 'Temporary file cannot be opened as FileMaker(tm) Pro file',
        813: 'Record Synchronization error on network',
        814: 'File(s) cannot be opened because maximum number is open',
        815: 'Couldn\'t open lookup file',
        816: 'Unable to convert file',
        817: 'Unable to open file because it does not belong to this solution',
        819: 'Cannot save a local copy of a remote file',
        820: 'File is in the process of being closed',
        821: 'Host forced a disconnect',
        822: 'FMI files not found; reinstall missing files',
        823: 'Cannot set file to single-user, guests are connected',
        824: 'File is damaged or not a FileMaker(tm) file',
        900: 'General spelling engine error',
        901: 'Main spelling dictionary not installed',
        902: 'Could not launch the Help system',
        903: 'Command cannot be used in a shared file',
        904: 'Command can only be used in a file hosted under '
             'FileMaker(tm) Server',
        905: 'No active field selected; command can only be used if there '
             'is an active field',
        920: 'Can\'t initialize the spelling engine',
        921: 'User dictionary cannot be loaded for editing',
        922: 'User dictionary cannot be found',
        923: 'User dictionary is read-only',
        951: 'An unexpected error occurred (returned only by '
             'web-published databases)',
        954: 'Unsupported XML grammar (returned only by '
             'web-published databases)',
        955: 'No database name (returned only by web-published databases)',
        956: 'Maximum number of database sessions exceeded (returned '
             'only by web-published databases)',
        957: 'Conflicting commands (returned only by web-published databases)',
        958: 'Parameter missing (returned only by web-published databases)',
        971: 'The user name is invalid',
        972: 'The password is invalid',
        973: 'The database is invalid',
        974: 'Permission Denied',
        975: 'The field has restricted access',
        976: 'Security is disabled',
        977: 'Invalid client IP address',
        978: 'The number of allowed guests has been exceeded',
        1200: 'Generic calculation error',
        1201: 'Too few parameters in the function',
        1202: 'Too many parameters in the function',
        1203: 'Unexpected end of calculation',
        1204: 'Number, text constant, field name or "(" expected',
        1205: 'Comment is not terminated with "*/"',
        1206: 'Text constant must end with a quotation mark',
        1207: 'Unbalanced parenthesis',
        1208: 'Operator missing, function not found or "(" not expected',
        1209: 'Name (such as field name or layout name) is missing',
        1210: 'Plug-in function has already been registered',
        1211: 'List usage is not allowed in this function',
        1212: 'An operator (for example, +, -, *) is expected here',
        1213: 'This variable has already been defined in the Let function',
        1214: 'AVERAGE, COUNT, EXTEND, GETREPETITION, MAX, MIN, NPV, '
              'STDEV, SUM and GETSUMMARY: expression found where a field '
              'alone is needed',
        1215: 'This parameter is an invalid Get function parameter',
        1216: 'Only Summary fields allowed as first argument in GETSUMMARY',
        1217: 'Break field is invalid',
        1218: 'Cannot evaluate the number',
        1219: 'A field cannot be used in its own formula',
        1220: 'Field type must be normal or calculated',
        1221: 'Data type must be number, date, time, or timestamp',
        1222: 'Calculation cannot be stored',
        1223: 'The function referred to does not exist',
        1400: 'ODBC driver initialization failed; make sure the ODBC '
              'drivers are properly installed',
        1401: 'Failed to allocate environment (ODBC)',
        1402: 'Failed to free environment (ODBC)',
        1403: 'Failed to disconnect (ODBC)',
        1404: 'Failed to allocate connection (ODBC)',
        1405: 'Failed to free connection (ODBC)',
        1406: 'Failed check for SQL API (ODBC)',
        1407: 'Failed to allocate statement (ODBC)',
        1408: 'Extended error (ODBC)',
        1413: 'Failed communication link (ODBC)',
        1414: 'SQL statement is too long',
        1450: 'Action requires PHP privilege extension (*)',
        1451: 'Action requires that current file be remote',
        1501: 'SMTP authentication failed',
        1502: 'Connection refused by SMTP server',
        1503: 'Error with SSL',
        1504: 'SMTP server requires the connection to be encrypted',
        1505: 'Specified authentication is not supported by SMTP server',
        1506: 'Email message(s) could not be sent successfully',
        1507: 'Unable to log in to the SMTP server',
        1550: 'Cannot load the plug-in, or the plug-in is not a valid plug-in',
        1551: 'Cannot install the plug-in; cannot delete an existing plug-in '
              'or write to the folder or disk',
        1626: 'Protocol is not supported',
        1627: 'Authentication failed',
        1628: 'There was an error with SSL',
        1629: 'Connection timed out; the timeout value is 60 seconds',
        1630: 'URL format is incorrect',
        1631: 'Connection failed',
        1632: 'Certificate cannot be authenticated by a supported '
              'certificate authority',
        1633: 'Certificate is valid but still causes an error '
              '(for example, the certificate has expired)',
    }

    def __init__(self, error=-1):
        """Initialize Exception from message of FileMaker error code."""
        if isinstance(error, int):
            self.code = error
            message = FMError.CODES.get(self.code, 'Unknown error code')
            error = f'FileMaker Error {self.code}: {message}'
        else:
            self.code = -1
        super().__init__(error)


def escape_unicode(ustr, quote=True):
    """Return ASCII string for use in XHTML from unicode string."""
    return escape(ustr.strip(), quote=quote).encode(
        'ascii', 'xmlcharrefreplace').replace(b"'", b'&#39;').decode('ascii')


if __name__ == '__main__':
    import doctest

    doctest.testmod()
