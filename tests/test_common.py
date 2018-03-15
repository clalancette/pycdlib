try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import pytest
import os
import sys
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pycdlib

# Technically, Rock Ridge doesn't impose a length limitation on NM (alternate
# name) or SL (symlinks).  However, in practice, the Linux kernel (at least
# ext4) doesn't support any names longer than 255, and the ISO driver doesn't
# support any names longer than 248.  Thus we stick to 248 for our tests.
RR_MAX_FILENAME_LENGTH = 248

def find_executable(executable):
    paths = os.environ['PATH'].split(os.pathsep)

    if os.path.isfile(executable):
        return executable
    else:
        for p in paths:
            f = os.path.join(p, executable)
            if os.path.isfile(f):
                return f
    return None

################################ INTERNAL HELPERS #############################

def internal_check_pvd(pvd, extent, size, ptbl_size, ptbl_location_le, ptbl_location_be):
    # The length of the system identifer should always be 32.
    assert(len(pvd.system_identifier) == 32)
    # The length of the volume identifer should always be 32.
    assert(len(pvd.volume_identifier) == 32)
    # The amount of space the ISO takes depends on the files and directories
    # on the ISO.
    assert(pvd.space_size == size)
    # The set size should always be one for these tests.
    assert(pvd.set_size == 1)
    # genisoimage only supports setting the sequence number to 1
    assert(pvd.seqnum == 1)
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(pvd.log_block_size == 2048)
    # The path table size depends on how many directories there are on the ISO.
    assert(pvd.path_tbl_size == ptbl_size)
    # The little endian version of the path table should start at the location
    # passed in (this changes based on how many volume descriptors there are,
    # e.g. Joliet).
    assert(pvd.path_table_location_le == ptbl_location_le)
    # The optional path table location should always be zero.
    assert(pvd.optional_path_table_location_le == 0)
    # The big endian version of the path table changes depending on how many
    # directories there are on the ISO.
    assert(pvd.path_table_location_be == ptbl_location_be)
    # The optional path table location should always be zero.
    assert(pvd.optional_path_table_location_be == 0)
    # The length of the volume set identifer should always be 128.
    assert(len(pvd.volume_set_identifier) == 128)
    # The volume set identifier is always blank here.
    assert(pvd.volume_set_identifier == b' '*128)
    # The publisher identifier text should be blank.
    assert(pvd.publisher_identifier.text == b' '*128)
    # The preparer identifier text should be blank.
    assert(pvd.preparer_identifier.text == b' '*128)
    # The copyright file identifier should be blank.
    assert(pvd.copyright_file_identifier == b' '*37)
    # The abstract file identifier should be blank.
    assert(pvd.abstract_file_identifier == b' '*37)
    # The bibliographic file identifier should be blank.
    assert(pvd.bibliographic_file_identifier == b' '*37)
    # The primary volume descriptor should always have a file structure version
    # of 1.
    assert(pvd.file_structure_version == 1)
    # The length of the application use string should always be 512.
    assert(len(pvd.application_use) == 512)
    # The PVD should be where we want it.
    assert(pvd.extent_location() == extent)

def internal_check_enhanced_vd(en_vd, size, ptbl_size, ptbl_location_le,
                               ptbl_location_be):
    assert(en_vd.version == 2)
    assert(en_vd.flags == 0)
    # The length of the system identifer should always be 32.
    assert(len(en_vd.system_identifier) == 32)
    # The length of the volume identifer should always be 32.
    assert(len(en_vd.volume_identifier) == 32)
    # The amount of space the ISO takes depends on the files and directories
    # on the ISO.
    assert(en_vd.space_size == size)
    assert(en_vd.escape_sequences == b'\x00'*32)
    assert(en_vd.set_size == 1)
    assert(en_vd.seqnum == 1)
    assert(en_vd.log_block_size == 2048)
    assert(en_vd.path_tbl_size == ptbl_size)
    # The little endian version of the path table should start at the location
    # passed in (this changes based on how many volume descriptors there are,
    # e.g. Joliet).
    assert(en_vd.path_table_location_le == ptbl_location_le)
    # The optional path table location should always be zero.
    assert(en_vd.optional_path_table_location_le == 0)
    # The big endian version of the path table changes depending on how many
    # directories there are on the ISO.
    assert(en_vd.path_table_location_be == ptbl_location_be)
    # The optional path table location should always be zero.
    assert(en_vd.optional_path_table_location_be == 0)
    # The length of the volume set identifer should always be 128.
    assert(len(en_vd.volume_set_identifier) == 128)
    # The volume set identifier is always blank here.
    assert(en_vd.volume_set_identifier == b' '*128)
    # The publisher identifier text should be blank.
    assert(en_vd.publisher_identifier.text == b' '*128)
    # The preparer identifier text should be blank.
    assert(en_vd.preparer_identifier.text == b' '*128)
    # The copyright file identifier should be blank.
    assert(en_vd.copyright_file_identifier == b' '*37)
    # The abstract file identifier should be blank.
    assert(en_vd.abstract_file_identifier == b' '*37)
    # The bibliographic file identifier should be blank.
    assert(en_vd.bibliographic_file_identifier == b' '*37)
    # The primary volume descriptor should always have a file structure version
    # of 1.
    assert(en_vd.file_structure_version == 2)

def internal_check_eltorito(brs, boot_catalog, boot_catalog_extent, load_rba, media_type=0,
                            system_type=0, bootable=True):
    # Now check the Eltorito Boot Record.

    # We support only one boot record for now.
    assert(len(brs) == 1)
    eltorito = brs[0]
    # The boot_system_identifier for El Torito should always be a space-padded
    # version of "EL TORITO SPECIFICATION".
    assert(eltorito.boot_system_identifier == b"EL TORITO SPECIFICATION".ljust(32, b'\x00'))
    # The boot identifier should always be 32 zeros.
    assert(eltorito.boot_identifier == b"\x00"*32)
    # The boot_system_use field should always contain the boot catalog extent
    # encoded as a string.
    assert(eltorito.boot_system_use[:4] == struct.pack("=L", boot_catalog_extent))
    # The boot catalog validation entry should have a platform id of 0.
    assert(boot_catalog.validation_entry.platform_id == 0)
    # The boot catalog validation entry should have an id string of all zeros.
    assert(boot_catalog.validation_entry.id_string == b"\x00"*24)
    # The boot catalog validation entry should have a checksum of 0x55aa.
    assert(boot_catalog.validation_entry.checksum == 0x55aa)

    # The boot catalog initial entry should have a boot indicator of 0x88.
    if bootable:
        assert(boot_catalog.initial_entry.boot_indicator == 0x88)
    else:
        assert(boot_catalog.initial_entry.boot_indicator == 0)
    # The boot catalog initial entry should have a boot media type of 0.
    assert(boot_catalog.initial_entry.boot_media_type == media_type)
    # The boot catalog initial entry should have a load segment of 0.
    assert(boot_catalog.initial_entry.load_segment == 0)
    # The boot catalog initial entry should have a system type of 0.
    assert(boot_catalog.initial_entry.system_type == system_type)
    # The boot catalog initial entry should have a sector count of 4.
    if media_type == 0:
        sector_count = 4
    else:
        sector_count = 1
    assert(boot_catalog.initial_entry.sector_count == sector_count)
    # The boot catalog initial entry should have the correct load rba.
    if load_rba is not None:
        assert(boot_catalog.initial_entry.load_rba == load_rba)
    # The El Torito boot record should always be at extent 17.
    assert(eltorito.extent_location() == 17)

def internal_check_joliet(svd, space_size, path_tbl_size, path_tbl_loc_le,
                          path_tbl_loc_be):
    # The supplementary volume descriptor should always have a version of 1.
    assert(svd.version == 1 or svd.version == 2)
    # The supplementary volume descriptor should always have flags of 0.
    assert(svd.flags == 0)
    # The supplementary volume descriptor system identifier length should always
    # be 32.
    assert(len(svd.system_identifier) == 32)
    # The supplementary volume descriptor volume identifer length should always
    # be 32.
    assert(len(svd.volume_identifier) == 32)
    # The amount of space the ISO takes depends on the files and directories
    # on the ISO.
    assert(svd.space_size == space_size)
    # The supplementary volume descriptor in these tests only supports the one
    # Joliet sequence of '%\E'.
    assert(svd.escape_sequences == b'%/@'+b'\x00'*29 or
           svd.escape_sequences == b'%/C'+b'\x00'*29 or
           svd.escape_sequences == b'%/E'+b'\x00'*29)
    # The supplementary volume descriptor should always have a set size of 1.
    assert(svd.set_size == 1)
    # The supplementary volume descriptor should always have a sequence number of 1.
    assert(svd.seqnum == 1)
    # The supplementary volume descriptor should always have a logical block size
    # of 2048.
    assert(svd.log_block_size == 2048)
    # The path table size depends on how many directories there are on the ISO.
    assert(svd.path_tbl_size == path_tbl_size)
    # The little endian version of the path table moves depending on what else is
    # on the ISO.
    assert(svd.path_table_location_le == path_tbl_loc_le)
    # The optional path table location should be 0.
    assert(svd.optional_path_table_location_le == 0)
    # The big endian version of the path table changes depending on how many
    # directories there are on the ISO.
    assert(svd.path_table_location_be == path_tbl_loc_be)
    # The length of the volume set identifer should always be 128.
    assert(svd.volume_set_identifier == b'\x00 '*64)
    # The publisher identifier text should be blank.
    assert(svd.publisher_identifier.text == b'\x00 '*64)
    # The preparer identifier text should be blank.
    assert(svd.preparer_identifier.text == b'\x00 '*64)
    # The copyright file identifier should be blank.
    assert(svd.copyright_file_identifier == b'\x00 '*18+b'\x00')
    # The abstract file identifier should be blank.
    assert(svd.abstract_file_identifier == b'\x00 '*18+b'\x00')
    # The bibliographic file identifier should be blank.
    assert(svd.bibliographic_file_identifier == b'\x00 '*18+b'\x00')
    # The supplementary volume descriptor should always have a file structure version
    # of 1.
    assert(svd.file_structure_version == 1)
    # The length of the application use string should always be 512.
    assert(len(svd.application_use) == 512)

def internal_check_terminator(terminators, extent):
    # There should only ever be one terminator (though the standard seems to
    # allow for multiple, I'm not sure how or why that would work).
    assert(len(terminators) == 1)
    terminator = terminators[0]

    assert(terminator.extent_location() == extent)

def internal_check_root_dir_record(root_dir_record, num_children, data_length,
                                   extent_location, rr, rr_nlinks, xa, rr_onetwelve):
    # The root_dir_record directory record length should be exactly 34.
    assert(root_dir_record.dr_len == 34)
    # We don't support xattrs at the moment, so it should always be 0.
    assert(root_dir_record.xattr_len == 0)
    # Make sure the root directory record starts at the extent we expect.
    assert(root_dir_record.extent_location() == extent_location)

    # We don't check the extent_location_le or extent_location_be, since I
    # don't really understand the algorithm by which genisoimage generates them.

    # The length of the root directory record depends on the number of entries
    # there are at the top level.
    assert(root_dir_record.file_length() == data_length)

    # We skip checking the date since it changes all of the time.

    # The file flags for the root dir record should always be 0x2 (DIRECTORY bit).
    assert(root_dir_record.file_flags == 2)
    # The file unit size should always be zero.
    assert(root_dir_record.file_unit_size == 0)
    # The interleave gap size should always be zero.
    assert(root_dir_record.interleave_gap_size == 0)
    # The sequence number should always be one.
    assert(root_dir_record.seqnum == 1)
    # The len_fi should always be one.
    assert(root_dir_record.len_fi == 1)

    # Everything after here is derived data.

    # The root directory should be the, erm, root.
    assert(root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(root_dir_record.file_ident == b"\x00")
    assert(root_dir_record.parent == None)
    assert(root_dir_record.rock_ridge == None)
    # The number of children the root directory record has depends on the number
    # of files+directories there are at the top level.
    assert(len(root_dir_record.children) == num_children)

    # Now check the "dot" directory record.
    internal_check_dot_dir_record(root_dir_record.children[0], rr, rr_nlinks, True, xa, data_length, rr_onetwelve)

    # Now check the "dotdot" directory record.
    internal_check_dotdot_dir_record(root_dir_record.children[1], rr, rr_nlinks, xa, rr_onetwelve)

def internal_check_dot_dir_record(dot_record, rr, rr_nlinks, first_dot, xa, datalen=2048, rr_onetwelve=False):
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == b"\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34 with no extensions.
    if rr:
        if first_dot:
            if rr_onetwelve:
                expected_dr_len = 140
            else:
                expected_dr_len = 136
        else:
            # All other Rock Ridge "dot" entries are 102 bytes long.
            expected_dr_len = 102
    else:
        expected_dr_len = 34

    if xa:
        expected_dr_len += 14

    assert(dot_record.data_length == datalen)
    assert(dot_record.dr_len == expected_dr_len)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 2)

    if rr:
        assert(dot_record.rock_ridge._initialized == True)
        if first_dot:
            assert(dot_record.rock_ridge.dr_entries.sp_record != None)
            if xa:
                assert(dot_record.rock_ridge.dr_entries.sp_record.bytes_to_skip == 14)
            else:
                assert(dot_record.rock_ridge.dr_entries.sp_record.bytes_to_skip == 0)
        else:
            assert(dot_record.rock_ridge.dr_entries.sp_record == None)
        if not rr_onetwelve:
            assert(dot_record.rock_ridge.dr_entries.rr_record != None)
            assert(dot_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x81)
        if first_dot:
            assert(dot_record.rock_ridge.dr_entries.ce_record != None)
            assert(dot_record.rock_ridge.ce_entries.sp_record == None)
            assert(dot_record.rock_ridge.ce_entries.rr_record == None)
            assert(dot_record.rock_ridge.ce_entries.ce_record == None)
            assert(dot_record.rock_ridge.ce_entries.px_record == None)
            assert(dot_record.rock_ridge.ce_entries.er_record != None)
            assert(dot_record.rock_ridge.ce_entries.er_record.ext_id == b'RRIP_1991A')
            assert(dot_record.rock_ridge.ce_entries.er_record.ext_des == b'THE ROCK RIDGE INTERCHANGE PROTOCOL PROVIDES SUPPORT FOR POSIX FILE SYSTEM SEMANTICS')
            assert(dot_record.rock_ridge.ce_entries.er_record.ext_src == b'PLEASE CONTACT DISC PUBLISHER FOR SPECIFICATION SOURCE.  SEE PUBLISHER IDENTIFIER IN PRIMARY VOLUME DESCRIPTOR FOR CONTACT INFORMATION.')
            assert(dot_record.rock_ridge.ce_entries.es_record == None)
            assert(dot_record.rock_ridge.ce_entries.pn_record == None)
            assert(dot_record.rock_ridge.ce_entries.sl_records == [])
            assert(dot_record.rock_ridge.ce_entries.nm_records == [])
            assert(dot_record.rock_ridge.ce_entries.cl_record == None)
            assert(dot_record.rock_ridge.ce_entries.pl_record == None)
            assert(dot_record.rock_ridge.ce_entries.tf_record == None)
            assert(dot_record.rock_ridge.ce_entries.sf_record == None)
            assert(dot_record.rock_ridge.ce_entries.re_record == None)
        else:
            assert(dot_record.rock_ridge.dr_entries.ce_record == None)
        assert(dot_record.rock_ridge.dr_entries.px_record != None)
        assert(dot_record.rock_ridge.dr_entries.px_record.posix_file_mode == 0o040555)
        assert(dot_record.rock_ridge.dr_entries.px_record.posix_file_links == rr_nlinks)
        assert(dot_record.rock_ridge.dr_entries.px_record.posix_user_id == 0)
        assert(dot_record.rock_ridge.dr_entries.px_record.posix_group_id == 0)
        assert(dot_record.rock_ridge.dr_entries.px_record.posix_serial_number == 0)
        assert(dot_record.rock_ridge.dr_entries.er_record == None)
        assert(dot_record.rock_ridge.dr_entries.es_record == None)
        assert(dot_record.rock_ridge.dr_entries.pn_record == None)
        assert(dot_record.rock_ridge.dr_entries.sl_records == [])
        assert(dot_record.rock_ridge.dr_entries.nm_records == [])
        assert(dot_record.rock_ridge.dr_entries.cl_record == None)
        assert(dot_record.rock_ridge.dr_entries.pl_record == None)
        assert(dot_record.rock_ridge.dr_entries.tf_record != None)
        assert(dot_record.rock_ridge.dr_entries.tf_record.creation_time == None)
        assert(type(dot_record.rock_ridge.dr_entries.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.dr_entries.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.dr_entries.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(dot_record.rock_ridge.dr_entries.tf_record.backup_time == None)
        assert(dot_record.rock_ridge.dr_entries.tf_record.expiration_time == None)
        assert(dot_record.rock_ridge.dr_entries.tf_record.effective_time == None)
        assert(dot_record.rock_ridge.dr_entries.sf_record == None)
        assert(dot_record.rock_ridge.dr_entries.re_record == None)

def internal_check_dotdot_dir_record(dotdot_record, rr, rr_nlinks, xa, rr_onetwelve=False):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == b"\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34 with no extensions.
    if rr:
        if rr_onetwelve:
            expected_dr_len = 104
        else:
            expected_dr_len = 102
    else:
        expected_dr_len = 34

    if xa:
        expected_dr_len += 14

    assert(dotdot_record.dr_len == expected_dr_len)
    # The "dotdot" directory record is not the root.
    assert(dotdot_record.is_root == False)
    # The "dotdot" directory record should have no children.
    assert(len(dotdot_record.children) == 0)
    assert(dotdot_record.file_flags == 2)

    if rr:
        assert(dotdot_record.rock_ridge._initialized == True)
        assert(dotdot_record.rock_ridge.dr_entries.sp_record == None)
        if not rr_onetwelve:
            assert(dotdot_record.rock_ridge.dr_entries.rr_record != None)
            assert(dotdot_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x81)
        assert(dotdot_record.rock_ridge.dr_entries.ce_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.px_record != None)
        assert(dotdot_record.rock_ridge.dr_entries.px_record.posix_file_mode == 0o040555)
        assert(dotdot_record.rock_ridge.dr_entries.px_record.posix_file_links == rr_nlinks)
        assert(dotdot_record.rock_ridge.dr_entries.px_record.posix_user_id == 0)
        assert(dotdot_record.rock_ridge.dr_entries.px_record.posix_group_id == 0)
        assert(dotdot_record.rock_ridge.dr_entries.px_record.posix_serial_number == 0)
        assert(dotdot_record.rock_ridge.dr_entries.er_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.es_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.pn_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.sl_records == [])
        assert(dotdot_record.rock_ridge.dr_entries.nm_records == [])
        assert(dotdot_record.rock_ridge.dr_entries.cl_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.pl_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.tf_record != None)
        assert(dotdot_record.rock_ridge.dr_entries.tf_record.creation_time == None)
        assert(type(dotdot_record.rock_ridge.dr_entries.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.dr_entries.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.dr_entries.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(dotdot_record.rock_ridge.dr_entries.tf_record.backup_time == None)
        assert(dotdot_record.rock_ridge.dr_entries.tf_record.expiration_time == None)
        assert(dotdot_record.rock_ridge.dr_entries.tf_record.effective_time == None)
        assert(dotdot_record.rock_ridge.dr_entries.sf_record == None)
        assert(dotdot_record.rock_ridge.dr_entries.re_record == None)

def internal_check_file_contents(iso, path, contents, which='iso_path'):
    fout = BytesIO()
    if which == 'iso_path':
        iso.get_file_from_iso_fp(fout, iso_path=path)
    elif which == 'rr_path':
        iso.get_file_from_iso_fp(fout, rr_path=path)
    elif which == 'joliet_path':
        iso.get_file_from_iso_fp(fout, joliet_path=path)
    elif which == 'udf_path':
        iso.get_file_from_iso_fp(fout, udf_path=path)
    else:
        assert('' == 'Invalid Test parameter')
    assert(fout.getvalue() == contents)

def internal_check_ptr(ptr, name, len_di, loc, parent):
    assert(ptr.len_di == len_di)
    assert(ptr.xattr_length == 0)
    if loc is not None:
        assert(ptr.extent_location == loc)
    if parent > 0:
        assert(ptr.parent_directory_num == parent)
    assert(ptr.directory_identifier == name)

def internal_check_empty_directory(dirrecord, name, dr_len, extent=None,
                                   rr=False, hidden=False):
    internal_check_dir_record(dirrecord, 2, name, dr_len, extent, rr, b'dir1', 2, False, hidden)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr, 3, False)

def internal_check_file(dirrecord, name, dr_len, loc, datalen, hidden, num_linked_records):
    assert(len(dirrecord.children) == 0)
    assert(dirrecord.isdir == False)
    assert(dirrecord.is_root == False)
    assert(dirrecord.file_ident == name)
    if dr_len is not None:
        assert(dirrecord.dr_len == dr_len)
    if loc is not None:
        assert(dirrecord.extent_location() == loc)
    if hidden:
        assert(dirrecord.file_flags == 1)
    else:
        assert(dirrecord.file_flags == 0)
    assert(dirrecord.file_length() == datalen)
    assert(len(dirrecord.linked_records) == num_linked_records)

def internal_generate_inorder_names(numdirs):
    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append(b"DIR" + bytes(str(i).encode('ascii')))
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    return names

def internal_generate_joliet_inorder_names(numdirs):
    tmp = []
    for i in range(1, 1+numdirs):
        name = "dir" + str(i)
        tmp.append(bytes(name.encode('utf-16_be')))
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    return names

def internal_check_dir_record(dir_record, num_children, name, dr_len,
                              extent_location, rr, rr_name, rr_links, xa, hidden=False,
                              is_cl_record=False, datalen=2048, relocated=False):
    # The directory should have the number of children passed in.
    assert(len(dir_record.children) == num_children)
    # The directory should be a directory.
    if is_cl_record:
        assert(dir_record.isdir == False)
    else:
        assert(dir_record.isdir == True)
    # The directory should not be the root.
    assert(dir_record.is_root == False)
    # The directory should have an ISO9660 mangled name the same as passed in.
    assert(dir_record.file_ident == name)
    # The directory record should have a dr_len as passed in.
    if dr_len is not None:
        assert(dir_record.dr_len == dr_len)
    # The "dir1" directory record should be at the extent passed in.
    if extent_location is not None:
        assert(dir_record.extent_location() == extent_location)
    if is_cl_record:
        assert(dir_record.file_flags == 0)
    else:
        if hidden:
            assert(dir_record.file_flags == 3)
        else:
            assert(dir_record.file_flags == 2)

    if rr:
        assert(dir_record.rock_ridge.dr_entries.sp_record == None)
        assert(dir_record.rock_ridge.dr_entries.rr_record != None)
        if is_cl_record:
            assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x99)
        elif relocated:
            assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0xC9)
        else:
            assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x89)

        px_record = None
        if dir_record.rock_ridge.dr_entries.px_record is not None:
            px_record = dir_record.rock_ridge.dr_entries.px_record
        elif dir_record.rock_ridge.ce_entries.px_record is not None:
            px_record = dir_record.rock_ridge.ce_entries.px_record
        assert(px_record is not None)
        assert(px_record.posix_file_mode == 0o040555)
        assert(px_record.posix_file_links == rr_links)
        assert(px_record.posix_user_id == 0)
        assert(px_record.posix_group_id == 0)
        assert(px_record.posix_serial_number == 0)
        assert(dir_record.rock_ridge.dr_entries.er_record == None)
        assert(dir_record.rock_ridge.dr_entries.es_record == None)
        assert(dir_record.rock_ridge.dr_entries.pn_record == None)
        assert(dir_record.rock_ridge.dr_entries.sl_records == [])
        assert(len(dir_record.rock_ridge.dr_entries.nm_records) > 0)
        assert(dir_record.rock_ridge.name() == rr_name)
        if is_cl_record:
            assert(dir_record.rock_ridge.dr_entries.cl_record != None)
        else:
            assert(dir_record.rock_ridge.dr_entries.cl_record == None)
        assert(dir_record.rock_ridge.dr_entries.pl_record == None)
        if dir_record.rock_ridge.dr_entries.tf_record is not None:
            tf_record = dir_record.rock_ridge.dr_entries.tf_record
        elif dir_record.rock_ridge.ce_entries.tf_record is not None:
            tf_record = dir_record.rock_ridge.ce_entries.tf_record
        assert(tf_record is not None)
        assert(tf_record.creation_time == None)
        assert(type(tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(tf_record.backup_time == None)
        assert(tf_record.expiration_time == None)
        assert(tf_record.effective_time == None)
        assert(dir_record.rock_ridge.dr_entries.sf_record == None)
        if relocated:
            assert(dir_record.rock_ridge.dr_entries.re_record != None)
        else:
            assert(dir_record.rock_ridge.dr_entries.re_record == None)

    # The "dir1" directory record should have a valid "dot" record.
    if num_children > 0:
        internal_check_dot_dir_record(dir_record.children[0], rr, rr_links, False, xa, datalen)

def internal_check_joliet_root_dir_record(jroot_dir_record, num_children,
                                          data_length, extent_location):
    # The jroot_dir_record directory record length should be exactly 34.
    assert(jroot_dir_record.dr_len == 34)
    # We don't support xattrs at the moment, so it should always be 0.
    assert(jroot_dir_record.xattr_len == 0)
    # Make sure the root directory record starts at the extent we expect.
    assert(jroot_dir_record.extent_location() == extent_location)

    # We don't check the extent_location_le or extent_location_be, since I
    # don't really understand the algorithm by which genisoimage generates them.

    # The length of the root directory record depends on the number of entries
    # there are at the top level.
    assert(jroot_dir_record.file_length() == data_length)

    # We skip checking the date since it changes all of the time.

    # The file flags for the root dir record should always be 0x2 (DIRECTORY bit).
    assert(jroot_dir_record.file_flags == 2)
    # The file unit size should always be zero.
    assert(jroot_dir_record.file_unit_size == 0)
    # The interleave gap size should always be zero.
    assert(jroot_dir_record.interleave_gap_size == 0)
    # The sequence number should always be one.
    assert(jroot_dir_record.seqnum == 1)
    # The len_fi should always be one.
    assert(jroot_dir_record.len_fi == 1)

    # Everything after here is derived data.

    # The root directory should be the, erm, root.
    assert(jroot_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(jroot_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(jroot_dir_record.file_ident == b"\x00")
    assert(jroot_dir_record.parent == None)
    assert(jroot_dir_record.rock_ridge == None)
    # The number of children the root directory record has depends on the number
    # of files+directories there are at the top level.
    assert(len(jroot_dir_record.children) == num_children)

    # Now check the "dot" directory record.
    internal_check_dot_dir_record(jroot_dir_record.children[0], False, 0, False, False)

    # Now check the "dotdot" directory record.
    internal_check_dotdot_dir_record(jroot_dir_record.children[1], False, 0, False)

def internal_check_rr_longname(iso, dir_record, extent, letter, num_linked_records):
    internal_check_file(dir_record, letter.upper()*8+b".;1", None, extent, 3, hidden=False, num_linked_records=num_linked_records)
    internal_check_file_contents(iso, b"/"+letter.upper()*8+b".;1", letter*2+b"\n")
    # Now check rock ridge extensions.
    assert(dir_record.rock_ridge.dr_entries.sp_record == None)
    assert(dir_record.rock_ridge.dr_entries.rr_record != None)
    assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x89)
    assert(dir_record.rock_ridge.dr_entries.ce_record != None)
    assert(dir_record.rock_ridge.ce_entries.sp_record == None)
    assert(dir_record.rock_ridge.ce_entries.rr_record == None)
    assert(dir_record.rock_ridge.ce_entries.ce_record == None)
    assert(dir_record.rock_ridge.ce_entries.px_record != None)
    assert(dir_record.rock_ridge.ce_entries.px_record.posix_file_mode == 0o0100444)
    assert(dir_record.rock_ridge.ce_entries.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.ce_entries.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.ce_entries.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.ce_entries.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.ce_entries.er_record == None)
    assert(dir_record.rock_ridge.ce_entries.es_record == None)
    assert(dir_record.rock_ridge.ce_entries.pn_record == None)
    assert(dir_record.rock_ridge.ce_entries.sl_records == [])
    assert(len(dir_record.rock_ridge.ce_entries.nm_records) > 0)
    assert(dir_record.rock_ridge.ce_entries.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.ce_entries.cl_record == None)
    assert(dir_record.rock_ridge.ce_entries.pl_record == None)
    assert(dir_record.rock_ridge.ce_entries.tf_record != None)
    assert(type(dir_record.rock_ridge.ce_entries.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.ce_entries.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.ce_entries.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(dir_record.rock_ridge.ce_entries.sf_record == None)
    assert(dir_record.rock_ridge.ce_entries.re_record == None)
    assert(dir_record.rock_ridge.dr_entries.px_record == None)
    assert(dir_record.rock_ridge.dr_entries.er_record == None)
    assert(dir_record.rock_ridge.dr_entries.es_record == None)
    assert(dir_record.rock_ridge.dr_entries.pn_record == None)
    assert(dir_record.rock_ridge.dr_entries.sl_records == [])
    assert(len(dir_record.rock_ridge.dr_entries.nm_records) > 0)
    assert(dir_record.rock_ridge.dr_entries.nm_records[0].posix_name_flags == 1)
    assert(dir_record.rock_ridge.name() == letter*RR_MAX_FILENAME_LENGTH)
    assert(dir_record.rock_ridge.dr_entries.cl_record == None)
    assert(dir_record.rock_ridge.dr_entries.pl_record == None)
    assert(dir_record.rock_ridge.dr_entries.tf_record == None)
    assert(dir_record.rock_ridge.dr_entries.sf_record == None)
    assert(dir_record.rock_ridge.dr_entries.re_record == None)
    internal_check_file_contents(iso, b"/"+letter*RR_MAX_FILENAME_LENGTH, letter*2+b"\n", which='rr_path')

def internal_check_rr_file(dir_record, name):
    assert(dir_record.rock_ridge._initialized == True)
    assert(dir_record.rock_ridge.dr_entries.sp_record == None)
    assert(dir_record.rock_ridge.dr_entries.rr_record != None)
    assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x89)
    assert(dir_record.rock_ridge.dr_entries.ce_record == None)
    assert(dir_record.rock_ridge.dr_entries.px_record != None)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_file_mode == 0o0100444)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.dr_entries.er_record == None)
    assert(dir_record.rock_ridge.dr_entries.es_record == None)
    assert(dir_record.rock_ridge.dr_entries.pn_record == None)
    assert(dir_record.rock_ridge.dr_entries.sl_records == [])
    assert(len(dir_record.rock_ridge.dr_entries.nm_records) > 0)
    assert(dir_record.rock_ridge.dr_entries.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.dr_entries.nm_records[0].posix_name == name)
    assert(dir_record.rock_ridge.dr_entries.cl_record == None)
    assert(dir_record.rock_ridge.dr_entries.pl_record == None)
    assert(dir_record.rock_ridge.dr_entries.tf_record != None)
    assert(dir_record.rock_ridge.dr_entries.tf_record.creation_time == None)
    assert(type(dir_record.rock_ridge.dr_entries.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.dr_entries.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.dr_entries.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(dir_record.rock_ridge.dr_entries.tf_record.backup_time == None)
    assert(dir_record.rock_ridge.dr_entries.tf_record.expiration_time == None)
    assert(dir_record.rock_ridge.dr_entries.tf_record.effective_time == None)
    assert(dir_record.rock_ridge.dr_entries.sf_record == None)
    assert(dir_record.rock_ridge.dr_entries.re_record == None)

def internal_check_rr_symlink(dir_record, name, dr_len, extent, comps):
    # The "sym" file should not have any children.
    assert(len(dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(dir_record.file_ident == name)
    # The "sym" directory record should have a length of 126.
    assert(dir_record.dr_len == dr_len)
    # The "sym" data should start at extent 26.
    assert(dir_record.extent_location() == extent)
    assert(dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(dir_record.rock_ridge._initialized == True)
    assert(dir_record.rock_ridge.dr_entries.sp_record == None)
    assert(dir_record.rock_ridge.dr_entries.rr_record != None)
    assert(dir_record.rock_ridge.dr_entries.rr_record.rr_flags == 0x8d)
    assert(dir_record.rock_ridge.dr_entries.px_record != None)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_file_mode == 0o0120555)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.dr_entries.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.dr_entries.er_record == None)
    assert(dir_record.rock_ridge.dr_entries.es_record == None)
    assert(dir_record.rock_ridge.dr_entries.pn_record == None)
    assert(dir_record.rock_ridge.is_symlink() == True)
    split = dir_record.rock_ridge.symlink_path().split(b'/')
    assert(len(split) == len(comps))
    for index,comp in enumerate(comps):
        assert(comps[index] == split[index])
    assert(len(dir_record.rock_ridge.dr_entries.nm_records) > 0)
    assert(dir_record.rock_ridge.dr_entries.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.dr_entries.nm_records[0].posix_name == b'sym')
    assert(dir_record.rock_ridge.dr_entries.cl_record == None)
    assert(dir_record.rock_ridge.dr_entries.pl_record == None)
    tf_record = None
    if dir_record.rock_ridge.dr_entries.tf_record is not None:
        tf_record = dir_record.rock_ridge.dr_entries.tf_record
    elif dir_record.rock_ridge.ce_entries.tf_record is not None:
        tf_record = dir_record.rock_ridge.ce_entries.tf_record
    assert(tf_record != None)
    assert(tf_record.creation_time == None)
    assert(type(tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(tf_record.backup_time == None)
    assert(tf_record.expiration_time == None)
    assert(tf_record.effective_time == None)
    assert(dir_record.rock_ridge.dr_entries.sf_record == None)
    assert(dir_record.rock_ridge.dr_entries.re_record == None)

def internal_check_udf_tag(tag, ident, location):
    assert(tag.tag_ident == ident)
    assert(tag.desc_version == 2)
    assert(tag.tag_serial_number == 0)
    if location is not None:
        assert(tag.tag_location == location)

def internal_check_udf_anchor(anchor, location):
    assert(anchor.extent_location() == location)
    internal_check_udf_tag(anchor.udf_tag, 2, location)
    assert(anchor.main_vd_length == 32768)
    assert(anchor.main_vd_extent == 32)
    assert(anchor.reserve_vd_length == 32768)
    assert(anchor.reserve_vd_extent == 48)

def internal_check_udf_entity(entity, flags, ident, suffix):
    assert(entity.flags == flags)
    if ident is not None:
        full = ident + b'\x00' * (23 - len(ident))
        assert(entity.identifier == full)
    full = suffix + b'\x00' * (8 - len(suffix))
    assert(entity.suffix == full)

def internal_check_udf_pvd(pvd, location):
    assert(pvd.extent_location() == location)
    internal_check_udf_tag(pvd.desc_tag, 1, location)
    assert(pvd.vol_desc_seqnum == 0)
    assert(pvd.desc_num == 0)
    assert(pvd.vol_ident == b'\x08CDROM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06')
    assert(pvd.desc_char_set == b'\x00OSTA Compressed Unicode\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(pvd.explanatory_char_set == b'\x00OSTA Compressed Unicode\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(pvd.vol_abstract_length == 0)
    assert(pvd.vol_abstract_extent == 0)
    assert(pvd.vol_copyright_length == 0)
    assert(pvd.vol_copyright_extent == 0)
    internal_check_udf_entity(pvd.app_ident, 0, b'\x00', b'')
    internal_check_udf_entity(pvd.impl_ident, 0, b'*genisoimage', b'')
    assert(pvd.implementation_use == b'\x00' * 64)
    assert(pvd.predecessor_vol_desc_location == 0)

def internal_check_udf_impl_use(impl_use, location):
    assert(impl_use.extent_location() == location)
    internal_check_udf_tag(impl_use.desc_tag, 4, location)
    assert(impl_use.vol_desc_seqnum == 1)
    assert(impl_use.impl_ident.identifier == b'*UDF LV Info\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(impl_use.impl_use.char_set == b'\x00OSTA Compressed Unicode' + b'\x00' * 40)
    assert(impl_use.impl_use.log_vol_ident == b'\x08CDROM' + b'\x00' * 121 + b'\x06')
    assert(impl_use.impl_use.lv_info1 == b'\x00' * 36)
    assert(impl_use.impl_use.lv_info2 == b'\x00' * 36)
    assert(impl_use.impl_use.lv_info3 == b'\x00' * 36)
    internal_check_udf_entity(impl_use.impl_ident, 0, b'*UDF LV Info', b'\x02\x01')
    assert(impl_use.impl_use.impl_use == b'\x00' * 128)

def internal_check_udf_partition(partition, location, length):
    assert(partition.extent_location() == location)
    internal_check_udf_tag(partition.desc_tag, 5, location)
    assert(partition.vol_desc_seqnum == 2)
    assert(partition.part_flags == 1)
    assert(partition.part_num == 0)
    assert(partition.part_contents.flags == 2)
    internal_check_udf_entity(partition.part_contents, 2, b'+NSR02', b'')
    assert(partition.access_type == 1)
    assert(partition.part_start_location == 257)
    assert(partition.part_length == length)
    internal_check_udf_entity(partition.impl_ident, 0, None, b'')
    assert(partition.implementation_use == b'\x00' * 128)

def internal_check_udf_longad(longad, size, blocknum, abs_blocknum):
    assert(longad.extent_length == size)
    if blocknum is not None:
        assert(longad.log_block_num == blocknum)
    assert(longad.part_ref_num == 0)
    if abs_blocknum is not None:
        assert(longad.impl_use == b'\x00\x00' + struct.pack("=L", abs_blocknum))

def internal_check_udf_logical_volume(lv, location):
    assert(lv.extent_location() == location)
    internal_check_udf_tag(lv.desc_tag, 6, location)
    assert(lv.vol_desc_seqnum == 3)
    assert(lv.desc_char_set == b'\x00OSTA Compressed Unicode\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    assert(lv.logical_vol_ident == b'\x08CDROM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06')
    internal_check_udf_entity(lv.domain_ident, 0, b'*OSTA UDF Compliant', b'\x02\x01\x03')
    internal_check_udf_longad(lv.logical_volume_contents_use, 4096, 0, 0)
    internal_check_udf_entity(lv.impl_ident, 0, None, b'')
    assert(lv.implementation_use == b'\x00' * 128)
    assert(lv.integrity_sequence_length == 4096)
    assert(lv.integrity_sequence_extent == 64)

def internal_check_udf_unallocated_space(unallocated_space, location):
    assert(unallocated_space.extent_location() == location)
    internal_check_udf_tag(unallocated_space.desc_tag, 7, location)
    assert(unallocated_space.vol_desc_seqnum == 4)

def internal_check_udf_terminator(terminator, location, tagloc):
    assert(terminator.extent_location() == location)
    internal_check_udf_tag(terminator.desc_tag, 8, tagloc)

def internal_check_udf_headers(iso, end_anchor_extent, part_length, unique_id, num_dirs, num_files):
    assert(iso.udf_bea is not None)
    assert(iso.udf_bea.extent_location() == 18)
    assert(iso.udf_nsr is not None)
    assert(iso.udf_nsr.extent_location() == 19)
    assert(iso.udf_tea is not None)
    assert(iso.udf_tea.extent_location() == 20)

    assert(len(iso.udf_anchors) == 2)
    internal_check_udf_anchor(iso.udf_anchors[0], 256)
    internal_check_udf_anchor(iso.udf_anchors[1], end_anchor_extent)

    internal_check_udf_pvd(iso.udf_pvd, 32)

    internal_check_udf_impl_use(iso.udf_impl_use, 33)

    internal_check_udf_partition(iso.udf_partition, 34, part_length)

    internal_check_udf_logical_volume(iso.udf_logical_volume, 35)

    internal_check_udf_unallocated_space(iso.udf_unallocated_space, 36)

    internal_check_udf_terminator(iso.udf_terminator, 37, 37)

    internal_check_udf_pvd(iso.udf_reserve_pvd, 48)

    internal_check_udf_impl_use(iso.udf_reserve_impl_use, 49)

    internal_check_udf_partition(iso.udf_reserve_partition, 50, part_length)

    internal_check_udf_logical_volume(iso.udf_reserve_logical_volume, 51)

    internal_check_udf_unallocated_space(iso.udf_reserve_unallocated_space, 52)

    internal_check_udf_terminator(iso.udf_reserve_terminator, 53, 53)

    assert(iso.udf_logical_volume_integrity.extent_location() == 64)
    internal_check_udf_tag(iso.udf_logical_volume_integrity.desc_tag, 9, 64)
    assert(iso.udf_logical_volume_integrity.logical_volume_contents_use.unique_id == unique_id)
    assert(iso.udf_logical_volume_integrity.length_impl_use == 46)
    assert(iso.udf_logical_volume_integrity.free_space_table == 0)
    assert(iso.udf_logical_volume_integrity.size_table == part_length)
    internal_check_udf_entity(iso.udf_logical_volume_integrity.logical_volume_impl_use.impl_id, 0, None, b'')
    assert(iso.udf_logical_volume_integrity.logical_volume_impl_use.num_files == num_files)
    assert(iso.udf_logical_volume_integrity.logical_volume_impl_use.num_dirs == num_dirs)
    assert(iso.udf_logical_volume_integrity.logical_volume_impl_use.min_udf_read_revision == 258)
    assert(iso.udf_logical_volume_integrity.logical_volume_impl_use.min_udf_write_revision == 258)
    assert(iso.udf_logical_volume_integrity.logical_volume_impl_use.max_udf_write_revision == 258)

    internal_check_udf_terminator(iso.udf_logical_volume_integrity_terminator, 65, 65)

    internal_check_udf_tag(iso.udf_file_set.desc_tag, 256, 0)
    internal_check_udf_entity(iso.udf_file_set.domain_ident, 0, b"*OSTA UDF Compliant", b"\x02\x01\x03")
    internal_check_udf_longad(iso.udf_file_set.root_dir_icb, 2048, 2, 0)

    internal_check_udf_terminator(iso.udf_file_set_terminator, 258, 1)

def internal_check_udf_file_entry(file_entry, location, tag_location, num_links, info_len, num_fi_descs, isdir):
    if location is not None:
        assert(file_entry.extent_location() == location)
    internal_check_udf_tag(file_entry.desc_tag, 261, tag_location)
    assert(file_entry.icb_tag.prior_num_direct_entries == 0)
    assert(file_entry.icb_tag.strategy_type == 4)
    assert(file_entry.icb_tag.strategy_param == 0)
    assert(file_entry.icb_tag.max_num_entries == 1)
    if isdir:
        assert(file_entry.icb_tag.file_type == 4)
    else:
        assert(file_entry.icb_tag.file_type == 5)
    assert(file_entry.icb_tag.parent_icb_log_block_num == 0)
    assert(file_entry.icb_tag.parent_icb_part_ref_num == 0)
    assert(file_entry.icb_tag.flags == 560)
    assert(file_entry.uid == 4294967295)
    assert(file_entry.gid == 4294967295)
    if isdir:
        assert(file_entry.perms == 5285)
    else:
        assert(file_entry.perms == 4228)
    assert(file_entry.file_link_count == num_links)
    assert(file_entry.info_len == info_len)
    assert(file_entry.log_block_recorded == 1)
    internal_check_udf_longad(file_entry.extended_attr_icb, 0, 0, 0)
    internal_check_udf_entity(file_entry.impl_ident, 0, b"*genisoimage", b"")
    assert(file_entry.extended_attrs == b"")
    assert(len(file_entry.alloc_descs) == 1)
    assert(len(file_entry.fi_descs) == num_fi_descs)

def internal_check_udf_file_ident_desc(fi_desc, extent, tag_location, characteristics, blocknum, abs_blocknum, name, isparent, isdir):
    if extent is not None:
        assert(fi_desc.extent_location() == extent)
    internal_check_udf_tag(fi_desc.desc_tag, 257, tag_location)
    assert(fi_desc.file_characteristics == characteristics)
    namelen = len(name)
    if namelen > 0:
        namelen += 1
    assert(fi_desc.len_fi == namelen)
    internal_check_udf_longad(fi_desc.icb, 2048, blocknum, abs_blocknum)
    assert(fi_desc.len_impl_use == 0)
    assert(fi_desc.impl_use == b"")
    assert(fi_desc.fi == name)
    if isparent:
        assert(fi_desc.file_entry is None)
    else:
        assert(fi_desc.file_entry is not None)
    assert(fi_desc.isdir == isdir)
    assert(fi_desc.isparent == isparent)

######################## EXTERNAL CHECKERS #####################################
def check_nofiles(iso, filesize):
    assert(filesize == 49152)

    internal_check_pvd(iso.pvd, extent=16, size=24, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        iso.get_file_from_iso_fp(BytesIO(), iso_path="/FOO.;1")

def check_onefile(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 24, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_onedir(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the one empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 24)

def check_twofiles(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the first file.  It should have a name of BAR.;1, it should
    # have a directory record length of 40, it should start at extent 24,
    # and its contents should be "bar\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

    # Now check the second file.  It should have a name of FOO.;1, it should
    # have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_twodirs(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=30, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    aa_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(aa_record.ptr, name=b'AA', len_di=2, loc=None, parent=1)
    # Now check the first empty directory.  Its name should be AA, and it should
    # start at extent 24.
    internal_check_empty_directory(aa_record, b"AA", 36, None)

    bb_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(bb_record.ptr, name=b'BB', len_di=2, loc=None, parent=1)
    # Now check the second empty directory.  Its name should be BB, and it
    # should start at extent 25.
    internal_check_empty_directory(bb_record, b"BB", 36, None)

def check_onefileonedir(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 24)

    # Now check the file.  It should have a name of FOO.;1, it should
    # have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

def check_onefile_onedirwithfile(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the file within it), the name should be DIR1, and it should start
    # at extent 24.
    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    internal_check_dir_record(dir1_record, 3, b"DIR1", 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    # Now check the file at the root.  It should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the file in the subdirectory.  It should have a name of BAR.;1,
    # it should have a directory record length of 40, it should start at
    # extent 26, and its contents should be "bar\n".
    internal_check_file(dir1_record.children[2], b"BAR.;1", 40, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", b"bar\n")

def check_twoextentfile(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file at the root.  It should have a name of BIGFILE.;1, it
    # should have a directory record length of 44, it should start at extent 24,
    # and its contents should be the bytes 0x0-0xff, repeating 8 times plus one.
    outstr = b""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BIGFILE.;1", 44, 24, 2049, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BIGFILE.;1", outstr)

def check_twoleveldeepdir(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=38, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the subdirectory), the name should be DIR1, and it should start
    # at extent 24.
    internal_check_dir_record(dir1_record, 3, b'DIR1', 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    subdir1_record = dir1_record.children[2]
    internal_check_ptr(subdir1_record.ptr, name=b'SUBDIR1', len_di=7, loc=25, parent=2)
    # Now check the empty subdirectory record.  The name should be SUBDIR1.
    internal_check_empty_directory(subdir1_record, b'SUBDIR1', 40, 25)

def check_tendirs(iso, filesize):
    assert(filesize == 69632)

    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=132, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=12, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(10)
    for index in range(2, 2+10):
        dir_record = iso.pvd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

        internal_check_empty_directory(dir_record, names[index], 38)

def check_dirs_overflow_ptr_extent(iso, filesize):
    assert(filesize == 671744)

    internal_check_pvd(iso.pvd, extent=16, size=328, ptbl_size=4122, ptbl_location_le=19, ptbl_location_be=23)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=297, data_length=12288, extent_location=27, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=27, parent=1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(295)
    for index in range(2, 2+295):
        dir_record = iso.pvd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

        internal_check_empty_directory(dir_record, names[index], 33 + len(names[index]) + (1 - (len(names[index]) % 2)))

def check_dirs_just_short_ptr_extent(iso, filesize):
    assert(filesize == 659456)

    internal_check_pvd(iso.pvd, extent=16, size=322, ptbl_size=4094, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=295, data_length=12288, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(293)
    for index in range(2, 2+293):
        dir_record = iso.pvd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

        internal_check_empty_directory(dir_record, names[index], 33 + len(names[index]) + (1 - (len(names[index]) % 2)))

def check_twoleveldeepfile(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=38, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the subdirectory), the name should be DIR1, and it should start
    # at extent 24.
    internal_check_dir_record(dir1_record, 3, b'DIR1', 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    subdir1_record = dir1_record.children[2]
    internal_check_ptr(subdir1_record.ptr, name=b'SUBDIR1', len_di=7, loc=25, parent=2)
    # Now check the sub-directory record.  It should have 3 children (dot,
    # dotdot, and the subdirectory), the name should be DIR1, and it should
    # start at extent 25.
    internal_check_dir_record(subdir1_record, 3, b'SUBDIR1', 40, 25, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(subdir1_record.children[1], False, 3, False)

    # Now check the file in the subdirectory.  It should have a name of FOO.;1,
    # it should have a directory record length of 40, it should start at
    # extent 26, and its contents should be "foo\n".
    internal_check_file(subdir1_record.children[2], b"FOO.;1", 40, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/DIR1/SUBDIR1/FOO.;1", b"foo\n")

def check_joliet_nofiles(iso, filesize):
    assert(filesize == 61440)

    internal_check_pvd(iso.pvd, extent=16, size=30, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 30, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_joliet_onedir(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # directory, the number of extents should be the same as the PVD, the path
    # table should be 26 bytes (10 bytes for the root directory entry, and 16
    # bytes for the directory), the little endian path table should start at
    # extent 24, and the big endian path table should start at extent 26 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 26, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=29, parent=1)
    # Now check the empty subdirectory record.  The name should be DIR1, and
    # it should start at extent 29.
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 29)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the directory), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 30 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=31, parent=1)
    # Now check the empty Joliet subdirectory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(joliet_dir1_record, "dir1".encode('utf-16_be'), 42, 31)

def check_joliet_onefile(iso, filesize):
    assert(filesize == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 30, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n", 'iso_path')

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 30, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", 'joliet_path')

def check_joliet_onefileonedir(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file and one directory, the number of extents should be the same as the
    # PVD, the path table should be 26 bytes (10 bytes for the root directory
    # entry and 16 bytes for the directory), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 26, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=29, parent=1)
    # Now check the empty directory record.  The name should be DIR1, and it
    # should start at extent 29.
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 29)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=31, parent=1)
    # Now check the empty Joliet directory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(joliet_dir1_record, "dir1".encode('utf-16_be'), 42, 31)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 32, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n", 'iso_path')

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "foo".encode('utf-16_be'), 40, 32, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", 'joliet_path')

def check_eltorito_nofiles(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_eltorito_twofile(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[4], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.;1", 40, 26, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the aa file.  It should have a name of AA.;1, it should
    # have a directory record length of 40, it should start at extent 27, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AA.;1", 38, 27, 3, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/AA.;1", b"aa\n")

def check_rr_nofiles(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

def check_rr_onefile(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

def check_rr_twofile(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the bar file.  It should have a name of BAR.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "bar\n".
    bar_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(bar_dir_record, b"BAR.;1", 116, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # bar, and contain "bar\n".
    internal_check_rr_file(bar_dir_record, b'bar')
    internal_check_file_contents(iso, "/bar", b"bar\n", which='rr_path')

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

def check_rr_onefileonedir(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the empty directory record.  The name should be DIR1, the
    # directory record length should be 114 (for the Rock Ridge), it should
    # start at extent 24, and it should have Rock Ridge.
    internal_check_empty_directory(dir1_record, b"DIR1", 114, 24, True)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

def check_rr_onefileonedirwithfile(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 24, and it should have Rock
    # Ridge.
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, 24, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

    # Now check the bar file.  It should have a name of BAR.;1, it should
    # have a directory record length of 116, it should start at extent 27, and
    # its contents should be "bar\n".
    bar_dir_record = dir1_record.children[2]
    internal_check_file(bar_dir_record, b"BAR.;1", 116, 27, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", b"bar\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # bar, and contain "bar\n".
    internal_check_rr_file(bar_dir_record, b'bar')
    internal_check_file_contents(iso, "/dir1/bar", b"bar\n", which='rr_path')

def check_rr_symlink(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 26, [b'foo'])

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        internal_check_file_contents(iso, "/sym", b"foo\n")

def check_rr_symlink2(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 24, and it should have Rock
    # Ridge.
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, 24, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = dir1_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/DIR1/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/dir1/foo", b"foo\n", which='rr_path')

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 132, 26, [b'dir1', b'foo'])

def check_rr_symlink_dot(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 122, 25, [b'.'])

def check_rr_symlink_dotdot(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 122, 25, [b'..'])

def check_rr_symlink_broken(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 25, [b'foo'])

def check_alternating_subdir(iso, filesize):
    assert(filesize == 61440)

    internal_check_pvd(iso.pvd, extent=16, size=30, ptbl_size=30, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=6, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    aa_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(aa_record.ptr, name=b'AA', len_di=2, loc=None, parent=1)
    # Now check the directory record.  The number of children should be 3,
    # the name should be AA, the directory record length should be 36 (for
    # the Rock Ridge), it should start at extent 24, and it should not have Rock
    # Ridge.
    internal_check_dir_record(aa_record, 3, b"AA", 36, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(aa_record.children[1], False, 3, False)

    # Now check the BB file.  It should have a name of BB.;1, it should have a
    # directory record length of 38, it should start at extent 26, and its
    # contents should be "bb\n".
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(bb_dir_record, b"BB.;1", 38, 26, 3, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BB.;1", b"bb\n")

    cc_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(cc_record.ptr, name=b'CC', len_di=2, loc=None, parent=1)
    # Now check the directory record.  The number of children should be 3,
    # the name should be CC, the directory record length should be 36 (for
    # the Rock Ridge), it should start at extent 25, and it should not have Rock
    # Ridge.
    internal_check_dir_record(cc_record, 3, b"CC", 36, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(cc_record.children[1], False, 3, False)

    # Now check the DD file.  It should have a name of DD.;1, it should have a
    # directory record length of 38, it should start at extent 27, and its
    # contents should be "dd\n".
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_file(dd_dir_record, b"DD.;1", 38, 27, 3, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/DD.;1", b"dd\n")

    # Now check the SUB1 file.  It should have a name of SUB1.;1, it should
    # have a directory record length of 40, it should start at extent 28, and
    # its contents should be "sub1\n".
    sub1_dir_record = aa_record.children[2]
    internal_check_file(sub1_dir_record, b"SUB1.;1", 40, None, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/AA/SUB1.;1", b"sub1\n")

    # Now check the SUB2 file.  It should have a name of SUB2.;1, it should
    # have a directory record length of 40, it should start at extent 29, and
    # its contents should be "sub1\n".
    sub2_dir_record = cc_record.children[2]
    internal_check_file(sub2_dir_record, b"SUB2.;1", 40, None, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/CC/SUB2.;1", b"sub2\n")

def check_rr_verylongname(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 26, b'a', num_linked_records=0)

def check_rr_verylongname_joliet(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 32, b'a', num_linked_records=1)

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], ("a"*64).encode('utf-16_be'), 162, 32, 3, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/"+'a'*64, b"aa\n", 'joliet_path')

def check_rr_manylongname(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=9, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_longname(iso, aa_dir_record, 26, b'a', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 27,
    # and the name should have all 'b' in it.
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_longname(iso, bb_dir_record, 27, b'b', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 28,
    # and the name should have all 'c' in it.
    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_rr_longname(iso, cc_dir_record, 28, b'c', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 29,
    # and the name should have all 'd' in it.
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_rr_longname(iso, dd_dir_record, 29, b'd', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 30,
    # and the name should have all 'e' in it.
    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_longname(iso, ee_dir_record, 30, b'e', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 31,
    # and the name should have all 'f' in it.
    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_rr_longname(iso, ff_dir_record, 31, b'f', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 32,
    # and the name should have all 'g' in it.
    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_rr_longname(iso, gg_dir_record, 32, b'g', num_linked_records=0)

def check_rr_manylongname2(iso, filesize):
    assert(filesize == 71680)

    internal_check_pvd(iso.pvd, extent=16, size=35, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=10, data_length=4096, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check out the file with a long name.  It should start at extent 27,
    # and the name should have all 'a' in it.
    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_longname(iso, aa_dir_record, 27, b'a', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 28,
    # and the name should have all 'b' in it.
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_longname(iso, bb_dir_record, 28, b'b', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 29,
    # and the name should have all 'c' in it.
    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_rr_longname(iso, cc_dir_record, 29, b'c', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 30,
    # and the name should have all 'd' in it.
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_rr_longname(iso, dd_dir_record, 30, b'd', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 31,
    # and the name should have all 'e' in it.
    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_longname(iso, ee_dir_record, 31, b'e', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 32,
    # and the name should have all 'f' in it.
    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_rr_longname(iso, ff_dir_record, 32, b'f', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 33,
    # and the name should have all 'g' in it.
    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_rr_longname(iso, gg_dir_record, 33, b'g', num_linked_records=0)

    # Now check out the file with a long name.  It should start at extent 34,
    # and the name should have all 'h' in it.
    hh_dir_record = iso.pvd.root_dir_record.children[9]
    internal_check_rr_longname(iso, hh_dir_record, 34, b'h', num_linked_records=0)

def check_rr_verylongnameandsymlink(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 26, b'a', num_linked_records=0)

def check_joliet_and_rr_nofiles(iso, filesize):
    assert(filesize == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table
    # should be 10 bytes (for the root directory entry), the little endian path
    # table should start at extent 24, and the big endian path table should
    # start at extent 26 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot" and "dotdot")
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 29 (one past the non-Joliet directory
    # record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_joliet_and_rr_onefile(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one file,
    # the number of extents should be the same as the PVD, the path table
    # should be 10 bytes (for the root directory entry), the little endian path
    # table should start at extent 24, and the big endian path table should
    # start at extent 26 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the Joliet
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # file) the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 29 (one past the non-Joliet directory
    # record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the FOO file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 31, and
    # its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 116, 31, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 31, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 31, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", which='joliet_path')

def check_joliet_and_rr_onedir(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # directory, the number of extents should be the same as the PVD, the path
    # table should be 26 bytes (10 bytes for the root directory entry and 16
    # bytes for the directory), the little endian path table should start at
    # extent 24, and the big endian path table should start at extent 26 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 26, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the directory) the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 30 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=29, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 114, 29, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=31, parent=1)
    # Now check the Joliet directory record.  The number of children should be
    # 2, the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(joliet_dir1_record, 2, "dir1".encode('utf-16_be'), 42, 31, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(joliet_dir1_record.children[1], False, 3, False)

def check_rr_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 26, and the initial entry should start at
    # extent 27.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_rr_and_eltorito_onefile(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 26, and the initial entry should start at
    # extent 27.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=24, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 28, and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 116, 28, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_rr_and_eltorito_onedir(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 27, and the initial entry should start at
    # extent 28.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 27, 28)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=24, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=25, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 114, 25, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 27.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 27, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 28, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_joliet_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 31, and the initial entry should start at
    # extent 32.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 31, 32)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 31.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 31.
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 31, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

def check_isohybrid(iso, filesize):
    assert(filesize == 1048576)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check out the isohybrid stuff.
    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)

    # Now check the boot file.  It should have a name of ISOLINUX.BIN;1, it
    # should have a directory record length of 48, and it should start at
    # extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"ISOLINUX.BIN;1", 48, 26, 68, hidden=False, num_linked_records=0)

def check_isohybrid_mac_uefi(iso, filesize):
    assert(filesize == 1048576)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, None)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=6, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check out the isohybrid stuff.
    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)

    # Now check the boot file.  It should have a name of ISOLINUX.BIN;1, it
    # should have a directory record length of 48, and it should start at
    # extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"EFIBOOT.IMG;1", 46, None, 1, hidden=False, num_linked_records=0)

def check_joliet_and_eltorito_onefile(iso, filesize):
    assert(filesize == 69632)

    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 34, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 31, and the initial entry should start at
    # extent 32.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 31, 32)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file and El Torito,
    # the Joliet root directory record should have 5 entries ("dot", "dotdot",
    # the boot catalog, the boot file, and the extra file), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 40, it should start at extent 32, and it
    # should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    # Now check the foo file.  It should have a name of FOO.;1, it should have
    # a directory record length of 40, it should start at extent 33, and it
    # should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 40, 33, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n", 'iso_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[4], "foo".encode('utf-16_be'), 40, 33, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/foo', b"foo\n", 'joliet_path')

def check_joliet_and_eltorito_onedir(iso, filesize):
    assert(filesize == 71680)

    internal_check_pvd(iso.pvd, extent=16, size=35, ptbl_size=22, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 26 bytes (10 bytes for the root directory entry and 16
    # bytes for the extra directory), the little endian path table should start
    # at extent 25, and the big endian path table should start at extent 27
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_joliet(iso.svds[0], 35, 26, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 33, and the initial entry should start at
    # extent 34.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 33, 34)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=31, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one directory and El
    # Torito, the Joliet root directory record should have 5 entries ("dot",
    # "dotdot", the boot catalog, the boot file, and the extra directory), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 31 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 31)

    dir1_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=30, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 38, it
    # should start at extent 30, and it should not have Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 38, 30, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 33.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 33, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 40, it should start at extent 34, and it
    # should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 34, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[4]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=32, parent=1)
    internal_check_dir_record(joliet_dir1_record, 2, "dir1".encode('utf-16_be'), 42, 32, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(joliet_dir1_record.children[1], False, 3, False)

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 33, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 34, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

def check_joliet_rr_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 69632)

    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On an ISO with Joliet, Rock
    # Ridge, and El Torito, the number of extents should be the same as the
    # PVD, the path table should be 10 bytes (for the root directory entry),
    # the little endian path table should start at extent 25, and the big
    # endian path table should start at extent 27 (since the little endian path
    # table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 34, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 32, and the initial entry should start at
    # extent 33.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 32, 33)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files and Joliet,
    # Rock Ridge, and El Torito, the Joliet root directory record should have 4
    # entries ("dot", "dotdot", the boot catalog, and the boot file), the data
    # length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 32.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 32, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 33, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 33, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 32, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 33, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", which='joliet_path')

def check_joliet_rr_and_eltorito_onefile(iso, filesize):
    assert(filesize == 71680)

    internal_check_pvd(iso.pvd, extent=16, size=35, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On an ISO with Joliet, Rock
    # Ridge, and El Torito, and one file, the number of extents should be the
    # same as the PVD, the path table should be 10 bytes (for the root
    # directory entry), the little endian path table should start at extent 25,
    # and the big endian path table should start at extent 27 (since the
    # little endian path table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 35, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 32, and the initial entry should start at
    # extent 33.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 32, 33)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=29, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file and Joliet,
    # Rock Ridge, and El Torito, the Joliet root directory record should have 5
    # entries ("dot", "dotdot", the boot catalog, the boot file, and the file),
    # the data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 32.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 32, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 33, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 33, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 34, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 116, 34, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 32, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 33, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", which='joliet_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[4], "foo".encode('utf-16_be'), 40, 34, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", which='joliet_path')

def check_joliet_rr_and_eltorito_onedir(iso, filesize):
    assert(filesize == 73728)

    internal_check_pvd(iso.pvd, extent=16, size=36, ptbl_size=22, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 34, and the initial entry should start at
    # extent 35.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 34, 35)

    # Do checks on the Joliet volume descriptor.  On an ISO with Joliet, Rock
    # Ridge, and El Torito, and one directory, the number of extents should
    # be the same as the PVD, the path table should be 26 bytes (10 bytes for
    # the root directory entry and 16 bytes for the directory), the little
    # endian path table should start at extent 25, and the big endian path
    # table should start at extent 27 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 36, 26, 25, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=31, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=29, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one directory and
    # Joliet, Rock Ridge, and El Torito, the Joliet root directory record
    # should have 5 entries ("dot", "dotdot", the boot catalog, the boot file,
    # and the directory), the data length is exactly one extent (2048 bytes),
    # and the root directory should start at extent 31 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 31)

    dir1_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=30, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114, it
    # should start at extent 30, and it should not have Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 114, 30, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 34, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 35, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[4]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=32, parent=1)
    internal_check_dir_record(joliet_dir1_record, 2, "dir1".encode('utf-16_be'), 42, 32, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(joliet_dir1_record.children[1], False, 3, False)

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 34, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 35, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", which='joliet_path')

def check_rr_deep_dir(iso, filesize):
    assert(filesize == 69632)

    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=122, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=None, parent=1)
    rr_moved_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(rr_moved_record.ptr, name=b'RR_MOVED', len_di=8, loc=None, parent=1)
    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=None, parent=2)
    dir8_record = rr_moved_record.children[2]
    internal_check_ptr(dir8_record.ptr, name=b'DIR8', len_di=4, loc=None, parent=3)
    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'DIR3', len_di=4, loc=None, parent=4)
    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'DIR4', len_di=4, loc=None, parent=6)
    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'DIR5', len_di=4, loc=None, parent=7)
    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'DIR6', len_di=4, loc=None, parent=8)
    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'DIR7', len_di=4, loc=None, parent=9)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

def check_rr_deep(iso, filesize):
    assert(filesize == 71680)

    internal_check_pvd(iso.pvd, extent=16, size=35, ptbl_size=122, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/foo", b"foo\n", which='rr_path')

def check_rr_deep2(iso, filesize):
    assert(filesize == 73728)

    internal_check_pvd(iso.pvd, extent=16, size=36, ptbl_size=134, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/foo", b"foo\n", which='rr_path')

def check_xa_nofiles(iso, filesize):
    assert(filesize == 49152)

    internal_check_pvd(iso.pvd, extent=16, size=24, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

def check_xa_onefile(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 54, 24, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

def check_xa_onedir(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 52, 24, False, None, 0, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, True)

def check_sevendeepdirs(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=94, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the first directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 38, it
    # should start at extent 24, and it should not have Rock Ridge.
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, 24, True, b"dir1", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=25, parent=2)
    # Now check the second directory record.  The number of children should be
    # 3, the name should be DIR2, the directory record length should be 38, it
    # should start at extent 25, and it should not have Rock Ridge.
    internal_check_dir_record(dir2_record, 3, b"DIR2", 114, 25, True, b"dir2", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_record.children[1], True, 3, False)

    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'DIR3', len_di=4, loc=26, parent=3)
    # Now check the third directory record.  The number of children should be
    # 3, the name should be DIR3, the directory record length should be 38, it
    # should start at extent 26, and it should not have Rock Ridge.
    internal_check_dir_record(dir3_record, 3, b"DIR3", 114, 26, True, b"dir3", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir3_record.children[1], True, 3, False)

    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'DIR4', len_di=4, loc=27, parent=4)
    # Now check the fourth directory record.  The number of children should be
    # 3, the name should be DIR4, the directory record length should be 38, it
    # should start at extent 27, and it should not have Rock Ridge.
    internal_check_dir_record(dir4_record, 3, b"DIR4", 114, 27, True, b"dir4", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir4_record.children[1], True, 3, False)

    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'DIR5', len_di=4, loc=28, parent=5)
    # Now check the fifth directory record.  The number of children should be
    # 3, the name should be DIR5, the directory record length should be 38, it
    # should start at extent 28, and it should not have Rock Ridge.
    internal_check_dir_record(dir5_record, 3, b"DIR5", 114, 28, True, b"dir5", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir5_record.children[1], True, 3, False)

    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'DIR6', len_di=4, loc=29, parent=6)
    # Now check the sixth directory record.  The number of children should be
    # 3, the name should be DIR6, the directory record length should be 38, it
    # should start at extent 29, and it should not have Rock Ridge.
    internal_check_dir_record(dir6_record, 3, b"DIR6", 114, 29, True, b"dir6", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir6_record.children[1], True, 3, False)

    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'DIR7', len_di=4, loc=30, parent=7)
    # Now check the seventh directory record.  The number of children should be
    # 2, the name should be DIR7, the directory record length should be 38, it
    # should start at extent 30, and it should not have Rock Ridge.
    internal_check_dir_record(dir7_record, 2, b"DIR7", 114, 30, True, b"dir7", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir7_record.children[1], True, 3, False)

def check_xa_joliet_nofiles(iso, filesize):
    assert(filesize == 61440)

    internal_check_pvd(iso.pvd, extent=16, size=30, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 30, 10, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_xa_joliet_onefile(iso, filesize):
    assert(filesize == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 54, 30, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n", 'iso_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 30, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", 'joliet_path')

def check_xa_joliet_onedir(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 26, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=True, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=29, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 52, 29, False, None, 0, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], False, 3, True)

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=31, parent=1)
    internal_check_dir_record(joliet_dir1_record, 2, "dir1".encode('utf-16_be'), 42, 31, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(joliet_dir1_record.children[1], False, 3, False)

def check_isolevel4_nofiles(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_enhanced_vd(iso.enhanced_vd, 25, 10, 20, 22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

def check_isolevel4_onefile(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_enhanced_vd(iso.enhanced_vd, 26, 10, 20, 22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"foo", 36, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_isolevel4_onedir(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_enhanced_vd(iso.enhanced_vd, 26, 22, 20, 22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'dir1', len_di=4, loc=25, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"dir1", 38, 25, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

def check_isolevel4_eltorito(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 34, and the initial entry should start at
    # extent 35.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_enhanced_vd(iso.enhanced_vd, 28, 10, 21, 23)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_everything(iso, filesize):
    assert(filesize == 108544)

    internal_check_pvd(iso.pvd, extent=16, size=53, ptbl_size=106, ptbl_location_le=22, ptbl_location_be=24)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 34, and the initial entry should start at
    # extent 35.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 49, 50)

    internal_check_enhanced_vd(iso.enhanced_vd, 53, 106, 22, 24)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[1], 53, 138, 26, 28)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=20)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=39, parent=1)
    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[4]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=40, parent=1)
    joliet_dir2_record = joliet_dir1_record.children[2]
    internal_check_ptr(joliet_dir2_record.ptr, name='dir2'.encode('utf-16_be'), len_di=8, loc=41, parent=2)
    joliet_dir3_record = joliet_dir2_record.children[2]
    internal_check_ptr(joliet_dir3_record.ptr, name='dir3'.encode('utf-16_be'), len_di=8, loc=42, parent=3)
    joliet_dir4_record = joliet_dir3_record.children[2]
    internal_check_ptr(joliet_dir4_record.ptr, name='dir4'.encode('utf-16_be'), len_di=8, loc=43, parent=4)
    joliet_dir5_record = joliet_dir4_record.children[2]
    internal_check_ptr(joliet_dir5_record.ptr, name='dir5'.encode('utf-16_be'), len_di=8, loc=44, parent=5)
    joliet_dir6_record = joliet_dir5_record.children[2]
    internal_check_ptr(joliet_dir6_record.ptr, name='dir6'.encode('utf-16_be'), len_di=8, loc=45, parent=6)
    joliet_dir7_record = joliet_dir6_record.children[2]
    internal_check_ptr(joliet_dir7_record.ptr, name='dir7'.encode('utf-16_be'), len_di=8, loc=46, parent=7)
    joliet_dir8_record = joliet_dir7_record.children[2]
    internal_check_ptr(joliet_dir8_record.ptr, name='dir8'.encode('utf-16_be'), len_di=8, loc=47, parent=8)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=7, data_length=2048, extent_location=30, rr=True, rr_nlinks=3, xa=True, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 7, 2048, 39)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 128, 50, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.vd.extent_location() == 16)
    assert(boot_rec.boot_info_table.dirrecord.extent_location() == 50)
    assert(boot_rec.boot_info_table.orig_len == 5)
    assert(boot_rec.boot_info_table.csum == 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 136, 49, 2048, hidden=False, num_linked_records=1)

    dir1_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(dir1_record.ptr, name=b'dir1', len_di=4, loc=31, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(dir1_record, 4, b"dir1", 128, 31, True, b"dir1", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, True)

    internal_check_file(dir1_record.children[3], b"foo", 126, 51, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/dir1/foo", b"foo\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[5], b"foo", 126, 51, 4, hidden=False, num_linked_records=3)
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_symlink(sym_dir_record, b'sym', 136, 52, [b'foo'])

    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'dir2', len_di=4, loc=32, parent=2)
    internal_check_dir_record(dir2_record, 3, b"dir2", 128, 32, True, b"dir2", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_record.children[1], True, 3, True)

    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'dir3', len_di=4, loc=33, parent=3)
    internal_check_dir_record(dir3_record, 3, b"dir3", 128, 33, True, b"dir3", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir3_record.children[1], True, 3, True)

    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'dir4', len_di=4, loc=34, parent=4)
    internal_check_dir_record(dir4_record, 3, b"dir4", 128, 34, True, b"dir4", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir4_record.children[1], True, 3, True)

    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'dir5', len_di=4, loc=35, parent=5)
    internal_check_dir_record(dir5_record, 3, b"dir5", 128, 35, True, b"dir5", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir5_record.children[1], True, 3, True)

    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'dir6', len_di=4, loc=36, parent=6)
    internal_check_dir_record(dir6_record, 3, b"dir6", 128, 36, True, b"dir6", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir6_record.children[1], True, 3, True)

    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'dir7', len_di=4, loc=37, parent=7)
    internal_check_dir_record(dir7_record, 3, b"dir7", 128, 37, True, b"dir7", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir7_record.children[1], True, 3, True)

    dir8_record = dir7_record.children[2]
    internal_check_ptr(dir8_record.ptr, name=b'dir8', len_di=4, loc=38, parent=8)
    internal_check_dir_record(dir8_record, 3, b"dir8", 128, 38, True, b"dir8", 2, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir8_record.children[1], True, 3, True)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(dir8_record.children[2], b"bar", 126, 52, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar", b"bar\n")

def check_rr_xa_nofiles(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=True, rr_onetwelve=False)

def check_rr_xa_onefile(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=True, rr_onetwelve=False)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 130, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

def check_rr_xa_onedir(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=True, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(dir1_record, 2, b"DIR1", 128, 24, True, b'dir1', 2, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, True)

def check_rr_joliet_symlink(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 29)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 31, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 32, [b'foo'])

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 31, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n", which='joliet_path')

def check_rr_joliet_deep(iso, filesize):
    assert(filesize == 98304)

    internal_check_pvd(iso.pvd, extent=16, size=48, ptbl_size=122, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)
    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=None, parent=1)
    rr_moved_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(rr_moved_record.ptr, name=b'RR_MOVED', len_di=8, loc=None, parent=1)
    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=None, parent=2)
    dir8_record = rr_moved_record.children[2]
    internal_check_ptr(dir8_record.ptr, name=b'DIR8', len_di=4, loc=None, parent=3)
    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'DIR3', len_di=4, loc=None, parent=4)
    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'DIR4', len_di=4, loc=None, parent=6)
    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'DIR5', len_di=4, loc=None, parent=7)
    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'DIR6', len_di=4, loc=None, parent=8)
    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'DIR7', len_di=4, loc=None, parent=9)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=None, parent=1)
    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=None, parent=1)
    joliet_dir2_record = joliet_dir1_record.children[2]
    internal_check_ptr(joliet_dir2_record.ptr, name='dir2'.encode('utf-16_be'), len_di=8, loc=None, parent=2)
    joliet_dir3_record = joliet_dir2_record.children[2]
    internal_check_ptr(joliet_dir3_record.ptr, name='dir3'.encode('utf-16_be'), len_di=8, loc=None, parent=3)
    joliet_dir4_record = joliet_dir3_record.children[2]
    internal_check_ptr(joliet_dir4_record.ptr, name='dir4'.encode('utf-16_be'), len_di=8, loc=None, parent=4)
    joliet_dir5_record = joliet_dir4_record.children[2]
    internal_check_ptr(joliet_dir5_record.ptr, name='dir5'.encode('utf-16_be'), len_di=8, loc=None, parent=5)
    joliet_dir6_record = joliet_dir5_record.children[2]
    internal_check_ptr(joliet_dir6_record.ptr, name='dir6'.encode('utf-16_be'), len_di=8, loc=None, parent=6)
    joliet_dir7_record = joliet_dir6_record.children[2]
    internal_check_ptr(joliet_dir7_record.ptr, name='dir7'.encode('utf-16_be'), len_di=8, loc=None, parent=7)
    joliet_dir8_record = joliet_dir7_record.children[2]
    internal_check_ptr(joliet_dir8_record.ptr, name='dir8'.encode('utf-16_be'), len_di=8, loc=None, parent=8)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=28, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 38)

def check_eltorito_multi_boot(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    assert(len(iso.eltorito_boot_catalog.sections) == 1)
    sec = iso.eltorito_boot_catalog.sections[0]
    assert(sec.header_indicator == 0x91)
    assert(sec.platform_id == 0)
    assert(sec.num_section_entries == 1)
    assert(sec.id_string == b'\x00'*28)
    assert(len(sec.section_entries) == 1)
    entry = sec.section_entries[0]
    assert(entry.boot_indicator == 0x88)
    assert(entry.boot_media_type == 0x0)
    assert(entry.load_segment == 0x0)
    assert(entry.system_type == 0)
    assert(entry.sector_count == 4)
    assert(entry.load_rba == 28)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

def check_eltorito_multi_boot_hard_link(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    assert(len(iso.eltorito_boot_catalog.sections) == 1)
    sec = iso.eltorito_boot_catalog.sections[0]
    assert(sec.header_indicator == 0x91)
    assert(sec.platform_id == 0)
    assert(sec.num_section_entries == 1)
    assert(sec.id_string == b'\x00'*28)
    assert(len(sec.section_entries) == 1)
    entry = sec.section_entries[0]
    assert(entry.boot_indicator == 0x88)
    assert(entry.boot_media_type == 0x0)
    assert(entry.load_segment == 0x0)
    assert(entry.system_type == 0)
    assert(entry.sector_count == 4)
    assert(entry.load_rba == 28)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=6, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

    internal_check_file(iso.pvd.root_dir_record.children[5], b"bootlink", 42, 28, 6, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/bootlink", b"boot2\n")

def check_eltorito_boot_info_table(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.vd.extent_location() == 16)
    assert(boot_rec.boot_info_table.dirrecord.extent_location() == 27)
    assert(boot_rec.boot_info_table.orig_len == 5)
    assert(boot_rec.boot_info_table.csum == 0)

def check_eltorito_boot_info_table_large(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 80, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"bootboot\x10\x00\x00\x00\x1b\x00\x00\x00P\x00\x00\x00\x88\xbd\xbd\xd1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00bootbootbootboot")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.vd.extent_location() == 16)
    assert(boot_rec.boot_info_table.dirrecord.extent_location() == 27)
    assert(boot_rec.boot_info_table.orig_len == 80)
    assert(boot_rec.boot_info_table.csum == 0xd1bdbd88)

def check_hard_link(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_dir_record(dir1_record, 3, b"DIR1", 38, 24, False, b'', 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    internal_check_file(dir1_record.children[2], b"FOO.;1", 40, 25, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/DIR1/FOO.;1", b"foo\n")

def check_same_dirname_different_parent(iso, filesize):
    assert(filesize == 79872)

    internal_check_pvd(iso.pvd, extent=16, size=39, ptbl_size=58, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 39, 74, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=33, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=28, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=None, parent=1)
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, None, True, b'dir1', 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 4, False)

    dir2_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=None, parent=1)
    internal_check_dir_record(dir2_record, 3, b"DIR2", 114, None, True, b'dir2', 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_record.children[1], True, 4, False)

    boot1_record = dir1_record.children[2]
    internal_check_ptr(boot1_record.ptr, name=b'BOOT', len_di=4, loc=None, parent=2)
    internal_check_dir_record(boot1_record, 2, b"BOOT", 114, None, True, b'boot', 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot1_record.children[1], True, 3, False)

    boot2_record = dir2_record.children[2]
    internal_check_ptr(boot2_record.ptr, name=b'BOOT', len_di=4, loc=None, parent=3)
    internal_check_dir_record(boot2_record, 2, b"BOOT", 114, None, True, b'boot', 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot2_record.children[1], True, 3, False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 33)

    dir1_joliet_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(dir1_joliet_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=None, parent=1)
    internal_check_dir_record(dir1_joliet_record, 3, "dir1".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_joliet_record.children[1], False, 3, False)

    dir2_joliet_record = iso.joliet_vd.root_dir_record.children[3]
    internal_check_ptr(dir2_joliet_record.ptr, name='dir2'.encode('utf-16_be'), len_di=8, loc=None, parent=1)
    internal_check_dir_record(dir2_joliet_record, 3, "dir2".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_joliet_record.children[1], False, 3, False)

    boot1_joliet_record = dir1_joliet_record.children[2]
    internal_check_ptr(boot1_joliet_record.ptr, name='boot'.encode('utf-16_be'), len_di=8, loc=None, parent=2)
    internal_check_dir_record(boot1_joliet_record, 2, "boot".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot1_joliet_record.children[1], False, 3, False)

    boot2_joliet_record = dir2_joliet_record.children[2]
    internal_check_ptr(boot2_joliet_record.ptr, name='boot'.encode('utf-16_be'), len_di=8, loc=None, parent=3)
    internal_check_dir_record(boot2_joliet_record, 2, "boot".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot2_joliet_record.children[1], False, 3, False)

def check_joliet_isolevel4(iso, filesize):
    assert(filesize == 69632)

    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=22, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_enhanced_vd(iso.enhanced_vd, 34, 22, 21, 23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file and one directory, the number of extents should be the same as the
    # PVD, the path table should be 26 bytes (10 bytes for the root directory
    # entry and 16 bytes for the directory), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.joliet_vd, 34, 26, 25, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=31, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'dir1', len_di=4, loc=30, parent=1)
    # Now check the empty directory record.  The name should be DIR1, and it
    # should start at extent 29.
    internal_check_empty_directory(dir1_record, b"dir1", 38, 30)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 31)

    joliet_dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(joliet_dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=32, parent=1)
    # Now check the empty Joliet directory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(joliet_dir1_record, "dir1".encode('utf-16_be'), 42, 32)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"foo", 36, 33, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "foo".encode('utf-16_be'), 40, 33, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_eltorito_nofiles_hide(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_joliet_and_eltorito_nofiles_hide(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 31, and the initial entry should start at
    # extent 32.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 31, 32)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

def check_joliet_and_eltorito_nofiles_hide_only(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 31, and the initial entry should start at
    # extent 32.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 31, 32)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048, hidden=False, num_linked_records=0)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

def check_joliet_and_eltorito_nofiles_hide_iso_only(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 25, 27)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 31, and the initial entry should start at
    # extent 32.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 31, 32)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n", 'iso_path')

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, None, 2048, hidden=False, num_linked_records=0)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", 'joliet_path')

def check_hard_link_reshuffle(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 24, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BAR.;1", b"foo\n")

def check_rr_deeper_dir(iso, filesize):
    assert(filesize == 86016)

    internal_check_pvd(iso.pvd, extent=16, size=42, ptbl_size=202, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)
    a1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(a1_record.ptr, name=b'A1', len_di=2, loc=None, parent=1)
    dir1_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=None, parent=1)
    rr_moved_record = iso.pvd.root_dir_record.children[4]
    internal_check_ptr(rr_moved_record.ptr, name=b'RR_MOVED', len_di=8, loc=None, parent=1)
    a2_record = a1_record.children[2]
    internal_check_ptr(a2_record.ptr, name=b'A2', len_di=2, loc=None, parent=2)
    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=None, parent=3)
    a8_record = rr_moved_record.children[2]
    internal_check_ptr(a8_record.ptr, name=b'A8', len_di=2, loc=None, parent=4)
    dir8_record = rr_moved_record.children[3]
    internal_check_ptr(dir8_record.ptr, name=b'DIR8', len_di=4, loc=None, parent=4)
    a3_record = a2_record.children[2]
    internal_check_ptr(a3_record.ptr, name=b'A3', len_di=2, loc=None, parent=5)
    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'DIR3', len_di=4, loc=None, parent=6)
    a4_record = a3_record.children[2]
    internal_check_ptr(a4_record.ptr, name=b'A4', len_di=2, loc=None, parent=9)
    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'DIR4', len_di=4, loc=None, parent=10)
    a5_record = a4_record.children[2]
    internal_check_ptr(a5_record.ptr, name=b'A5', len_di=2, loc=None, parent=11)
    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'DIR5', len_di=4, loc=None, parent=12)
    a6_record = a5_record.children[2]
    internal_check_ptr(a6_record.ptr, name=b'A6', len_di=2, loc=None, parent=13)
    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'DIR6', len_di=4, loc=None, parent=14)
    a7_record = a6_record.children[2]
    internal_check_ptr(a7_record.ptr, name=b'A7', len_di=2, loc=None, parent=15)
    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'DIR7', len_di=4, loc=None, parent=16)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=23, rr=True, rr_nlinks=5, xa=False, rr_onetwelve=False)

def check_eltorito_boot_info_table_large_odd(iso, filesize):
    assert(filesize == 57344)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 81, hidden=False, num_linked_records=0)

    internal_check_file_contents(iso, "/boot", b"booboobo\x10\x00\x00\x00\x1b\x00\x00\x00\x51\x00\x00\x00\x1e\xb1\xa3\xb0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00ooboobooboobooboo")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.vd.extent_location() == 16)
    assert(boot_rec.boot_info_table.dirrecord.extent_location() == 27)
    assert(boot_rec.boot_info_table.orig_len == 81)
    assert(boot_rec.boot_info_table.csum == 0xb0a3b11e)

def check_joliet_large_directory(iso, filesize):
    assert(filesize == 264192)

    internal_check_pvd(iso.pvd, extent=16, size=129, ptbl_size=678, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 129, 874, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    # FIXME: this test should probably be more comprehensive

def check_zero_byte_file(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 0, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

def check_eltorito_hide_boot(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Here, the initial entry is hidden, so we check it out by manually looking
    # for it in the raw output.  To do that in the current framework, we need
    # to re-write the iso into a string, then search the string.
    initial_entry_offset = iso.eltorito_boot_catalog.initial_entry.get_rba()

    # Re-render the output into a string.
    myout = BytesIO()
    iso.write_fp(myout)

    # Now seek within the string to the right location.
    myout.seek(initial_entry_offset * 2048)

    val = myout.read(5)
    assert(val == b"boot\n")

def check_modify_in_place_spillover(iso, filesize):
    assert(filesize == 151552)

    internal_check_pvd(iso.pvd, extent=16, size=74, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    internal_check_dir_record(dir1_record, 50, b"DIR1", 38, 24, False, None, 0, False, False, False, 4096)

def check_duplicate_pvd(iso, filesize):
    assert(filesize == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_pvd(iso.pvds[1], extent=17, size=26, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

def check_eltorito_multi_multi_boot(iso, filesize):
    assert(filesize == 61440)

    internal_check_pvd(iso.pvd, extent=16, size=30, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    assert(len(iso.eltorito_boot_catalog.sections) == 2)
    sec = iso.eltorito_boot_catalog.sections[0]
    assert(sec.header_indicator == 0x90)
    assert(sec.platform_id == 0)
    assert(sec.num_section_entries == 1)
    assert(sec.id_string == b'\x00'*28)
    assert(len(sec.section_entries) == 1)
    entry = sec.section_entries[0]
    assert(entry.boot_indicator == 0x88)
    assert(entry.boot_media_type == 0x0)
    assert(entry.load_segment == 0x0)
    assert(entry.system_type == 0)
    assert(entry.sector_count == 4)
    assert(entry.load_rba == 28)

    sec = iso.eltorito_boot_catalog.sections[1]
    assert(sec.header_indicator == 0x91)
    assert(sec.platform_id == 0)
    assert(sec.num_section_entries == 1)
    assert(sec.id_string == b'\x00'*28)
    assert(len(sec.section_entries) == 1)
    entry = sec.section_entries[0]
    assert(entry.boot_indicator == 0x88)
    assert(entry.boot_media_type == 0x0)
    assert(entry.load_segment == 0x0)
    assert(entry.system_type == 0)
    assert(entry.sector_count == 4)
    assert(entry.load_rba == 29)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=6, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

def check_hidden_file(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AAAAAAAA.;1", 44, 24, 3, hidden=True, num_linked_records=0)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", b"aa\n")

def check_hidden_dir(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)
    # Now check the one empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 24, hidden=True)

def check_eltorito_hd_emul(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 4, 2)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 512, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*446 + b"\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00"*16 + b"\x00"*16 + b"\x00"*16 + b'\x55' + b'\xaa')

def check_eltorito_hd_emul_bad_sec(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 4, 2)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 512, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*446 + b"\x00\x00\x00\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00"*16 + b"\x00"*16 + b"\x00"*16 + b'\x55' + b'\xaa')

def check_eltorito_hd_emul_invalid_geometry(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 4, 2)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 512, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*446 + b"\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00"*16 + b"\x00"*16 + b"\x00"*16 + b'\x55' + b'\xaa')

def check_eltorito_hd_emul_not_bootable(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 4, 2, bootable=False)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 512, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*446 + b"\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00" + b"\x00"*16 + b"\x00"*16 + b"\x00"*16 + b'\x55' + b'\xaa')

def check_eltorito_floppy12(iso, filesize):
    assert(filesize == 1282048)

    internal_check_pvd(iso.pvd, extent=16, size=626, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 1, 0)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 1228800, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*(2400*512))

def check_eltorito_floppy144(iso, filesize):
    assert(filesize == 1527808)

    internal_check_pvd(iso.pvd, extent=16, size=746, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 2, 0)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 1474560, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*(2880*512))

def check_eltorito_floppy288(iso, filesize):
    assert(filesize == 3002368)

    internal_check_pvd(iso.pvd, extent=16, size=1466, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26, 3, 0)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 2949120, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"\x00"*(5760*512))

def check_eltorito_multi_hidden(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    assert(len(iso.eltorito_boot_catalog.sections) == 1)
    sec = iso.eltorito_boot_catalog.sections[0]
    assert(sec.header_indicator == 0x91)
    assert(sec.platform_id == 0)
    assert(sec.num_section_entries == 1)
    assert(sec.id_string == b'\x00'*28)
    assert(len(sec.section_entries) == 1)
    entry = sec.section_entries[0]
    assert(entry.boot_indicator == 0x88)
    assert(entry.boot_media_type == 0x0)
    assert(entry.load_segment == 0x0)
    assert(entry.system_type == 0)
    assert(entry.sector_count == 4)
    assert(entry.load_rba == 28)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_onefile_with_semicolon(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO;1.;1", 42, 24, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOO;1.;1', b"foo\n")

def check_bad_eltorito_ident(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Because this is a bad eltorito ident, we expect the len(brs) to be > 0,
    # but no eltorito catalog available
    assert(len(iso.brs) == 1)
    assert(iso.eltorito_boot_catalog is None)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/BOOT.;1', b"boot\n")

def check_rr_two_dirs_same_level(iso, filesize):
    assert(filesize == 77824)

    # For two relocated directories at the same level with the same name,
    # genisoimage seems to pad the second entry in the PTR with three zeros (000), the
    # third one with 001, etc.  pycdlib does not do this, so the sizes do not match.
    # Hence, for now, we disable this check.
    #internal_check_pvd(iso.pvd, extent=16, size=38, ptbl_size=128, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    a_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(a_dir_record.ptr, name=b'A', len_di=1, loc=None, parent=1)
    # Now check the empty directory record.  The name should be DIR1, the
    # directory record length should be 114 (for the Rock Ridge), it should
    # start at extent 24, and it should have Rock Ridge.
    internal_check_dir_record(a_dir_record, 3, b"A", 108, None, True, b'A', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(a_dir_record.children[1], True, 4, False)

    b_dir_record = a_dir_record.children[2]
    internal_check_dir_record(b_dir_record, 3, b"B", 108, None, True, b'B', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(b_dir_record.children[1], True, 3, False)

    c_dir_record = b_dir_record.children[2]
    internal_check_dir_record(c_dir_record, 3, b"C", 108, 29, True, b'C', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(c_dir_record.children[1], True, 3, False)

    d_dir_record = c_dir_record.children[2]
    internal_check_dir_record(d_dir_record, 3, b"D", 108, 30, True, b'D', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(d_dir_record.children[1], True, 3, False)

    e_dir_record = d_dir_record.children[2]
    internal_check_dir_record(e_dir_record, 3, b"E", 108, 31, True, b'E', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(e_dir_record.children[1], True, 3, False)

    f_dir_record = e_dir_record.children[2]
    internal_check_dir_record(f_dir_record, 4, b"F", 108, 32, True, b'F', 4, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(f_dir_record.children[1], True, 3, False)

    g_dir_record = f_dir_record.children[2]
    internal_check_dir_record(g_dir_record, 3, b"G", 108, None, True, b'G', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(g_dir_record.children[1], True, 4, False)

    # This is the first of the two relocated entries.
    one_dir_record = g_dir_record.children[2]
    internal_check_dir_record(one_dir_record, 0, b"1", 120, None, True, b"1", 2, False, False, True)

    h_dir_record = f_dir_record.children[3]
    internal_check_dir_record(h_dir_record, 3, b"H", 108, None, True, b'H', 3, False, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(g_dir_record.children[1], True, 4, False)

    # This is the second of the two relocated entries.
    one_dir_record = h_dir_record.children[2]
    internal_check_dir_record(one_dir_record, 0, b"1", 120, None, True, b"1", 2, False, False, True)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    internal_check_file_contents(iso, "/A/B/C/D/E/F/G/1/FIRST.;1", b"first\n")
    internal_check_file_contents(iso, "/A/B/C/D/E/F/H/1/SECOND.;1", b"second\n")

def check_eltorito_rr_verylongname(iso, filesize):
    assert(filesize == 59392)

    internal_check_pvd(iso.pvd, extent=16, size=29, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 27, 28)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AAAAAAAA.;1", None, 27, 2048, hidden=False, num_linked_records=0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.;1", 116, 28, 5, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_isohybrid_file_before(iso, filesize):
    assert(filesize == 1048576)

    internal_check_pvd(iso.pvd, extent=16, size=28, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=5, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    # Now check out the isohybrid stuff.
    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)
    assert(iso.isohybrid_mbr.rba != 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 27, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the boot file.  It should have a name of ISOLINUX.BIN;1, it
    # should have a directory record length of 48, and it should start at
    # extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[4], b"ISOLINUX.BIN;1", 48, 26, 68, hidden=False, num_linked_records=0)

def check_eltorito_rr_joliet_verylongname(iso, filesize):
    assert(filesize == 71680)

    internal_check_pvd(iso.pvd, extent=16, size=35, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 33, 34)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with El
    # Torito, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little endian
    # path table should start at extent 25, and the big endian path table
    # should start at extent 27 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 35, 10, 25, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=31, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 31)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AAAAAAAA.;1", None, 33, 2048, hidden=False, num_linked_records=1)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.;1", 116, 34, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    joliet_name = "a"*64
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], joliet_name.encode('utf-16_be'), 162, 33, 2048, hidden=False, num_linked_records=1)

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot".encode('utf-16_be'), 42, 34, 5, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/boot", b"boot\n", which='joliet_path')

def check_joliet_dirs_overflow_ptr_extent(iso, filesize):
    assert(filesize == 970752)

    internal_check_pvd(iso.pvd, extent=16, size=474, ptbl_size=3016, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 474, 4114, 24, 28)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=216+2, data_length=10240, extent_location=32, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=32, parent=1)
    # The rest of the path table records will be checked by the loop below.

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=253, parent=1)

    names = internal_generate_joliet_inorder_names(216)
    for index in range(2, 2+216):
        joliet_dir_record = iso.joliet_vd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(joliet_dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

def check_joliet_dirs_just_short_ptr_extent(iso, filesize):
    assert(filesize == 958464)

    internal_check_pvd(iso.pvd, extent=16, size=468, ptbl_size=3002, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 468, 4094, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=215+2, data_length=10240, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)
    # The rest of the path table records will be checked by the loop below.

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=248, parent=1)

    names = internal_generate_joliet_inorder_names(215)
    for index in range(2, 2+215):
        joliet_dir_record = iso.joliet_vd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(joliet_dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

def check_joliet_dirs_add_ptr_extent(iso, filesize):
    assert(filesize == 1308672)

    internal_check_pvd(iso.pvd, extent=16, size=639, ptbl_size=4122, ptbl_location_le=20, ptbl_location_be=24)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 639, 5694, 28, 32)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=295+2, data_length=12288, extent_location=36, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=36, parent=1)
    # The rest of the path table records will be checked by the loop below.

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=337, parent=1)

    names = internal_generate_joliet_inorder_names(295)
    for index in range(2, 2+295):
        joliet_dir_record = iso.joliet_vd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(joliet_dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

def check_joliet_dirs_rm_ptr_extent(iso, filesize):
    assert(filesize == 1292288)

    internal_check_pvd(iso.pvd, extent=16, size=631, ptbl_size=4094, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 631, 5654, 24, 28)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=293+2, data_length=12288, extent_location=32, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=32, parent=1)
    # The rest of the path table records will be checked by the loop below.

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=331, parent=1)

    names = internal_generate_joliet_inorder_names(293)
    for index in range(2, 2+293):
        joliet_dir_record = iso.joliet_vd.root_dir_record.children[index]
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(joliet_dir_record.ptr, name=names[index], len_di=len(names[index]), loc=None, parent=1)

def check_long_directory_name(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=28, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    directory1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(directory1_record.ptr, name=b'DIRECTORY1', len_di=10, loc=24, parent=1)
    # Now check the one empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(directory1_record, b"DIRECTORY1", 44, 24)

def check_long_file_name(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOOBARBAZ1.;1", 46, 24, 11, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOOBARBAZ1.;1', b"foobarbaz1\n")

def check_overflow_root_dir_record(iso, filesize):
    assert(filesize == 94208)

    internal_check_pvd(iso.pvd, extent=16, size=46, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=16, data_length=4096, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    internal_check_dot_dir_record(iso.pvd.root_dir_record.children[0], True, 2, True, False, 4096)

def check_overflow_correct_extents(iso, filesize):
    assert(filesize == 102400)

    internal_check_pvd(iso.pvd, extent=16, size=50, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=18, data_length=6144, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    internal_check_dot_dir_record(iso.pvd.root_dir_record.children[0], True, 2, True, False, 6144)

def check_duplicate_deep_dir(iso, filesize):
    assert(filesize == 135168)

    internal_check_pvd(iso.pvd, extent=16, size=66, ptbl_size=216, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)
    books_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(books_record.ptr, name=b'BOOKS', len_di=5, loc=None, parent=1)
    rr_moved_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(rr_moved_record.ptr, name=b'RR_MOVED', len_di=8, loc=None, parent=1)
    lkhg_record = books_record.children[2]
    internal_check_ptr(lkhg_record.ptr, name=b'LKHG', len_di=4, loc=None, parent=2)
    first_one_record = rr_moved_record.children[2]
    internal_check_ptr(first_one_record.ptr, name=b'1', len_di=1, loc=None, parent=3)
    one_thousand_record = rr_moved_record.children[3]
    internal_check_ptr(one_thousand_record.ptr, name=b'1000', len_di=4, loc=None, parent=3)
    hypernew_record = lkhg_record.children[2]
    internal_check_ptr(hypernew_record.ptr, name=b'HYPERNEW', len_di=8, loc=None, parent=4)
    get_record = hypernew_record.children[2]
    internal_check_ptr(get_record.ptr, name=b'GET', len_di=3, loc=None, parent=7)
    first_fs_record = get_record.children[2]
    internal_check_ptr(first_fs_record.ptr, name=b'FS', len_di=2, loc=None, parent=9)
    khg_record = get_record.children[3]
    internal_check_ptr(khg_record.ptr, name=b'KHG', len_di=3, loc=None, parent=9)
    second_fs_record = first_fs_record.children[2]
    internal_check_ptr(second_fs_record.ptr, name=b'FS', len_di=2, loc=None, parent=11)
    fourth_one_record = khg_record.children[2]
    internal_check_ptr(fourth_one_record.ptr, name=b'1', len_di=1, loc=None, parent=12)
    one_one_seven_record = khg_record.children[3]
    internal_check_ptr(one_one_seven_record.ptr, name=b'117', len_di=3, loc=None, parent=12)
    thirty_five_record = khg_record.children[4]
    internal_check_ptr(thirty_five_record.ptr, name=b'35', len_di=2, loc=None, parent=12)
    fifth_one_record = second_fs_record.children[2]
    internal_check_ptr(fifth_one_record.ptr, name=b'1', len_di=1, loc=None, parent=13)
    sixth_one_record = one_one_seven_record.children[2]
    internal_check_ptr(sixth_one_record.ptr, name=b'1', len_di=1, loc=None, parent=15)
    seventh_one_record = thirty_five_record.children[2]
    internal_check_ptr(seventh_one_record.ptr, name=b'1', len_di=1, loc=None, parent=16)

    # This is the second of the two relocated entries.
    rr_moved_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_dir_record(rr_moved_dir_record, 4, b"RR_MOVED", 122, None, True, b"rr_moved", 4, False, False, False)

    # In theory we should check the dir_records underneath rr_moved here.
    # Unfortunately, which directory gets renamed to 1000 is unstable,
    # and thus we don't know which record it is.  We skip the check for now,
    # although we could go grubbing through the children to try and find it.

def check_onefile_joliet_no_file(iso, filesize):
    assert(filesize == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 30, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

def check_joliet_isolevel4_nofiles(iso, filesize):
    assert(filesize == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.joliet_vd, 31, 10, 25, 27)

    internal_check_enhanced_vd(iso.enhanced_vd, 31, 10, 21, 23)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 30)

def check_rr_absolute_symlink(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 140, 25, [b'', b'usr', b'local', b'foo'])

def check_deep_rr_symlink(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=94, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    dir2_record = dir1_record.children[2]
    dir3_record = dir2_record.children[2]
    dir4_record = dir3_record.children[2]
    dir5_record = dir4_record.children[2]
    dir6_record = dir5_record.children[2]
    dir7_record = dir6_record.children[2]

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = dir7_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 140, 32, [b'', b'usr', b'share', b'foo'])

def check_rr_deep_weird_layout(iso, filesize):
    assert(filesize == 73728)

    internal_check_pvd(iso.pvd, extent=16, size=36, ptbl_size=146, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    astroid_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(astroid_record.ptr, name=b'ASTROID', len_di=7, loc=None, parent=1)
    internal_check_dir_record(astroid_record, 3, b'ASTROID', 120, None, True, b'astroid', 3, False)

    rr_moved_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(rr_moved_record.ptr, name=b'RR_MOVED', len_di=8, loc=None, parent=1)

    astroid2_record = astroid_record.children[2]
    internal_check_ptr(astroid2_record.ptr, name=b'ASTROID', len_di=7, loc=None, parent=2)

    sidepack_record = rr_moved_record.children[2]
    internal_check_ptr(sidepack_record.ptr, name=b'SIDEPACK', len_di=8, loc=None, parent=3)

    tests_record = astroid2_record.children[2]
    internal_check_ptr(tests_record.ptr, name=b'TESTS', len_di=5, loc=28, parent=4)

    testdata_record = tests_record.children[2]
    internal_check_ptr(testdata_record.ptr, name=b'TESTDATA', len_di=8, loc=29, parent=6)

    python3_record = testdata_record.children[2]
    internal_check_ptr(python3_record.ptr, name=b'PYTHON3', len_di=7, loc=30, parent=7)

    data_record = python3_record.children[2]
    internal_check_ptr(data_record.ptr, name=b'DATA', len_di=4, loc=31, parent=8)

    absimp_record = data_record.children[2]
    internal_check_ptr(absimp_record.ptr, name=b'ABSIMP', len_di=6, loc=32, parent=9)

    internal_check_file_contents(iso, "/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP/STRING.PY;1", b"from __future__ import absolute_import, print_functino\nimport string\nprint(string)\n")

    internal_check_file_contents(iso, "/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP/SIDEPACK/__INIT__.PY;1", b'"""a side package with nothing in it\n"""\n')

def check_rr_long_dir_name(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=26, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    aa_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(aa_record.ptr, name=b'AAAAAAAA', len_di=8, loc=None, parent=1)
    internal_check_dir_record(aa_record, 2, b'AAAAAAAA', None, None, True, b'a'*RR_MAX_FILENAME_LENGTH, 2, False)

def check_rr_out_of_order_ce(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=26, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    aa_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(aa_record.ptr, name=b'AAAAAAAA', len_di=8, loc=None, parent=1)
    internal_check_dir_record(aa_record, 2, b'AAAAAAAA', None, None, True, b'a'*RR_MAX_FILENAME_LENGTH, 2, False)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 254, 27, [b"a"*RR_MAX_FILENAME_LENGTH, b"b"*RR_MAX_FILENAME_LENGTH, b"c"*RR_MAX_FILENAME_LENGTH, b"d"*RR_MAX_FILENAME_LENGTH, b"e"*RR_MAX_FILENAME_LENGTH])

def check_rr_ce_removal(iso, filesize):
    assert(filesize == 61440)

    internal_check_pvd(iso.pvd, extent=16, size=30, ptbl_size=74, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    ee_record = iso.pvd.root_dir_record.children[5]
    internal_check_ptr(ee_record.ptr, name=b'EEEEEEEE', len_di=8, loc=None, parent=1)
    internal_check_dir_record(ee_record, 2, b'EEEEEEEE', None, None, True, b'e'*RR_MAX_FILENAME_LENGTH, 2, False)

def check_rr_relocated_hidden(iso, filesize):
    assert(filesize == 73728)

    internal_check_pvd(iso.pvd, extent=16, size=36, ptbl_size=134, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=None, parent=1)
    rr_moved_record = iso.pvd.root_dir_record.children[3]
    internal_check_ptr(rr_moved_record.ptr, name=b'_RR_MOVE', len_di=8, loc=None, parent=1)
    dir2_record = dir1_record.children[2]
    internal_check_ptr(dir2_record.ptr, name=b'DIR2', len_di=4, loc=None, parent=2)
    dir8_record = rr_moved_record.children[2]
    internal_check_ptr(dir8_record.ptr, name=b'DIR8', len_di=4, loc=None, parent=3)
    dir3_record = dir2_record.children[2]
    internal_check_ptr(dir3_record.ptr, name=b'DIR3', len_di=4, loc=None, parent=4)
    dir9_record = dir8_record.children[2]
    internal_check_ptr(dir9_record.ptr, name=b'DIR9', len_di=4, loc=None, parent=5)
    dir4_record = dir3_record.children[2]
    internal_check_ptr(dir4_record.ptr, name=b'DIR4', len_di=4, loc=None, parent=6)
    dir5_record = dir4_record.children[2]
    internal_check_ptr(dir5_record.ptr, name=b'DIR5', len_di=4, loc=None, parent=8)
    dir6_record = dir5_record.children[2]
    internal_check_ptr(dir6_record.ptr, name=b'DIR6', len_di=4, loc=None, parent=9)
    dir7_record = dir6_record.children[2]
    internal_check_ptr(dir7_record.ptr, name=b'DIR7', len_di=4, loc=None, parent=10)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=4, xa=False, rr_onetwelve=False)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/foo", b"foo\n", which='rr_path')

def check_duplicate_pvd_joliet(iso, filesize):
    assert(filesize == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_pvd(iso.pvds[1], extent=17, size=32, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_joliet(iso.svds[0], 32, 10, 25, 27)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 30)

    internal_check_root_dir_record(iso.pvds[1].root_dir_record, num_children=3, data_length=2048, extent_location=29, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 31, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    internal_check_file(iso.pvds[1].root_dir_record.children[2], b"FOO.;1", 40, 31, 4, hidden=False, num_linked_records=0)

def check_onefile_toolong(iso, filesize):
    assert(filesize == 51200)

    internal_check_pvd(iso.pvd, extent=16, size=25, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 24, 2048, hidden=False, num_linked_records=0)

def check_pvd_zero_datetime(iso, filesize):
    assert(filesize == 49152)

    internal_check_pvd(iso.pvd, extent=16, size=24, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=23, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    assert(iso.pvd.volume_creation_date.year == 0)
    assert(iso.pvd.volume_creation_date.month == 0)
    assert(iso.pvd.volume_creation_date.dayofmonth == 0)
    assert(iso.pvd.volume_creation_date.hour == 0)
    assert(iso.pvd.volume_creation_date.minute == 0)
    assert(iso.pvd.volume_creation_date.second == 0)
    assert(iso.pvd.volume_creation_date.hundredthsofsecond == 0)
    assert(iso.pvd.volume_creation_date.gmtoffset == 0)

def check_joliet_different_names(iso, filesize):
    assert(filesize == 67584)

    internal_check_pvd(iso.pvd, extent=16, size=33, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=28, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 29)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 116, 31, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOOJ.;1", 116, 32, 10, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, "/FOOJ.;1", b"foojoliet\n")

def check_hidden_joliet_file(iso, size):
    assert(size == 63488)

    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

def check_hidden_joliet_dir(iso, size):
    assert(size == 65536)

    internal_check_pvd(iso.pvd, extent=16, size=32, ptbl_size=22, ptbl_location_le=20, ptbl_location_be=22)

    internal_check_joliet(iso.svds[0], 32, 26, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)
    dir1_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name='dir1'.encode('utf-16_be'), len_di=8, loc=31, parent=1)

def check_rr_onefileonedir_hidden(iso, filesize):
    assert(filesize == 55296)

    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=22, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=23, rr=True, rr_nlinks=3, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_ptr(dir1_record.ptr, name=b'DIR1', len_di=4, loc=24, parent=1)

    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4, hidden=True, num_linked_records=0)
    internal_check_empty_directory(dir1_record, b"DIR1", 114, 24, rr=True, hidden=True)

def check_rr_onefile_onetwelve(iso, size):
    assert(size == 53248)

    internal_check_pvd(iso.pvd, extent=16, size=26, ptbl_size=10, ptbl_location_le=19, ptbl_location_be=21)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=23, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=23, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=True)

    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 118, 25, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")
    internal_check_file_contents(iso, "/foo", b"foo\n", which='rr_path')

def check_joliet_ident_encoding(iso, filesize):
    assert(filesize == 69632)

    # Do checks on the PVD.  With a Joliet ISO with one file, the ISO
    # should be 31 extents (24 extents for the metadata, 1 for the Joliet,
    # one for the Joliet root directory record, 4 for the Joliet path table
    # records, and 1 for the file contents). The path table should be 10 bytes
    # (for the root directory entry), the little endian path table should start
    # at extent 20, and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, extent=16, size=34, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_enhanced_vd(iso.enhanced_vd, 34, 10, 21, 23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.joliet_vd, 34, 10, 25, 27)
    assert(iso.joliet_vd.volume_identifier == 'cidata'.ljust(16, ' ').encode('utf-16_be'))
    assert(iso.joliet_vd.system_identifier == 'LINUX'.ljust(16, ' ').encode('utf-16_be'))

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=30, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=29, rr=True, rr_nlinks=2, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"meta-data", 124, 32, 25, hidden=False, num_linked_records=1)
    internal_check_file(iso.pvd.root_dir_record.children[3], b"user-data", 124, 33, 78, hidden=False, num_linked_records=1)

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "meta-data".encode('utf-16_be'), 52, 32, 25, hidden=False, num_linked_records=1)
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "user-data".encode('utf-16_be'), 52, 33, 78, hidden=False, num_linked_records=1)

def check_duplicate_pvd_isolevel4(iso, filesize):
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_pvd(iso.pvds[1], extent=17, size=27, ptbl_size=10, ptbl_location_le=21, ptbl_location_be=23)

    internal_check_enhanced_vd(iso.enhanced_vd, 27, 10, 21, 23)

    internal_check_terminator(iso.vdsts, extent=19)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=25, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=25, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

def check_joliet_hidden_iso_file(iso, filesize):
    assert(filesize == 63488)

    # Do checks on the PVD.  With a Joliet ISO with one file, the ISO
    # should be 31 extents (24 extents for the metadata, 1 for the Joliet,
    # one for the Joliet root directory record, 4 for the Joliet path table
    # records, and 1 for the file contents). The path table should be 10 bytes
    # (for the root directory entry), the little endian path table should start
    # at extent 20, and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, extent=16, size=31, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=28, parent=1)

    internal_check_ptr(iso.joliet_vd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=29, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=28, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 30, 4, hidden=False, num_linked_records=0)
    internal_check_file_contents(iso, "/foo", b"foo\n", 'joliet_path')

def check_eltorito_bootlink(iso, filesize):
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, extent=16, size=27, ptbl_size=10, ptbl_location_le=20, ptbl_location_be=22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    internal_check_terminator(iso.vdsts, extent=18)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=24, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=24, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048, hidden=False, num_linked_records=0)

    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOTLINK.;1", 44, 26, 5, hidden=False, num_linked_records=0)

    # Here, the initial entry is hidden, so we check it out by manually looking
    # for it in the raw output.  To do that in the current framework, we need
    # to re-write the iso into a string, then search the string.
    initial_entry_offset = iso.eltorito_boot_catalog.initial_entry.get_rba()

    # Re-render the output into a string.
    myout = BytesIO()
    iso.write_fp(myout)

    # Now seek within the string to the right location.
    myout.seek(initial_entry_offset * 2048)

    val = myout.read(5)
    assert(val == b"boot\n")

def check_udf_nofiles(iso, filesize):
    assert(filesize == 546816)

    internal_check_pvd(iso.pvd, extent=16, size=267, ptbl_size=10, ptbl_location_le=261, ptbl_location_be=263)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=265, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=2, data_length=2048, extent_location=265, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_udf_headers(iso, 266, 9, 261, 1, 0)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 1, 40, 1, True)

    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

def check_udf_onedir(iso, filesize):
    assert(filesize == 552960)

    internal_check_pvd(iso.pvd, extent=16, size=270, ptbl_size=22, ptbl_location_le=263, ptbl_location_be=265)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=267, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=267, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 268)

    internal_check_udf_headers(iso, 269, 12, 263, 2, 0)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 2, 84, 2, True)
    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    dir1_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(dir1_file_ident, 260, 3, 2, 4, 261, b"dir1", False, True)

    dir1_file_entry = dir1_file_ident.file_entry
    internal_check_udf_file_entry(dir1_file_entry, 261, 4, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(dir1_file_entry.fi_descs[0], 262, 5, 10, 2, 0, b"", True, True)

def check_udf_twodirs(iso, filesize):
    assert(filesize == 559104)

    internal_check_pvd(iso.pvd, extent=16, size=273, ptbl_size=34, ptbl_location_le=265, ptbl_location_be=267)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=269, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=269, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_udf_headers(iso, 272, 15, 265, 3, 0)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 3, 128, 3, True)
    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    dir1_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(dir1_file_ident, 260, 3, 2, None, None, b"dir1", False, True)

    dir1_file_entry = dir1_file_ident.file_entry
    internal_check_udf_file_entry(dir1_file_entry, None, None, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(dir1_file_entry.fi_descs[0], None, None, 10, 2, 0, b"", True, True)

    dir2_file_ident = iso.udf_root.fi_descs[2]
    internal_check_udf_file_ident_desc(dir2_file_ident, 260, 3, 2, None, None, b"dir2", False, True)

    dir2_file_entry = dir2_file_ident.file_entry
    internal_check_udf_file_entry(dir2_file_entry, None, None, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(dir2_file_entry.fi_descs[0], None, None, 10, 2, 0, b"", True, True)

def check_udf_subdir(iso, filesize):
    assert(filesize == 559104)

    internal_check_pvd(iso.pvd, extent=16, size=273, ptbl_size=38, ptbl_location_le=265, ptbl_location_be=267)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=269, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=269, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_udf_headers(iso, 272, 15, 265, 3, 0)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 2, 84, 2, True)
    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    dir1_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(dir1_file_ident, 260, 3, 2, 4, 261, b"dir1", False, True)

    dir1_file_entry = dir1_file_ident.file_entry
    internal_check_udf_file_entry(dir1_file_entry, 261, 4, 2, 88, 2, True)
    internal_check_udf_file_ident_desc(dir1_file_entry.fi_descs[0], 262, 5, 10, 2, 0, b"", True, True)

    subdir1_file_ident = dir1_file_entry.fi_descs[1]
    internal_check_udf_file_ident_desc(subdir1_file_ident, 262, 5, 2, 6, 263, b"subdir1", False, True)

    subdir1_file_entry = subdir1_file_ident.file_entry
    internal_check_udf_file_entry(subdir1_file_entry, 263, 6, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(subdir1_file_entry.fi_descs[0], 264, 7, 10, None, None, b"", True, True)

def check_udf_subdir_odd(iso, filesize):
    assert(filesize == 559104)

    internal_check_pvd(iso.pvd, extent=16, size=273, ptbl_size=36, ptbl_location_le=265, ptbl_location_be=267)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=269, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=269, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_udf_headers(iso, 272, 15, 265, 3, 0)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 2, 84, 2, True)
    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    dir1_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(dir1_file_ident, 260, 3, 2, 4, 261, b"dir1", False, True)

    dir1_file_entry = dir1_file_ident.file_entry
    internal_check_udf_file_entry(dir1_file_entry, 261, 4, 2, 88, 2, True)
    internal_check_udf_file_ident_desc(dir1_file_entry.fi_descs[0], 262, 5, 10, 2, 0, b"", True, True)

    subdi1_file_ident = dir1_file_entry.fi_descs[1]
    internal_check_udf_file_ident_desc(subdi1_file_ident, 262, 5, 2, 6, 263, b"subdi1", False, True)

    subdi1_file_entry = subdi1_file_ident.file_entry
    internal_check_udf_file_entry(subdi1_file_entry, 263, 6, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(subdi1_file_entry.fi_descs[0], 264, 7, 10, None, None, b"", True, True)

def check_udf_onefile(iso, filesize):
    assert(filesize == 550912)

    internal_check_pvd(iso.pvd, extent=16, size=269, ptbl_size=10, ptbl_location_le=262, ptbl_location_be=264)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=266, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=3, data_length=2048, extent_location=266, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 267, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n", which='iso_path')

    internal_check_udf_headers(iso, 268, 11, 262, 1, 1)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 1, 84, 2, True)

    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    foo_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(foo_file_ident, 260, 3, 0, 4, 261, b"foo", False, False)

    foo_file_entry = foo_file_ident.file_entry
    internal_check_udf_file_entry(foo_file_entry, 261, 4, 1, 4, 0, False)

    internal_check_file_contents(iso, '/foo', b"foo\n", which='udf_path')

def check_udf_onefileonedir(iso, filesize):
    assert(filesize == 557056)

    internal_check_pvd(iso.pvd, extent=16, size=272, ptbl_size=22, ptbl_location_le=264, ptbl_location_be=266)

    internal_check_terminator(iso.vdsts, extent=17)

    internal_check_ptr(iso.pvd.root_dir_record.ptr, name=b'\x00', len_di=1, loc=268, parent=1)

    internal_check_root_dir_record(iso.pvd.root_dir_record, num_children=4, data_length=2048, extent_location=268, rr=False, rr_nlinks=0, xa=False, rr_onetwelve=False)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_empty_directory(dir1_record, b"DIR1", 38, 269)

    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 270, 4, hidden=False, num_linked_records=1)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n", which='iso_path')

    internal_check_udf_headers(iso, 271, 14, 264, 2, 1)

    internal_check_udf_file_entry(iso.udf_root, 259, 2, 2, 128, 3, True)

    internal_check_udf_file_ident_desc(iso.udf_root.fi_descs[0], 260, 3, 10, 2, 0, b"", True, True)

    foo_file_ident = iso.udf_root.fi_descs[2]
    internal_check_udf_file_ident_desc(foo_file_ident, 260, 3, 0, 6, 263, b"foo", False, False)

    foo_file_entry = foo_file_ident.file_entry
    internal_check_udf_file_entry(foo_file_entry, 263, 6, 1, 4, 0, False)

    internal_check_file_contents(iso, '/foo', b"foo\n", which='udf_path')

    dir1_file_ident = iso.udf_root.fi_descs[1]
    internal_check_udf_file_ident_desc(dir1_file_ident, 260, 3, 2, 4, 261, b"dir1", False, True)

    dir1_file_entry = dir1_file_ident.file_entry
    internal_check_udf_file_entry(dir1_file_entry, 261, 4, 1, 40, 1, True)
    internal_check_udf_file_ident_desc(dir1_file_entry.fi_descs[0], 262, 5, 10, 2, 0, b"", True, True)
