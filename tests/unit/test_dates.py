from __future__ import absolute_import

import pytest
import os
import sys
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import struct
import time

prefix = '.'
for i in range(0, 3):
    if os.path.isdir(os.path.join(prefix, 'pycdlib')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pycdlib.dates
import pycdlib.pycdlibexception

def test_string_to_timestruct_invalid_input_type():
    if sys.version_info >= (3, 0):
        with pytest.raises(AttributeError) as exc_info:
            ts = pycdlib.dates.string_to_timestruct('')

def test_string_to_timestruct_blank_bytes():
    ts = pycdlib.dates.string_to_timestruct(b'')
    assert(ts.tm_year == 0)
    assert(ts.tm_mon == 0)
    assert(ts.tm_mday == 0)
    assert(ts.tm_hour == 0)
    assert(ts.tm_min == 0)
    assert(ts.tm_sec == 0)
    assert(ts.tm_wday == 0)
    assert(ts.tm_yday == 0)
    assert(ts.tm_isdst == 0)

def test_string_to_timestruct():
    ts = pycdlib.dates.string_to_timestruct(b'20180718212300')
    assert(ts.tm_year == 2018)
    assert(ts.tm_mon == 7)
    assert(ts.tm_mday == 18)
    assert(ts.tm_hour == 21)
    assert(ts.tm_min == 23)
    assert(ts.tm_sec == 0)
    assert(ts.tm_wday == 2)
    assert(ts.tm_yday == 199)
    assert(ts.tm_isdst == -1)

def test_dirrecorddate_record_not_initialized():
    drdate = pycdlib.dates.DirectoryRecordDate()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.record()
    assert(str(excinfo.value) == 'Directory Record Date not initialized')

def test_dirrecorddate_new_after_new():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.new()
    assert(str(excinfo.value) == 'Directory Record Date already initialized')

def test_dirrecorddate_parse_after_new():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.parse(b'')
    assert(str(excinfo.value) == 'Directory Record Date already initialized')

def test_dirrecorddate_parse_after_parse():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.parse(b'\x76\x07\x12\x15\x21\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.parse(b'\x76\x07\x12\x15\x21\x00\x00')
    assert(str(excinfo.value) == 'Directory Record Date already initialized')

def test_dirrecorddate_new_after_parse():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.parse(b'\x76\x07\x12\x15\x21\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.new()
    assert(str(excinfo.value) == 'Directory Record Date already initialized')

def test_dirrecorddate_record_after_new():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.new()
    assert(len(drdate.record()) == 7)

def test_dirrecorddate_compare_equal():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.new()

    drdate2 = drdate

    assert(not(drdate2 != drdate))

def test_dirrecorddate_compare_not_equal():
    drdate = pycdlib.dates.DirectoryRecordDate()
    drdate.new()

    time.sleep(1)

    drdate2 = pycdlib.dates.DirectoryRecordDate()
    drdate2.new()

    assert(drdate2 != drdate)

def test_volumedescdate_record_not_initialized():
    voldate = pycdlib.dates.VolumeDescriptorDate()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        voldate.record()
    assert(str(excinfo.value) == 'This Volume Descriptor Date is not initialized')

def test_volumedescdate_parse_invalid_string():
    voldate = pycdlib.dates.VolumeDescriptorDate()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        voldate.parse(b'')
    assert(str(excinfo.value) == 'Invalid ISO9660 date string')

def test_volumedescdate_new_after_new():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.new()
    assert(str(excinfo.value) == 'This Volume Descriptor Date object is already initialized')

def test_volumedescdate_parse_after_new():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.parse(b'')
    assert(str(excinfo.value) == 'This Volume Descriptor Date object is already initialized')

def test_volumedescdate_parse_after_parse():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'This Volume Descriptor Date object is already initialized')

def test_volumedescdate_new_after_parse():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        drdate.new()
    assert(str(excinfo.value) == 'This Volume Descriptor Date object is already initialized')

def test_volumedescdate_parse_zero():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(drdate.year == 0)
    assert(drdate.month == 0)
    assert(drdate.dayofmonth == 0)
    assert(drdate.hour == 0)
    assert(drdate.minute == 0)
    assert(drdate.second == 0)
    assert(drdate.hundredthsofsecond == 0)
    assert(drdate.gmtoffset == 0)
    assert(drdate.date_str == b'0000000000000000' + b'\x00')

def test_volumedescdate_parse_nonzero():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'2019010721250000\x00')
    assert(drdate.year == 2019)
    assert(drdate.month == 1)
    assert(drdate.dayofmonth == 7)
    assert(drdate.hour == 21)
    assert(drdate.minute == 25)
    assert(drdate.second == 0)
    assert(drdate.hundredthsofsecond == 0)
    assert(drdate.gmtoffset == 0)

def test_volumedescdate_parse_hundredths():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'2019010721250005\x00')
    assert(drdate.year == 2019)
    assert(drdate.month == 1)
    assert(drdate.dayofmonth == 7)
    assert(drdate.hour == 21)
    assert(drdate.minute == 25)
    assert(drdate.second == 0)
    assert(drdate.hundredthsofsecond == 5)
    assert(drdate.gmtoffset == 0)

def test_volumedescdate_parse_null_hundredths():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'20190107212500\x00\x00\x00')
    assert(drdate.year == 2019)
    assert(drdate.month == 1)
    assert(drdate.dayofmonth == 7)
    assert(drdate.hour == 21)
    assert(drdate.minute == 25)
    assert(drdate.second == 0)
    assert(drdate.hundredthsofsecond == 0)
    assert(drdate.gmtoffset == 0)

def test_volumedescdate_record_after_parse():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.parse(b'2019010721250000\x00')
    rec = drdate.record()
    assert(rec == b'2019010721250000\x00')

def save_and_set_tz(newtz):
    if 'TZ' in os.environ:
        oldtz = os.environ['TZ']
    else:
        oldtz = None

    os.environ['TZ'] = newtz
    time.tzset()

    return oldtz

def restore_tz(oldtz):
    if oldtz is not None:
        os.environ['TZ'] = oldtz
    else:
        del os.environ['TZ']
    time.tzset()

def test_volumedescdate_new_nonzero():
    oldtz = save_and_set_tz('US/Eastern')

    test_seconds_since_epoch = 1546914300.0
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.new(test_seconds_since_epoch)
    assert(drdate.year == 2019)
    assert(drdate.month == 1)
    assert(drdate.dayofmonth == 7)
    assert(drdate.hour == 21)
    assert(drdate.minute == 25)
    assert(drdate.second == 0)
    assert(drdate.hundredthsofsecond == 0)
    restore_tz(oldtz)

def test_volumedescdate_test_equal():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.new(1546914300.0)

    drdate2 = pycdlib.dates.VolumeDescriptorDate()
    drdate2.new(1546914300.0)

    assert(not(drdate != drdate2))

def test_volumedescdate_test_not_equal():
    drdate = pycdlib.dates.VolumeDescriptorDate()
    drdate.new(1546914300.0)

    drdate2 = pycdlib.dates.VolumeDescriptorDate()
    drdate2.new(1546914200.0)

    assert(drdate != drdate2)
