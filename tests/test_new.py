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

    out = StringIO.StringIO()
    iso.write(out)

    check_nofile(iso, len(out.getvalue()))

def test_new_onefile():
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onedir(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_twofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_twofile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    # Add new directory.
    iso.add_directory("/DIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefileonedir(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_onefile_onedirwithfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    # Add new directory.
    iso.add_directory("/DIR1")
    # Add new sub-file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile_onedirwithfile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_tendirs():
    numdirs = 10

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    out = StringIO.StringIO()
    iso.write(out)

    check_tendirs(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_dirs_overflow_ptr_extent():
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    out = StringIO.StringIO()
    iso.write(out)

    check_dirs_overflow_ptr_extent(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_dirs_just_short_ptr_extent():
    numdirs = 293

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)
    # Now add two more to push it over the boundary
    iso.add_directory("/DIR294")
    iso.add_directory("/DIR295")

    # Now remove them to put it back down below the boundary.
    iso.rm_directory("/DIR295")
    iso.rm_directory("/DIR294")

    out = StringIO.StringIO()
    iso.write(out)

    check_dirs_just_short_ptr_extent(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_twoextentfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)

    iso.add_fp(StringIO.StringIO(outstr), len(outstr), "/BIGFILE.;1")

    check_twoextentfile(iso, outstr)

    # Now make sure we can re-open the written ISO.
    out = StringIO.StringIO()
    iso.write(out)
    pyiso.PyIso().open(out)

def test_new_twoleveldeepdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_twoleveldeepdir(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_twoleveldeepfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/DIR1/SUBDIR1/FOO.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_twoleveldeepfile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_dirs_overflow_ptr_extent_reverse():
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in reversed(range(1, 1+numdirs)):
        iso.add_directory("/DIR%d" % i)

    out = StringIO.StringIO()
    iso.write(out)

    check_dirs_overflow_ptr_extent(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

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

    # Now make sure we can re-open the written ISO.
    out = StringIO.StringIO()
    iso.write(out)
    pyiso.PyIso().open(out)

def test_new_removefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add second new file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    # Remove the second file.
    iso.rm_file("/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_removedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add new directory.
    iso.add_directory("/DIR1")

    # Remove the directory
    iso.rm_directory("/DIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

def test_new_eltorito():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_eltorito_nofile(iso, len(out.getvalue()))

def test_new_remove_eltorito():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.remove_eltorito()
    iso.rm_file("/BOOT.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_nofile(iso, len(out.getvalue()))

def test_new_rr_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_nofile(iso, len(out.getvalue()))

def test_new_rr_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO.;1", "/foo")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefile(iso, len(out.getvalue()))

def test_new_rr_twofile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    # Add a new file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1", "/bar")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_twofile(iso, len(out.getvalue()))

def test_new_rr_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    # Add new directory.
    iso.add_directory("/DIR1", "/dir1")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefileonedir(iso, len(out.getvalue()))

def test_new_rr_onefileonedirwithfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    # Add new directory.
    iso.add_directory("/DIR1", "/dir1")

    # Add a new file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1", "/dir1/bar")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefileonedirwithfile(iso, len(out.getvalue()))

def test_new_rr_symlink():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    iso.add_symlink("/SYM.;1", "sym", "/foo")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_symlink(iso, len(out.getvalue()))

def test_new_rr_symlink2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add new directory.
    iso.add_directory("/DIR1", "/dir1")

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/DIR1/FOO.;1", "/dir1/foo")

    iso.add_symlink("/SYM.;1", "sym", "/dir1/foo")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_symlink2(iso, len(out.getvalue()))

def test_new_rr_symlink_dot():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "/.")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_symlink_dot(iso, len(out.getvalue()))

def test_new_rr_symlink_broken():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "/foo")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_symlink_broken(iso, len(out.getvalue()))

def test_new_alternating_subdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    ddstr = "dd\n"
    iso.add_fp(StringIO.StringIO(ddstr), len(ddstr), "/DD.;1")

    bbstr = "bb\n"
    iso.add_fp(StringIO.StringIO(bbstr), len(bbstr), "/BB.;1")

    iso.add_directory("/CC")

    iso.add_directory("/AA")

    subdirfile1 = "sub1\n"
    iso.add_fp(StringIO.StringIO(subdirfile1), len(subdirfile1), "/AA/SUB1.;1")

    subdirfile2 = "sub2\n"
    iso.add_fp(StringIO.StringIO(subdirfile2), len(subdirfile2), "/CC/SUB2.;1")

    f = open('/home/clalancette/upstream/pyiso/debug.iso', 'w')
    iso.write(f)
    f.close()

    out = StringIO.StringIO()
    iso.write(out)

    check_alternating_subdir(iso, len(out.getvalue()))

# FIXME: add a test to write a file out, then write it out again and make sure
# everything still works.
