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

################################ INTERNAL HELPERS #############################

def internal_check_pvd(pvd, extent, size, ptbl_size, ptbl_location_le, ptbl_location_be):
    # The primary volume descriptor should always have a type of 1.
    assert(pvd.descriptor_type == 1)
    # The primary volume descriptor should always have an identifier of "CD001".
    assert(pvd.identifier == b"CD001")
    # The primary volume descriptor should always have a version of 1.
    assert(pvd.version == 1)
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
    assert(en_vd.descriptor_type == 2)
    assert(en_vd.identifier == b"CD001")
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

def internal_check_eltorito(brs, boot_catalog, boot_catalog_extent, load_rba):
    # Now check the Eltorito Boot Record.

    # We support only one boot record for now.
    assert(len(brs) == 1)
    eltorito = brs[0]
    # The boot record should always have a type of 0.
    assert(eltorito.descriptor_type == 0)
    # The identifier should always be "CD001".
    assert(eltorito.identifier == b"CD001")
    # The version should always be 1.
    assert(eltorito.version == 1)
    # The boot_system_identifier for El Torito should always be a space-padded
    # version of "EL TORITO SPECIFICATION".
    assert(eltorito.boot_system_identifier == b"EL TORITO SPECIFICATION".ljust(32, b'\x00'))
    # The boot identifier should always be 32 zeros.
    assert(eltorito.boot_identifier == b"\x00"*32)
    # The boot_system_use field should always contain the boot catalog extent
    # encoded as a string.
    assert(eltorito.boot_system_use[:4] == struct.pack("=L", boot_catalog_extent))
    # The boot catalog validation entry should have a header id of 1.
    assert(boot_catalog.validation_entry.header_id == 1)
    # The boot catalog validation entry should have a platform id of 0.
    assert(boot_catalog.validation_entry.platform_id == 0)
    # The boot catalog validation entry should have an id string of all zeros.
    assert(boot_catalog.validation_entry.id_string == b"\x00"*24)
    # The boot catalog validation entry should have a checksum of 0x55aa.
    assert(boot_catalog.validation_entry.checksum == 0x55aa)
    # The boot catalog validation entry should have keybyte1 as 0x55.
    assert(boot_catalog.validation_entry.keybyte1 == 0x55)
    # The boot catalog validation entry should have keybyte2 as 0xaa.
    assert(boot_catalog.validation_entry.keybyte2 == 0xaa)

    # The boot catalog initial entry should have a boot indicator of 0x88.
    assert(boot_catalog.initial_entry.boot_indicator == 0x88)
    # The boot catalog initial entry should have a boot media type of 0.
    assert(boot_catalog.initial_entry.boot_media_type == 0)
    # The boot catalog initial entry should have a load segment of 0.
    assert(boot_catalog.initial_entry.load_segment == 0)
    # The boot catalog initial entry should have a system type of 0.
    assert(boot_catalog.initial_entry.system_type == 0)
    # The boot catalog initial entry should have a sector count of 4.
    assert(boot_catalog.initial_entry.sector_count == 4)
    # The boot catalog initial entry should have the correct load rba.
    if load_rba is not None:
        assert(boot_catalog.initial_entry.load_rba == load_rba)
    # The El Torito boot record should always be at extent 17.
    assert(eltorito.extent_location() == 17)

def internal_check_joliet(svd, space_size, path_tbl_size, path_tbl_loc_le,
                          path_tbl_loc_be):
    # The supplementary volume descriptor should always have a type of 2.
    assert(svd.descriptor_type == 2)
    # The supplementary volume descriptor should always have an identifier
    # of "CD001".
    assert(svd.identifier == b"CD001")
    # The supplementary volume descriptor should always have a version of 1.
    assert(svd.version == 1)
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
    assert(svd.escape_sequences == b'%/E'+b'\x00'*29)
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

    # The volume descriptor set terminator should always have a type of 255.
    assert(terminator.descriptor_type == 255)
    # The volume descriptor set terminatorshould always have an identifier
    # of "CD001".
    assert(terminator.identifier == b"CD001")
    # The volume descriptor set terminator should always have a version of 1.
    assert(terminator.version == 1)

    assert(terminator.extent_location() == extent)

def internal_check_root_dir_record(root_dir_record, num_children, data_length,
                                   extent_location, rr, rr_nlinks, xa=False):
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
    internal_check_dot_dir_record(root_dir_record.children[0], rr, rr_nlinks, True, xa)

    # Now check the "dotdot" directory record.
    internal_check_dotdot_dir_record(root_dir_record.children[1], rr, rr_nlinks, xa)

def internal_check_dot_dir_record(dot_record, rr, rr_nlinks, first_dot, xa):
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == b"\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34 with no extensions.
    if rr:
        if first_dot:
            # The "dot" record of the root directory record has extra Rock Ridge
            # information, so should be 136 bytes.
            expected_dr_len = 136
        else:
            # All other Rock Ridge "dot" entries are 102 bytes long.
            expected_dr_len = 102
    else:
        expected_dr_len = 34

    if xa:
        expected_dr_len += 14

    assert(dot_record.dr_len == expected_dr_len)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 2)

    if rr:
        assert(dot_record.rock_ridge.initialized == True)
        assert(dot_record.rock_ridge.su_entry_version == 1)
        if first_dot:
            assert(dot_record.rock_ridge.sp_record != None)
            if xa:
                assert(dot_record.rock_ridge.sp_record.bytes_to_skip == 14)
            else:
                assert(dot_record.rock_ridge.sp_record.bytes_to_skip == 0)
        else:
            assert(dot_record.rock_ridge.sp_record == None)
        assert(dot_record.rock_ridge.rr_record != None)
        assert(dot_record.rock_ridge.rr_record.rr_flags == 0x81)
        if first_dot:
            assert(dot_record.rock_ridge.ce_record != None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.sp_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.rr_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.ce_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.px_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record != None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_id == b'RRIP_1991A')
            assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_des == b'THE ROCK RIDGE INTERCHANGE PROTOCOL PROVIDES SUPPORT FOR POSIX FILE SYSTEM SEMANTICS')
            assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_src == b'PLEASE CONTACT DISC PUBLISHER FOR SPECIFICATION SOURCE.  SEE PUBLISHER IDENTIFIER IN PRIMARY VOLUME DESCRIPTOR FOR CONTACT INFORMATION.')
            assert(dot_record.rock_ridge.ce_record.continuation_entry.es_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.pn_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.sl_records == [])
            assert(dot_record.rock_ridge.ce_record.continuation_entry.nm_records == [])
            assert(dot_record.rock_ridge.ce_record.continuation_entry.cl_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.pl_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.tf_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.sf_record == None)
            assert(dot_record.rock_ridge.ce_record.continuation_entry.re_record == None)
        else:
            assert(dot_record.rock_ridge.ce_record == None)
        assert(dot_record.rock_ridge.px_record != None)
        assert(dot_record.rock_ridge.px_record.posix_file_mode == 0o040555)
        assert(dot_record.rock_ridge.px_record.posix_file_links == rr_nlinks)
        assert(dot_record.rock_ridge.px_record.posix_user_id == 0)
        assert(dot_record.rock_ridge.px_record.posix_group_id == 0)
        assert(dot_record.rock_ridge.px_record.posix_serial_number == 0)
        assert(dot_record.rock_ridge.er_record == None)
        assert(dot_record.rock_ridge.es_record == None)
        assert(dot_record.rock_ridge.pn_record == None)
        assert(dot_record.rock_ridge.sl_records == [])
        assert(dot_record.rock_ridge.nm_records == [])
        assert(dot_record.rock_ridge.cl_record == None)
        assert(dot_record.rock_ridge.pl_record == None)
        assert(dot_record.rock_ridge.tf_record != None)
        assert(dot_record.rock_ridge.tf_record.creation_time == None)
        assert(type(dot_record.rock_ridge.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(dot_record.rock_ridge.tf_record.backup_time == None)
        assert(dot_record.rock_ridge.tf_record.expiration_time == None)
        assert(dot_record.rock_ridge.tf_record.effective_time == None)
        assert(dot_record.rock_ridge.sf_record == None)
        assert(dot_record.rock_ridge.re_record == None)

def internal_check_dotdot_dir_record(dotdot_record, rr, rr_nlinks, xa):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == b"\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34 with no extensions.
    if rr:
        # The "dotdot" directory record length should be exactly 102 with Rock Ridge.
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
        assert(dotdot_record.rock_ridge.initialized == True)
        assert(dotdot_record.rock_ridge.su_entry_version == 1)
        assert(dotdot_record.rock_ridge.sp_record == None)
        assert(dotdot_record.rock_ridge.rr_record != None)
        assert(dotdot_record.rock_ridge.rr_record.rr_flags == 0x81)
        assert(dotdot_record.rock_ridge.ce_record == None)
        assert(dotdot_record.rock_ridge.px_record != None)
        assert(dotdot_record.rock_ridge.px_record.posix_file_mode == 0o040555)
        assert(dotdot_record.rock_ridge.px_record.posix_file_links == rr_nlinks)
        assert(dotdot_record.rock_ridge.px_record.posix_user_id == 0)
        assert(dotdot_record.rock_ridge.px_record.posix_group_id == 0)
        assert(dotdot_record.rock_ridge.px_record.posix_serial_number == 0)
        assert(dotdot_record.rock_ridge.er_record == None)
        assert(dotdot_record.rock_ridge.es_record == None)
        assert(dotdot_record.rock_ridge.pn_record == None)
        assert(dotdot_record.rock_ridge.sl_records == [])
        assert(dotdot_record.rock_ridge.nm_records == [])
        assert(dotdot_record.rock_ridge.cl_record == None)
        assert(dotdot_record.rock_ridge.pl_record == None)
        assert(dotdot_record.rock_ridge.tf_record != None)
        assert(dotdot_record.rock_ridge.tf_record.creation_time == None)
        assert(type(dotdot_record.rock_ridge.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(dotdot_record.rock_ridge.tf_record.backup_time == None)
        assert(dotdot_record.rock_ridge.tf_record.expiration_time == None)
        assert(dotdot_record.rock_ridge.tf_record.effective_time == None)
        assert(dotdot_record.rock_ridge.sf_record == None)
        assert(dotdot_record.rock_ridge.re_record == None)

def internal_check_file_contents(iso, path, contents):
    fout = BytesIO()
    iso.get_and_write_fp(path, fout)
    assert(fout.getvalue() == contents)

def internal_check_ptr(ptr, name, len_di, loc, parent):
    assert(ptr.len_di == len_di)
    assert(ptr.xattr_length == 0)
    if loc >= 0:
        assert(ptr.extent_location == loc)
    if parent > 0:
        assert(ptr.parent_directory_num == parent)
    assert(ptr.directory_identifier == name)
    assert(ptr.dirrecord is not None)
    assert(ptr.directory_num is not None)

def internal_check_empty_directory(dirrecord, name, dr_len, extent=None,
                                   rr=False, hidden=False):
    internal_check_dir_record(dirrecord, 2, name, dr_len, extent, rr, b'dir1', 2, False, hidden)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr, 3, False)

def internal_check_file(dirrecord, name, dr_len, loc, datalen, hidden=False):
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

def internal_generate_inorder_names(numdirs):
    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append(b"DIR" + bytes(str(i).encode('ascii')))
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    return names

def internal_check_dir_record(dir_record, num_children, name, dr_len,
                              extent_location, rr, rr_name, rr_links, xa, hidden=False):
    # The directory should have the number of children passed in.
    assert(len(dir_record.children) == num_children)
    # The directory should be a directory.
    assert(dir_record.isdir == True)
    # The directory should not be the root.
    assert(dir_record.is_root == False)
    # The directory should have an ISO9660 mangled name the same as passed in.
    assert(dir_record.file_ident == name)
    # The directory record should have a dr_len as passed in.
    assert(dir_record.dr_len == dr_len)
    # The "dir1" directory record should be at the extent passed in.
    if extent_location is not None:
        assert(dir_record.extent_location() == extent_location)
    if hidden:
        assert(dir_record.file_flags == 3)
    else:
        assert(dir_record.file_flags == 2)

    if rr:
        assert(dir_record.rock_ridge.sp_record == None)
        assert(dir_record.rock_ridge.rr_record != None)
        assert(dir_record.rock_ridge.rr_record.rr_flags == 0x89)
        assert(dir_record.rock_ridge.ce_record == None)
        assert(dir_record.rock_ridge.px_record != None)
        assert(dir_record.rock_ridge.px_record.posix_file_mode == 0o040555)
        assert(dir_record.rock_ridge.px_record.posix_file_links == rr_links)
        assert(dir_record.rock_ridge.px_record.posix_user_id == 0)
        assert(dir_record.rock_ridge.px_record.posix_group_id == 0)
        assert(dir_record.rock_ridge.px_record.posix_serial_number == 0)
        assert(dir_record.rock_ridge.er_record == None)
        assert(dir_record.rock_ridge.es_record == None)
        assert(dir_record.rock_ridge.pn_record == None)
        assert(dir_record.rock_ridge.sl_records == [])
        assert(len(dir_record.rock_ridge.nm_records) > 0)
        assert(dir_record.rock_ridge.nm_records[0].posix_name == rr_name)
        assert(dir_record.rock_ridge.cl_record == None)
        assert(dir_record.rock_ridge.pl_record == None)
        assert(dir_record.rock_ridge.tf_record != None)
        assert(dir_record.rock_ridge.tf_record.creation_time == None)
        assert(type(dir_record.rock_ridge.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dir_record.rock_ridge.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
        assert(type(dir_record.rock_ridge.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
        assert(dir_record.rock_ridge.tf_record.backup_time == None)
        assert(dir_record.rock_ridge.tf_record.expiration_time == None)
        assert(dir_record.rock_ridge.tf_record.effective_time == None)
        assert(dir_record.rock_ridge.sf_record == None)
        assert(dir_record.rock_ridge.re_record == None)

    # The "dir1" directory record should have a valid "dot" record.
    internal_check_dot_dir_record(dir_record.children[0], rr, rr_links, False, xa)

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

def internal_check_rr_longname(iso, dir_record, extent, letter):
    internal_check_file(dir_record, letter.upper()*8+b".;1", None, extent, 3)
    internal_check_file_contents(iso, b"/"+letter.upper()*8+b".;1", letter*2+b"\n")
    # Now check rock ridge extensions.
    assert(dir_record.rock_ridge.sp_record == None)
    assert(dir_record.rock_ridge.rr_record != None)
    assert(dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dir_record.rock_ridge.ce_record != None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.sp_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.rr_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.ce_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record != None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0o0100444)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.er_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.es_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.pn_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.sl_records == [])
    assert(len(dir_record.rock_ridge.ce_record.continuation_entry.nm_records) > 0)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.cl_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.pl_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.tf_record != None)
    assert(type(dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.sf_record == None)
    assert(dir_record.rock_ridge.ce_record.continuation_entry.re_record == None)
    assert(dir_record.rock_ridge.px_record == None)
    assert(dir_record.rock_ridge.er_record == None)
    assert(dir_record.rock_ridge.es_record == None)
    assert(dir_record.rock_ridge.pn_record == None)
    assert(dir_record.rock_ridge.sl_records == [])
    assert(len(dir_record.rock_ridge.nm_records) > 0)
    assert(dir_record.rock_ridge.nm_records[0].posix_name_flags == 1)
    assert(dir_record.rock_ridge.name() == letter*RR_MAX_FILENAME_LENGTH)
    assert(dir_record.rock_ridge.cl_record == None)
    assert(dir_record.rock_ridge.pl_record == None)
    assert(dir_record.rock_ridge.tf_record == None)
    assert(dir_record.rock_ridge.sf_record == None)
    assert(dir_record.rock_ridge.re_record == None)
    internal_check_file_contents(iso, b"/"+letter*RR_MAX_FILENAME_LENGTH, letter*2+b"\n")

def internal_check_rr_file(dir_record, name):
    assert(dir_record.rock_ridge.initialized == True)
    assert(dir_record.rock_ridge.sp_record == None)
    assert(dir_record.rock_ridge.rr_record != None)
    assert(dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dir_record.rock_ridge.ce_record == None)
    assert(dir_record.rock_ridge.px_record != None)
    assert(dir_record.rock_ridge.px_record.posix_file_mode == 0o0100444)
    assert(dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.er_record == None)
    assert(dir_record.rock_ridge.es_record == None)
    assert(dir_record.rock_ridge.pn_record == None)
    assert(dir_record.rock_ridge.sl_records == [])
    assert(len(dir_record.rock_ridge.nm_records) > 0)
    assert(dir_record.rock_ridge.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.nm_records[0].posix_name == name)
    assert(dir_record.rock_ridge.cl_record == None)
    assert(dir_record.rock_ridge.pl_record == None)
    assert(dir_record.rock_ridge.tf_record != None)
    assert(dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dir_record.rock_ridge.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(dir_record.rock_ridge.tf_record.backup_time == None)
    assert(dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(dir_record.rock_ridge.tf_record.effective_time == None)
    assert(dir_record.rock_ridge.sf_record == None)
    assert(dir_record.rock_ridge.re_record == None)

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
    assert(dir_record.rock_ridge.initialized == True)
    assert(dir_record.rock_ridge.sp_record == None)
    assert(dir_record.rock_ridge.rr_record != None)
    assert(dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(dir_record.rock_ridge.ce_record == None)
    assert(dir_record.rock_ridge.px_record != None)
    assert(dir_record.rock_ridge.px_record.posix_file_mode == 0o0120555)
    assert(dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dir_record.rock_ridge.er_record == None)
    assert(dir_record.rock_ridge.es_record == None)
    assert(dir_record.rock_ridge.pn_record == None)
    assert(dir_record.rock_ridge.is_symlink() == True)
    assert(len(dir_record.rock_ridge.sl_records) == 1)
    assert(len(dir_record.rock_ridge.sl_records[0].symlink_components) == len(comps))
    for index,comp in enumerate(comps):
        assert(dir_record.rock_ridge.sl_records[0].symlink_components[index].name() == comp)
    assert(len(dir_record.rock_ridge.nm_records) > 0)
    assert(dir_record.rock_ridge.nm_records[0].posix_name_flags == 0)
    assert(dir_record.rock_ridge.nm_records[0].posix_name == b'sym')
    assert(dir_record.rock_ridge.cl_record == None)
    assert(dir_record.rock_ridge.pl_record == None)
    assert(dir_record.rock_ridge.tf_record != None)
    assert(dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dir_record.rock_ridge.tf_record.access_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.tf_record.modification_time) == pycdlib.dates.DirectoryRecordDate)
    assert(type(dir_record.rock_ridge.tf_record.attribute_change_time) == pycdlib.dates.DirectoryRecordDate)
    assert(dir_record.rock_ridge.tf_record.backup_time == None)
    assert(dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(dir_record.rock_ridge.tf_record.effective_time == None)
    assert(dir_record.rock_ridge.sf_record == None)
    assert(dir_record.rock_ridge.re_record == None)

######################## EXTERNAL CHECKERS #####################################
def check_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 49152)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 24, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, False, 0)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        iso.get_and_write_fp("/FOO.;1", BytesIO())

def check_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there
    # are no volume descriptors beyond the primary and the terminator), and
    # the big endian path table should start at extent 21 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With just one file, there should
    # be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # file), the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the file itself.  The file should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 24,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 24, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With just one dir, there should
    # be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The first entry in the PTR should have an identifier of 'DIR1', it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the one empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"DIR1", 38, 24)

def check_twofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With two files, the ISO should be 26 extents (24
    # extents for the metadata, and 1 extent for each of the two short files).
    # The path table should be 10 bytes (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there
    # are no volume descriptors beyond the primary and the terminator), and
    # the big endian path table should start at extent 21 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With two files, there should be
    # just one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With two files at the root, the
    # root directory record should have 4 entries ("dot", "dotdot", and the
    # two files), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the first file.  It should have a name of BAR.;1, it should
    # have a directory record length of 40, it should start at extent 24,
    # and its contents should be "bar\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

    # Now check the second file.  It should have a name of FOO.;1, it should
    # have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_twodirs(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With two directories, the ISO should be 26 extents
    # (24 extents for the metadata, and one extent for each of the two
    # directories).  The path table should be exactly 30 bytes (for the root
    # directory entry and the two directories), the little endian path table
    # should start at extent 19 (default when there are no volume descriptors
    # beyond the primary and the terminator), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 30, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With two directories, there should
    # be three entries (the root entry, and the two directories).
    assert(len(iso.pvd.path_table_records) == 3)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of 'AA', it
    # should have a len of 2, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'AA', 2, -1, 1)
    # The second entry in the PTR should have an identifier of 'BB', it
    # should have a len of 2, it should start at extent 25, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[2], b'BB', 2, -1, 1)

    # Now check the root directory record.  With two directories at the root,
    # the root directory record should have 4 entries ("dot", "dotdot",
    # and the two directories), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 23 (2 beyond the
    # big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the first empty directory.  Its name should be AA, and it should
    # start at extent 24.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"AA", 36, None)
    # Now check the second empty directory.  Its name should be BB, and it
    # should start at extent 25.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[3], b"BB", 36, None)

def check_onefileonedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file and one directory, the ISO should be
    # 26 extents (24 extents for the metadata, 1 extent for the file, and 1
    # extent for the directory).  The path table should be 22 bytes (10
    # bytes for the root directory entry, and 12 bytes for the "dir1" entry),
    # the little endian path table should start at extent 19 (default when
    # there are no volume descriptors beyond the primary and the terminator),
    # and the big endian path table should start at extent 21 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one directory,
    # there should be two entries (the root entry and the one directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have 4 entries ("dot",
    # "dotdot", the one file, and the one directory), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"DIR1", 38, 24)

    # Now check the file.  It should have a name of FOO.;1, it should
    # have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Check to make sure accessing a directory raises an exception.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        iso.get_and_write_fp("/DIR1", BytesIO())

def check_onefile_onedirwithfile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With one file and one directory with a file, the
    # ISO should be 27 extents (24 extents for the metadata, 1 extent for the
    # file, 1 extent for the directory, and 1 more extent for the file.  The
    # path table should be 22 bytes (10 bytes for the root directory entry, and
    # 12 bytes for the "dir1" entry), the little endian path table should start
    # at extent 19 (default when there are no volume descriptors beyond the
    # primary and the terminator), and the big endian path table should start
    # at extent 21 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one directory,
    # there should be two entries (the root entry and the one directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have 4 entries ("dot",
    # "dotdot", the one file, and the one directory), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the file within it), the name should be DIR1, and it should start
    # at extent 24.
    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_record, 3, b"DIR1", 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], False, 3, False)

    # Now check the file at the root.  It should have a name of FOO.;1, it
    # should have a directory record length of 40, it should start at extent 25,
    # and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the file in the subdirectory.  It should have a name of BAR.;1,
    # it should have a directory record length of 40, it should start at
    # extent 26, and its contents should be "bar\n".
    internal_check_file(dir1_record.children[2], b"BAR.;1", 40, 26, 4)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", b"bar\n")

def check_twoextentfile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file, the ISO should be 26 extents (24
    # extents for the metadata, and 2 extents for the file).  The path table
    # should be 10 bytes (10 bytes for the root directory entry), the little
    # endian path table should start at extent 19 (default when there are no
    # volume descriptors beyond the primary and the terminator), and the big
    # endian path table should start at extent 21 (since the little endian
    # path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With just one file, there should
    # be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # file), the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the file at the root.  It should have a name of BIGFILE.;1, it
    # should have a directory record length of 44, it should start at extent 24,
    # and its contents should be the bytes 0x0-0xff, repeating 8 times plus one.
    outstr = b""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BIGFILE.;1", 44, 24, 2049)
    internal_check_file_contents(iso, "/BIGFILE.;1", outstr)

def check_twoleveldeepdir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With a two level deep directory, the ISO should be
    # 26 extents (24 extents for the metadata, 1 for the directory at the root,
    # and one for the subdirectory).  The path table should be 38 bytes (10
    # bytes for the root directory entry, 12 for the first ptr, and 16 for the
    # second directory entry), the little endian path table should start at
    # extent 19 (default when there are no volume descriptors beyond the primary
    # and the terminator), and the big endian path table should start at
    # extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 38, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With a directory and a
    # subdirectory, there should be three entries (the root entry, the
    # directory and the subdirectory).
    assert(len(iso.pvd.path_table_records) == 3)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)
    # The third entry in the PTR should have an identifier of SUBDIR1, it
    # should have a len of 7, it should start at extent 25, and its parent
    # directory number should be 2.
    internal_check_ptr(iso.pvd.path_table_records[2], b'SUBDIR1', 7, 25, 2)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the subdirectory), the name should be DIR1, and it should start
    # at extent 24.
    dir1 = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1, 3, b'DIR1', 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1.children[1], False, 3, False)

    # Now check the empty subdirectory record.  The name should be SUBDIR1.
    subdir1 = dir1.children[2]
    internal_check_empty_directory(subdir1, b'SUBDIR1', 40, 25)

def check_tendirs(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 69632)

    # Do checks on the PVD.  With ten directories, the ISO should be 34 extents
    # (24 extents for the metadata, plus 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, plus 12*9=108 for the first 9 directories + 14 for the
    # last directory entry), the little endian path table should start at
    # extent 19 (default when there are no volume descriptors beyond the primary
    # and the terminator), and the big endian path table should start at
    # extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 34, 132, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With ten directories at the root,
    # the root directory record should have 12 entries ("dot", "dotdot", and the
    # ten directories), the data length is exactly one extent (2048 bytes),
    # and the root directory should start at extent 23 (2 beyond the big
    # endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 12, 2048, 23, False, 0)

    # Now check out the path table records.  With ten directories, there should
    # be a total of 11 entries (the root entry and the ten directories).
    assert(len(iso.pvd.path_table_records) == 10+1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(10)
    for index in range(2, 2+10):
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index], 38)

def check_dirs_overflow_ptr_extent(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 671744)

    # Do checks on the PVD.  With 295 directories, the ISO should be 328 extents
    # (33 extents for the metadata, plus 1 extent for each of the 295
    # directories).  The path table should be 4122 bytes (10 bytes for the root
    # directory entry, plus 12*9=108 for the first 9 directories + 14*90=1260
    # bytes for DIR10-DIR99 + 14*196=2744 for DIR100-DIR295), the little endian
    # path table should start at extent 19 (default when there are no volume
    # descriptors beyond the primary and the terminator), and the big endian
    # path table should start at extent 23 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 328, 4122, 19, 23)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With 295 directories at the root,
    # the root directory record should have 297 entries ("dot", "dotdot", and
    # the 295 directories), the data length is 6 extents, and the root
    # directory should start at extent 27 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 297, 12288, 27, False, 0)

    # Now check out the path table records.  With 295 directories, there should
    # be a total of 296 entries (the root entry and the 295 directories).
    assert(len(iso.pvd.path_table_records) == 295+1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 27, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(295)
    for index in range(2, 2+295):
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index], 33 + len(names[index]) + (1 - (len(names[index]) % 2)))

def check_dirs_just_short_ptr_extent(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 659456)

    # Do checks on the PVD.  With 293 directories, the ISO should be 322 extents
    # (29 extents for the metadata, plus 1 extent for each of the 293
    # directories).  The path table should be 4122 bytes (10 bytes for the root
    # directory entry, plus 12*9=108 for the first 9 directories + 14*90=1260
    # bytes for DIR10-DIR99 + 14*194=2716 for DIR100-DIR293), the little endian
    # path table should start at extent 19 (default when there are no volume
    # descriptors beyond the primary and the terminator), and the big endian
    # path table should start at extent 21 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 322, 4094, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With 293 directories at the root,
    # the root directory record should have 295 entries ("dot", "dotdot", and
    # the 293 directories), the data length is 6 extents, and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 295, 12288, 23, False, 0)

    # Now check out the path table records.  With 293 directories, there should
    # be a total of 294 entries (the root entry and the 293 directories).
    assert(len(iso.pvd.path_table_records) == 293+1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(293)
    for index in range(2, 2+293):
        # We skip checking the path table record extent locations because
        # genisoimage seems to have a bug assigning the extent locations, and
        # seems to assign them in reverse order.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index], 33 + len(names[index]) + (1 - (len(names[index]) % 2)))

def check_twoleveldeepfile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With a two level deep file, the ISO should be
    # 27 extents (24 extents for the metadata, 1 for the directory at the root,
    # one for the subdirectory, and one for the file).  The path table should
    # be 38 bytes (10 bytes for the root directory entry, 12 for the first ptr,
    # and 16 for the second directory entry), the little endian path table
    # should start at extent 19 (default when there are no volume descriptors
    # beyond the primary and the terminator), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 38, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With a directory and a
    # subdirectory, there should be three entries (the root entry, the
    # directory and the subdirectory).
    assert(len(iso.pvd.path_table_records) == 3)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)
    # The third entry in the PTR should have an identifier of SUBDIR1, it
    # should have a len of 7, it should start at extent 25, and its parent
    # directory number should be 2.
    internal_check_ptr(iso.pvd.path_table_records[2], b'SUBDIR1', 7, 25, 2)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the directory record.  It should have 3 children (dot, dotdot,
    # and the subdirectory), the name should be DIR1, and it should start
    # at extent 24.
    dir1 = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1, 3, b'DIR1', 38, 24, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1.children[1], False, 3, False)

    # Now check the sub-directory record.  It should have 3 children (dot,
    # dotdot, and the subdirectory), the name should be DIR1, and it should
    # start at extent 25.
    subdir1 = dir1.children[2]
    internal_check_dir_record(subdir1, 3, b'SUBDIR1', 40, 25, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(subdir1.children[1], False, 3, False)

    # Now check the file in the subdirectory.  It should have a name of FOO.;1,
    # it should have a directory record length of 40, it should start at
    # extent 26, and its contents should be "foo\n".
    internal_check_file(subdir1.children[2], b"FOO.;1", 40, 26, 4)
    internal_check_file_contents(iso, "/DIR1/SUBDIR1/FOO.;1", b"foo\n")

def check_joliet_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 61440)

    # Do checks on the PVD.  With a Joliet ISO with no files, the ISO should be
    # 30 extents (24 extents for the metadata, 1 for the Joliet, one for the
    # Joliet root directory record, and 4 for the Joliet path table records).
    # The path table should be 10 bytes (10 bytes for the root directory entry),
    # the little endian path table should start at extent 20, and the big
    # endian path table should start at extent 22 (since the little endian path
    # table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 30, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 30, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot", and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 28 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 28, False, 0)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_joliet_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With a Joliet ISO with one directory, the ISO
    # should be 32 extents (24 extents for the metadata, 1 for the directory,
    # 1 for the Joliet, one for the Joliet root directory record, 4 for the
    # Joliet path table records, and 1 for the joliet directory). The path
    # table should be 22 bytes (10 bytes for the root directory entry and 12
    # bytes for the directory), the little endian path table should start at
    # extent 20, and the big endian path table should start at extent 22 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 32, 22, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # directory, the number of extents should be the same as the PVD, the path
    # table should be 26 bytes (10 bytes for the root directory entry, and 16
    # bytes for the directory), the little endian path table should start at
    # extent 24, and the big endian path table should start at extent 26 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one directory, there should be
    # two entries (the root entry, and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 31, 1)

    # Now check the root directory record.  With one directory, the root
    # directory record should have 3 entries ("dot", "dotdot", and directory),
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 28 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0)

    # Now check the empty subdirectory record.  The name should be DIR1, and
    # it should start at extent 29.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"DIR1", 38, 29)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the directory), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 30 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the empty Joliet subdirectory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(iso.joliet_vd.root_dir_record.children[2], "dir1".encode('utf-16_be'), 42, 31)

def check_joliet_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 63488)

    # Do checks on the PVD.  With a Joliet ISO with one file, the ISO
    # should be 31 extents (24 extents for the metadata, 1 for the Joliet,
    # one for the Joliet root directory record, 4 for the Joliet path table
    # records, and 1 for the file contents). The path table should be 10 bytes
    # (for the root directory entry), the little endian path table should start
    # at extent 20, and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 31, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file, the number of extents should be the same as the PVD, the path
    # table should be 10 bytes (for the root directory entry), the little
    # endian path table should start at extent 24, and the big endian path
    # table should start at extent 26 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With one file, the root directory
    # record should have 3 entries ("dot", "dotdot", and the file), the data
    # length is exactly one extent (2048 bytes), and the root directory should
    # start at extent 28 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0)

    # Now check the Joliet root directory record.  With one file, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the file), the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 29 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 40, 30, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 30, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_joliet_onefileonedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With a Joliet ISO with one file and one directory,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the
    # directory, 1 for the Joliet, one for the Joliet root directory record, one
    # for the joliet directory, 4 for the Joliet path table records, and 1 for
    # the file contents). The path table should be 22 bytes (10 bytes for the
    # root directory entry and 12 bytes for the directory), the little endian
    # path table should start at extent 20, and the big endian path table
    # should start at extent 22 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 22, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file and one directory, the number of extents should be the same as the
    # PVD, the path table should be 26 bytes (10 bytes for the root directory
    # entry and 16 bytes for the directory), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file and one directory,
    # there should be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 31, 1)

    # Now check the root directory record.  With one file and one directory,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 28 (2 beyond the
    # big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 28, False, 0)

    # Now check the empty directory record.  The name should be DIR1, and it
    # should start at extent 29.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"DIR1", 38, 29)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the empty Joliet directory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(iso.joliet_vd.root_dir_record.children[2], "dir1".encode('utf-16_be'), 42, 31)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 32, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "foo".encode('utf-16_be'), 40, 32, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_eltorito_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 25, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_eltorito_twofile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With two files and eltorito, the ISO should be 28
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, 1 for the boot file, and 1 for the additional
    # file), the path table should be exactly 10 bytes long (the root directory
    # entry), the little endian path table should start at extent 20 (default
    # when there is just the PVD and the Eltorito Boot Record), and the big
    # endian path table should start at extent 22 (since the little endian path
    # table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With two files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With two files, the root directory
    # record should have 5 entries ("dot", "dotdot", the boot file, the boot
    # catalog, and the second file), the data length is exactly one extent
    # (2048 bytes), and the root directory should start at extent 24 (2 beyond
    # the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[4], b"BOOT.CAT;1", 44, 25, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.;1", 40, 26, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the aa file.  It should have a name of AA.;1, it should
    # have a directory record length of 40, it should start at extent 27, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AA.;1", 38, 27, 3)
    internal_check_file_contents(iso, "/AA.;1", b"aa\n")

def check_rr_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 25 extents (24
    # extents for the metadata, and 1 for the Rock Ridge ER record), the path
    # table should be exactly 10 bytes long (the root directory entry), the
    # little endian path table should start at extent 19 (default when there is
    # just the PVD), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot", and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, True, 2)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        iso.get_and_write_fp("/FOO.;1", BytesIO())

def check_rr_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file, the ISO should be 26 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER record, and 1 for the
    # file), the path table should be exactly 10 bytes long (the root directory
    # entry), the little endian path table should start at extent 19 (default
    # when there is just the PVD), and the big endian path table should start
    # at extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 3 entries ("dot", "dotdot", and the file), the data
    # length is exactly one extent (2048 bytes), and the root directory should
    # start at extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Make sure trying to get a non-existent file raises an exception
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        iso.get_and_write_fp("/BAR.;1", BytesIO())

def check_rr_twofile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With two files, the ISO should be 27 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER record, and 1 for each
    # of the files), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With two files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With two files, the root directory
    # record should have 4 entries ("dot", "dotdot", and the two files), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 23 (2 beyond the big endian path table record
    # entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    # Now check the bar file.  It should have a name of BAR.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "bar\n".
    bar_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(bar_dir_record, b"BAR.;1", 116, 25, 4)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # bar, and contain "bar\n".
    internal_check_rr_file(bar_dir_record, b'bar')
    internal_check_file_contents(iso, "/bar", b"bar\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_rr_onefileonedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With one file and one directory, the ISO should be
    # 27 extents (24 extents for the metadata, 1 for the Rock Ridge ER record,
    # 1 for the file, and one for the directory), the path table should be
    # exactly 22 bytes long (10 bytes for the root directory entry and 12 bytes
    # for the directory), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one directory,
    # there should be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 23 (2 beyond the
    # big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    # Now check the empty directory record.  The name should be DIR1, the
    # directory record length should be 114 (for the Rock Ridge), it should
    # start at extent 24, and it should have Rock Ridge.
    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_empty_directory(dir1_dir_record, b"DIR1", 114, 24, True)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_rr_onefileonedirwithfile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With one file and one directory with a file, the
    # ISO should be 28 extents (24 extents for the metadata, 1 for the
    # Rock Ridge ER record, 1 for the file, one for the directory, and one for
    # the file in the directory), the path table should be exactly 22 bytes
    # long (10 bytes for the root directory entry and 12 bytes for the
    # directory), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one directory,
    # with a file, there should be two entries (the root entry and the
    # directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory
    # with a file in it, the root directory record should have 4 entries
    # ("dot", "dotdot", the file, and the directory), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    # Now check the directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 24, and it should have Rock
    # Ridge.
    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_dir_record, 3, b"DIR1", 114, 24, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_dir_record.children[1], True, 3, False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the bar file.  It should have a name of BAR.;1, it should
    # have a directory record length of 116, it should start at extent 27, and
    # its contents should be "bar\n".
    bar_dir_record = dir1_dir_record.children[2]
    internal_check_file(bar_dir_record, b"BAR.;1", 116, 27, 4)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", b"bar\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # bar, and contain "bar\n".
    internal_check_rr_file(bar_dir_record, b'bar')
    internal_check_file_contents(iso, "/dir1/bar", b"bar\n")

def check_rr_symlink(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file and one symlink, the ISO should be
    # 26 extents (24 extents for the metadata, 1 for the Rock Ridge ER record,
    # and 1 for the file), the path table should be 10 bytes long (for the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table should
    # start at extent 21 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one symlink,
    # there should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one file and one symlink,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the symlink), the data length is exactly one extent
    # (2048 bytes), and the root directory should start at extent 23 (2 beyond
    # the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 26, [b'foo'])

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibException):
        internal_check_file_contents(iso, "/sym", b"foo\n")

def check_rr_symlink2(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With one directory with a file and one symlink,
    # the ISO should be 27 extents (24 extents for the metadata, 1 for the
    # Rock Ridge ER record, 1 for the directory, and one for the file), the path
    # table should be 22 bytes long (10 bytes for the root directory entry and
    # 12 bytes for the directory), the little endian path table should start at
    # extent 19 (default when there is just the PVD), and the big endian path
    # table should start at extent 21 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one directory with a file and
    # one symlink, there should be two entries (the root entry and the
    # directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one directory with a file and
    # one symlink, the root directory record should have 4 entries ("dot",
    # "dotdot", the directory, and the symlink), the data length is exactly one
    # extent (2048 bytes), and the root directory should start at extent 23 (2
    # beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    # Now check the directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 24, and it should have Rock
    # Ridge.
    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_dir_record, 3, b"DIR1", 114, 24, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_dir_record.children[1], True, 3, False)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 26, and
    # its contents should be "foo\n".
    foo_dir_record = dir1_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 26, 4)
    internal_check_file_contents(iso, "/DIR1/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/dir1/foo", b"foo\n")

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 132, 26, [b'dir1', b'foo'])

def check_rr_symlink_dot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one symlink to dot, the ISO should be 25
    # extents (24 extents for the metadata, and 1 for the Rock Ridge ER record),
    # the path table should be 10 bytes long (for the root directory entry)
    # the little endian path table should start at extent 19 (default when
    # there is just the PVD), and the big endian path table should start at
    # extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one symlink, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one symlink, the root
    # directory record should have 3 entries ("dot", "dotdot", and the symlink),
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 122, 25, [b'.'])

def check_rr_symlink_dotdot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one symlink to dotdot, the ISO should be 25
    # extents (24 extents for the metadata, and 1 for the Rock Ridge ER record),
    # the path table should be 10 bytes long (for the root directory entry)
    # the little endian path table should start at extent 19 (default when
    # there is just the PVD), and the big endian path table should start at
    # extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one symlink, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one symlink, the root
    # directory record should have 3 entries ("dot", "dotdot", and the symlink),
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 122, 25, [b'..'])

def check_rr_symlink_broken(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one symlink to broken, the ISO should be 25
    # extents (24 extents for the metadata, and 1 for the Rock Ridge ER record),
    # the path table should be 10 bytes long (for the root directory entry)
    # the little endian path table should start at extent 19 (default when
    # there is just the PVD), and the big endian path table should start at
    # extent 21 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one symlink, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one symlink, the root
    # directory record should have 3 entries ("dot", "dotdot", and the symlink),
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 23 (2 beyond the big endian path table
    # record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 25, [b'foo'])

def check_alternating_subdir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 61440)

    # Do checks on the PVD.  With two directories with a file and two files,
    # the ISO should be 30 extents (24 extents for the metadata, 1 each of the
    # directories, 1 for each of the files in the directories, and 1 for each
    # of the files), the path table should be 30 bytes long (10 bytes for the
    # root directory entry, and 10 bytes for each of the directories), the
    # little endian path table should start at extent 19 (default when there is
    # just the PVD), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 30, 30, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With two directories, there should
    # be three entries (the root entry, and the two directories).
    assert(len(iso.pvd.path_table_records) == 3)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of AA, it should
    # have a len of 2, it should start at extent 24, and its parent directory
    # number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'AA', 2, -1, 1)
    # The third entry in the PTR should have an identifier of CC, it should
    # have a len of 2, it should start at extent 25, and its parent directory
    # number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[2], b'CC', 2, -1, 1)

    # Now check the root directory record.  With two directories with a file and
    # two files, the root directory record should have 6 entries ("dot",
    # "dotdot", the two directories, and the two files), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 6, 2048, 23, False, 0)

    # Now check the directory record.  The number of children should be 3,
    # the name should be AA, the directory record length should be 36 (for
    # the Rock Ridge), it should start at extent 24, and it should not have Rock
    # Ridge.
    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(aa_dir_record, 3, b"AA", 36, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(aa_dir_record.children[1], False, 3, False)

    # Now check the BB file.  It should have a name of BB.;1, it should have a
    # directory record length of 38, it should start at extent 26, and its
    # contents should be "bb\n".
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(bb_dir_record, b"BB.;1", 38, 26, 3)
    internal_check_file_contents(iso, "/BB.;1", b"bb\n")

    # Now check the directory record.  The number of children should be 3,
    # the name should be CC, the directory record length should be 36 (for
    # the Rock Ridge), it should start at extent 25, and it should not have Rock
    # Ridge.
    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_dir_record(cc_dir_record, 3, b"CC", 36, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(cc_dir_record.children[1], False, 3, False)

    # Now check the DD file.  It should have a name of DD.;1, it should have a
    # directory record length of 38, it should start at extent 27, and its
    # contents should be "dd\n".
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_file(dd_dir_record, b"DD.;1", 38, 27, 3)
    internal_check_file_contents(iso, "/DD.;1", b"dd\n")

    # Now check the SUB1 file.  It should have a name of SUB1.;1, it should
    # have a directory record length of 40, it should start at extent 28, and
    # its contents should be "sub1\n".
    sub1_dir_record = aa_dir_record.children[2]
    internal_check_file(sub1_dir_record, b"SUB1.;1", 40, None, 5)
    internal_check_file_contents(iso, "/AA/SUB1.;1", b"sub1\n")

    # Now check the SUB2 file.  It should have a name of SUB2.;1, it should
    # have a directory record length of 40, it should start at extent 29, and
    # its contents should be "sub1\n".
    sub2_dir_record = cc_dir_record.children[2]
    internal_check_file(sub2_dir_record, b"SUB2.;1", 40, None, 5)
    internal_check_file_contents(iso, "/CC/SUB2.;1", b"sub2\n")

def check_rr_verylongname(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With one file, the ISO should be 27 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER entry, 1 for the
    # Rock Ridge continuation entry, and 1 for the file contents), the path
    # table should be 10 bytes long (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there is
    # just the PVD), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one file, the root directory
    # record should have 3 entries ("dot", "dotdot", and the file), the data
    # length is exactly one extent (2048 bytes), and the root directory should
    # start at extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 26, b'a')

def check_rr_verylongname_joliet(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With one file, the ISO should be 27 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER entry, 1 for the
    # Rock Ridge continuation entry, and 1 for the file contents), the path
    # table should be 10 bytes long (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there is
    # just the PVD), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With one file, the root directory
    # record should have 3 entries ("dot", "dotdot", and the file), the data
    # length is exactly one extent (2048 bytes), and the root directory should
    # start at extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, True, 2)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 32, b'a')

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 30, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], ("a"*64).encode('utf-16_be'), 162, 32, 3)
    internal_check_file_contents(iso, "/"+'a'*64, b"aa\n")

def check_rr_manylongname(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With seven files, the ISO should be 33 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER entry, 1 for the
    # Rock Ridge continuation entry, and 7 for the file contents), the path
    # table should be 10 bytes long (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there is
    # just the PVD), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With seven files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With seven files, the root directory
    # record should have 9 entries ("dot", "dotdot", and the seven files), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 23 (2 beyond the big endian path table record
    # entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 9, 2048, 23, True, 2)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_longname(iso, aa_dir_record, 26, b'a')

    # Now check out the file with a long name.  It should start at extent 27,
    # and the name should have all 'b' in it.
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_longname(iso, bb_dir_record, 27, b'b')

    # Now check out the file with a long name.  It should start at extent 28,
    # and the name should have all 'c' in it.
    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_rr_longname(iso, cc_dir_record, 28, b'c')

    # Now check out the file with a long name.  It should start at extent 29,
    # and the name should have all 'd' in it.
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_rr_longname(iso, dd_dir_record, 29, b'd')

    # Now check out the file with a long name.  It should start at extent 30,
    # and the name should have all 'e' in it.
    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_longname(iso, ee_dir_record, 30, b'e')

    # Now check out the file with a long name.  It should start at extent 31,
    # and the name should have all 'f' in it.
    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_rr_longname(iso, ff_dir_record, 31, b'f')

    # Now check out the file with a long name.  It should start at extent 32,
    # and the name should have all 'g' in it.
    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_rr_longname(iso, gg_dir_record, 32, b'g')

def check_rr_manylongname2(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 71680)

    # Do checks on the PVD.  With eight files, the ISO should be 35 extents (24
    # extents for the metadata, 1 for the Rock Ridge ER entry, 1 for the first
    # Rock Ridge continuation entry, 1 for the second Rock Ridge continuation
    # entry, and 8 for the file contents), the path table should be 10 bytes
    # long (for the root directory entry), the little endian path table should
    # start at extent 19 (default when there is just the PVD), and the big
    # endian path table should start at extent 21 (since the little endian path
    # table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 35, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With eight files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With eight files, the root directory
    # record should have 10 entries ("dot", "dotdot", and the eight files), the
    # data length is two extents (4096 bytes), and the root directory should
    # start at extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 10, 4096, 23, True, 2)

    # Now check out the file with a long name.  It should start at extent 27,
    # and the name should have all 'a' in it.
    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_rr_longname(iso, aa_dir_record, 27, b'a')

    # Now check out the file with a long name.  It should start at extent 28,
    # and the name should have all 'b' in it.
    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_longname(iso, bb_dir_record, 28, b'b')

    # Now check out the file with a long name.  It should start at extent 29,
    # and the name should have all 'c' in it.
    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_rr_longname(iso, cc_dir_record, 29, b'c')

    # Now check out the file with a long name.  It should start at extent 30,
    # and the name should have all 'd' in it.
    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_rr_longname(iso, dd_dir_record, 30, b'd')

    # Now check out the file with a long name.  It should start at extent 31,
    # and the name should have all 'e' in it.
    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_longname(iso, ee_dir_record, 31, b'e')

    # Now check out the file with a long name.  It should start at extent 32,
    # and the name should have all 'f' in it.
    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_rr_longname(iso, ff_dir_record, 32, b'f')

    # Now check out the file with a long name.  It should start at extent 33,
    # and the name should have all 'g' in it.
    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_rr_longname(iso, gg_dir_record, 33, b'g')

    # Now check out the file with a long name.  It should start at extent 34,
    # and the name should have all 'h' in it.
    hh_dir_record = iso.pvd.root_dir_record.children[9]
    internal_check_rr_longname(iso, hh_dir_record, 34, b'h')

def check_rr_verylongnameandsymlink(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With one file with a long name and one symlink,
    # the ISO should be 27 extents (24 extents for the metadata, 1 for the
    # Rock Ridge ER entry, 1 for the Rock Ridge continuation entry, and 1 for
    # the file contents), the path table should be 10 bytes long (for the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table
    # should start at extent 21 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With one file and one symlink,
    # there should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With one file and one symlink, the
    # root directory record should have 4 entries ("dot", "dotdot", the file,
    # and the symlink), the data length is two extents (4096 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    # Now check out the file with a long name.  It should start at extent 26,
    # and the name should have all 'a' in it.
    internal_check_rr_longname(iso, iso.pvd.root_dir_record.children[2], 26, b'a')

def check_joliet_and_rr_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 63488)

    # Do checks on the PVD.  With no files and Joliet and Rock Ridge, the ISO
    # should be 31 extents (24 extents for the metadata, 1 for the Rock Ridge
    # ER entry, 1 for the Joliet VD, 1 for the Joliet root directory record,
    # and 4 for the Joliet path table), the path table should be 10 bytes long
    # (for the root directory entry), the little endian path table should start
    # at extent 20, and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 31, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table
    # should be 10 bytes (for the root directory entry), the little endian path
    # table should start at extent 24, and the big endian path table should
    # start at extent 26 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 28 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 28, True, 2)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot" and "dotdot")
    # the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 29 (one past the non-Joliet directory
    # record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_joliet_and_rr_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With one file and Joliet and Rock Ridge, the ISO
    # should be 32 extents (24 extents for the metadata, 1 for the Rock Ridge
    # ER entry, 1 for the Joliet VD, 1 for the Joliet root directory record,
    # 4 for the Joliet path table, and 1 for the file contents), the path table
    # should be 10 bytes long (for the root directory entry), the little endian
    # path table should start at extent 20, and the big endian path table
    # should start at extent 22 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 32, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one file,
    # the number of extents should be the same as the PVD, the path table
    # should be 10 bytes (for the root directory entry), the little endian path
    # table should start at extent 24, and the big endian path table should
    # start at extent 26 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With one file, the root directory
    # record should have 3 entries ("dot", "dotdot", and the file), the data
    # length is exactly one extent (2048 bytes), and the root directory should
    # start at extent 28 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, True, 2)

    # Now check the Joliet root directory record.  With one file, the Joliet
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # file) the data length is exactly one extent (2048 bytes), and the root
    # directory should start at extent 29 (one past the non-Joliet directory
    # record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the FOO file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 31, and
    # its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 116, 31, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 31, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 31, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_joliet_and_rr_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With one directory and Joliet and Rock Ridge, the
    # ISO should be 33 extents (24 extents for the metadata, 1 for the Rock Ridge
    # ER entry, 1 for the Joliet VD, 1 for the Joliet root directory record,
    # 4 for the Joliet path table, 1 for the directory contents, and 1 for the
    # Joliet directory contents), the path table should be 22 bytes long (10
    # bytes for the root directory entry, and 12 bytes for the directory), the
    # little endian path table should start at extent 20, and the big endian
    # path table should start at extent 22 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 22, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # directory, the number of extents should be the same as the PVD, the path
    # table should be 26 bytes (10 bytes for the root directory entry and 16
    # bytes for the directory), the little endian path table should start at
    # extent 24, and the big endian path table should start at extent 26 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_joliet(iso.svds[0], 33, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one directory, there should
    # be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 31, 1)

    # Now check the root directory record.  With one directory, the root
    # directory record should have 3 entries ("dot", "dotdot", and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 28 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, True, 3)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 3 entries ("dot", "dotdot", and
    # the directory) the data length is exactly one extent (2048 bytes), and
    # the root directory should start at extent 30 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[2], 2, b"DIR1", 114, 29, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], True, 3, False)

    # Now check the Joliet directory record.  The number of children should be
    # 2, the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(iso.joliet_vd.root_dir_record.children[2], 2, "dir1".encode('utf-16_be'), 42, 31, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.joliet_vd.root_dir_record.children[2].children[1], False, 3, False)

def check_rr_and_eltorito_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files and El Torito and Rock Ridge, the
    # ISO should be 28 extents (24 extents for the metadata, 1 for the Rock Ridge
    # ER entry, 1 for the El Torito boot record, 1 for the El Torito boot
    # catalog, and 1 for the El Torito boot file), the path table should be 10
    # bytes long (for the root directory entry), the little endian path table
    # should start at extent 20, and the big endian path table should start at
    # extent 22 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 26, and the initial entry should start at
    # extent 27.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one directory, there should
    # be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files but El Torito, the
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 24 (2 beyond the
    # big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, True, 2)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 27, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_rr_and_eltorito_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 59392)

    # Do checks on the PVD.  With one file and El Torito and Rock Ridge, the
    # ISO should be 29 extents (24 extents for the metadata, 1 for the Rock Ridge
    # ER entry, 1 for the El Torito boot record, 1 for the El Torito boot
    # catalog, 1 for the El Torito boot file, and 1 for the additional file),
    # the path table should be 10 bytes long (for the root directory entry),
    # little endian path table should start at extent 20, and the big endian
    # path table should start at extent 22 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 29, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 26, and the initial entry should start at
    # extent 27.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With one file and El Torito, the
    # root directory record should have 5 entries ("dot", "dotdot", the boot
    # catalog, the boot file, and the additional file), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 24 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, True, 2)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 27, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 28, and its contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 116, 28, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

def check_rr_and_eltorito_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 59392)

    # Do checks on the PVD.  With one directory and El Torito and Rock Ridge,
    # the ISO should be 29 extents (24 extents for the metadata, 1 for the
    # Rock Ridge ER entry, 1 for the El Torito boot record, 1 for the El Torito
    # boot catalog, 1 for the El Torito boot file, and 1 for the additional
    # directory), the path table should be 22 bytes long (10 bytes for the root
    # directory entry, and 12 bytes for the directory), the little endian path
    # table should start at extent 20, and the big endian path table should
    # start at extent 22 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 29, 22, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 27, and the initial entry should start at
    # extent 28.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 27, 28)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one directory, there should
    # be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 25, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 25, 1)

    # Now check the root directory record.  With one directory and El Torito,
    # the root directory record should have 5 entries ("dot", "dotdot", the boot
    # catalog, the boot file, and the additional directory), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 24 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, True, 3)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114 (for
    # the Rock Ridge), it should start at extent 29, and it should have Rock
    # Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[4], 2, b"DIR1", 114, 25, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[4].children[1], True, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 27.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 27, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 116 (for Rock Ridge), it should start
    # at extent 27, and its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 28, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_joliet_and_eltorito_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files and El Torito and Joliet,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Joliet VD, 1 for the Joliet root dir record, and 4
    # for the Joliet path table), the path table should be 10 bytes long (for
    # the root directory entry), the little endian path table should start at
    # extent 21, and the big endian path table should start at extent 23 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 29 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 31.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 31.
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 31, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_isohybrid(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 1048576)

    # Do checks on the PVD.  With one file and El Torito, the ISO should be
    # 45 extents (24 extents for the metadata, 1 for the El Torito boot record,
    # 1 for the El Torito boot catalog, and 19 for the boot file), the path
    # table should be 10 bytes long (for the root directory entry), the little
    # endian path table should start at extent 20, and the big endian path
    # table should start at extent 22 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files and El Torito, there
    # should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048)

    # Now check out the isohybrid stuff.
    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)

    # Now check the boot file.  It should have a name of ISOLINUX.BIN;1, it
    # should have a directory record length of 48, and it should start at
    # extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"ISOLINUX.BIN;1", 48, 26, 68)

def check_isohybrid_mac_uefi(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 1048576)

    # Do checks on the PVD.  With one file and El Torito, the ISO should be
    # 45 extents (24 extents for the metadata, 1 for the El Torito boot record,
    # 1 for the El Torito boot catalog, and 19 for the boot file), the path
    # table should be 10 bytes long (for the root directory entry), the little
    # endian path table should start at extent 20, and the big endian path
    # table should start at extent 22 (since the little endian path table
    # record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 29, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, None)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files and El Torito, there
    # should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 6, 2048, 24, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048)

    # Now check out the isohybrid stuff.
    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)

    # Now check the boot file.  It should have a name of ISOLINUX.BIN;1, it
    # should have a directory record length of 48, and it should start at
    # extent 26.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"EFIBOOT.IMG;1", 46, None, 1)

def check_joliet_and_eltorito_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 69632)

    # Do checks on the PVD.  With one file and Joliet and El Torito, the ISO
    # should be 34 extents (24 extents for the metadata, 1 for the El Torito
    # boot record, 1 for the El Torito boot catalog, 1 for the El Torito boot
    # file, 1 for the extra file, 1 for the Joliet VD, 1 for the Joliet root
    # dir record, and 4 for the Joliet path table), the path table should be
    # 10 bytes long (for the root directory entry), the little endian path
    # table should start at extent 21, and the big endian path table should
    # start at extent 23 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 34, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With one file and Joliet and El
    # Torito, there should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With one file and El Torito, the
    # root directory record should have 5 entries ("dot", "dotdot", the boot
    # catalog, the boot file, and the extra file), the data length is exactly
    # one extent (2048 bytes), and the root directory should start at extent
    # 29 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With one file and El Torito,
    # the Joliet root directory record should have 5 entries ("dot", "dotdot",
    # the boot catalog, the boot file, and the extra file), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 35.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 40, it should start at extent 32, and it
    # should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should have
    # a directory record length of 40, it should start at extent 33, and it
    # should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 40, 33, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[4], "foo".encode('utf-16_be'), 40, 33, 4)
    internal_check_file_contents(iso, '/foo', b"foo\n")

def check_joliet_and_eltorito_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 71680)

    # Do checks on the PVD.  With one directory and Joliet and El Torito, the
    # ISO should be 35 extents (24 extents for the metadata, 1 for the El Torito
    # boot record, 1 for the El Torito boot catalog, 1 for the El Torito boot
    # file, 1 for the extra directory, 1 for the Joliet VD, 1 for the Joliet
    # root dir record, 4 for the Joliet path table, and 1 for the Joliet extra
    # directory), the path table should be 22 bytes long (10 bytes for the root
    # directory entry and 12 bytes for the extra directory), the little endian
    # path table should start at extent 21, and the big endian path table should
    # start at extent 23 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 35, 22, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With one directory and Joliet and
    # El Torito, there should be two entries (the root entry and the extra
    # directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 30, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 30, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 31, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 32, 1)

    # Now check the root directory record.  With one directory and El Torito,
    # the root directory record should have 5 entries ("dot", "dotdot", the boot
    # catalog, the boot file, and the extra directory), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 29 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With one directory and El
    # Torito, the Joliet root directory record should have 5 entries ("dot",
    # "dotdot", the boot catalog, the boot file, and the extra directory), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 31 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 31)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 38, it
    # should start at extent 30, and it should not have Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[4], 2, b"DIR1", 38, 30, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[4].children[1], False, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 33.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 33, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 40, it should start at extent 34, and it
    # should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 34, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_dir_record(iso.joliet_vd.root_dir_record.children[4], 2, "dir1".encode('utf-16_be'), 42, 32, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.joliet_vd.root_dir_record.children[4].children[1], False, 3, False)

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 33, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 34, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_joliet_rr_and_eltorito_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 69632)

    # Do checks on the PVD.  With no files, Joliet, Rock Ridge, and El Torito,
    # the ISO should be 34 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Rock Ridge ER record, 1 for the Joliet VD, 1 for the
    # Joliet root dir record, and 4 for the Joliet path table), the path table
    # should be 10 bytes long (for the root directory entry), the little endian
    # path table should start at extent 21, and the big endian path table should
    # start at extent 23 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 34, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files and Joliet, Rock
    # Ridge, and El Torito, there should be one entry (the root entry).
    # directory).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With Joliet, Rock Ridge, and
    # El Torito the root directory record should have 4 entries ("dot",
    # "dotdot", the boot catalog, and the boot file), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 29 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, True, 2)

    # Now check the Joliet root directory record.  With no files and Joliet,
    # Rock Ridge, and El Torito, the Joliet root directory record should have 4
    # entries ("dot", "dotdot", the boot catalog, and the boot file), the data
    # length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 32.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 32, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 33, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 33, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 32, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 33, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_joliet_rr_and_eltorito_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 71680)

    # Do checks on the PVD.  With one file, Joliet, Rock Ridge, and El Torito,
    # the ISO should be 35 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Rock Ridge ER record, 1 for the Joliet VD, 1 for the
    # Joliet root dir record, 4 for the Joliet path table, and 1 for the file),
    # the path table should be 10 bytes long (for the root directory entry),
    # the little endian path table should start at extent 21, and the big
    # endian path table should start at extent 23 (since the little endian
    # path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 35, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With one file and Joliet, Rock
    # Ridge, and El Torito, there should be one entry (the root entry).
    # directory).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With Joliet, Rock Ridge, and
    # El Torito the root directory record should have 5 entries ("dot",
    # "dotdot", the boot catalog, the boot file, and the file), the data length
    # is exactly one extent (2048 bytes), and the root directory should start at
    # extent 29 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, True, 2)

    # Now check the Joliet root directory record.  With one file and Joliet,
    # Rock Ridge, and El Torito, the Joliet root directory record should have 5
    # entries ("dot", "dotdot", the boot catalog, the boot file, and the file),
    # the data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 30 (one past the non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 30)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 32.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 32, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 33, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 33, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the foo file.  It should have a name of FOO.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 34, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"FOO.;1", 116, 34, 4)
    internal_check_file_contents(iso, '/FOO.;1', b"foo\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 32, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 33, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[4], "foo".encode('utf-16_be'), 40, 34, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_joliet_rr_and_eltorito_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 73728)

    # Do checks on the PVD.  With one directory, Joliet, Rock Ridge, and El
    # Torito, the ISO should be 36 extents (24 extents for the metadata, 1 for
    # the El Torito boot record, 1 for the El Torito boot catalog, 1 for the
    # El Torito boot file, 1 for the Rock Ridge ER record, 1 for the Joliet VD,
    # 1 for the Joliet root dir record, 4 for the Joliet path table, 1 for the
    # the directory, and 1 for the Joliet directory), the path table should
    # be 22 bytes long (10 bytes for the root directory entry, and 12 bytes for
    # the directory), the little endian path table should start at extent 21,
    # and the big endian path table should start at extent 23 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 36, 22, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With one directory and Joliet, Rock
    # Ridge, and El Torito, there should be two entries (the root entry and the
    # directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)
    # The first entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 30, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 30, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 31, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 32, 1)

    # Now check the root directory record.  With one directory, Joliet,
    # Rock Ridge, and El Torito, the root directory record should have 5
    # entries ("dot", "dotdot", the boot catalog, the boot file, and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 29 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, True, 3)

    # Now check the Joliet root directory record.  With one directory and
    # Joliet, Rock Ridge, and El Torito, the Joliet root directory record
    # should have 5 entries ("dot", "dotdot", the boot catalog, the boot file,
    # and the directory), the data length is exactly one extent (2048 bytes),
    # and the root directory should start at extent 31 (one past the non-Joliet
    # directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 5, 2048, 31)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 114, it
    # should start at extent 30, and it should not have Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[4], 2, b"DIR1", 114, 30, True, b"dir1", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[4].children[1], True, 3, False)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 124, 34, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 116, 35, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_dir_record(iso.joliet_vd.root_dir_record.children[4], 2, "dir1".encode('utf-16_be'), 42, 32, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.joliet_vd.root_dir_record.children[4].children[1], False, 3, False)

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, 34, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 35, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_rr_deep_dir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 69632)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 34, 122, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 10)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], b'RR_MOVED', 8, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[3], b'DIR2', 4, -1, 2)
    internal_check_ptr(iso.pvd.path_table_records[4], b'DIR8', 4, -1, 3)
    internal_check_ptr(iso.pvd.path_table_records[5], b'DIR3', 4, -1, 4)
    internal_check_ptr(iso.pvd.path_table_records[6], b'DIR4', 4, -1, 6)
    internal_check_ptr(iso.pvd.path_table_records[7], b'DIR5', 4, -1, 7)
    internal_check_ptr(iso.pvd.path_table_records[8], b'DIR6', 4, -1, 8)
    internal_check_ptr(iso.pvd.path_table_records[9], b'DIR7', 4, -1, 9)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 4)

def check_rr_deep(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 71680)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 35, 122, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 10)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 4)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/foo", b"foo\n")

def check_rr_deep2(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 73728)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 36, 134, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 11)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 4)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/foo", b"foo\n")

def check_xa_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 49152)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 24, 10, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, False, 0, True)

def check_xa_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0, True)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 54, 24, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

def check_xa_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 22, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0, True)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[2], 2, b"DIR1", 52, 24, False, None, 0, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], False, 3, True)

def check_sevendeepdirs(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With seven directories, the ISO should be 31
    # extents (24 extents for the metadata, plus 1 extent for each of the seven
    # directories, plus 1 extent for the Rock Ridge ER entry).  The path table
    # should be 94 bytes (10 bytes for the root directory entry, plus 12*7=84
    # for the 7 directories), the little endian path table should start at
    # extent 19 (default when there are no volume descriptors beyond the
    # primary and the terminator), and the big endian path table should start
    # at extent 21 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 32, 94, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With one directory at the root,
    # the root directory record should have 3 entries ("dot", "dotdot", and the
    # one directory), the data length is exactly one extent (2048 bytes),
    # and the root directory should start at extent 23 (2 beyond the big
    # endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 3)

    # Now check out the path table records.  With ten directories, there should
    # be a total of 11 entries (the root entry and the ten directories).
    assert(len(iso.pvd.path_table_records) == 7+1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)
    # The third entry in the PTR should have an identifier of DIR2, it
    # should have a len of 4, it should start at extent 25, and its parent
    # directory number should be 2.
    internal_check_ptr(iso.pvd.path_table_records[2], b'DIR2', 4, 25, 2)
    # The fourth entry in the PTR should have an identifier of DIR3, it
    # should have a len of 4, it should start at extent 26, and its parent
    # directory number should be 3.
    internal_check_ptr(iso.pvd.path_table_records[3], b'DIR3', 4, 26, 3)
    # The fifth entry in the PTR should have an identifier of DIR4, it
    # should have a len of 4, it should start at extent 27, and its parent
    # directory number should be 4.
    internal_check_ptr(iso.pvd.path_table_records[4], b'DIR4', 4, 27, 4)
    # The sixth entry in the PTR should have an identifier of DIR5, it
    # should have a len of 4, it should start at extent 28, and its parent
    # directory number should be 5.
    internal_check_ptr(iso.pvd.path_table_records[5], b'DIR5', 4, 28, 5)
    # The seventh entry in the PTR should have an identifier of DIR6, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 6.
    internal_check_ptr(iso.pvd.path_table_records[6], b'DIR6', 4, 29, 6)
    # The eighth entry in the PTR should have an identifier of DIR7, it
    # should have a len of 4, it should start at extent 30, and its parent
    # directory number should be 7.
    internal_check_ptr(iso.pvd.path_table_records[7], b'DIR7', 4, 30, 7)

    # Now check the first directory record.  The number of children should be 3,
    # the name should be DIR1, the directory record length should be 38, it
    # should start at extent 24, and it should not have Rock Ridge.
    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, 24, True, b"dir1", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 3, False)

    # Now check the second directory record.  The number of children should be
    # 3, the name should be DIR2, the directory record length should be 38, it
    # should start at extent 25, and it should not have Rock Ridge.
    dir2_record = dir1_record.children[2]
    internal_check_dir_record(dir2_record, 3, b"DIR2", 114, 25, True, b"dir2", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_record.children[1], True, 3, False)

    # Now check the third directory record.  The number of children should be
    # 3, the name should be DIR3, the directory record length should be 38, it
    # should start at extent 26, and it should not have Rock Ridge.
    dir3_record = dir2_record.children[2]
    internal_check_dir_record(dir3_record, 3, b"DIR3", 114, 26, True, b"dir3", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir3_record.children[1], True, 3, False)

    # Now check the fourth directory record.  The number of children should be
    # 3, the name should be DIR4, the directory record length should be 38, it
    # should start at extent 27, and it should not have Rock Ridge.
    dir4_record = dir3_record.children[2]
    internal_check_dir_record(dir4_record, 3, b"DIR4", 114, 27, True, b"dir4", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir4_record.children[1], True, 3, False)

    # Now check the fifth directory record.  The number of children should be
    # 3, the name should be DIR5, the directory record length should be 38, it
    # should start at extent 28, and it should not have Rock Ridge.
    dir5_record = dir4_record.children[2]
    internal_check_dir_record(dir5_record, 3, b"DIR5", 114, 28, True, b"dir5", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir5_record.children[1], True, 3, False)

    # Now check the sixth directory record.  The number of children should be
    # 3, the name should be DIR6, the directory record length should be 38, it
    # should start at extent 29, and it should not have Rock Ridge.
    dir6_record = dir5_record.children[2]
    internal_check_dir_record(dir6_record, 3, b"DIR6", 114, 29, True, b"dir6", 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir6_record.children[1], True, 3, False)

    # Now check the seventh directory record.  The number of children should be
    # 2, the name should be DIR7, the directory record length should be 38, it
    # should start at extent 30, and it should not have Rock Ridge.
    dir7_record = dir6_record.children[2]
    internal_check_dir_record(dir7_record, 2, b"DIR7", 114, 30, True, b"dir7", 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir7_record.children[1], True, 3, False)

def check_xa_joliet_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 61440)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 30, 10, 20, 22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 30, 10, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 28, False, 0, True)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 2, 2048, 29)

def check_xa_joliet_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 63488)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 31, 10, 20, 22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 31, 10, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0, True)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 29)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 54, 30, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 30, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_xa_joliet_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 32, 22, 20, 22)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 26, 24, 26)

    assert(iso.joliet_vd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 31, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0, True)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[2], 2, b"DIR1", 52, 29, False, None, 0, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], False, 3, True)

    internal_check_dir_record(iso.joliet_vd.root_dir_record.children[2], 2, "dir1".encode('utf-16_be'), 42, 31, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.joliet_vd.root_dir_record.children[2].children[1], False, 3, False)

def check_isolevel4_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 20, 22)

    internal_check_enhanced_vd(iso.enhanced_vd, 25, 10, 20, 22)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 24, False, 0)

def check_isolevel4_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 20, 22)

    internal_check_enhanced_vd(iso.enhanced_vd, 26, 10, 20, 22)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 24, False, 0)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"foo", 36, 25, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_isolevel4_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 26, 22, 20, 22)

    internal_check_enhanced_vd(iso.enhanced_vd, 26, 22, 20, 22)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'dir1', 4, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 24, False, 0)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[2], 2, b"dir1", 38, 25, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], False, 3, False)

def check_isolevel4_eltorito(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 21, 23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 34, and the initial entry should start at
    # extent 35.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    internal_check_enhanced_vd(iso.enhanced_vd, 28, 10, 21, 23)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_everything(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 108544)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 53, 106, 22, 24)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 20)

    # Now check out the path table records.  With one symlink, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 9)

    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 30, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'dir1', 4, 31, 1)
    # The third entry in the PTR should have an identifier of DIR2, it
    # should have a len of 4, it should start at extent 25, and its parent
    # directory number should be 2.
    internal_check_ptr(iso.pvd.path_table_records[2], b'dir2', 4, 32, 2)
    # The fourth entry in the PTR should have an identifier of DIR3, it
    # should have a len of 4, it should start at extent 26, and its parent
    # directory number should be 3.
    internal_check_ptr(iso.pvd.path_table_records[3], b'dir3', 4, 33, 3)
    # The fifth entry in the PTR should have an identifier of DIR4, it
    # should have a len of 4, it should start at extent 27, and its parent
    # directory number should be 4.
    internal_check_ptr(iso.pvd.path_table_records[4], b'dir4', 4, 34, 4)
    # The sixth entry in the PTR should have an identifier of DIR5, it
    # should have a len of 4, it should start at extent 28, and its parent
    # directory number should be 5.
    internal_check_ptr(iso.pvd.path_table_records[5], b'dir5', 4, 35, 5)
    # The seventh entry in the PTR should have an identifier of DIR6, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 6.
    internal_check_ptr(iso.pvd.path_table_records[6], b'dir6', 4, 36, 6)
    # The eighth entry in the PTR should have an identifier of DIR7, it
    # should have a len of 4, it should start at extent 30, and its parent
    # directory number should be 7.
    internal_check_ptr(iso.pvd.path_table_records[7], b'dir7', 4, 37, 7)
    # The eighth entry in the PTR should have an identifier of DIR7, it
    # should have a len of 4, it should start at extent 30, and its parent
    # directory number should be 7.
    internal_check_ptr(iso.pvd.path_table_records[8], b'dir8', 4, 38, 8)

    assert(len(iso.joliet_vd.path_table_records) == 9)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 39, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 40, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[2], 'dir2'.encode('utf-16_be'), 8, 41, 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[3], 'dir3'.encode('utf-16_be'), 8, 42, 3)
    internal_check_ptr(iso.joliet_vd.path_table_records[4], 'dir4'.encode('utf-16_be'), 8, 43, 4)
    internal_check_ptr(iso.joliet_vd.path_table_records[5], 'dir5'.encode('utf-16_be'), 8, 44, 5)
    internal_check_ptr(iso.joliet_vd.path_table_records[6], 'dir6'.encode('utf-16_be'), 8, 45, 6)
    internal_check_ptr(iso.joliet_vd.path_table_records[7], 'dir7'.encode('utf-16_be'), 8, 46, 7)
    internal_check_ptr(iso.joliet_vd.path_table_records[8], 'dir8'.encode('utf-16_be'), 8, 47, 8)

    # Now check the root directory record.  With one file and one symlink,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the symlink), the data length is exactly one extent
    # (2048 bytes), and the root directory should start at extent 23 (2 beyond
    # the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 7, 2048, 30, True, 3, True)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 7, 2048, 39)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 128, 50, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.pvd_extent == 16)
    assert(boot_rec.boot_info_table.rec_extent == 50)
    assert(boot_rec.boot_info_table.orig_len == 5)
    assert(boot_rec.boot_info_table.csum == 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 124 (for Rock Ridge), and it
    # should start at extent 34.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 136, 49, 2048)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    dir1 = iso.pvd.root_dir_record.children[4]
    internal_check_dir_record(dir1, 4, b"dir1", 128, 31, True, b"dir1", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1.children[1], True, 3, True)

    internal_check_file(dir1.children[3], b"foo", 126, 51, 4)
    internal_check_file_contents(iso, "/dir1/foo", b"foo\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[5], b"foo", 126, 51, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 132, and the symlink components should be 'dir1' and 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_rr_symlink(sym_dir_record, b'sym', 136, 52, [b'foo'])

    dir2 = dir1.children[2]
    internal_check_dir_record(dir2, 3, b"dir2", 128, 32, True, b"dir2", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2.children[1], True, 3, True)

    dir3 = dir2.children[2]
    internal_check_dir_record(dir3, 3, b"dir3", 128, 33, True, b"dir3", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir3.children[1], True, 3, True)

    dir4 = dir3.children[2]
    internal_check_dir_record(dir4, 3, b"dir4", 128, 34, True, b"dir4", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir4.children[1], True, 3, True)

    dir5 = dir4.children[2]
    internal_check_dir_record(dir5, 3, b"dir5", 128, 35, True, b"dir5", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir5.children[1], True, 3, True)

    dir6 = dir5.children[2]
    internal_check_dir_record(dir6, 3, b"dir6", 128, 36, True, b"dir6", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir6.children[1], True, 3, True)

    dir7 = dir6.children[2]
    internal_check_dir_record(dir7, 3, b"dir7", 128, 37, True, b"dir7", 3, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir7.children[1], True, 3, True)

    dir8 = dir7.children[2]
    internal_check_dir_record(dir8, 3, b"dir8", 128, 38, True, b"dir8", 2, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir8.children[1], True, 3, True)

    # Now check the boot file.  It should have a name of BOOT.;1, it should have
    # a directory record length of 116 (for Rock Ridge), it should start at
    # extent 35, and it should contain "boot\n".
    internal_check_file(dir8.children[2], b"bar", 126, 52, 4)
    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar", b"bar\n")

def check_rr_xa_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, True, 2, True)

def check_rr_xa_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 26, 10, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2, True)

    # Now check the boot file.  It should have a name of FOO.;1, it should have
    # a directory record length of 54 (for the XA record), it should start at
    # extent 24, and it should contain "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"FOO.;1", 130, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_rr_xa_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 26, 22, 19, 21)

    assert(iso.pvd.application_use[141:149] == b"CD-XA001")

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 3, True)

    # Now check the directory record.  The number of children should be 2,
    # the name should be DIR1, the directory record length should be 52 (38+14
    # for the XA record), it should start at extent 24, and it should not have
    # Rock Ridge.
    internal_check_dir_record(iso.pvd.root_dir_record.children[2], 2, b"DIR1", 128, 24, True, b'dir1', 2, True)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1], True, 3, True)

def check_rr_joliet_symlink(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With one file and one symlink, the ISO should be
    # 26 extents (24 extents for the metadata, 1 for the Rock Ridge ER record,
    # and 1 for the file), the path table should be 10 bytes long (for the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table should
    # start at extent 21 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 32, 10, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 32, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file and one symlink,
    # there should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 29, 1)

    # Now check the root directory record.  With one file and one symlink,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the symlink), the data length is exactly one extent
    # (2048 bytes), and the root directory should start at extent 23 (2 beyond
    # the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 28, True, 2)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 29)

    # Now check the foo file.  It should have a name of FOO.;1, it should
    # have a directory record length of 116, it should start at extent 25, and
    # its contents should be "foo\n".
    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, b"FOO.;1", 116, 31, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check out the rock ridge record for the file.  It should have the name
    # foo, and contain "foo\n".
    internal_check_rr_file(foo_dir_record, b'foo')
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the rock ridge symlink.  It should have a directory record
    # length of 126, and the symlink components should be 'foo'.
    sym_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_rr_symlink(sym_dir_record, b"SYM.;1", 126, 32, [b'foo'])

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "foo".encode('utf-16_be'), 40, 31, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_rr_joliet_deep(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 98304)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 48, 122, 20, 22)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 10)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], b'RR_MOVED', 8, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[3], b'DIR2', 4, -1, 2)
    internal_check_ptr(iso.pvd.path_table_records[4], b'DIR8', 4, -1, 3)
    internal_check_ptr(iso.pvd.path_table_records[5], b'DIR3', 4, -1, 4)
    internal_check_ptr(iso.pvd.path_table_records[6], b'DIR4', 4, -1, 6)
    internal_check_ptr(iso.pvd.path_table_records[7], b'DIR5', 4, -1, 7)
    internal_check_ptr(iso.pvd.path_table_records[8], b'DIR6', 4, -1, 8)
    internal_check_ptr(iso.pvd.path_table_records[9], b'DIR7', 4, -1, 9)

    assert(len(iso.joliet_vd.path_table_records) == 9)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, -1, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, -1, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[2], 'dir2'.encode('utf-16_be'), 8, -1, 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[3], 'dir3'.encode('utf-16_be'), 8, -1, 3)
    internal_check_ptr(iso.joliet_vd.path_table_records[4], 'dir4'.encode('utf-16_be'), 8, -1, 4)
    internal_check_ptr(iso.joliet_vd.path_table_records[5], 'dir5'.encode('utf-16_be'), 8, -1, 5)
    internal_check_ptr(iso.joliet_vd.path_table_records[6], 'dir6'.encode('utf-16_be'), 8, -1, 6)
    internal_check_ptr(iso.joliet_vd.path_table_records[7], 'dir7'.encode('utf-16_be'), 8, -1, 7)
    internal_check_ptr(iso.joliet_vd.path_table_records[8], 'dir8'.encode('utf-16_be'), 8, -1, 8)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 28, True, 4)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 38)

def check_eltorito_multi_boot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 59392)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 29, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

def check_eltorito_multi_boot_hard_link(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 59392)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 29, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 6, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

    internal_check_file(iso.pvd.root_dir_record.children[5], b"bootlink", 42, 28, 6)
    internal_check_file_contents(iso, "/bootlink", b"boot2\n")

def check_eltorito_boot_info_table(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 21, 23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.pvd_extent == 16)
    assert(boot_rec.boot_info_table.rec_extent == 27)
    assert(boot_rec.boot_info_table.orig_len == 5)
    assert(boot_rec.boot_info_table.csum == 0)

def check_eltorito_boot_info_table_large(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 21, 23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 80)
    internal_check_file_contents(iso, "/boot", b"bootboot\x10\x00\x00\x00\x1b\x00\x00\x00P\x00\x00\x00\x88\xbd\xbd\xd1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00bootbootbootboot")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.pvd_extent == 16)
    assert(boot_rec.boot_info_table.rec_extent == 27)
    assert(boot_rec.boot_info_table.orig_len == 80)
    assert(boot_rec.boot_info_table.csum == 0xd1bdbd88)

def check_hard_link(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 26, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    dir1 = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1, 3, b"DIR1", 38, 24, False, b'', 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1.children[1], False, 3, False)

    internal_check_file(dir1.children[2], b"FOO.;1", 40, 25, 4)
    internal_check_file_contents(iso, "/DIR1/FOO.;1", b"foo\n")

def check_same_dirname_different_parent(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 79872)

    # Do checks on the PVD.  With one file and one symlink, the ISO should be
    # 26 extents (24 extents for the metadata, 1 for the Rock Ridge ER record,
    # and 1 for the file), the path table should be 10 bytes long (for the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there is just the PVD), and the big endian path table should
    # start at extent 21 (since the little endian path table record is always
    # rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 39, 58, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 39, 74, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one file and one symlink,
    # there should be one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 5)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], b'DIR2', 4, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[3], b'BOOT', 4, -1, 2)
    internal_check_ptr(iso.pvd.path_table_records[4], b'BOOT', 4, -1, 3)

    assert(len(iso.joliet_vd.path_table_records) == 5)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 33, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, -1, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[2], 'dir2'.encode('utf-16_be'), 8, -1, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[3], 'boot'.encode('utf-16_be'), 8, -1, 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[4], 'boot'.encode('utf-16_be'), 8, -1, 3)

    # Now check the root directory record.  With one file and one symlink,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the symlink), the data length is exactly one extent
    # (2048 bytes), and the root directory should start at extent 23 (2 beyond
    # the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 28, True, 4)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_record, 3, b"DIR1", 114, None, True, b'dir1', 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_record.children[1], True, 4, False)

    dir2_record = iso.pvd.root_dir_record.children[3]
    internal_check_dir_record(dir2_record, 3, b"DIR2", 114, None, True, b'dir2', 3, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_record.children[1], True, 4, False)

    boot1_record = dir1_record.children[2]
    internal_check_dir_record(boot1_record, 2, b"BOOT", 114, None, True, b'boot', 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot1_record.children[1], True, 3, False)

    boot2_record = dir2_record.children[2]
    internal_check_dir_record(boot2_record, 2, b"BOOT", 114, None, True, b'boot', 2, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot2_record.children[1], True, 3, False)

    # Now check the Joliet root directory record.  With no files, the Joliet
    # root directory record should have 2 entries ("dot", and "dotdot"), the
    # data length is exactly one extent (2048 bytes), and the root directory
    # should start at extent 29 (one past the non-Joliet root directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 33)

    dir1_joliet_record = iso.joliet_vd.root_dir_record.children[2]
    internal_check_dir_record(dir1_joliet_record, 3, "dir1".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1_joliet_record.children[1], False, 3, False)

    dir2_joliet_record = iso.joliet_vd.root_dir_record.children[3]
    internal_check_dir_record(dir2_joliet_record, 3, "dir2".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir2_joliet_record.children[1], False, 3, False)

    boot1_joliet_record = dir1_joliet_record.children[2]
    internal_check_dir_record(boot1_joliet_record, 2, "boot".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot1_joliet_record.children[1], False, 3, False)

    boot2_joliet_record = dir2_joliet_record.children[2]
    internal_check_dir_record(boot2_joliet_record, 2, "boot".encode('utf-16_be'), 42, None, False, None, 0, False)
    # The directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(boot2_joliet_record.children[1], False, 3, False)

def check_joliet_isolevel4(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 69632)

    # Do checks on the PVD.  With a Joliet ISO with one file and one directory,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the
    # directory, 1 for the Joliet, one for the Joliet root directory record, one
    # for the joliet directory, 4 for the Joliet path table records, and 1 for
    # the file contents). The path table should be 22 bytes (10 bytes for the
    # root directory entry and 12 bytes for the directory), the little endian
    # path table should start at extent 20, and the big endian path table
    # should start at extent 22 (since the little endian path table record is
    # always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 34, 22, 21, 23)

    internal_check_enhanced_vd(iso.enhanced_vd, 34, 22, 21, 23)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with one
    # file and one directory, the number of extents should be the same as the
    # PVD, the path table should be 26 bytes (10 bytes for the root directory
    # entry and 16 bytes for the directory), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.joliet_vd, 34, 26, 25, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With one file and one directory,
    # there should be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 28, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)
    # The second entry in the PTR should have an identifier of DIR1, it
    # should have a len of 4, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'dir1', 4, 30, 1)

    assert(len(iso.joliet_vd.path_table_records) == 2)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 31, 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[1], 'dir1'.encode('utf-16_be'), 8, 32, 1)

    # Now check the root directory record.  With one file and one directory,
    # the root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 28 (2 beyond the
    # big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, False, 0)

    # Now check the empty directory record.  The name should be DIR1, and it
    # should start at extent 29.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"dir1", 38, 30)

    # Now check the Joliet root directory record.  With one directory, the
    # Joliet root directory record should have 4 entries ("dot", "dotdot", the
    # file, and the directory), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 31)

    # Now check the empty Joliet directory record.  The name should be dir1,
    # and it should start at extent 31.
    internal_check_empty_directory(iso.joliet_vd.root_dir_record.children[2], "dir1".encode('utf-16_be'), 42, 32)

    # Now check the file.  It should have a name of FOO.;1, it should have a
    # directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.pvd.root_dir_record.children[3], b"foo", 36, 33, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

    # Now check the Joliet file.  It should have a name of "foo", it should have
    # a directory record length of 40, it should start at extent 32, and its
    # contents should be "foo\n".
    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "foo".encode('utf-16_be'), 40, 33, 4)
    internal_check_file_contents(iso, "/foo", b"foo\n")

def check_eltorito_nofiles_hide(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 24, False, 0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 26, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

def check_joliet_and_eltorito_nofiles_hide(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files and El Torito and Joliet,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Joliet VD, 1 for the Joliet root dir record, and 4
    # for the Joliet path table), the path table should be 10 bytes long (for
    # the root directory entry), the little endian path table should start at
    # extent 21, and the big endian path table should start at extent 23 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 29 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_joliet_and_eltorito_nofiles_hide_only(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files and El Torito and Joliet,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Joliet VD, 1 for the Joliet root dir record, and 4
    # for the Joliet path table), the path table should be 10 bytes long (for
    # the root directory entry), the little endian path table should start at
    # extent 21, and the big endian path table should start at extent 23 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 29 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 3, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"BOOT.CAT;1", 44, 31, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_joliet_and_eltorito_nofiles_hide_iso_only(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files and El Torito and Joliet,
    # the ISO should be 33 extents (24 extents for the metadata, 1 for the El
    # Torito boot record, 1 for the El Torito boot catalog, 1 for the El Torito
    # boot file, 1 for the Joliet VD, 1 for the Joliet root dir record, and 4
    # for the Joliet path table), the path table should be 10 bytes long (for
    # the root directory entry), the little endian path table should start at
    # extent 21, and the big endian path table should start at extent 23 (since
    # the little endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 33, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 29, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 29, 1)

    assert(len(iso.joliet_vd.path_table_records) == 1)
    internal_check_ptr(iso.joliet_vd.path_table_records[0], b'\x00', 1, 30, 1)

    # Now check the root directory record.  With El Torito, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot catalog, and the
    # boot file), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 29 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 29, False, 0)

    # Now check the Joliet root directory record.  With El Torito, the Joliet
    # root directory record should have 4 entries ("dot", "dotdot", the boot
    # catalog, and the boot file), the data length is exactly one extent (2048
    # bytes), and the root directory should start at extent 30 (one past the
    # non-Joliet directory record).
    internal_check_joliet_root_dir_record(iso.joliet_vd.root_dir_record, 4, 2048, 30)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 32, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.;1", 40, 32, 5)
    internal_check_file_contents(iso, "/BOOT.;1", b"boot\n")

    internal_check_file(iso.joliet_vd.root_dir_record.children[3], "boot.cat".encode('utf-16_be'), 50, None, 2048)

    internal_check_file(iso.joliet_vd.root_dir_record.children[2], "boot".encode('utf-16_be'), 42, 32, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

def check_hard_link_reshuffle(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 24, 4)
    internal_check_file_contents(iso, "/FOO.;1", b"foo\n")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4)
    internal_check_file_contents(iso, "/BAR.;1", b"foo\n")

def check_rr_deeper_dir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 86016)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 42, 202, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 18)
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'A1', 2, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], b'DIR1', 4, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[3], b'RR_MOVED', 8, -1, 1)
    internal_check_ptr(iso.pvd.path_table_records[4], b'A2', 2, -1, 2)
    internal_check_ptr(iso.pvd.path_table_records[5], b'DIR2', 4, -1, 3)
    internal_check_ptr(iso.pvd.path_table_records[6], b'A8', 2, -1, 4)
    internal_check_ptr(iso.pvd.path_table_records[7], b'DIR8', 4, -1, 4)
    internal_check_ptr(iso.pvd.path_table_records[8], b'A3', 2, -1, 5)
    internal_check_ptr(iso.pvd.path_table_records[9], b'DIR3', 4, -1, 6)
    internal_check_ptr(iso.pvd.path_table_records[10], b'A4', 2, -1, 9)
    internal_check_ptr(iso.pvd.path_table_records[11], b'DIR4', 4, -1, 10)
    internal_check_ptr(iso.pvd.path_table_records[12], b'A5', 2, -1, 11)
    internal_check_ptr(iso.pvd.path_table_records[13], b'DIR5', 4, -1, 12)
    internal_check_ptr(iso.pvd.path_table_records[14], b'A6', 2, -1, 13)
    internal_check_ptr(iso.pvd.path_table_records[15], b'DIR6', 4, -1, 14)
    internal_check_ptr(iso.pvd.path_table_records[16], b'A7', 2, -1, 15)
    internal_check_ptr(iso.pvd.path_table_records[17], b'DIR7', 4, -1, 16)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 23, True, 5)

def check_eltorito_boot_info_table_large_odd(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 28, 10, 21, 23)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 26, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    boot_rec = iso.pvd.root_dir_record.children[2]
    internal_check_file(boot_rec, b"boot", 38, 27, 81)

    internal_check_file_contents(iso, "/boot", b"booboobo\x10\x00\x00\x00\x1b\x00\x00\x00\x51\x00\x00\x00\x1e\xb1\xa3\xb0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00ooboobooboobooboo")

    assert(boot_rec.boot_info_table is not None)
    assert(boot_rec.boot_info_table.pvd_extent == 16)
    assert(boot_rec.boot_info_table.rec_extent == 27)
    assert(boot_rec.boot_info_table.orig_len == 81)
    assert(boot_rec.boot_info_table.csum == 0xb0a3b11e)

def check_joliet_large_directory(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 264192)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 129, 678, 20, 22)

    # Do checks on the Joliet volume descriptor.  On a Joliet ISO with no files,
    # the number of extents should be the same as the PVD, the path table should
    # be 10 bytes (for the root directory entry), the little endian path table
    # should start at extent 24, and the big endian path table should start at
    # extent 26 (since the little endian path table record is always rounded up
    # to 2 extents).
    internal_check_joliet(iso.svds[0], 129, 874, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With one symlink, there should be
    # one entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 50)

    assert(len(iso.joliet_vd.path_table_records) == 50)

    # FIXME: this test should probably be more comprehensive

def check_zero_byte_file(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"FOO.;1", 40, 25, 0)
    internal_check_file_contents(iso, "/FOO.;1", b"")

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BAR.;1", 40, 24, 4)
    internal_check_file_contents(iso, "/BAR.;1", b"bar\n")

def check_eltorito_hide_boot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 27, 10, 20, 22)

    # Check to ensure the El Torito information is sane.  The boot catalog
    # should start at extent 25, and the initial entry should start at
    # extent 26.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 25, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 24, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[2], b"BOOT.CAT;1", 44, 25, 2048)

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
    # Make sure the filesize is what we expect.
    assert(filesize == 151552)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 74, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    dir1_record = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1_record, 50, b"DIR1", 38, 24, False, None, 0, False)

def check_duplicate_pvd(iso, filesize):
    assert(filesize == 102400)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 20, 22)

    internal_check_pvd(iso.pvds[1], 17, 25, 10, 20, 22)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 24, False, 0)

def check_eltorito_multi_multi_boot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 61440)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 30, 10, 21, 23)

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

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 6, 2048, 25, False, 0)

    # Now check the boot catalog file.  It should have a name of BOOT.CAT;1,
    # it should have a directory record length of 44, and it should start at
    # extent 25.
    internal_check_file(iso.pvd.root_dir_record.children[3], b"boot.cat", 42, 26, 2048)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"boot", 38, 27, 5)
    internal_check_file_contents(iso, "/boot", b"boot\n")

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[4], b"boot2", 38, 28, 6)
    internal_check_file_contents(iso, "/boot2", b"boot2\n")

def check_hidden_file(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (24 extents for the metadata, 1 for the eltorito boot record,
    # 1 for the boot catalog, and 1 for the boot file), the path table should
    # be exactly 10 bytes long (the root directory entry), the little endian
    # path table should start at extent 20 (default when there is just the PVD
    # and the Eltorito Boot Record), and the big endian path table should start
    # at extent 22 (since the little endian path table record is always rounded
    # up to 2 extents).
    internal_check_pvd(iso.pvd, 16, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files, there should be one
    # entry (the root entry).
    assert(len(iso.pvd.path_table_records) == 1)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the boot file.  It should have a name of BOOT.;1, it should
    # have a directory record length of 40, it should start at extent 26, and
    # its contents should be "boot\n".
    internal_check_file(iso.pvd.root_dir_record.children[2], b"AAAAAAAA.;1", 44, 24, 3, hidden=True)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", b"aa\n")

def check_hidden_dir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 16, 25, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With just one dir, there should
    # be two entries (the root entry and the directory).
    assert(len(iso.pvd.path_table_records) == 2)
    # The first entry in the PTR should have an identifier of the byte 0, it
    # should have a len of 1, it should start at extent 23, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[0], b'\x00', 1, 23, 1)
    # The first entry in the PTR should have an identifier of 'DIR1', it
    # should have a len of 4, it should start at extent 24, and its parent
    # directory number should be 1.
    internal_check_ptr(iso.pvd.path_table_records[1], b'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have 3 entries ("dot", "dotdot", and the
    # directory), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 23 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # Now check the one empty directory.  Its name should be DIR1, and it should
    # start at extent 24.
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], b"DIR1", 38, 24, hidden=True)

# FIXME: add a test where we use non-standard names for the Eltorito files.
