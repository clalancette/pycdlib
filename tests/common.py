import StringIO
import pytest
import os
import sys

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

def check_pvd(pvd, size, path_table_size, path_table_location_be):
    # The primary volume descriptor should always have a type of 1.
    assert(pvd.descriptor_type == 1)
    # The primary volume descriptor should always have an identifier of "CD001".
    assert(pvd.identifier == "CD001")
    # The primary volume descriptor should always have a version of 1.
    assert(pvd.version == 1)
    # The primary volume descriptor should always have a file structure version
    # of 1.
    assert(pvd.file_structure_version == 1)
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(pvd.log_block_size == 2048)
    # The little endian version of the path table should always start at
    # extent 19.
    assert(pvd.path_table_location_le == 19)
    # The length of the system identifer should always be 32.
    assert(len(pvd.system_identifier) == 32)
    # The length of the volume identifer should always be 32.
    assert(len(pvd.volume_identifier) == 32)
    # The length of the volume set identifer should always be 128.
    assert(len(pvd.volume_set_identifier) == 128)
    # The length of the copyright file identifer should always be 37.
    assert(len(pvd.copyright_file_identifier) == 37)
    # The length of the abstract file identifer should always be 37.
    assert(len(pvd.abstract_file_identifier) == 37)
    # The length of the bibliographic file identifer should always be 37.
    assert(len(pvd.bibliographic_file_identifier) == 37)
    # The length of the application use string should always be 512.
    assert(len(pvd.application_use) == 512)
    # The big endian version of the path table changes depending on how many
    # directories there are on the ISO.
    assert(pvd.path_table_location_be == path_table_location_be)
    # genisoimage only supports setting the sequence number to 1
    assert(pvd.seqnum == 1)
    # The amount of space the ISO takes depends on the files and directories
    # on the ISO.
    assert(pvd.space_size == size)
    # The path table size depends on how many directories there are on the ISO.
    assert(pvd.path_tbl_size == path_table_size)

def check_terminator(terminators):
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

def check_root_dir_record(root_dir_record, num_children, data_length,
                          extent_location):
    # The root_dir_record directory record length should be exactly 34.
    assert(root_dir_record.dr_len == 34)
    # The root directory should be the, erm, root.
    assert(root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(root_dir_record.file_ident == "\x00")
    # The length of the root directory record depends on the number of entries
    # there are at the top level.
    assert(root_dir_record.data_length == data_length)
    # The number of children the root directory record has depends on the number
    # of files+directories there are at the top level.
    assert(len(root_dir_record.children) == num_children)
    # Make sure the root directory record starts at the extent we expect.
    assert(root_dir_record.extent_location() == extent_location)

def check_dot_dir_record(dot_record):
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

def check_dotdot_dir_record(dotdot_record):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == "\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34.
    assert(dotdot_record.dr_len == 34)
    # The "dotdot" directory record is not the root.
    assert(dotdot_record.is_root == False)
    # The "dotdot" directory record should have no children.
    assert(len(dotdot_record.children) == 0)

def check_file_contents(iso, path, contents):
    fout = StringIO.StringIO()
    iso.get_and_write(path, fout)
    assert(fout.getvalue() == contents)

def check_nofile(iso, filesize):
    assert(filesize == 49152)

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), and the path table should be exactly 10 bytes (the root
    # directory entry).
    check_pvd(iso.pvd, 24, 10, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With no files, the root directory
    # record should have "dot" and "dotdot" as children.
    check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO.;1", StringIO.StringIO())

def check_onefile(iso, filesize):
    assert(filesize == 51200)

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 25, 10, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 40)
    # The "foo" data should start at extent 24.
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO.;1", "foo\n")

    out = StringIO.StringIO()
    # Make sure trying to get a non-existent file raises an exception
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/BAR.;1", out)

def check_onedir(iso, filesize):
    assert(filesize == 51200)

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be exactly 22 bytes (for the root directory entry and
    # the directory).
    check_pvd(iso.pvd, 25, 22, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one directory at the root, the
    # root directory record should have "dot", "dotdot", and the directory as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)
    assert(iso.pvd.path_table_records[1].directory_identifier == 'DIR1')
    assert(iso.pvd.path_table_records[1].len_di == 4)
    assert(iso.pvd.path_table_records[1].extent_location == 24)
    assert(iso.pvd.path_table_records[1].parent_directory_num == 1)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    assert(len(iso.pvd.root_dir_record.children[2].children) == 2)
    # The "dir1" directory should be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == True)
    # The "dir1" directory should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "DIR1")
    # The "dir1" directory record should have a length of 38.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 38)
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

def check_twofile(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With two files, the ISO should be 26 extents (24
    # extents for the metadata, and 1 extent for each of the two short files).
    # The path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 26, 10, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With two files at the root, the
    # root directory record should have "dot", "dotdot", and the two files as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO.;1", "foo\n")

    # The "bar" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "bar" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "bar" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "bar" file should have an ISO9660 mangled name of "BAR.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "BAR.;1")
    # The "bar" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 40)
    # The "bar" data should start at extent 24.
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # Make sure getting the data from the bar file works, and returns the right
    # thing.
    check_file_contents(iso, "/BAR.;1", "bar\n")

def check_onefileonedir(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one file and one directory, the ISO should be
    # 26 extents (24 extents for the metadata, 1 extent for the file, and 1
    # extent for the extra directory).  The path table should be 22 bytes (10
    # bytes for the root directory entry, and 12 bytes for the "dir1" entry).
    check_pvd(iso.pvd, 26, 22, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the one
    # file, and the one directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)
    assert(iso.pvd.path_table_records[1].directory_identifier == 'DIR1')
    assert(iso.pvd.path_table_records[1].len_di == 4)
    assert(iso.pvd.path_table_records[1].extent_location == 24)
    assert(iso.pvd.path_table_records[1].parent_directory_num == 1)

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    assert(len(iso.pvd.root_dir_record.children[2].children) == 2)
    # The "dir1" directory should be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == True)
    # The "dir1" directory should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "DIR1")
    # The "dir1" directory record should have a length of 38.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 38)
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO.;1", "foo\n")

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
    check_pvd(iso.pvd, 27, 22, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the file,
    # and the directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 2)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)
    assert(iso.pvd.path_table_records[1].directory_identifier == 'DIR1')
    assert(iso.pvd.path_table_records[1].len_di == 4)
    assert(iso.pvd.path_table_records[1].extent_location == 24)
    assert(iso.pvd.path_table_records[1].parent_directory_num == 1)

    # The "dir1" directory should have three children (the "dot", the "dotdot"
    # and the "bar" entries).
    assert(len(iso.pvd.root_dir_record.children[2].children) == 3)
    # The "dir1" directory should be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == True)
    # The "dir1" directory should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "DIR1")
    # The "dir1" directory record should have a length of 38.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 38)
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO.;1", "foo\n")

    # The "bar" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children[2].children) == 0)
    # The "bar" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].children[2].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].children[2].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "BAR.;1".
    assert(iso.pvd.root_dir_record.children[2].children[2].file_ident == "BAR.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].children[2].dr_len == 40)
    # The "bar" data should start at extent 26.
    assert(iso.pvd.root_dir_record.children[2].children[2].extent_location() == 26)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/DIR1/BAR.;1", "bar\n")

def generate_inorder_names(numdirs):
    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append("DIR%d" % i)
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    return names

def check_directory(dirrecord, name):
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
    # The "dir?" directory record should have a valid "dot" record.
    check_dot_dir_record(dirrecord.children[0])
    # The "dir?" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(dirrecord.children[1])

def check_twoextentfile(iso, outstr):
    # Do checks on the PVD.  With one big file, the ISO should be 26 extents
    # (24 extents for the metadata, and 2 extents for the file).
    # The path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 26, 10, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    # The "bigfile" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "bigfile" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "bigfile" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "bigfile" file should have an ISO9660 mangled name of "BIGFILE.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "BIGFILE.;1")
    # The "bigfile" directory record should have a length of 44.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 44)
    # The "bigfile" data should start at extent 24.
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # Make sure getting the data from the bigfile file works, and returns the right
    # thing.
    check_file_contents(iso, "/BIGFILE.;1", outstr)

def check_twoleveldeepdir(iso, filesize):
    assert(filesize == 53248)

    # Do checks on the PVD.  With one big file, the ISO should be 26 extents
    # (24 extents for the metadata, and 1 extent for the dir1 entry, and 1
    # extent for the subdir1 entry).
    # The path table should be 38 bytes (for the root directory entry, and the
    # dir1 entry, and the subdir1 entry).
    check_pvd(iso.pvd, 26, 38, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With one dir at the root, the
    # root directory record should have "dot", "dotdot", and the dir as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 3)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)
    assert(iso.pvd.path_table_records[1].directory_identifier == 'DIR1')
    assert(iso.pvd.path_table_records[1].len_di == 4)
    assert(iso.pvd.path_table_records[1].extent_location == 24)
    assert(iso.pvd.path_table_records[1].parent_directory_num == 1)
    assert(iso.pvd.path_table_records[2].directory_identifier == 'SUBDIR1')
    assert(iso.pvd.path_table_records[2].len_di == 7)
    assert(iso.pvd.path_table_records[2].extent_location == 25)
    # FIXME: new has a bug here.
    #assert(iso.pvd.path_table_records[2].parent_directory_num == 2)

    # FIXME: we should check out the directory records here.

def check_tendirs(iso, filesize):
    assert(filesize == 69632)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 34, 132, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 12, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Now check out the path table records.
    assert(len(iso.pvd.path_table_records) == 10+1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    names = generate_inorder_names(10)
    for index in range(2, 2+10):
        assert(iso.pvd.path_table_records[index-1].directory_identifier == names[index])
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        assert(iso.pvd.path_table_records[index-1].len_di == len(names[index]))
        assert(iso.pvd.path_table_records[index-1].parent_directory_num == 1)

        check_directory(iso.pvd.root_dir_record.children[index], names[index])

def check_dirs_overflow_ptr_extent(iso, filesize):
    assert(filesize == 671744)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 328, 4122, 23)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 297, 12288, 27)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    assert(len(iso.pvd.path_table_records) == 295+1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    # FIXME: new has a bug here.
    #assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    names = generate_inorder_names(295)
    for index in range(2, 2+295):
        assert(iso.pvd.path_table_records[index-1].directory_identifier == names[index])
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        assert(iso.pvd.path_table_records[index-1].len_di == len(names[index]))
        assert(iso.pvd.path_table_records[index-1].parent_directory_num == 1)

        check_directory(iso.pvd.root_dir_record.children[index], names[index])

def check_dirs_just_short_ptr_extent(iso, filesize):
    assert(filesize == 659456)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 322, 4094, 21)

    check_terminator(iso.vdsts)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 295, 12288, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    assert(len(iso.pvd.path_table_records) == 293+1)
    assert(iso.pvd.path_table_records[0].directory_identifier == '\x00')
    assert(iso.pvd.path_table_records[0].len_di == 1)
    assert(iso.pvd.path_table_records[0].extent_location == 23)
    assert(iso.pvd.path_table_records[0].parent_directory_num == 1)

    names = generate_inorder_names(293)
    for index in range(2, 2+293):
        assert(iso.pvd.path_table_records[index-1].directory_identifier == names[index])
        # Note that we skip checking the path table record extent location
        # because I don't understand the algorithm by which genisoimage assigns
        # extents.
        assert(iso.pvd.path_table_records[index-1].len_di == len(names[index]))
        assert(iso.pvd.path_table_records[index-1].parent_directory_num == 1)

        check_directory(iso.pvd.root_dir_record.children[index], names[index])
