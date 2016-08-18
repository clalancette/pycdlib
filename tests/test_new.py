import pytest
import os
import sys
import cStringIO
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
    out = cStringIO.StringIO()
    iso.write_fp(out)

    check_func(iso, len(out.getvalue()))

    iso2 = pyiso.PyIso()
    iso2.open_fp(out)
    check_func(iso2, len(out.getvalue()))
    iso2.close()

def test_new_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_onefile(tmpdir):
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1")

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    do_a_test(iso, check_onedir)

    iso.close()

def test_new_twofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    do_a_test(iso, check_twofiles)

    iso.close()

def test_new_twofiles2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new files.
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/BAR.;1")
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_twofiles)

    iso.close()

def test_new_twodirs(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directories.
    iso.add_directory("/AA")
    iso.add_directory("/BB")

    do_a_test(iso, check_twodirs)

    iso.close()

def test_new_twodirs2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directories.
    iso.add_directory("/BB")
    iso.add_directory("/AA")

    do_a_test(iso, check_twodirs)

    iso.close()

def test_new_onefileonedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    # Add new directory.
    iso.add_directory("/DIR1")

    do_a_test(iso, check_onefileonedir)

    iso.close()

def test_new_onefileonedir2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new directory.
    iso.add_directory("/DIR1")
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_onefileonedir)

    iso.close()

def test_new_onefile_onedirwithfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    # Add new directory.
    iso.add_directory("/DIR1")
    # Add new sub-file.
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

    do_a_test(iso, check_onefile_onedirwithfile)

    iso.close()

def test_new_tendirs(tmpdir):
    numdirs = 10

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_tendirs)

    iso.close()

def test_new_dirs_overflow_ptr_extent(tmpdir):
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

    iso.close()

def test_new_dirs_just_short_ptr_extent(tmpdir):
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

    iso.close()

def test_new_twoextentfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)

    iso.add_fp(cStringIO.StringIO(outstr), len(outstr), "/BIGFILE.;1")

    do_a_test(iso, check_twoextentfile)

    iso.close()

def test_new_twoleveldeepdir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")

    do_a_test(iso, check_twoleveldeepdir)

    iso.close()

def test_new_twoleveldeepfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")
    mystr = "foo\n"
    iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/DIR1/SUBDIR1/FOO.;1")

    do_a_test(iso, check_twoleveldeepfile)

    iso.close()

def test_new_dirs_overflow_ptr_extent_reverse(tmpdir):
    numdirs = 295

    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    for i in reversed(range(1, 1+numdirs)):
        iso.add_directory("/DIR%d" % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

    iso.close()

def test_new_toodeepdir(tmpdir):
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
    out = cStringIO.StringIO()
    iso.write_fp(out)
    pyiso.PyIso().open_fp(out)

    iso.close()

def test_new_toodeepfile(tmpdir):
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
        iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/FOO.;1")

    # Now make sure we can re-open the written ISO.
    out = cStringIO.StringIO()
    iso.write_fp(out)
    pyiso.PyIso().open_fp(out)

    iso.close()

def test_new_removefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add second new file.
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    # Remove the second file.
    iso.rm_file("/BAR.;1")

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_removedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add new directory.
    iso.add_directory("/DIR1")

    # Remove the directory
    iso.rm_directory("/DIR1")

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_eltorito(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_eltorito_nofiles)

    iso.close()

def test_new_rm_eltorito(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.rm_eltorito()
    iso.rm_file("/BOOT.;1")

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_eltorito_twofile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AA.;1")

    do_a_test(iso, check_eltorito_twofile)

    iso.close()

def test_new_rr_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_rr_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    mystr = "foo\n"
    iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1", rr_name="foo")

    do_a_test(iso, check_rr_onefile)

    iso.close()

def test_new_rr_twofile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    # Add a new file.
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/BAR.;1", rr_name="bar")

    do_a_test(iso, check_rr_twofile)

    iso.close()

def test_new_rr_onefileonedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    # Add new directory.
    iso.add_directory("/DIR1", rr_name="dir1")

    do_a_test(iso, check_rr_onefileonedir)

    iso.close()

def test_new_rr_onefileonedirwithfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    # Add new directory.
    iso.add_directory("/DIR1", rr_name="dir1")

    # Add a new file.
    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1", rr_name="bar")

    do_a_test(iso, check_rr_onefileonedirwithfile)

    iso.close()

def test_new_rr_symlink(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    iso.add_symlink("/SYM.;1", "sym", "foo")

    do_a_test(iso, check_rr_symlink)

    iso.close()

def test_new_rr_symlink2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add new directory.
    iso.add_directory("/DIR1", rr_name="dir1")

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/DIR1/FOO.;1", rr_name="foo")

    iso.add_symlink("/SYM.;1", "sym", "dir1/foo")

    do_a_test(iso, check_rr_symlink2)

    iso.close()

def test_new_rr_symlink_dot(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", ".")

    do_a_test(iso, check_rr_symlink_dot)

    iso.close()

def test_new_rr_symlink_dotdot(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "..")

    do_a_test(iso, check_rr_symlink_dotdot)

    iso.close()

def test_new_rr_symlink_broken(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_symlink("/SYM.;1", "sym", "foo")

    do_a_test(iso, check_rr_symlink_broken)

    iso.close()

def test_new_rr_verylongname(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_name="a"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongname)

    iso.close()

def test_new_rr_verylongname_joliet(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_name="a"*RR_MAX_FILENAME_LENGTH, joliet_path="/"+"a"*64)

    do_a_test(iso, check_rr_verylongname_joliet)

    iso.close()

def test_new_rr_manylongname(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_name="a"*RR_MAX_FILENAME_LENGTH)

    bbstr = "bb\n"
    iso.add_fp(cStringIO.StringIO(bbstr), len(bbstr), "/BBBBBBBB.;1", rr_name="b"*RR_MAX_FILENAME_LENGTH)

    ccstr = "cc\n"
    iso.add_fp(cStringIO.StringIO(ccstr), len(ccstr), "/CCCCCCCC.;1", rr_name="c"*RR_MAX_FILENAME_LENGTH)

    ddstr = "dd\n"
    iso.add_fp(cStringIO.StringIO(ddstr), len(ddstr), "/DDDDDDDD.;1", rr_name="d"*RR_MAX_FILENAME_LENGTH)

    eestr = "ee\n"
    iso.add_fp(cStringIO.StringIO(eestr), len(eestr), "/EEEEEEEE.;1", rr_name="e"*RR_MAX_FILENAME_LENGTH)

    ffstr = "ff\n"
    iso.add_fp(cStringIO.StringIO(ffstr), len(ffstr), "/FFFFFFFF.;1", rr_name="f"*RR_MAX_FILENAME_LENGTH)

    ggstr = "gg\n"
    iso.add_fp(cStringIO.StringIO(ggstr), len(ggstr), "/GGGGGGGG.;1", rr_name="g"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname)

    iso.close()

def test_new_rr_manylongname2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_name="a"*RR_MAX_FILENAME_LENGTH)

    bbstr = "bb\n"
    iso.add_fp(cStringIO.StringIO(bbstr), len(bbstr), "/BBBBBBBB.;1", rr_name="b"*RR_MAX_FILENAME_LENGTH)

    ccstr = "cc\n"
    iso.add_fp(cStringIO.StringIO(ccstr), len(ccstr), "/CCCCCCCC.;1", rr_name="c"*RR_MAX_FILENAME_LENGTH)

    ddstr = "dd\n"
    iso.add_fp(cStringIO.StringIO(ddstr), len(ddstr), "/DDDDDDDD.;1", rr_name="d"*RR_MAX_FILENAME_LENGTH)

    eestr = "ee\n"
    iso.add_fp(cStringIO.StringIO(eestr), len(eestr), "/EEEEEEEE.;1", rr_name="e"*RR_MAX_FILENAME_LENGTH)

    ffstr = "ff\n"
    iso.add_fp(cStringIO.StringIO(ffstr), len(ffstr), "/FFFFFFFF.;1", rr_name="f"*RR_MAX_FILENAME_LENGTH)

    ggstr = "gg\n"
    iso.add_fp(cStringIO.StringIO(ggstr), len(ggstr), "/GGGGGGGG.;1", rr_name="g"*RR_MAX_FILENAME_LENGTH)

    hhstr = "hh\n"
    iso.add_fp(cStringIO.StringIO(hhstr), len(hhstr), "/HHHHHHHH.;1", rr_name="h"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname2)

    iso.close()

def test_new_rr_verylongnameandsymlink(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    aastr = "aa\n"
    iso.add_fp(cStringIO.StringIO(aastr), len(aastr), "/AAAAAAAA.;1", rr_name="a"*RR_MAX_FILENAME_LENGTH)

    iso.add_symlink("/BBBBBBBB.;1", "b"*RR_MAX_FILENAME_LENGTH, "a"*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongnameandsymlink)

    iso.close()

def test_new_alternating_subdir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    ddstr = "dd\n"
    iso.add_fp(cStringIO.StringIO(ddstr), len(ddstr), "/DD.;1")

    bbstr = "bb\n"
    iso.add_fp(cStringIO.StringIO(bbstr), len(bbstr), "/BB.;1")

    iso.add_directory("/CC")

    iso.add_directory("/AA")

    subdirfile1 = "sub1\n"
    iso.add_fp(cStringIO.StringIO(subdirfile1), len(subdirfile1), "/AA/SUB1.;1")

    subdirfile2 = "sub2\n"
    iso.add_fp(cStringIO.StringIO(subdirfile2), len(subdirfile2), "/CC/SUB2.;1")

    do_a_test(iso, check_alternating_subdir)

    iso.close()

def test_new_joliet_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_onedir)

    iso.close()

def test_new_joliet_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_joliet_onefile)

    iso.close()

def test_new_joliet_onefileonedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_onefileonedir)

    iso.close()

def test_new_joliet_and_rr_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    do_a_test(iso, check_joliet_and_rr_nofiles)

    iso.close()

def test_new_joliet_and_rr_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo", joliet_path="/foo")

    do_a_test(iso, check_joliet_and_rr_onefile)

    iso.close()

def test_new_joliet_and_rr_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, rock_ridge=True)

    # Add a directory.
    iso.add_directory("/DIR1", rr_name="dir1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_and_rr_onedir)

    iso.close()

def test_new_rr_and_eltorito_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_rr_and_eltorito_nofiles)

    iso.close()

def test_new_rr_and_eltorito_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    do_a_test(iso, check_rr_and_eltorito_onefile)

    iso.close()

def test_new_rr_and_eltorito_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", rr_name="dir1")

    do_a_test(iso, check_rr_and_eltorito_onedir)

    iso.close()

def test_new_rr_and_eltorito_onedir2(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_name="dir1")

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_rr_and_eltorito_onedir)

    iso.close()

def test_new_joliet_and_eltorito_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_joliet_and_eltorito_nofiles)

    iso.close()

def test_new_joliet_and_eltorito_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_joliet_and_eltorito_onefile)

    iso.close()

def test_new_joliet_and_eltorito_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_and_eltorito_onedir)

    iso.close()

def test_new_isohybrid(tmpdir):
    # Create a new ISO
    iso = pyiso.PyIso()
    iso.new()
    # Add Eltorito
    isolinux_fp = open('/usr/share/syslinux/isolinux.bin', 'rb')
    iso.add_fp(isolinux_fp, os.fstat(isolinux_fp.fileno()).st_size, "/ISOLINUX.BIN;1")
    iso.add_eltorito("/ISOLINUX.BIN;1", "/BOOT.CAT;1", boot_load_size=4)
    # Now add the syslinux
    iso.add_isohybrid('/usr/share/syslinux/isohdpfx.bin')

    do_a_test(iso, check_isohybrid)

    iso.close()

    isolinux_fp.close()

def test_new_joliet_rr_and_eltorito_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    do_a_test(iso, check_joliet_rr_and_eltorito_nofiles)

    iso.close()

def test_new_joliet_rr_and_eltorito_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo", joliet_path="/foo")

    do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

    iso.close()

def test_new_joliet_rr_and_eltorito_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_name="boot", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.add_directory("/DIR1", rr_name="dir1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

    iso.close()

def test_new_rr_rmfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    iso.rm_file("/FOO.;1", rr_name="foo")

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_rr_rmdir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_name="dir1")

    iso.rm_directory("/DIR1", rr_name="dir1")

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_joliet_rmfile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

    iso.rm_file("/BOOT.;1", joliet_path="/boot")

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_rmdir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    iso.rm_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rr_deep(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', rr_name='dir8')

    do_a_test(iso, check_rr_deep_dir)

    iso.close()

def test_new_xa_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    do_a_test(iso, check_xa_nofiles)

    iso.close()

def test_new_xa_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    do_a_test(iso, check_xa_onefile)

    iso.close()

def test_new_xa_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(xa=True)

    iso.add_directory("/DIR1")

    do_a_test(iso, check_xa_onedir)

    iso.close()

def test_new_sevendeepdirs(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory("/DIR1", rr_name="dir1")
    iso.add_directory("/DIR1/DIR2", rr_name="dir2")
    iso.add_directory("/DIR1/DIR2/DIR3", rr_name="dir3")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4", rr_name="dir4")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5", rr_name="dir5")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6", rr_name="dir6")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7", rr_name="dir7")

    do_a_test(iso, check_sevendeepdirs)

    iso.close()

def test_new_xa_joliet_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    do_a_test(iso, check_xa_joliet_nofiles)

    iso.close()

def test_new_xa_joliet_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    do_a_test(iso, check_xa_joliet_onefile)

    iso.close()

def test_new_xa_joliet_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True, xa=True)

    iso.add_directory("/DIR1", joliet_path="/dir1")

    do_a_test(iso, check_xa_joliet_onedir)

    iso.close()

def test_new_isolevel4_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    do_a_test(iso, check_isolevel4_nofiles)

    iso.close()

def test_new_isolevel4_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/foo")

    do_a_test(iso, check_isolevel4_onefile)

    iso.close()

def test_new_isolevel4_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    iso.add_directory("/dir1")

    do_a_test(iso, check_isolevel4_onedir)

    iso.close()

def test_new_isolevel4_eltorito(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat")

    do_a_test(iso, check_isolevel4_eltorito)

    iso.close()

def test_new_everything(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4, rock_ridge=True, joliet=True, xa=True)

    iso.add_directory("/dir1", rr_name="dir1", joliet_path="/dir1")
    iso.add_directory("/dir1/dir2", rr_name="dir2", joliet_path="/dir1/dir2")
    iso.add_directory("/dir1/dir2/dir3", rr_name="dir3", joliet_path="/dir1/dir2/dir3")
    iso.add_directory("/dir1/dir2/dir3/dir4", rr_name="dir4", joliet_path="/dir1/dir2/dir3/dir4")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5", rr_name="dir5", joliet_path="/dir1/dir2/dir3/dir4/dir5")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6", rr_name="dir6", joliet_path = "/dir1/dir2/dir3/dir4/dir5/dir6")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6/dir7", rr_name="dir7", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7")
    iso.add_directory("/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8", rr_name="dir8", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8")

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot", rr_name="boot", joliet_path="/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/foo", rr_name="foo", joliet_path="/foo")

    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar", rr_name="bar", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar")

    iso.add_symlink("/sym", "sym", "foo", joliet_path="/sym")

    iso.add_hard_link(iso_new_path="/dir1/foo", iso_old_path="/foo", rr_name="foo")
    iso.add_hard_link(iso_old_path="/foo", joliet_new_path="/dir1/foo")

    do_a_test(iso, check_everything)

    iso.close()

def test_new_rr_xa_nofiles(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    do_a_test(iso, check_rr_xa_nofiles)

    iso.close()

def test_new_rr_xa_onefile(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo")

    do_a_test(iso, check_rr_xa_onefile)

    iso.close()

def test_new_rr_xa_onedir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, xa=True)

    iso.add_directory("/DIR1", rr_name="dir1")

    do_a_test(iso, check_rr_xa_onedir)

    iso.close()

def test_new_rr_joliet_symlink(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_name="foo", joliet_path="/foo")

    iso.add_symlink("/SYM.;1", "sym", "foo", joliet_path="/sym")

    do_a_test(iso, check_rr_joliet_symlink)

    iso.close()

def test_new_rr_joliet_deep(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True, joliet=True)

    iso.add_directory("/DIR1", rr_name="dir1", joliet_path="/dir1")
    iso.add_directory("/DIR1/DIR2", rr_name="dir2", joliet_path="/dir1/dir2")
    iso.add_directory("/DIR1/DIR2/DIR3", rr_name="dir3", joliet_path="/dir1/dir2/dir3")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4", rr_name="dir4", joliet_path="/dir1/dir2/dir3/dir4")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5", rr_name="dir5", joliet_path="/dir1/dir2/dir3/dir4/dir5")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6", rr_name="dir6", joliet_path = "/dir1/dir2/dir3/dir4/dir5/dir6")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7", rr_name="dir7", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7")
    iso.add_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8", rr_name="dir8", joliet_path="/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8")

    do_a_test(iso, check_rr_joliet_deep)

    iso.close()

def test_new_duplicate_child(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    iso.add_directory("/DIR1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/DIR1")

def test_new_eltorito_multi_boot(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat")

    boot2str = "boot2\n"
    iso.add_fp(cStringIO.StringIO(boot2str), len(boot2str), "/boot2")
    iso.add_eltorito("/boot2", "/boot.cat")

    do_a_test(iso, check_eltorito_multi_boot)

    iso.close()

def test_new_eltorito_boot_table(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table)

    iso.close()

def test_new_eltorito_boot_table_large(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boot"*20
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table_large)

    iso.close()

def test_new_hard_link(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    # Add a directory.
    iso.add_directory("/DIR1")

    iso.add_hard_link(iso_new_path="/DIR1/FOO.;1", iso_old_path="/FOO.;1")

    do_a_test(iso, check_hard_link)

    iso.close()

def test_new_invalid_interchange(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(interchange_level=5)

    with pytest.raises(pyiso.PyIsoException):
        iso.new(interchange_level=0)

def test_new_open_twice(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    with pytest.raises(pyiso.PyIsoException):
        iso.new()

    iso.close()

def test_new_add_fp_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1")

def test_new_add_fp_no_rr_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1")

def test_new_add_fp_rr_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1", rr_name="foo")

def test_new_add_fp_no_joliet_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1")

    iso.close()

def test_new_add_fp_joliet_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1", joliet_path="/foo")

    iso.close()

def test_new_add_fp_joliet_name_too_long(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FOO.;1", joliet_path="/"+'a'*65)

    iso.close()

def test_new_add_dir_joliet_name_too_long(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/DIR1", joliet_path="/"+'a'*65)

    iso.close()

def test_new_close_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.close()

def test_new_rm_isohybrid_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_isohybrid()

def test_new_add_isohybrid_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.add_isohybrid('/usr/share/syslinux/isohdpfx.bin')

def test_new_add_isohybrid_bad_boot_load_size(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    isolinux_fp = open('/usr/bin/ls', 'rb')
    iso.add_fp(isolinux_fp, os.fstat(isolinux_fp.fileno()).st_size, "/ISOLINUX.BIN;1")
    iso.add_eltorito("/ISOLINUX.BIN;1", "/BOOT.CAT;1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_isohybrid('/usr/share/syslinux/isohdpfx.bin')

    iso.close()

def test_new_add_isohybrid_bad_file_signature(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    isolinux_fp = open('/usr/bin/ls', 'rb')
    iso.add_fp(isolinux_fp, os.fstat(isolinux_fp.fileno()).st_size, "/ISOLINUX.BIN;1")
    iso.add_eltorito("/ISOLINUX.BIN;1", "/BOOT.CAT;1", boot_load_size=4)
    with pytest.raises(pyiso.PyIsoException):
        iso.add_isohybrid('/usr/share/syslinux/isohdpfx.bin')

    iso.close()

def test_new_add_eltorito_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.add_eltorito("/ISOLINUX.BIN;1", "/BOOT.CAT;1", boot_load_size=4)

def test_new_add_file(tmpdir):
    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.new()
    # Add a new file.

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")

    iso.add_file(str(testout), "/FOO.;1")

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_add_file_twoleveldeep(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add new directory.
    iso.add_directory("/DIR1")
    iso.add_directory("/DIR1/SUBDIR1")
    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")
    iso.add_file(str(testout), "/DIR1/SUBDIR1/FOO.;1")

    do_a_test(iso, check_twoleveldeepfile)

    iso.close()

def test_new_add_isohybrid_fp_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        with open('/usr/share/syslinux/isohdpfx.bin', 'r') as fp:
            iso.add_isohybrid_fp(fp)

def test_new_rr_symlink_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.add_symlink("/SYM.;1", "sym", "foo")

def test_new_rr_symlink_no_rr(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    with pytest.raises(pyiso.PyIsoException):
        iso.add_symlink("/SYM.;1", "sym", "foo")

    iso.close()

def test_new_rr_symlink_not_relative(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    # Add a new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", "foo")

    with pytest.raises(pyiso.PyIsoException):
        iso.add_symlink("/SYM.;1", "sym", "/foo")

    iso.close()

def test_new_add_file_no_rr_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_file(str(testout), "/FOO.;1")

def test_new_add_file_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_file(str(testout), "/FOO.;1")

def test_new_hard_link_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(iso_new_path="/DIR1/FOO.;1", iso_old_path="/FOO.;1")

def test_new_write_fp_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    out = cStringIO.StringIO()
    with pytest.raises(pyiso.PyIsoException):
        iso.write_fp(out)

def test_new_same_dirname_different_parent(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    iso.new(rock_ridge=True, joliet=True)

    # Add new directory.
    iso.add_directory("/DIR1", rr_name="dir1", joliet_path="/dir1")
    iso.add_directory("/DIR1/BOOT", rr_name="boot", joliet_path="/dir1/boot")
    iso.add_directory("/DIR2", rr_name="dir2", joliet_path="/dir2")
    iso.add_directory("/DIR2/BOOT", rr_name="boot", joliet_path="/dir2/boot")

    do_a_test(iso, check_same_dirname_different_parent)

    iso.close()

def test_new_joliet_isolevel4(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4, joliet=True)
    # Add new file.
    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/foo", joliet_path="/foo")
    # Add new directory.
    iso.add_directory("/dir1", joliet_path="/dir1")

    do_a_test(iso, check_joliet_isolevel4)

    iso.close()

def test_new_eltorito_hide(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")
    iso.rm_hard_link(iso_path="/BOOT.CAT;1")

    do_a_test(iso, check_eltorito_nofiles_hide)

    iso.close()

def test_new_eltorito_nofiles_hide_joliet(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")
    iso.rm_hard_link(joliet_path="/boot.cat")
    iso.rm_hard_link(iso_path="/BOOT.CAT;1")

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide)

    iso.close()

def test_new_eltorito_nofiles_hide_joliet_only(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")
    iso.rm_hard_link(joliet_path="/boot.cat")

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide_only)

    iso.close()

def test_new_eltorito_nofiles_hide_iso_only(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")
    iso.rm_hard_link(iso_path="/BOOT.CAT;1")

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide_iso_only)

    iso.close()

def test_new_hard_link_reshuffle(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    iso.add_hard_link(iso_new_path="/BAR.;1", iso_old_path="/FOO.;1")

    do_a_test(iso, check_hard_link_reshuffle)

    iso.close()

def test_new_invalid_sys_ident(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(sys_ident='a'*33)

def test_new_invalid_vol_ident(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(vol_ident='a'*33)

def test_new_seqnum_greater_than_set_size(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(seqnum=99)

def test_new_invalid_vol_set_ident(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(vol_set_ident='a'*129)

def test_new_invalid_app_use(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(app_use='a'*513)

def test_new_invalid_app_use_xa(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(pyiso.PyIsoException):
        iso.new(xa=True, app_use='a'*142)

def test_new_invalid_filename_character(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FO#.;1")

def test_new_invalid_filename_semicolons(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FO0;1.;1")

def test_new_invalid_filename_version(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/FO0.;32768")

def test_new_invalid_filename_dotonly(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/.")

def test_new_invalid_filename_toolong(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/THISISAVERYLONGNAME.;1")

def test_new_invalid_extension_toolong(tmpdir):
    iso = pyiso.PyIso()
    iso.new()

    # Add a new file.
    mystr = "foo\n"
    with pytest.raises(pyiso.PyIsoException):
        iso.add_fp(cStringIO.StringIO(mystr), len(mystr), "/NAME.LONGEXT;1")

def test_new_invalid_dirname(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/")

def test_new_invalid_dirname_toolong(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/THISISAVERYLONGDIRECTORY")

def test_new_invalid_dirname_toolong4(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)
    # Add a directory.
    with pytest.raises(pyiso.PyIsoException):
        iso.add_directory("/"+"a"*208)

def test_new_rr_invalid_name(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_file(str(testout), "/FOO.;1", rr_name="foo/bar")

def test_new_hard_link_invalid_keyword(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")

    iso.add_file(str(testout), "/FOO.;1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(foo='bar')

def test_new_hard_link_no_eltorito(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")

    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(boot_catalog_old=True)

def test_new_hard_link_no_old_kw(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")

    iso.add_file(str(testout), "/FOO.;1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(iso_new_path='/FOO.;1')

def test_new_hard_link_no_new_kw(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")

    iso.add_file(str(testout), "/FOO.;1")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(iso_old_path='/FOO.;1')

def test_new_hard_link_new_missing_rr(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    testout = tmpdir.join("writetest.iso")
    with open(str(testout), 'w') as outfp:
        outfp.write("foo\n")

    iso.add_file(str(testout), "/FOO.;1", rr_name="foo")
    with pytest.raises(pyiso.PyIsoException):
        iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path="/BAR.;1")

def test_new_hard_link_eltorito(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.rm_hard_link("/BOOT.CAT;1")
    iso.add_hard_link(boot_catalog_old=True, iso_new_path="/BOOT.CAT;1")

    do_a_test(iso, check_eltorito_nofiles)

    iso.close()

def test_new_rm_hard_link_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link()

def test_new_rm_hard_link_no_path(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link()

def test_new_rm_hard_link_both_paths(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link(iso_path="/BOOT.;1", joliet_path="/boot")

def test_new_rm_hard_link_bad_path(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link(iso_path="BOOT.;1")

def test_new_rm_hard_link_dir(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    # Add a directory.
    iso.add_directory("/DIR1")

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link(iso_path="/DIR1")

def test_new_rm_hard_link_no_joliet(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    with pytest.raises(pyiso.PyIsoException):
        iso.rm_hard_link(joliet_path="/boot")

def test_new_rm_hard_link_remove_file(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")

    iso.rm_hard_link(iso_path="/BOOT.;1")

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_rm_hard_link_joliet_remove_file(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

    iso.rm_hard_link(iso_path="/BOOT.;1")
    iso.rm_hard_link(joliet_path="/boot")

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_rm_second(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")
    iso.add_hard_link(iso_old_path="/FOO.;1", iso_new_path="/BAR.;1")
    iso.add_hard_link(iso_old_path="/FOO.;1", iso_new_path="/BAZ.;1")

    iso.rm_hard_link(iso_path="/BAR.;1")
    iso.rm_hard_link(iso_path="/BAZ.;1")

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_rm_hard_link_rm_joliet_first(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

    iso.rm_hard_link(joliet_path="/foo")
    iso.rm_hard_link(iso_path="/FOO.;1")

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_rm_joliet_and_links(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")
    iso.add_hard_link(iso_old_path="/FOO.;1", iso_new_path="/BAR.;1")
    iso.add_hard_link(iso_old_path="/FOO.;1", iso_new_path="/BAZ.;1")

    iso.rm_hard_link(joliet_path="/foo")
    iso.rm_hard_link(iso_path="/BAR.;1")
    iso.rm_hard_link(iso_path="/BAZ.;1")
    iso.rm_hard_link(iso_path="/FOO.;1")

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_isolevel4(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    iso.rm_hard_link(iso_path="/FOO.;1")

    do_a_test(iso, check_isolevel4_nofiles)

    iso.close()

def test_add_hard_link_joliet_to_joliet(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    foostr = "foo\n"
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")
    iso.add_hard_link(joliet_old_path="/foo", joliet_new_path="/bar")

    iso.close()

def test_new_rr_deeper(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(rock_ridge=True)

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', rr_name='dir8')

    iso.add_directory('/A1', rr_name='a1')
    iso.add_directory('/A1/A2', rr_name='a2')
    iso.add_directory('/A1/A2/A3', rr_name='a3')
    iso.add_directory('/A1/A2/A3/A4', rr_name='a4')
    iso.add_directory('/A1/A2/A3/A4/A5', rr_name='a5')
    iso.add_directory('/A1/A2/A3/A4/A5/A6', rr_name='a6')
    iso.add_directory('/A1/A2/A3/A4/A5/A6/A7', rr_name='a7')
    iso.add_directory('/A1/A2/A3/A4/A5/A6/A7/A8', rr_name='a8')

    do_a_test(iso, check_rr_deeper_dir)

    iso.close()

def test_new_eltorito_boot_table_large_odd(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=4)

    bootstr = "boo"*27
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/boot")
    iso.add_eltorito("/boot", "/boot.cat", boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table_large_odd)

    iso.close()

def test_new_joliet_large_directory(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(joliet=True)

    for i in range(1, 50):
        iso.add_directory("/DIR%d" % i, joliet_path="/dir%d" % i)

    do_a_test(iso, check_joliet_large_directory)

    iso.close()

def test_new_zero_byte_file(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new(interchange_level=1)

    foostr = ""
    iso.add_fp(cStringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    barstr = "bar\n"
    iso.add_fp(cStringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    do_a_test(iso, check_zero_byte_file)

    iso.close()

def test_new_eltorito_hide_boot(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    iso.rm_hard_link(iso_path="/BOOT.;1")

    do_a_test(iso, check_eltorito_hide_boot)

    iso.close()

def test_new_full_path_from_dirrecord(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    iso.add_directory("/DIR1")

    bootstr = "boot\n"
    iso.add_fp(cStringIO.StringIO(bootstr), len(bootstr), "/DIR1/BOOT.;1")

    for child in iso.list_dir("/DIR1"):
        if child.file_identifier() == "BOOT.;1":
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == "/DIR1/BOOT.;1")

    iso.close()

def test_new_full_path_from_dirrecord_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pyiso.PyIso()

    with pytest.raises(pyiso.PyIsoException):
        iso.full_path_from_dirrecord(None)
