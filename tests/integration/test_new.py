# -*- coding: utf-8 -*-

import io
import os
import sys
import struct

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pycdlib

from test_common import *

def do_a_test(iso, check_func, tmpdir=None):
    if tmpdir is None:
        out = io.BytesIO()

        def do_getlen(obj):
            return len(obj.getvalue())

        def do_sync(obj):
            pass
    else:
        out = open(os.path.join(str(tmpdir), check_func.__name__), 'w+b')

        def do_getlen(obj):
            return os.fstat(out.fileno()).st_size

        def do_sync(obj):
            obj.flush()
            os.fsync(obj.fileno())

    try:
        iso.write_fp(out)
        do_sync(out)

        check_func(iso, do_getlen(out))

        iso2 = pycdlib.PyCdlib()
        iso2.open_fp(out)
        check_func(iso2, do_getlen(out))
        iso2.close()
    finally:
        out.close()

def test_new_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_onefile():
    # Now open up the ISO with pycdlib and check some things out.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    iso.add_directory('/DIR1')

    do_a_test(iso, check_onedir)

    iso.close()

def test_new_twofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add new files.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1')

    do_a_test(iso, check_twofiles)

    iso.close()

def test_new_twofiles2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add new files.
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_twofiles)

    iso.close()

def test_new_twodirs():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new directories.
    iso.add_directory('/AA')
    iso.add_directory('/BB')

    do_a_test(iso, check_twodirs)

    iso.close()

def test_new_twodirs2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new directories.
    iso.add_directory('/BB')
    iso.add_directory('/AA')

    do_a_test(iso, check_twodirs)

    iso.close()

def test_new_onefileonedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    # Add new directory.
    iso.add_directory('/DIR1')

    do_a_test(iso, check_onefileonedir)

    iso.close()

def test_new_onefileonedir2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add new directory.
    iso.add_directory('/DIR1')
    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_onefileonedir)

    iso.close()

def test_new_onefile_onedirwithfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    # Add new directory.
    iso.add_directory('/DIR1')
    # Add new sub-file.
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/DIR1/BAR.;1')

    do_a_test(iso, check_onefile_onedirwithfile)

    iso.close()

def test_new_tendirs():
    numdirs = 10

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory('/DIR%d' % i)

    do_a_test(iso, check_tendirs)

    iso.close()

def test_new_dirs_overflow_ptr_extent():
    numdirs = 295

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory('/DIR%d' % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

    iso.close()

def test_new_dirs_just_short_ptr_extent():
    numdirs = 293

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    for i in range(1, 1+numdirs):
        iso.add_directory('/DIR%d' % i)
    # Now add two more to push it over the boundary
    iso.add_directory('/DIR294')
    iso.add_directory('/DIR295')

    # Now remove them to put it back down below the boundary.
    iso.rm_directory('/DIR295')
    iso.rm_directory('/DIR294')

    do_a_test(iso, check_dirs_just_short_ptr_extent)

    iso.close()

def test_new_twoextentfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    outstr = b''
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack('=B', i)
    outstr += struct.pack('=B', 0)

    iso.add_fp(io.BytesIO(outstr), len(outstr), '/BIGFILE.;1')

    do_a_test(iso, check_twoextentfile)

    iso.close()

def test_new_twoleveldeepdir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new directory.
    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/SUBDIR1')

    do_a_test(iso, check_twoleveldeepdir)

    iso.close()

def test_new_twoleveldeepfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new directory.
    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/SUBDIR1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/SUBDIR1/FOO.;1')

    do_a_test(iso, check_twoleveldeepfile)

    iso.close()

def test_new_dirs_overflow_ptr_extent_reverse():
    numdirs = 295

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    for i in reversed(range(1, 1+numdirs)):
        iso.add_directory('/DIR%d' % i)

    do_a_test(iso, check_dirs_overflow_ptr_extent)

    iso.close()

def test_new_toodeepdir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/DIR2')
    iso.add_directory('/DIR1/DIR2/DIR3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8')
    assert(str(excinfo.value) == 'Directory levels too deep (maximum is 7)')

    # Now make sure we can re-open the written ISO.
    out = io.BytesIO()
    iso.write_fp(out)
    pycdlib.PyCdlib().open_fp(out)

    iso.close()

def test_new_toodeepfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/DIR2')
    iso.add_directory('/DIR1/DIR2/DIR3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7')
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/FOO.;1')
    assert(str(excinfo.value) == 'Directory levels too deep (maximum is 7)')

    # Now make sure we can re-open the written ISO.
    out = io.BytesIO()
    iso.write_fp(out)
    pycdlib.PyCdlib().open_fp(out)

    iso.close()

def test_new_removefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    # Add second new file.
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1')

    # Remove the second file.
    iso.rm_file('/BAR.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_removedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    # Add new directory.
    iso.add_directory('/DIR1')

    # Remove the directory
    iso.rm_directory('/DIR1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_eltorito_nofiles)

    iso.close()

def test_new_rm_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_eltorito()
    iso.rm_file('/BOOT.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_eltorito_twofile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AA.;1')

    do_a_test(iso, check_eltorito_twofile)

    iso.close()

def test_new_rr_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_rr_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    do_a_test(iso, check_rr_onefile)

    iso.close()

def test_new_rr_twofile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    # Add a new file.
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1', rr_name='bar')

    do_a_test(iso, check_rr_twofile)

    iso.close()

def test_new_rr_onefileonedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    # Add new directory.
    iso.add_directory('/DIR1', rr_name='dir1')

    do_a_test(iso, check_rr_onefileonedir)

    iso.close()

def test_new_rr_onefileonedirwithfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    # Add new directory.
    iso.add_directory('/DIR1', rr_name='dir1')

    # Add a new file.
    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/DIR1/BAR.;1', rr_name='bar')

    do_a_test(iso, check_rr_onefileonedirwithfile)

    iso.close()

def test_new_rr_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    do_a_test(iso, check_rr_symlink)

    iso.close()

def test_new_rr_symlink2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add new directory.
    iso.add_directory('/DIR1', rr_name='dir1')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1', rr_name='foo')

    iso.add_symlink('/SYM.;1', 'sym', 'dir1/foo')

    do_a_test(iso, check_rr_symlink2)

    iso.close()

def test_new_rr_symlink_dot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_symlink('/SYM.;1', 'sym', '.')

    do_a_test(iso, check_rr_symlink_dot)

    iso.close()

def test_new_rr_symlink_dotdot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_symlink('/SYM.;1', 'sym', '..')

    do_a_test(iso, check_rr_symlink_dotdot)

    iso.close()

def test_new_rr_symlink_broken():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    do_a_test(iso, check_rr_symlink_broken)

    iso.close()

def test_new_rr_verylongname():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongname)

    iso.close()

def test_new_rr_verylongname_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH, joliet_path='/'+'a'*64)

    do_a_test(iso, check_rr_verylongname_joliet)

    iso.close()

def test_new_rr_manylongname():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    bbstr = b'bb\n'
    iso.add_fp(io.BytesIO(bbstr), len(bbstr), '/BBBBBBBB.;1', rr_name='b'*RR_MAX_FILENAME_LENGTH)

    ccstr = b'cc\n'
    iso.add_fp(io.BytesIO(ccstr), len(ccstr), '/CCCCCCCC.;1', rr_name='c'*RR_MAX_FILENAME_LENGTH)

    ddstr = b'dd\n'
    iso.add_fp(io.BytesIO(ddstr), len(ddstr), '/DDDDDDDD.;1', rr_name='d'*RR_MAX_FILENAME_LENGTH)

    eestr = b'ee\n'
    iso.add_fp(io.BytesIO(eestr), len(eestr), '/EEEEEEEE.;1', rr_name='e'*RR_MAX_FILENAME_LENGTH)

    ffstr = b'ff\n'
    iso.add_fp(io.BytesIO(ffstr), len(ffstr), '/FFFFFFFF.;1', rr_name='f'*RR_MAX_FILENAME_LENGTH)

    ggstr = b'gg\n'
    iso.add_fp(io.BytesIO(ggstr), len(ggstr), '/GGGGGGGG.;1', rr_name='g'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname)

    iso.close()

def test_new_rr_manylongname2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    bbstr = b'bb\n'
    iso.add_fp(io.BytesIO(bbstr), len(bbstr), '/BBBBBBBB.;1', rr_name='b'*RR_MAX_FILENAME_LENGTH)

    ccstr = b'cc\n'
    iso.add_fp(io.BytesIO(ccstr), len(ccstr), '/CCCCCCCC.;1', rr_name='c'*RR_MAX_FILENAME_LENGTH)

    ddstr = b'dd\n'
    iso.add_fp(io.BytesIO(ddstr), len(ddstr), '/DDDDDDDD.;1', rr_name='d'*RR_MAX_FILENAME_LENGTH)

    eestr = b'ee\n'
    iso.add_fp(io.BytesIO(eestr), len(eestr), '/EEEEEEEE.;1', rr_name='e'*RR_MAX_FILENAME_LENGTH)

    ffstr = b'ff\n'
    iso.add_fp(io.BytesIO(ffstr), len(ffstr), '/FFFFFFFF.;1', rr_name='f'*RR_MAX_FILENAME_LENGTH)

    ggstr = b'gg\n'
    iso.add_fp(io.BytesIO(ggstr), len(ggstr), '/GGGGGGGG.;1', rr_name='g'*RR_MAX_FILENAME_LENGTH)

    hhstr = b'hh\n'
    iso.add_fp(io.BytesIO(hhstr), len(hhstr), '/HHHHHHHH.;1', rr_name='h'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_manylongname2)

    iso.close()

def test_new_rr_verylongnameandsymlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    iso.add_symlink('/BBBBBBBB.;1', 'b'*RR_MAX_FILENAME_LENGTH, 'a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_verylongnameandsymlink)

    iso.close()

def test_new_alternating_subdir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    ddstr = b'dd\n'
    iso.add_fp(io.BytesIO(ddstr), len(ddstr), '/DD.;1')

    bbstr = b'bb\n'
    iso.add_fp(io.BytesIO(bbstr), len(bbstr), '/BB.;1')

    iso.add_directory('/CC')

    iso.add_directory('/AA')

    subdirfile1 = b'sub1\n'
    iso.add_fp(io.BytesIO(subdirfile1), len(subdirfile1), '/AA/SUB1.;1')

    subdirfile2 = b'sub2\n'
    iso.add_fp(io.BytesIO(subdirfile2), len(subdirfile2), '/CC/SUB2.;1')

    do_a_test(iso, check_alternating_subdir)

    iso.close()

def test_new_joliet_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_onedir)

    iso.close()

def test_new_joliet_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    do_a_test(iso, check_joliet_onefile)

    iso.close()

def test_new_joliet_onefileonedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.add_directory('/DIR1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_onefileonedir)

    iso.close()

def test_new_joliet_and_rr_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    do_a_test(iso, check_joliet_and_rr_nofiles)

    iso.close()

def test_new_joliet_and_rr_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', joliet_path='/foo')

    do_a_test(iso, check_joliet_and_rr_onefile)

    iso.close()

def test_new_joliet_and_rr_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    # Add a directory.
    iso.add_directory('/DIR1', rr_name='dir1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_and_rr_onedir)

    iso.close()

def test_new_rr_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_rr_and_eltorito_nofiles)

    iso.close()

def test_new_rr_and_eltorito_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    do_a_test(iso, check_rr_and_eltorito_onefile)

    iso.close()

def test_new_rr_and_eltorito_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.add_directory('/DIR1', rr_name='dir1')

    do_a_test(iso, check_rr_and_eltorito_onedir)

    iso.close()

def test_new_rr_and_eltorito_onedir2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_rr_and_eltorito_onedir)

    iso.close()

def test_new_joliet_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_joliet_and_eltorito_nofiles)

    iso.close()

def test_new_joliet_and_eltorito_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    do_a_test(iso, check_joliet_and_eltorito_onefile)

    iso.close()

def test_new_joliet_and_eltorito_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.add_directory('/DIR1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_and_eltorito_onedir)

    iso.close()

def test_new_isohybrid():
    # Create a new ISO
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add Eltorito
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4)
    # Now add the syslinux data
    iso.add_isohybrid()

    do_a_test(iso, check_isohybrid)

    iso.close()

def test_new_isohybrid_mac():
    # Create a new ISO
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add Eltorito
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    efibootstr = b'a'
    iso.add_fp(io.BytesIO(efibootstr), len(efibootstr), '/EFIBOOT.IMG;1')
    macbootstr = b'b'
    iso.add_fp(io.BytesIO(macbootstr), len(macbootstr), '/MACBOOT.IMG;1')

    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4, boot_info_table=True)
    iso.add_eltorito('/MACBOOT.IMG;1', efi=True)
    # Now add the syslinux data
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_isohybrid(part_type=0, mac=True, efi=False)

    iso.close()

def test_new_isohybrid_uefi():
    # Create a new ISO
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add Eltorito
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    efibootstr = b'a'
    iso.add_fp(io.BytesIO(efibootstr), len(efibootstr), '/EFIBOOT.IMG;1')

    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4, boot_info_table=True)
    iso.add_eltorito('/EFIBOOT.IMG;1', efi=True)
    # Now add the syslinux data
    iso.add_isohybrid(efi=True)

    do_a_test(iso, check_isohybrid_uefi)

    iso.close()

def test_new_isohybrid_mac_uefi():
    # Create a new ISO
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add Eltorito
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    efibootstr = b'a'
    iso.add_fp(io.BytesIO(efibootstr), len(efibootstr), '/EFIBOOT.IMG;1')
    macbootstr = b'b'
    iso.add_fp(io.BytesIO(macbootstr), len(macbootstr), '/MACBOOT.IMG;1')

    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4, boot_info_table=True)
    iso.add_eltorito('/MACBOOT.IMG;1', efi=True)
    iso.add_eltorito('/EFIBOOT.IMG;1', efi=True)
    # Now add the syslinux data
    iso.add_isohybrid(mac=True)

    do_a_test(iso, check_isohybrid_mac_uefi)

    iso.close()

def test_new_joliet_rr_and_eltorito_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_joliet_rr_and_eltorito_nofiles)

    iso.close()

def test_new_joliet_rr_and_eltorito_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', joliet_path='/foo')

    do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

    iso.close()

def test_new_joliet_rr_and_eltorito_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.add_directory('/DIR1', rr_name='dir1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

    iso.close()

def test_new_rr_rmfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    iso.rm_file('/FOO.;1', rr_name='foo')

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_rr_rmdir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')

    iso.rm_directory('/DIR1', rr_name='dir1')

    do_a_test(iso, check_rr_nofiles)

    iso.close()

def test_new_joliet_rmfile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')

    iso.rm_file('/BOOT.;1', joliet_path='/boot')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_rmdir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    iso.rm_directory('/DIR1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rr_deep():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

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

def test_new_xa_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(xa=True)

    do_a_test(iso, check_xa_nofiles)

    iso.close()

def test_new_xa_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(xa=True)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_xa_onefile)

    iso.close()

def test_new_xa_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(xa=True)

    iso.add_directory('/DIR1')

    do_a_test(iso, check_xa_onedir)

    iso.close()

def test_new_sevendeepdirs():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7')

    do_a_test(iso, check_sevendeepdirs)

    iso.close()

def test_new_xa_joliet_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, xa=True)

    do_a_test(iso, check_xa_joliet_nofiles)

    iso.close()

def test_new_xa_joliet_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, xa=True)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    do_a_test(iso, check_xa_joliet_onefile)

    iso.close()

def test_new_xa_joliet_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, xa=True)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    do_a_test(iso, check_xa_joliet_onedir)

    iso.close()

def test_new_isolevel4_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    do_a_test(iso, check_isolevel4_nofiles)

    iso.close()

def test_new_isolevel4_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/foo')

    do_a_test(iso, check_isolevel4_onefile)

    iso.close()

def test_new_isolevel4_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    iso.add_directory('/dir1')

    do_a_test(iso, check_isolevel4_onedir)

    iso.close()

def test_new_isolevel4_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    do_a_test(iso, check_isolevel4_eltorito)

    iso.close()

def test_new_everything():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, rock_ridge='1.09', joliet=3, xa=True)

    iso.add_directory('/dir1', rr_name='dir1', joliet_path='/dir1')
    iso.add_directory('/dir1/dir2', rr_name='dir2', joliet_path='/dir1/dir2')
    iso.add_directory('/dir1/dir2/dir3', rr_name='dir3', joliet_path='/dir1/dir2/dir3')
    iso.add_directory('/dir1/dir2/dir3/dir4', rr_name='dir4', joliet_path='/dir1/dir2/dir3/dir4')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5', rr_name='dir5', joliet_path='/dir1/dir2/dir3/dir4/dir5')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5/dir6', rr_name='dir6', joliet_path = '/dir1/dir2/dir3/dir4/dir5/dir6')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5/dir6/dir7', rr_name='dir7', joliet_path='/dir1/dir2/dir3/dir4/dir5/dir6/dir7')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8', rr_name='dir8', joliet_path='/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot', rr_name='boot', joliet_path='/boot')
    iso.add_eltorito('/boot', '/boot.cat', boot_info_table=True)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/foo', rr_name='foo', joliet_path='/foo')

    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar', rr_name='bar', joliet_path='/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8/bar')

    iso.add_symlink('/sym', 'sym', 'foo', joliet_path='/sym')

    iso.add_hard_link(iso_new_path='/dir1/foo', iso_old_path='/foo', rr_name='foo')
    iso.add_hard_link(iso_old_path='/foo', joliet_new_path='/dir1/foo')

    do_a_test(iso, check_everything)

    iso.close()

def test_new_rr_xa_nofiles():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', xa=True)

    do_a_test(iso, check_rr_xa_nofiles)

    iso.close()

def test_new_rr_xa_onefile():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', xa=True)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    do_a_test(iso, check_rr_xa_onefile)

    iso.close()

def test_new_rr_xa_onedir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', xa=True)

    iso.add_directory('/DIR1', rr_name='dir1')

    do_a_test(iso, check_rr_xa_onedir)

    iso.close()

def test_new_rr_joliet_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', joliet_path='/foo')

    iso.add_symlink('/SYM.;1', 'sym', 'foo', joliet_path='/sym')

    do_a_test(iso, check_rr_joliet_symlink)

    iso.close()

def test_new_rr_joliet_deep():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    iso.add_directory('/DIR1', rr_name='dir1', joliet_path='/dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2', joliet_path='/dir1/dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3', joliet_path='/dir1/dir2/dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4', joliet_path='/dir1/dir2/dir3/dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5', joliet_path='/dir1/dir2/dir3/dir4/dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6', joliet_path = '/dir1/dir2/dir3/dir4/dir5/dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7', joliet_path='/dir1/dir2/dir3/dir4/dir5/dir6/dir7')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', rr_name='dir8', joliet_path='/dir1/dir2/dir3/dir4/dir5/dir6/dir7/dir8')

    do_a_test(iso, check_rr_joliet_deep)

    iso.close()

def test_new_duplicate_child():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/DIR1')
    assert(str(excinfo.value) == 'Failed adding duplicate name to parent')

def test_new_eltorito_multi_boot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    do_a_test(iso, check_eltorito_multi_boot)

    iso.close()

def test_new_eltorito_boot_table():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat', boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table)

    iso.close()

def test_new_eltorito_boot_table_large():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot'*20
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat', boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table_large)

    iso.close()

def test_new_hard_link():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    # Add a directory.
    iso.add_directory('/DIR1')

    iso.add_hard_link(iso_new_path='/DIR1/FOO.;1', iso_old_path='/FOO.;1')

    do_a_test(iso, check_hard_link)

    iso.close()

def test_new_invalid_interchange():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(interchange_level=5)
    assert(str(excinfo.value) == 'Invalid interchange level (must be between 1 and 4)')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(interchange_level=0)
    assert(str(excinfo.value) == 'Invalid interchange level (must be between 1 and 4)')

def test_new_open_twice():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new()
    assert(str(excinfo.value) == 'This object already has an ISO; either close it or create a new object')

    iso.close()

def test_new_add_fp_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_add_fp_no_rr_name():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    assert(str(excinfo.value) == 'Rock Ridge name must be supplied for a Rock Ridge new path')

    iso.close()

def test_new_add_fp_rr_name():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')
    assert(str(excinfo.value) == 'A rock ridge name can only be specified for a rock-ridge ISO')

    iso.close()

def test_new_add_fp_no_joliet_name():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_onefile_joliet_no_file)

    iso.close()

def test_new_add_fp_joliet_name():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    assert(str(excinfo.value) == 'A Joliet path can only be specified for a Joliet ISO')

    iso.close()

def test_new_add_fp_joliet_name_too_long():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/'+'a'*65)
    assert(str(excinfo.value) == 'Joliet names can be a maximum of 64 characters')

    iso.close()

def test_new_add_dir_joliet_name_too_long():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/DIR1', joliet_path='/'+'a'*65)
    assert(str(excinfo.value) == 'Joliet names can be a maximum of 64 characters')

    iso.close()

def test_new_close_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.close()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_rm_isohybrid_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_isohybrid()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_add_isohybrid_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_isohybrid()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_add_isohybrid_bad_boot_load_size():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    isolinuxstr = b'\x00'*0x801
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')

    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_isohybrid()
    assert(str(excinfo.value) == 'El Torito Boot Catalog sector count must be 4 (was actually 0x8)')

    iso.close()

def test_new_add_isohybrid_bad_file_signature():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    isolinuxstr = b'\x00'*0x44
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_isohybrid()
    assert(str(excinfo.value) == 'Invalid signature on boot file for iso hybrid')

    iso.close()

def test_new_add_eltorito_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4)
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_add_file(tmpdir):
    # Now open up the ISO with pycdlib and check some things out.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a new file.

    testout = tmpdir.join('writetest.iso')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')

    iso.add_file(str(testout), '/FOO.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_add_file_twoleveldeep(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add new directory.
    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/SUBDIR1')
    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')
    iso.add_file(str(testout), '/DIR1/SUBDIR1/FOO.;1')

    do_a_test(iso, check_twoleveldeepfile)

    iso.close()

def test_new_rr_symlink_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/SYM.;1', 'sym', 'foo')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_rr_symlink_no_rr():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/SYM.;1', 'sym', 'foo')
    assert(str(excinfo.value) == 'Can only add a symlink to a Rock Ridge or UDF ISO')

    iso.close()

def test_new_rr_symlink_absolute():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_symlink('/SYM.;1', 'sym', '/usr/local/foo')

    do_a_test(iso, check_rr_absolute_symlink)

    iso.close()

def test_new_add_file_no_rr_name(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_file(str(testout), '/FOO.;1')
    assert(str(excinfo.value) == 'Rock Ridge name must be supplied for a Rock Ridge new path')

def test_new_add_file_not_initialized(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_file(str(testout), '/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_hard_link_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_new_path='/DIR1/FOO.;1', iso_old_path='/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_write_fp_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.write_fp(out)
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_same_dirname_different_parent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    iso.new(rock_ridge='1.09', joliet=3)

    # Add new directory.
    iso.add_directory('/DIR1', rr_name='dir1', joliet_path='/dir1')
    iso.add_directory('/DIR1/BOOT', rr_name='boot', joliet_path='/dir1/boot')
    iso.add_directory('/DIR2', rr_name='dir2', joliet_path='/dir2')
    iso.add_directory('/DIR2/BOOT', rr_name='boot', joliet_path='/dir2/boot')

    do_a_test(iso, check_same_dirname_different_parent)

    iso.close()

def test_new_joliet_isolevel4():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, joliet=3)
    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/foo', joliet_path='/foo')
    # Add new directory.
    iso.add_directory('/dir1', joliet_path='/dir1')

    do_a_test(iso, check_joliet_isolevel4)

    iso.close()

def test_new_eltorito_hide():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    iso.rm_hard_link(iso_path='/BOOT.CAT;1')

    do_a_test(iso, check_eltorito_nofiles_hide)

    iso.close()

def test_new_eltorito_nofiles_hide_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    iso.rm_hard_link(joliet_path='/boot.cat')
    iso.rm_hard_link(iso_path='/BOOT.CAT;1')

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide)

    iso.close()

def test_new_eltorito_nofiles_hide_joliet_only():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    # After add_fp:
    #  boot - 1 link (1 Joliet)
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    # After add_eltorito:
    #  boot - 1 link (1 Joliet, eltorito initial entry is "special")
    #  boot.cat - 1 link (1 Joliet)
    iso.rm_hard_link(joliet_path='/boot.cat')
    # After rm_hard_link:
    #  boot - 1 link (1 Joliet, eltorito initial entry is "special")
    #  boot.cat - 0 links (ISO only)

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide_only)

    iso.close()

def test_new_eltorito_nofiles_hide_iso_only():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    iso.rm_hard_link(iso_path='/BOOT.CAT;1')

    do_a_test(iso, check_joliet_and_eltorito_nofiles_hide_iso_only)

    iso.close()

def test_new_hard_link_reshuffle():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_new_path='/BAR.;1', iso_old_path='/FOO.;1')

    do_a_test(iso, check_hard_link_reshuffle)

    iso.close()

def test_new_invalid_sys_ident():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(sys_ident='a'*33)
    assert(str(excinfo.value) == 'The system identifer has a maximum length of 32')

def test_new_invalid_vol_ident():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(vol_ident='a'*33)
    assert(str(excinfo.value) == 'The volume identifier has a maximum length of 32')

def test_new_seqnum_greater_than_set_size():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(seqnum=99)
    assert(str(excinfo.value) == 'Sequence number must be less than or equal to set size')

def test_new_invalid_vol_set_ident():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(vol_set_ident='a'*129)
    assert(str(excinfo.value) == 'The maximum length for the volume set identifier is 128')

def test_new_invalid_app_use():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(app_use='a'*513)
    assert(str(excinfo.value) == 'The maximum length for the application use is 512')

def test_new_invalid_app_use_xa():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(xa=True, app_use='a'*142)
    assert(str(excinfo.value) == 'Cannot have XA and an app_use of > 140 bytes')

def test_new_invalid_filename_character():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FO#.;1')
    assert(str(excinfo.value) == 'ISO9660 filenames must consist of characters A-Z, 0-9, and _')

def test_new_invalid_filename_semicolons():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FO0;1.;1')
    assert(str(excinfo.value) == 'ISO9660 filenames must contain exactly one semicolon')

def test_new_invalid_filename_version():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;32768')
    assert(str(excinfo.value) == 'ISO9660 filenames must have a version between 1 and 32767')

def test_new_invalid_filename_dotonly():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/.')
    assert(str(excinfo.value) == 'ISO9660 filenames must have a non-empty name or extension')

def test_new_invalid_filename_toolong():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/THISISAVERYLONGNAME.;1')
    assert(str(excinfo.value) == 'ISO9660 filenames at interchange level 1 cannot have more than 8 characters or 3 characters in the extension')

def test_new_invalid_extension_toolong():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/NAME.LONGEXT;1')
    assert(str(excinfo.value) == 'ISO9660 filenames at interchange level 1 cannot have more than 8 characters or 3 characters in the extension')

def test_new_invalid_dirname():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/')
    assert(str(excinfo.value) == 'ISO9660 directory names must be at least 1 character long')

def test_new_invalid_dirname_toolong():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/THISISAVERYLONGDIRECTORY')
    assert(str(excinfo.value) == 'ISO9660 directory names at interchange level 1 cannot exceed 8 characters')

def test_new_invalid_dirname_toolong4():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3)
    # Add a directory.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/'+'a'*208)
    assert(str(excinfo.value) == 'ISO9660 directory names at interchange level 3 cannot exceed 207 characters')

def test_new_rr_invalid_name(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_file(str(testout), '/FOO.;1', rr_name='foo/bar')
    assert(str(excinfo.value) == 'A rock ridge name must be relative')

def test_new_hard_link_invalid_keyword(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')

    iso.add_file(str(testout), '/FOO.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(foo='bar')
    assert(str(excinfo.value) == 'Exactly one old path must be specified')

def test_new_hard_link_no_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(boot_catalog_old=True)
    assert(str(excinfo.value) == 'Attempting to make link to non-existent El Torito boot catalog')

def test_new_hard_link_no_old_kw(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')

    iso.add_file(str(testout), '/FOO.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_new_path='/FOO.;1')
    assert(str(excinfo.value) == 'Exactly one old path must be specified')

def test_new_hard_link_no_new_kw(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')

    iso.add_file(str(testout), '/FOO.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_old_path='/FOO.;1')
    assert(str(excinfo.value) == 'Exactly one new path must be specified')

def test_new_hard_link_new_missing_rr(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    testout = tmpdir.join('foo')
    with open(str(testout), 'wb') as outfp:
        outfp.write(b'foo\n')

    iso.add_file(str(testout), '/FOO.;1', rr_name='foo')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')
    assert(str(excinfo.value) == 'Rock Ridge name must be supplied for a Rock Ridge new path')

def test_new_hard_link_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_hard_link('/BOOT.CAT;1')
    iso.add_hard_link(boot_catalog_old=True, iso_new_path='/BOOT.CAT;1')

    do_a_test(iso, check_eltorito_nofiles)

    iso.close()

def test_new_rm_hard_link_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_rm_hard_link_no_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link()
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, joliet_path, or udf_path')

def test_new_rm_hard_link_both_paths():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(iso_path='/BOOT.;1', joliet_path='/boot')
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, joliet_path, or udf_path')

def test_new_rm_hard_link_bad_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(iso_path='BOOT.;1')
    assert(str(excinfo.value) == 'Must be a path starting with /')

def test_new_rm_hard_link_dir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add a directory.
    iso.add_directory('/DIR1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(iso_path='/DIR1')
    assert(str(excinfo.value) == 'Cannot remove a directory with rm_hard_link (try rm_directory instead)')

def test_new_rm_hard_link_no_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(joliet_path='/boot')
    assert(str(excinfo.value) == 'Cannot remove Joliet link from non-Joliet ISO')

def test_new_rm_hard_link_remove_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')

    iso.rm_hard_link(iso_path='/BOOT.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_rm_hard_link_joliet_remove_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')

    iso.rm_hard_link(iso_path='/BOOT.;1')
    iso.rm_hard_link(joliet_path='/boot')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_rm_second():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAZ.;1')

    iso.rm_hard_link(iso_path='/BAR.;1')
    iso.rm_hard_link(iso_path='/BAZ.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_rm_hard_link_rm_joliet_first():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_hard_link(joliet_path='/foo')
    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_rm_joliet_and_links():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAZ.;1')

    iso.rm_hard_link(joliet_path='/foo')
    iso.rm_hard_link(iso_path='/BAR.;1')
    iso.rm_hard_link(iso_path='/BAZ.;1')
    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_hard_link_isolevel4():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_isolevel4_nofiles)

    iso.close()

def test_add_hard_link_joliet_to_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    iso.add_hard_link(joliet_old_path='/foo', joliet_new_path='/bar')

    iso.close()

def test_new_rr_deeper():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

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

def test_new_eltorito_boot_table_large_odd():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boo'*27
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat', boot_info_table=True)

    do_a_test(iso, check_eltorito_boot_info_table_large_odd)

    iso.close()

def test_new_eltorito_boot_table_invalid_out(tmpdir):
    testboot = tmpdir.join('boot')
    testout = tmpdir.join('boot.out')

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    with open(str(testboot), 'wb') as outfp:
        outfp.write(b'abcdefghijklmnopqrstuvwxyz'*10)
    iso.add_file(str(testboot), '/boot')
    iso.add_eltorito('/boot', '/boot.cat', boot_info_table=True)

    iso.force_consistency()

    iso.get_file_from_iso(str(testout), iso_path='/boot')

    with open(str(testout), 'rb') as infp:
        data = infp.read()

    assert(data == b'abcdefgh\x10\x00\x00\x00\x1b\x00\x00\x00\x04\x01\x00\x00\xf5:\x045\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00mnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz')

    iso.close()

def test_new_joliet_large_directory():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    for i in range(1, 50):
        iso.add_directory('/DIR%d' % i, joliet_path='/dir%d' % i)

    do_a_test(iso, check_joliet_large_directory)

    iso.close()

def test_new_zero_byte_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1)

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1')

    do_a_test(iso, check_zero_byte_file)

    iso.close()

def test_new_eltorito_hide_boot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_hard_link(iso_path='/BOOT.;1')

    do_a_test(iso, check_eltorito_hide_boot)

    iso.close()

def test_new_full_path_from_dirrecord():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/DIR1/BOOT.;1')

    full_path = None
    for child in iso.list_children(iso_path='/DIR1'):
        if child.file_identifier() == b'BOOT.;1':
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/DIR1/BOOT.;1')
            break

    assert(full_path is not None)
    iso.close()

def test_new_full_path_from_dirrecord_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.full_path_from_dirrecord(None)
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_rock_ridge_one_point_twelve():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.12')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')

    iso.close()

def test_new_duplicate_pvd():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.duplicate_pvd()

    do_a_test(iso, check_duplicate_pvd)

    iso.close()

def test_new_duplicate_pvd_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.duplicate_pvd()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_eltorito_multi_multi_boot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    boot3str = b'boot3\n'
    iso.add_fp(io.BytesIO(boot3str), len(boot3str), '/boot3')
    iso.add_eltorito('/boot3', '/boot.cat')

    do_a_test(iso, check_eltorito_multi_multi_boot)

    iso.close()

def test_new_duplicate_pvd_not_same():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.duplicate_pvd()

    out = io.BytesIO()
    iso.write_fp(out)

    iso.close()

    # Back up to the application use portion of the duplicate PVD to make
    # it different than the primary one.  The duplicate PVD lives at extent
    # 17, so go to extent 18, backup 653 (to skip the zeros), then backup
    # one more to get back into the application use area.
    out.seek(18*2048 - 653 - 1)
    out.write(b'\xff')

    iso2 = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        iso2.open_fp(out)
    assert(str(excinfo.value) == 'Multiple occurrences of PVD did not agree!')

def infinitenamechecks(iso, filesize):
    dr = iso.pvd.root_dir_record.children[2]
    assert(len(dr.rock_ridge.dr_entries.nm_records) == 1)
    assert(dr.rock_ridge.dr_entries.nm_records[0].posix_name == b'a'*172)
    assert(dr.rock_ridge.dr_entries.nm_records[0].posix_name_flags == 1)

    assert(dr.rock_ridge.dr_entries.ce_record is not None)
    assert(len(dr.rock_ridge.ce_entries.nm_records) == 2)
    assert(dr.rock_ridge.ce_entries.nm_records[0].posix_name == b'a'*250)
    assert(dr.rock_ridge.ce_entries.nm_records[0].posix_name_flags == 1)
    assert(dr.rock_ridge.ce_entries.nm_records[1].posix_name == b'a'*78)
    assert(dr.rock_ridge.ce_entries.nm_records[1].posix_name_flags == 0)

def test_new_rr_exceedinglylongname():
    # This is a test to test out names > 255 in pycdlib.  Note that the Linux
    # kernel doesn't support this (nor does genisoimage), so this is strictly
    # an internal-only test to make sure we get things correct.

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*500)

    do_a_test(iso, infinitenamechecks)

    iso.close()

def symlink_path_checks(iso, size):
    assert(iso.pvd.root_dir_record.children[3].rock_ridge.symlink_path() == b'aaaaaaaa')

def test_new_rr_symlink_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='aaaaaaaa')

    iso.add_symlink('/BBBBBBBB.;1', 'bbbbbbbb', 'aaaaaaaa')

    do_a_test(iso, symlink_path_checks)

    iso.close()

def test_new_rr_symlink_path_not_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='aaaaaaaa')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.pvd.root_dir_record.children[2].rock_ridge.symlink_path()
    assert(str(excinfo.value) == 'Entry is not a symlink!')

def verylongsymlinkchecks(iso, size):
    assert(iso.pvd.root_dir_record.children[3].rock_ridge.symlink_path() == b'a'*RR_MAX_FILENAME_LENGTH)

def test_new_rr_verylongnameandsymlink_symlink_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    iso.add_symlink('/BBBBBBBB.;1', 'b'*RR_MAX_FILENAME_LENGTH, 'a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, verylongsymlinkchecks)

    iso.close()

def verylong_symlink_path_checks(iso, size):
    assert(iso.pvd.root_dir_record.children[3].rock_ridge.symlink_path() == b'a'*RR_MAX_FILENAME_LENGTH)

def test_new_rr_verylongsymlink_symlink_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='aaaaaaaa')

    iso.add_symlink('/BBBBBBBB.;1', 'bbbbbbbb', 'a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, verylong_symlink_path_checks)

    iso.close()

def extremelylong_symlink_path_checks(iso, size):
    assert(iso.pvd.root_dir_record.children[3].rock_ridge.symlink_path() == b'a'*500)

def test_new_rr_extremelylongsymlink_symlink_path():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', rr_name='aaaaaaaa')

    iso.add_symlink('/BBBBBBBB.;1', 'bbbbbbbb', 'a'*500)

    do_a_test(iso, extremelylong_symlink_path_checks)

    iso.close()

def test_new_rr_invalid_rr_version():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(rock_ridge='1.90')
    assert(str(excinfo.value) == 'Rock Ridge value must be None (no Rock Ridge), 1.09, 1.10, or 1.12')

def test_new_rr_onefile_onetwelve():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.12')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    do_a_test(iso, check_rr_onefile_onetwelve)

    iso.close()

def check_rr_onetwelve_px_in_ce(iso, filesize):
    # The version on the ISO must reflect what we wrote: 1.12.
    assert(iso.rock_ridge == '1.12')
    # Sanity-check that the scenario actually exercises CE-resident PX.
    # If a future writer change keeps PX inline even for very long names,
    # this test would otherwise silently stop covering the bug.
    long_name_dr = iso.pvd.root_dir_record.children[2]
    assert(long_name_dr.rock_ridge.dr_entries.ce_record is not None)
    assert(long_name_dr.rock_ridge.dr_entries.px_record is None)
    assert(long_name_dr.rock_ridge.ce_entries.px_record is not None)

def test_new_rr_onetwelve_px_in_ce():
    # Regression test for https://github.com/clalancette/pycdlib/pull/138.
    # When a Rock Ridge 1.12 record's filename is long enough to push the
    # PX record into the SUSP CE block, the parser must defer determining
    # the on-disk Rock Ridge version until after the CE block is read.
    # Pre-fix, _set_rock_ridge was called with the version inferred from
    # the directory record alone -- which sees no PX, defaults to '1.09',
    # and then trips 'Inconsistent Rock Ridge versions on the ISO!' on
    # the next correctly-inferred (inline-PX) record like '.' or '..'.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.12')

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1',
               rr_name='a' * RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_onetwelve_px_in_ce)

    iso.close()

def test_new_rr_intact_er_still_detected():
    # Sanity: a normal Rock Ridge ISO with the canonical ER record present
    # is still recognized as Rock Ridge after open.  Guards against the
    # post-hoc detection in _walk_directories accidentally wiping out
    # iso.rock_ridge for legitimate RR ISOs.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    assert(iso2.rock_ridge == '1.09')
    assert(iso2.has_rock_ridge())
    iso2.close()

def test_new_rr_missing_er_treated_as_non_rr():
    # Regression test for https://github.com/clalancette/pycdlib/issues/123.
    # A non-Rock-Ridge ISO can have system-use bytes that coincidentally
    # match RR SUSP signatures (e.g. some MAC app ISOs).  Per-record
    # opportunistic detection alone used to set iso.rock_ridge='1.09' from
    # those false positives, and walk(rr_path=...) would later trip with
    # "Cannot generate a Rock Ridge path on a non-Rock Ridge ISO" deep in
    # the traversal when an individual record didn't have RR data.  The
    # canonical RR signal is the ER record with ext_id 'RRIP_1991A' (or
    # 'IEEE_P1282' for 1.12) -- without it, the volume is not RR.
    #
    # Build a real RR 1.09 ISO, then scrub the ER ext_id bytes so the ISO
    # no longer declares RR via the canonical signal while leaving every
    # per-record RR-shaped byte intact.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    data = bytearray(out.getvalue())
    pos = data.find(b'RRIP_1991A')
    assert(pos >= 0)
    data[pos:pos + len(b'RRIP_1991A')] = b'XXXXXXXXXX'

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(bytes(data)))
    assert(iso2.rock_ridge == '')
    assert(not iso2.has_rock_ridge())
    # rr_path now hits the API-boundary guard with a clear message
    # instead of tripping deep inside walk().
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        list(iso2.walk(rr_path='/'))
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')
    iso2.close()

def test_new_rr_onetwelve_missing_er_treated_as_non_rr():
    # Same as test_new_rr_missing_er_treated_as_non_rr but for Rock Ridge
    # 1.12, whose ER ext_id is IEEE_P1282 instead of RRIP_1991A.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.12')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    data = bytearray(out.getvalue())
    pos = data.find(b'IEEE_P1282')
    assert(pos >= 0)
    data[pos:pos + len(b'IEEE_P1282')] = b'XXXXXXXXXX'

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(bytes(data)))
    assert(iso2.rock_ridge == '')
    assert(not iso2.has_rock_ridge())
    iso2.close()

def test_new_in_place_editor_modifies_file(tmpdir):
    # The InPlaceEditor context manager opens an ISO, runs one or more
    # in-place edits, and closes cleanly on exit.  The new content is
    # readable from the same file after the with-block exits.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.modify_file(io.BytesIO(b'new\n'), 4, '/FOO.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
    assert buf.getvalue() == b'new\n'
    iso2.close()

def test_new_in_place_editor_multiple_modifies(tmpdir):
    # The editor can batch multiple modifications in a single session,
    # amortizing the parse cost.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'AAA\n'), 4, '/A.;1')
    iso.add_fp(io.BytesIO(b'BBB\n'), 4, '/B.;1')
    iso.add_fp(io.BytesIO(b'CCC\n'), 4, '/C.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.modify_file(io.BytesIO(b'aaa\n'), 4, '/A.;1')
        ed.modify_file(io.BytesIO(b'bbb\n'), 4, '/B.;1')
        ed.modify_file(io.BytesIO(b'ccc\n'), 4, '/C.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    for path, expected in [('/A.;1', b'aaa\n'),
                           ('/B.;1', b'bbb\n'),
                           ('/C.;1', b'ccc\n')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path=path)
        assert buf.getvalue() == expected
    iso2.close()

def test_new_in_place_editor_propagates_exceptions(tmpdir):
    # If modify_file raises (e.g., bad iso_path), the editor still
    # closes the underlying ISO via __exit__.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        with pycdlib.InPlaceEditor(iso_path) as ed:
            ed.modify_file(io.BytesIO(b'x\n'), 2, '/NOPE.;1')

def test_new_in_place_editor_shrinks_across_extent_boundary(tmpdir):
    # modify_file allows the new content to occupy *fewer* extents
    # than the old content.  The orphaned extents inside the file's
    # original allocation are zeroed; the file's data_length on disk
    # reflects the new (smaller) size.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    # 5000 bytes occupies three 2048-byte extents.
    iso.add_fp(io.BytesIO(b'A' * 5000), 5000, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    # Shrink the file to 100 bytes (one extent) -- crosses two
    # extent boundaries downward.
    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.modify_file(io.BytesIO(b'b' * 100), 100, '/FOO.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
    assert buf.getvalue() == b'b' * 100
    iso2.close()

def test_new_in_place_editor_rejects_growing_across_extent_boundary(tmpdir):
    # Growing across an extent boundary is still rejected -- the
    # next extent on disk belongs to whatever sits after this file
    # in the volume layout.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
            ed.modify_file(io.BytesIO(b'f' * 2049), 2049, '/FOO.;1')

def test_new_in_place_editor_rm_file_basic(tmpdir):
    # rm_file removes a file from the in-memory tree and commits the
    # change to disk: the file's directory record is gone from the
    # parent's extent on disk.  The file's data extent stays as
    # orphaned bytes inside the volume.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'AAA\n'), 4, '/A.;1')
    iso.add_fp(io.BytesIO(b'BBB\n'), 4, '/B.;1')
    iso.add_fp(io.BytesIO(b'CCC\n'), 4, '/C.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/B.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    children = sorted(
        ch.file_identifier()
        for ch in iso2.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    assert children == [b'A.;1', b'C.;1']
    # The remaining files still read back correctly.
    for path, expected in [('/A.;1', b'AAA\n'), ('/C.;1', b'CCC\n')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path=path)
        assert buf.getvalue() == expected
    iso2.close()

def test_new_in_place_editor_multi_extent_directory(tmpdir):
    # Every other InPlaceEditor test operates on a directory that fits in a
    # single extent, so the editor never exercises _rewrite_dir_record_extent's
    # extent-transition and trailing-pad paths (the equivalent multi-extent
    # tests all go through modify_file_in_place/rm_file instead).
    #
    # Build a root directory that genuinely spans two extents, then remove the
    # first-sorting child so every later record shifts down -- which moves the
    # byte at which the rewrite crosses into the second extent -- plus a child
    # from the middle, and modify a child whose record lives in the second
    # extent.  If the rewrite leaves stale bytes behind at either the extent
    # transition or the tail, the re-parse below sees phantom records or fails.
    iso_path = str(tmpdir.join('test.iso'))
    names = ['F%03d' % i for i in range(60)]

    iso = pycdlib.PyCdlib()
    iso.new()
    for name in names:
        iso.add_fp(io.BytesIO((name + '\n').encode()), 5, '/%s.;1' % name)
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    # Make the multi-extent precondition explicit rather than incidental.
    probe = pycdlib.PyCdlib()
    probe.open(iso_path)
    assert probe.pvd.root_dir_record.data_length > 2048
    probe.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/F000.;1')
        ed.rm_file('/F030.;1')
        ed.modify_file(io.BytesIO(b'zzz\n'), 4, '/F059.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    children = sorted(
        ch.file_identifier()
        for ch in iso2.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    expected = sorted(('%s.;1' % name).encode()
                      for name in names if name not in ('F000', 'F030'))
    assert children == expected

    # A record in the first extent, and the modified one in the second.
    for path, contents in [('/F001.;1', b'F001\n'), ('/F059.;1', b'zzz\n')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path=path)
        assert buf.getvalue() == contents
    root_extent = iso2.pvd.root_dir_record.extent_location()
    root_data_length = iso2.pvd.root_dir_record.data_length
    iso2.close()

    # Now check the on-disk bytes.  The assertions above are not enough on
    # their own: if the rewrite omitted the pad at the extent transition,
    # every later record would simply shift down by the width of the gap and
    # pycdlib's own parser would still walk them, so the child list would
    # come back correct.  Ecma-119 6.8.1.1 forbids a directory record from
    # straddling an extent boundary, so assert that directly, along with the
    # gap at the end of each extent being zero-filled.
    with open(iso_path, 'rb') as f:
        data = f.read()

    lbs = 2048
    for extent in range(root_data_length // lbs):
        base = (root_extent + extent) * lbs
        offset = 0
        while offset < lbs and data[base + offset] != 0:
            reclen = data[base + offset]
            assert offset + reclen <= lbs, \
                'directory record straddles the end of extent %d' % extent
            offset += reclen
        assert data[base + offset:base + lbs] == b'\x00' * (lbs - offset), \
            'stale bytes after the last record in extent %d' % extent

def test_new_in_place_editor_rm_file_joliet(tmpdir):
    # rm_file is Joliet-aware: removing a file removes its record from
    # both the ISO9660 and Joliet trees.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    iso.add_fp(io.BytesIO(b'AAA\n'), 4, '/A.;1', joliet_path='/a')
    iso.add_fp(io.BytesIO(b'BBB\n'), 4, '/B.;1', joliet_path='/b')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/B.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    # Gone from ISO9660 root.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        iso2.get_file_from_iso_fp(io.BytesIO(), iso_path='/B.;1')
    # Gone from Joliet root too.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        iso2.get_file_from_iso_fp(io.BytesIO(), joliet_path='/b')
    iso2.close()

def test_new_in_place_editor_rm_file_rejects_directory(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/DIR')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
            ed.rm_file('/DIR')

def test_new_in_place_editor_rm_file_rejects_udf(tmpdir):
    # UDF in-place rm is out of scope for v1.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', udf_path='/foo')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.rm_file('/FOO.;1')
        assert 'UDF' in str(excinfo.value)

def test_new_in_place_editor_rm_file_rock_ridge(tmpdir):
    # rm_file on a Rock Ridge ISO removes the Rock Ridge-bearing
    # directory record from the parent extent without leaving stale
    # SUSP bytes behind that would fail re-parse.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'AAA\n'), 4, '/A.;1', rr_name='a')
    iso.add_fp(io.BytesIO(b'BBB\n'), 4, '/B.;1', rr_name='b')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/B.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    children = sorted(
        ch.file_identifier()
        for ch in iso2.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    assert children == [b'A.;1']
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, rr_path='/a')
    assert buf.getvalue() == b'AAA\n'
    iso2.close()

def test_new_in_place_editor_rm_file_rejects_eltorito_boot_file(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'BOOT' * 512), 2048, '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
            ed.rm_file('/BOOT.;1')

def test_new_in_place_editor_add_fp_basic(tmpdir):
    # add_fp appends a new file to the volume and inserts its
    # directory record into the parent's extent on disk.  The file
    # is readable from a freshly opened copy of the same ISO file.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'existing\n'), 9, '/EXIST.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_fp(io.BytesIO(b'new file contents\n'), 18, '/NEW.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    # Both files are present and read back correctly.
    for path, expected in [('/EXIST.;1', b'existing\n'),
                           ('/NEW.;1',   b'new file contents\n')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path=path)
        assert buf.getvalue() == expected
    iso2.close()

def test_new_in_place_editor_add_fp_joliet(tmpdir):
    # add_fp with joliet_path inserts the record into both the
    # ISO9660 and Joliet trees.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    iso.add_fp(io.BytesIO(b'existing\n'), 9, '/EXIST.;1', joliet_path='/exist')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_fp(io.BytesIO(b'new\n'), 4, '/NEW.;1', joliet_path='/new')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    for kwargs, expected in [({'iso_path': '/NEW.;1'},     b'new\n'),
                              ({'joliet_path': '/new'},     b'new\n')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, **kwargs)
        assert buf.getvalue() == expected
    iso2.close()

def test_new_in_place_editor_add_file_filename_variant(tmpdir):
    # The filename variant reads the new content from a file on the
    # local filesystem (pycdlib manages opening/closing).
    payload = tmpdir.join('payload')
    payload.write_binary(b'from disk\n')

    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_file(str(payload), '/NEW.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/NEW.;1')
    assert buf.getvalue() == b'from disk\n'
    iso2.close()

def test_new_in_place_editor_add_fp_rejects_udf(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1', udf_path='/old')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.add_fp(io.BytesIO(b'new\n'), 4, '/NEW.;1')
        assert 'UDF' in str(excinfo.value)

def test_new_in_place_editor_add_fp_rock_ridge_short_name(tmpdir):
    # Rock Ridge ISOs are supported as long as the SUSP fields fit
    # inside the directory record (i.e., no Continuation Entry block
    # needs to be allocated).  Short rr_name values comfortably fit.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1', rr_name='old')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_fp(io.BytesIO(b'new contents\n'), 13, '/NEW.;1', rr_name='new')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/NEW.;1')
    assert buf.getvalue() == b'new contents\n'
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, rr_path='/new')
    assert buf.getvalue() == b'new contents\n'
    iso2.close()

def test_new_in_place_editor_add_fp_rejects_rock_ridge_ce_required(tmpdir):
    # When the rr_name is long enough to push the SUSP fields out of
    # the directory record into a Continuation Entry block, in-place
    # add can't allocate the CE storage and must refuse.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1', rr_name='old')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.add_fp(io.BytesIO(b'x'), 1, '/NEW.;1', rr_name='a' * 200)
        assert 'Continuation Entry' in str(excinfo.value)

def test_new_in_place_editor_add_fp_rock_ridge_requires_rr_name(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1', rr_name='old')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
            ed.add_fp(io.BytesIO(b'new\n'), 4, '/NEW.;1')

def test_new_in_place_editor_add_fp_rejects_rr_name_on_non_rock_ridge(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/OLD.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
            ed.add_fp(io.BytesIO(b'new\n'), 4, '/NEW.;1', rr_name='new')

def test_new_in_place_editor_add_fp_rejects_eltorito(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'BOOT' * 512), 2048, '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.add_fp(io.BytesIO(b'new\n'), 4, '/NEW.;1')
        assert 'El Torito' in str(excinfo.value)

def test_new_in_place_editor_add_fp_rejects_parent_overflow(tmpdir):
    # Pack root with enough children that adding one more would
    # require a new extent.  Verify add_fp refuses cleanly with
    # "would overflow" messaging.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    # 49 short-name files exactly fill root's one-extent allocation
    # (under interchange level 1); the 50th forces overflow into a
    # second extent.  Once written to disk, in-place add can't grow
    # the parent extent, so adding any file after this point must
    # refuse.
    for i in range(49):
        iso.add_fp(io.BytesIO(b'x'), 1, f'/F{i:03d}.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.add_fp(io.BytesIO(b'one more\n'), 9, '/ZZZ.;1')
        assert 'overflow' in str(excinfo.value).lower()

def test_new_in_place_editor_mixed_workflow(tmpdir):
    # The point of InPlaceEditor: rm_file + modify_file + add_fp can
    # all be interleaved freely in a single session without the
    # silent-corruption failure mode that motivated the new class.
    # This mirrors the reporter's actual workflow on a Fedora-style
    # boot ISO -- minus the UDF/Rock-Ridge bits that the editor v1
    # doesn't yet support.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    iso.add_directory('/IMAGES', joliet_path='/images')
    iso.add_directory('/EFI', joliet_path='/EFI')
    iso.add_directory('/EFI/BOOT', joliet_path='/EFI/BOOT')
    iso.add_fp(io.BytesIO(b'OLD GRUB CFG'), 12, '/EFI/BOOT/GRUB.CFG;1',
               joliet_path='/EFI/BOOT/grub.cfg')
    iso.add_fp(io.BytesIO(b'install image bytes'), 19, '/IMAGES/INSTALL.IMG;1',
               joliet_path='/images/install.img')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/IMAGES/INSTALL.IMG;1')
        ed.modify_file(io.BytesIO(b'NEW GRUB CFG'), 12, '/EFI/BOOT/GRUB.CFG;1')
        ed.add_fp(io.BytesIO(b'kickstart payload'), 17, '/KS.CFG;1',
                  joliet_path='/ks.cfg')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    # GRUB.CFG has the new content.
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/EFI/BOOT/GRUB.CFG;1')
    assert buf.getvalue() == b'NEW GRUB CFG'
    # KS.CFG was added.
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/KS.CFG;1')
    assert buf.getvalue() == b'kickstart payload'
    # Via Joliet too.
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, joliet_path='/ks.cfg')
    assert buf.getvalue() == b'kickstart payload'
    # INSTALL.IMG is gone from both trees.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        iso2.get_file_from_iso_fp(io.BytesIO(), iso_path='/IMAGES/INSTALL.IMG;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        iso2.get_file_from_iso_fp(io.BytesIO(), joliet_path='/images/install.img')
    iso2.close()

def test_new_pycdlib_modify_file_in_place_warns(tmpdir):
    # PyCdlib.modify_file_in_place is the deprecated method-on-class
    # surface.  Verify it fires the DeprecationWarning that the
    # standalone-function and InPlaceEditor migrations should drive
    # users toward.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path, mode='rb+')
    with pytest.warns(DeprecationWarning, match='modify_file_in_place is deprecated'):
        iso2.modify_file_in_place(io.BytesIO(b'new\n'), 4, '/FOO.;1')
    iso2.close()

@uses_deprecated("modify_file_in_place")
def test_new_modify_file_in_place_unsorted_dir_records():
    # Regression test for https://github.com/clalancette/pycdlib/issues/122.
    # modify_file_in_place used to compute the on-disk byte offset of a
    # directory record from extents_to_here / offset_to_here -- both
    # derived from pycdlib's in-memory sorted order of children.  When
    # the actual on-disk order doesn't match (some writers don't emit
    # records strictly sorted), the write lands on the wrong byte range
    # and silently corrupts whatever sibling actually sat at that offset.
    # The fix rewrites the parent's full child list instead of trusting
    # the per-record offset.
    #
    # Construct the on-disk vs in-memory skew by building a sorted ISO
    # with three same-length-name files and swapping two of the records
    # in the bytes.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'AAA\n'), 4, '/AAA.;1')
    iso.add_fp(io.BytesIO(b'BBB\n'), 4, '/BBB.;1')
    iso.add_fp(io.BytesIO(b'CCC\n'), 4, '/CCC.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    root_extent = iso.pvd.root_dir_record.extent_location()
    iso.close()

    # Locate the AAA and BBB records inside the root directory extent
    # (layout: dot, dotdot, AAA, BBB, CCC) and swap their bytes so the
    # on-disk order becomes dot, dotdot, BBB, AAA, CCC.
    data = bytearray(out.getvalue())
    pos = root_extent * 2048
    pos += data[pos]   # skip dot
    pos += data[pos]   # skip dotdot
    aaa_pos = pos
    aaa_len = data[aaa_pos]
    bbb_pos = aaa_pos + aaa_len
    bbb_len = data[bbb_pos]
    assert(aaa_len == bbb_len)
    aaa_bytes = bytes(data[aaa_pos:aaa_pos + aaa_len])
    bbb_bytes = bytes(data[bbb_pos:bbb_pos + bbb_len])
    data[aaa_pos:aaa_pos + aaa_len] = bbb_bytes
    data[bbb_pos:bbb_pos + bbb_len] = aaa_bytes

    # Re-open the patched ISO and modify AAA in place.  pycdlib reads
    # records in on-disk order (BBB, AAA, CCC) but stores them sorted in
    # memory (AAA, BBB, CCC) -- the divergence that triggers the bug.
    fp = io.BytesIO(bytes(data))
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(fp)
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/AAA.;1')
    iso2.close()

    # All three files must still be readable with their expected contents.
    # Pre-fix, BBB or CCC would be corrupted by AAA's write hitting the
    # wrong byte range.
    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(fp)
    for path, expected in [('/AAA.;1', b'aaa\n'),
                           ('/BBB.;1', b'BBB\n'),
                           ('/CCC.;1', b'CCC\n')]:
        buf = io.BytesIO()
        iso3.get_file_from_iso_fp(buf, iso_path=path)
        assert(buf.getvalue() == expected)
    iso3.close()

@uses_deprecated("modify_file_in_place")
def test_new_rewrite_dir_record_extent_pads_after_rm():
    # Regression test for the zero-padding bug in
    # _rewrite_dir_record_extent.  Before the fix, the function wrote
    # the in-memory children list consecutively into the parent's
    # directory extent on disk but did not clear bytes past the new
    # last record.  After rm_file + modify_file_in_place in the same
    # parent, the post-rewrite extent retained the trailing bytes of
    # the removed record, which either failed the parser's
    # zero-padding check ("Invalid padding on ISO") or produced a
    # phantom record.
    #
    # Build a directory with several siblings, rm one, modify another,
    # then verify the ISO re-parses cleanly and the rm and modify both
    # took effect.
    iso = pycdlib.PyCdlib()
    iso.new()
    for name in ('AAA', 'BBB', 'CCC', 'DDD', 'EEE'):
        iso.add_fp(io.BytesIO((name + '\n').encode()), 4, f'/{name}.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    iso2.rm_file(iso_path='/CCC.;1')
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/AAA.;1')
    iso2.close()

    # Reopen and verify the ISO is well-formed.  Without the zero-pad
    # fix, this raises "Invalid padding on ISO".
    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out)
    # All remaining files should be present and rm'd file should be
    # absent.  Without the fix, a phantom record could synthesize an
    # unexpected entry here.
    children = sorted(
        ch.file_identifier()
        for ch in iso3.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    assert children == [b'AAA.;1', b'BBB.;1', b'DDD.;1', b'EEE.;1']
    for path, expected in [('/AAA.;1', b'aaa\n'),
                           ('/BBB.;1', b'BBB\n'),
                           ('/DDD.;1', b'DDD\n'),
                           ('/EEE.;1', b'EEE\n')]:
        buf = io.BytesIO()
        iso3.get_file_from_iso_fp(buf, iso_path=path)
        assert(buf.getvalue() == expected)
    iso3.close()

@uses_deprecated("modify_file_in_place")
def test_new_rewrite_dir_record_extent_pads_after_rm_multi_extent():
    # Same as the previous test but with a parent directory whose
    # children span multiple extents.  The rm is small enough that the
    # in-memory layout still occupies the same number of extents (i.e.,
    # data_length does not shrink), so the parser still expects to read
    # the full multi-extent span.  Without the zero-pad fix, the
    # trailing bytes of the last extent the rewrite touches contain
    # stale bytes from the removed record.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Each record at level-1 is roughly 40+ bytes with Rock Ridge off;
    # 60 children of similar names easily spill into a second extent.
    names = [f'F{i:03d}' for i in range(60)]
    for name in names:
        iso.add_fp(io.BytesIO((name + '\n').encode()), 5, f'/{name}.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    # Confirm the parent really does span >1 extent on disk.
    assert iso2.pvd.root_dir_record.data_length > 2048
    # Remove a child from the middle of the sort order and modify
    # another sibling.  The rewrite covers all of the original
    # data_length span, so the bug surfaces in whichever extent the
    # new last record lands in.
    iso2.rm_file(iso_path='/F030.;1')
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/F000.;1')
    iso2.close()

    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out)
    children = sorted(
        ch.file_identifier()
        for ch in iso3.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    expected = sorted(f'{name}.;1'.encode() for name in names if name != 'F030')
    assert children == expected
    # Spot-check the modified file and a few unmodified ones.
    buf = io.BytesIO()
    iso3.get_file_from_iso_fp(buf, iso_path='/F000.;1')
    assert buf.getvalue() == b'aaa\n'
    for name in ('F001', 'F029', 'F031', 'F059'):
        buf = io.BytesIO()
        iso3.get_file_from_iso_fp(buf, iso_path=f'/{name}.;1')
        assert buf.getvalue() == (name + '\n').encode()
    iso3.close()

@uses_deprecated("modify_file_in_place")
def test_new_rewrite_dir_record_extent_pads_across_extent_transition():
    # When _rewrite_dir_record_extent's serialized children pack
    # differently than the on-disk layout (e.g., because a child was
    # removed), the loop advances to a new extent partway through.
    # Without the fix, the trailing bytes of the previous extent are
    # left holding stale bytes from the on-disk layout.  This test
    # exercises that intermediate-extent-transition case specifically:
    # by removing an early-sorting child, the loop's transition point
    # shifts and the trailing bytes of the first extent must be
    # zero-padded.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Roughly 60 same-length children to span 2 extents; the rm of the
    # first one shifts where the loop transitions to extent 2.
    names = [f'F{i:03d}' for i in range(60)]
    for name in names:
        iso.add_fp(io.BytesIO((name + '\n').encode()), 5, f'/{name}.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    assert iso2.pvd.root_dir_record.data_length > 2048
    # Remove the first sortable child (after dot/dotdot) so every
    # subsequent record shifts to a lower byte offset, including the
    # boundary that decides which extent each record lands in.
    iso2.rm_file(iso_path='/F000.;1')
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/F059.;1')
    iso2.close()

    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out)
    children = sorted(
        ch.file_identifier()
        for ch in iso3.pvd.root_dir_record.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    expected = sorted(f'{name}.;1'.encode() for name in names if name != 'F000')
    assert children == expected
    buf = io.BytesIO()
    iso3.get_file_from_iso_fp(buf, iso_path='/F059.;1')
    assert buf.getvalue() == b'aaa\n'
    iso3.close()

@uses_deprecated("modify_file_in_place")
def test_new_modify_file_in_place_rewrites_grandparent_after_underflow():
    # When rm_file shrinks a parent's data_length via _remove_child's
    # underflow handler, the parent's on-disk directory record (stored
    # in the grandparent's extent) still has the original, larger
    # data_length.  Without the grandparent rewrite,
    # modify_file_in_place updates the parent's extent but leaves the
    # grandparent's record for the parent stale.  When the ISO is
    # re-parsed, the parser walks the parent's data using the stale
    # on-disk data_length and reads past the new in-memory layout into
    # the dropped extent's stale bytes, producing phantom records or
    # parse failures.
    #
    # Build a directory whose children span two extents, rm enough
    # children to trigger underflow (parent.data_length shrinks from
    # 2 extents to 1), modify a remaining sibling, and verify the
    # re-parsed ISO reflects the shrunken span -- no phantom records.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/DIR')
    # 60 children at level-1 ISO9660 spans roughly two extents.
    names = [f'F{i:03d}' for i in range(60)]
    for name in names:
        iso.add_fp(io.BytesIO((name + '\n').encode()), 5, f'/DIR/{name}.;1')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    dir_record = iso2._find_iso_record(b'/DIR')
    original_dir_data_length = dir_record.data_length
    assert original_dir_data_length > 2048
    # Removing 50 children drops the in-memory total well below one
    # extent, which fires _remove_child's underflow once and shrinks
    # parent.data_length by logical_block_size.
    for i in range(50):
        iso2.rm_file(iso_path=f'/DIR/F{i:03d}.;1')
    assert dir_record.data_length < original_dir_data_length
    # Modifying a remaining sibling exercises modify_file_in_place's
    # rewrite of parent (and now grandparent) extents on disk.
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/DIR/F059.;1')
    iso2.close()

    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out)
    dir_record3 = iso3._find_iso_record(b'/DIR')
    # The on-disk data_length for /DIR (read from root's extent) must
    # reflect the shrunken in-memory value.  Without the fix, this
    # still holds the original value and the parser reads stale bytes
    # from the dropped extent.
    assert dir_record3.data_length == dir_record.data_length
    # Exactly the surviving 10 children should be visible.
    remaining = [f'F{i:03d}' for i in range(50, 60)]
    children = sorted(
        ch.file_identifier()
        for ch in dir_record3.children
        if ch.file_identifier() not in (b'.', b'..')
    )
    assert children == sorted(f'{name}.;1'.encode() for name in remaining)
    buf = io.BytesIO()
    iso3.get_file_from_iso_fp(buf, iso_path='/DIR/F059.;1')
    assert buf.getvalue() == b'aaa\n'
    for name in ('F050', 'F055', 'F058'):
        buf = io.BytesIO()
        iso3.get_file_from_iso_fp(buf, iso_path=f'/DIR/{name}.;1')
        assert buf.getvalue() == (name + '\n').encode()
    iso3.close()

@uses_deprecated("modify_file_in_place")
def test_new_modify_file_in_place_rewrites_subdir_dotdots_after_underflow():
    # Companion to the grandparent rewrite test.  When _remove_child's
    # underflow handler shrinks parent.data_length, the in-memory
    # update also touches each subdirectory's dotdot record (because
    # dotdot.data_length carries the parent's size).  Those dotdot
    # records live in their respective subdirectories' own extents,
    # which modify_file_in_place doesn't otherwise touch.  Without the
    # subdir-dotdot rewrite, each subdirectory's on-disk dotdot field
    # is stale -- an internal inconsistency that pedantic ISO9660
    # validators flag even though no real parser uses dotdot's
    # data_length for navigation.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/PARENT')
    # SUBDIR is the subdirectory whose on-disk dotdot we'll inspect.
    iso.add_directory('/PARENT/SUBDIR')
    # Pack PARENT with enough file children to span two extents.
    names = [f'F{i:03d}' for i in range(60)]
    for name in names:
        iso.add_fp(io.BytesIO((name + '\n').encode()), 5, f'/PARENT/{name}.;1')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    parent = iso2._find_iso_record(b'/PARENT')
    original_data_length = parent.data_length
    assert original_data_length > 2048
    # Remove enough children to trigger _remove_child's underflow,
    # shrinking PARENT.data_length by one extent.
    for i in range(50):
        iso2.rm_file(iso_path=f'/PARENT/F{i:03d}.;1')
    assert parent.data_length < original_data_length
    # Modify a remaining sibling.  Without the dotdot rewrite,
    # PARENT/SUBDIR's on-disk dotdot still claims PARENT.data_length
    # is the original (larger) value.
    iso2.modify_file_in_place(io.BytesIO(b'aaa\n'), 4, '/PARENT/F059.;1')
    iso2.close()

    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out)
    parent3 = iso3._find_iso_record(b'/PARENT')
    subdir3 = iso3._find_iso_record(b'/PARENT/SUBDIR')
    # The dotdot (children[1]) is parsed from SUBDIR's on-disk extent;
    # its data_length should match the parent's actual data_length.
    assert subdir3.children[1].is_dotdot()
    assert subdir3.children[1].data_length == parent3.data_length
    iso3.close()

def test_new_update_file_contents_fp_basic():
    # update_file_contents_fp replaces a file's contents in memory and
    # the new content lands on disk via the next write_fp() call.
    # Unlike modify_file_in_place there is no extent-count constraint.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'original'), 8, '/FOO.;1')

    iso.update_file_contents_fp(io.BytesIO(b'updated content longer than original'), 36,
                                iso_path='/FOO.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
    assert buf.getvalue() == b'updated content longer than original'
    iso2.close()

def test_new_update_file_contents_fp_shorter_content():
    # Shrinking the content is fine -- write_fp recomputes the layout.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'A' * 5000), 5000, '/FOO.;1')

    iso.update_file_contents_fp(io.BytesIO(b'tiny'), 4, iso_path='/FOO.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
    assert buf.getvalue() == b'tiny'
    iso2.close()

def test_new_update_file_contents_fp_propagates_to_joliet_and_udf():
    # The shared Inode is what update_file_contents_fp swaps, so every
    # tree that linked the file (ISO9660 + Joliet + UDF here) sees the
    # new content automatically.  The caller only specifies one
    # lookup path.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09', udf='2.60')
    iso.add_fp(io.BytesIO(b'original'), 8, '/FOO.;1', rr_name='foo',
               joliet_path='/foo', udf_path='/foo')

    iso.update_file_contents_fp(io.BytesIO(b'updated'), 7, iso_path='/FOO.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    # Reads via every tree return the new content.
    for kwargs in ({'iso_path': '/FOO.;1'},
                   {'rr_path': '/foo'},
                   {'joliet_path': '/foo'},
                   {'udf_path': '/foo'}):
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, **kwargs)
        assert buf.getvalue() == b'updated', f'{kwargs} returned {buf.getvalue()!r}'
    iso2.close()

def test_new_update_file_contents_via_each_path_kwarg():
    # Each of iso_path / rr_path / joliet_path / udf_path is a valid
    # lookup for update_file_contents_fp on an ISO that has all three
    # extensions.
    for path_kwarg in ('iso_path', 'rr_path', 'joliet_path', 'udf_path'):
        iso = pycdlib.PyCdlib()
        iso.new(joliet=3, rock_ridge='1.09', udf='2.60')
        iso.add_fp(io.BytesIO(b'before'), 6, '/FOO.;1', rr_name='foo',
                   joliet_path='/foo', udf_path='/foo')
        lookup = {'iso_path': '/FOO.;1', 'rr_path': '/foo',
                  'joliet_path': '/foo', 'udf_path': '/foo'}[path_kwarg]
        iso.update_file_contents_fp(io.BytesIO(b'after'), 5, **{path_kwarg: lookup})

        out = io.BytesIO()
        iso.write_fp(out)
        iso.close()

        out.seek(0)
        iso2 = pycdlib.PyCdlib()
        iso2.open_fp(out)
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
        assert buf.getvalue() == b'after'
        iso2.close()

def test_new_update_file_contents_rejects_no_path():
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'x'), 1, '/FOO.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'y'), 1)
    assert 'Exactly one of' in str(excinfo.value)
    iso.close()

def test_new_update_file_contents_rejects_multiple_paths():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    iso.add_fp(io.BytesIO(b'x'), 1, '/FOO.;1', joliet_path='/foo')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'y'), 1,
                                    iso_path='/FOO.;1', joliet_path='/foo')
    assert 'Exactly one of' in str(excinfo.value)
    iso.close()

def test_new_update_file_contents_rejects_directory():
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/DIR')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'x'), 1, iso_path='/DIR')
    assert 'directory' in str(excinfo.value)
    iso.close()

def test_new_update_file_contents_rejects_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_symlink('/SYM.;1', rr_symlink_name='sym', rr_path='target')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'x'), 1, iso_path='/SYM.;1')
    assert 'symlink' in str(excinfo.value)
    iso.close()

def test_new_update_file_contents_rejects_not_initialized():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'x'), 1, iso_path='/FOO.;1')
    assert 'not initialized' in str(excinfo.value)

def test_new_update_file_contents_filename(tmpdir):
    # update_file_contents (filename variant) opens the file itself
    # and manages its lifetime, the same way add_file does relative
    # to add_fp.
    src = tmpdir.join('payload')
    src.write_binary(b'from a real file on disk')

    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'placeholder'), 11, '/FOO.;1')

    iso.update_file_contents(str(src), iso_path='/FOO.;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/FOO.;1')
    assert buf.getvalue() == b'from a real file on disk'
    iso2.close()

def test_new_update_file_contents_composes_with_add_rm_then_write_fp():
    # The reporter's actual workflow: open, do some mix of add_fp,
    # rm_file, update_file_contents_fp, then write_fp.
    # update_file_contents_fp is the supported alternative to
    # modify_file_in_place for that pattern.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')
    iso.add_directory('/ISOLINUX', rr_name='isolinux', joliet_path='/isolinux')
    iso.add_fp(io.BytesIO(b'OLD ISOLINUX CFG'), 16, '/ISOLINUX/ISOLINUX.CFG;1',
               rr_name='isolinux.cfg', joliet_path='/isolinux/isolinux.cfg')
    iso.add_fp(io.BytesIO(b'OLD GRUB'), 8, '/ISOLINUX/GRUB.CFG;1',
               rr_name='grub.cfg', joliet_path='/isolinux/grub.cfg')
    iso.add_fp(io.BytesIO(b'remove me'), 9, '/ISOLINUX/EXTRA.TXT;1',
               rr_name='extra.txt', joliet_path='/isolinux/extra.txt')

    seed = io.BytesIO()
    iso.write_fp(seed)
    iso.close()

    seed.seek(0)
    iso = pycdlib.PyCdlib()
    iso.open_fp(seed)
    iso.rm_file(iso_path='/ISOLINUX/EXTRA.TXT;1', rr_name='extra.txt',
                joliet_path='/isolinux/extra.txt')
    iso.update_file_contents_fp(io.BytesIO(b'NEW ISOLINUX'), 12,
                                iso_path='/ISOLINUX/ISOLINUX.CFG;1')
    iso.add_fp(io.BytesIO(b'kickstart'), 9, '/KS.CFG;1',
               rr_name='ks.cfg', joliet_path='/ks.cfg')
    iso.update_file_contents_fp(io.BytesIO(b'NEW GRUB'), 8,
                                joliet_path='/isolinux/grub.cfg')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    out.seek(0)
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    # The updated, added, and surviving files all read correctly.
    for path, expected in [('/ISOLINUX/ISOLINUX.CFG;1', b'NEW ISOLINUX'),
                           ('/ISOLINUX/GRUB.CFG;1',     b'NEW GRUB'),
                           ('/KS.CFG;1',                b'kickstart')]:
        buf = io.BytesIO()
        iso2.get_file_from_iso_fp(buf, iso_path=path)
        assert buf.getvalue() == expected, f'{path}: {buf.getvalue()!r}'
    # EXTRA.TXT is gone.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput):
        iso2.get_file_from_iso_fp(io.BytesIO(),
                                  iso_path='/ISOLINUX/EXTRA.TXT;1')
    iso2.close()

def test_new_udf_boot_descriptor_parsed():
    # Coverage for the UDF BOOT2 (Boot Descriptor) dispatch in
    # _parse_volume_descriptors.  pycdlib's writer doesn't emit BOOT2 on
    # its own, so build a real UDF ISO and overwrite the BEA01 extent
    # with a synthetic BOOT2 descriptor.  Re-open and verify the BOOT2
    # was parsed and stashed in iso.udf_boots.  (Replacing BEA01 also
    # disables the rest of the UDF parse path -- _has_udf is only set
    # when BEA01 is seen -- so we don't need the rest of the UDF
    # machinery to remain functional for this test.)
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', udf_path='/foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    # Bytes copied from the existing UDFBootDescriptor.parse unit test
    # in test_udf.py: structure_type=0, ident='BOOT2', version=1,
    # reserved1=0, then 32-byte architecture_type and boot_ident
    # (zero-init UDFEntityIDs), then boot_extent_loc/len/load/start (24
    # zero bytes), then a valid 12-byte UDFTimestamp, flags=0,
    # reserved2 = 32 zeros, boot_use = 1906 zeros.
    boot2 = (b'\x00BOOT2\x01\x00'
             + b'\x00' * 32
             + b'\x00' * 32
             + b'\x00' * 24
             + b'\x00\x00\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00'
             + b'\x00\x00'
             + b'\x00' * 32
             + b'\x00' * 1906)
    assert(len(boot2) == 2048)
    data = bytearray(out.getvalue())
    bea01_byte = data.find(b'BEA01')
    assert(bea01_byte >= 0)
    extent_start = (bea01_byte // 2048) * 2048
    data[extent_start:extent_start + 2048] = boot2

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(bytes(data)))
    assert(len(iso2.udf_boots) == 1)
    iso2.close()

def test_new_udf_creation_time_forces_efe_round_trip():
    # Regression test for https://github.com/clalancette/pycdlib/issues/94.
    # When the user supplies creation_time on add_directory/add_file for a
    # UDF path, pycdlib must emit an Extended File Entry (tag 266) for that
    # entry, since regular File Entries (tag 261) have no on-disk slot for
    # creation_time.  Round-trip the resulting ISO and verify the
    # creation_time, the EFE on-disk format, and that an unstamped child
    # mirrors its EFE parent.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    # An explicit creation_time forces EFE for /dir1.
    creation_secs = 1234567890.0
    iso.add_directory('/DIR1', udf_path='/dir1', creation_time=creation_secs)
    # No creation_time on this child -- it must mirror the EFE parent.
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', udf_path='/dir1/foo')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))

    # The root was created without creation_time, parent=None, so it
    # should still be a regular File Entry.
    assert(iso2.udf_root is not None)
    assert(type(iso2.udf_root) is pycdlib.udf.UDFFileEntry)
    assert(iso2.udf_root.desc_tag.tag_ident == 261)

    sub = iso2._find_udf_record(b'/dir1')[1]
    assert(isinstance(sub, pycdlib.udf.UDFExtendedFileEntry))
    assert(sub.desc_tag.tag_ident == 266)
    # creation_time round-tripped (granularity is whole seconds).
    assert(sub.creation_time.year == 2009)
    assert(sub.creation_time.month == 2)
    assert(sub.creation_time.day == 13)

    foo = iso2._find_udf_record(b'/dir1/foo')[1]
    # Mirroring: parent /dir1 is EFE, so /dir1/foo is EFE too even though
    # the caller didn't supply a creation_time for it.
    assert(isinstance(foo, pycdlib.udf.UDFExtendedFileEntry))
    assert(foo.desc_tag.tag_ident == 266)

    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, udf_path='/dir1/foo')
    assert(buf.getvalue() == b'foo\n')

    iso2.close()

def test_new_udf_no_creation_time_keeps_fe():
    # Sibling test: if no creation_time is supplied, every UDF entry stays
    # in the regular File Entry format (tag 261), matching the parent.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', udf_path='/foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    assert(type(iso2.udf_root) is pycdlib.udf.UDFFileEntry)
    sub = iso2._find_udf_record(b'/dir1')[1]
    assert(type(sub) is pycdlib.udf.UDFFileEntry)
    foo = iso2._find_udf_record(b'/foo')[1]
    assert(type(foo) is pycdlib.udf.UDFFileEntry)
    iso2.close()

def test_new_creation_time_no_compatible_storage_errors():
    # creation_time has nowhere to live on plain ISO9660 / Joliet (the DR
    # has no creation-time field), so passing it without RR or UDF raises.
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(b'x'), 1, '/X.;1', creation_time=0.0)
    assert('creation_time' in str(excinfo.value))
    iso.close()

def test_new_rock_ridge_creation_time_round_trip():
    # On a Rock Ridge ISO, creation_time should land in the TF record's
    # CREATION timestamp (bit 0).  Verify by re-opening and inspecting
    # the parsed RRTFRecord.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    creation_secs = 1234567890.0
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo',
               creation_time=creation_secs)
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    rec = iso2.get_record(rr_path='/foo')
    assert(rec.rock_ridge is not None)
    tf = rec.rock_ridge.dr_entries.tf_record
    if tf is None and rec.rock_ridge.ce_entries is not None:
        tf = rec.rock_ridge.ce_entries.tf_record
    assert(tf is not None)
    assert(tf.creation_time is not None)
    assert(tf.creation_time.years_since_1900 == 109)  # 2009
    assert(tf.creation_time.month == 2)
    assert(tf.creation_time.day_of_month == 13)
    iso2.close()

def test_new_add_symlink_creation_time_forces_efe():
    # add_symlink with creation_time on a UDF symlink path forces the
    # EFE format for the symlink's UDF File Entry.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_symlink(udf_symlink_path='/lnk', udf_target='target',
                    creation_time=1234567890.0)
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    rec = iso2._find_udf_record(b'/lnk')[1]
    assert(isinstance(rec, pycdlib.udf.UDFExtendedFileEntry))
    assert(rec.creation_time.year == 2009)
    iso2.close()

def test_new_add_hard_link_creation_time_round_trip_rr():
    # Rock Ridge hard links get their own DR (and own TF record) per link,
    # so creation_time on the new link round-trips cleanly without
    # disturbing the original DR.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/FOO2.;1',
                      rr_name='foo2', creation_time=1234567890.0)
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    rec = iso2.get_record(rr_path='/foo2')
    tf = rec.rock_ridge.dr_entries.tf_record
    if tf is None and rec.rock_ridge.ce_entries is not None:
        tf = rec.rock_ridge.ce_entries.tf_record
    assert(tf is not None)
    assert(tf.creation_time is not None)
    assert(tf.creation_time.years_since_1900 == 109)
    # The original link's DR keeps its default flags (no creation_time).
    rec_orig = iso2.get_record(rr_path='/foo')
    tf_orig = rec_orig.rock_ridge.dr_entries.tf_record
    if tf_orig is None and rec_orig.rock_ridge.ce_entries is not None:
        tf_orig = rec_orig.rock_ridge.ce_entries.tf_record
    assert(tf_orig is not None)
    assert(tf_orig.creation_time is None)
    iso2.close()

def test_new_add_hard_link_creation_time_udf_rejected():
    # UDF hard links share a single File Entry in pycdlib, so a per-link
    # creation_time can't be honored -- we must reject it.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', udf_path='/foo')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(udf_old_path='/foo', udf_new_path='/foo2',
                          creation_time=0.0)
    assert('UDF hard links' in str(excinfo.value))
    iso.close()

def test_new_add_directory_creation_time_no_storage_errors():
    # creation_time on add_directory must error if neither RR nor UDF can
    # store it.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory(joliet_path='/dir1', creation_time=0.0)
    assert('creation_time' in str(excinfo.value))
    iso.close()

def test_new_dir_subextent_data_length_opens():
    # Regression test: real-world ISOs (Windows XP / 2003 install media,
    # PS2 GT4) declare a directory data_length that ends inside an
    # extent, with the trailing partial extent zero-padded.  The parser
    # used to demand a *full* logical-block-sized run of zeros after a
    # zero-length DR, which fails when data_length runs out partway
    # through.  Build a small ISO, byte-patch root's data_length to
    # claim an extra 100 bytes that fall in the zero pad past the real
    # content, and check that re-opening still works.
    iso = pycdlib.PyCdlib()
    iso.new()
    # Force root into multiple extents so there's a zero-padded tail
    # past the last DR but still inside the directory's extents on
    # disk.  We can then patch root.data_length to claim 100 of those
    # zero bytes without colliding with file data.
    for i in range(80):
        name = '/F%03d.;1' % i
        iso.add_fp(io.BytesIO(b'x'), 1, name)
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    data = bytearray(out.getvalue())

    # PVD root_directory_record lives at offset 156 within the PVD
    # (extent 16).  DR layout: byte 0=dr_len, byte 1=xattr_len,
    # bytes 2-9=extent_le|extent_be, bytes 10-17=data_length_le|be.
    pvd_root_dr_off = 16 * 2048 + 156
    root_extent_le, _root_extent_be, root_data_length_le, _root_data_length_be = \
        struct.unpack_from('<LLLL', data, pvd_root_dr_off + 2)
    # Need root to span more than one extent so there's zero-pad space
    # past the last DR but before the next ISO descriptor.
    assert(root_data_length_le > 2048)
    assert(root_data_length_le % 2048 == 0)

    # Extend data_length by 100 bytes.  The 100 extra bytes need to be
    # zero -- they live in what would otherwise be the directory's
    # zero-pad tail past the last DR.  Force them to be zero (they
    # generally already are from pycdlib's writer, but being explicit
    # keeps the test stable against writer changes).
    extra = 100
    new_dl = root_data_length_le + extra
    pad_start = root_extent_le * 2048 + root_data_length_le
    for i in range(extra):
        data[pad_start + i] = 0

    def patch_data_length(off):
        struct.pack_into('<L', data, off + 10, new_dl)
        # The big-endian copy lives at offset+14, computed via swab.
        be = ((new_dl & 0xff) << 24) | ((new_dl & 0xff00) << 8) | \
             ((new_dl & 0xff0000) >> 8) | ((new_dl >> 24) & 0xff)
        struct.pack_into('<L', data, off + 14, be)

    # 1. PVD root DR.
    patch_data_length(pvd_root_dr_off)
    # 2. Root's dot DR (first DR at start of root extent).
    root_extent_off = root_extent_le * 2048
    patch_data_length(root_extent_off)
    # 3. Root's dotdot DR (second DR; for root's parent-is-self, this
    # also reports root's data_length).  Dot DR is dr_len=34.
    patch_data_length(root_extent_off + 34)

    # Verify it opens.
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(bytes(data)))
    # Sanity: round-trip through pycdlib once more to confirm we
    # didn't just paper over a parse error -- the rewritten ISO
    # should still be coherent.
    out2 = io.BytesIO()
    iso2.write_fp(out2)
    iso2.close()
    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(io.BytesIO(out2.getvalue()))
    iso3.close()

def test_new_walk_with_non_utf8_directory_name():
    # Regression test for https://github.com/clalancette/pycdlib/issues/109.
    # The 1.15.0 walk encoding work decoded the file/directory names that
    # walk() yields, but full_path_from_dirrecord still hardcoded UTF-8
    # for ISO9660 records and tripped UnicodeDecodeError when walk
    # recursed into a sub-directory whose on-disk name isn't UTF-8.
    # In addition, the descended walk() iteration used to look up the
    # directory via list_children(iso_path=relpath), which re-encoded
    # the path through hardcoded UTF-8 and failed to find the record.
    # Build a small ISO and byte-patch a directory's file_ident to be
    # the shift_jis bytes for the character 'せ' (which are *not* valid
    # UTF-8) to exercise both code paths.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/AA')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/AA/FOO.;1')
    out = io.BytesIO()
    iso.write_fp(out)
    root_extent = iso.pvd.root_dir_record.extent_location()
    iso.close()

    data = bytearray(out.getvalue())
    ext_off = root_extent * 2048
    pos = data.find(b'AA', ext_off, ext_off + 2048)
    assert(pos >= 0)
    data[pos:pos + 2] = b'\x82\xb9'  # shift_jis for 'せ'; not valid UTF-8

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(bytes(data)))
    walked = list(iso2.walk(iso_path='/', encoding='shift_jis'))
    assert(walked == [
        ('/', ['せ'], []),
        ('/せ', [], ['FOO.;1']),
    ])
    iso2.close()

def test_new_set_hidden_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1')
    iso.set_hidden('/AAAAAAAA.;1')

    do_a_test(iso, check_hidden_file)

    iso.close()

def test_new_set_hidden_dir():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    iso.set_hidden('/DIR1')

    do_a_test(iso, check_hidden_dir)

    iso.close()

def test_new_set_hidden_joliet_file():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', joliet_path='/aaaaaaaa')
    iso.set_hidden(joliet_path='/aaaaaaaa')

    do_a_test(iso, check_hidden_joliet_file)

    iso.close()

def test_new_set_hidden_joliet_dir():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')
    iso.set_hidden(joliet_path='/dir1')

    do_a_test(iso, check_hidden_joliet_dir)

    iso.close()

def test_new_set_hidden_rr_onefileonedir():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')
    iso.set_hidden(rr_path='/foo')

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.set_hidden(rr_path='/dir1')

    do_a_test(iso, check_rr_onefileonedir_hidden)

    iso.close()

def test_new_clear_hidden_joliet_file():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    iso.clear_hidden(joliet_path='/foo')

    do_a_test(iso, check_joliet_onefile)

    iso.close()

def test_new_clear_hidden_joliet_dir():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')
    iso.clear_hidden(joliet_path='/dir1')

    do_a_test(iso, check_joliet_onedir)

    iso.close()

def test_new_clear_hidden_rr_onefileonedir():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')
    iso.clear_hidden(rr_path='/foo')

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.clear_hidden(rr_path='/dir1')

    do_a_test(iso, check_rr_onefileonedir)

    iso.close()

def test_new_set_hidden_not_initialized():
    iso = pycdlib.PyCdlib()
    iso.new()

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1')
    iso.close()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.set_hidden('/AAAAAAAA.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_clear_hidden_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    iso.clear_hidden('/FOO.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_clear_hidden_dir():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    iso.clear_hidden('/DIR1')

    do_a_test(iso, check_onedir)

    iso.close()

def test_new_clear_hidden_not_initialized():
    iso = pycdlib.PyCdlib()
    iso.new()

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1')
    iso.close()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.clear_hidden('/AAAAAAAA.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_duplicate_rrmoved_name():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/A', rr_name='A')
    iso.add_directory('/A/B', rr_name='B')
    iso.add_directory('/A/B/C', rr_name='C')
    iso.add_directory('/A/B/C/D', rr_name='D')
    iso.add_directory('/A/B/C/D/E', rr_name='E')
    iso.add_directory('/A/B/C/D/E/F', rr_name='F')
    iso.add_directory('/A/B/C/D/E/F/G', rr_name='G')
    iso.add_directory('/A/B/C/D/E/F/G/1', rr_name='1')

    iso.add_directory('/A/B/C/D/E/F/H', rr_name='H')
    iso.add_directory('/A/B/C/D/E/F/H/1', rr_name='1')

    firststr = b'first\n'
    iso.add_fp(io.BytesIO(firststr), len(firststr), '/A/B/C/D/E/F/G/1/FIRST.;1', rr_name='first')

    secondstr = b'second\n'
    iso.add_fp(io.BytesIO(secondstr), len(secondstr), '/A/B/C/D/E/F/H/1/SECOND.;1', rr_name='second')

    do_a_test(iso, check_rr_two_dirs_same_level)

    iso.close()

def test_new_eltorito_hd_emul():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')

    do_a_test(iso, check_eltorito_hd_emul)

    iso.close()

def test_new_eltorito_hd_emul_too_short():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')
    assert(str(excinfo.value) == 'Could not read entire HD MBR, must be at least 512 bytes')

    iso.close()

def test_new_eltorito_hd_emul_bad_keybyte1():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x56' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')
    assert(str(excinfo.value) == 'Invalid magic on HD MBR')

    iso.close()

def test_new_eltorito_hd_emul_bad_keybyte2():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xab'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')
    assert(str(excinfo.value) == 'Invalid magic on HD MBR')

    iso.close()

def test_new_eltorito_hd_emul_multiple_part():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')
    assert(str(excinfo.value) == 'Boot image has multiple partitions')

    iso.close()

def test_new_eltorito_hd_emul_no_part():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')
    assert(str(excinfo.value) == 'Boot image has no partitions')

    iso.close()

def test_new_eltorito_hd_emul_bad_sec():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x00\x00\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')

    do_a_test(iso, check_eltorito_hd_emul_bad_sec)

    iso.close()

def test_new_eltorito_hd_emul_invalid_geometry():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul')

    do_a_test(iso, check_eltorito_hd_emul_invalid_geometry)

    iso.close()

def test_new_eltorito_hd_emul_not_bootable():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*446 + b'\x00\x01\x01\x00\x02\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*16 + b'\x00'*16 + b'\x00'*16 + b'\x55' + b'\xaa'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='hdemul', bootable=False)

    do_a_test(iso, check_eltorito_hd_emul_not_bootable)

    iso.close()

def test_new_eltorito_floppy12():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*(2400*512)
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='floppy', bootable=True)

    do_a_test(iso, check_eltorito_floppy12)

    iso.close()

def test_new_eltorito_floppy144():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*(2880*512)
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='floppy', bootable=True)

    do_a_test(iso, check_eltorito_floppy144)

    iso.close()

def test_new_eltorito_floppy288():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*(5760*512)
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='floppy', bootable=True)

    do_a_test(iso, check_eltorito_floppy288)

    iso.close()

def test_new_eltorito_bad_floppy():
    iso = pycdlib.PyCdlib()

    iso.new(interchange_level=1)

    bootstr = b'\x00'*(576*512)
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', media_name='floppy', bootable=True)
    assert(str(excinfo.value) == 'Invalid sector count for floppy media type; must be 2400, 2880, or 5760')

    iso.close()

def test_new_eltorito_multi_hidden():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    iso.rm_hard_link(iso_path='/boot2')

    do_a_test(iso, check_eltorito_multi_hidden)

    iso.close()

def test_new_eltorito_rr_verylongname():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot')

    iso.add_eltorito('/BOOT.;1', '/AAAAAAAA.;1', rr_bootcatname='a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_eltorito_rr_verylongname)

    iso.close()

def test_new_isohybrid_file_before():
    # Create a new ISO
    iso = pycdlib.PyCdlib()
    iso.new()
    # Add Eltorito
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4)
    # Now add the syslinux data
    iso.add_isohybrid()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    do_a_test(iso, check_isohybrid_file_before)

    iso.close()

def test_new_force_consistency_not_initialized():
    # Create a new ISO
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.force_consistency()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_eltorito_rr_joliet_verylongname():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)
    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', rr_name='boot', joliet_path='/boot')

    iso.add_eltorito('/BOOT.;1', '/AAAAAAAA.;1', rr_bootcatname='a'*RR_MAX_FILENAME_LENGTH, joliet_bootcatfile='/'+'a'*64)

    do_a_test(iso, check_eltorito_rr_joliet_verylongname)

    iso.close()

def test_new_joliet_dirs_overflow_ptr_extent():
    numdirs = 216

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    for i in range(1, 1+numdirs):
        iso.add_directory('/DIR%d' % i, joliet_path='/dir%d' % i)

    do_a_test(iso, check_joliet_dirs_overflow_ptr_extent)

    iso.close()

def test_new_joliet_dirs_just_short_ptr_extent():
    numdirs = 215

    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    for i in range(1, 1+numdirs):
        iso.add_directory('/DIR%d' % i, joliet_path='/dir%d' % i)

    do_a_test(iso, check_joliet_dirs_just_short_ptr_extent)

    iso.close()

def test_new_joliet_rm_large_directory():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    for i in range(1, 50):
        iso.add_directory('/DIR%d' % i, joliet_path='/dir%d' % i)

    for i in range(1, 50):
        iso.rm_directory('/DIR%d' % i, joliet_path='/dir%d' % i)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_overflow_root_dir_record():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    for letter in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'o'):
        thisstr = b'\n'
        iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/'+letter.upper()*7+'.;1', rr_name=letter*20, joliet_path='/'+letter*20)

    do_a_test(iso, check_overflow_root_dir_record)

    iso.close()

def test_new_overflow_correct_extents():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    thisstr = b'\n'
    for letter in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n'):
        iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/'+letter.upper()*8+'.;1', rr_name=letter*136, joliet_path='/'+letter*64)

    iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/OOOOOOOO.;1', rr_name='o'*57, joliet_path='/'+'o'*57)

    iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/P.;1', rr_name='p', joliet_path='/p')

    do_a_test(iso, check_overflow_correct_extents)

    iso.close()

def test_new_overflow_correct_extents2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    thisstr = b'\n'

    iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/P.;1', rr_name='p', joliet_path='/p')

    iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/OOOOOOOO.;1', rr_name='o'*57, joliet_path='/'+'o'*57)

    for letter in ('n', 'm', 'l', 'k', 'j', 'i', 'h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'):
        iso.add_fp(io.BytesIO(thisstr), len(thisstr), '/'+letter.upper()*8+'.;1', rr_name=letter*136, joliet_path='/'+letter*64)

    do_a_test(iso, check_overflow_correct_extents)

    iso.close()

def test_new_duplicate_deep_dir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    iso.add_directory('/BOOKS', rr_name='books', joliet_path='/books')
    iso.add_directory('/BOOKS/LKHG', rr_name='lkhg', joliet_path='/books/lkhg')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW', rr_name='HyperNews', joliet_path='/books/lkhg/HyperNews')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET', rr_name='get', joliet_path='/books/lkhg/HyperNews/get')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/FS', rr_name='fs', joliet_path='/books/lkhg/HyperNews/get/fs')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/FS/FS', rr_name='fs', joliet_path='/books/lkhg/HyperNews/get/fs/fs')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/FS/FS/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/fs/fs/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG', rr_name='khg', joliet_path='/books/lkhg/HyperNews/get/khg')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/117', rr_name='117', joliet_path='/books/lkhg/HyperNews/get/khg/117')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/117/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/117/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/117/1/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/117/1/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/117/1/1/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/117/1/1/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/117/1/1/1/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/117/1/1/1/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/35', rr_name='35', joliet_path='/books/lkhg/HyperNews/get/khg/35')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/35/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/35/1')
    iso.add_directory('/BOOKS/LKHG/HYPERNEW/GET/KHG/35/1/1', rr_name='1', joliet_path='/books/lkhg/HyperNews/get/khg/35/1/1')

    do_a_test(iso, check_duplicate_deep_dir)

    iso.close()

def test_new_always_consistent():
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new(joliet=3)

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_hard_link(joliet_path='/foo')

    iso.add_directory('/DIR1', joliet_path='/dir1')

    iso.rm_hard_link(iso_path='/FOO.;1')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_file('/FOO.;1', joliet_path='/foo')

    iso.rm_directory('/DIR1', joliet_path='/dir1')

    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    iso.rm_eltorito()

    do_a_test(iso, check_joliet_onefile)

    iso.close()

def test_new_remove_eighth_dir():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', rr_name='dir8')

    iso.rm_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8', rr_name='dir8')

    do_a_test(iso, check_sevendeepdirs)

    iso.close()

def test_new_joliet_level_1():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=1)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_level_2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=2)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_level_3():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_joliet_invalid_level():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(joliet=4)
    assert(str(excinfo.value) == 'Invalid Joliet level; must be 1, 2, or 3')

def test_new_duplicate_pvd_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.duplicate_pvd()

    do_a_test(iso, check_duplicate_pvd)

    iso.close()

def test_new_rr_symlink_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    do_a_test(iso, check_rr_symlink)

    iso.close()

def test_new_eltorito_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_eltorito_nofiles)

    iso.close()

def test_new_joliet_false():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=False)

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_joliet_true():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=True)

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_eltorito_multi_boot_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    do_a_test(iso, check_eltorito_multi_boot)

    iso.close()

def test_new_rm_joliet_hard_link():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_hard_link(joliet_path='/foo')

    do_a_test(iso, check_onefile_joliet_no_file)

    iso.close()

@uses_deprecated("add_joliet_directory")
def test_new_add_joliet_directory_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_joliet_directory('/foo')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

@uses_deprecated("add_joliet_directory")
def test_new_add_joliet_directory():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1')
    iso.add_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_onedir)

    iso.close()

@uses_deprecated("add_joliet_directory")
def test_new_add_joliet_directory_isolevel4():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, joliet=3)
    # Add new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/foo', joliet_path='/foo')
    # Add new directory.
    iso.add_directory('/dir1')
    iso.add_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_isolevel4)

    iso.close()

@uses_deprecated("add_joliet_directory")
def test_new_add_joliet_directory_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new(joliet=3)

    iso.add_directory('/DIR1')
    iso.add_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_onedir)

    iso.close()

@uses_deprecated("rm_joliet_directory")
def test_new_rm_joliet_directory():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    iso.rm_directory('/DIR1')
    iso.rm_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

@uses_deprecated("rm_joliet_directory")
def test_new_rm_joliet_directory_not_initialized():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_joliet_directory('/dir1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

@uses_deprecated("rm_joliet_directory")
def test_new_rm_joliet_directory_always_consistent():
    # Create a new ISO.
    iso = pycdlib.PyCdlib(always_consistent=True)
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    iso.rm_directory('/DIR1')
    iso.rm_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

@uses_deprecated("rm_joliet_directory")
def test_new_rm_joliet_directory_iso_level4():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    iso.rm_directory('/DIR1')
    iso.rm_joliet_directory('/dir1')

    do_a_test(iso, check_joliet_isolevel4_nofiles)

    iso.close()

def test_new_deep_rr_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a large directory structure.
    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/DIR2', rr_name='dir2')
    iso.add_directory('/DIR1/DIR2/DIR3', rr_name='dir3')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4', rr_name='dir4')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5', rr_name='dir5')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6', rr_name='dir6')
    iso.add_directory('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7', rr_name='dir7')

    iso.add_symlink('/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/SYM.;1', 'sym', '/usr/share/foo')

    do_a_test(iso, check_deep_rr_symlink)

    iso.close()

def test_new_rr_deep_weird_layout():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/ASTROID', rr_name='astroid')
    iso.add_directory('/ASTROID/ASTROID', rr_name='astroid')
    iso.add_directory('/ASTROID/ASTROID/TESTS', rr_name='tests')
    iso.add_directory('/ASTROID/ASTROID/TESTS/TESTDATA', rr_name='testdata')
    iso.add_directory('/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3', rr_name='python3')
    iso.add_directory('/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA', rr_name='data')
    iso.add_directory('/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP', rr_name='absimp')
    iso.add_directory('/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP/SIDEPACK', rr_name='sidepackage')

    strstr = b'from __future__ import absolute_import, print_functino\nimport string\nprint(string)\n'
    iso.add_fp(io.BytesIO(strstr), len(strstr), '/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP/STRING.PY;1', rr_name='string.py')

    initstr = b'"""a side package with nothing in it\n"""\n'
    iso.add_fp(io.BytesIO(initstr), len(initstr), '/ASTROID/ASTROID/TESTS/TESTDATA/PYTHON3/DATA/ABSIMP/SIDEPACK/__INIT__.PY;1', rr_name='__init__.py')

    do_a_test(iso, check_rr_deep_weird_layout)

    iso.close()

def test_new_rr_long_dir_name():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/AAAAAAAA', rr_name='a'*248)

    do_a_test(iso, check_rr_long_dir_name)

    iso.close()

def test_new_rr_out_of_order_ce():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_symlink('/SYM.;1', 'sym', '/'.join(['a'*RR_MAX_FILENAME_LENGTH, 'b'*RR_MAX_FILENAME_LENGTH, 'c'*RR_MAX_FILENAME_LENGTH, 'd'*RR_MAX_FILENAME_LENGTH, 'e'*RR_MAX_FILENAME_LENGTH]))
    iso.add_directory('/AAAAAAAA', rr_name='a'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_out_of_order_ce)

    iso.close()

def test_new_rr_ce_removal():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/AAAAAAAA', rr_name='a'*RR_MAX_FILENAME_LENGTH)
    iso.add_directory('/BBBBBBBB', rr_name='b'*RR_MAX_FILENAME_LENGTH)
    iso.add_directory('/CCCCCCCC', rr_name='c'*RR_MAX_FILENAME_LENGTH)
    iso.add_directory('/DDDDDDDD', rr_name='d'*RR_MAX_FILENAME_LENGTH)

    iso.rm_directory('/CCCCCCCC', rr_name='c'*RR_MAX_FILENAME_LENGTH)

    iso.add_directory('/EEEEEEEE', rr_name='e'*RR_MAX_FILENAME_LENGTH)

    do_a_test(iso, check_rr_ce_removal)

    iso.close()

def test_new_duplicate_pvd_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.duplicate_pvd()

    do_a_test(iso, check_duplicate_pvd_joliet)

    iso.close()

def test_new_write_fp_not_binary(tmpdir):
    # Create a new ISO.
    iso = pycdlib.PyCdlib()

    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        with open(os.path.join(str(tmpdir), 'out.iso'), 'w') as outfp:
            iso.write_fp(outfp)
    assert(str(excinfo.value) == "The file to write out must be in binary mode (add 'b' to the open flags)")

    iso.close()

def test_new_add_directory_no_path():
    iso = pycdlib.PyCdlib()

    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory()
    assert(str(excinfo.value) == 'Either iso_path or joliet_path must be passed')

    iso.close()

def test_new_add_directory_joliet_only():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1')
    iso.add_directory(joliet_path='/dir1')

    do_a_test(iso, check_joliet_onedir)

    iso.close()

def test_new_rm_directory_no_path():
    iso = pycdlib.PyCdlib()

    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_directory()
    assert(str(excinfo.value) == 'Either iso_path or joliet_path must be passed')

    iso.close()

@uses_deprecated("add_joliet_directory")
def test_new_rm_directory_joliet_only():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_joliet_directory(joliet_path='/dir1')
    iso.rm_directory(joliet_path='/dir1')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

@uses_deprecated("get_and_write_fp")
def test_new_get_and_write_dir():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_and_write_fp('/DIR1', out)
    assert(str(excinfo.value) == 'Cannot write out a directory')

    iso.close()

@uses_deprecated("get_and_write_fp")
def test_new_get_and_write_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    iso.get_and_write_fp('/foo', out)
    assert(out.getvalue() == b'foo\n')

    iso.close()

@uses_deprecated("get_and_write_fp")
def test_new_get_and_write_iso9660():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    iso.get_and_write_fp('/FOO.;1', out)
    assert(out.getvalue() == b'foo\n')

    iso.close()

@uses_deprecated("get_and_write_fp")
def test_new_get_and_write_rr():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    out = io.BytesIO()
    iso.get_and_write_fp('/foo', out)
    assert(out.getvalue() == b'foo\n')

    iso.close()

@uses_deprecated("get_and_write_fp")
def test_new_get_and_write_iso9660_no_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_and_write_fp('/BAR.;1', out)
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_get_record_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_record()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_record_invalid_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_record(foo='bar')
    assert(str(excinfo.value) == "Invalid keyword, must be one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_get_record_multiple_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_record(iso_path='/bar', joliet_path='/bar')
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_get_record_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    rec = iso.get_record(joliet_path='/dir1')

    assert(rec.file_identifier().decode('utf-16_be') == 'dir1')
    assert(len(rec.children) == 2)

    iso.close()

def test_new_get_record_iso_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')

    rec = iso.get_record(iso_path='/DIR1')

    assert(rec.file_identifier() == b'DIR1')
    assert(len(rec.children) == 2)

    iso.close()

def test_new_get_record_rr_path():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')

    rec = iso.get_record(rr_path='/dir1')

    assert(rec.file_identifier() == b'DIR1')
    assert(len(rec.children) == 2)
    assert(rec.rock_ridge.name() == b'dir1')

    iso.close()

def test_new_different_joliet_name():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', joliet_path='/bar')

    foojstr = b'foojoliet\n'
    iso.add_fp(io.BytesIO(foojstr), len(foojstr), '/FOOJ.;1', rr_name='fooj', joliet_path='/foo')

    do_a_test(iso, check_joliet_different_names)

    # Check that we can get the content for the first file using its various names
    out = io.BytesIO()
    iso.get_file_from_iso_fp(out, iso_path='/FOO.;1')
    assert(out.getvalue() == b'foo\n')

    out2 = io.BytesIO()
    iso.get_file_from_iso_fp(out2, rr_path='/foo')
    assert(out2.getvalue() == b'foo\n')

    out3 = io.BytesIO()
    iso.get_file_from_iso_fp(out3, joliet_path='/bar')
    assert(out3.getvalue() == b'foo\n')

    # Check that we can get the content for the second file using its various names
    out4 = io.BytesIO()
    iso.get_file_from_iso_fp(out4, iso_path='/FOOJ.;1')
    assert(out4.getvalue() == b'foojoliet\n')

    out5 = io.BytesIO()
    iso.get_file_from_iso_fp(out5, rr_path='/fooj')
    assert(out5.getvalue() == b'foojoliet\n')

    out6 = io.BytesIO()
    iso.get_file_from_iso_fp(out6, joliet_path='/foo')
    assert(out6.getvalue() == b'foojoliet\n')

    iso.close()

def test_new_different_rr_isolevel4_name():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/foo', rr_name='bar')

    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/bar', rr_name='foo')

    out = io.BytesIO()
    iso.get_file_from_iso_fp(out, iso_path='/foo')
    assert(out.getvalue() == b'foo\n')

    out2 = io.BytesIO()
    iso.get_file_from_iso_fp(out2, rr_path='/bar')
    assert(out2.getvalue() == b'foo\n')

    iso.close()

def test_new_get_file_from_iso_fp_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp('foo')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_file_from_iso_fp_invalid_keyword():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp('junk', foo='bar')
    assert(str(excinfo.value) == 'Unknown keyword foo')

def test_new_get_file_from_iso_fp_too_many_args():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp('junk', iso_path='/bar', rr_path='/bar')
    assert(str(excinfo.value) == "Exactly one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path' must be passed")

def test_new_list_children_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children():
            pass
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_list_children_too_few_args():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children():
            pass
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_list_children_too_many_args():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children(iso_path='/foo', rr_path='/bar'):
            pass
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_list_children_invalid_arg():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children(foo='bar'):
            pass
    assert(str(excinfo.value) == "Invalid keyword, must be one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_list_children_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory(joliet_path='/dir1')

    for index,c in enumerate(iso.list_children(joliet_path='/')):
        if index == 2:
            assert(c.file_identifier() == 'dir1'.encode('utf-16_be'))

    assert(index == 2)

    iso.close()

def test_new_list_children_rr():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory(iso_path='/DIR1', rr_name='dir1')

    for index,c in enumerate(iso.list_children(rr_path='/')):
        if index == 2:
            assert(c.file_identifier() == b'DIR1')
            assert(c.rock_ridge.name() == b'dir1')

    assert(index == 2)

    iso.close()

def test_new_list_children():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory(iso_path='/DIR1')

    for index,c in enumerate(iso.list_children(iso_path='/')):
        if index == 2:
            assert(c.file_identifier() == b'DIR1')

    assert(index == 2)

    iso.close()

@uses_deprecated("list_dir")
def test_new_list_dir_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')

    for index,c in enumerate(iso.list_dir('/', joliet=True)):
        if index == 2:
            assert(c.file_identifier() == 'dir1'.encode('utf-16_be'))

    assert(index == 2)

    iso.close()

def test_new_get_file_from_iso_invalid_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, iso_path='/FOO.;1/BAR.;1')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_get_file_from_iso_invalid_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, joliet_path='/foo/bar')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_get_file_from_iso_joliet_path_not_absolute():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, joliet_path='foo')
    assert(str(excinfo.value) == 'Must be a path starting with /')

    iso.close()

def test_new_get_file_from_iso_joliet_path_not_found():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, joliet_path='/bar')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_get_file_from_iso_blocksize():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    out = io.BytesIO()
    iso.get_file_from_iso_fp(out, joliet_path='/foo', blocksize=16384)

    assert(out.getvalue() == b'foo\n')

    iso.close()

def test_new_get_file_from_iso_no_joliet():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, joliet_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a joliet_path from a non-Joliet ISO')

    iso.close()

def test_new_get_file_from_iso_no_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, rr_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')

    iso.close()

def test_new_set_hidden_no_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.set_hidden()
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, rr_path, or joliet_path')

    iso.close()

def test_new_clear_hidden_no_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.clear_hidden()
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, rr_path, or joliet_path')

    iso.close()

def test_new_set_hidden_too_many_paths():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', joliet_path='/aaaaaaaa')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.set_hidden(iso_path='/AAAAAAAA.;1', joliet_path='/aaaaaaaa')
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, rr_path, or joliet_path')

    iso.close()

def test_new_clear_hidden_too_many_paths():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    aastr = b'aa\n'
    iso.add_fp(io.BytesIO(aastr), len(aastr), '/AAAAAAAA.;1', joliet_path='/aaaaaaaa')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.clear_hidden(iso_path='/AAAAAAAA.;1', joliet_path='/aaaaaaaa')
    assert(str(excinfo.value) == 'Must provide exactly one of iso_path, rr_path, or joliet_path')

    iso.close()

def test_new_add_directory_with_mode():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory(iso_path='/DIR1', file_mode=0o040555)
    assert(str(excinfo.value) == 'A file mode can only be specified for Rock Ridge ISOs')

    iso.close()

def test_new_full_path_from_dirrecord_root():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    fullpath = iso.full_path_from_dirrecord(iso.pvd.root_directory_record())
    assert(fullpath == '/')

    iso.close()

def test_new_full_path_rockridge():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory(iso_path='/DIR1', rr_name='dir1')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/DIR1/BOOT.;1', rr_name='boot')

    full_path = None
    for child in iso.list_children(rr_path='/dir1'):
        if child.file_identifier() == b'BOOT.;1':
            full_path = iso.full_path_from_dirrecord(child, rockridge=True)
            assert(full_path == '/dir1/boot')
            break

    assert(full_path is not None)
    iso.close()

def test_new_list_children_joliet_subdir():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory(iso_path='/DIR1', joliet_path='/dir1')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/DIR1/BOOT.;1', joliet_path='/dir1/boot')

    full_path = None
    for child in iso.list_children(joliet_path='/dir1'):
        if child.file_identifier() == 'boot'.encode('utf-16_be'):
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/dir1/boot')
            break

    assert(full_path is not None)
    iso.close()

def test_new_joliet_encoded_system_identifier():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, joliet=3, rock_ridge='1.09', sys_ident='LINUX', vol_ident='cidata')

    user_data_str = b'''\
#cloud-config
password: password
chpasswd: { expire: False }
ssh_pwauth: True
'''
    iso.add_fp(io.BytesIO(user_data_str), len(user_data_str), '/user-data', rr_name='user-data', joliet_path='/user-data')

    meta_data_str = b'''\
local-hostname: cloudimg
'''
    iso.add_fp(io.BytesIO(meta_data_str), len(meta_data_str), '/meta-data', rr_name='meta-data', joliet_path='/meta-data')

    do_a_test(iso, check_joliet_ident_encoding)

    iso.close()

def test_new_duplicate_pvd_isolevel4():
    # 51200 without interchange_level 4, without duplicate_pvd
    # 53248 without interchange level 4, with duplicate pvd
    # 55296 with interchange level 4, with duplicate pvd
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.duplicate_pvd()

    do_a_test(iso, check_duplicate_pvd_isolevel4)

    iso.close()

def test_new_joliet_hidden_iso_file():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_joliet_hidden_iso_file)

    iso.close()

def test_new_add_file_hard_link_rm_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/LINK.;1')

    iso.rm_file('/FOO.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_file_mode_not_rock_ridge():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', file_mode=0o0100444)
    assert(str(excinfo.value) == 'Can only specify a file mode for Rock Ridge ISOs')

    iso.close()

def test_new_eltorito_hide_boot_link():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_hard_link(iso_old_path='/BOOT.;1', iso_new_path='/BOOTLINK.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_hard_link(iso_path='/BOOT.;1')

    do_a_test(iso, check_eltorito_bootlink)

    iso.close()

def test_new_iso_only_add_rm_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    iso.rm_hard_link('/BAR.;1')

    iso.rm_file('/FOO.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_rm_hard_link_twice():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    iso.rm_hard_link(iso_path='/BAR.;1')
    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_rm_hard_link_twice2():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    iso.rm_hard_link(iso_path='/FOO.;1')
    iso.rm_hard_link(iso_path='/BAR.;1')

    do_a_test(iso, check_nofiles)

    iso.close()

def test_new_rm_eltorito_leave_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    iso.rm_eltorito()

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_add_eltorito_rm_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')

    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file('/BOOT.;1')
    assert(str(excinfo.value) == "Cannot remove a file that is referenced by El Torito; use 'rm_eltorito' to remove El Torito, or use 'rm_hard_link' to hide the entry")

    iso.close()

def test_new_eltorito_multi_boot_rm_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file('/boot2')
    assert(str(excinfo.value) == "Cannot remove a file that is referenced by El Torito; use 'rm_eltorito' to remove El Torito, or use 'rm_hard_link' to hide the entry")

    iso.close()

def test_new_get_file_from_iso_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    out = io.BytesIO()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, iso_path='/SYM.;1')
    assert(str(excinfo.value) == 'Symlinks have no data associated with them')

    iso.close()

def test_new_udf_nofiles():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    do_a_test(iso, check_udf_nofiles)

    iso.close()

def test_new_get_file_byte_extents():
    # Regression test for https://github.com/clalancette/pycdlib/issues/104.
    # Build an ISO9660+UDF image with a single small file, write it out, and
    # verify get_file_byte_extents returns offsets that, when read directly
    # from the on-disk image, contain exactly the file's bytes -- exercising
    # both the iso_path and udf_path lookup paths.
    payload = b'kernel-payload-bytes'
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(payload), len(payload), '/FOO.;1', udf_path='/foo')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    out.seek(0)
    iso2.open_fp(out)
    raw = out.getvalue()

    iso_extents = iso2.get_file_byte_extents(iso_path='/FOO.;1')
    assert(len(iso_extents) == 1)
    iso_off, iso_len = iso_extents[0]
    assert(iso_len == len(payload))
    assert(raw[iso_off:iso_off + iso_len] == payload)

    udf_extents = iso2.get_file_byte_extents(udf_path='/foo')
    assert(len(udf_extents) == 1)
    udf_off, udf_len = udf_extents[0]
    assert(udf_len == len(payload))
    assert(raw[udf_off:udf_off + udf_len] == payload)

    # Both views should resolve to the same on-disk bytes (linked Inodes).
    assert(iso_extents == udf_extents)

    iso2.close()

def test_new_udf_custom_vol_ident():
    # Regression test for https://github.com/clalancette/pycdlib/issues/40.
    # vol_ident passed to PyCdlib.new() must propagate to the UDF identifier
    # fields, not just the ISO9660 PVD.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60', vol_ident='MYDISK')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    out.seek(0)
    iso2.open_fp(out)

    expected_32 = b'\x08MYDISK' + b'\x00' * 24 + b'\x07'
    expected_128 = b'\x08MYDISK' + b'\x00' * 120 + b'\x07'

    assert(iso2.pvd.volume_identifier.rstrip() == b'MYDISK')
    assert(iso2.udf_main_descs.pvds[0].vol_ident == expected_32)
    assert(iso2.udf_main_descs.impl_use[0].impl_use.log_vol_ident == expected_128)
    assert(iso2.udf_main_descs.logical_volumes[0].logical_vol_ident == expected_128)
    assert(iso2.udf_reserve_descs.pvds[0].vol_ident == expected_32)
    assert(iso2.udf_reserve_descs.impl_use[0].impl_use.log_vol_ident == expected_128)
    assert(iso2.udf_reserve_descs.logical_volumes[0].logical_vol_ident == expected_128)
    assert(iso2.udf_file_set.log_vol_ident == expected_128)
    assert(iso2.udf_file_set.file_set_ident == expected_32)

    iso2.close()

def test_new_udf_onedir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    do_a_test(iso, check_udf_onedir)

    iso.close()

def test_new_udf_twodirs():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.add_directory('/DIR2', udf_path='/dir2')

    do_a_test(iso, check_udf_twodirs)

    iso.close()

def test_new_udf_subdir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.add_directory('/DIR1/SUBDIR1', udf_path='/dir1/subdir1')

    do_a_test(iso, check_udf_subdir)

    iso.close()

def test_new_udf_subdir_odd():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.add_directory('/DIR1/SUBDI1', udf_path='/dir1/subdi1')

    do_a_test(iso, check_udf_subdir_odd)

    iso.close()

def test_new_udf_rm_directory():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.rm_directory('/DIR1', udf_path='/dir1')

    do_a_test(iso, check_udf_nofiles)

    iso.close()

def test_new_udf_onefile():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    do_a_test(iso, check_udf_onefile)

    iso.close()

def test_new_udf_onefileonedir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    do_a_test(iso, check_udf_onefileonedir)

    iso.close()

def test_new_udf_rm_file():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.rm_file('/FOO.;1', udf_path='/foo')

    do_a_test(iso, check_udf_nofiles)

    iso.close()

def test_new_udf_dir_spillover():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    for i in range(ord('a'), ord('v')):
        iso_dirname = '/' + chr(i).upper() * 8
        udf_dirname = '/' + chr(i) * 64
        iso.add_directory(iso_dirname, udf_path=udf_dirname)

    do_a_test(iso, check_udf_dir_spillover)

    iso.close()

def test_new_udf_dir_oneshort():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    for i in range(ord('a'), ord('u')):
        iso_dirname = '/' + chr(i).upper() * 8
        udf_dirname = '/' + chr(i) * 64
        iso.add_directory(iso_dirname, udf_path=udf_dirname)

    do_a_test(iso, check_udf_dir_oneshort)

    iso.close()

def test_new_udf_iso_hidden():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.rm_hard_link(iso_path='/FOO.;1')

    do_a_test(iso, check_udf_iso_hidden)

    iso.close()

def test_new_udf_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', udf_new_path='/foo')

    do_a_test(iso, check_udf_onefile)

    iso.close()

def test_new_udf_rm_add_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.rm_hard_link(iso_path='/FOO.;1')

    iso.add_hard_link(udf_old_path='/foo', iso_new_path='/FOO.;1')

    do_a_test(iso, check_udf_onefile)

    iso.close()

def test_new_udf_hidden():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.rm_hard_link(udf_path='/foo')

    do_a_test(iso, check_udf_hidden)

    iso.close()

@pytest.mark.slow
def test_new_very_largefile(tmpdir):
    indir = tmpdir.mkdir('verylarge')
    largefile = os.path.join(str(indir), 'bigfile')

    with open(largefile, 'w') as outfp:
        outfp.truncate(5*1024*1024*1024)  # 5 GB

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3)

    # Add a new file.
    iso.add_file(largefile, '/BIGFILE.;1')

    full_path = None
    num_children = 0
    for child in iso.list_children(iso_path='/'):
        if child.file_identifier() == b'BIGFILE.;1':
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/BIGFILE.;1')
        num_children += 1

    assert(full_path is not None)
    assert(num_children == 3)

    do_a_test(iso, check_very_largefile, tmpdir)

    iso.close()

@pytest.mark.slow
def test_new_six_gb_file(tmpdir):
    # An issue was found where any files larger than 6442444800 bytes couldn't
    # be extracted with pycdlib.  This test ensures that that continues to work.
    indir = tmpdir.mkdir('sixgb')
    largefile = os.path.join(str(indir), 'bigfile')
    output_iso = os.path.join(str(indir), 'sixgb.iso')
    testfile = os.path.join(str(indir), 'testfile')

    with open(largefile, 'w') as outfp:
        outfp.truncate(6442444801)

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3)
    iso.add_file(largefile, '/BIGFILE.;1')
    iso.write(output_iso)
    iso.close()

    newiso = pycdlib.PyCdlib()
    newiso.open(output_iso)
    newiso.get_file_from_iso(testfile, iso_path='/BIGFILE.;1')
    newiso.close()

    st = os.stat(testfile)
    assert(st.st_size == 6442444801)

@pytest.mark.slow
def test_new_rm_very_largefile(tmpdir):
    indir = tmpdir.mkdir('rmverylarge')
    largefile = os.path.join(str(indir), 'bigfile')

    with open(largefile, 'w') as outfp:
        outfp.truncate(5*1024*1024*1024)  # 5 GB

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3)

    # Add a new file.
    iso.add_file(largefile, '/BIGFILE.;1')

    iso.rm_file('/BIGFILE.;1')

    do_a_test(iso, check_nofiles, tmpdir)

    iso.close()

@pytest.mark.slow
def test_new_udf_very_large(tmpdir):
    indir = tmpdir.mkdir('udfverylarge')
    largefile = os.path.join(str(indir), 'foo')

    with open(largefile, 'wb') as outfp:
        outfp.truncate(1073739776+1)

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1, udf='2.60')

    # Add a new file.
    iso.add_file(largefile, '/FOO.;1', udf_path='/foo')

    do_a_test(iso, check_udf_very_large, tmpdir)

    iso.close()

def test_new_udf_above_multi_extent_threshold(tmpdir):
    # Regression test for issue #65: a UDF file larger than the ISO9660
    # multi-extent boundary (0xfffff800 ~= 4 GiB) used to leave the UDF
    # File Entry pointing at only the last fragment's inode while the
    # earlier fragments became orphaned inodes.  Use a sparse input and
    # verify the in-memory state without writing the (~4 GiB) ISO out.
    indir = tmpdir.mkdir('udfabovemulti')
    largefile = os.path.join(str(indir), 'foo')

    SIZE = 0xfffff800 + 1
    with open(largefile, 'wb') as outfp:
        outfp.truncate(SIZE)

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, udf='2.60')
    iso.add_file(largefile, udf_path='/foo')

    fe = list(iso.udf_root.fi_descs.values())[1].file_entry
    assert(fe.info_len == SIZE)
    assert(sum(ad.extent_length for ad in fe.alloc_descs) == SIZE)
    assert(fe.inode is not None)
    assert(fe.inode.data_length == SIZE)
    assert(fe.inode.fp_offset == 0)
    # Exactly one inode should be tracked: the full-file UDF inode.  Without
    # the fix, the splitting loop would also leave an orphaned per-chunk
    # inode behind.
    assert(len(iso.inodes) == 1)
    assert(iso.inodes[0] is fe.inode)
    assert(len(fe.inode.linked_records) == 1)

    iso.close()

@pytest.mark.slow
def test_new_udf_above_multi_extent_threshold_roundtrip(tmpdir):
    # Round-trip companion to test_new_udf_above_multi_extent_threshold:
    # write a >4 GiB UDF file to a real ISO and read it back to verify the
    # data on either side of the multi-extent boundary survives intact.
    indir = tmpdir.mkdir('udfabovemultirt')
    largefile = os.path.join(str(indir), 'foo')
    output_iso = os.path.join(str(indir), 'udfabovemulti.iso')
    extracted = os.path.join(str(indir), 'extracted')

    SIZE = 0xfffff800 + 4096
    boundary = 0xfffff800
    with open(largefile, 'wb') as outfp:
        outfp.truncate(SIZE)
        outfp.seek(0)
        outfp.write(b'\xaa' * 16)
        outfp.seek(boundary - 8)
        outfp.write(b'\xbb' * 16)
        outfp.seek(SIZE - 16)
        outfp.write(b'\xcc' * 16)

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, udf='2.60')
    iso.add_file(largefile, udf_path='/foo')
    iso.write(output_iso)
    iso.close()

    newiso = pycdlib.PyCdlib()
    newiso.open(output_iso)
    newiso.get_file_from_iso(extracted, udf_path='/foo')
    newiso.close()

    assert(os.stat(extracted).st_size == SIZE)
    with open(extracted, 'rb') as fp:
        assert(fp.read(16) == b'\xaa' * 16)
        fp.seek(boundary - 8)
        assert(fp.read(16) == b'\xbb' * 16)
        fp.seek(SIZE - 16)
        assert(fp.read(16) == b'\xcc' * 16)

@pytest.mark.slow
def test_new_udf_bridge_above_multi_extent_threshold(tmpdir):
    # UDF Bridge round-trip for a file larger than 0xfffff800 bytes.  Both
    # the ISO9660 and UDF views must point at the same physical extents
    # (single copy of the file data on disc, per ECMA-167) and both must
    # extract identical content.
    indir = tmpdir.mkdir('bridgeabovemultirt')
    largefile = os.path.join(str(indir), 'foo')
    output_iso = os.path.join(str(indir), 'bridge.iso')
    extracted_iso = os.path.join(str(indir), 'extracted_iso')
    extracted_udf = os.path.join(str(indir), 'extracted_udf')

    SIZE = 0xfffff800 + 4096
    boundary = 0xfffff800
    with open(largefile, 'wb') as outfp:
        outfp.truncate(SIZE)
        outfp.seek(0)
        outfp.write(b'\xaa' * 16)
        outfp.seek(boundary - 8)
        outfp.write(b'\xbb' * 16)
        outfp.seek(SIZE - 16)
        outfp.write(b'\xcc' * 16)

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, udf='2.60')
    iso.add_file(largefile, '/FOO.;1', udf_path='/foo')

    # Single shared inode across the ISO9660 multi-extent chunks and the UDF
    # File Entry: confirm we don't have separate per-chunk inodes for the
    # ISO9660 view.
    file_inodes = [ino for ino in iso.inodes if ino.data_length > 0]
    assert(len(file_inodes) == 1)
    assert(file_inodes[0].data_length == SIZE)
    # 2 ISO9660 multi-extent chunks + 1 UDF File Entry = 3 linked records.
    assert(len(file_inodes[0].linked_records) == 3)

    iso.write(output_iso)
    iso.close()

    # The on-disc file should contain a single copy of the data.  An
    # over-budget bound: header/metadata extents + ceil(SIZE/2048) data
    # extents + a small slack for trailing UDF anchors and padding.  If the
    # data were duplicated, the size would balloon by roughly another SIZE.
    iso_size = os.stat(output_iso).st_size
    data_extents = (SIZE + 2047) // 2048
    assert(iso_size < (data_extents + 4096) * 2048)

    newiso = pycdlib.PyCdlib()
    newiso.open(output_iso)
    newiso.get_file_from_iso(extracted_iso, iso_path='/FOO.;1')
    newiso.get_file_from_iso(extracted_udf, udf_path='/foo')
    newiso.close()

    for extracted in (extracted_iso, extracted_udf):
        assert(os.stat(extracted).st_size == SIZE)
        with open(extracted, 'rb') as fp:
            assert(fp.read(16) == b'\xaa' * 16)
            fp.seek(boundary - 8)
            assert(fp.read(16) == b'\xbb' * 16)
            fp.seek(SIZE - 16)
            assert(fp.read(16) == b'\xcc' * 16)

def test_new_lookup_after_rmdir():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')

    rec = iso.get_record(iso_path='/DIR1')
    assert(rec.file_identifier() == b'DIR1')
    assert(len(rec.children) == 2)

    iso.rm_directory('/DIR1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rec = iso.get_record(iso_path='/DIR1')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_lookup_after_rmfile():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    rec = iso.get_record(iso_path='/FOO.;1')
    assert(rec.file_identifier() == b'FOO.;1')
    assert(len(rec.children) == 0)

    iso.rm_file('/FOO.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rec = iso.get_record(iso_path='/FOO.;1')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_udf_lookup_after_rmdir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    rec = iso.get_record(udf_path='/dir1')

    iso.rm_directory('/DIR1', udf_path='/dir1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rec = iso.get_record(udf_path='/dir1')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_udf_lookup_after_rmfile():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    rec = iso.get_record(udf_path='/foo')

    iso.rm_file('/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rec = iso.get_record(udf_path='/foo')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_full_path_no_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    rec = iso.get_record(iso_path='/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        name = iso.full_path_from_dirrecord(rec, True)
    assert(str(excinfo.value) == 'Cannot generate a Rock Ridge path on a non-Rock Ridge ISO')

    iso.close()

def test_new_list_children_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/DIR1/BOOT.;1', udf_path='/dir1/boot')

    full_path = None
    for child in iso.list_children(udf_path='/dir1'):
        if child is not None:
            if child.file_identifier() == b'boot':
                break
    else:
        assert(False)

    iso.close()

def test_new_udf_list_children_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children(udf_path='/foo'):
            pass
    assert(str(excinfo.value) == 'UDF File Entry is not a directory!')

    iso.close()

def test_new_list_children_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children(iso_path='/FOO.;1'):
            pass
    assert(str(excinfo.value) == 'Record is not a directory!')

    iso.close()

def test_new_list_children_joliet_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for c in iso.list_children(joliet_path='/foo'):
            pass
    assert(str(excinfo.value) == 'Record is not a directory!')

    iso.close()

def test_new_udf_remove_base():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_directory(udf_path='/')
    assert(str(excinfo.value) == 'Cannot remove base directory')

    iso.close()

def test_new_remove_udf_path_not_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_directory(udf_path='/dir1')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_add_dir_udf_path_not_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory(udf_path='/dir1')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_rm_link_udf_path_not_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(udf_path='/foo')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_rm_link_udf_path_not_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_hard_link(udf_path='/dir1')
    assert(str(excinfo.value) == 'Cannot remove a directory with rm_hard_link (try rm_directory instead)')

    iso.close()

def test_new_add_link_udf_path_not_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_old_path='/FOO.;1', udf_new_path='/foo')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_add_fp_udf_path_not_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_get_file_from_iso_fp_udf_path_not_udf():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, udf_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a udf_path from a non-UDF ISO')

    iso.close()

def test_new_joliet_udf_nofiles():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, udf='2.60')

    do_a_test(iso, check_joliet_udf_nofiles)

    iso.close()

def test_new_udf_dir_exactly2048():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/AAAAAAAA', udf_path='/' + 'a'*248)
    iso.add_directory('/BBBBBBBB', udf_path='/' + 'b'*248)
    iso.add_directory('/CCCCCCCC', udf_path='/' + 'c'*248)
    iso.add_directory('/DDDDDDDD', udf_path='/' + 'd'*248)
    iso.add_directory('/EEEEEEEE', udf_path='/' + 'e'*248)
    iso.add_directory('/FFFFFFFF', udf_path='/' + 'f'*248)
    iso.add_directory('/GGGGGGGG', udf_path='/' + 'g'*240)

    do_a_test(iso, check_udf_dir_exactly2048)

    iso.close()

def test_new_udf_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_symlink('/BAR.;1', udf_symlink_path='/bar', udf_target='foo')

    do_a_test(iso, check_udf_symlink)

    iso.close()

def test_new_udf_symlink_in_dir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1', udf_path='/dir1/foo')

    iso.add_symlink('/BAR.;1', udf_symlink_path='/bar', udf_target='dir1/foo')

    do_a_test(iso, check_udf_symlink_in_dir)

    iso.close()

def test_new_udf_symlink_abs_path():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_symlink('/BAR.;1', udf_symlink_path='/bar', udf_target='/etc/os-release')

    do_a_test(iso, check_udf_symlink_abs_path)

    iso.close()

def test_new_symlink_no_rr_symlink_name():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1')
    assert(str(excinfo.value) == 'Either a Rock Ridge or a UDF symlink must be specified')

    iso.close()

def test_new_symlink_rr_path_no_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1', rr_path='/foo')
    assert(str(excinfo.value) == 'Can only add a symlink to a Rock Ridge or UDF ISO')

    iso.close()

def test_new_symlink_no_rr_no_udf():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1', udf_symlink_path='/foo')
    assert(str(excinfo.value) == 'Can only add a symlink to a Rock Ridge or UDF ISO')

    iso.close()

def test_new_symlink_no_udf():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1', udf_symlink_path='/foo', udf_target='bar')
    assert(str(excinfo.value) == 'A UDF symlink can only be created on a UDF ISO')

    iso.close()

def test_new_udf_symlink_no_target():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1', udf_symlink_path='/foo')
    assert(str(excinfo.value) == "Both of 'udf_symlink_path' and 'udf_target' must be provided for a UDF symlink")

    iso.close()

def test_new_udf_symlink_add_rr():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/BAR.;1', rr_symlink_name='foo', rr_path='/')
    assert(str(excinfo.value) == 'A Rock Ridge symlink can only be created on a Rock Ridge ISO')

    iso.close()

def test_new_rr_symlink_no_iso_path():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink(rr_symlink_name='foo', rr_path='/')
    assert(str(excinfo.value) == "When making a Rock Ridge symlink 'symlink_path' is required")

    iso.close()

def test_new_symlink_no_type_specified():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink()
    assert(str(excinfo.value) == 'Either a Rock Ridge or a UDF symlink must be specified')

    iso.close()

def test_new_rr_rm_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    iso.rm_file('/SYM.;1')

    do_a_test(iso, check_rr_onefile)

    iso.close()

def test_new_udf_rm_link_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    # Add: any new extents for FI container (0) + log_block_size (File Entry) + file_entry.info_len
    iso.add_symlink('/SYM.;1', udf_symlink_path='/sym', udf_target='/foo')

    iso.rm_file('/SYM.;1')
    iso.rm_hard_link(udf_path='/sym')

    do_a_test(iso, check_udf_onefile)

    iso.close()

def test_new_udf_rr_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', udf_path='/foo')

    # Add: any new extents for FI container (0) + log_block_size (File Entry) + file_entry.info_len
    iso.add_symlink('/SYM.;1', rr_symlink_name='sym', rr_path='foo', udf_symlink_path='/sym', udf_target='foo')

    do_a_test(iso, check_udf_rr_symlink)

    iso.close()

def test_new_udf_overflow_dir_extent():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    tmp = []
    for i in range(1, 1+46):
        tmp.append('/dir' + str(i))
    names = sorted(tmp)

    for name in names:
        iso.add_directory(name.upper(), udf_path=name)

    do_a_test(iso, check_udf_overflow_dir_extent)

    iso.close()

def test_new_udf_hardlink():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_hard_link(udf_old_path='/foo', udf_new_path='/bar')

    do_a_test(iso, check_udf_hardlink)

    iso.close()

def test_new_multi_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    iso.add_hard_link(iso_old_path='/BAR.;1', iso_new_path='/BAZ.;1')

    do_a_test(iso, check_multi_hard_link)

    iso.close()

def test_new_multi_hard_link2():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAZ.;1')

    do_a_test(iso, check_multi_hard_link)

    iso.close()

def test_new_joliet_with_version():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo.;1')

    do_a_test(iso, check_joliet_with_version)

    iso.close()

def test_new_link_joliet_to_iso():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
    iso.rm_hard_link(iso_path='/FOO.;1')

    iso.add_hard_link(joliet_old_path='/foo', iso_new_path='/FOO.;1')

    do_a_test(iso, check_joliet_onefile)

    iso.close()

def test_new_udf_joliet_onefile():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo', udf_path='/foo')

    do_a_test(iso, check_udf_joliet_onefile)

    iso.close()

def test_new_link_joliet_to_udf():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.add_hard_link(joliet_old_path='/foo', udf_new_path='/foo')

    do_a_test(iso, check_udf_joliet_onefile)

    iso.close()

def test_new_link_udf_to_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_hard_link(udf_old_path='/foo', joliet_new_path='/foo')

    do_a_test(iso, check_udf_joliet_onefile)

    iso.close()

def test_new_joliet_hard_link_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', joliet_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_hard_link('/BOOT.CAT;1')
    iso.rm_hard_link(joliet_path='/boot.cat')

    iso.add_hard_link(boot_catalog_old=True, joliet_new_path='/boot.cat')

    do_a_test(iso, check_joliet_and_eltorito_joliet_only)

    iso.close()

def test_new_udf_hard_link_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1', udf_path='/boot')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    iso.rm_hard_link('/BOOT.CAT;1')
    iso.rm_hard_link(udf_path='/boot.cat')

    iso.add_hard_link(boot_catalog_old=True, udf_new_path='/boot.cat')

    do_a_test(iso, check_udf_and_eltorito_udf_only)

    iso.close()

def test_new_bogus_symlink():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/SYM.;1', 'sym')
    assert(str(excinfo.value) == "Both of 'rr_symlink_name' and 'rr_path' must be provided for a Rock Ridge symlink")

    iso.close()

def test_new_joliet_symlink_no_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_symlink('/SYM.;1', 'sym', 'foo', joliet_path='/foo')
    assert(str(excinfo.value) == 'A Joliet path can only be specified for a Joliet ISO')

    iso.close()

def test_new_eltorito_udf_rm_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    iso.rm_eltorito()

    do_a_test(iso, check_udf_onefile)

    iso.close()

def test_new_add_eltorito_udf_path_no_udf():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1', udf_bootcatfile='/foo')
    assert(str(excinfo.value) == 'A UDF path must not be passed when adding El Torito to a non-UDF ISO')

    iso.close()

def test_new_add_eltorito_joliet_path_no_joliet():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1', joliet_bootcatfile='/foo')
    assert(str(excinfo.value) == 'A joliet path must not be passed when adding El Torito to a non-Joliet ISO')

    iso.close()

def test_new_rm_file_linked_by_eltorito_bootcat():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file('/BOOT.CAT;1')
    assert(str(excinfo.value) == "Cannot remove a file that is referenced by El Torito; use 'rm_eltorito' to remove El Torito, or use 'rm_hard_link' to hide the entry")

    iso.close()

def test_new_invalid_udf_version():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.new(udf='foo')
    assert(str(excinfo.value) == 'UDF value must be empty (no UDF), or 2.60')

def test_new_udf_rm_hard_link_multi_links():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/bar')

    iso.add_hard_link(udf_old_path='/bar', udf_new_path='/foo')
    iso.add_hard_link(udf_old_path='/bar', udf_new_path='/baz')

    iso.rm_hard_link(udf_path='/bar')

    do_a_test(iso, check_udf_onefile_multi_links)

    iso.close()

def test_new_hard_link_invalid_new_keyword():
    iso = pycdlib.PyCdlib()
    iso.new()

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_old_path='/FOO.;1', blah='some')
    assert(str(excinfo.value) == 'Unknown keyword blah')

    iso.close()

def test_new_udf_dotdot_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_symlink('/DIR1/SYM.;1', udf_symlink_path='/dir1/sym', udf_target='../foo')

    do_a_test(iso, check_udf_dotdot_symlink)

    iso.close()

def test_new_udf_dot_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_symlink('/SYM.;1', udf_symlink_path='/sym', udf_target='./foo')

    do_a_test(iso, check_udf_dot_symlink)

    iso.close()

def test_new_udf_zero_byte_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1', udf_path='/bar')

    do_a_test(iso, check_udf_zero_byte_file)

    iso.close()

def test_new_udf_fail_find():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp('/foo')
    assert(str(excinfo.value) == "Exactly one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path' must be passed")

    iso.close()

def test_new_udf_onefile_onedirwithfile():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    barstr = b'bar\n'
    iso.add_fp(io.BytesIO(barstr), len(barstr), '/DIR1/BAR.;1', udf_path='/dir1/bar')

    do_a_test(iso, check_udf_onefile_onedirwithfile)

    iso.close()

def test_new_udf_get_invalid():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    out = io.BytesIO()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(out, udf_path='/foo/some')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_zero_byte_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')
    iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

    do_a_test(iso, check_zero_byte_hard_link)

    iso.close()

def test_new_udf_zero_byte_hard_link():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')
    iso.add_hard_link(udf_old_path='/foo', udf_new_path='/bar')

    do_a_test(iso, check_udf_zero_byte_hard_link)

    iso.close()

def test_new_unicode_name():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F__O.;1')

    do_a_test(iso, check_unicode_name)

    iso.close()

def test_new_unicode_name_isolevel4():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/föo')

    do_a_test(iso, check_unicode_name_isolevel4)

    iso.close()

def test_new_unicode_name_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F__O.;1', joliet_path='/föo')

    do_a_test(iso, check_unicode_name_joliet)

    iso.close()

def test_new_unicode_name_udf():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F__O.;1', udf_path='/föo')

    do_a_test(iso, check_unicode_name_udf)

    iso.close()

def test_new_unicode_name_two_byte():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1')

    do_a_test(iso, check_unicode_name_two_byte)

    iso.close()

def test_new_unicode_name_two_byte_isolevel4():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/fᴔo')

    do_a_test(iso, check_unicode_name_two_byte_isolevel4)

    iso.close()

def test_new_unicode_name_two_byte_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1', joliet_path='/fᴔo')

    do_a_test(iso, check_unicode_name_two_byte_joliet)

    iso.close()

def test_new_unicode_name_two_byte_udf():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1', udf_path='/fᴔo')

    do_a_test(iso, check_unicode_name_two_byte_udf)

    iso.close()

def test_new_unicode_name_two_byte_isolevel4_list_children():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/fᴔo')

    full_path = None
    for child in iso.list_children(iso_path='/'):
        if child.file_identifier() == b'f\xe1\xb4\x94o':
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/fᴔo')
            break

    assert(full_path is not None)

    iso.close()

def test_new_unicode_name_two_byte_joliet_list_children():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1', joliet_path='/fᴔo')

    full_path = None
    for child in iso.list_children(joliet_path='/'):
        if child.file_identifier() == b'\x00f\x1d\x14\x00o':
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/fᴔo')
            break

    assert(full_path is not None)

    iso.close()

def test_new_unicode_name_two_byte_udf_list_children():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1', udf_path='/fᴔo')

    full_path = None
    for child in iso.list_children(udf_path='/'):
        if child is not None and child.file_identifier() == b'\x00f\x1d\x14\x00o':
            full_path = iso.full_path_from_dirrecord(child)
            assert(full_path == '/fᴔo')
            break

    assert(full_path is not None)

    iso.close()

def test_new_add_non_binary_file():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = u'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.StringIO(foostr), len(foostr), '/FOO.;1')
    assert(str(excinfo.value) == 'The fp argument must be in binary mode')

    iso.close()

def test_new_udf_get_symlink_file():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_symlink('/BAR.;1', udf_symlink_path='/bar', udf_target='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), udf_path='/bar')
    assert(str(excinfo.value) == 'Can only write out a file')

    iso.close()

def test_new_udf_unicode_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/F___O.;1', udf_path='/fᴔo')

    iso.add_symlink('/BAR.;1', udf_symlink_path='/bar', udf_target='fᴔo')

    do_a_test(iso, check_udf_unicode_symlink)

    iso.close()

def test_new_udf_bad_tag_location():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    out = io.BytesIO()
    iso.write_fp(out)

    iso.close()

    # Seek to the end anchor and change the tag location to be incorrect
    out.seek(-2048, 2)
    out.seek(12, 1)
    out.write(b'\x00\x00\x00\x00')

    # Now fix up the checksum
    out.seek(-2048, 2)
    out.seek(4, 1)
    out.write(b'\xcd')

    out.seek(0)

    iso = pycdlib.PyCdlib()
    iso.open_fp(out)

    # Now check that the tag location has been corrected by pycdlib.
    assert(iso.udf_anchors[1].desc_tag.tag_location == 266)

    iso.close()

def test_new_eltorito_rm_multi_boot():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'foo\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/FOO.;1')
    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/BOOT2.;1')
    iso.add_eltorito('/BOOT2.;1', '/BOOT.CAT;1')

    iso.rm_eltorito()
    iso.rm_file('/BOOT2.;1')

    do_a_test(iso, check_onefile)

    iso.close()

def test_new_full_path_from_dirrecord_udf_root():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    assert(iso.full_path_from_dirrecord(iso.udf_root) == '/')

    iso.close()

def test_new_udf_file_entry_is_dot():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    rec = iso.get_record(udf_path='/dir1')

    assert(not rec.is_dot())

    iso.close()

def test_new_udf_file_entry_is_dotdot():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')

    rec = iso.get_record(udf_path='/dir1')

    assert(not rec.is_dotdot())

    iso.close()

def test_new_walk_iso():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/SUBDIR1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1')

    iso.add_directory('/DIR2')
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR2/FOO.;1')

    iso.add_directory('/DIR3')
    iso.add_directory('/DIR3/SUBDIR3')

    # A list of lists, where each sub-list consists of the expected
    # name, directories, and files.
    expected_names = [
        ['/', ['DIR3', 'DIR2', 'DIR1'], []],
        ['/DIR1', ['SUBDIR1'], ['FOO.;1']],
        ['/DIR1/SUBDIR1', [], []],
        ['/DIR2', [], ['FOO.;1']],
        ['/DIR3', ['SUBDIR3'], []],
        ['/DIR3/SUBDIR3', [], []]
    ]
    expected_offset = 0
    for dirname, dirlist, filelist in iso.walk(iso_path='/'):
        assert(dirname == expected_names[expected_offset][0])
        assert(dirlist == expected_names[expected_offset][1])
        assert(filelist == expected_names[expected_offset][2])
        expected_offset += 1

    iso.close()

def test_new_walk_rr():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')
    iso.add_directory('/DIR1/SUBDIR1', rr_name='subdir1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1', rr_name='foo')

    iso.add_directory('/DIR2', rr_name='dir2')
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR2/FOO.;1', rr_name='foo')

    iso.add_directory('/DIR3', rr_name='dir3')
    iso.add_directory('/DIR3/SUBDIR3', rr_name='subdir3')

    # A list of lists, where each sub-list consists of the expected
    # name, directories, and files.
    expected_names = [
        ['/', ['dir3', 'dir2', 'dir1'], []],
        ['/dir1', ['subdir1'], ['foo']],
        ['/dir1/subdir1', [], []],
        ['/dir2', [], ['foo']],
        ['/dir3', ['subdir3'], []],
        ['/dir3/subdir3', [], []]
    ]
    expected_offset = 0
    for dirname, dirlist, filelist in iso.walk(rr_path='/'):
        assert(dirname == expected_names[expected_offset][0])
        assert(dirlist == expected_names[expected_offset][1])
        assert(filelist == expected_names[expected_offset][2])
        expected_offset += 1

    iso.close()

def test_new_walk_joliet():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')
    iso.add_directory('/DIR1/SUBDIR1', joliet_path='/dir1/subdir1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1', joliet_path='/dir1/foo')

    iso.add_directory('/DIR2', joliet_path='/dir2')
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR2/FOO.;1', joliet_path='/dir2/foo')

    iso.add_directory('/DIR3', joliet_path='/dir3')
    iso.add_directory('/DIR3/SUBDIR3', joliet_path='/dir3/subdir3')

    # A list of lists, where each sub-list consists of the expected
    # name, directories, and files.
    expected_names = [
        ['/', ['dir3', 'dir2', 'dir1'], []],
        ['/dir1', ['subdir1'], ['foo']],
        ['/dir1/subdir1', [], []],
        ['/dir2', [], ['foo']],
        ['/dir3', ['subdir3'], []],
        ['/dir3/subdir3', [], []]
    ]
    expected_offset = 0
    for dirname, dirlist, filelist in iso.walk(joliet_path='/'):
        assert(dirname == expected_names[expected_offset][0])
        assert(dirlist == expected_names[expected_offset][1])
        assert(filelist == expected_names[expected_offset][2])
        expected_offset += 1

    iso.close()

def test_new_walk_udf():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    iso.add_directory('/DIR1/SUBDIR1', udf_path='/dir1/subdir1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1', udf_path='/dir1/foo')

    iso.add_directory('/DIR2', udf_path='/dir2')
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR2/FOO.;1', udf_path='/dir2/foo')

    iso.add_directory('/DIR3', udf_path='/dir3')
    iso.add_directory('/DIR3/SUBDIR3', udf_path='/dir3/subdir3')

    # A list of lists, where each sub-list consists of the expected
    # name, directories, and files.
    expected_names = [
        ['/', ['dir3', 'dir2', 'dir1'], []],
        ['/dir1', ['subdir1'], ['foo']],
        ['/dir1/subdir1', [], []],
        ['/dir2', [], ['foo']],
        ['/dir3', ['subdir3'], []],
        ['/dir3/subdir3', [], []]
    ]
    expected_offset = 0
    for dirname, dirlist, filelist in iso.walk(udf_path='/'):
        assert(dirname == expected_names[expected_offset][0])
        assert(dirlist == expected_names[expected_offset][1])
        assert(filelist == expected_names[expected_offset][2])
        expected_offset += 1

    iso.close()

def test_new_walk_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(iso_path='/'):
            pass
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_walk_bad_keyword():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(foo='bar'):
            pass
    assert(str(excinfo.value) == "Invalid keyword, must be one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_walk_no_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk():
            pass
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_walk_too_many_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(iso_path='/', joliet_path='/'):
            pass
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_walk_joliet_no_joliet():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(joliet_path='/'):
            pass
    assert(str(excinfo.value) == 'A Joliet path can only be specified for a Joliet ISO')

    iso.close()

def test_new_walk_rr_no_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(rr_path='/'):
            pass
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')

    iso.close()

def test_new_walk_udf_no_udf():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for x,y,z in iso.walk(udf_path='/'):
            pass
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_walk_iso_remove_dirlist_entry():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    iso.add_directory('/DIR1/SUBDIR1')
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR1/FOO.;1')

    iso.add_directory('/DIR2')
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/DIR2/FOO.;1')

    iso.add_directory('/DIR3')
    iso.add_directory('/DIR3/SUBDIR3')

    # A list of lists, where each sub-list consists of the expected
    # name, directories, and files.
    expected_names = [
        ['/', ['DIR3', 'DIR2', 'DIR1'], []],
        ['/DIR1', ['SUBDIR1'], ['FOO.;1']],
        ['/DIR2', [], ['FOO.;1']],
        ['/DIR3', ['SUBDIR3'], []],
        ['/DIR3/SUBDIR3', [], []]
    ]
    expected_offset = 0
    for dirname, dirlist, filelist in iso.walk(iso_path='/'):
        assert(dirname == expected_names[expected_offset][0])
        assert(dirlist == expected_names[expected_offset][1])
        assert(filelist == expected_names[expected_offset][2])
        if dirname == '/DIR1':
            del dirlist[:]
        expected_offset += 1

    iso.close()

def test_new_walk_filename():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for dirname, dirlist, filelist in iso.walk(iso_path='/FOO.;1'):
            pass
    assert(str(excinfo.value) == 'Record is not a directory!')

def test_new_walk_udf_filename():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        for dirname, dirlist, filelist in iso.walk(udf_path='/foo'):
            pass
    assert(str(excinfo.value) == 'UDF File Entry is not a directory!')

def test_new_walk_udf_zero_entry_path():
    # FIXME: implement me!
    pass

def test_new_open_file_from_iso_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(iso_path='/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_open_file_from_iso_invalid_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(foo_path='/FOO.;1')
    assert(str(excinfo.value) == "Invalid keyword, must be one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_open_file_from_iso_too_many_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(iso_path='/FOO.;1', udf_path='/foo')
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_open_file_from_iso_too_few_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso()
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_open_file_from_iso_invalid_joliet():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(joliet_path='/foo')
    assert(str(excinfo.value) == 'A Joliet path can only be specified for a Joliet ISO')

    iso.close()

def test_new_open_file_from_iso_invalid_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(rr_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')

    iso.close()

def test_new_open_file_from_iso_invalid_udf():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(udf_path='/foo')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_open_file_from_iso_dir():
    iso = pycdlib.PyCdlib()
    iso.new()

    iso.add_directory('/DIR1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(iso_path='/DIR1')
    assert(str(excinfo.value) == 'Path to open must be a file')

    iso.close()

def test_new_open_file_from_iso_joliet_dir():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    iso.add_directory('/DIR1', joliet_path='/dir1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(joliet_path='/dir1')
    assert(str(excinfo.value) == 'Path to open must be a file')

    iso.close()

def test_new_open_file_from_iso_rr_dir():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    iso.add_directory('/DIR1', rr_name='dir1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(rr_path='/dir1')
    assert(str(excinfo.value) == 'Path to open must be a file')

    iso.close()

def test_new_open_file_from_iso_udf_dir():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory('/DIR1', udf_path='/dir1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(udf_path='/dir1')
    assert(str(excinfo.value) == 'Path to open must be a file')

    iso.close()

def test_new_open_file_from_iso_udf_no_inode():
    # FIXME: implement me!
    pass

def test_new_open_file_from_iso_ctxt_manager():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.read() == b'foo\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_past_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(20)
        assert(infp.read() == b'')
        assert(infp.tell() == 20)

    iso.close()

def test_new_open_file_from_iso_single():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.read(1) == b'f')
        assert(infp.tell() == 1)

    iso.close()

def test_new_open_file_from_iso_past_half_past_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(2)
        assert(infp.read(4) == b'o\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_readall():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.readall() == b'foo\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_readall_past_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(20)
        assert(infp.readall() == b'')
        assert(infp.tell() == 20)

    iso.close()

def test_new_open_file_from_iso_readall_half_past_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(2)
        assert(infp.readall() == b'o\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_seek_invalid_offset():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(4.5)
        assert(str(excinfo.value) == 'an integer is required')

    iso.close()

def test_new_open_file_from_iso_seek_invalid_whence():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(0, whence=5)
        assert(str(excinfo.value) == 'Invalid value for whence (options are 0, 1, and 2)')

    iso.close()

def test_new_open_file_from_iso_seek_whence_begin():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(1, whence=0)
        assert(infp.tell() == 1)
        assert(infp.readall() == b'oo\n')

    iso.close()

def test_new_open_file_from_iso_seek_whence_negative_begin():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(-1, whence=0)
        assert(str(excinfo.value) == 'Invalid offset value (must be positive)')

    iso.close()

def test_new_open_file_from_iso_seek_whence_begin_beyond_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(10, whence=0)
        assert(infp.tell() == 10)
        assert(infp.readall() == b'')
        assert(infp.tell() == 10)

    iso.close()

def test_new_open_file_from_iso_seek_whence_curr():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(1, whence=1)
        assert(infp.tell() == 1)
        infp.seek(1, whence=1)
        assert(infp.tell() == 2)
        assert(infp.readall() == b'o\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_seek_whence_curr_before_start():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(-2, whence=1)
        assert(str(excinfo.value) == 'Invalid offset value (cannot seek before start of file)')

    iso.close()

def test_new_open_file_from_iso_seek_whence_curr_negative():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.readall() == b'foo\n')
        assert(infp.tell() == 4)
        infp.seek(-2, whence=1)
        assert(infp.tell() == 2)
        assert(infp.readall() == b'o\n')

    iso.close()

def test_new_open_file_from_iso_seek_whence_end():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(-2, whence=2)
        assert(infp.tell() == 2)
        assert(infp.readall() == b'o\n')
        assert(infp.tell() == 4)

    iso.close()

def test_new_open_file_from_iso_seek_whence_end_before_start():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(-5, whence=2)
        assert(str(excinfo.value) == 'Invalid offset value (cannot seek before start of file)')

    iso.close()

def test_new_open_file_from_iso_not_open():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.close()
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.read()
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.readall()
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.readinto(bytearray(5))
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seek(0, 0)
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.tell()
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.length()
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.readable()
        assert(str(excinfo.value) == 'I/O operation on closed file.')
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            infp.seekable()
        assert(str(excinfo.value) == 'I/O operation on closed file.')

    iso.close()

def test_new_open_file_from_iso_length():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.length() == 4)

    iso.close()

def test_new_open_file_from_iso_readable():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.readable())

    iso.close()

def test_new_open_file_from_iso_seekable():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        assert(infp.seekable())

    iso.close()

def test_new_open_file_from_iso_readinto():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        arr = bytearray(4)
        assert(infp.readinto(arr) == 4)
        assert(arr == b'\x66\x6f\x6f\x0a')

    iso.close()

def test_new_open_file_from_iso_readinto_partial():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        arr = bytearray(2)
        assert(infp.readinto(arr) == 2)
        assert(arr == b'\x66\x6f')
        assert(infp.readinto(arr) == 2)
        assert(arr == b'\x6f\x0a')

    iso.close()

def test_new_open_file_from_iso_readinto_past_eof():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with iso.open_file_from_iso(iso_path='/FOO.;1') as infp:
        infp.seek(4)
        arr = bytearray(2)
        assert(infp.readinto(arr) == 0)
        assert(arr == b'\x00\x00')

    iso.close()

def _build_two_file_iso():
    """Build an ISO containing two files whose contents are easy to tell
    apart byte-wise.  Returns the freshly-opened PyCdlib object."""
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'A' * 4096), 4096, '/A.;1')
    iso.add_fp(io.BytesIO(b'B' * 4096), 4096, '/B.;1')
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(io.BytesIO(out.getvalue()))
    return iso2

def test_new_open_file_from_iso_concurrent_reads_dont_corrupt():
    # Regression test: PyCdlibIO.read used to issue a bare
    # self._fp.read(n) without seeking first, relying on _cdfp's position
    # being whatever __enter__ left it.  But _cdfp is shared with the
    # rest of pycdlib, so opening (and reading) a second file on the same
    # ISO would silently shift _cdfp to the second file's data and the
    # next read() on the first PyCdlibIO would return the second file's
    # bytes instead of the first file's continuation.
    iso = _build_two_file_iso()

    with iso.open_file_from_iso(iso_path='/A.;1') as fa:
        first = fa.read(100)
        assert(first == b'A' * 100)

        # Opening and reading from B mutates the shared _cdfp position.
        with iso.open_file_from_iso(iso_path='/B.;1') as fb:
            assert(fb.read(100) == b'B' * 100)

        # fa.read must continue at A[100:200], not at B[100:200].
        second = fa.read(100)
        assert(second == b'A' * 100)

    iso.close()

def test_new_open_file_from_iso_concurrent_open_no_read_dont_corrupt():
    # Same hazard, weaker trigger: merely entering the second file's
    # context manager seeks the shared _cdfp to that file's start (in
    # InodeOpenData.__enter__), even if no read happens.  fa's next
    # read must still return A's continuation.
    iso = _build_two_file_iso()

    with iso.open_file_from_iso(iso_path='/A.;1') as fa:
        assert(fa.read(100) == b'A' * 100)

        with iso.open_file_from_iso(iso_path='/B.;1') as fb_unused:
            pass

        assert(fa.read(100) == b'A' * 100)

    iso.close()

def test_new_open_file_from_iso_concurrent_readinto_dont_corrupt():
    # readinto has the same bare-read hazard; verify the regression case
    # against it directly.
    iso = _build_two_file_iso()

    with iso.open_file_from_iso(iso_path='/A.;1') as fa:
        buf = bytearray(100)
        assert(fa.readinto(buf) == 100)
        assert(bytes(buf) == b'A' * 100)

        with iso.open_file_from_iso(iso_path='/B.;1') as fb:
            buf2 = bytearray(100)
            assert(fb.readinto(buf2) == 100)
            assert(bytes(buf2) == b'B' * 100)

        buf3 = bytearray(100)
        assert(fa.readinto(buf3) == 100)
        assert(bytes(buf3) == b'A' * 100)

    iso.close()

def test_new_open_file_from_iso_concurrent_readall_dont_corrupt():
    # readall has the same bare-read hazard.  Read part of A, then poke
    # _cdfp by opening B, then readall the rest of A.
    iso = _build_two_file_iso()

    with iso.open_file_from_iso(iso_path='/A.;1') as fa:
        first = fa.read(100)
        assert(first == b'A' * 100)

        with iso.open_file_from_iso(iso_path='/B.;1') as fb:
            assert(fb.read(100) == b'B' * 100)

        rest = fa.readall()
        assert(rest == b'A' * (4096 - 100))

    iso.close()

def test_new_udf_cyrillic():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    teststr = b''
    iso.add_fp(io.BytesIO(teststr), len(teststr), '/TEST.TXT;1', udf_path='/test.txt')

    iso.add_directory('/__', udf_path='/РЭ')
    iso.add_directory('/__/PORT', udf_path='/РЭ/Port')
    iso.add_directory('/__/________', udf_path='/РЭ/Руководства')

    iso.add_fp(io.BytesIO(teststr), len(teststr), '/__/PORT/________.TXT;1', udf_path='/РЭ/Port/виртуальный порт.txt')

    iso.add_fp(io.BytesIO(teststr), len(teststr), '/__/________/________.TXT;1', udf_path='/РЭ/Руководства/Руководство по.txt')

    do_a_test(iso, check_udf_unicode)

    iso.close()

def test_new_eltorito_get_bootcat():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    do_a_test(iso, check_eltorito_get_bootcat)

    iso.close()

def test_new_eltorito_invalid_platform_id():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', None, None, None, 0xff)
    assert(str(excinfo.value) == 'Invalid platform ID (must be one of 0, 1, 2, or 0xef)')

    iso.close()

def test_new_eltorito_uefi():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', None, None, None, 0xef)

    do_a_test(iso, check_eltorito_uefi)

    iso.close()

def test_new_has_rock_ridge_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.has_rock_ridge()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_has_joliet_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.has_joliet()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_has_udf_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.has_udf()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_open_file_from_iso_eltorito_boot_catalog():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.open_file_from_iso(iso_path='/BOOT.CAT;1')
    assert(str(excinfo.value) == 'File has no data')

    iso.close()

def test_new_add_fp_all_none():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_fp(io.BytesIO(foostr), len(foostr))
    assert(str(excinfo.value) == "At least one of 'iso_path', 'joliet_path', or 'udf_path' must be provided")

    iso.close()

def test_new_rm_joliet_only():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

    iso.rm_file(joliet_path='/foo')

    do_a_test(iso, check_joliet_nofiles)

    iso.close()

def test_new_rm_udf_only():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.rm_file(udf_path='/foo')

    do_a_test(iso, check_udf_nofiles)

    iso.close()

def test_new_udf_zero_byte_rm_file():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), udf_path='/foo')

    iso.rm_file(udf_path='/foo')

    do_a_test(iso, check_udf_nofiles)

    iso.close()

def test_new_rm_file_no_udf():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    foostr = b''
    iso.add_fp(io.BytesIO(foostr), len(foostr), joliet_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file(udf_path='/foo')
    assert(str(excinfo.value) == 'Can only specify a UDF path for a UDF ISO')

    iso.close()

def test_new_rm_dir_udf_only():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    iso.add_directory(udf_path='/dir1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file(udf_path='/dir1')
    assert(str(excinfo.value) == 'Cannot remove a directory with rm_file (try rm_directory instead)')

    iso.close()

def test_new_eltorito_udf_rm_file_referenced_by_eltorito():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    # Add a new file.
    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    iso.add_eltorito('/FOO.;1', '/BOOT.CAT;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file(udf_path='/foo')
    assert(str(excinfo.value) == "Cannot remove a file that is referenced by El Torito; use 'rm_eltorito' to remove El Torito, or use 'rm_hard_link' to hide the entry")

    iso.close()

def test_new_udf_eltorito_multi_boot_rm_file():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4, udf='2.60')

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/boot', udf_path='/boot')
    iso.add_eltorito('/boot', '/boot.cat')

    boot2str = b'boot2\n'
    iso.add_fp(io.BytesIO(boot2str), len(boot2str), '/boot2', udf_path='/boot2')
    iso.add_eltorito('/boot2', '/boot.cat')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.rm_file(udf_path='/boot2')
    assert(str(excinfo.value) == "Cannot remove a file that is referenced by El Torito; use 'rm_eltorito' to remove El Torito, or use 'rm_hard_link' to hide the entry")

    iso.close()

def test_new_udf_anchor_after_shrink():
    # Create a UDF ISO with a small file and a large file, write it, reopen,
    # remove the large file, add a different small file, write again, then
    # reopen.  The removal makes the reshuffled layout more compact than the
    # original pvd.space_size, which (before the fix) caused the second UDF
    # anchor to be placed at an extent the parser wouldn't check.
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', udf_path='/foo')

    bigstr = b'x' * 102400
    iso.add_fp(io.BytesIO(bigstr), len(bigstr), '/BIG.;1', udf_path='/big')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)

    iso2.rm_file(iso_path='/BIG.;1', udf_path='/big')

    barstr = b'bar\n'
    iso2.add_fp(io.BytesIO(barstr), len(barstr), '/BAR.;1', udf_path='/bar')

    out2 = io.BytesIO()
    iso2.write_fp(out2)

    check_udf_anchor_after_shrink(iso2, len(out2.getvalue()))

    iso2.close()

    # The critical check: reopen the twice-written ISO and verify it parses
    # correctly, confirming both UDF anchors are at locations the parser finds.
    iso3 = pycdlib.PyCdlib()
    iso3.open_fp(out2)
    check_udf_anchor_after_shrink(iso3, len(out2.getvalue()))
    iso3.close()

def test_new_rr_file_mode():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    assert(iso.file_mode(rr_path='/foo') == 0o0100444)

    iso.close()

def test_new_file_mode_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.file_mode(rr_path='/foo')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_rr_file_mode_bad_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.file_mode(foo_path='/foo')
    assert(str(excinfo.value) == "Invalid keyword, must be one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_rr_file_mode_multiple_kwarg():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.file_mode(rr_path='/foo', iso_path='/FOO.;1')
    assert(str(excinfo.value) == "Must specify one, and only one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path'")

    iso.close()

def test_new_rr_file_mode_not_rr():
    iso = pycdlib.PyCdlib()
    iso.new()

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.file_mode(rr_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')

    iso.close()

def test_new_rr_empty_dir_get_record():
    # Create a new ISO.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # Add new directory.
    iso.add_directory('/DIR1', rr_name='dir1')

    # Now try to get a non-existent record in that directory.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        rec = iso.get_record(rr_path='/dir1/foo')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_rr_long_names_overflow_ce_block():
    # Regression test for issue #177: enough files with long Rock Ridge names
    # to overflow a single Rock Ridge Continuation Block.  Once the first
    # block filled up, add_entry() returned -1 instead of None, which
    # add_rr_ce_entry() accepted as a valid offset instead of allocating a
    # second block.  The bogus -1 offset then failed on write.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    for i in range(40):
        rr_name = ('f%03d' % i) + 'x' * 200
        iso.add_fp(io.BytesIO(b'hello\n'), 6, '/FILE%03d.;1' % i, rr_name=rr_name)

    out = io.BytesIO()
    iso.write_fp(out)

    iso.close()

    # Make sure the result round-trips and the long names survived.
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    for i in range(40):
        rr_name = ('f%03d' % i) + 'x' * 200
        rec = iso2.get_record(rr_path='/' + rr_name)
        assert(rec.get_data_length() == 6)
    iso2.close()

def test_new_rr_symlink_chained_ce():
    # A symlink whose target needs more continuation area than fits in a single
    # logical block gets split across several areas, each linking to the next
    # with a CE record.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    # 4019 bytes, with every component well under NAME_MAX (255) and the whole
    # target under PATH_MAX (4096), so this is a symlink that can really exist
    # on a Unix filesystem.  Anything past roughly a 2040-byte target needs
    # more than one 2048-byte block for its continuation area.
    target = '/'.join(['c' * 200] * 20)
    iso.add_symlink('/SYM.;1', 'sym', target)

    rec = iso.get_record(rr_path='/sym')
    assert(len(rec.rock_ridge.ce_areas) > 1)
    for ce_area in rec.rock_ridge.ce_areas:
        assert(ce_area.length <= 2048)

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    # Now make sure it reads back as the same symlink.
    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)
    rec2 = iso2.get_record(rr_path='/sym')
    assert(len(rec2.rock_ridge.ce_areas) > 1)
    assert(rec2.rock_ridge.symlink_path() == target.encode('utf-8'))
    iso2.close()

def test_new_isolevel4_deep_directory():
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)

    iso.add_directory('/dir1')
    iso.add_directory('/dir1/dir2')
    iso.add_directory('/dir1/dir2/dir3')
    iso.add_directory('/dir1/dir2/dir3/dir4')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5/dir6')
    iso.add_directory('/dir1/dir2/dir3/dir4/dir5/dir6/dir7')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/dir1/dir2/dir3/dir4/dir5/dir6/dir7/foo')

    do_a_test(iso, check_isolevel4_deep_directory)

    iso.close()

@pytest.mark.slow
def test_new_isolevel1_largefile(tmpdir):
    indir = tmpdir.mkdir('verylarge')
    largefile = os.path.join(str(indir), 'bigfile')

    with open(largefile, 'w') as outfp:
        outfp.truncate(5*1024*1024*1024)  # 5 GB

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=1)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_file(largefile, '/BIGFILE.;1')
    assert(str(excinfo.value) == 'File sizes for interchange level < 3 must be less than 4GiB')

    iso.close()

# Validation / error-path coverage for get_file_byte_extents().  The happy path
# (iso_path + udf_path) is covered by test_new_get_file_byte_extents above;
# these exercise the kwargs-parsing and lookup guards, which are all fast,
# in-memory checks that raise before any real work.
def test_new_get_file_byte_extents_not_initialized():
    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(iso_path='/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_file_byte_extents_unknown_keyword():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(bogus_path='/FOO.;1')
    assert(str(excinfo.value) == 'Unknown keyword bogus_path')
    iso.close()

def test_new_get_file_byte_extents_no_path():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents()
    assert(str(excinfo.value) == "Exactly one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path' must be passed")
    iso.close()

def test_new_get_file_byte_extents_multiple_paths():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(iso_path='/FOO.;1', joliet_path='/foo')
    assert(str(excinfo.value) == "Exactly one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path' must be passed")
    iso.close()

def test_new_get_file_byte_extents_wrong_type():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(iso_path=42)
    assert(str(excinfo.value) == 'iso_path must be a string')
    iso.close()

def test_new_get_file_byte_extents_udf_path_non_udf():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(udf_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a udf_path from a non-UDF ISO')
    iso.close()

def test_new_get_file_byte_extents_joliet_path_non_joliet():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(joliet_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a joliet_path from a non-Joliet ISO')
    iso.close()

def test_new_get_file_byte_extents_rr_path_non_rr():
    iso = pycdlib.PyCdlib()
    iso.new()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(rr_path='/foo')
    assert(str(excinfo.value) == 'Cannot fetch a rr_path from a non-Rock Ridge ISO')
    iso.close()

def test_new_get_file_byte_extents_directory():
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_directory('/DIR1')
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(iso_path='/DIR1')
    assert(str(excinfo.value) == 'Cannot get extents for a directory')
    iso.close()

def test_new_rm_eltorito_hidden_boot_catalog():
    # Regression test for https://github.com/clalancette/pycdlib/issues/175;
    # an ISO whose El Torito boot catalog has no directory record (like
    # Microsoft Windows installation ISOs) gets a 'fake' directory record
    # during parsing, and rm_eltorito used to fail on it with
    # 'Invalid child index to remove'.
    iso = pycdlib.PyCdlib()
    iso.new()

    bootstr = b'boot\n'
    iso.add_fp(io.BytesIO(bootstr), len(bootstr), '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')

    # Hide the boot catalog so it has no directory record on the ISO.
    iso.rm_hard_link(iso_path='/BOOT.CAT;1')

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open_fp(out)

    iso2.rm_eltorito()
    iso2.rm_file('/BOOT.;1')

    do_a_test(iso2, check_nofiles)

    iso2.close()

def test_new_get_file_from_iso_bad_blocksize():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', blocksize='foo')
    assert(str(excinfo.value) == 'blocksize must be an integer')

    iso.close()

def test_new_get_file_from_iso_bad_iso_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', iso_path=1)
    assert(str(excinfo.value) == 'iso_path must be a string')

    iso.close()

def test_new_get_file_from_iso_bad_rr_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', rr_path=1)
    assert(str(excinfo.value) == 'iso_path must be a string')

    iso.close()

def test_new_get_file_from_iso_bad_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', joliet_path=1)
    assert(str(excinfo.value) == 'iso_path must be a string')

    iso.close()

def test_new_get_file_from_iso_bad_udf_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', udf_path=1)
    assert(str(excinfo.value) == 'iso_path must be a string')

    iso.close()

def test_new_get_file_from_iso_unknown_keyword():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk', foo_path='/FOO.;1')
    assert(str(excinfo.value) == 'Unknown keyword foo_path')

    iso.close()

def test_new_get_file_from_iso_no_paths():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso('junk')
    assert(str(excinfo.value) == "Exactly one of 'iso_path', 'rr_path', 'joliet_path', or 'udf_path' must be passed")

    iso.close()

def test_new_get_file_from_iso_fp_bad_blocksize():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), blocksize='foo')
    assert(str(excinfo.value) == 'blocksize must be an integer')

    iso.close()

def test_new_get_file_from_iso_fp_bad_iso_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), iso_path=1)
    assert(str(excinfo.value) == 'iso_path must be a string')

    iso.close()

def test_new_get_file_from_iso_fp_bad_rr_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), rr_path=1)
    assert(str(excinfo.value) == 'rr_path must be a string')

    iso.close()

def test_new_get_file_from_iso_fp_bad_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), joliet_path=1)
    assert(str(excinfo.value) == 'joliet_path must be a string')

    iso.close()

def test_new_get_file_from_iso_fp_bad_udf_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_from_iso_fp(io.BytesIO(), udf_path=1)
    assert(str(excinfo.value) == 'udf_path must be a string')

    iso.close()

def test_new_get_file_byte_extents_bad_rr_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(rr_path=1)
    assert(str(excinfo.value) == 'rr_path must be a string')

    iso.close()

def test_new_get_file_byte_extents_bad_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(joliet_path=1)
    assert(str(excinfo.value) == 'joliet_path must be a string')

    iso.close()

def test_new_get_file_byte_extents_bad_udf_path():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(udf_path=1)
    assert(str(excinfo.value) == 'udf_path must be a string')

    iso.close()

def test_new_get_file_byte_extents_symlink():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo')
    iso.add_symlink('/SYM.;1', 'sym', 'foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(rr_path='/sym')
    assert(str(excinfo.value) == 'Symlinks have no data associated with them')

    iso.close()

def test_new_get_iso9660_facade_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_iso9660_facade()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_joliet_facade_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_joliet_facade()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_joliet_facade_not_joliet():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_joliet_facade()
    assert(str(excinfo.value) == 'Can only get a Joliet facade for a Joliet ISO')

    iso.close()

def test_new_get_rock_ridge_facade_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_rock_ridge_facade()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_rock_ridge_facade_not_rock_ridge():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_rock_ridge_facade()
    assert(str(excinfo.value) == 'Can only get a Rock Ridge facade for a Rock Ridge ISO')

    iso.close()

def test_new_get_udf_facade_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_udf_facade()
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_get_udf_facade_not_udf():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_udf_facade()
    assert(str(excinfo.value) == 'Can only get a UDF facade for a UDF ISO')

    iso.close()

def test_new_rr_add_directory_no_rr_name():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/DIR1')
    assert(str(excinfo.value) == 'A rock ridge name must be passed for a rock-ridge ISO')

    iso.close()

def test_new_joliet_add_directory_empty_joliet_path():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_directory('/DIR1', joliet_path='')
    assert(str(excinfo.value) == 'A Joliet path must be passed for a Joliet ISO')

    iso.close()

def test_new_add_file_creation_time_not_rr_or_udf(tmpdir):
    iso = pycdlib.PyCdlib()
    iso.new()

    testout = tmpdir.join('foo')
    testout.write('foo\n')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_file(str(testout), '/FOO.;1', creation_time=1.0)
    assert(str(excinfo.value) == 'creation_time can only be stored on a Rock Ridge iso_path or a udf_path')

    iso.close()

def test_new_add_hard_link_creation_time_not_rock_ridge():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09', joliet=3)

    foostr = b'foo\n'
    iso.add_fp(io.BytesIO(foostr), len(foostr), '/FOO.;1', rr_name='foo', joliet_path='/foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.add_hard_link(iso_old_path='/FOO.;1', joliet_new_path='/bar', creation_time=1.0)
    assert(str(excinfo.value) == 'creation_time can only be stored on a Rock Ridge iso_new_path')

    iso.close()

def test_new_udf_get_file_byte_extents_directory():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_file_byte_extents(udf_path='/')
    assert(str(excinfo.value) == 'Can only get extents for a file')

    iso.close()

def test_new_in_place_rm_file_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        pycdlib.inplaceeditor._do_rm_file(iso, '/FOO.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_in_place_add_fp_not_initialized():
    iso = pycdlib.PyCdlib()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        pycdlib.inplaceeditor._do_add_fp(iso, io.BytesIO(b'x'), 1, False, '/BAR.;1')
    assert(str(excinfo.value) == 'This object is not initialized; call either open() or new() to create an ISO')

def test_new_in_place_rm_file_read_only_iso(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    # open() uses a read-only mode, which in-place editing must refuse.
    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        pycdlib.inplaceeditor._do_rm_file(iso2, '/FOO.;1')
    assert(str(excinfo.value) == 'To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

    iso2.close()

def test_new_in_place_add_fp_read_only_iso(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'old\n'), 4, '/FOO.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        pycdlib.inplaceeditor._do_add_fp(iso2, io.BytesIO(b'x'), 1, False, '/BAR.;1')
    assert(str(excinfo.value) == 'To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

    iso2.close()

def test_new_in_place_rm_file_eltorito_boot_catalog(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'boot\n'), 5, '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.rm_file('/BOOT.CAT;1')
        assert(str(excinfo.value) == 'Cannot remove a file that is the El Torito boot catalog; use PyCdlib.rm_eltorito + write_fp() to produce a new ISO instead')

def test_new_in_place_add_fp_joliet_path_on_non_joliet(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'a\n'), 2, '/A.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            ed.add_fp(io.BytesIO(b'b\n'), 2, '/B.;1', joliet_path='/b')
        assert(str(excinfo.value) == 'Cannot use joliet_path on a non-Joliet ISO')

def test_new_in_place_add_fp_explicit_file_mode(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'a\n'), 2, '/A.;1', rr_name='a')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_fp(io.BytesIO(b'b\n'), 2, '/B.;1', rr_name='b', file_mode=0o0100644)

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    rec = iso2._find_rr_record(b'/b')
    assert(rec.rock_ridge.get_file_mode() == 0o0100644)
    iso2.close()

def test_new_update_file_contents_udf_path_on_non_udf():
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'a\n'), 2, '/A.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'b\n'), 2, udf_path='/a')
    assert(str(excinfo.value) == 'Cannot use udf_path on a non-UDF ISO')

    iso.close()

def test_new_update_file_contents_rr_path_on_non_rock_ridge():
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'a\n'), 2, '/A.;1')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'b\n'), 2, rr_path='/a')
    assert(str(excinfo.value) == 'Cannot use rr_path on a non-Rock-Ridge ISO')

    iso.close()

def test_new_update_file_contents_udf_directory():
    iso = pycdlib.PyCdlib()
    iso.new(udf='2.60')
    iso.add_fp(io.BytesIO(b'a\n'), 2, '/A.;1', udf_path='/a')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.update_file_contents_fp(io.BytesIO(b'b\n'), 2, udf_path='/')
    assert(str(excinfo.value) == 'Cannot update the contents of a directory or empty UDF entry')

    iso.close()

def test_new_write_progress_cb_wrong_arg_count():
    iso = pycdlib.PyCdlib()
    iso.new()

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.write_fp(io.BytesIO(), progress_cb=lambda done: None)
    assert(str(excinfo.value) == 'The progress callback must take 2 or 3 arguments')

    iso.close()

def test_new_in_place_modify_eltorito_boot_catalog(tmpdir):
    # The El Torito boot catalog's directory record deliberately has no
    # Inode (the catalog is managed in memory), so an in-place modify of it
    # is rejected rather than dereferencing None.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'boot\n'), 5, '/BOOT.;1')
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInternalError) as excinfo:
            ed.modify_file(io.BytesIO(b'x'*2048), 2048, '/BOOT.CAT;1')
        assert(str(excinfo.value) == 'Child file found without inode')

def test_new_in_place_add_fp_enhanced_vd(tmpdir):
    # An interchange level 4 ISO carries an enhanced VD, whose sizes have to
    # be copied from the PVD and written back out after an in-place add.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)
    iso.add_fp(io.BytesIO(b'aaa\n'), 4, '/A.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.add_fp(io.BytesIO(b'bbb\n'), 4, '/B.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    assert(iso2.enhanced_vd is not None)
    assert(iso2.enhanced_vd.space_size == iso2.pvd.space_size)
    buf = io.BytesIO()
    iso2.get_file_from_iso_fp(buf, iso_path='/B.;1')
    assert(buf.getvalue() == b'bbb\n')
    iso2.close()

def test_new_in_place_rm_file_enhanced_vd(tmpdir):
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=4)
    iso.add_fp(io.BytesIO(b'aaa\n'), 4, '/A.;1')
    iso.add_fp(io.BytesIO(b'bbb\n'), 4, '/B.;1')
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    with pycdlib.InPlaceEditor(iso_path) as ed:
        ed.rm_file('/A.;1')

    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    assert(iso2.enhanced_vd is not None)
    assert(iso2.enhanced_vd.space_size == iso2.pvd.space_size)
    names = [c.file_identifier() for c in iso2.pvd.root_directory_record().children]
    assert(b'A.;1' not in names)
    assert(b'B.;1' in names)
    iso2.close()

def test_new_in_place_add_fp_joliet_overflow_rolls_back(tmpdir):
    # Joliet names are UTF-16BE, so the Joliet root directory extent fills up
    # well before the ISO9660 one.  Twelve files with long Joliet names leaves
    # the Joliet root with no room for a thirteenth, while the ISO9660 root
    # still has plenty -- so the add succeeds on the ISO9660 side and then has
    # to be rolled back when the Joliet side overflows.
    iso_path = str(tmpdir.join('test.iso'))
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    for index in range(12):
        iso.add_fp(io.BytesIO(b'x\n'), 2, '/FILE%04d.;1' % index,
                   joliet_path='/' + ('j%03d' % index) + 'x'*58)
    with open(iso_path, 'wb') as f:
        iso.write_fp(f)
    iso.close()

    ed = pycdlib.InPlaceEditor(iso_path)
    iso_root = ed._iso.pvd.root_directory_record()
    joliet_root = ed._iso.joliet_vd.root_directory_record()
    iso_children_before = len(iso_root.children)
    joliet_children_before = len(joliet_root.children)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        ed.add_fp(io.BytesIO(b'y\n'), 2, '/NEW.;1', joliet_path='/' + 'jnew' + 'y'*58)
    assert(str(excinfo.value) == "Adding this file would overflow the Joliet parent directory's extent; use PyCdlib.add_fp + write_fp() to produce a new ISO instead")

    # The ISO9660 side must have been rolled back, so the failure is atomic.
    assert(len(iso_root.children) == iso_children_before)
    assert(len(joliet_root.children) == joliet_children_before)
    assert(not any(c.file_identifier() == b'NEW.;1' for c in iso_root.children))
    ed._iso.close()

    # And the on-disk ISO must still be intact.
    iso2 = pycdlib.PyCdlib()
    iso2.open(iso_path)
    assert(len(iso2.pvd.root_directory_record().children) == iso_children_before)
    iso2.close()

def test_new_get_file_byte_extents_before_write():
    # get_file_byte_extents() reports byte offsets derived from extent
    # locations, which are only assigned during a reshuffle.  On an ISO built
    # with new() and not yet written out, the call must still work (forcing
    # the reshuffle itself) rather than reading an unassigned extent.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1')

    extents = iso.get_file_byte_extents(iso_path='/FOO.;1')
    assert(len(extents) == 1)

    # The reported offset must match where the data actually lands on disk.
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    (offset, length) = extents[0]
    assert(out.getvalue()[offset:offset+length] == b'foo\n')

def test_new_get_file_byte_extents_joliet_before_write():
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3)
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', joliet_path='/foo')

    iso_extents = iso.get_file_byte_extents(iso_path='/FOO.;1')
    joliet_extents = iso.get_file_byte_extents(joliet_path='/foo')
    # Both names point at the same shared Inode, so the same bytes.
    assert(iso_extents == joliet_extents)

    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    (offset, length) = joliet_extents[0]
    assert(out.getvalue()[offset:offset+length] == b'foo\n')

def test_new_rr_find_record_missing_component():
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')

    # 'aaa' sorts before 'foo', so the binary search lands on an existing
    # entry that simply does not match.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso._find_rr_record(b'/aaa')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_rr_find_record_missing_component_sorts_last():
    # A name that sorts after every entry in the directory leaves the binary
    # search with index == len(children), so looking it up has to report
    # 'Could not find path' rather than running off the end of the list.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')
    iso.add_directory('/DIR1', rr_name='dir1')

    for path in (b'/zzz', b'/dir1/zzz'):
        with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
            iso._find_rr_record(path)
        assert(str(excinfo.value) == 'Could not find path')

    # The same through the public API that callers actually use.
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso.get_record(rr_path='/zzz')
    assert(str(excinfo.value) == 'Could not find path')

    # An entry sorting last is still findable.
    assert(iso.get_record(rr_path='/foo').rock_ridge.name() == b'foo')

    iso.close()

def test_new_rr_find_record_component_is_not_a_directory():
    # Walking '/foo/deeper' has to stop at 'foo', which is a file and so has
    # no children to descend into.
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_fp(io.BytesIO(b'foo\n'), 4, '/FOO.;1', rr_name='foo')

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidInput) as excinfo:
        iso._find_rr_record(b'/foo/deeper')
    assert(str(excinfo.value) == 'Could not find path')

    iso.close()

def test_new_get_file_byte_extents_zero_length_file():
    # A zero-length file has an Inode but no data extents, so there are no
    # byte ranges to report.
    iso = pycdlib.PyCdlib()
    iso.new()
    iso.add_fp(io.BytesIO(b''), 0, '/EMPTY.;1')

    assert(iso.get_file_byte_extents(iso_path='/EMPTY.;1') == [])

    iso.close()


def _build_multi_section_iso(num_sections, **kwargs):
    # Build an ISO whose El Torito Boot Catalog holds num_sections sections,
    # and return the bytes of the written ISO along with the catalog.
    iso = pycdlib.PyCdlib()
    iso.new(**kwargs)

    rr_name = 'boot' if kwargs.get('rock_ridge') else None
    joliet_path = '/boot' if kwargs.get('joliet') else None
    udf_path = '/boot' if kwargs.get('udf') else None
    iso.add_fp(io.BytesIO(b'boot\n'), 5, '/BOOT.;1', rr_name=rr_name,
               joliet_path=joliet_path, udf_path=udf_path)

    catalog_kwargs = {}
    if kwargs.get('rock_ridge'):
        catalog_kwargs['rr_bootcatname'] = 'boot.cat'
    if kwargs.get('joliet'):
        catalog_kwargs['joliet_bootcatfile'] = '/boot.cat'
    if kwargs.get('udf'):
        catalog_kwargs['udf_bootcatfile'] = '/boot.cat'
    iso.add_eltorito('/BOOT.;1', '/BOOT.CAT;1', **catalog_kwargs)

    for i_unused in range(0, num_sections):
        iso.add_eltorito('/BOOT.;1')

    catalog = iso.eltorito_boot_catalog
    out = io.BytesIO()
    iso.write_fp(out)
    iso.close()

    return out.getvalue(), catalog

def test_new_eltorito_sections_past_one_sector():
    # El Torito puts no limit on the number of sectors the Boot Catalog uses,
    # so a catalog with more sections than fit in one sector grows to two and
    # can be read back.
    data, catalog = _build_multi_section_iso(40)

    assert(catalog.record_length() == 2624)
    for rec in catalog.dirrecords:
        assert(rec.get_data_length() == 4096)

    iso = pycdlib.PyCdlib()
    iso.open_fp(io.BytesIO(data))

    assert(len(iso.eltorito_boot_catalog.sections) == 40)
    assert(len(iso.eltorito_boot_catalog.standalone_entries) == 0)
    assert(iso.pvd.space_size * 2048 == len(data))

    iso.close()

def test_new_eltorito_sections_exactly_fill_a_sector():
    # A catalog whose entries exactly fill a sector still needs room for the
    # empty entry that terminates it, or the parser would run into whatever
    # follows the catalog on the ISO.
    data, catalog = _build_multi_section_iso(31)

    assert(catalog.record_length() == 2048)
    for rec in catalog.dirrecords:
        assert(rec.get_data_length() == 4096)

    iso = pycdlib.PyCdlib()
    iso.open_fp(io.BytesIO(data))

    assert(len(iso.eltorito_boot_catalog.sections) == 31)
    assert(len(iso.eltorito_boot_catalog.standalone_entries) == 0)

    iso.close()

def test_new_eltorito_sections_past_one_sector_joliet_rr_udf():
    # Every name the boot catalog is known by has to grow, not just the
    # ISO9660 one.
    data, catalog = _build_multi_section_iso(40, joliet=3, rock_ridge='1.09',
                                             udf='2.60')

    assert(len(catalog.dirrecords) == 3)
    for rec in catalog.dirrecords:
        assert(rec.get_data_length() == 4096)

    iso = pycdlib.PyCdlib()
    iso.open_fp(io.BytesIO(data))

    assert(len(iso.eltorito_boot_catalog.sections) == 40)
    assert(iso.pvd.space_size * 2048 == len(data))

    iso.close()

def _make_isohybrid_uefi_iso(tmpdir, name):
    # Build a UEFI isohybrid ISO with pycdlib and write it out to a real file,
    # returning its path.  These tests have to work on a file rather than a
    # BytesIO: reading from a BytesIO does not allocate the read buffer up
    # front, so the allocation peak would not reflect what a caller passing a
    # filename would see.
    iso = pycdlib.PyCdlib()
    iso.new()
    isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
    iso.add_fp(io.BytesIO(isolinuxstr), len(isolinuxstr), '/ISOLINUX.BIN;1')
    efibootstr = b'a'
    iso.add_fp(io.BytesIO(efibootstr), len(efibootstr), '/EFIBOOT.IMG;1')
    iso.add_eltorito('/ISOLINUX.BIN;1', '/BOOT.CAT;1', boot_load_size=4,
                     boot_info_table=True)
    iso.add_eltorito('/EFIBOOT.IMG;1', efi=True)
    iso.add_isohybrid(efi=True)

    outfile = os.path.join(str(tmpdir), name)
    with open(outfile, 'wb') as outfp:
        iso.write_fp(outfp)
    iso.close()

    return outfile

def _secondary_gpt_offset(path):
    # The secondary GPT header lives at the backup LBA that the primary GPT
    # header (at LBA 1) points to, which is at offset 32 of that header.
    with open(path, 'rb') as fp:
        fp.seek(512 + 32)
        backup_lba, = struct.unpack('<Q', fp.read(8))
    return backup_lba * 512

# The two tests below are the isohybrid half of the unbounded-allocation tests;
# the ones for the path table, directory records, and Rock Ridge continuation
# areas live in test_parse.py, since those ISOs are built with genisoimage.
def test_new_isohybrid_gpt_num_parts_larger_than_iso(tmpdir):
    outfile = _make_isohybrid_uefi_iso(tmpdir, 'gptnumpartstoobig.iso')

    # The number of GPT partition entries is at offset 80 of the GPT header,
    # and the ISO is read backwards from current_lba (offset 24) for
    # num_parts*128 bytes, so raise current_lba to keep that offset positive.
    num_parts = 0x2000000
    gpt_offset = _secondary_gpt_offset(outfile)
    with open(outfile, 'r+b') as fp:
        fp.seek(gpt_offset + 24)
        fp.write(struct.pack('<Q', num_parts // 4))
        fp.seek(gpt_offset + 80)
        fp.write(struct.pack('<I', num_parts))

    err, peak = open_measuring_peak(outfile)

    assert(isinstance(err, pycdlib.pycdlibexception.PyCdlibInvalidISO))
    assert(peak < MAX_ALLOWED_PEAK)

def test_new_isohybrid_gpt_parts_before_start_of_iso(tmpdir):
    # num_parts and current_lba both come off of the ISO, so an ISO can claim
    # that the GPT partition entries start before the beginning of the ISO.
    outfile = _make_isohybrid_uefi_iso(tmpdir, 'gptpartsnegative.iso')

    gpt_offset = _secondary_gpt_offset(outfile)
    with open(outfile, 'r+b') as fp:
        fp.seek(gpt_offset + 80)
        fp.write(struct.pack('<I', BOGUS_LENGTH))

    iso = pycdlib.PyCdlib()
    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO) as excinfo:
        iso.open(outfile)
    assert(str(excinfo.value) == 'Secondary GPT partition entries start before the start of the ISO')
