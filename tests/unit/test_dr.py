from __future__ import absolute_import

import pytest
import os
import sys
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import struct

prefix = '.'
for i in range(0, 3):
    if os.path.isdir(os.path.join(prefix, 'pycdlib')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pycdlib.dr

# XA
def test_xa_parse_initialized_twice():
    xa = pycdlib.dr.XARecord()
    xa.parse(b'\x00\x00\x00\x00\x00\x00\x58\x41\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        xa.parse(b'\x00\x00\x00\x00\x00\x00\x58\x41\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'This XARecord is already initialized')

def test_xa_parse_bad_reserved():
    xa = pycdlib.dr.XARecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        xa.parse(b'\x00\x00\x00\x00\x00\x00\x58\x41\x00\x00\x00\x00\x00\x01')
    assert(str(excinfo.value) == 'Unused fields should be 0')

def test_xa_new_initialized_twice():
    xa = pycdlib.dr.XARecord()
    xa.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        xa.new()
    assert(str(excinfo.value) == 'This XARecord is already initialized')

def test_xa_record_not_initialized():
    xa = pycdlib.dr.XARecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        xa.record()
    assert(str(excinfo.value) == 'This XARecord is not initialized')

# DR
def test_dr_parse_initialized_twice():
    dr = pycdlib.dr.DirectoryRecord()
    dr.parse(None, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*7 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00', None)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        dr.parse(None, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*7 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00', None)
    assert(str(excinfo.value) == 'Directory Record already initialized')

def test_dr_bad_record_length():
    dr = pycdlib.dr.DirectoryRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        dr.parse(None, b'\x00' * 256, None)
    assert(str(excinfo.value) == 'Directory record longer than 255 bytes!')

def test_dr_bad_extent_location():
    dr = pycdlib.dr.DirectoryRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        dr.parse(None, b'\x00\x00\x01\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*7 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00', None)
    assert(str(excinfo.value) == 'Little-endian (1) and big-endian (2) extent location disagree')

def test_dr_bad_seqnum():
    dr = pycdlib.dr.DirectoryRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        dr.parse(None, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*7 + b'\x00\x00\x00\x01\x00\x00\x02\x00\x00', None)
    assert(str(excinfo.value) == 'Little-endian and big-endian seqnum disagree')
