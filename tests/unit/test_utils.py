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

import pycdlib.utils
import pycdlib.pycdlibexception

def test_swab_32bit():
    assert(pycdlib.utils.swab_32bit(0x89) == 0x89000000)

def test_swab_16bit():
    assert(pycdlib.utils.swab_16bit(0x55aa) == 0xaa55)

def test_ceiling_div():
    assert(pycdlib.utils.ceiling_div(0, 2048) == 0)

def test_ceiling_div2():
    assert(pycdlib.utils.ceiling_div(2048, 2048) == 1)

def test_ceiling_div3():
    assert(pycdlib.utils.ceiling_div(2049, 2048) == 2)

def test_ceiling_div_nan():
    with pytest.raises(ZeroDivisionError) as exc_info:
        pycdlib.utils.ceiling_div(2048, 0)

def test_copy_data_no_sendfile():
    infp = BytesIO()
    outfp = BytesIO()

    infp.write(b'\x00'*1)
    infp.seek(0)

    pycdlib.utils.copy_data(1, 8192, infp, outfp)

    assert(outfp.getvalue() == b'\x00')

def test_copy_data_no_sendfile_short():
    infp = BytesIO()
    outfp = BytesIO()

    infp.write(b'\x00'*10)
    infp.seek(0)

    pycdlib.utils.copy_data(100, 8192, infp, outfp)

    assert(outfp.getvalue() == b'\x00'*10)

def test_copy_data_sendfile(tmpdir):
    testin = tmpdir.join('in')
    testout = tmpdir.join('out')

    with open(str(testin), 'wb+') as infp:
        infp.write(b'\x00'*10)
        infp.seek(0)

        with open(str(testout), 'wb') as outfp:
            pycdlib.utils.copy_data(10, 8192, infp, outfp)

    with open(str(testout), 'rb') as infp:
        assert(infp.read() == b'\x00'*10)

def test_encode_space_pad_too_short():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as exc_info:
        pycdlib.utils.encode_space_pad(b'hello', 4, 'ascii')
    assert(str(exc_info.value) == 'Input string too long!')

def test_encode_space_pad_no_pad():
    assert(pycdlib.utils.encode_space_pad(b'hello', 5, 'ascii') == b'hello')

def test_encode_space_pad_one():
    assert(pycdlib.utils.encode_space_pad(b'hello', 6, 'ascii') == b'hello ')

def test_encode_space_pad_extra():
    assert(pycdlib.utils.encode_space_pad(b'hello', 11, 'utf-16_be') == b'\x00h\x00e\x00l\x00l\x00o\x00')

def test_normpath_double_slashes_beginning():
    assert(pycdlib.utils.normpath('//') == b'/')

def test_normpath_double_slashes_middle():
    assert(pycdlib.utils.normpath('/foo//bar') == b'/foo/bar')

def test_normpath_with_dotdot():
    assert(pycdlib.utils.normpath('/foo/bar/../baz') == b'/foo/baz')

def test_normpath_with_dotdot_after_slash():
    assert(pycdlib.utils.normpath('/../foo') == b'/foo')

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

def test_gmtoffset_from_tm():
    oldtz = save_and_set_tz('US/Eastern')
    now = 1546914300.0
    assert(pycdlib.utils.gmtoffset_from_tm(now, time.localtime(now)) == -20)
    restore_tz(oldtz)

def test_gmtoffset_from_tm_day_rollover():
    # Setup the timezone to Tokyo
    oldtz = save_and_set_tz('Asia/Tokyo')

    # This tm is carefully chosen so that the day of the week is the next day
    # in the Tokyo region.
    now = 1550417871
    local = time.localtime(now)
    assert(pycdlib.utils.gmtoffset_from_tm(now, local) == 36)

    restore_tz(oldtz)

def test_zero_pad():
    fp = BytesIO()
    pycdlib.utils.zero_pad(fp, 5, 10)
    assert(fp.getvalue() == b'\x00'*5)

def test_zero_pad_no_pad():
    fp = BytesIO()
    pycdlib.utils.zero_pad(fp, 5, 5)
    assert(fp.getvalue() == b'')

def test_zero_pad_negative_pad():
    fp = BytesIO()
    pycdlib.utils.zero_pad(fp, 5, 4)
    assert(fp.getvalue() == b'\x00'*3)

def test_starts_with_slash():
    assert(pycdlib.utils.starts_with_slash(b'/'))

def test_starts_with_slash_no_slash():
    assert(not pycdlib.utils.starts_with_slash(b'foo/bar'))

def test_starts_with_slash_double_slash():
    assert(pycdlib.utils.starts_with_slash(b'//foo/bar'))

def test_split_path():
    assert(pycdlib.utils.split_path(b'/foo/bar') == [b'foo', b'bar'])

def test_split_path_no_leading_slash():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as exc_info:
        pycdlib.utils.split_path(b'foo/bar')
    assert(str(exc_info.value) == 'Must be a path starting with /')

def test_split_path_single():
    assert(pycdlib.utils.split_path(b'/foo') == [b'foo'])

def test_split_path_slash_only():
    assert(pycdlib.utils.split_path(b'/') == [b''])

def test_split_path_trailing_slash():
    assert(pycdlib.utils.split_path(b'/foo/') == [b'foo', b''])

def test_file_object_supports_binary_bytesio():
    fp = BytesIO()
    assert(pycdlib.utils.file_object_supports_binary(fp))

def test_file_object_supports_binary_real_file(tmpdir):
    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        assert(pycdlib.utils.file_object_supports_binary(outfp))

def test_file_object_does_not_support_binary_real_file(tmpdir):
    testout = tmpdir.join('foo')
    with open(str(testout), 'w') as outfp:
        assert(not pycdlib.utils.file_object_supports_binary(outfp))
