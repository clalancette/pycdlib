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


def test_UDF_tag_identifier_not8_01(caplog):
    with caplog.at_level(logging.WARNING):
        files = try_list_files('ff42e1a03e7d70b48305d83edf6ed5fce0a858ef001acafab86e9e03c561f30c')
    assert 'CDVD.IRX' in files
    assert 'COLECO.ROM' in files
    assert 'SYSTEM.CNF' in files
    assert 'UDF File Set Terminator Tag identifier not 8' in caplog.text

def test_UDF_tag_identifier_not8_02(caplog):
    with caplog.at_level(logging.WARNING):
        files = try_list_files('13a28a1c9dd619fb9ac9e6db7e7ab291d4944e3367b847be13807821c8d0cf3e')
    assert set(files) == {'HDLC_000.08', 'SYSTEM.CNF'}
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

def test_inconsistent_rock_ridge_versions():
    files = try_list_files('3547ce8751f05737ef3c8b7fda4929e0d74b710e033e2b8ae20d7873688930cc')
    assert set(files) == {
        'autorun',
        'autorun.inf',
        'grub-add.sh.txt',
        'logo.png',
        'opciones.sh.txt',
        'README',
        'salir.sh.txt',
    }

def test_rock_ridge_without_name():
    files = try_list_files('2d484db5b69f000267f0f176e32fd3adf1e4b6e99876d2f77c76eb5018813010')
    assert '.MacFlyPro.plist' in files
    assert 'Macflypro_Installer.pkg' in files

def test_sample_with_too_few_UDF_anchors_01():
    files = try_list_files('d17b4c19412a5ad927b6249a29a3b7901ce8815dcfa048531e67a4439298dcc5')
    assert files == ['6ddd602cc282b8a72-816779ddd662cc282b8a72-8166-9ceb-898064d602cc.vbs']

def test_sample_with_too_few_UDF_anchors_02():
    files = try_list_files('b229372a2b31f94799b84ae96c4d87327faabcc1cccd2cf3e4f6afb2aa2e7a23')
    assert files == ['2d70ff0773808c99ed0dde261d25b4f2142d367133184.vbs']

def test_le_be_mismatch_01():
    files = try_list_files('822c04f4af4d112035cccb9723492d0e1cc33d39c64a1fc8770359443343353b')
    assert 'ASSET.COM' in files
    assert 'AUTOEXEC.BAT' in files
    assert 'SERTAG.EXE' in files
    assert 'STAG_W1.EXE' in files
    assert 'Boot-1.44M.img' in files
    assert len(files) == 21

def test_le_be_mismatch_02():
    files = try_list_files('27fdfc58cadf156a2385fd72923511acc1b309c96ab0f7b3b0edc99edad1960a')
    assert 'autorun.inf' in files
    assert 'BOSCH.exe' in files

def test_le_be_mismatch_03():
    files = try_list_files('e81af9201d76081c695f616a118b0c7e16087d8a8bef5e44daa63e7396bd8c4f')
    assert files == ['gm.exe']

def test_Invalid_SUSP_SP_record_01():
    files = try_list_files('276e7a55df16522ee3e187815ff76fa3562b8a609632acbb9fea4ec385941694')
    assert 'ForestDumbForever!.info' in files
    assert 'ForestDumbForever!_D1.dms' in files
    assert 'ForestDumbForever!_D2.dms' in files
    assert 'StworkiNew.rawm' in files
    assert 'StworkiNew.mask' in files

def test_Invalid_SUSP_SP_record_01():
    files = try_list_files('00cd2850489cf197ac4ba99786d192dd0135fdbd6922130a0ad17ecf905de2d1')
    assert set(files) == {
        'vmadd-full-0.0.1-1.i386.rpm',
        'vmadd-heartbeat-0.0.1-1.i386.rpm',
        'vmadd-kernel-module-0.0.1-1.i386.rpm',
        'vmadd-scsi-0.0.1-1.i386.rpm',
        'vmadd-shutdown-0.0.1-1.i386.rpm',
        'vmadd-timesync-0.0.1-1.i386.rpm',
        'vmadd-x11-0.0.1-1.i386.rpm',
    }

def test_buffer_too_small_for_unpacking():
    files = try_list_files('6e3df3aa5f6dedd765a865ca7799982154a9c19f230d80a469d6cffd5e7cbf72')
    assert 'SKLoader.exe' in files
    assert 'autorun.inf' in files
    assert 'MacKMLinkFull.tgz' in files