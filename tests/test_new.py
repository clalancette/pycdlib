import pytest
import subprocess
import os
import sys
import StringIO
import struct

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

    check_nofile(iso)

def test_new_onefile():
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO")

    check_onefile(iso)

def test_new_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    check_onedir(iso)

def test_new_twofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO")
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR")

    check_twofile(iso)

def test_new_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO")
    # Add new directory.
    iso.add_directory("/DIR1")

    check_onefileonedir(iso)

def test_new_onefile_onedirwithfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO")
    # Add new directory.
    iso.add_directory("/DIR1")
    # Add new sub-file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR")

    check_onefile_onedirwithfile(iso)

def test_new_tendirs():
    numdirs = 10

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

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

    names = generate_inorder_names(numdirs)
    for index in range(2, 2+numdirs):
        check_directory(iso.pvd.root_dir_record.children[index], names[index])

def test_parse_twoextentfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)

    iso.add_fp(StringIO.StringIO(outstr), len(outstr), "/BIGFILE")

    check_twoextentfile(iso, outstr)

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

def test_new_removefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO")

    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR")

    iso.rm_file("/BAR")

    check_onefile(iso)
