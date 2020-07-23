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

# Volume Descriptor Pointer
def test_vdp_parse_initialized_twice():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    vdp.parse(b'\x00'*16 + b'\x00\x00\x00x\00' + b'\x00'*8 + b'\x00'*484, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        vdp.parse(b'\x00'*16 + b'\x00\x00\x00x\00' + b'\x00'*8 + b'\x00'*484, 0, b'\x00'*16)
    assert(str(excinfo.value) == 'UDF Volume Descriptor Pointer already initialized')

def test_vdp_parse():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    vdp.parse(b'\x00'*16 + b'\x00\x00\x00x\00' + b'\x00'*8 + b'\x00'*484, 0, tag)
    assert(vdp.orig_extent_loc == 0)
    assert(vdp.initialized)

def test_vdp_record_not_initialized():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        vdp.record()
    assert(str(excinfo.value) == 'UDF Volume Descriptor Pointer not initialized')

def test_vdp_record():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    vdp.parse(b'\x00'*16 + b'\x00\x00\x00x\00' + b'\x00'*8 + b'\x00'*484, 0, tag)
    assert(vdp.record() == (b'\x00\x00\x02\x00\x22\x00\x00\x00\x9c\x93\xf0\x01\x00\x00\x00\x00\x00\x00\x00\x78' + b'\x00'*492))

def test_vdp_extent_location_not_initialized():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        vdp.extent_location()
    assert(str(excinfo.value) == 'UDF Volume Descriptor Pointer not initialized')

def test_vdp_extent_location_parse():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    vdp.parse(b'\x00'*16 + b'\x00\x00\x00x\00' + b'\x00'*8 + b'\x00'*484, 0, tag)
    assert(vdp.extent_location() == 0)

def test_vdp_extent_location_new():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    vdp.new()
    assert(vdp.extent_location() == 0)

def test_vdp_new_initialized_twice():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    vdp.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        vdp.new()
    assert(str(excinfo.value) == 'UDF Volume Descriptor Pointer already initialized')

def test_vdp_new():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    vdp.new()
    assert(vdp.vol_seqnum == 0)
    assert(vdp.initialized)

def test_vdp_set_extent_location_not_initialized():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        vdp.set_extent_location(1)
    assert(str(excinfo.value) == 'UDF Volume Descriptor Pointer not initialized')

def test_vdp_set_extent_location():
    vdp = pycdlib.udf.UDFVolumeDescriptorPointer()
    vdp.new()
    vdp.set_extent_location(1)
    assert(vdp.new_extent_loc == 1)

# Timestamp
def test_timestamp_parse_initialized_twice():
    ts = pycdlib.udf.UDFTimestamp()
    ts.parse(b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Timestamp already initialized')

def test_timestamp_parse_bad_tz():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x06\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF timezone')

def test_timestamp_parse_bad_year():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x00\x00\x01\x01\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF year')

def test_timestamp_parse_bad_month():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF month')

def test_timestamp_parse_bad_day():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF day')

def test_timestamp_parse_bad_hour():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x01\x01\x20\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF hour')

def test_timestamp_parse_bad_minute():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x01\x01\x00\x40\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF minute')

def test_timestamp_parse_bad_second():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ts.parse(b'\x00\x00\x01\x00\x01\x01\x00\x00\x40\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid UDF second')

def test_timestamp_record_not_initialized():
    ts = pycdlib.udf.UDFTimestamp()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ts.record()
    assert(str(excinfo.value) == 'UDF Timestamp not initialized')

def test_timestamp_new_initialized_twice():
    ts = pycdlib.udf.UDFTimestamp()
    ts.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ts.new()
    assert(str(excinfo.value) == 'UDF Timestamp already initialized')

def test_timestamp_equal():
    ts = pycdlib.udf.UDFTimestamp()
    ts.new()

    ts2 = pycdlib.udf.UDFTimestamp()
    ts2.new()

    assert(ts == ts2)

# EntityID
def test_entityid_parse_initialized_twice():
    entity = pycdlib.udf.UDFEntityID()
    entity.parse(b'\x00'*32)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entity.parse(b'\x00'*32)
    assert(str(excinfo.value) == 'UDF Entity ID already initialized')

def test_entityid_parse_bad_flags():
    entity = pycdlib.udf.UDFEntityID()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        entity.parse(b'\x04' + b'\x00'*31)
    assert(str(excinfo.value) == 'UDF Entity ID flags must be between 0 and 3')

def test_entityid_record_not_initialized():
    entity = pycdlib.udf.UDFEntityID()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entity.record()
    assert(str(excinfo.value) == 'UDF Entity ID not initialized')

def test_entityid_new_initialized_twice():
    entity = pycdlib.udf.UDFEntityID()
    entity.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entity.new(0)
    assert(str(excinfo.value) == 'UDF Entity ID already initialized')

def test_entityid_new_bad_flags():
    entity = pycdlib.udf.UDFEntityID()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        entity.new(4)
    assert(str(excinfo.value) == 'UDF Entity ID flags must be between 0 and 3')

def test_entityid_new_bad_identifier():
    entity = pycdlib.udf.UDFEntityID()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        entity.new(0, b'\x00'*25)
    assert(str(excinfo.value) == 'UDF Entity ID identifier must be less than 23 characters')

def test_entityid_new_bad_suffix():
    entity = pycdlib.udf.UDFEntityID()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        entity.new(0, b'', b'\x00'*10)
    assert(str(excinfo.value) == 'UDF Entity ID suffix must be less than 8 characters')

def test_entityid_equals():
    entity = pycdlib.udf.UDFEntityID()
    entity.new(0)

    entity2 = pycdlib.udf.UDFEntityID()
    entity2.new(0)

    assert(entity == entity2)

# Charspec
def test_charspec_parse_initialized_twice():
    charspec = pycdlib.udf.UDFCharspec()
    charspec.parse(b'\x00'*64)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        charspec.parse(b'\x00'*64)
    assert(str(excinfo.value) == 'UDF Charspec already initialized')

def test_charspec_parse_bad_set_type():
    charspec = pycdlib.udf.UDFCharspec()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        charspec.parse(b'\x09' + b'\x00'*63)
    assert(str(excinfo.value) == 'Invalid charset parsed; only 0-8 supported')

def test_charspec_new_initialized_twice():
    charspec = pycdlib.udf.UDFCharspec()
    charspec.new(0, b'')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        charspec.new(0, b'')
    assert(str(excinfo.value) == 'UDF Charspec already initialized')

def test_charspec_new_bad_set_type():
    charspec = pycdlib.udf.UDFCharspec()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        charspec.new(9, b'')
    assert(str(excinfo.value) == 'Invalid charset specified; only 0-8 supported')

def test_charspec_new_bad_set_information():
    charspec = pycdlib.udf.UDFCharspec()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        charspec.new(0, b'\x00'*64)
    assert(str(excinfo.value) == 'Invalid charset information; exceeds maximum size of 63')

def test_charspec_record_not_initialized():
    charspec = pycdlib.udf.UDFCharspec()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        charspec.record()
    assert(str(excinfo.value) == 'UDF Charspec not initialized')

def test_charspec_equal():
    charspec = pycdlib.udf.UDFCharspec()
    charspec.new(0, b'\x00'*63)

    charspec2 = pycdlib.udf.UDFCharspec()
    charspec2.new(0, b'\x00'*63)

    assert(charspec == charspec2)

# ExtentAD
def test_extentad_parse_initialized_twice():
    extentad = pycdlib.udf.UDFExtentAD()
    extentad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        extentad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Extent descriptor already initialized')

def test_extentad_parse_bad_length():
    extentad = pycdlib.udf.UDFExtentAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        extentad.parse(b'\x00\x00\x00\xff\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Extent descriptor length must be less than 0x3fffffff')

def test_extentad_record_not_initialized():
    extentad = pycdlib.udf.UDFExtentAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        extentad.record()
    assert(str(excinfo.value) == 'UDF Extent AD not initialized')

def test_extentad_new_initialized_twice():
    extentad = pycdlib.udf.UDFExtentAD()
    extentad.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        extentad.new(0, 0)
    assert(str(excinfo.value) == 'UDF Extent AD already initialized')

def test_extentad_new_bad_length():
    extentad = pycdlib.udf.UDFExtentAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        extentad.new(0xff000000, 0)
    assert(str(excinfo.value) == 'UDF Extent AD length must be less than 0x3fffffff')

def test_extentad_equals():
    extentad = pycdlib.udf.UDFExtentAD()
    extentad.new(0, 0)

    extentad2 = pycdlib.udf.UDFExtentAD()
    extentad2.new(0, 0)

    assert(extentad == extentad2)

# PVD
def test_pvd_parse_initialized_twice():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor already initialized')

def test_pvd_parse_bad_volseqnum():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Only DVD Read-Only disks are supported')

def test_pvd_parse_bad_maxvolseqnum():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Only DVD Read-Only disks are supported')

def test_pvd_parse_bad_interchangelevel():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Unsupported interchange level (only 2 and 3 supported)')

def test_pvd_parse_bad_charsetlist():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Only DVD Read-Only disks are supported')

def test_pvd_parse_bad_maxcharsetlist():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Only DVD Read-Only disks are supported')

def test_pvd_parse_bad_flags():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x02\x00' + b'\x00'*22, 0, tag)
    assert(str(excinfo.value) == 'Invalid UDF flags')

def test_pvd_parse_bad_reserved():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pvd.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x01\x00\x01\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00' + b'\x00'*128 + b'\x00'*64 + b'\x00'*64 + b'\x00'*8 + b'\x00'*8 + b'\x00'*32 + b'\x00\x00\x01\x00\x01\x01\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*64 + b'\x00\x00\x00\x00\x00\x00' + b'\x01' + b'\x00'*21, 0, tag)
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor reserved data not 0')

def test_pvd_record_not_initialized():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pvd.record()
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor not initialized')

def test_pvd_extent_location_not_initialized():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pvd.extent_location()
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor not initialized')

def test_pvd_new_initialized_twice():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    pvd.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pvd.new()
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor already initialized')

def test_pvd_set_extent_location_not_initialized():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pvd.set_extent_location(0)
    assert(str(excinfo.value) == 'UDF Primary Volume Descriptor not initialized')

def test_pvd_equals():
    pvd = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    pvd.new()

    pvd2 = pycdlib.udf.UDFPrimaryVolumeDescriptor()
    pvd2.new()
    pvd2.vol_set_ident = pvd.vol_set_ident
    pvd2.recording_date = pvd.recording_date

    assert(pvd == pvd2)

# Implementation Use Volume Descriptor Implementation Use
def test_impl_use_impl_use_parse_initialized_twice():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptorImplementationUse()
    impl.parse(b'\x00'*64 + b'\x00'*128 + b'\x00'*36 + b'\x00'*36 + b'\x00'*36 + b'\x00'*32 + b'\x00'*128)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.parse(b'\x00'*64 + b'\x00'*128 + b'\x00'*36 + b'\x00'*36 + b'\x00'*36 + b'\x00'*32 + b'\x00'*128)
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor Implementation Use field already initialized')

def test_impl_use_impl_use_record_not_initialized():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptorImplementationUse()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.record()
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor Implementation Use field not initialized')

def test_impl_use_impl_use_new_initialized_twice():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptorImplementationUse()
    impl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.new()
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor Implementation Use field already initialized')

def test_impl_use_impl_use_new_initialized_twice():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptorImplementationUse()
    impl.new()

    impl2 = pycdlib.udf.UDFImplementationUseVolumeDescriptorImplementationUse()
    impl2.new()

    assert(impl == impl2)

# Implementation Use
def test_impl_use_parse_initialized_twice():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    impl.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00*UDF LV Info' + b'\x00'*19 + b'\x00'*460, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00*UDF LV Info' + b'\x00'*19 + b'\x00'*460, 0, tag)
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor already initialized')

def test_impl_use_parse_bad_ident():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        impl.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00*MDF LV Info' + b'\x00'*19 + b'\x00'*460, 0, tag)
    assert(str(excinfo.value) == "Implementation Use Identifier not '*UDF LV Info'")

def test_impl_use_record_not_initialized():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.record()
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor not initialized')

def test_impl_use_extent_location_not_initialized():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.extent_location()
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor not initialized')

def test_impl_use_new_initialized_twice():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    impl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.new()
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor already initialized')

def test_impl_use_set_extent_location_not_initialized():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        impl.set_extent_location(0)
    assert(str(excinfo.value) == 'UDF Implementation Use Volume Descriptor not initialized')

def test_impl_use_equals():
    impl = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    impl.new()

    impl2 = pycdlib.udf.UDFImplementationUseVolumeDescriptor()
    impl2.new()

    assert(impl == impl2)

# Partition Header Descriptor
def test_part_header_parse_initialized_twice():
    header = pycdlib.udf.UDFPartitionHeaderDescriptor()
    header.parse(b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*88)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        header.parse(b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*8 + b'\x00'*88)
    assert(str(excinfo.value) == 'UDF Partition Header Descriptor already initialized')

def test_part_header_record_not_initialized():
    header = pycdlib.udf.UDFPartitionHeaderDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        header.record()
    assert(str(excinfo.value) == 'UDF Partition Header Descriptor not initialized')

def test_part_header_new_initialized_twice():
    header = pycdlib.udf.UDFPartitionHeaderDescriptor()
    header.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        header.new()
    assert(str(excinfo.value) == 'UDF Partition Header Descriptor already initialized')

def test_part_header_equals():
    header = pycdlib.udf.UDFPartitionHeaderDescriptor()
    header.new()

    header2 = pycdlib.udf.UDFPartitionHeaderDescriptor()
    header2.new()

    assert(header == header2)

# Partition Volume
def test_part_parse_initialized_twice():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    part.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00+NSR02' + b'\x00'*25 + b'\x00'*128 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*156, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00+NSR02' + b'\x00'*25 + b'\x00'*128 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*156, 0, tag)
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor already initialized')

def test_part_parse_bad_flags():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        part.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x02\x00\x00\x00' + b'\x00+NSR02' + b'\x00'*25 + b'\x00'*128 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*156, 0, tag)
    assert(str(excinfo.value) == 'Invalid partition flags')

def test_part_parse_bad_entity():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        part.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00+NSR04' + b'\x00'*25 + b'\x00'*128 + b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*156, 0, tag)
    assert(str(excinfo.value) == "Partition Contents Identifier not '+FDC01', '+CD001', '+CDW02', '+NSR02', or '+NSR03'")

def test_part_parse_bad_access_type():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        part.parse(b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00+NSR02' + b'\x00'*25 + b'\x00'*128 + b'\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*156, 0, tag)
    assert(str(excinfo.value) == 'Invalid UDF partition access type')

def test_part_record_not_initialized():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.record()
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor not initialized')

def test_part_extent_location_not_initialized():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.extent_location()
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor not initialized')

def test_part_new_initialized_twice():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    part.new(2)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.new(2)
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor already initialized')

def test_part_new_initialized_version3():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    part.new(3)
    assert(part.part_contents.identifier[:6] == b'+NSR03')

def test_part_new_bad_version():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.new(4)
    assert(str(excinfo.value) == 'Invalid NSR version requested')

def test_part_set_extent_location_not_initialized():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.set_extent_location(0)
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor not initialized')

def test_part_set_start_location_not_initialized():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        part.set_start_location(0)
    assert(str(excinfo.value) == 'UDF Partition Volume Descriptor not initialized')

def test_part_equals():
    part = pycdlib.udf.UDFPartitionVolumeDescriptor()
    part.new(3)

    part2 = pycdlib.udf.UDFPartitionVolumeDescriptor()
    part2.new(3)

    assert(part == part2)

# Type 0 Partition Map
def test_type_zero_part_map_parse_initialized_twice():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    partmap.parse(b'\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.parse(b'\x00\x00')
    assert(str(excinfo.value) == 'UDF Type 0 Partition Map already initialized')

def test_type_zero_part_map_parse_bad_map_type():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x01\x00')
    assert(str(excinfo.value) == 'UDF Type 0 Partition Map type is not 0')

def test_type_zero_part_map_parse_bad_map_length():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x00\x01')
    assert(str(excinfo.value) == 'UDF Type 0 Partition Map length does not equal data length')

def test_type_zero_part_map_parse():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    partmap.parse(b'\x00\x00')
    assert(partmap._initialized)

def test_type_zero_part_map_record_not_initialized():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.record()
    assert(str(excinfo.value) == 'UDF Type 0 Partition Map not initialized')

def test_type_zero_part_map_record():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    partmap.parse(b'\x00\x00')
    assert(partmap.record() == b'\x00\x00')

def test_type_zero_part_map_new_initialized_twice():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    partmap.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.new()
    assert(str(excinfo.value) == 'UDF Type 0 Partition Map already initialized')

def test_type_zero_part_map_new():
    partmap = pycdlib.udf.UDFType0PartitionMap()
    partmap.new()
    assert(partmap._initialized)

# Type 1 Partition Map
def test_type_one_part_map_parse_initialized_twice():
    partmap = pycdlib.udf.UDFType1PartitionMap()
    partmap.parse(b'\x01\x06\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.parse(b'\x01\x06\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Type 1 Partition Map already initialized')

def test_type_one_part_map_parse_bad_map_type():
    partmap = pycdlib.udf.UDFType1PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x00\x06\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Type 1 Partition Map type is not 1')

def test_type_one_part_map_parse_bad_map_length():
    partmap = pycdlib.udf.UDFType1PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x01\x05\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Type 1 Partition Map length is not 6')

def test_type_one_part_map_record_not_initialized():
    partmap = pycdlib.udf.UDFType1PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.record()
    assert(str(excinfo.value) == 'UDF Type 1 Partition Map not initialized')

def test_type_one_part_map_new_initialized_twice():
    partmap = pycdlib.udf.UDFType1PartitionMap()
    partmap.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.new()
    assert(str(excinfo.value) == 'UDF Type 1 Partition Map already initialized')

# Type 2 Partition Map
def test_type_two_part_map_parse_initialized_twice():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    partmap.parse(b'\x02\x40' + b'\x00'*62)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.parse(b'\x02\x40' + b'\x00'*62)
    assert(str(excinfo.value) == 'UDF Type 2 Partition Map already initialized')

def test_type_two_part_map_parse_bad_map_type():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x00\x40' + b'\x00'*62)
    assert(str(excinfo.value) == 'UDF Type 2 Partition Map type is not 2')

def test_type_two_part_map_parse_bad_map_length():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        partmap.parse(b'\x02\x20' + b'\x00'*62)
    assert(str(excinfo.value) == 'UDF Type 2 Partition Map length is not 64')

def test_type_two_part_map_parse():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    partmap.parse(b'\x02\x40' + b'\x00'*62)
    assert(partmap._initialized)

def test_type_two_part_map_record_not_initialized():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.record()
    assert(str(excinfo.value) == 'UDF Type 2 Partition Map not initialized')

def test_type_two_part_map_record():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    partmap.parse(b'\x02\x40' + b'\x00'*62)
    assert(partmap.record() == (b'\x02\x40' + b'\x00'*62))

def test_type_two_part_map_new_initialized_twice():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    partmap.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        partmap.new()
    assert(str(excinfo.value) == 'UDF Type 2 Partition Map already initialized')

def test_type_two_part_map_new():
    partmap = pycdlib.udf.UDFType2PartitionMap()
    partmap.new()
    assert(partmap._initialized)

# Extended AD
def test_extendedad_parse_initialized_twice():
    ad = pycdlib.udf.UDFExtendedAD()
    ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*6 + b'\x00'*2)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*6 + b'\x00'*2)
    assert(str(excinfo.value) == 'UDF Extended Allocation descriptor already initialized')

def test_extendedad_parse():
    ad = pycdlib.udf.UDFExtendedAD()
    ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*6 + b'\x00'*2)
    assert(ad._initialized)
    assert(ad.extent_length == 0)

def test_extendedad_record_not_initialized():
    ad = pycdlib.udf.UDFExtendedAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.record()
    assert(str(excinfo.value) == 'UDF Extended Allocation Descriptor not initialized')

def test_extendedad_record():
    ad = pycdlib.udf.UDFExtendedAD()
    ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*6 + b'\x00'*2)
    rec = ad.record()
    assert(rec == b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*6 + b'\x00'*2)

def test_extendedad_new_initialized_twice():
    ad = pycdlib.udf.UDFExtendedAD()
    ad.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.new()
    assert(str(excinfo.value) == 'UDF Extended Allocation Descriptor already initialized')

def test_extendedad_new():
    ad = pycdlib.udf.UDFExtendedAD()
    ad.new()
    assert(ad._initialized)
    assert(ad.extent_length == 0)

# Short AD
def test_shortad_parse_initialized_twice():
    ad = pycdlib.udf.UDFShortAD()
    ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Short Allocation descriptor already initialized')

def test_shortad_record_not_initialized():
    ad = pycdlib.udf.UDFShortAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.record()
    assert(str(excinfo.value) == 'UDF Short AD not initialized')

def test_shortad_new_initialized_twice():
    ad = pycdlib.udf.UDFShortAD()
    ad.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.new(0)
    assert(str(excinfo.value) == 'UDF Short AD already initialized')

def test_shortad_new_bad_length():
    ad = pycdlib.udf.UDFShortAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.new(0x40000000)
    assert(str(excinfo.value) == 'UDF Short AD length must be less than or equal to 0x3fffffff')

def test_shortad_set_extent_location_not_initialized():
    ad = pycdlib.udf.UDFShortAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.set_extent_location(0, 0)
    assert(str(excinfo.value) == 'UDF Short AD not initialized')

def test_shortad_set_extent_location():
    ad = pycdlib.udf.UDFShortAD()
    ad.new(0)
    ad.set_extent_location(0, 1)
    assert(ad.log_block_num == 1)

# Long AD
def test_longad_parse_initialized_twice():
    ad = pycdlib.udf.UDFLongAD()
    ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'UDF Long Allocation descriptor already initialized')

def test_longad_record_not_initialized():
    ad = pycdlib.udf.UDFLongAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.record()
    assert(str(excinfo.value) == 'UDF Long AD not initialized')

def test_longad_new_initialized_twice():
    ad = pycdlib.udf.UDFLongAD()
    ad.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.new(0, 0)
    assert(str(excinfo.value) == 'UDF Long AD already initialized')

def test_longad_set_extent_location_not_initialized():
    ad = pycdlib.udf.UDFLongAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.set_extent_location(0, 0)
    assert(str(excinfo.value) == 'UDF Long AD not initialized')

def test_longad_length():
    ad = pycdlib.udf.UDFLongAD()
    assert(ad.length() == 16)

def test_longad_equals():
    ad = pycdlib.udf.UDFLongAD()
    ad.new(0, 0)

    ad2 = pycdlib.udf.UDFLongAD()
    ad2.new(0, 0)

    assert(ad == ad2)

# Inline AD
def test_inlinead_parse_initialized_twice():
    ad = pycdlib.udf.UDFInlineAD()
    ad.parse(0, 0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.parse(0, 0, 0)
    assert(str(excinfo.value) == 'UDF Inline Allocation Descriptor already initialized')

def test_inlinead_record_not_initialized():
    ad = pycdlib.udf.UDFInlineAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.record()
    assert(str(excinfo.value) == 'UDF Inline AD not initialized')

def test_inlinead_record():
    ad = pycdlib.udf.UDFInlineAD()
    ad.parse(0, 0, 0)
    assert(ad.record() == b'')

def test_inlinead_new_initialized_twice():
    ad = pycdlib.udf.UDFInlineAD()
    ad.new(0, 0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.new(0, 0, 0)
    assert(str(excinfo.value) == 'UDF Inline AD already initialized')

def test_inlinead_set_extent_location_not_initialized():
    ad = pycdlib.udf.UDFInlineAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.set_extent_location()
    assert(str(excinfo.value) == 'UDF Inline AD not initialized')

def test_inlinead_set_extent_location_not_initialized():
    ad = pycdlib.udf.UDFInlineAD()
    ad.new(0, 0, 0)
    ad.set_extent_location(1, 1)
    assert(ad.log_block_num == 1)

def test_inlinead_length_not_initialized():
    ad = pycdlib.udf.UDFInlineAD()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ad.length()
    assert(str(excinfo.value) == 'UDF Inline AD not initialized')

def test_inlinead_length():
    ad = pycdlib.udf.UDFInlineAD()
    ad.new(1, 0, 0)
    assert(ad.length() == 1)

# Logical Volume Descriptor
def test_logvoldesc_parse_initialized_twice():
    logvol = pycdlib.udf.UDFLogicalVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    logvol.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00'*64 + b'\x00'*128 + b'\x00\x08\x00\x00' + b'\x00*OSTA UDF Compliant' + b'\x00'*12 + b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*8 + b'\x00'*72, 0, tag)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        logvol.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00'*64 + b'\x00'*128 + b'\x00\x08\x00\x00' + b'\x00*OSTA UDF Compliant' + b'\x00'*12 + b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*8 + b'\x00'*72, 0, tag)
    assert(str(excinfo.value) == 'UDF Logical Volume Descriptor already initialized')

def test_logvoldesc_parse_bad_logical_block_size():
    logvol = pycdlib.udf.UDFLogicalVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        logvol.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00'*64 + b'\x00'*128 + b'\x00\x07\x00\x00' + b'\x00*OSTA UDF Compliant' + b'\x00'*12 + b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*8 + b'\x00'*72, 0, tag)
    assert(str(excinfo.value) == 'Volume Descriptor block size is not 2048')

def test_logvoldesc_parse_bad_domain_ident():
    logvol = pycdlib.udf.UDFLogicalVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        logvol.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00'*64 + b'\x00'*128 + b'\x00\x08\x00\x00' + b'\x00$OSTA UDF Compliant' + b'\x00'*12 + b'\x00'*16 + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*8 + b'\x00'*72, 0, tag)
    assert(str(excinfo.value) == "Volume Descriptor Identifier not '*OSTA UDF Compliant'")

def test_logvoldesc_parse_bad_map_table_length():
    logvol = pycdlib.udf.UDFLogicalVolumeDescriptor()
    tag = pycdlib.udf.UDFTag()
    tag.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        logvol.parse(b'\x00'*16 + b'\x00\x00\x00\x00' + b'\x00'*64 + b'\x00'*128 + b'\x00\x08\x00\x00' + b'\x00*OSTA UDF Compliant' + b'\x00'*12 + b'\x00'*16 + b'\x00\x00\x00\x10\x00\x00\x00\x00' + b'\x00'*32 + b'\x00'*128 + b'\x00'*8 + b'\x00'*72, 0, tag)
    assert(str(excinfo.value) == 'Map table length greater than size of partition map data; ISO corrupt')
