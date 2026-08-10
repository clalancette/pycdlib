import os
import sys
import struct
import time

import pytest

prefix = '.'
for i in range(0, 3):
    if os.path.isdir(os.path.join(prefix, 'pycdlib')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pycdlib.dates
import pycdlib.dr
import pycdlib.rockridge

# SP record
def test_rrsprecord_parse_double_initialized():
    sp = pycdlib.rockridge.RRSPRecord()
    sp.parse(b'SP\x07\x01\xbe\xef\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sp.parse(b'SP\x07\x01\xbe\xef\x00')
    assert(str(excinfo.value) == 'SP record already initialized')

def test_rrsprecord_parse_bad_length():
    sp = pycdlib.rockridge.RRSPRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sp.parse(b'SP\x06\x01\xbe\xef\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrsprecord_parse_bad_check_byte():
    sp = pycdlib.rockridge.RRSPRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sp.parse(b'SP\x07\x01\xbf\xef\x00')
    assert(str(excinfo.value) == 'Invalid check bytes on rock ridge extension')

def test_rrsprecord_new_double_initialized():
    sp = pycdlib.rockridge.RRSPRecord()
    sp.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sp.new(0)
    assert(str(excinfo.value) == 'SP record already initialized')

def test_rrsprecord_record_not_initialized():
    sp = pycdlib.rockridge.RRSPRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sp.record()
    assert(str(excinfo.value) == 'SP record not initialized')

def test_rrsprecord_record():
    sp = pycdlib.rockridge.RRSPRecord()
    sp.new(0)
    rec = sp.record()
    assert(rec == b'SP\x07\x01\xbe\xef\x00')

def test_rrsprecord_length():
    assert(pycdlib.rockridge.RRSPRecord.length() == 7)

# RR record
def test_rrrrrecord_parse_double_initialized():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.parse(b'RR\x05\x01\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.parse(b'RR\x05\x01\x00')
    assert(str(excinfo.value) == 'RR record already initialized')

def test_rrrrrecord_parse_bad_length():
    rr = pycdlib.rockridge.RRRRRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'RR\x06\x01\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrrrrecord_new_double_initialized():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.new()
    assert(str(excinfo.value) == 'RR record already initialized')

def test_rrrrrecord_append_field_not_initialized():
    rr = pycdlib.rockridge.RRRRRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.append_field('PX')
    assert(str(excinfo.value) == 'RR record not initialized')

def test_rrrrrecord_append_field_invalid_field():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.append_field('AA')
    assert(str(excinfo.value) == 'Unknown RR field name AA')

def test_rrrrrecord_append_field_px():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('PX')
    assert(rr.rr_flags == 0x1)

def test_rrrrrecord_append_field_pn():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('PN')
    assert(rr.rr_flags == 0x2)

def test_rrrrrecord_append_field_sl():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('SL')
    assert(rr.rr_flags == 0x4)

def test_rrrrrecord_append_field_nm():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('NM')
    assert(rr.rr_flags == 0x8)

def test_rrrrrecord_append_field_cl():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('CL')
    assert(rr.rr_flags == 0x10)

def test_rrrrrecord_append_field_pl():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('PL')
    assert(rr.rr_flags == 0x20)

def test_rrrrrecord_append_field_re():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('RE')
    assert(rr.rr_flags == 0x40)

def test_rrrrrecord_append_field_tf():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rr.append_field('TF')
    assert(rr.rr_flags == 0x80)

def test_rrrrrecord_record_not_initialized():
    rr = pycdlib.rockridge.RRRRRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.record()
    assert(str(excinfo.value) == 'RR record not initialized')

def test_rrrrrecord_record():
    rr = pycdlib.rockridge.RRRRRecord()
    rr.new()
    rec = rr.record()
    assert(rec == b'RR\x05\x01\x00')

def test_rrrrrecord_length():
    assert(pycdlib.rockridge.RRRRRecord.length() == 5)

# CE record
def test_rrcerecord_parse_double_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    ce.parse(b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.parse(b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'CE record already initialized')

def test_rrcerecord_parse_bad_length():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ce.parse(b'CE\x1a\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrcerecord_parse_bl_le_be_mismatch():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ce.parse(b'CE\x1c\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'CE record big and little endian continuation area do not agree')

def test_rrcerecord_parse_offset_le_be_mismatch():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ce.parse(b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'CE record big and little endian continuation area offset do not agree')

def test_rrcerecord_parse_len_le_be_mismatch():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        ce.parse(b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'CE record big and little endian continuation area length do not agree')

def test_rrcerecord_new_double_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    ce.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.new()
    assert(str(excinfo.value) == 'CE record already initialized')

def test_rrcerecord_update_extent_not_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.update_extent(0)
    assert(str(excinfo.value) == 'CE record not initialized')

def test_rrcerecord_update_offset_not_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.update_offset(0)
    assert(str(excinfo.value) == 'CE record not initialized')

def test_rrcerecord_update_len_not_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.update_len(0)
    assert(str(excinfo.value) == 'CE record not initialized')

def test_rrcerecord_update_add_record_not_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.add_record(0)
    assert(str(excinfo.value) == 'CE record not initialized')

def test_rrcerecord_record_not_initialized():
    ce = pycdlib.rockridge.RRCERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        ce.record()
    assert(str(excinfo.value) == 'CE record not initialized')

def test_rrcerecord_record():
    ce = pycdlib.rockridge.RRCERecord()
    ce.new()
    rec = ce.record()
    assert(rec == b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rrcerecord_length():
    assert(pycdlib.rockridge.RRCERecord.length() == 28)

# PX record
def test_rrpxrecord_parse_double_initialized():
    px = pycdlib.rockridge.RRPXRecord()
    px.parse(b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        px.parse(b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record already initialized')

def test_rrpxrecord_parse_mode_le_be_mismatch():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x24\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record big and little-endian file mode do not agree')

def test_rrpxrecord_parse_links_le_be_mismatch():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record big and little-endian file links do not agree')

def test_rrpxrecord_parse_user_le_be_mismatch():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record big and little-endian file user ID do not agree')

def test_rrpxrecord_parse_group_le_be_mismatch():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record big and little-endian file group ID do not agree')

def test_rrpxrecord_parse_serial_le_be_mismatch():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x2C\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PX record big and little-endian file serial number do not agree')

def test_rrpxrecord_parse_bad_length():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        px.parse(b'PX\x23\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on Rock Ridge PX record')

def test_rrpxrecord_new_double_initialized():
    px = pycdlib.rockridge.RRPXRecord()
    px.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        px.new(0)
    assert(str(excinfo.value) == 'PX record already initialized')

def test_rrpxrecord_record_not_initialized():
    px = pycdlib.rockridge.RRPXRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        px.record('1.12')
    assert(str(excinfo.value) == 'PX record not initialized')

def test_rrpxrecord_record_invalid_version():
    px = pycdlib.rockridge.RRPXRecord()
    px.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        px.record('4.0')
    assert(str(excinfo.value) == 'Invalid rr_version')

def test_rrpxrecord_record():
    px = pycdlib.rockridge.RRPXRecord()
    px.new(0)
    rec = px.record('1.09')
    assert(rec == b'PX\x24\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rrpxrecord_length_oneohnine():
    assert(pycdlib.rockridge.RRPXRecord.length('1.09') == 36)

def test_rrpxrecord_length_onetwelve():
    assert(pycdlib.rockridge.RRPXRecord.length('1.12') == 44)

def test_rrpxrecord_length_invalid_version():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pycdlib.rockridge.RRPXRecord.length('4.0')
    assert(str(excinfo.value) == 'Invalid rr_version')

# ER record
def test_rrerrecord_parse_double_initialized():
    er = pycdlib.rockridge.RRERRecord()
    er.parse(b'ER\x0b\x01\x01\x01\x01\x01aaa')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        er.parse(b'ER\x0b\x01\x01\x01\x01\x01aaa')
    assert(str(excinfo.value) == 'ER record already initialized')

def test_rrerrecord_parse_bad_length():
    er = pycdlib.rockridge.RRERRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        er.parse(b'ER\x19\x01\x01\x01\x01\x01aaa')
    assert(str(excinfo.value) == 'Length of ER record much too long')

def test_rrerrecord_parse_len_gt_su_len():
    er = pycdlib.rockridge.RRERRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        er.parse(b'ER\x09\x01\x09\x01\x01\x01aaa')
    assert(str(excinfo.value) == 'Combined length of ER ID, des, and src longer than record')

def test_rrerrecord_new_double_initialized():
    er = pycdlib.rockridge.RRERRecord()
    er.new(b'', b'', b'')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        er.new(b'', b'', b'')
    assert(str(excinfo.value) == 'ER record already initialized')

def test_rrerrecord_record_not_initialized():
    er = pycdlib.rockridge.RRERRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        er.record()
    assert(str(excinfo.value) == 'ER record not initialized')

def test_rrerrecord_record():
    er = pycdlib.rockridge.RRERRecord()
    er.new(b'a', b'a', b'a')
    rec = er.record()
    assert(rec == b'ER\x0b\x01\x01\x01\x01\x01aaa')

def test_rrerrecord_length():
    assert(pycdlib.rockridge.RRERRecord.length(b'a', b'a', b'a') == 11)

# ES record
def test_rresrecord_parse_double_initialized():
    es = pycdlib.rockridge.RRESRecord()
    es.parse(b'ES\x05\x01\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        es.parse(b'ES\x05\x01\x00')
    assert(str(excinfo.value) == 'ES record already initialized')

def test_rresrecord_parse_bad_length():
    es = pycdlib.rockridge.RRESRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        es.parse(b'ES\x06\x01\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rresrecord_new_double_initialized():
    es = pycdlib.rockridge.RRESRecord()
    es.new(0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        es.new(0)
    assert(str(excinfo.value) == 'ES record already initialized')

def test_rresrecord_record_not_initialized():
    es = pycdlib.rockridge.RRESRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        es.record()
    assert(str(excinfo.value) == 'ES record not initialized')

def test_rresrecord_record():
    es = pycdlib.rockridge.RRESRecord()
    es.new(0)
    rec = es.record()
    assert(rec == b'ES\x05\x01\x00')

def test_rresrecord_length():
    assert(pycdlib.rockridge.RRESRecord.length() == 5)

# PN record
def test_rrpnrecord_parse_double_initialized():
    pn = pycdlib.rockridge.RRPNRecord()
    pn.parse(b'PN\x14\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pn.parse(b'PN\x14\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PN record already initialized')

def test_rrpnrecord_parse_bad_length():
    pn = pycdlib.rockridge.RRPNRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pn.parse(b'PN\x13\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrpnrecord_parse_dev_high_be_le_mismatch():
    pn = pycdlib.rockridge.RRPNRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pn.parse(b'PN\x14\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Dev_t high little-endian does not match big-endian')

def test_rrpnrecord_parse_dev_low_be_le_mismatch():
    pn = pycdlib.rockridge.RRPNRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pn.parse(b'PN\x14\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Dev_t low little-endian does not match big-endian')

def test_rrpnrecord_new_double_initialized():
    pn = pycdlib.rockridge.RRPNRecord()
    pn.new(0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pn.new(0, 0)
    assert(str(excinfo.value) == 'PN record already initialized')

def test_rrpnrecord_record_not_initialized():
    pn = pycdlib.rockridge.RRPNRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pn.record()
    assert(str(excinfo.value) == 'PN record not initialized')

def test_rrpnrecord_record():
    pn = pycdlib.rockridge.RRPNRecord()
    pn.new(0, 0)
    rec = pn.record()
    assert(rec == b'PN\x14\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rrpnrecord_length():
    assert(pycdlib.rockridge.RRPNRecord.length() == 20)

# SL.Component
def test_rrsl_component_bad_flags():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        com = pycdlib.rockridge.RRSLRecord.Component(0x10, 0, b'')
    assert(str(excinfo.value) == 'Invalid Rock Ridge symlink flags 0x10')

def test_rrsl_component_bad_length():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        com = pycdlib.rockridge.RRSLRecord.Component(0x02, 1, b'')
    assert(str(excinfo.value) == 'Rock Ridge symlinks to dot, dotdot, or root should have zero length')

def test_rrsl_component_name_dot():
    com = pycdlib.rockridge.RRSLRecord.Component(0x02, 0, b'')
    assert(com.name() == b'.')

def test_rrsl_component_name_dotdot():
    com = pycdlib.rockridge.RRSLRecord.Component(0x04, 0, b'')
    assert(com.name() == b'..')

def test_rrsl_component_name_root():
    com = pycdlib.rockridge.RRSLRecord.Component(0x08, 0, b'')
    assert(com.name() == b'/')

def test_rrsl_component_is_continued():
    com = pycdlib.rockridge.RRSLRecord.Component(0x01, 0, b'')
    assert(com.is_continued())

def test_rrsl_component_record_dot():
    com = pycdlib.rockridge.RRSLRecord.Component(0x02, 0, b'')
    assert(com.record() == b'\x02\x00')

def test_rrsl_component_record_dotdot():
    com = pycdlib.rockridge.RRSLRecord.Component(0x04, 0, b'')
    assert(com.record() == b'\x04\x00')

def test_rrsl_component_record_root():
    com = pycdlib.rockridge.RRSLRecord.Component(0x08, 0, b'')
    assert(com.record() == b'\x08\x00')

def test_rrsl_component_set_continued():
    com = pycdlib.rockridge.RRSLRecord.Component(0x0, 0, b'')
    com.set_continued()
    assert(com.is_continued())

def test_rrsl_component_equal():
    com = pycdlib.rockridge.RRSLRecord.Component(0x0, 0, b'')
    com2 = pycdlib.rockridge.RRSLRecord.Component(0x0, 0, b'')
    assert(com == com2)

def test_rrsl_component_not_equal():
    com = pycdlib.rockridge.RRSLRecord.Component(0x0, 0, b'')
    com2 = pycdlib.rockridge.RRSLRecord.Component(0x1, 0, b'')
    assert(com != com2)

def test_rrsl_component_length_dot():
    assert(pycdlib.rockridge.RRSLRecord.Component.length(b'.') == 2)

def test_rrsl_component_length_dotdot():
    assert(pycdlib.rockridge.RRSLRecord.Component.length(b'..') == 2)

def test_rrsl_component_length_root():
    assert(pycdlib.rockridge.RRSLRecord.Component.length(b'/') == 2)

def test_rrsl_component_length_root():
    assert(pycdlib.rockridge.RRSLRecord.Component.length(b'foo') == 5)

def test_rrsl_component_factory_dot():
    com = pycdlib.rockridge.RRSLRecord.Component.factory(b'.')
    assert(com.flags == 0x2)
    assert(com.curr_length == 0)
    assert(com.data == b'.')

def test_rrsl_component_factory_dotdot():
    com = pycdlib.rockridge.RRSLRecord.Component.factory(b'..')
    assert(com.flags == 0x4)
    assert(com.curr_length == 0)
    assert(com.data == b'..')

def test_rrsl_component_factory_root():
    com = pycdlib.rockridge.RRSLRecord.Component.factory(b'/')
    assert(com.flags == 0x8)
    assert(com.curr_length == 0)
    assert(com.data == b'/')

def test_rrsl_component_factory():
    com = pycdlib.rockridge.RRSLRecord.Component.factory(b'foo')
    assert(com.flags == 0x0)
    assert(com.curr_length == 3)
    assert(com.data == b'foo')

def test_rrsl_component_not_equal_bad_type():
    com = pycdlib.rockridge.RRSLRecord.Component(0x0, 0, b'')
    assert(com.__eq__(True) == NotImplemented)

# SL record
def test_rrslrecord_parse_double_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.parse(b'SL\x08\x01\x00\x00\x03foo')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.parse(b'SL\x08\x01\x00\x00\x03foo')
    assert(str(excinfo.value) == 'SL record already initialized')

def test_rrslrecord_new_double_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.new()
    assert(str(excinfo.value) == 'SL record already initialized')

def test_rrslrecord_add_component_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.add_component(b'a')
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_add_component_too_long():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        sl.add_component(b'a'*256)
    assert(str(excinfo.value) == 'Symlink would be longer than 255')

def test_rrslrecord_current_length_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.current_length()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_record_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.record()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_name_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.name()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_name_with_root():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    sl.add_component(b'/')
    assert(sl.name() == b'')

def test_rrslrecord_name_with_continued_comp():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    sl.add_component(b'foo')
    sl.set_last_component_continued()
    sl.add_component(b'bar')
    assert(sl.name() == b'foobar')

def test_rrslrecord_set_continued_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.set_continued()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_set_last_component_continued_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.set_last_component_continued()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_set_last_component_continued_no_components():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.set_last_component_continued()
    assert(str(excinfo.value) == 'Trying to set continued on a non-existent component!')

def test_rrslrecord_last_component_continued_not_initialized():
    sl = pycdlib.rockridge.RRSLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.last_component_continued()
    assert(str(excinfo.value) == 'SL record not initialized')

def test_rrslrecord_last_component_continued_no_components():
    sl = pycdlib.rockridge.RRSLRecord()
    sl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sl.last_component_continued()
    assert(str(excinfo.value) == 'Trying to get continued on a non-existent component!')

# AL Record
def test_rralrecord_component_bad_flags():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pycdlib.rockridge.RRALRecord.Component(5, 0, b'')
    assert(str(excinfo.value) == 'Invalid Arbitrary Attribute flags 0x5')

def test_rralrecord_component_set_continued():
    comp = pycdlib.rockridge.RRALRecord.Component(0, 0, b'')
    comp.set_continued()
    assert(comp.flags == 0x1)

def test_rralrecord_component_factory():
    comp = pycdlib.rockridge.RRALRecord.Component.factory(b'foo')
    assert(comp.flags == 0x0)
    assert(comp.curr_length == 3)
    assert(comp.data == b'foo')

def test_rralrecord_parse_double_initialized():
    al = pycdlib.rockridge.RRALRecord()
    al.parse(b'\x41\x4c\x10\x01\x00\x00\x03\x04\x6e\x74\x00\x04\x01\x01\x01\xff')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.parse(b'\x41\x4c\x10\x01\x00\x00\x03\x04\x6e\x74\x00\x04\x01\x01\x01\xff')
    assert(str(excinfo.value) == 'AL record already initialized')

def test_rralrecord_parse():
    al = pycdlib.rockridge.RRALRecord()
    al.parse(b'\x41\x4c\x10\x01\x00\x00\x03\x04\x6e\x74\x00\x04\x01\x01\x01\xff')
    assert(al._initialized)
    assert(al.flags == 0)
    assert(len(al.components) == 2)
    assert(al.components[0].flags == 0)
    assert(al.components[0].curr_length == 3)
    assert(al.components[0].data == b'\x04nt')
    assert(al.components[1].flags == 0)
    assert(al.components[1].curr_length == 4)
    assert(al.components[1].data == b'\x01\x01\x01\xff')

def test_rralrecord_current_length_not_initialized():
    al = pycdlib.rockridge.RRALRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.current_length()
    assert(str(excinfo.value) == 'AL record not initialized')

def test_rralrecord_record_not_initialized():
    al = pycdlib.rockridge.RRALRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.record()
    assert(str(excinfo.value) == 'AL record not initialized')

def test_rralrecord_record():
    al = pycdlib.rockridge.RRALRecord()
    al.parse(b'\x41\x4c\x10\x01\x00\x00\x03\x04\x6e\x74\x00\x04\x01\x01\x01\xff')
    assert(al.record() == b'\x41\x4c\x10\x01\x00\x00\x03\x04\x6e\x74\x00\x04\x01\x01\x01\xff')

def test_rralrecord_new_initialized_twice():
    al = pycdlib.rockridge.RRALRecord()
    al.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.new()
    assert(str(excinfo.value) == 'AL record already initialized')

def test_rralrecord_set_continued_not_initialized():
    al = pycdlib.rockridge.RRALRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.set_continued()
    assert(str(excinfo.value) == 'AL record not initialized')

def test_rralrecord_set_continued():
    al = pycdlib.rockridge.RRALRecord()
    al.new()
    al.set_continued()
    assert(al.flags == 0x1)

def test_rralrecord_set_last_component_continued_not_initialized():
    al = pycdlib.rockridge.RRALRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.set_last_component_continued()
    assert(str(excinfo.value) == 'AL record not initialized')

def test_rralrecord_set_last_component_continued_no_components():
    al = pycdlib.rockridge.RRALRecord()
    al.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.set_last_component_continued()
    assert(str(excinfo.value) == 'Trying to set continued on a non-existent component!')

def test_rralrecord_set_last_component_continued():
    al = pycdlib.rockridge.RRALRecord()
    al.new()
    al.add_component(b'foo')
    al.set_last_component_continued()
    assert(len(al.components) == 1)
    assert(al.components[0].flags == 0x1)

def test_rralrecord_add_component_not_initialized():
    al = pycdlib.rockridge.RRALRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        al.add_component(b'foo')
    assert(str(excinfo.value) == 'AL record not initialized')

def test_rralrecord_add_component_too_long():
    al = pycdlib.rockridge.RRALRecord()
    al.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        al.add_component(b'a'*256)
    assert(str(excinfo.value) == 'Attribute would be longer than 255')

# NM record
def test_rrnmrecord_parse_double_initialized():
    nm = pycdlib.rockridge.RRNMRecord()
    nm.parse(b'NM\x05\x01\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nm.parse(b'NM\x05\x01\x00')
    assert(str(excinfo.value) == 'NM record already initialized')

def test_rrnmrecord_parse_invalid_flag():
    nm = pycdlib.rockridge.RRNMRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        nm.parse(b'NM\x05\x01\x03')
    assert(str(excinfo.value) == 'Invalid Rock Ridge NM flags')

def test_rrnmrecord_parse_flag_with_name_accepted():
    # Regression test for issue #130: VirtualBox Guest Additions ISOs
    # set the CURRENT (0x2) flag *and* include a name.  Per spec the two
    # are mutually exclusive, but the name is the writer's clear intent;
    # accept it rather than raising.  Pre-fix this raised
    # 'Invalid name in Rock Ridge NM entry (0x2 1)'.
    nm = pycdlib.rockridge.RRNMRecord()
    nm.parse(b'NM\x06\x01\x02a')
    assert(nm.posix_name == b'a')
    assert(nm.posix_name_flags == 0x2)

def test_rrnmrecord_new_double_initialized():
    nm = pycdlib.rockridge.RRNMRecord()
    nm.new(b'foo')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nm.new(b'foo')
    assert(str(excinfo.value) == 'NM record already initialized')

def test_rrnmrecord_record_not_initialized():
    nm = pycdlib.rockridge.RRNMRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nm.record()
    assert(str(excinfo.value) == 'NM record not initialized')

def test_rrnmrecord_set_continued_not_initialized():
    nm = pycdlib.rockridge.RRNMRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        nm.set_continued()
    assert(str(excinfo.value) == 'NM record not initialized')

# CL record
def test_rrclrecord_parse_double_initialized():
    cl = pycdlib.rockridge.RRCLRecord()
    cl.parse(b'CL\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        cl.parse(b'CL\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'CL record already initialized')

def test_rrclrecord_parse_invalid_size():
    cl = pycdlib.rockridge.RRCLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        cl.parse(b'CL\x0d\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrclrecord_parse_be_le_mismatch():
    cl = pycdlib.rockridge.RRCLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        cl.parse(b'CL\x0c\x01\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Little endian block num does not equal big endian; corrupt ISO')

def test_rrclrecord_new_double_initialized():
    cl = pycdlib.rockridge.RRCLRecord()
    cl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        cl.new()
    assert(str(excinfo.value) == 'CL record already initialized')

def test_rrclrecord_record_not_initialized():
    cl = pycdlib.rockridge.RRCLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        cl.record()
    assert(str(excinfo.value) == 'CL record not initialized')

def test_rrclrecord_set_log_block_num_not_initialized():
    cl = pycdlib.rockridge.RRCLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        cl.set_log_block_num(0)
    assert(str(excinfo.value) == 'CL record not initialized')

# PL record
def test_rrplrecord_parse_double_initialized():
    pl = pycdlib.rockridge.RRPLRecord()
    pl.parse(b'PL\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pl.parse(b'PL\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'PL record already initialized')

def test_rrplrecord_parse_invalid_size():
    pl = pycdlib.rockridge.RRPLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pl.parse(b'PL\x0d\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrplrecord_parse_be_le_mismatch():
    pl = pycdlib.rockridge.RRPLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        pl.parse(b'PL\x0c\x01\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Little endian block num does not equal big endian; corrupt ISO')

def test_rrplrecord_new_double_initialized():
    pl = pycdlib.rockridge.RRPLRecord()
    pl.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pl.new()
    assert(str(excinfo.value) == 'PL record already initialized')

def test_rrplrecord_record_not_initialized():
    pl = pycdlib.rockridge.RRPLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pl.record()
    assert(str(excinfo.value) == 'PL record not initialized')

def test_rrplrecord_set_log_block_num_not_initialized():
    pl = pycdlib.rockridge.RRPLRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pl.set_log_block_num(0)
    assert(str(excinfo.value) == 'PL record not initialized')

# TF record
def test_rrtfrecord_parse_double_initialized():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(b'TF\x05\x01\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tf.parse(b'TF\x05\x01\x00')
    assert(str(excinfo.value) == 'TF record already initialized')

def test_rrtfrecord_parse_invalid_size():
    tf = pycdlib.rockridge.RRTFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        tf.parse(b'TF\x04\x01\x00')
    assert(str(excinfo.value) == 'Not enough bytes in the TF record')

def test_rrtfrecord_parse_use_vol_desc_dates():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(b'TF\x16\x01\x81' + b'\x00'*17)
    assert(tf.creation_time.date_str == b'0' * 16 + b'\x00')

def test_rrtfrecord_new_double_initialized():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tf.new(0, time.time())
    assert(str(excinfo.value) == 'TF record already initialized')

def test_rrtfrecord_new_use_vol_desc_dates():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0x81, time.time())
    assert(type(tf.creation_time) == pycdlib.dates.VolumeDescriptorDate)

def test_rrtfrecord_record_not_initialized():
    tf = pycdlib.rockridge.RRTFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        tf.record()
    assert(str(excinfo.value) == 'TF record not initialized')

def test_rrtfrecord_length_use_vol_desc_dates():
    assert(pycdlib.rockridge.RRTFRecord.length(0x81) == 0x16)

def test_rrtfrecord_new_creation_seconds_forces_creation_bit():
    # Passing creation_seconds adds the creation_time bit (0x01) on top of
    # whatever flags were requested, and the field is populated from the
    # creation_seconds value rather than from date_seconds.
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(pycdlib.rockridge.TF_FLAGS, 0.0, creation_seconds=1234567890.0)
    assert(tf.time_flags & 0x01)
    assert(tf.creation_time is not None)
    assert(tf.creation_time.years_since_1900 == 109)
    assert(tf.creation_time.month == 2)
    assert(tf.creation_time.day_of_month == 13)

def test_rrtfrecord_new_no_creation_seconds_keeps_flags():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(pycdlib.rockridge.TF_FLAGS, 0.0)
    # No creation_seconds -> creation_time bit stays off, no field set.
    assert(not (tf.time_flags & 0x01))
    assert(tf.creation_time is None)

# The seven TF timestamp fields, in SUSP/RRIP bit order (bit 0 through bit 6).
_TF_FIELD_NAMES = ['creation_time', 'access_time', 'modification_time',
                   'attribute_change_time', 'backup_time', 'expiration_time',
                   'effective_time']

def _tf_vol_desc_date(day):
    # A 17-byte Volume Descriptor style date; the day of month is varied so
    # that each timestamp in a record is distinguishable from the others.
    return ('2020010%d00000000' % day).encode() + b'\x00'

def _tf_dir_record_date(day):
    # A 7-byte Directory Record style date, likewise varied by day of month.
    return struct.pack('=BBBBBBb', 120, 1, day, 0, 0, 0, 0)

def _tf_record_bytes(time_flags, dates_bytes):
    return b'TF' + struct.pack('=BBB', 5 + len(dates_bytes), 1, time_flags) + dates_bytes

def test_rrtfrecord_parse_all_fields_long_form():
    # Bit 7 set selects the long (Volume Descriptor, 17-byte) form.  With all
    # seven timestamps enabled, each one must land in its own field; giving
    # each a distinct day of month catches any slip in the offset arithmetic.
    days = list(range(1, 8))
    data = _tf_record_bytes(0xFF, b''.join(_tf_vol_desc_date(d) for d in days))
    assert(len(data) == pycdlib.rockridge.RRTFRecord.length(0xFF))

    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(data)

    for name, day in zip(_TF_FIELD_NAMES, days):
        field = getattr(tf, name)
        assert(type(field) == pycdlib.dates.VolumeDescriptorDate)
        assert(field.dayofmonth == day)

def test_rrtfrecord_parse_all_fields_short_form():
    # The same, for the short (Directory Record, 7-byte) form.
    days = list(range(1, 8))
    data = _tf_record_bytes(0x7F, b''.join(_tf_dir_record_date(d) for d in days))
    assert(len(data) == pycdlib.rockridge.RRTFRecord.length(0x7F))

    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(data)

    for name, day in zip(_TF_FIELD_NAMES, days):
        field = getattr(tf, name)
        assert(type(field) == pycdlib.dates.DirectoryRecordDate)
        assert(field.day_of_month == day)

def test_rrtfrecord_parse_backup_expiration_effective_only_long_form():
    # Only the three trailing timestamps enabled, so the parser has to skip
    # over the four disabled ones rather than reading them in sequence.
    days = [5, 6, 7]
    data = _tf_record_bytes(0xF0, b''.join(_tf_vol_desc_date(d) for d in days))
    assert(len(data) == pycdlib.rockridge.RRTFRecord.length(0xF0))

    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(data)

    for name in _TF_FIELD_NAMES[:4]:
        assert(getattr(tf, name) is None)
    assert(tf.backup_time.dayofmonth == 5)
    assert(tf.expiration_time.dayofmonth == 6)
    assert(tf.effective_time.dayofmonth == 7)

def test_rrtfrecord_parse_backup_expiration_effective_only_short_form():
    days = [5, 6, 7]
    data = _tf_record_bytes(0x70, b''.join(_tf_dir_record_date(d) for d in days))
    assert(len(data) == pycdlib.rockridge.RRTFRecord.length(0x70))

    tf = pycdlib.rockridge.RRTFRecord()
    tf.parse(data)

    for name in _TF_FIELD_NAMES[:4]:
        assert(getattr(tf, name) is None)
    assert(tf.backup_time.day_of_month == 5)
    assert(tf.expiration_time.day_of_month == 6)
    assert(tf.effective_time.day_of_month == 7)

def test_rrtfrecord_new_all_fields_short_form():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0x7F, 1234567890.0)

    for name in _TF_FIELD_NAMES:
        field = getattr(tf, name)
        assert(type(field) == pycdlib.dates.DirectoryRecordDate)
        assert(field.years_since_1900 == 109)
        assert(field.month == 2)
        assert(field.day_of_month == 13)

def test_rrtfrecord_new_all_fields_long_form():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0xFF, 1234567890.0)

    for name in _TF_FIELD_NAMES:
        field = getattr(tf, name)
        assert(type(field) == pycdlib.dates.VolumeDescriptorDate)
        assert(field.year == 2009)
        assert(field.month == 2)
        assert(field.dayofmonth == 13)

def test_rrtfrecord_new_backup_expiration_effective_only():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0x70, 1234567890.0)

    for name in _TF_FIELD_NAMES[:4]:
        assert(getattr(tf, name) is None)
    for name in _TF_FIELD_NAMES[4:]:
        assert(getattr(tf, name) is not None)

def test_rrtfrecord_record_round_trip_short_form():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0x7F, 1234567890.0)

    rec = tf.record()
    assert(len(rec) == pycdlib.rockridge.RRTFRecord.length(0x7F))

    parsed = pycdlib.rockridge.RRTFRecord()
    parsed.parse(rec)
    assert(parsed.time_flags == 0x7F)
    for name in _TF_FIELD_NAMES:
        original = getattr(tf, name)
        field = getattr(parsed, name)
        assert(field.years_since_1900 == original.years_since_1900)
        assert(field.month == original.month)
        assert(field.day_of_month == original.day_of_month)

def test_rrtfrecord_record_round_trip_long_form():
    tf = pycdlib.rockridge.RRTFRecord()
    tf.new(0xFF, 1234567890.0)

    rec = tf.record()
    assert(len(rec) == pycdlib.rockridge.RRTFRecord.length(0xFF))

    parsed = pycdlib.rockridge.RRTFRecord()
    parsed.parse(rec)
    assert(parsed.time_flags == 0xFF)
    for name in _TF_FIELD_NAMES:
        original = getattr(tf, name)
        field = getattr(parsed, name)
        assert(field.year == original.year)
        assert(field.month == original.month)
        assert(field.dayofmonth == original.dayofmonth)

# SF record
def test_rrsfrecord_parse_double_initialized():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.parse(b'SF\x0C\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sf.parse(b'SF\x0C\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'SF record already initialized')

def test_rrsfrecord_parse_one_ten():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.parse(b'SF\x0C\x01\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(sf.virtual_file_size_low == 0)

def test_rrsfrecord_parse_one_ten_be_le_mismatch():
    sf = pycdlib.rockridge.RRSFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sf.parse(b'SF\x0C\x01\x00\x00\x00\x01\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Virtual file size little-endian does not match big-endian')

def test_rrsfrecord_parse_one_twelve_high_be_le_mismatch():
    sf = pycdlib.rockridge.RRSFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sf.parse(b'SF\x15\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Virtual file size high little-endian does not match big-endian')

def test_rrsfrecord_parse_one_twelve_low_be_le_mismatch():
    sf = pycdlib.rockridge.RRSFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sf.parse(b'SF\x15\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Virtual file size low little-endian does not match big-endian')

def test_rrsfrecord_parse_one_twelve():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.parse(b'SF\x15\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(sf.virtual_file_size_low == 0)
    assert(sf.virtual_file_size_high == 0)
    assert(sf.table_depth == 0)

def test_rrsfrecord_parse_invalid_length():
    sf = pycdlib.rockridge.RRSFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sf.parse(b'SF\x16\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(str(excinfo.value) == 'Invalid length on Rock Ridge SF record (expected 12 or 21)')

def test_rrsfrecord_new_double_initialized():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.new(None, 0, None)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sf.new(None, 0, None)
    assert(str(excinfo.value) == 'SF record already initialized')

def test_rrsfrecord_new_one_ten():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.new(None, 0, None)
    assert(sf.virtual_file_size_low == 0)

def test_rrsfrecord_new_one_twelve():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.new(0, 0, 0)
    assert(sf.virtual_file_size_low == 0)
    assert(sf.virtual_file_size_high == 0)
    assert(sf.table_depth == 0)

def test_rrsfrecord_record_not_initialized():
    sf = pycdlib.rockridge.RRSFRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sf.record()
    assert(str(excinfo.value) == 'SF record not initialized')

def test_rrsfrecord_record_one_ten():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.new(None, 0, None)
    assert(sf.record() == b'SF\x0C\x01\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rrsfrecord_record_one_twelve():
    sf = pycdlib.rockridge.RRSFRecord()
    sf.new(0, 0, 0)
    assert(sf.record() == b'SF\x15\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rrsfrecord_length_one_ten():
    assert(pycdlib.rockridge.RRSFRecord.length('1.10') == 12)

def test_rrsfrecord_length_one_twelve():
    assert(pycdlib.rockridge.RRSFRecord.length('1.12') == 21)

def test_rrsfrecord_length_invalid_version():
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pycdlib.rockridge.RRSFRecord.length('foo')
    assert(str(excinfo.value) == 'Invalid rr_version')

# RE record
def test_rrrerecord_parse_double_initialized():
    re = pycdlib.rockridge.RRRERecord()
    re.parse(b'RE\x04\x01')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        re.parse(b'RE\x04\x01')
    assert(str(excinfo.value) == 'RE record already initialized')

def test_rrrerecord_parse_bad_length():
    re = pycdlib.rockridge.RRRERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        re.parse(b'RE\x06\x01\xbe\xef\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrrerecord_new_double_initialized():
    re = pycdlib.rockridge.RRRERecord()
    re.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        re.new()
    assert(str(excinfo.value) == 'RE record already initialized')

def test_rrrerecord_record_not_initialized():
    re = pycdlib.rockridge.RRRERecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        re.record()
    assert(str(excinfo.value) == 'RE record not initialized')

def test_rrrerecord_record():
    re = pycdlib.rockridge.RRRERecord()
    re.new()
    assert(re.record() == b'RE\x04\x01')

def test_rrrerecord_length():
    assert(pycdlib.rockridge.RRRERecord.length() == 4)

# ST record
def test_rrstrecord_parse_double_initialized():
    st = pycdlib.rockridge.RRSTRecord()
    st.parse(b'ST\x04\x01')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        st.parse(b'ST\x04\x01')
    assert(str(excinfo.value) == 'ST record already initialized')

def test_rrstrecord_parse_bad_length():
    st = pycdlib.rockridge.RRSTRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        st.parse(b'ST\x06\x01\xbe\xef\x00')
    assert(str(excinfo.value) == 'Invalid length on rock ridge extension')

def test_rrstrecord_new_double_initialized():
    st = pycdlib.rockridge.RRSTRecord()
    st.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        st.new()
    assert(str(excinfo.value) == 'ST record already initialized')

def test_rrstrecord_record_not_initialized():
    st = pycdlib.rockridge.RRSTRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        st.record()
    assert(str(excinfo.value) == 'ST record not initialized')

def test_rrstrecord_record():
    st = pycdlib.rockridge.RRSTRecord()
    st.new()
    assert(st.record() == b'ST\x04\x01')

def test_rrstrecord_length():
    assert(pycdlib.rockridge.RRSTRecord.length() == 4)

# PD record
def test_rrpdrecord_parse_double_initialized():
    pd = pycdlib.rockridge.RRPDRecord()
    pd.parse(b'PD\x04\x01\x00')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pd.parse(b'PD\x04\x01\x00')
    assert(str(excinfo.value) == 'PD record already initialized')

def test_rrpdrecord_new_double_initialized():
    pd = pycdlib.rockridge.RRPDRecord()
    pd.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pd.new()
    assert(str(excinfo.value) == 'PD record already initialized')

def test_rrpdrecord_record_not_initialized():
    pd = pycdlib.rockridge.RRPDRecord()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        pd.record()
    assert(str(excinfo.value) == 'PD record not initialized')

def test_rrpdrecord_record():
    pd = pycdlib.rockridge.RRPDRecord()
    pd.new()
    assert(pd.record() == b'PD\x04\x01')

def test_rrpdrecord_length():
    assert(pycdlib.rockridge.RRPDRecord.length(b'') == 4)

# RockRidge class
def test_rr_parse_bad_padding_byte():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'\x01', False, 0, False, b'')
    assert(str(excinfo.value) == 'Invalid pad byte')

def test_rr_parse_not_enough_bytes():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'\x00\x00\x00', False, 0, False, b'')
    assert(str(excinfo.value) == 'Not enough bytes left in the System Use field')

def test_rr_parse_invalid_rr_version():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'\x00\x00\x00\x00', False, 0, False, b'')
    assert(str(excinfo.value) == 'Invalid RR version 0!')

def test_rr_parse_invalid_rtype():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'\x00\x00\x01\x01', False, 0, False, b'')
    assert(str(excinfo.value) == 'Unknown SUSP record')

def test_rr_parse_invalid_sp_record():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'SP\x01\x01', False, 0, False, b'')
    assert(str(excinfo.value) == 'Invalid SUSP SP record')

def test_rr_parse_sp_record_in_non_root_dr():
    # Regression test for issue #130: VirtualBox Guest Additions ISOs put
    # SP records in dot/dotdot DRs of non-root directories, not only in
    # the root's first DR.  Pre-fix this raised 'Invalid SUSP SP record'
    # whenever is_first_dir_record_of_root was False.
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'SP\x07\x01\xbe\xef\x00', False, 0, False, b'')
    assert(rr.dr_entries.sp_record is not None)

def test_rr_parse_double_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00CE\x1c\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', False, 0, False, b'')
    assert(str(excinfo.value) == 'Only single CE record supported')

def test_rr_parse_pd_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'PD\x04\x01', False, 0, False, b'')
    assert(len(rr.dr_entries.pd_records) == 1)

def test_rr_parse_st_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'ST\x04\x01', False, 0, False, b'')
    assert(rr.dr_entries.st_record is not None)

def test_rr_parse_double_st_record():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'ST\x04\x01ST\x04\x01', False, 0, False, b'')
    assert(str(excinfo.value) == 'Only single ST record supported')

def test_rr_parse_es_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'ES\x05\x01\x00', False, 0, False, b'')
    assert(len(rr.dr_entries.es_records) == 1)

def test_rr_parse_pn_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'PN\x14\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', False, 0, False, b'')
    assert(rr.dr_entries.pn_record is not None)

def test_rr_parse_oneten():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'SF\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00', False, 0, False, b'')
    assert(rr.rr_version == '1.10')

def test_rr_parse_invalid_size():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(b'PD\x00\x01', False, 0, False, b'')
    assert(str(excinfo.value) == 'Zero size for Rock Ridge entry length')

def test_rr_record_dr_entries_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.record_dr_entries()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_record_ce_entries_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.record_ce_entries()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_record_es_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'ES\x05\x01\x00', False, 0, False, b'')
    assert(rr.record_dr_entries() == b'ES\x05\x01\x00')

def test_rr_record_pd_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'PD\x04\x01', False, 0, False, b'')
    assert(rr.record_dr_entries() == b'PD\x04\x01')

def test_rr_record_st_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'ST\x04\x01', False, 0, False, b'')
    assert(rr.record_dr_entries() == b'ST\x04\x01')

def test_rr_record_sf_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'SF\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00', False, 0, False, b'')
    assert(rr.record_dr_entries() == b'SF\x0c\x01\x00\x00\x00\x00\x00\x00\x00\x00')

def test_rr_new_initialize_twice():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    assert(str(excinfo.value) == 'Rock Ridge extension already initialized')

def test_rr_new_invalid_rr_version():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.new(False, b'foo', 0, None, '1.13', False, False, False, 0, 0, {}, time.time())
    assert(str(excinfo.value) == 'Only Rock Ridge versions 1.09, 1.10, and 1.12 are implemented')

def test_rr_new_sprecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(True, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.sp_record is not None)

def test_rr_new_rrrecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.rr_record is not None)

def test_rr_new_clrecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', True, False, False, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.cl_record is not None)
    assert(rr.child_link_extent() == 0)

def test_rr_new_rerecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, True, False, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.re_record is not None)

def test_rr_new_plrecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, True, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.pl_record is not None)
    assert(rr.parent_link_extent() == 0)

def test_rr_new_increase_dr_len_too_far():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-7, {}, time.time())
    assert(str(excinfo.value) == 'Rock Ridge entry increased DR length too far')

def test_rr_new_alrecord():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, True, 0, 0, {b'name': b'value'}, time.time())
    assert(rr.dr_entries.ce_record is None)
    assert(len(rr.dr_entries.al_records) == 1)

def test_rr_new_alrecord_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-50, {b'name': b'value'}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(len(rr.dr_entries.al_records) == 1)
    assert(rr.dr_entries.al_records[0].flags == 0x1)
    assert(len(rr.dr_entries.al_records[0].components) == 1)
    assert(rr.dr_entries.al_records[0].components[0].flags == 0x1)
    assert(rr.dr_entries.al_records[0].components[0].curr_length == 2)
    assert(rr.dr_entries.al_records[0].components[0].data == b'na')
    assert(len(rr.ce_entries.al_records) == 1)
    assert(rr.ce_entries.al_records[0].flags == 0)
    assert(len(rr.ce_entries.al_records[0].components) == 2)
    assert(rr.ce_entries.al_records[0].components[0].flags == 0)
    assert(rr.ce_entries.al_records[0].components[0].curr_length == 2)
    assert(rr.ce_entries.al_records[0].components[0].data == b'me')
    assert(rr.ce_entries.al_records[0].components[1].flags == 0)
    assert(rr.ce_entries.al_records[0].components[1].curr_length == 5)
    assert(rr.ce_entries.al_records[0].components[1].data == b'value')

def test_rr_new_alrecord_ce_record_only():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {b'name': b'value'}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(len(rr.dr_entries.al_records) == 0)
    assert(len(rr.ce_entries.al_records) == 1)
    assert(rr.ce_entries.al_records[0].flags == 0)
    assert(len(rr.ce_entries.al_records[0].components) == 2)
    assert(rr.ce_entries.al_records[0].components[0].flags == 0)
    assert(rr.ce_entries.al_records[0].components[0].curr_length == 4)
    assert(rr.ce_entries.al_records[0].components[0].data == b'name')
    assert(rr.ce_entries.al_records[0].components[1].flags == 0)
    assert(rr.ce_entries.al_records[0].components[1].curr_length == 5)
    assert(rr.ce_entries.al_records[0].components[1].data == b'value')

def test_rr_get_file_mode_ce_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {}, time.time())
    assert(rr.dr_entries.ce_record is not None)
    assert(rr.ce_entries.px_record is not None)
    assert(rr.get_file_mode() == 0)

def test_rr_add_to_file_links_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.add_to_file_links()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_remove_from_file_links_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.remove_from_file_links()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_copy_file_links_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.copy_file_links(None)
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

# Bookkeeping coverage for nlinks: the integration suite no longer asserts
# the exact posix_file_links value on directory records (the value comes
# from genisoimage's stat() call on the source dir, which is filesystem-
# dependent -- e.g. btrfs reports 1 for any directory).  These unit tests
# pin the pure increment/decrement/copy semantics directly.

def test_rr_add_to_file_links_increments():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    # A freshly-created PX record starts at 1 link.
    assert(rr.dr_entries.px_record.posix_file_links == 1)
    rr.add_to_file_links()
    assert(rr.dr_entries.px_record.posix_file_links == 2)
    rr.add_to_file_links()
    rr.add_to_file_links()
    assert(rr.dr_entries.px_record.posix_file_links == 4)

def test_rr_remove_from_file_links_decrements():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.add_to_file_links()
    rr.add_to_file_links()
    assert(rr.dr_entries.px_record.posix_file_links == 3)
    rr.remove_from_file_links()
    assert(rr.dr_entries.px_record.posix_file_links == 2)
    rr.remove_from_file_links()
    rr.remove_from_file_links()
    assert(rr.dr_entries.px_record.posix_file_links == 0)

def test_rr_copy_file_links_overrides():
    src = pycdlib.rockridge.RockRidge()
    src.new(False, b'src', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    src.add_to_file_links()
    src.add_to_file_links()
    src.add_to_file_links()
    assert(src.dr_entries.px_record.posix_file_links == 4)

    dst = pycdlib.rockridge.RockRidge()
    dst.new(False, b'dst', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    assert(dst.dr_entries.px_record.posix_file_links == 1)
    dst.copy_file_links(src)
    assert(dst.dr_entries.px_record.posix_file_links == 4)

def test_rr_add_to_file_links_uses_ce_entries_when_dr_lacks_px():
    # When the PX record lives in the SUSP CE block (because the DR was
    # too full), add_to_file_links must operate on the CE-resident PX.
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    # Move the PX record into the CE entries to mimic the spilled layout.
    # ce_entries is lazy-allocated, so materialize it via _ensure_ce_entries.
    rr._ensure_ce_entries().px_record = rr.dr_entries.px_record
    rr.dr_entries.px_record = None
    rr.add_to_file_links()
    assert(rr.ce_entries.px_record.posix_file_links == 2)
    rr.remove_from_file_links()
    rr.remove_from_file_links()
    assert(rr.ce_entries.px_record.posix_file_links == 0)

def test_rr_add_to_file_links_no_px_record():
    # If neither dr_entries nor ce_entries holds a PX record, the method
    # cannot do anything sensible and must raise.
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.dr_entries.px_record = None
    # ce_entries is None by default (no CE overflow happened), which already
    # means "no PX record on the CE side".
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.add_to_file_links()
    assert(str(excinfo.value) == 'No Rock Ridge file links')

def test_rr_remove_from_file_links_no_px_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.dr_entries.px_record = None
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.remove_from_file_links()
    assert(str(excinfo.value) == 'No Rock Ridge file links')

def test_rr_copy_file_links_no_px_record_in_src():
    src = pycdlib.rockridge.RockRidge()
    src.new(False, b'src', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    src.dr_entries.px_record = None
    dst = pycdlib.rockridge.RockRidge()
    dst.new(False, b'dst', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        dst.copy_file_links(src)
    assert(str(excinfo.value) == 'No Rock Ridge file links')

def test_rr_copy_file_links_no_px_record_in_dst():
    src = pycdlib.rockridge.RockRidge()
    src.new(False, b'src', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    dst = pycdlib.rockridge.RockRidge()
    dst.new(False, b'dst', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    dst.dr_entries.px_record = None
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        dst.copy_file_links(src)
    assert(str(excinfo.value) == 'No Rock Ridge file links')

def test_rr_get_file_mode_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.get_file_mode()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_name_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.name()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_is_symlink_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.is_symlink()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_symlink_path_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.symlink_path()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_symlink_path_no_end():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, b'bar', '1.09', False, False, False, 0, 0, {}, time.time())
    rr.dr_entries.sl_records[0].set_last_component_continued()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.symlink_path()
    assert(str(excinfo.value) == 'Saw a continued symlink record with no end; ISO is probably malformed')

def test_rr_child_link_record_exists_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.child_link_record_exists()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_child_link_update_from_dirrecord_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.child_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_child_link_update_from_dirrecord_no_child_link():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.child_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'No child link found!')

def test_rr_child_link_extent_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.child_link_extent()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_child_link_extent_no_child_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.child_link_extent()
    assert(str(excinfo.value) == 'Asked for child extent for non-existent child record')

def test_rr_parent_link_record_exists_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.parent_link_record_exists()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_parent_link_update_from_dirrecord_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.parent_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_parent_link_update_from_dirrecord_no_parent_link():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.parent_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'No parent link found!')

def test_rr_parent_link_extent_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.parent_link_extent()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_parent_link_extent_no_parent_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.parent_link_extent()
    assert(str(excinfo.value) == 'Asked for parent extent for non-existent parent record')

def test_rr_relocated_record_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.relocated_record()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_add_ce_area_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.add_ce_area(None, 0, 0)
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_clear_ce_areas_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.clear_ce_areas()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_ce_area_lengths_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.ce_area_lengths(2048)
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_record_ce_areas_not_initialized():
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.record_ce_areas()
    assert(str(excinfo.value) == 'Rock Ridge extension not initialized')

def test_rr_parse_continuation_does_not_downgrade_version():
    # Regression test: RockRidge.parse() runs once for the inline DR area
    # and a second time (with continuation=True) for the CE block.  Each
    # call recomputes its own rr_version from the records it sees in
    # that buffer.  Before the fix, the second call would unconditionally
    # overwrite self.rr_version, so an ISO whose 44-byte (RR 1.12) PX
    # was inline but whose CE block carried only NM/SL/etc. would end
    # up with rr_version demoted back to '1.09'.  On write, that
    # produced a 36-byte PX (8 bytes shorter than the dr_len field
    # claimed) and the next round-trip would fail with "Invalid RR
    # version 0!" parsing the resulting 8 bytes of trailing slop.
    def le_be(val):
        return struct.pack('<L', val) + struct.pack('>L', val)

    ts7 = b'\x00\x00\x01\x01\x01\x01\x00'  # valid 7-byte DirectoryRecordDate

    # Inline RR: SP + RR + PX (44-byte / 1.12 form) + TF + CE.
    sp = b'SP\x07\x01\xbe\xef\x00'
    rr_rec = b'RR\x05\x01\x81'
    px_1_12 = (b'PX\x2c\x01' + le_be(0o100644) + le_be(1)
               + le_be(0) + le_be(0) + le_be(0))
    tf = b'TF\x1a\x01\x0e' + ts7 * 3
    ce = b'CE\x1c\x01' + le_be(0) + le_be(0) + le_be(0)
    inline = sp + rr_rec + px_1_12 + tf + ce
    assert(len(inline) == 110)  # sanity

    # Continuation block: a single NM record.  No PX, no SF, no ES, no
    # ER -- nothing that signals 1.12.
    nm = b'NM\x06\x01\x00X'

    rr = pycdlib.rockridge.RockRidge()
    rr.parse(inline, True, 0, False, b'.')
    assert(rr.rr_version == '1.12')

    rr.parse(nm, False, 0, True, b'.')
    assert(rr.rr_version == '1.12')

def test_rr_parse_continuation_can_upgrade_version():
    # Inverse of the above: if the inline area has no 1.12 signals but
    # the continuation does, rr_version should escalate to '1.12'.
    def le_be(val):
        return struct.pack('<L', val) + struct.pack('>L', val)

    ts7 = b'\x00\x00\x01\x01\x01\x01\x00'

    # Inline: just SP and CE (no PX), so rr_version starts at '1.09'.
    inline = (b'SP\x07\x01\xbe\xef\x00'
              + b'CE\x1c\x01' + le_be(0) + le_be(0) + le_be(0))

    # Continuation carries a 44-byte PX (1.12 signal).
    px_1_12 = (b'PX\x2c\x01' + le_be(0o100644) + le_be(1)
               + le_be(0) + le_be(0) + le_be(0))

    rr = pycdlib.rockridge.RockRidge()
    rr.parse(inline, True, 0, False, b'.')
    assert(rr.rr_version == '1.09')

    rr.parse(px_1_12, False, 0, True, b'.')
    assert(rr.rr_version == '1.12')

# RockRidgeContinuationBlock and RockRidgeContinuationEntry
def test_rrcontentry_track_into_empty():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    assert(len(rr._entries) == 1)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)

def test_rrcontentry_track_at_end():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)
    rr.track_entry(23, 33)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_track_at_beginning():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(23, 33)
    rr.track_entry(0, 23)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_track_overlap():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.track_entry(22, 33)
    assert(str(excinfo.value) == 'Overlapping CE regions on the ISO')

def test_rrcontentry_track_exact_duplicate_idempotent():
    # Regression test for issue #130: ISOs (e.g. VirtualBox Guest Additions)
    # share a single CE region across many DRs to save space, so the parser
    # sees the same (offset, length) registered repeatedly.  Treat
    # exact-match re-registrations as idempotent rather than overlapping.
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)
    rr.track_entry(0, 23)
    assert(len(rr._entries) == 1)

def test_rrcontentry_track_rest():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)
    rr.track_entry(23, 2025)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 2025)

def test_rrcontentry_track_toolarge():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.track_entry(23, 2026)
    assert(str(excinfo.value) == 'No room in continuation block to track entry')

def test_rrcontentry_add_into_empty():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)

    assert(len(rr._entries) == 1)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)

def test_rrcontentry_add_at_end():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)
    assert(rr.add_entry(33) is not None)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_add_at_beginning():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(23, 33)
    assert(rr.add_entry(23) is not None)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_add_multiple():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)
    rr.track_entry(40, 12)
    assert(rr.add_entry(12) is not None)

    assert(len(rr._entries) == 3)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 12)
    assert(rr._entries[2].offset == 40)
    assert(rr._entries[2].length == 12)

def _ce_record(block, offset, length):
    def swab(x):
        return struct.unpack('>I', struct.pack('<I', x))[0]
    return b'CE' + bytes([28, 1]) + struct.pack('<IIIIII', block, swab(block),
                                                offset, swab(offset),
                                                length, swab(length))

def test_rr_two_ce_records_in_one_area():
    # A CE record is single-instance per System Use area, not per Rock Ridge
    # object: an area is allowed to chain to a further area via its own CE, but
    # two CE records in the same area is invalid.
    rr = pycdlib.rockridge.RockRidge()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        rr.parse(_ce_record(24, 0, 100) + _ce_record(25, 0, 100), False, 0,
                 True, b'foo')
    assert(str(excinfo.value) == 'Only single CE record supported')

def test_rr_ce_record_in_each_area():
    # One CE in the directory record and another in the continuation area it
    # points at is a legal chain, and must not trip the single-instance check.
    rr = pycdlib.rockridge.RockRidge()
    rr.parse(_ce_record(24, 0, 100), False, 0, False, b'foo')
    rr.parse(_ce_record(25, 0, 100), False, 0, True, b'foo')

    assert(rr.dr_entries.ce_record is not None)
    assert(rr.dr_entries.ce_record.bl_cont_area == 24)
    assert(rr.ce_entries is not None)
    assert(rr.ce_entries.ce_record is not None)
    assert(rr.ce_entries.ce_record.bl_cont_area == 25)

def test_rrcontentry_add_no_room_returns_none():
    # Regression test for issue #177: when the continuation block is full,
    # add_entry() must return None (as documented), not -1.  The caller in
    # PrimaryOrSupplementaryVD.add_rr_ce_entry() checks 'is not None' to
    # decide whether to allocate a new block, so a -1 return silently gets
    # stored as the CE offset and later blows up in swab_32bit() on write.
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(2048) == 0)

    assert(rr.add_entry(1) is None)
    assert(len(rr._entries) == 1)

def test_rrcontentry_add_no_room_at_beginning_returns_none():
    # Same as above, but exercising the path where entries already exist and
    # neither the leading gap nor the tail has room for the new entry.
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(10, 2038)

    assert(rr.add_entry(11) is None)
    assert(len(rr._entries) == 1)

def test_rrcontentry_add_larger_than_block_returns_none():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)

    assert(rr.add_entry(2049) is None)
    assert(len(rr._entries) == 0)

def test_rrcontblock_remove_entry_no_entry():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.remove_entry(0, 0)
    assert(str(excinfo.value) == 'Could not find an entry for the RR CE entry in the CE block!')

def test_rr_get_file_mode_no_px_anywhere():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.dr_entries.px_record = None
    rr.ce_entries = None

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.get_file_mode()
    assert(str(excinfo.value) == 'No Rock Ridge file mode')

def test_rr_child_link_update_from_dirrecord_no_cl_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.cl_to_moved_dr = pycdlib.dr.DirectoryRecord()
    rr.dr_entries.cl_record = None
    rr.ce_entries = None

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.child_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'Could not find child link record!')

def test_rr_parent_link_update_from_dirrecord_no_pl_record():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    rr.parent_link = pycdlib.dr.DirectoryRecord()
    rr.dr_entries.pl_record = None
    rr.ce_entries = None

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rr.parent_link_update_from_dirrecord()
    assert(str(excinfo.value) == 'Could not find parent link record!')

def test_rr_ce_area_lengths_entry_too_large_for_area():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {}, time.time())
    assert(rr.ce_entries is not None)

    # An area with room for the linking CE record and almost nothing else
    # cannot hold any real entry.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.ce_area_lengths(pycdlib.rockridge.RRCERecord.length() + 2)
    assert(str(excinfo.value) == 'Rock Ridge entry is too large to fit into a Continuation Area')

def test_rr_record_ce_areas_entries_do_not_fit():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28, {}, time.time())
    assert(rr.ce_entries is not None)

    # Deliberately allocate an area far smaller than ce_area_lengths asked for.
    block = pycdlib.rockridge.RockRidgeContinuationBlock(0, 2048)
    rr.add_ce_area(block, 0, 4)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        rr.record_ce_areas()
    assert(str(excinfo.value) == 'Rock Ridge Continuation entries do not fit into the areas allocated for them')

def test_rr_parse_al_record():
    # AL (Arbitrary Attribute) records round-trip: generate one via new(),
    # then parse it back out of a SUSP byte string.
    source = pycdlib.rockridge.RockRidge()
    source.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28,
               {b'name': b'value'}, time.time())
    al_bytes = source.ce_entries.al_records[0].record()

    rr = pycdlib.rockridge.RockRidge()
    rr.parse(b'RR\x05\x01\x89' + al_bytes, False, 0, False, b'foo')

    assert(len(rr.dr_entries.al_records) == 1)
    components = rr.dr_entries.al_records[0].components
    assert(len(components) == 2)
    assert(components[0].data == b'name')
    assert(components[1].data == b'value')

def test_rr_record_ce_entries_includes_al_records():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 254-28,
           {b'name': b'value'}, time.time())
    assert(len(rr.ce_entries.al_records) == 1)

    ce = rr.record_ce_entries()
    assert(rr.ce_entries.al_records[0].record() in ce)

def test_rr_record_ce_entries_no_ce_entries():
    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, 0, {}, time.time())
    assert(rr.ce_entries is None)
    assert(rr.record_ce_entries() == b'')

# Each of the SUSP records that _assign_entries lays down has its own "this
# will not fit in the Directory Record" path, which returns -1 so that new()
# retries with a Continuation Entry.  The tests below drive one record type
# each, sizing curr_dr_len so that the record under test is the one that
# overflows.
#
# With a 3-byte Rock Ridge name, the records ahead of CL/RE/PL consume a fixed
# 75 bytes: RR (5) + NM (5 + 3) + PX (36) + TF (26).
_RR_BYTES_BEFORE_RELOCATION_RECORDS = 75

def test_rr_assign_entries_sp_record_does_not_fit():
    # The SP record is the first one laid down, so it overflows as soon as the
    # incoming length leaves fewer bytes than the record needs.  _assign_entries
    # is driven directly here because at these sizes new() cannot succeed even
    # after adding a Continuation Entry -- the CE record itself no longer fits.
    rr = pycdlib.rockridge.RockRidge()
    rr.rr_version = '1.09'

    curr_dr_len = pycdlib.rockridge.ALLOWED_DR_SIZE - pycdlib.rockridge.RRSPRecord.length() + 1
    assert(rr._assign_entries(True, b'foo', 0, None, False, False, False, 0,
                              curr_dr_len, {}, 1234567890.0) == -1)

def test_rr_assign_entries_rr_record_does_not_fit():
    # With is_first_dir_record_of_root False there is no SP record, so the RR
    # record is the first one laid down.
    rr = pycdlib.rockridge.RockRidge()
    rr.rr_version = '1.09'

    curr_dr_len = pycdlib.rockridge.ALLOWED_DR_SIZE - pycdlib.rockridge.RRRRRecord.length() + 1
    assert(rr._assign_entries(False, b'foo', 0, None, False, False, False, 0,
                              curr_dr_len, {}, 1234567890.0) == -1)

def test_rr_new_cl_record_forced_into_continuation_area():
    curr_dr_len = (pycdlib.rockridge.ALLOWED_DR_SIZE
                   - _RR_BYTES_BEFORE_RELOCATION_RECORDS
                   - pycdlib.rockridge.RRCLRecord.length() + 1)

    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', True, False, False, 0, curr_dr_len,
           {}, time.time())

    assert(rr.dr_entries.ce_record is not None)
    assert(rr.dr_entries.cl_record is None)
    assert(rr.ce_entries.cl_record is not None)

def test_rr_new_re_record_forced_into_continuation_area():
    curr_dr_len = (pycdlib.rockridge.ALLOWED_DR_SIZE
                   - _RR_BYTES_BEFORE_RELOCATION_RECORDS
                   - pycdlib.rockridge.RRRERecord.length() + 1)

    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, True, False, 0, curr_dr_len,
           {}, time.time())

    assert(rr.dr_entries.ce_record is not None)
    assert(rr.dr_entries.re_record is None)
    assert(rr.ce_entries.re_record is not None)

def test_rr_new_pl_record_forced_into_continuation_area():
    curr_dr_len = (pycdlib.rockridge.ALLOWED_DR_SIZE
                   - _RR_BYTES_BEFORE_RELOCATION_RECORDS
                   - pycdlib.rockridge.RRPLRecord.length() + 1)

    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, True, 0, curr_dr_len,
           {}, time.time())

    assert(rr.dr_entries.ce_record is not None)
    assert(rr.dr_entries.pl_record is None)
    assert(rr.ce_entries.pl_record is not None)

def test_rr_new_al_record_does_not_fit():
    # The AL record is sized from the attribute name/value pairs, and splits
    # across the Directory Record and the Continuation Entry when it cannot fit
    # inline.
    attributes = {b'k': b'v'*60}
    attr_list = list(attributes.keys()) + list(attributes.values())
    curr_dr_len = (pycdlib.rockridge.ALLOWED_DR_SIZE
                   - _RR_BYTES_BEFORE_RELOCATION_RECORDS
                   - pycdlib.rockridge.RRALRecord.length(attr_list) + 1)

    rr = pycdlib.rockridge.RockRidge()
    rr.new(False, b'foo', 0, None, '1.09', False, False, False, 0, curr_dr_len,
           attributes, time.time())

    assert(rr.dr_entries.ce_record is not None)
    assert(len(rr.dr_entries.al_records) == 1)
    assert(len(rr.ce_entries.al_records) == 1)
