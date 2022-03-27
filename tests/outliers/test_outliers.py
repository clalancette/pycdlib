from __future__ import absolute_import

import os
import pathlib
import pytest
import sys
import lzma
import logging

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

import pycdlib


def try_list_files(name):
    listing = []
    iso = pycdlib.PyCdlib()
    path = pathlib.Path(F'tests/outliers/data/{name}.binx')
    with path.open('rb') as stream:
        data = stream.read()
    data = lzma.decompress(data)
    data = bytes(b ^ 0x65 for b in data)
    with BytesIO(data) as stream:
        iso.open_fp(stream)
    if iso.has_udf():
        facade = iso.get_udf_facade()
    elif iso.has_joliet():
        facade = iso.get_joliet_facade()
    elif iso.has_rock_ridge():
        facade = iso.get_rock_ridge_facade()
    else:
        facade = iso.get_iso9660_facade()
    for root, _, files in facade.walk('/'):
        root = root.rstrip('/')
        for name in files:
            name = name.lstrip('/')
            facade.get_record(F'{root}/{name}')
            name, _, _ = name.partition(';')
            listing.append(name)
    return listing


def test_UDF_tag_identifier_not_8(caplog):
    with caplog.at_level(logging.WARNING):
        files = try_list_files('ff42e1a03e7d70b48305d83edf6ed5fce0a858ef001acafab86e9e03c561f30c')
    assert 'CDVD.IRX' in files
    assert 'COLECO.ROM' in files
    assert 'SYSTEM.CNF' in files
    assert 'UDF File Set Terminator Tag identifier not 8' in caplog.text

def test_invalid_Joliet_ISO(caplog):
    with caplog.at_level(logging.WARNING):
        files = try_list_files('ea6cd95fbceed7e3048f79d1c596abc770ef8a4bc3661785570188aa65e01a36')
    assert files == ['LUBRNQUWR78KA.VBS']
    assert 'File structure version expected to be 1' in caplog.text
    assert 'Big-endian path table records use little-endian byte order.' in caplog.text
    assert 'Allowing duplicate dir entry with same identifier "."' in caplog.text
    assert 'Joliet big-endian path table records use little-endian byte order.' in caplog.text

def test_sample_with_no_path_table_records():
    files = try_list_files('e1567a6661b475460efe1b89a9ead760cc887b0951c74e6b70631bc08e8e4a5b')
    assert set(files) == {'auth_crt.pfx', 'init.config'}
