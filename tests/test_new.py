import pytest
import subprocess
import os
import sys
import StringIO
import struct

prefix = 'src/pyiso'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

from common import *

def do_a_test(iso, check_func):
    out = StringIO.StringIO()
    iso.write(out)

    check_func(iso, len(out.getvalue()))

    # Now make sure we can re-open the written ISO.
    pyiso.PyIso().open(out)

    iso2 = pyiso.PyIso()
    iso2.open(out)
    check_func(iso2, len(out.getvalue()))
    iso2.close()

def test_new_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    do_a_test(iso, check_nofiles)

def test_new_onefile():
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO.;1")

    do_a_test(iso, check_onefile)

def test_new_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    do_a_test(iso, check_onedir)

def test_new_twofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    do_a_test(iso, check_twofiles)

def test_new_twofiles2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_twofiles)

def test_new_twodirs():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directories.
    iso.add_directory("/AA")
    iso.add_directory("/BB")

    do_a_test(iso, check_twodirs)

def test_new_twodirs2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directories.
    iso.add_directory("/BB")
    iso.add_directory("/AA")

    do_a_test(iso, check_twodirs)

def test_new_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    # Add new directory.
    iso.add_directory("/DIR1")

    do_a_test(iso, check_onefileonedir)

def test_new_onefileonedir2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new directory.
    iso.add_directory("/DIR1")
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_onefileonedir)

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

    do_a_test(iso, check_onefile_onedirwithfile)

def test_new_tendirs():
    numdirs = 10

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_tendirs)

def test_new_dirs_overflow_ptr_extent():
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

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

    do_a_test(iso, check_dirs_just_short_ptr_extent)

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

    do_a_test(iso, check_twoextentfile)

def test_new_twoleveldeepdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")

    do_a_test(iso, check_twoleveldeepdir)

def test_new_twoleveldeepfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/DIR1/SUBDIR1/FOO.;1")

    do_a_test(iso, check_twoleveldeepfile)

def test_new_dirs_overflow_ptr_extent_reverse():
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in reversed(range(1, 1+numdirs)):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

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

def test_new_toodeepfile():
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
    foostr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/FOO.;1")

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

    do_a_test(iso, check_onefile)

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

    do_a_test(iso, check_onefile)

def test_new_eltorito():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_eltorito_nofiles)

def test_new_rm_eltorito():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.rm_eltorito()
    iso.rm_file("/BOOT.;1")

    do_a_test(iso, check_nofiles)

def test_new_eltorito_twofile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    aastr = "aa\n"
    iso.add_fp(StringIO.StringIO(aastr), len(aastr), "/AA.;1")

    do_a_test(iso, check_eltorito_twofile)

def test_new_rr_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    do_a_test(iso, check_rr_nofiles)

def test_new_rr_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(StringIO.StringIO(mystr), len(mystr), "/FOO.;1", "/foo")

    do_a_test(iso, check_rr_onefile)

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

    do_a_test(iso, check_rr_twofile)

def test_new_rr_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    # Add new directory.
    iso.add_directory("/DIR1", rr_path="/dir1")

    do_a_test(iso, check_rr_onefileonedir)

def test_new_rr_onefileonedirwithfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    # Add new directory.
    iso.add_directory("/DIR1", rr_path="/dir1")

    # Add a new file.
    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1", "/dir1/bar")

    do_a_test(iso, check_rr_onefileonedirwithfile)

def test_new_rr_symlink():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    iso.add_symlink("/SYM.;1", "sym", "foo")

    do_a_test(iso, check_rr_symlink)

def test_new_rr_symlink2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add new directory.
    iso.add_directory("/DIR1", rr_path="/dir1")

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/DIR1/FOO.;1", "/dir1/foo")

    iso.add_symlink("/SYM.;1", "sym", "dir1/foo")

    do_a_test(iso, check_rr_symlink2)

def test_new_rr_symlink_dot():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", ".")

    do_a_test(iso, check_rr_symlink_dot)

def test_new_rr_symlink_dotdot():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "..")

    do_a_test(iso, check_rr_symlink_dotdot)

def test_new_rr_symlink_broken():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "foo")

    do_a_test(iso, check_rr_symlink_broken)

def test_new_rr_verylongname():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(StringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_path="/"+"a"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongname)

def test_new_rr_manylongname():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(StringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_path="/"+"a"*RR_MAX_FILENAME_LENGTH)

    bbstr = "bb\n"
    iso.add_fp(StringIO.StringIO(bbstr), len(bbstr), "/BBBBBBBB.;1", rr_path="/"+"b"*RR_MAX_FILENAME_LENGTH)

    ccstr = "cc\n"
    iso.add_fp(StringIO.StringIO(ccstr), len(ccstr), "/CCCCCCCC.;1", rr_path="/"+"c"*RR_MAX_FILENAME_LENGTH)

    ddstr = "dd\n"
    iso.add_fp(StringIO.StringIO(ddstr), len(ddstr), "/DDDDDDDD.;1", rr_path="/"+"d"*RR_MAX_FILENAME_LENGTH)

    eestr = "ee\n"
    iso.add_fp(StringIO.StringIO(eestr), len(eestr), "/EEEEEEEE.;1", rr_path="/"+"e"*RR_MAX_FILENAME_LENGTH)

    ffstr = "ff\n"
    iso.add_fp(StringIO.StringIO(ffstr), len(ffstr), "/FFFFFFFF.;1", rr_path="/"+"f"*RR_MAX_FILENAME_LENGTH)

    ggstr = "gg\n"
    iso.add_fp(StringIO.StringIO(ggstr), len(ggstr), "/GGGGGGGG.;1", rr_path="/"+"g"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname)

def test_new_rr_manylongname2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(StringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_path="/"+"a"*RR_MAX_FILENAME_LENGTH)

    bbstr = "bb\n"
    iso.add_fp(StringIO.StringIO(bbstr), len(bbstr), "/BBBBBBBB.;1", rr_path="/"+"b"*RR_MAX_FILENAME_LENGTH)

    ccstr = "cc\n"
    iso.add_fp(StringIO.StringIO(ccstr), len(ccstr), "/CCCCCCCC.;1", rr_path="/"+"c"*RR_MAX_FILENAME_LENGTH)

    ddstr = "dd\n"
    iso.add_fp(StringIO.StringIO(ddstr), len(ddstr), "/DDDDDDDD.;1", rr_path="/"+"d"*RR_MAX_FILENAME_LENGTH)

    eestr = "ee\n"
    iso.add_fp(StringIO.StringIO(eestr), len(eestr), "/EEEEEEEE.;1", rr_path="/"+"e"*RR_MAX_FILENAME_LENGTH)

    ffstr = "ff\n"
    iso.add_fp(StringIO.StringIO(ffstr), len(ffstr), "/FFFFFFFF.;1", rr_path="/"+"f"*RR_MAX_FILENAME_LENGTH)

    ggstr = "gg\n"
    iso.add_fp(StringIO.StringIO(ggstr), len(ggstr), "/GGGGGGGG.;1", rr_path="/"+"g"*RR_MAX_FILENAME_LENGTH)

    hhstr = "hh\n"
    iso.add_fp(StringIO.StringIO(hhstr), len(hhstr), "/HHHHHHHH.;1", rr_path="/"+"h"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname2)

def test_new_rr_verylongnameandsymlink():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(StringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_path="/"+"a"*RR_MAX_FILENAME_LENGTH)

    iso.add_symlink("/BBBBBBBB.;1", "b"*RR_MAX_FILENAME_LENGTH, "a"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongnameandsymlink)

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

    do_a_test(iso, check_alternating_subdir)

def test_new_joliet_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    do_a_test(iso, check_joliet_nofiles)

def test_new_joliet_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_onedir)

def test_new_joliet_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_joliet_onefile)

def test_new_joliet_onefileonedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_onefileonedir)

def test_new_joliet_and_rr_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    do_a_test(iso, check_joliet_and_rr_nofiles)

def test_new_joliet_and_rr_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

    do_a_test(iso, check_joliet_and_rr_onefile)

def test_new_joliet_and_rr_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    # Add a directory.
    iso.add_directory("/DIR1", rr_path="/dir1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_and_rr_onedir)

def test_new_rr_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_rr_and_eltorito_nofiles)

def test_new_rr_and_eltorito_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo")

    do_a_test(iso, check_rr_and_eltorito_onefile)

def test_new_rr_and_eltorito_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", rr_path="/dir1")

    do_a_test(iso, check_rr_and_eltorito_onedir)

def test_new_rr_and_eltorito_onedir2():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_path="/dir1")

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_rr_and_eltorito_onedir)

def test_new_joliet_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_joliet_and_eltorito_nofiles)

def test_new_joliet_and_eltorito_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_joliet_and_eltorito_onefile)

def test_new_joliet_and_eltorito_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_and_eltorito_onedir)

def test_new_isohybrid():
    # Create a new ISO
    iso = pyiso.PyIso()
    iso.new()
    # Add Eltorito
    isolinux_fp = open('/usr/share/syslinux/isolinux.bin', 'rb')
    iso.add_fp(isolinux_fp, os.fstat(isolinux_fp.fileno()).st_size, "/ISOLINUX.BIN;1")
    iso.add_eltorito("/ISOLINUX.BIN;1", "/BOOT.CAT;1", boot_load_size=4)
    # Now add the syslinux
    isohybrid_fp = open('/usr/share/syslinux/isohdpfx.bin', 'rb')
    iso.add_isohybrid(isohybrid_fp)

    do_a_test(iso, check_isohybrid)

    isohybrid_fp.close()
    isolinux_fp.close()

def test_new_joliet_rr_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_joliet_rr_and_eltorito_nofiles)

def test_new_joliet_rr_and_eltorito_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

    do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

def test_new_joliet_rr_and_eltorito_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", rr_path="/dir1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

def test_new_rr_rmfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo")

    iso.rm_file("/FOO.;1", rr_path="/foo")

    do_a_test(iso, check_rr_nofiles)

def test_new_rr_rmdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_path="/dir1")

    iso.rm_directory("/DIR1", rr_path="/dir1")

    do_a_test(iso, check_rr_nofiles)

def test_new_joliet_rmfile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

    iso.rm_file("/BOOT.;1", joliet_path="/boot")

    do_a_test(iso, check_joliet_nofiles)

def test_new_joliet_rmdir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    iso.rm_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_nofiles)

def test_new_rr_deep():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory('/DIR1', '/dir1')
    iso.add_directory('/DIR1/DIR2', '/dir1/dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', '/dir1/dir2/dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', '/dir1/dir2/dir3/dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', '/dir1/dir2/dir3/dir4/dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', '/dir1/dir2/dir3/dir4/dir5/dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', '/dir1/dir2/dir3/dir4/dir5/dir6/dir7')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', '/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8')

    do_a_test(iso, check_rr_deep_dir)

def test_new_xa_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    do_a_test(iso, check_xa_nofiles)

def test_new_xa_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_xa_onefile)

def test_new_xa_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    iso.add_directory("/DIR1")

    do_a_test(iso, check_xa_onedir)

def test_new_sevendeepdirs():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_path="/dir1")
    iso.add_directory("/DIR1/DIR2", rr_path="/dir1/dir2")
    iso.add_directory("/DIR1/DIR2/DIR3", rr_path="/dir1/dir2/dir3")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4", rr_path="/dir1/dir2/dir3/dir4")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5", rr_path="/dir1/dir2/dir3/dir4/dir5")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7")

    do_a_test(iso, check_sevendeepdirs)

def test_new_xa_joliet_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    do_a_test(iso, check_xa_joliet_nofiles)

def test_new_xa_joliet_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_xa_joliet_onefile)

def test_new_xa_joliet_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_xa_joliet_onedir)

def test_new_isolevel4_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    do_a_test(iso, check_isolevel4_nofiles)

def test_new_isolevel4_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/foo")

    do_a_test(iso, check_isolevel4_onefile)

def test_new_isolevel4_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    iso.add_directory("/dir1")

    do_a_test(iso, check_isolevel4_onedir)

def test_new_isolevel4_eltorito():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat")

    do_a_test(iso, check_isolevel4_eltorito)

def test_new_everything():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4, rock_ridge=True, joliet=True, xa=True)

    iso.add_directory("/dir1", rr_path="/dir1", joliet_path="/dir1")
    iso.add_directory("/dir1/dir2", rr_path="/dir1/dir2", joliet_path="/dir1/dir2")
    iso.add_directory("/dir1/dir2/dir3", rr_path="/dir1/dir2/dir3", joliet_path="/dir1/dir2/dir3")
    iso.add_directory("/dir1/dir2/dir3/dir4", rr_path="/dir1/dir2/dir3/dir4", joliet_path="/dir1/dir2/dir3/dir4")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5", rr_path="/dir1/dir2/dir3/dir4/dir5", joliet_path="/dir1/dir2/dir3/dir4/dir5")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6", joliet_path = "/dir1/dir2/dir3/dir4/dir5/dir6")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6/dir7", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8")

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/boot", rr_path="/boot", joliet_path="/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/foo", rr_path="/foo", joliet_path="/foo")

    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar")

    iso.add_symlink("/sym", "sym", "foo", joliet_path="/sym")

    iso.add_hard_link("/dir1/foo", "/foo", rr_path="/foo", joliet_path="/dir1/foo")

    do_a_test(iso, check_everything)

def test_new_rr_xa_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    do_a_test(iso, check_rr_xa_nofiles)

def test_new_rr_xa_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo")

    do_a_test(iso, check_rr_xa_onefile)

def test_new_rr_xa_onedir():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    iso.add_directory("/DIR1", rr_path="/dir1")

    do_a_test(iso, check_rr_xa_onedir)

def test_new_rr_joliet_symlink():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

    iso.add_symlink("/SYM.;1", "sym", "foo", joliet_path="/sym")

    do_a_test(iso, check_rr_joliet_symlink)

def test_new_rr_joliet_deep():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    iso.add_directory("/DIR1", rr_path="/dir1", joliet_path="/dir1")
    iso.add_directory("/DIR1/DIR2", rr_path="/dir1/dir2", joliet_path="/dir1/dir2")
    iso.add_directory("/DIR1/DIR2/DIR3", rr_path="/dir1/dir2/dir3", joliet_path="/dir1/dir2/dir3")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4", rr_path="/dir1/dir2/dir3/dir4", joliet_path="/dir1/dir2/dir3/dir4")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5", rr_path="/dir1/dir2/dir3/dir4/dir5", joliet_path="/dir1/dir2/dir3/dir4/dir5")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6", joliet_path = "/dir1/dir2/dir3/dir4/dir5/dir6")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8", rr_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8")

    do_a_test(iso, check_rr_joliet_deep)

def test_new_duplicate_child():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    iso.add_directory("/DIR1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/DIR1")

def test_new_eltorito_multi_boot():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat")

    boot2str = "boot2\n"
    iso.add_fp(StringIO.StringIO(boot2str), len(boot2str), "/boot2")
    iso.add_eltorito("/boot2", "/boot.cat")

    do_a_test(iso, check_eltorito_multi_boot)

def test_new_eltorito_boot_table():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table)

def test_new_hardlink():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add a directory.
    iso.add_directory("/DIR1")

    iso.add_hard_link("/DIR1/FOO.;1", "/FOO.;1")

    do_a_test(iso, check_hard_link)
