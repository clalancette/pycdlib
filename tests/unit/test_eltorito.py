import os
import sys
import struct

import pytest

prefix = '.'
for i in range(0, 3):
    if os.path.isdir(os.path.join(prefix, 'pycdlib')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pycdlib.eltorito
import pycdlib.headervd
import pycdlib.inode

# BootInfoTable
def test_eltorito_bit_parse_initialized_twice():
    pvd = pycdlib.headervd.PrimaryOrSupplementaryVD(pycdlib.headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY)
    pvd.new(0, b'', b'', 0, 0, 2048, b'', b'', b'', b'', b'', b'', b'', 0.0, b'', False, 1, b'')
    pvd.set_extent_location(16)

    ino = pycdlib.inode.Inode()
    ino.new(0, None, False, 0)
    ino.set_extent_location(17)

    bit = pycdlib.eltorito.EltoritoBootInfoTable()

    bit.parse(pvd, b'\x10\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', ino)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bit.parse(pvd, b'\x10\x00\x00\x00\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', ino)
    assert(str(excinfo.value) == 'This Eltorito Boot Info Table is already initialized')

def test_eltorito_bit_new_initialized_twice():
    pvd = pycdlib.headervd.PrimaryOrSupplementaryVD(pycdlib.headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY)
    pvd.new(0, b'', b'', 0, 0, 2048, b'', b'', b'', b'', b'', b'', b'', 0.0, b'', False, 1, b'')
    pvd.set_extent_location(16)

    ino = pycdlib.inode.Inode()
    ino.new(0, None, False, 0)
    ino.set_extent_location(17)

    bit = pycdlib.eltorito.EltoritoBootInfoTable()

    bit.new(pvd, ino, 0, 0)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bit.new(pvd, ino, 0, 0)
    assert(str(excinfo.value) == 'This Eltorito Boot Info Table is already initialized')

def test_eltorito_bit_record_not_initialized():
    bit = pycdlib.eltorito.EltoritoBootInfoTable()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bit.record()
    assert(str(excinfo.value) == 'This Eltorito Boot Info Table not initialized')

# Validation Entry
def test_eltorito_validation_entry_parse_initialized_twice():
    val = pycdlib.eltorito.EltoritoValidationEntry()
    val.parse(b'\x01\x00\x00\x00' + b'\x00'*24 + b'\xaa\x55\x55\xaa')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        val.parse(b'\x01\x00\x00\x00' + b'\x00'*24 + b'\xaa\x55\x55\xaa')
    assert(str(excinfo.value) == 'El Torito Validation Entry already initialized')

def test_eltorito_validation_entry_new_initialized_twice():
    val = pycdlib.eltorito.EltoritoValidationEntry()
    val.new(0)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        val.new(0)
    assert(str(excinfo.value) == 'El Torito Validation Entry already initialized')

def test_eltorito_validation_entry_record_not_initialized():
    val = pycdlib.eltorito.EltoritoValidationEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        val.record()
    assert(str(excinfo.value) == 'El Torito Validation Entry not initialized')

# Entry
def test_eltorito_entry_parse_initialized_twice():
    entry = pycdlib.eltorito.EltoritoEntry()
    entry.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*19)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*19)
    assert(str(excinfo.value) == 'El Torito Entry already initialized')

def test_eltorito_entry_new_initialized_twice():
    entry = pycdlib.eltorito.EltoritoEntry()
    entry.new(0, 0, 'noemul', 0, False)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.new(0, 0, 'noemul', 0, False)
    assert(str(excinfo.value) == 'El Torito Entry already initialized')

def test_eltorito_entry_new_invalid_media_name():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        entry.new(0, 0, 'foo', 0, False)
    assert(str(excinfo.value) == "Invalid media name 'foo'")

def test_eltorito_entry_get_rba_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.get_rba()
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_set_data_location_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.set_data_location(0, 0)
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_set_inode_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.set_inode(None)
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_record_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.record()
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_length_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.length()
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_set_data_length_not_initialized():
    entry = pycdlib.eltorito.EltoritoEntry()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        entry.set_data_length(0)
    assert(str(excinfo.value) == 'El Torito Entry not initialized')

def test_eltorito_entry_set_data_length():
    entry = pycdlib.eltorito.EltoritoEntry()
    entry.new(0, 0, 'noemul', 0, False)

    entry.set_data_length(1)
    assert(entry.sector_count == 1)

# Section Header
def test_eltorito_section_header_parse_initialized_twice():
    sh = pycdlib.eltorito.EltoritoSectionHeader()
    sh.parse(b'\x00\x00\x00\x00' + b'\x00'*28)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.parse(b'\x00\x00\x00\x00' + b'\x00'*28)
    assert(str(excinfo.value) == 'El Torito Section Header already initialized')

def test_eltorito_section_header_new_initialized_twice():
    sh = pycdlib.eltorito.EltoritoSectionHeader()
    sh.new(b'', 0)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.new(b'', 0)
    assert(str(excinfo.value) == 'El Torito Section Header already initialized')

def test_eltorito_section_header_add_parsed_entry_not_initialized():
    sh = pycdlib.eltorito.EltoritoSectionHeader()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.add_parsed_entry(None)
    assert(str(excinfo.value) == 'El Torito Section Header not initialized')

def test_eltorito_section_header_add_parsed_entry_too_many():
    sh = pycdlib.eltorito.EltoritoSectionHeader()
    sh.new(b'', 0)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        sh.add_parsed_entry(None)
    assert(str(excinfo.value) == 'El Torito section had more entries than expected by section header; ISO is corrupt')

def test_eltorito_section_header_add_new_entry_not_initialized():
    sh = pycdlib.eltorito.EltoritoSectionHeader()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.add_new_entry(None)
    assert(str(excinfo.value) == 'El Torito Section Header not initialized')

def test_eltorito_section_header_set_record_not_last_not_initialized():
    sh = pycdlib.eltorito.EltoritoSectionHeader()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.set_record_not_last()
    assert(str(excinfo.value) == 'El Torito Section Header not initialized')

def test_eltorito_section_header_record_not_initialized():
    sh = pycdlib.eltorito.EltoritoSectionHeader()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        sh.record()
    assert(str(excinfo.value) == 'El Torito Section Header not initialized')

# Boot Catalog
def test_eltorito_boot_catalog_parse_initialized_twice():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)
    bc.parse(b'\x01\x00\x00\x00' + b'\x00'*24 + b'\xaa\x55\x55\xaa')
    bc.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*19)
    bc.parse(b'\x00'*32)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.parse(b'\x01\x00\x00\x00' + b'\x00'*24 + b'\xaa\x55\x55\xaa')
    assert(str(excinfo.value) == 'El Torito Boot Catalog already initialized')

def test_eltorito_boot_catalog_parse_invalid_entry():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)
    bc.parse(b'\x01\x00\x00\x00' + b'\x00'*24 + b'\xaa\x55\x55\xaa')
    bc.parse(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*19)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\x01'*32)
    assert(str(excinfo.value) == 'Invalid El Torito Boot Catalog entry')

def test_eltorito_boot_catalog_new_initialized_twice():
    ino = pycdlib.inode.Inode()
    ino.new(0, None, False, 0)

    bc = pycdlib.eltorito.EltoritoBootCatalog(None)
    bc.new(None, ino, 1, 0, 'noemul', 0, 0, False)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.new(None, ino, 1, 0, 'noemul', 0, 0, False)
    assert(str(excinfo.value) == 'El Torito Boot Catalog already initialized')

def test_eltorito_boot_catalog_add_section_not_initialized():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.add_section(None, 0, 0, 'noemul', 0, False, False)
    assert(str(excinfo.value) == 'El Torito Boot Catalog not initialized')

def test_eltorito_boot_catalog_add_section_too_many():
    ino = pycdlib.inode.Inode()
    ino.new(0, None, False, 0)

    bc = pycdlib.eltorito.EltoritoBootCatalog(None)
    bc.new(None, ino, 1, 0, 'noemul', 0, 0, False)

    for i in range(0, 31):
        bc.add_section(ino, 0, 0, 'noemul', 0, False, False)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        bc.add_section(ino, 0, 0, 'noemul', 0, False, False)
    assert(str(excinfo.value) == 'Too many El Torito sections')

def test_eltorito_boot_catalog_record_not_initialized():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.record()
    assert(str(excinfo.value) == 'El Torito Boot Catalog not initialized')

def test_eltorito_boot_catalog_add_dirrecord_not_initialized():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.add_dirrecord(None)
    assert(str(excinfo.value) == 'El Torito Boot Catalog not initialized')

def test_eltorito_boot_catalog_add_extent_location_not_initialized():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.extent_location()
    assert(str(excinfo.value) == 'El Torito Boot Catalog not initialized')

def test_eltorito_boot_catalog_update_catalog_extent_not_initialized():
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
        bc.update_catalog_extent(0)
    assert(str(excinfo.value) == 'El Torito Boot Catalog not initialized')

def _make_parsed_boot_catalog():
    # Drive an EltoritoBootCatalog through its parse state machine up to the
    # point where it is expecting a section header, so that tests can feed it
    # section headers and a terminator.
    bc = pycdlib.eltorito.EltoritoBootCatalog(None)

    val = pycdlib.eltorito.EltoritoValidationEntry()
    val.new(0)
    bc.parse(val.record())

    entry = pycdlib.eltorito.EltoritoEntry()
    entry.new(4, 0, 'noemul', 0, True)
    bc.parse(entry.record())

    return bc

def _section_header(header_indicator, num_section_entries):
    return struct.pack('<BBH28s', header_indicator, 0, num_section_entries, b'')

def test_eltorito_boot_catalog_parse_section_entry_count_mismatch():
    bc = _make_parsed_boot_catalog()

    # Claim two section entries but supply none before the terminator.
    bc.parse(_section_header(0x91, 2))

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\x00'*32)
    assert(str(excinfo.value) == 'El Torito section header specified 2 entries, only saw 0')

def test_eltorito_boot_catalog_parse_intermediate_section_header_not_0x90():
    bc = _make_parsed_boot_catalog()

    # Two section headers, where the non-final one is not marked 0x90.
    bc.parse(_section_header(0x91, 0))
    bc.parse(_section_header(0x91, 0))

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\x00'*32)
    assert(str(excinfo.value) == 'Intermediate El Torito section header not properly specified')

def _section_entry():
    entry = pycdlib.eltorito.EltoritoEntry()
    entry.new(4, 0, 'noemul', 0, True)
    return entry

def test_eltorito_boot_catalog_parse_section_entry_without_header():
    # El Torito 2.4 says a section entry must follow a section header, but
    # ISOs exist in the wild that do not do this (Mageia 4, per the comment in
    # the parser).  Such an entry is kept as a standalone entry instead of
    # being dropped.
    bc = _make_parsed_boot_catalog()

    standalone = _section_entry()
    bc.parse(standalone.record())
    bc.parse(b'\x00'*32)

    assert(len(bc.sections) == 0)
    assert(len(bc.standalone_entries) == 1)

def test_eltorito_boot_catalog_parse_section_entry_past_header_count():
    # A section header that claims one entry, followed by two: the second one
    # does not belong to the (now full) header, so it becomes standalone.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))
    bc.parse(_section_entry().record())
    bc.parse(_section_entry().record())
    bc.parse(b'\x00'*32)

    assert(len(bc.sections) == 1)
    assert(len(bc.sections[0].section_entries) == 1)
    assert(len(bc.standalone_entries) == 1)

def test_eltorito_boot_catalog_parse_section_entry_extension():
    # A 0x44 record extends the selection criteria of the section entry that
    # precedes it.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))
    bc.parse(_section_entry().record())

    entry = bc.sections[0].section_entries[0]
    original_length = len(entry.selection_criteria)

    extension = b'crit'.ljust(30, b'\x00')
    bc.parse(b'\x44\x00' + extension)

    assert(len(entry.selection_criteria) == original_length + len(extension))
    assert(entry.selection_criteria.endswith(extension))

def test_eltorito_boot_catalog_record_includes_standalone_entries():
    bc = _make_parsed_boot_catalog()

    standalone = _section_entry()
    bc.parse(standalone.record())
    bc.parse(b'\x00'*32)

    rec = bc.record()
    # Validation entry + initial entry + the standalone entry, 32 bytes each.
    assert(len(rec) == 96)
    assert(rec.endswith(standalone.record()))

def test_eltorito_boot_catalog_parse_unterminated_catalog_with_padding():
    # Some ISOs do not terminate the boot catalog with an empty entry, and
    # instead pad the rest of the extent with garbage.  The OpenBSD install
    # ISOs pad with 0xdf (https://github.com/clalancette/pycdlib/issues/180).
    # Since the final section header is marked 0x91 and has all of the entries
    # it promised, the padding means the end of the catalog, not corruption.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))
    assert(not bc.parse(_section_entry().record()))

    assert(bc.parse(b'\xdf'*32))
    assert(len(bc.sections) == 1)
    assert(len(bc.sections[0].section_entries) == 1)
    assert(len(bc.standalone_entries) == 0)

def test_eltorito_boot_catalog_parse_padding_with_unfinished_section():
    # A final section header that is still missing entries is corrupt, and the
    # error says so specifically, whether the end of the catalog was signalled
    # by an empty entry or by padding.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 2))
    bc.parse(_section_entry().record())

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\xdf'*32)
    assert(str(excinfo.value) == 'El Torito section header specified 2 entries, only saw 1')

def test_eltorito_boot_catalog_parse_padding_with_non_final_section_header():
    # A section header that is not marked as the final one (0x91) means more of
    # the catalog is expected, so garbage is not padding, it is an error.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x90, 1))
    bc.parse(_section_entry().record())

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\xdf'*32)
    assert(str(excinfo.value) == 'Invalid El Torito Boot Catalog entry')

def test_eltorito_boot_catalog_parse_non_bootable_section_entry():
    # A non-bootable section entry has a boot indicator of 0x00, the same as
    # the empty entry that terminates the catalog.  When the last section
    # header is still owed an entry and the record has content, it is an entry,
    # not the terminator.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))

    entry = pycdlib.eltorito.EltoritoEntry()
    entry.new(4, 0, 'noemul', 0, False)
    assert(not bc.parse(entry.record()))

    assert(len(bc.sections[0].section_entries) == 1)
    assert(bc.sections[0].section_entries[0].boot_indicator == 0x00)
    assert(len(bc.standalone_entries) == 0)

    assert(bc.parse(b'\x00'*32))

def test_eltorito_boot_catalog_parse_all_zero_record_is_terminator():
    # An all-zero record is always the terminator, even when the last section
    # header is still owed an entry; that shortfall is a corrupt catalog.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        bc.parse(b'\x00'*32)
    assert(str(excinfo.value) == 'El Torito section header specified 1 entries, only saw 0')

def test_eltorito_boot_catalog_parse_zero_record_after_full_section_terminates():
    # Once the last section header has all of the entries it promised, a record
    # starting with 0x00 is the terminator rather than another section entry,
    # even if it has content after the boot indicator.
    bc = _make_parsed_boot_catalog()

    bc.parse(_section_header(0x91, 1))
    bc.parse(_section_entry().record())

    assert(bc.parse(b'\x00' + b'\xff'*31))
    assert(len(bc.sections[0].section_entries) == 1)
    assert(len(bc.standalone_entries) == 0)

def test_eltorito_boot_catalog_parse_openbsd_style_catalog():
    # The exact boot catalog layout from the OpenBSD 7.9 amd64 install ISO of
    # issue #180: validation entry, initial entry, a final (0x91) EFI section
    # header with one entry, and 0xdf padding out to the end of the extent.
    validation = struct.pack('<BBH24sHBB', 0x01, 0, 0,
                             b'Copyright (c) 2026 Theo', 0, 0x55, 0xaa)
    csum = pycdlib.eltorito.EltoritoValidationEntry._checksum(validation)
    catalog = validation[:28] + struct.pack('<HBB', csum, 0x55, 0xaa)
    catalog += struct.pack('<BBHBBHL20s', 0x88, 0, 0, 0, 0, 4, 0x484b0, b'')
    catalog += _section_header(0x91, 1)
    catalog += struct.pack('<BBHBBHL20s', 0x88, 0, 0, 0xef, 0, 0x2bc, 0x5324d, b'')
    catalog += b'\xdf' * (2048 - len(catalog))

    bc = pycdlib.eltorito.EltoritoBootCatalog(None)
    offset = 0
    while not bc.parse(catalog[offset:offset + 32]):
        offset += 32

    # Parsing stops at the first byte of padding, not at the end of the extent.
    assert(offset == 128)
    assert(bc.initial_entry.load_rba == 0x484b0)
    assert(len(bc.sections) == 1)
    assert(bc.sections[0].header_indicator == 0x91)
    assert(len(bc.sections[0].section_entries) == 1)
    assert(bc.sections[0].section_entries[0].load_rba == 0x5324d)
    assert(len(bc.standalone_entries) == 0)
