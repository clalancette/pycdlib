import StringIO
import pytest
import os
import sys
import struct

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

# Technically, Rock Ridge doesn't impose a length limitation on NM (alternate
# name) or SL (symlinks).  However, in practice, the Linux kernel (at least
# ext4) doesn't support any names longer than 255, and the ISO driver doesn't
# support any names longer than 248.  Thus we stick to 248 for our tests.
RR_MAX_FILENAME_LENGTH = 248

################################ INTERNAL HELPERS #############################

def internal_check_pvd(pvd, size, ptbl_size, ptbl_location_le, ptbl_location_be):
    # The primary volume descriptor should always have a type of 1.
    assert(pvd.descriptor_type == 1)
    # The primary volume descriptor should always have an identifier of "CD001".
    assert(pvd.identifier == "CD001")
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
    assert(pvd.volume_set_identifier == ' '*128)
    # The publisher identifier text should be blank.
    assert(pvd.publisher_identifier.text == ' '*128)
    # The preparer identifier text should be blank.
    assert(pvd.preparer_identifier.text == ' '*128)
    # The copyright file identifier should be blank.
    assert(pvd.copyright_file_identifier == ' '*37)
    # The abstract file identifier should be blank.
    assert(pvd.abstract_file_identifier == ' '*37)
    # The bibliographic file identifier should be blank.
    assert(pvd.bibliographic_file_identifier == ' '*37)
    # The primary volume descriptor should always have a file structure version
    # of 1.
    assert(pvd.file_structure_version == 1)
    # The length of the application use string should always be 512.
    assert(len(pvd.application_use) == 512)
    # The PVD should always be at extent 16.
    assert(pvd.extent_location() == 16)

def internal_check_eltorito(brs, boot_catalog, boot_catalog_extent, load_rba):
    # Now check the Eltorito Boot Record.

    # We support only one boot record for now.
    assert(len(brs) == 1)
    eltorito = brs[0]
    # The boot record should always have a type of 0.
    assert(eltorito.descriptor_type == 0)
    # The identifier should always be "CD001".
    assert(eltorito.identifier == "CD001")
    # The version should always be 1.
    assert(eltorito.version == 1)
    # The boot_system_identifier for El Torito should always be a space-padded
    # version of "EL TORITO SPECIFICATION".
    assert(eltorito.boot_system_identifier == "{:\x00<32}".format("EL TORITO SPECIFICATION"))
    # The boot identifier should always be 32 zeros.
    assert(eltorito.boot_identifier == "\x00"*32)
    # The boot_system_use field should always contain the boot catalog extent
    # encoded as a string.
    assert(eltorito.boot_system_use[:4] == struct.pack("=L", boot_catalog_extent))
    # The boot catalog validation entry should have a header id of 1.
    assert(boot_catalog.validation_entry.header_id == 1)
    # The boot catalog validation entry should have a platform id of 0.
    assert(boot_catalog.validation_entry.platform_id == 0)
    # The boot catalog validation entry should have an id string of all zeros.
    assert(boot_catalog.validation_entry.id_string == "\x00"*24)
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
    assert(boot_catalog.initial_entry.load_segment == 0x0)
    # The boot catalog initial entry should have a system type of 0.
    assert(boot_catalog.initial_entry.system_type == 0)
    # The boot catalog initial entry should have a sector count of 4.
    assert(boot_catalog.initial_entry.sector_count == 4)
    # The boot catalog initial entry should have the correct load rba.
    assert(boot_catalog.initial_entry.load_rba == load_rba)
    # The El Torito boot record should always be at extent 17.
    assert(eltorito.extent_location() == 17)

def internal_check_joliet(svds, space_size, path_tbl_size, path_tbl_loc_le,
                          path_tbl_loc_be):
    # Now check out the Joliet stuff.
    assert(len(svds) == 1)

    svd = svds[0]
    # The supplementary volume descriptor should always have a type of 2.
    assert(svd.descriptor_type == 2)
    # The supplementary volume descriptor should always have an identifier
    # of "CD001".
    assert(svd.identifier == "CD001")
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
    assert(svd.escape_sequences == '%/E'+'\x00'*29)
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
    assert(svd.volume_set_identifier == '\x00 '*64)
    # The publisher identifier text should be blank.
    assert(svd.publisher_identifier.text == '\x00 '*64)
    # The preparer identifier text should be blank.
    assert(svd.preparer_identifier.text == '\x00 '*64)
    # The copyright file identifier should be blank.
    assert(svd.copyright_file_identifier == '\x00 '*18+'\x00')
    # The abstract file identifier should be blank.
    assert(svd.abstract_file_identifier == '\x00 '*18+'\x00')
    # The bibliographic file identifier should be blank.
    assert(svd.bibliographic_file_identifier == '\x00 '*18+'\x00')
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
    assert(terminator.identifier == "CD001")
    # The volume descriptor set terminator should always have a version of 1.
    assert(terminator.version == 1)

    assert(terminator.extent_location() == extent)

def internal_check_root_dir_record(root_dir_record, num_children, data_length,
                                   extent_location, rr, rr_nlinks):
    # The first tests are things that are parsed from the ISO.

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
    assert(root_dir_record.file_flags == 0x2)
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
    assert(root_dir_record.file_ident == "\x00")
    assert(root_dir_record.parent == None)
    assert(root_dir_record.rock_ridge == None)
    # The number of children the root directory record has depends on the number
    # of files+directories there are at the top level.
    assert(len(root_dir_record.children) == num_children)

    # Now check the "dot" directory record.
    internal_check_dot_dir_record(root_dir_record.children[0], rr, rr_nlinks)

    # Now check the "dotdot" directory record.
    internal_check_dotdot_dir_record(root_dir_record.children[1], rr, rr_nlinks)

def internal_check_dot_dir_record(dot_record, rr=False, rr_nlinks=0):
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34 with no extensions.
    expected_dr_len = 34
    if rr:
        # The "dot" directory record length should be exactly 136 with Rock Ridge.
        expected_dr_len = 136

    assert(dot_record.dr_len == expected_dr_len)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 0x2)

    if rr:
        assert(dot_record.rock_ridge.initialized == True)
        assert(dot_record.rock_ridge.su_entry_version == 1)
        assert(dot_record.rock_ridge.rr_record.rr_flags == 0x81)
        assert(dot_record.rock_ridge.px_record.posix_file_mode == 040555)
        assert(dot_record.rock_ridge.px_record.posix_file_links == rr_nlinks)
        assert(dot_record.rock_ridge.px_record.posix_user_id == 0)
        assert(dot_record.rock_ridge.px_record.posix_group_id == 0)
        assert(dot_record.rock_ridge.px_record.posix_serial_number == 0)
        assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_id == 'RRIP_1991A')
        assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_des == 'THE ROCK RIDGE INTERCHANGE PROTOCOL PROVIDES SUPPORT FOR POSIX FILE SYSTEM SEMANTICS')
        assert(dot_record.rock_ridge.ce_record.continuation_entry.er_record.ext_src == 'PLEASE CONTACT DISC PUBLISHER FOR SPECIFICATION SOURCE.  SEE PUBLISHER IDENTIFIER IN PRIMARY VOLUME DESCRIPTOR FOR CONTACT INFORMATION.')
        assert(dot_record.rock_ridge.es_record == None)
        assert(dot_record.rock_ridge.nm_record == None)
        assert(dot_record.rock_ridge.pn_record == None)
        assert(dot_record.rock_ridge.tf_record.creation_time == None)
        assert(type(dot_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
        assert(type(dot_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
        assert(dot_record.rock_ridge.tf_record.backup_time == None)
        assert(dot_record.rock_ridge.tf_record.expiration_time == None)
        assert(dot_record.rock_ridge.tf_record.effective_time == None)

def internal_check_dotdot_dir_record(dotdot_record, rr=False, rr_nlinks=0):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == "\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34 with no extensions.
    expected_dr_len = 34
    if rr:
        # The "dotdot" directory record length should be exactly 102 with Rock Ridge.
        expected_dr_len = 102

    assert(dotdot_record.dr_len == expected_dr_len)
    # The "dotdot" directory record is not the root.
    assert(dotdot_record.is_root == False)
    # The "dotdot" directory record should have no children.
    assert(len(dotdot_record.children) == 0)
    assert(dotdot_record.file_flags == 0x2)

    if rr:
        assert(dotdot_record.rock_ridge.initialized == True)
        assert(dotdot_record.rock_ridge.su_entry_version == 1)
        assert(dotdot_record.rock_ridge.rr_record.rr_flags == 0x81)
        assert(dotdot_record.rock_ridge.px_record.posix_file_mode == 040555)
        assert(dotdot_record.rock_ridge.px_record.posix_file_links == rr_nlinks)
        assert(dotdot_record.rock_ridge.px_record.posix_user_id == 0)
        assert(dotdot_record.rock_ridge.px_record.posix_group_id == 0)
        assert(dotdot_record.rock_ridge.px_record.posix_serial_number == 0)
        assert(dotdot_record.rock_ridge.er_record == None)
        assert(dotdot_record.rock_ridge.es_record == None)
        assert(dotdot_record.rock_ridge.nm_record == None)
        assert(dotdot_record.rock_ridge.pn_record == None)
        assert(dotdot_record.rock_ridge.tf_record.creation_time == None)
        assert(type(dotdot_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
        assert(type(dotdot_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
        assert(dotdot_record.rock_ridge.tf_record.backup_time == None)
        assert(dotdot_record.rock_ridge.tf_record.expiration_time == None)
        assert(dotdot_record.rock_ridge.tf_record.effective_time == None)

def internal_check_file_contents(iso, path, contents):
    fout = StringIO.StringIO()
    iso.get_and_write(path, fout)
    assert(fout.getvalue() == contents)

def internal_check_ptr(ptr, name, len_di, loc, parent):
    assert(ptr.len_di == len_di)
    assert(ptr.xattr_length == 0)
    if loc >= 0:
        assert(ptr.extent_location == loc)
    assert(ptr.parent_directory_num == parent)
    assert(ptr.directory_identifier == name)

def internal_check_empty_directory(dirrecord, name, extent=None):
    # The "dir?" directory should have two children (the "dot", and the
    # "dotdot" entries).
    assert(len(dirrecord.children) == 2)
    # The "dir?" directory should be a directory.
    assert(dirrecord.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dirrecord.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dirrecord.file_ident == name)
    # The "dir?" directory record should have a length of 38.
    assert(dirrecord.dr_len == (33 + len(name) + (1 - (len(name) % 2))))
    assert(dirrecord.file_flags == 0x2)
    if extent is not None:
        assert(dirrecord.extent_location() == extent)
    # The "dir?" directory record should have a valid "dot" record.
    internal_check_dot_dir_record(dirrecord.children[0])
    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1])

def internal_check_file(dirrecord, name, dr_len, loc):
    assert(len(dirrecord.children) == 0)
    assert(dirrecord.isdir == False)
    assert(dirrecord.is_root == False)
    assert(dirrecord.file_ident == name)
    if dr_len > 0:
        assert(dirrecord.dr_len == dr_len)
    assert(dirrecord.extent_location() == loc)
    assert(dirrecord.file_flags == 0)

def internal_generate_inorder_names(numdirs):
    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append("DIR%d" % i)
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    return names

def internal_check_dir_record(dir_record, num_children, name, extent_location):
    # The "dir1" directory should have three children (the "dot", the "dotdot"
    # and the "bar" entries).
    assert(len(dir_record.children) == num_children)
    # The "dir1" directory should be a directory.
    assert(dir_record.isdir == True)
    # The "dir1" directory should not be the root.
    assert(dir_record.is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(dir_record.file_ident == name)
    # The "dir1" directory record should have a length of 38.
    assert(dir_record.dr_len == (33 + len(name) + (1 - (len(name) % 2))))
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(dir_record.extent_location() == extent_location)
    assert(dir_record.file_flags == 0x2)
    # The "dir1" directory record should have a valid "dot" record.
    internal_check_dot_dir_record(dir_record.children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir_record.children[1])

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
    internal_check_pvd(iso.pvd, 24, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, False, 0)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO.;1", StringIO.StringIO())

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
    internal_check_pvd(iso.pvd, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    internal_check_file(iso.pvd.root_dir_record.children[2], "FOO.;1", 40, 24)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")

def check_onedir(iso, filesize):
    assert(filesize == 51200)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 25, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], "DIR1", 24)

def check_twofile(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With two files, the ISO should be 26 extents (24
    # extents for the metadata, and 1 extent for each of the two short files).
    # The path table should be 10 bytes (for the root directory entry).
    internal_check_pvd(iso.pvd, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With two files at the root, the
    # root directory record should have "dot", "dotdot", and the two files as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    internal_check_file(iso.pvd.root_dir_record.children[3], "FOO.;1", 40, 25)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")

    internal_check_file(iso.pvd.root_dir_record.children[2], "BAR.;1", 40, 24)
    internal_check_file_contents(iso, "/BAR.;1", "bar\n")

def check_twodirs(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 26, 30, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 3)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'AA', 2, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], 'BB', 2, 25, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], "AA", 24)
    internal_check_empty_directory(iso.pvd.root_dir_record.children[3], "BB", 25)

def check_onefileonedir(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file and one directory, the ISO should be
    # 26 extents (24 extents for the metadata, 1 extent for the file, and 1
    # extent for the extra directory).  The path table should be 22 bytes (10
    # bytes for the root directory entry, and 12 bytes for the "dir1" entry).
    internal_check_pvd(iso.pvd, 26, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the one
    # file, and the one directory as children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], "DIR1", 24)

    internal_check_file(iso.pvd.root_dir_record.children[3], "FOO.;1", 40, 25)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")

    # Check to make sure accessing a directory raises an exception.
    out = StringIO.StringIO()
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/DIR1", out)

def check_onefile_onedirwithfile(iso, filesize):
    assert(filesize == 55296)

    # Do checks on the PVD.  With one file and one directory with a file, the
    # ISO should be 27 extents (24 extents for the metadata, 1 extent for the
    # file, 1 extent for the directory, and 1 more extent for the file.  The
    # path table should be 22 bytes (10 bytes for the root directory entry, and
    # 12 bytes for the "dir1" entry).
    internal_check_pvd(iso.pvd, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the file,
    # and the directory as children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, False, 0)

    dir1_record = iso.pvd.root_dir_record.children[2]

    internal_check_dir_record(dir1_record, 3, "DIR1", 24)

    internal_check_file(iso.pvd.root_dir_record.children[3], "FOO.;1", 40, 25)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")

    internal_check_file(dir1_record.children[2], "BAR.;1", 40, 26)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", "bar\n")

def check_twoextentfile(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one big file, the ISO should be 26 extents
    # (24 extents for the metadata, and 2 extents for the file).
    # The path table should be 10 bytes (for the root directory entry).
    internal_check_pvd(iso.pvd, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    internal_check_file(iso.pvd.root_dir_record.children[2], "BIGFILE.;1", 44, 24)
    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)
    internal_check_file_contents(iso, "/BIGFILE.;1", outstr)

def check_twoleveldeepdir(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one big file, the ISO should be 26 extents
    # (24 extents for the metadata, and 1 extent for the dir1 entry, and 1
    # extent for the subdir1 entry).
    # The path table should be 38 bytes (for the root directory entry, and the
    # dir1 entry, and the subdir1 entry).
    internal_check_pvd(iso.pvd, 26, 38, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 3)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], 'SUBDIR1', 7, 25, 2)

    # Now check the root directory record.  With one dir at the root, the
    # root directory record should have "dot", "dotdot", and the dir as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    dir1 = iso.pvd.root_dir_record.children[2]
    internal_check_dir_record(dir1, 3, 'DIR1', 24)

    # Now check the subdirectory.
    subdir1 = dir1.children[2]
    internal_check_empty_directory(subdir1, 'SUBDIR1')

def check_tendirs(iso, filesize):
    assert(filesize == 69632)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    internal_check_pvd(iso.pvd, 34, 132, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 12, 2048, 23, False, 0)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 10+1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(10)
    for index in range(2, 2+10):
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index])

def check_dirs_overflow_ptr_extent(iso, filesize):
    assert(filesize == 671744)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    internal_check_pvd(iso.pvd, 328, 4122, 19, 23)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 297, 12288, 27, False, 0)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 295+1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 27, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(295)
    for index in range(2, 2+295):
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index])

def check_dirs_just_short_ptr_extent(iso, filesize):
    assert(filesize == 659456)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    internal_check_pvd(iso.pvd, 322, 4094, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 295, 12288, 23, False, 0)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 293+1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    # The rest of the path table records will be checked by the loop below.

    names = internal_generate_inorder_names(293)
    for index in range(2, 2+293):
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        internal_check_ptr(iso.pvd.path_table_records[index-1], names[index], len(names[index]), -1, 1)

        internal_check_empty_directory(iso.pvd.root_dir_record.children[index], names[index])

def check_twoleveldeepfile(iso, filesize):
    assert(filesize == 55296)

    # Do checks on the PVD.  With one big file, the ISO should be 26 extents
    # (24 extents for the metadata, and 1 extent for the dir1 entry, and 1
    # extent for the subdir1 entry).
    # The path table should be 38 bytes (for the root directory entry, and the
    # dir1 entry, and the subdir1 entry).
    internal_check_pvd(iso.pvd, 27, 38, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 3)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], 'SUBDIR1', 7, 25, 2)

    # Now check the root directory record.  With one dir at the root, the
    # root directory record should have "dot", "dotdot", and the dir as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, False, 0)

    dir1 = iso.pvd.root_dir_record.children[2]
    # Now check the first level directory.
    # The "dir?" directory should have three children (the "dot", the "dotdot",
    # and the "SUBDIR1" entries).
    assert(len(dir1.children) == 3)
    # The "dir?" directory should be a directory.
    assert(dir1.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dir1.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dir1.file_ident == 'DIR1')
    # The "dir?" directory record should have a length of 38.
    assert(dir1.dr_len == (33 + len('DIR1') + (1 - (len('DIR1') % 2))))
    assert(dir1.file_flags == 0x2)
    # The "dir?" directory record should have a valid "dot" record.
    internal_check_dot_dir_record(dir1.children[0])
    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dir1.children[1])

    # Now check the subdirectory.
    # The "dir?" directory should have three children (the "dot", the "dotdot",
    # and the "SUBDIR1" entries).
    subdir1 = dir1.children[2]
    assert(len(subdir1.children) == 3)
    # The "dir?" directory should be a directory.
    assert(subdir1.isdir == True)
    # The "dir?" directory should not be the root.
    assert(subdir1.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(subdir1.file_ident == 'SUBDIR1')
    # The "dir?" directory record should have a length of 38.
    assert(subdir1.dr_len == (33 + len('SUBDIR1') + (1 - (len('SUBDIR1') % 2))))
    assert(subdir1.file_flags == 0x2)
    # The "dir?" directory record should have a valid "dot" record.
    internal_check_dot_dir_record(subdir1.children[0])
    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(subdir1.children[1])

    internal_check_file(subdir1.children[2], "FOO.;1", 40, 26)
    internal_check_file_contents(iso, "/DIR1/SUBDIR1/FOO.;1", "foo\n")

def check_joliet_nofiles(iso, filesize):
    assert(filesize == 61440)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 30, 10, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 30, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 28, False, 0)

def check_joliet_onedir(iso, filesize):
    assert(filesize == 65536)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 32, 22, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 32, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 29, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0)

    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], "DIR1", 29)

def check_joliet_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 63488)

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there
    # are no volume descriptors beyond the primary and the terminator), and
    # the big endian path table should start at extent 21 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 31, 10, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 31, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, False, 0)

    internal_check_file(iso.pvd.root_dir_record.children[2], "FOO.;1", 40, 30)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_joliet_onefileonedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry), the
    # little endian path table should start at extent 19 (default when there
    # are no volume descriptors beyond the primary and the terminator), and
    # the big endian path table should start at extent 21 (since the little
    # endian path table record is always rounded up to 2 extents).
    internal_check_pvd(iso.pvd, 33, 22, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 33, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 29, 1)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 28, False, 0)

    internal_check_empty_directory(iso.pvd.root_dir_record.children[2], "DIR1", 29)

    internal_check_file(iso.pvd.root_dir_record.children[3], "FOO.;1", 40, 32)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_eltorito_nofiles(iso, filesize):
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (the metadata), the path table should be exactly 10 bytes long
    # (the root directory entry), the little endian path table should start at
    # extent 20 (default when there is just the PVD and the Eltorito Boot
    # Record), and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 10, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x19, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 24,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, False, 0)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 40, 26)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_eltorito_twofile(iso, filesize):
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (the metadata), the path table should be exactly 10 bytes long
    # (the root directory entry), the little endian path table should start at
    # extent 20 (default when there is just the PVD and the Eltorito Boot
    # Record), and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 28, 10, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x19, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 24,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, False, 0)

    # Now check out the "aa" directory record.
    aarecord = iso.pvd.root_dir_record.children[2]
    # The file identifier for the "aa" directory entry should be AA.;1.
    assert(aarecord.file_ident == "AA.;1")
    # The "aa" directory entry should not be a directory.
    assert(aarecord.isdir == False)
    # The "aa" directory record length should be exactly 40.
    assert(aarecord.dr_len == 38)
    # The "aa" directory record is not the root.
    assert(aarecord.is_root == False)
    # The "a" directory record should have no children.
    assert(len(aarecord.children) == 0)
    assert(aarecord.file_flags == 0)

    internal_check_file(iso.pvd.root_dir_record.children[3], "BOOT.;1", 40, 26)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[4]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_rr_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23, True, 2)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO.;1", StringIO.StringIO())

def check_rr_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 25)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.nm_record.posix_name == 'foo')
    assert(foo_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(foo_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(foo_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.effective_time == None)
    internal_check_file_contents(iso, "/foo", "foo\n")

    out = StringIO.StringIO()
    # Make sure trying to get a non-existent file raises an exception
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/BAR.;1", out)

def check_rr_twofile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    bar_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(bar_dir_record, "BAR.;1", 116, 25)
    internal_check_file_contents(iso, "/BAR.;1", "bar\n")
    # Now check rock ridge extensions.
    assert(bar_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(bar_dir_record.rock_ridge.nm_record.posix_name == 'bar')
    assert(bar_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(bar_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(bar_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(bar_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(bar_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(bar_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(bar_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(bar_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(bar_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(bar_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(bar_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(bar_dir_record.rock_ridge.tf_record.effective_time == None)
    internal_check_file_contents(iso, "/bar", "bar\n")

    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 26)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.nm_record.posix_name == 'foo')
    assert(foo_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(foo_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(foo_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.effective_time == None)
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_rr_onefileonedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    # The "dir1" directory should not have any children.
    assert(len(dir1_dir_record.children) == 2)
    # The "dir1" directory should not be a directory.
    assert(dir1_dir_record.isdir == True)
    # The "dir1" directory should not be the root.
    assert(dir1_dir_record.is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(dir1_dir_record.file_ident == "DIR1")
    # The "dir1" directory record should have a length of 114.
    assert(dir1_dir_record.dr_len == 114)
    # The "dir1" data should start at extent 25.
    assert(dir1_dir_record.extent_location() == 24)
    assert(dir1_dir_record.file_flags == 2)
    # Now check rock ridge extensions.
    assert(dir1_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dir1_dir_record.rock_ridge.nm_record.posix_name == 'dir1')
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_mode == 040555)
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_links == 2)
    assert(dir1_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dir1_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dir1_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(dir1_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.effective_time == None)

    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 26)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.nm_record.posix_name == 'foo')
    assert(foo_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(foo_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(foo_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.effective_time == None)
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_rr_onefileonedirwithfile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 28, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    # The "dir1" directory should not have any children.
    assert(len(dir1_dir_record.children) == 3)
    # The "dir1" directory should not be a directory.
    assert(dir1_dir_record.isdir == True)
    # The "dir1" directory should not be the root.
    assert(dir1_dir_record.is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(dir1_dir_record.file_ident == "DIR1")
    # The "dir1" directory record should have a length of 114.
    assert(dir1_dir_record.dr_len == 114)
    # The "dir1" data should start at extent 25.
    assert(dir1_dir_record.extent_location() == 24)
    assert(dir1_dir_record.file_flags == 2)
    # Now check rock ridge extensions.
    assert(dir1_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dir1_dir_record.rock_ridge.nm_record.posix_name == 'dir1')
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_mode == 040555)
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_links == 2)
    assert(dir1_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dir1_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dir1_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(dir1_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.effective_time == None)

    foo_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 26)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.nm_record.posix_name == 'foo')
    assert(foo_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(foo_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(foo_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.effective_time == None)

    bar_dir_record = dir1_dir_record.children[2]
    internal_check_file(bar_dir_record, "BAR.;1", 116, 27)
    internal_check_file_contents(iso, "/DIR1/BAR.;1", "bar\n")
    # Now check rock ridge extensions.
    assert(bar_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(bar_dir_record.rock_ridge.nm_record.posix_name == 'bar')
    assert(bar_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(bar_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(bar_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(bar_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(bar_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(bar_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(bar_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(bar_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(bar_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(bar_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(bar_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(bar_dir_record.rock_ridge.tf_record.effective_time == None)
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_rr_symlink(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 53248)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 26, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 25)
    internal_check_file_contents(iso, "/FOO.;1", "foo\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.nm_record.posix_name == 'foo')
    assert(foo_dir_record.rock_ridge.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(foo_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(foo_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(foo_dir_record.rock_ridge.tf_record.effective_time == None)

    sym_dir_record = iso.pvd.root_dir_record.children[3]
    # The "sym" file should not have any children.
    assert(len(sym_dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(sym_dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(sym_dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(sym_dir_record.file_ident == "SYM.;1")
    # The "sym" directory record should have a length of 126.
    assert(sym_dir_record.dr_len == 126)
    # The "sym" data should start at extent 26.
    assert(sym_dir_record.extent_location() == 26)
    assert(sym_dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(sym_dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(sym_dir_record.rock_ridge.nm_record.posix_name == 'sym')
    assert(sym_dir_record.rock_ridge.px_record.posix_file_mode == 0120555)
    assert(sym_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(sym_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(sym_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(sym_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(sym_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.effective_time == None)
    assert(len(sym_dir_record.rock_ridge.sl_records[0].symlink_components) == 1)
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[0] == 'foo')
    internal_check_file_contents(iso, "/foo", "foo\n")
    with pytest.raises(pyiso.PyIsoException):
        internal_check_file_contents(iso, "/sym", "foo\n")

def check_rr_symlink2(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 22, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 3)

    dir1_dir_record = iso.pvd.root_dir_record.children[2]
    assert(dir1_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dir1_dir_record.rock_ridge.nm_record.posix_name == 'dir1')
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_mode == 040555)
    assert(dir1_dir_record.rock_ridge.px_record.posix_file_links == 2)
    assert(dir1_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dir1_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dir1_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dir1_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dir1_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(dir1_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(dir1_dir_record.rock_ridge.tf_record.effective_time == None)

    foo_dir_record = dir1_dir_record.children[2]
    internal_check_file(foo_dir_record, "FOO.;1", 116, 26)
    internal_check_file_contents(iso, "/DIR1/FOO.;1", "foo\n")

    sym_dir_record = iso.pvd.root_dir_record.children[3]
    # The "sym" file should not have any children.
    assert(len(sym_dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(sym_dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(sym_dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(sym_dir_record.file_ident == "SYM.;1")
    # The "sym" directory record should have a length of 126.
    assert(sym_dir_record.dr_len == 132)
    # The "sym" data should start at extent 26.
    assert(sym_dir_record.extent_location() == 26)
    assert(sym_dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(sym_dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(sym_dir_record.rock_ridge.nm_record.posix_name == 'sym')
    assert(sym_dir_record.rock_ridge.px_record.posix_file_mode == 0120555)
    assert(sym_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(sym_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(sym_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(sym_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(sym_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.effective_time == None)
    assert(len(sym_dir_record.rock_ridge.sl_records[0].symlink_components) == 2)
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[0] == 'dir1')
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[1] == 'foo')
    internal_check_file_contents(iso, "/dir1/foo", "foo\n")

def check_rr_symlink_dot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    sym_dir_record = iso.pvd.root_dir_record.children[2]
    # The "sym" file should not have any children.
    assert(len(sym_dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(sym_dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(sym_dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(sym_dir_record.file_ident == "SYM.;1")
    # The "sym" directory record should have a length of 126.
    assert(sym_dir_record.dr_len == 122)
    # The "sym" data should start at extent 26.
    assert(sym_dir_record.extent_location() == 25)
    assert(sym_dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(sym_dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(sym_dir_record.rock_ridge.nm_record.posix_name == 'sym')
    assert(sym_dir_record.rock_ridge.px_record.posix_file_mode == 0120555)
    assert(sym_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(sym_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(sym_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(sym_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(sym_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.effective_time == None)
    assert(len(sym_dir_record.rock_ridge.sl_records[0].symlink_components) == 1)
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[0] == '.')

def check_rr_symlink_dotdot(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    sym_dir_record = iso.pvd.root_dir_record.children[2]
    # The "sym" file should not have any children.
    assert(len(sym_dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(sym_dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(sym_dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(sym_dir_record.file_ident == "SYM.;1")
    # The "sym" directory record should have a length of 126.
    assert(sym_dir_record.dr_len == 122)
    # The "sym" data should start at extent 26.
    assert(sym_dir_record.extent_location() == 25)
    assert(sym_dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(sym_dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(sym_dir_record.rock_ridge.nm_record.posix_name == 'sym')
    assert(sym_dir_record.rock_ridge.px_record.posix_file_mode == 0120555)
    assert(sym_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(sym_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(sym_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(sym_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(sym_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.effective_time == None)
    assert(len(sym_dir_record.rock_ridge.sl_records[0].symlink_components) == 1)
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[0] == '..')

def check_rr_symlink_broken(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 51200)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 25, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    sym_dir_record = iso.pvd.root_dir_record.children[2]
    # The "sym" file should not have any children.
    assert(len(sym_dir_record.children) == 0)
    # The "sym" file should not be a directory.
    assert(sym_dir_record.isdir == False)
    # The "sym" file should not be the root.
    assert(sym_dir_record.is_root == False)
    # The "sym" file should have an ISO9660 mangled name of "SYM.;1".
    assert(sym_dir_record.file_ident == "SYM.;1")
    # The "sym" directory record should have a length of 126.
    assert(sym_dir_record.dr_len == 126)
    # The "sym" data should start at extent 26.
    assert(sym_dir_record.extent_location() == 25)
    assert(sym_dir_record.file_flags == 0)
    # Now check rock ridge extensions.
    assert(sym_dir_record.rock_ridge.rr_record.rr_flags == 0x8d)
    assert(sym_dir_record.rock_ridge.nm_record.posix_name == 'sym')
    assert(sym_dir_record.rock_ridge.px_record.posix_file_mode == 0120555)
    assert(sym_dir_record.rock_ridge.px_record.posix_file_links == 1)
    assert(sym_dir_record.rock_ridge.px_record.posix_user_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_group_id == 0)
    assert(sym_dir_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(sym_dir_record.rock_ridge.tf_record.creation_time == None)
    assert(type(sym_dir_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(sym_dir_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(sym_dir_record.rock_ridge.tf_record.backup_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.expiration_time == None)
    assert(sym_dir_record.rock_ridge.tf_record.effective_time == None)
    assert(len(sym_dir_record.rock_ridge.sl_records[0].symlink_components) == 1)
    assert(sym_dir_record.rock_ridge.sl_records[0].symlink_components[0] == 'foo')

def check_alternating_subdir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 61440)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 30, 30, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 3)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'AA', 2, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[2], 'CC', 2, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 6, 2048, 23, False, 0)

    aa_dir_record = iso.pvd.root_dir_record.children[2]
    # The "aa" directory should not have any children.
    assert(len(aa_dir_record.children) == 3)
    # The "aa" directory should not be a directory.
    assert(aa_dir_record.isdir == True)
    # The "aa" directory should not be the root.
    assert(aa_dir_record.is_root == False)
    # The "aa" directory should have an ISO9660 mangled name of "AA".
    assert(aa_dir_record.file_ident == "AA")
    # The "aa" directory record should have a length of 114.
    assert(aa_dir_record.dr_len == 36)
    # The "aa" data should start at extent 24.
    assert(aa_dir_record.extent_location() == 24)
    assert(aa_dir_record.file_flags == 2)

    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(bb_dir_record, "BB.;1", 38, 26)
    internal_check_file_contents(iso, "/BB.;1", "bb\n")

    cc_dir_record = iso.pvd.root_dir_record.children[4]
    # The "cc" directory should not have any children.
    assert(len(cc_dir_record.children) == 3)
    # The "cc" directory should not be a directory.
    assert(cc_dir_record.isdir == True)
    # The "cc" directory should not be the root.
    assert(cc_dir_record.is_root == False)
    # The "cc" directory should have an ISO9660 mangled name of "CC".
    assert(cc_dir_record.file_ident == "CC")
    # The "cc" directory record should have a length of 114.
    assert(cc_dir_record.dr_len == 36)
    # The "cc" data should start at extent 25.
    assert(cc_dir_record.extent_location() == 25)
    assert(cc_dir_record.file_flags == 2)

    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_file(dd_dir_record, "DD.;1", 38, 27)
    internal_check_file_contents(iso, "/DD.;1", "dd\n")

    subdir1_dir_record = aa_dir_record.children[2]
    internal_check_file(subdir1_dir_record, "SUB1.;1", 40, 28)
    internal_check_file_contents(iso, "/AA/SUB1.;1", "sub1\n")

    subdir2_dir_record = cc_dir_record.children[2]
    internal_check_file(subdir2_dir_record, "SUB2.;1", 40, 29)
    internal_check_file_contents(iso, "/CC/SUB2.;1", "sub2\n")

def check_rr_verylongname(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23, True, 2)

    foo_dir_record = iso.pvd.root_dir_record.children[2]
    # Check the foo dir record, but skip the length check (genisoimage gets it wrong).
    internal_check_file(foo_dir_record, "AAAAAAAA.;1", -1, 26)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", "aa\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.name() == 'a'*RR_MAX_FILENAME_LENGTH)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record == None)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'a'*RR_MAX_FILENAME_LENGTH, "aa\n")

def check_rr_manylongname(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 33, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 9, 2048, 23, True, 2)

    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(aa_dir_record, "AAAAAAAA.;1", -1, 26)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", "aa\n")
    # Now check rock ridge extensions.
    assert(aa_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(aa_dir_record.rock_ridge.name() == 'a'*RR_MAX_FILENAME_LENGTH)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(aa_dir_record.rock_ridge.tf_record == None)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'a'*RR_MAX_FILENAME_LENGTH, "aa\n")

    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(bb_dir_record, "BBBBBBBB.;1", -1, 27)
    internal_check_file_contents(iso, "/BBBBBBBB.;1", "bb\n")
    # Now check rock ridge extensions.
    assert(bb_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(bb_dir_record.rock_ridge.name() == 'b'*RR_MAX_FILENAME_LENGTH)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(bb_dir_record.rock_ridge.tf_record == None)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'b'*RR_MAX_FILENAME_LENGTH, "bb\n")

    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_file(cc_dir_record, "CCCCCCCC.;1", -1, 28)
    internal_check_file_contents(iso, "/CCCCCCCC.;1", "cc\n")
    # Now check rock ridge extensions.
    assert(cc_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(cc_dir_record.rock_ridge.name() == 'c'*RR_MAX_FILENAME_LENGTH)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(cc_dir_record.rock_ridge.tf_record == None)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'c'*RR_MAX_FILENAME_LENGTH, "cc\n")

    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_file(dd_dir_record, "DDDDDDDD.;1", -1, 29)
    internal_check_file_contents(iso, "/DDDDDDDD.;1", "dd\n")
    # Now check rock ridge extensions.
    assert(dd_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dd_dir_record.rock_ridge.name() == 'd'*RR_MAX_FILENAME_LENGTH)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(dd_dir_record.rock_ridge.tf_record == None)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'d'*RR_MAX_FILENAME_LENGTH, "dd\n")

    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_file(ee_dir_record, "EEEEEEEE.;1", -1, 30)
    internal_check_file_contents(iso, "/EEEEEEEE.;1", "ee\n")
    # Now check rock ridge extensions.
    assert(ee_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(ee_dir_record.rock_ridge.name() == 'e'*RR_MAX_FILENAME_LENGTH)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(ee_dir_record.rock_ridge.tf_record == None)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'e'*RR_MAX_FILENAME_LENGTH, "ee\n")

    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_file(ff_dir_record, "FFFFFFFF.;1", -1, 31)
    internal_check_file_contents(iso, "/FFFFFFFF.;1", "ff\n")
    # Now check rock ridge extensions.
    assert(ff_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(ff_dir_record.rock_ridge.name() == 'f'*RR_MAX_FILENAME_LENGTH)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(ff_dir_record.rock_ridge.tf_record == None)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'f'*RR_MAX_FILENAME_LENGTH, "ff\n")

    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_file(gg_dir_record, "GGGGGGGG.;1", -1, 32)
    internal_check_file_contents(iso, "/GGGGGGGG.;1", "gg\n")
    # Now check rock ridge extensions.
    assert(gg_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(gg_dir_record.rock_ridge.name() == 'g'*RR_MAX_FILENAME_LENGTH)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(gg_dir_record.rock_ridge.tf_record == None)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'g'*RR_MAX_FILENAME_LENGTH, "gg\n")

def check_rr_manylongname2(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 71680)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 35, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 10, 4096, 23, True, 2)

    aa_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(aa_dir_record, "AAAAAAAA.;1", -1, 27)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", "aa\n")
    # Now check rock ridge extensions.
    assert(aa_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(aa_dir_record.rock_ridge.name() == 'a'*RR_MAX_FILENAME_LENGTH)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(aa_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(aa_dir_record.rock_ridge.tf_record == None)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(aa_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'a'*RR_MAX_FILENAME_LENGTH, "aa\n")

    bb_dir_record = iso.pvd.root_dir_record.children[3]
    internal_check_file(bb_dir_record, "BBBBBBBB.;1", -1, 28)
    internal_check_file_contents(iso, "/BBBBBBBB.;1", "bb\n")
    # Now check rock ridge extensions.
    assert(bb_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(bb_dir_record.rock_ridge.name() == 'b'*RR_MAX_FILENAME_LENGTH)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(bb_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(bb_dir_record.rock_ridge.tf_record == None)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(bb_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'b'*RR_MAX_FILENAME_LENGTH, "bb\n")

    cc_dir_record = iso.pvd.root_dir_record.children[4]
    internal_check_file(cc_dir_record, "CCCCCCCC.;1", -1, 29)
    internal_check_file_contents(iso, "/CCCCCCCC.;1", "cc\n")
    # Now check rock ridge extensions.
    assert(cc_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(cc_dir_record.rock_ridge.name() == 'c'*RR_MAX_FILENAME_LENGTH)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(cc_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(cc_dir_record.rock_ridge.tf_record == None)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(cc_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'c'*RR_MAX_FILENAME_LENGTH, "cc\n")

    dd_dir_record = iso.pvd.root_dir_record.children[5]
    internal_check_file(dd_dir_record, "DDDDDDDD.;1", -1, 30)
    internal_check_file_contents(iso, "/DDDDDDDD.;1", "dd\n")
    # Now check rock ridge extensions.
    assert(dd_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(dd_dir_record.rock_ridge.name() == 'd'*RR_MAX_FILENAME_LENGTH)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(dd_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(dd_dir_record.rock_ridge.tf_record == None)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dd_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'d'*RR_MAX_FILENAME_LENGTH, "dd\n")

    ee_dir_record = iso.pvd.root_dir_record.children[6]
    internal_check_file(ee_dir_record, "EEEEEEEE.;1", -1, 31)
    internal_check_file_contents(iso, "/EEEEEEEE.;1", "ee\n")
    # Now check rock ridge extensions.
    assert(ee_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(ee_dir_record.rock_ridge.name() == 'e'*RR_MAX_FILENAME_LENGTH)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(ee_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(ee_dir_record.rock_ridge.tf_record == None)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(ee_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'e'*RR_MAX_FILENAME_LENGTH, "ee\n")

    ff_dir_record = iso.pvd.root_dir_record.children[7]
    internal_check_file(ff_dir_record, "FFFFFFFF.;1", -1, 32)
    internal_check_file_contents(iso, "/FFFFFFFF.;1", "ff\n")
    # Now check rock ridge extensions.
    assert(ff_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(ff_dir_record.rock_ridge.name() == 'f'*RR_MAX_FILENAME_LENGTH)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(ff_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(ff_dir_record.rock_ridge.tf_record == None)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(ff_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'f'*RR_MAX_FILENAME_LENGTH, "ff\n")

    gg_dir_record = iso.pvd.root_dir_record.children[8]
    internal_check_file(gg_dir_record, "GGGGGGGG.;1", -1, 33)
    internal_check_file_contents(iso, "/GGGGGGGG.;1", "gg\n")
    # Now check rock ridge extensions.
    assert(gg_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(gg_dir_record.rock_ridge.name() == 'g'*RR_MAX_FILENAME_LENGTH)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(gg_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(gg_dir_record.rock_ridge.tf_record == None)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(gg_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'g'*RR_MAX_FILENAME_LENGTH, "gg\n")

    hh_dir_record = iso.pvd.root_dir_record.children[9]
    internal_check_file(hh_dir_record, "HHHHHHHH.;1", -1, 34)
    internal_check_file_contents(iso, "/HHHHHHHH.;1", "hh\n")
    # Now check rock ridge extensions.
    assert(hh_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(hh_dir_record.rock_ridge.name() == 'h'*RR_MAX_FILENAME_LENGTH)
    assert(hh_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(hh_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(hh_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(hh_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(hh_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(hh_dir_record.rock_ridge.tf_record == None)
    assert(type(hh_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(hh_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(hh_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'h'*RR_MAX_FILENAME_LENGTH, "hh\n")

def check_rr_verylongnameandsymlink(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 55296)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 27, 10, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 2)

    foo_dir_record = iso.pvd.root_dir_record.children[2]
    internal_check_file(foo_dir_record, "AAAAAAAA.;1", -1, 26)
    internal_check_file_contents(iso, "/AAAAAAAA.;1", "aa\n")
    # Now check rock ridge extensions.
    assert(foo_dir_record.rock_ridge.rr_record.rr_flags == 0x89)
    assert(foo_dir_record.rock_ridge.name() == 'a'*RR_MAX_FILENAME_LENGTH)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_mode == 0100444)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_file_links == 1)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_user_id == 0)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_group_id == 0)
    assert(foo_dir_record.rock_ridge.ce_record.continuation_entry.px_record.posix_serial_number == 0)
    assert(foo_dir_record.rock_ridge.tf_record == None)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(foo_dir_record.rock_ridge.ce_record.continuation_entry.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    internal_check_file_contents(iso, "/"+'a'*RR_MAX_FILENAME_LENGTH, "aa\n")

def check_joliet_and_rr_nofiles(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 63488)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 31, 10, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 31, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 28,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 28, True, 2)

def check_joliet_and_rr_onefile(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 65536)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 32, 10, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 32, 10, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 28,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, True, 2)

    internal_check_file(iso.pvd.root_dir_record.children[2], "FOO.;1", 116, 31)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")
    internal_check_file_contents(iso, "/foo", "foo\n")

def check_joliet_and_rr_onedir(iso, filesize):
    # Make sure the filesize is what we expect.
    assert(filesize == 67584)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), the path table should be exactly 10 bytes long (the root
    # directory entry), the little endian path table should start at extent 19
    # (default when there are no volume descriptors beyond the primary and the
    # terminator), and the big endian path table should start at extent 21
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 33, 22, 20, 22)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 33, 26, 24, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 28, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 29, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 28, True, 3)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    # The "dir?" directory should have two children (the "dot", and the
    # "dotdot" entries).
    dirrecord = iso.pvd.root_dir_record.children[2]
    assert(len(dirrecord.children) == 2)
    # The "dir?" directory should be a directory.
    assert(dirrecord.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dirrecord.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dirrecord.file_ident == 'DIR1')
    # The "dir?" directory record should have a length of 38.
    assert(dirrecord.dr_len == 114)
    assert(dirrecord.file_flags == 0x2)
    assert(dirrecord.extent_location() == 29)
    # The "dir?" directory record should have a valid "dot" record.
    dot_record = dirrecord.children[0]
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 102 with Rock Ridge.
    assert(dot_record.dr_len == 102)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 0x2)

    assert(dot_record.rock_ridge.initialized == True)
    assert(dot_record.rock_ridge.su_entry_version == 1)
    assert(dot_record.rock_ridge.rr_record.rr_flags == 0x81)
    assert(dot_record.rock_ridge.px_record.posix_file_mode == 040555)
    assert(dot_record.rock_ridge.px_record.posix_file_links == 2)
    assert(dot_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dot_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dot_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dot_record.rock_ridge.es_record == None)
    assert(dot_record.rock_ridge.nm_record == None)
    assert(dot_record.rock_ridge.pn_record == None)
    assert(dot_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dot_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dot_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dot_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(dot_record.rock_ridge.tf_record.backup_time == None)
    assert(dot_record.rock_ridge.tf_record.expiration_time == None)
    assert(dot_record.rock_ridge.tf_record.effective_time == None)

    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr=True, rr_nlinks=3)

def check_rr_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 57344)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (the metadata), the path table should be exactly 10 bytes long
    # (the root directory entry), the little endian path table should start at
    # extent 20 (default when there is just the PVD and the Eltorito Boot
    # Record), and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 28, 10, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x1a, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 24,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, True, 2)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 27)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_rr_and_eltorito_onefile(iso, filesize):
    assert(filesize == 59392)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (the metadata), the path table should be exactly 10 bytes long
    # (the root directory entry), the little endian path table should start at
    # extent 20 (default when there is just the PVD and the Eltorito Boot
    # Record), and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 29, 10, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x1a, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.  With no directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 24,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, True, 2)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 27)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

    internal_check_file(iso.pvd.root_dir_record.children[4], "FOO.;1", 116, 28)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")

def check_rr_and_eltorito_onedir(iso, filesize):
    assert(filesize == 59392)

    # Do checks on the PVD.  With no files but eltorito, the ISO should be 27
    # extents (the metadata), the path table should be exactly 10 bytes long
    # (the root directory entry), the little endian path table should start at
    # extent 20 (default when there is just the PVD and the Eltorito Boot
    # Record), and the big endian path table should start at extent 22
    # (since the little endian path table record is always rounded up to 2
    # extents).
    internal_check_pvd(iso.pvd, 29, 22, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x1b, 28)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 25, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 4 entries ("dot", "dotdot", the boot file, and the boot
    # catalog), the data length is exactly one extent (2048 bytes), and the
    # root directory should start at extent 24 (2 beyond the big endian path
    # table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 24, True, 3)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 28)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    # The "dir?" directory should have two children (the "dot", and the
    # "dotdot" entries).
    dirrecord = iso.pvd.root_dir_record.children[4]
    assert(len(dirrecord.children) == 2)
    # The "dir?" directory should be a directory.
    assert(dirrecord.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dirrecord.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dirrecord.file_ident == 'DIR1')
    # The "dir?" directory record should have a length of 38.
    assert(dirrecord.dr_len == 114)
    assert(dirrecord.file_flags == 0x2)
    assert(dirrecord.extent_location() == 25)
    # The "dir?" directory record should have a valid "dot" record.
    dot_record = dirrecord.children[0]
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 102 with Rock Ridge.
    assert(dot_record.dr_len == 102)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 0x2)

    assert(dot_record.rock_ridge.initialized == True)
    assert(dot_record.rock_ridge.su_entry_version == 1)
    assert(dot_record.rock_ridge.rr_record.rr_flags == 0x81)
    assert(dot_record.rock_ridge.px_record.posix_file_mode == 040555)
    assert(dot_record.rock_ridge.px_record.posix_file_links == 2)
    assert(dot_record.rock_ridge.px_record.posix_user_id == 0)
    assert(dot_record.rock_ridge.px_record.posix_group_id == 0)
    assert(dot_record.rock_ridge.px_record.posix_serial_number == 0)
    assert(dot_record.rock_ridge.es_record == None)
    assert(dot_record.rock_ridge.nm_record == None)
    assert(dot_record.rock_ridge.pn_record == None)
    assert(dot_record.rock_ridge.tf_record.creation_time == None)
    assert(type(dot_record.rock_ridge.tf_record.access_time) == pyiso.DirectoryRecordDate)
    assert(type(dot_record.rock_ridge.tf_record.modification_time) == pyiso.DirectoryRecordDate)
    assert(type(dot_record.rock_ridge.tf_record.attribute_change_time) == pyiso.DirectoryRecordDate)
    assert(dot_record.rock_ridge.tf_record.backup_time == None)
    assert(dot_record.rock_ridge.tf_record.expiration_time == None)
    assert(dot_record.rock_ridge.tf_record.effective_time == None)

    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr=True, rr_nlinks=3)

def check_joliet_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 67584)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 33, 10, 21, 23)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 33, 10, 25, 27)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x1f, 32)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, False, 0)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 40, 32)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_isohybrid(iso, filesize):
    assert(filesize == 1048576)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 45, 10, 20, 22)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x19, 26)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 18)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 24, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 24, False, 0)

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[2]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

    assert(iso.isohybrid_mbr.geometry_heads == 64)
    assert(iso.isohybrid_mbr.geometry_sectors == 32)

    # Now check out the "isolinux.bin" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[3], "ISOLINUX.BIN;1", 48, 26)

def check_joliet_and_eltorito_onefile(iso, filesize):
    assert(filesize == 69632)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 34, 10, 21, 23)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 34, 10, 25, 27)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x1f, 32)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, False, 0)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 40, 32)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

    internal_check_file(iso.pvd.root_dir_record.children[4], "FOO.;1", 40, 33)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")

def check_joliet_and_eltorito_onedir(iso, filesize):
    assert(filesize == 71680)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 35, 22, 21, 23)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 35, 26, 25, 27)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x21, 34)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 30, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, False, 0)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    # The "dir?" directory should have two children (the "dot", and the
    # "dotdot" entries).
    dirrecord = iso.pvd.root_dir_record.children[4]
    assert(len(dirrecord.children) == 2)
    # The "dir?" directory should be a directory.
    assert(dirrecord.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dirrecord.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dirrecord.file_ident == 'DIR1')
    # The "dir?" directory record should have a length of 38.
    assert(dirrecord.dr_len == 38)
    assert(dirrecord.file_flags == 0x2)
    assert(dirrecord.extent_location() == 30)
    # The "dir?" directory record should have a valid "dot" record.
    dot_record = dirrecord.children[0]
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34.
    assert(dot_record.dr_len == 34)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 0x2)

    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr=False)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 40, 34)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 44)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_joliet_rr_and_eltorito_nofiles(iso, filesize):
    assert(filesize == 69632)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 34, 10, 21, 23)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 34, 10, 25, 27)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x20, 33)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 29, True, 2)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 33)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

def check_joliet_rr_and_eltorito_onefile(iso, filesize):
    assert(filesize == 71680)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 35, 10, 21, 23)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 35, 10, 25, 27)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x20, 33)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, True, 2)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 33)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

    internal_check_file(iso.pvd.root_dir_record.children[4], "FOO.;1", 116, 34)
    internal_check_file_contents(iso, '/FOO.;1', "foo\n")

def check_joliet_rr_and_eltorito_onedir(iso, filesize):
    assert(filesize == 73728)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    internal_check_pvd(iso.pvd, 36, 22, 21, 23)

    # Check to ensure the El Torito information is sane.
    internal_check_eltorito(iso.brs, iso.eltorito_boot_catalog, 0x22, 35)

    # Check that the Joliet stuff is sane.
    internal_check_joliet(iso.svds, 36, 26, 25, 27)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 19)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 29, 1)
    internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 30, 1)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    internal_check_root_dir_record(iso.pvd.root_dir_record, 5, 2048, 29, True, 3)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    # The "dir?" directory should have two children (the "dot", and the
    # "dotdot" entries).
    dirrecord = iso.pvd.root_dir_record.children[4]
    assert(len(dirrecord.children) == 2)
    # The "dir?" directory should be a directory.
    assert(dirrecord.isdir == True)
    # The "dir?" directory should not be the root.
    assert(dirrecord.is_root == False)
    # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
    assert(dirrecord.file_ident == 'DIR1')
    # The "dir?" directory record should have a length of 38.
    assert(dirrecord.dr_len == 114)
    assert(dirrecord.file_flags == 0x2)
    assert(dirrecord.extent_location() == 30)
    # The "dir?" directory record should have a valid "dot" record.
    dot_record = dirrecord.children[0]
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34.
    assert(dot_record.dr_len == 102)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)
    assert(dot_record.file_flags == 0x2)

    # The "dir?" directory record should have a valid "dotdot" record.
    internal_check_dotdot_dir_record(dirrecord.children[1], rr=True, rr_nlinks=3)

    # Now check out the "boot" directory record.
    internal_check_file(iso.pvd.root_dir_record.children[2], "BOOT.;1", 116, 35)
    internal_check_file_contents(iso, "/BOOT.;1", "boot\n")

    # Now check out the "bootcat" directory record.
    bootcatrecord = iso.pvd.root_dir_record.children[3]
    # The file identifier for the "bootcat" directory entry should be "BOOT.CAT;1".
    assert(bootcatrecord.file_ident == "BOOT.CAT;1")
    # The "bootcat" directory entry should not be a directory.
    assert(bootcatrecord.isdir == False)
    # The "bootcat" directory record length should be exactly 44.
    assert(bootcatrecord.dr_len == 124)
    # The "bootcat" directory record is not the root.
    assert(bootcatrecord.is_root == False)
    # The "bootcat" directory record should have no children.
    assert(len(bootcatrecord.children) == 0)
    assert(bootcatrecord.file_flags == 0)

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
    internal_check_pvd(iso.pvd, 34, 122, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.  With no files or directories, there
    # should be exactly one entry (the root entry), it should have an identifier
    # of the byte 0, it should have a len of 1, it should start at extent 23,
    # and its parent directory number should be 1.
    assert(len(iso.pvd.path_table_records) == 10)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)
    #internal_check_ptr(iso.pvd.path_table_records[1], 'DIR1', 4, 26, 1)
    #internal_check_ptr(iso.pvd.path_table_records[2], 'DIR2', 4, 27, 2)
    #internal_check_ptr(iso.pvd.path_table_records[3], 'DIR3', 4, 28, 4)
    #internal_check_ptr(iso.pvd.path_table_records[4], 'DIR4', 4, 29, 6)
    #internal_check_ptr(iso.pvd.path_table_records[5], 'DIR5', 4, 30, 7)
    #internal_check_ptr(iso.pvd.path_table_records[6], 'DIR6', 4, 31, 8)
    #internal_check_ptr(iso.pvd.path_table_records[7], 'DIR7', 4, 32, 9)
    #internal_check_ptr(iso.pvd.path_table_records[8], 'DIR8', 4, 25, 3)
    #internal_check_ptr(iso.pvd.path_table_records[9], 'RR_MOVED', 8, 24, 1)

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
    internal_check_pvd(iso.pvd, 35, 122, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 10)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 4)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/foo", "foo\n")

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
    internal_check_pvd(iso.pvd, 36, 134, 19, 21)

    # Check to make sure the volume descriptor terminator is sane.
    internal_check_terminator(iso.vdsts, 17)

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 11)
    internal_check_ptr(iso.pvd.path_table_records[0], '\x00', 1, 23, 1)

    # Now check the root directory record.  With no files, the root directory
    # record should have 2 entries ("dot" and "dotdot"), the data length is
    # exactly one extent (2048 bytes), and the root directory should start at
    # extent 23 (2 beyond the big endian path table record entry).
    internal_check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23, True, 4)

    internal_check_file_contents(iso, "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/dir9/foo", "foo\n")
