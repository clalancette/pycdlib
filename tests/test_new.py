import pytest
import subprocess
import os
import sys
import StringIO

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

from common import *

def test_new_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Do checks on the PVD.  With no files, the ISO should be 24 extents.
    # The path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 24, 10, 21)

    # Now check the root directory record.  With no files, the root directory
    # record should have "dot" and "dotdot" as children.
    check_root_dir_record(iso.pvd.root_dir_record, 2, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO", StringIO.StringIO())

def test_new_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    # Do checks on the PVD.  With one directory, the ISO should be 25 extents
    # (24 extents for the metadata, and 1 extent for the directory record).  The
    # path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 25, 22, 21)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

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
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

    # Test adding a directory with an intermediate directory missing.
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/FOO/BAR")

def test_new_onefile():
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO")

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 25, 10, 21)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

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
    check_file_contents(iso, "/FOO", "foo\n")

def test_new_toodeepdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/DIR2")
    iso.add_directory("/DIR1/DIR2/DIR3")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8")

def test_new_manydirs():
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 328, 4122, 23)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 297, 12288, 27)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append("DIR%d" % i)
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    for index in range(2, 2+numdirs):
        # The "dir?" directory should have two children (the "dot", and the
        # "dotdot" entries).
        assert(len(iso.pvd.root_dir_record.children[index].children) == 2)
        # The "dir?" directory should be a directory.
        assert(iso.pvd.root_dir_record.children[index].isdir == True)
        # The "dir?" directory should not be the root.
        assert(iso.pvd.root_dir_record.children[index].is_root == False)
        # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
        assert(iso.pvd.root_dir_record.children[index].file_ident == names[index])
        # The "dir?" directory record should have a length of 38.
        assert(iso.pvd.root_dir_record.children[index].dr_len == (33 + len(names[index]) + (1 - (len(names[index]) % 2))))
        # The "dir?" directory record should have a valid "dot" record.
        check_dot_dir_record(iso.pvd.root_dir_record.children[index].children[0])
        # The "dir?" directory record should have a valid "dotdot" record.
        check_dotdot_dir_record(iso.pvd.root_dir_record.children[index].children[1])
