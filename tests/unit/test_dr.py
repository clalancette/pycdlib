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
