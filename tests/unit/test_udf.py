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

import pycdlib.udf

# BEA
def test_bea_parse_initialized_twice():
    bea = pycdlib.udf.BEAVolumeStructure()
    bea.parse(b'\x00BEA01\x01' + b'\x00'*2041, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bea.parse(b'\x00BEA01\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'BEA Volume Structure already initialized')

def test_bea_parse_bad_structure():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bea.parse(b'\x01BEA01\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure type')

def test_bea_parse_bad_ident():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bea.parse(b'\x00CEA01\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid standard identifier')

def test_bea_parse_bad_version():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bea.parse(b'\x00BEA01\x02' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure version')

def test_bea_record_not_initialized():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bea.record()
    assert(str(excinfo.value) == 'BEA Volume Structure not initialized')

def test_bea_new_initialized_twice():
    bea = pycdlib.udf.BEAVolumeStructure()
    bea.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bea.new()
    assert(str(excinfo.value) == 'BEA Volume Structure already initialized')

def test_bea_extent_location_not_initialized():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bea.extent_location()
    assert(str(excinfo.value) == 'UDF BEA Volume Structure not initialized')

def test_bea_set_extent_location_not_initialized():
    bea = pycdlib.udf.BEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bea.set_extent_location(0)
    assert(str(excinfo.value) == 'This Volume Descriptor is not initialized')

# NSR
def test_nsr_parse_initialized_twice():
    nsr = pycdlib.udf.NSRVolumeStructure()
    nsr.parse(b'\x00NSR02\x01' + b'\x00'*2041, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.parse(b'\x00NSR02\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'UDF NSR Volume Structure already initialized')

def test_nsr_parse_bad_structure():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        nsr.parse(b'\x01NSR02\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure type')

def test_nsr_parse_bad_ident():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        nsr.parse(b'\x00NSR04\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid standard identifier')

def test_nsr_parse_bad_version():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        nsr.parse(b'\x00NSR02\x02' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure version')

def test_nsr_record_not_initialized():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.record()
    assert(str(excinfo.value) == 'UDF NSR Volume Structure not initialized')

def test_nsr_new_initialized_twice():
    nsr = pycdlib.udf.NSRVolumeStructure()
    nsr.new(2)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.new(2)
    assert(str(excinfo.value) == 'UDF NSR Volume Structure already initialized')

def test_nsr_new_version_three():
    nsr = pycdlib.udf.NSRVolumeStructure()
    nsr.new(3)
    assert(nsr.standard_ident == b'NSR03')

def test_nsr_new_bad_version():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.new(4)
    assert(str(excinfo.value) == 'Invalid NSR version requested')

def test_nsr_extent_location_not_initialized():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.extent_location()
    assert(str(excinfo.value) == 'UDF NSR Volume Structure not initialized')

def test_nsr_set_extent_location_not_initialized():
    nsr = pycdlib.udf.NSRVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nsr.set_extent_location(0)
    assert(str(excinfo.value) == 'This Volume Descriptor is not initialized')

# TEA
def test_tea_parse_initialized_twice():
    tea = pycdlib.udf.TEAVolumeStructure()
    tea.parse(b'\x00TEA01\x01' + b'\x00'*2041, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tea.parse(b'\x00TEA01\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'TEA Volume Structure already initialized')

def test_tea_parse_bad_type():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tea.parse(b'\x01TEA01\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure type')

def test_tea_parse_bad_ident():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tea.parse(b'\x00TEA02\x01' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid standard identifier')

def test_tea_parse_bad_version():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tea.parse(b'\x00TEA01\x02' + b'\x00'*2041, 0)
    assert(str(excinfo.value) == 'Invalid structure version')

def test_tea_record_not_initialized():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tea.record()
    assert(str(excinfo.value) == 'UDF TEA Volume Structure not initialized')

def test_tea_new_initialized_twice():
    tea = pycdlib.udf.TEAVolumeStructure()
    tea.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tea.new()
    assert(str(excinfo.value) == 'UDF TEA Volume Structure already initialized')

def test_tea_extent_location_not_initialized():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tea.extent_location()
    assert(str(excinfo.value) == 'UDF TEA Volume Structure not initialized')

def test_tea_set_extent_location_not_initialized():
    tea = pycdlib.udf.TEAVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tea.set_extent_location(0)
    assert(str(excinfo.value) == 'This Volume Descriptor is not initialized')

# Boot Descriptor
def test_boot_descriptor_parse():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(boot.boot_extent_loc == 0)
    assert(boot.boot_extent_len == 0)
    assert(boot.load_address == 0)
    assert(boot.start_address == 0)
    assert(boot.flags == 0)

def test_boot_descriptor_parse_initialized_twice():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'UDF Boot Descriptor already initialized')

def test_boot_descriptor_parse_bad_type():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x01BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid structure type')

def test_boot_descriptor_parse_bad_ident():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x00BOOT1\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid standard identifier')

def test_boot_descriptor_parse_bad_version():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x00BOOT2\x02\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid structure version')

def test_boot_descriptor_parse_bad_reserved():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x00BOOT2\x01\x01' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid reserved1')

def test_boot_descriptor_parse_bad_flags():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x02\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid flags (must be 0 or 1)')

def test_boot_descriptor_parse_bad_reserved2():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x01'*32 + b'\x00'*1906, 0)
    assert(str(excinfo.value) == 'Invalid reserved2')

def test_boot_descriptor_new():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.new()
    assert(boot.flags == 0)
    assert(boot.boot_extent_loc == 0)
    assert(boot.boot_extent_len == 0)
    assert(boot.load_address == 0)
    assert(boot.start_address == 0)
    assert(boot.flags == 0)
    assert(boot._initialized)

def test_boot_descriptor_new_initialized_twice():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        boot.new()
    assert(str(excinfo.value) == 'UDF Boot Descriptor already initialized')

def test_boot_descriptor_record_not_initialized():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        boot.record()
    assert(str(excinfo.value) == 'UDF Boot Descriptor not initialized')

def test_boot_descriptor_record():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.new()
    rec = boot.record()
    assert(rec[0:8] == b'\x00BOOT2\x01\x00')

def test_boot_descriptor_extent_location_not_initialized():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        boot.extent_location()
    assert(str(excinfo.value) == 'UDF Boot Descriptor not initialized')

def test_boot_descriptor_extent_location():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.parse(b'\x00BOOT2\x01\x00' + b'\x00'*32 + b'\x00'*32 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x00' + b'\x00'*32 + b'\x00'*1906, 0)
    assert(boot.extent_location() == 0)

def test_boot_descriptor_set_extent_location_not_initialized():
    boot = pycdlib.udf.UDFBootDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        boot.set_extent_location(0)
    assert(str(excinfo.value) == 'This UDF Boot Descriptor is not initialized')

def test_boot_descriptor_set_extent_location():
    boot = pycdlib.udf.UDFBootDescriptor()
    boot.new()
    boot.set_extent_location(1)
    assert(boot.extent_location() == 1)

# UDFTag
def test_tag_parse_initialized_twice():
    tag = pycdlib.udf.UDFTag()
    tag.parse(b'\x00\x00\x02\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tag.parse(b'\x00\x00\x02\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0)
    assert(str(excinfo.value) == 'UDF Tag already initialized')

def test_tag_parse_bad_csum():
    tag = pycdlib.udf.UDFTag()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tag.parse(b'\x00\x00\x02\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0)
    assert(str(excinfo.value) == 'Tag checksum does not match!')

def test_tag_parse_not_enough_crc_data():
    tag = pycdlib.udf.UDFTag()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tag.parse(b'\x00\x00\x02\x00\x03\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00', 0)
    assert(str(excinfo.value) == 'Not enough bytes to compute CRC')

def test_tag_parse_bad_crc():
    tag = pycdlib.udf.UDFTag()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tag.parse(b'\x00\x00\x02\x00\x03\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\xee', 0)
    assert(str(excinfo.value) == 'Tag CRC does not match!')

def test_tag_parse():
    tag = pycdlib.udf.UDFTag()
    tag.parse(b'\x00\x00\x02\x00\x03\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00', 0)
    assert(tag.tag_ident == 0)
    assert(tag.desc_version == 2)
    assert(tag.tag_serial_number == 0)
    assert(tag.desc_crc_length == 1)
    assert(tag.tag_location == 0)
    assert(tag._initialized)

def test_tag_record_not_initialized():
    tag = pycdlib.udf.UDFTag()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tag.record(b'\x00')
    assert(str(excinfo.value) == 'UDF Descriptor Tag not initialized')

def test_tag_new_initialized_twice():
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tag.new(0, 0)
    assert(str(excinfo.value) == 'UDF Tag already initialized')

def test_tag_eq():
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)

    tag2 = pycdlib.udf.UDFTag()
    tag2.new(0, 0)

    assert(tag == tag2)

# Anchor
def test_anchor_parse_initialized_twice():
    anchor = pycdlib.udf.UDFAnchorVolumeStructure()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    anchor.parse(b'\x00'*16 + b'\x00'*8 + b'\x00'*8 + b'\x00'*480, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        anchor.parse(b'\x00'*16 + b'\x00'*8 + b'\x00'*8 + b'\x00'*480, 0, tag)
    assert(str(excinfo.value) == 'Anchor Volume Structure already initialized')

def test_anchor_record_not_initialized():
    anchor = pycdlib.udf.UDFAnchorVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        anchor.record()
    assert(str(excinfo.value) == 'UDF Anchor Volume Descriptor not initialized')

def test_anchor_extent_location_not_initialized():
    anchor = pycdlib.udf.UDFAnchorVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        anchor.extent_location()
    assert(str(excinfo.value) == 'UDF Anchor Volume Structure not initialized')

def test_anchor_new_initialized_twice():
    anchor = pycdlib.udf.UDFAnchorVolumeStructure()
    anchor.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        anchor.new()
    assert(str(excinfo.value) == 'UDF Anchor Volume Structure already initialized')

def test_anchor_set_extent_location_not_initialized():
    anchor = pycdlib.udf.UDFAnchorVolumeStructure()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        anchor.set_extent_location(0, 0, 0)
    assert(str(excinfo.value) == 'UDF Anchor Volume Structure not initialized')
