import pytest
import subprocess
import os
import sys
import StringIO
import struct
import stat

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

from common import *

def test_parse_invalid_file(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(AttributeError):
        iso.open(None)

    with pytest.raises(AttributeError):
        iso.open('foo')

def test_parse_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("nofile-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_nofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_nofile(iso2, os.stat(str(testout)).st_size)

def test_parse_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefile-test.iso")
    indir = tmpdir.mkdir("onefile")
    with open(os.path.join(str(tmpdir), "onefile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_onefile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_onefile(iso2, os.stat(str(testout)).st_size)

def test_parse_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onedir-test.iso")
    indir = tmpdir.mkdir("onedir")
    tmpdir.mkdir("onedir/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_onedir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_onedir(iso2, os.stat(str(testout)).st_size)

def test_parse_twofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twofile-test.iso")
    indir = tmpdir.mkdir("twofile")
    with open(os.path.join(str(tmpdir), "twofile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(tmpdir), "twofile", "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_twofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_twofile(iso2, os.stat(str(testout)).st_size)

def test_parse_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefileonedir-test.iso")
    indir = tmpdir.mkdir("onefileonedir")
    with open(os.path.join(str(tmpdir), "onefileonedir", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    tmpdir.mkdir("onefileonedir/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_onefileonedir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_onefileonedir(iso2, os.stat(str(testout)).st_size)

def test_parse_onefile_onedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefileonedirwithfile-test.iso")
    indir = tmpdir.mkdir("onefileonedirwithfile")
    with open(os.path.join(str(tmpdir), "onefileonedirwithfile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    tmpdir.mkdir("onefileonedirwithfile/dir1")
    with open(os.path.join(str(tmpdir), "onefileonedirwithfile", "dir1", "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_onefile_onedirwithfile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_onefile_onedirwithfile(iso2, os.stat(str(testout)).st_size)

def test_parse_tendirs(tmpdir):
    numdirs = 10
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("tendirs-test.iso")
    indir = tmpdir.mkdir("tendirs")
    for i in range(1, 1+numdirs):
        tmpdir.mkdir("tendirs/dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_tendirs(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_tendirs(iso2, os.stat(str(testout)).st_size)

def test_parse_dirs_overflow_ptr_extent(tmpdir):
    numdirs = 295
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("manydirs-test.iso")
    indir = tmpdir.mkdir("manydirs")
    for i in range(1, 1+numdirs):
        tmpdir.mkdir("manydirs/dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_dirs_overflow_ptr_extent(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_dirs_overflow_ptr_extent(iso2, os.stat(str(testout)).st_size)

def test_parse_dirs_just_short_ptr_extent(tmpdir):
    numdirs = 293
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("manydirs-test.iso")
    indir = tmpdir.mkdir("manydirs")
    for i in range(1, 1+numdirs):
        tmpdir.mkdir("manydirs/dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_dirs_just_short_ptr_extent(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_dirs_just_short_ptr_extent(iso2, os.stat(str(testout)).st_size)

def test_parse_twoextentfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("bigfile-test.iso")
    indir = tmpdir.mkdir("bigfile")
    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)
    with open(os.path.join(str(tmpdir), "bigfile", "bigfile"), 'wb') as outfp:
        outfp.write(outstr)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_twoextentfile(iso, outstr)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_twoextentfile(iso2, outstr)

def test_parse_twoleveldeepdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeep-test.iso")
    indir = tmpdir.mkdir("twoleveldeep")
    tmpdir.mkdir('twoleveldeep/dir1')
    tmpdir.mkdir('twoleveldeep/dir1/subdir1')
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_twoleveldeepdir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_twoleveldeepdir(iso2, os.stat(str(testout)).st_size)

def test_parse_twoleveldeepfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeepfile-test.iso")
    indir = tmpdir.mkdir("twoleveldeepfile")
    tmpdir.mkdir('twoleveldeepfile/dir1')
    tmpdir.mkdir('twoleveldeepfile/dir1/subdir1')
    with open(os.path.join(str(tmpdir), "twoleveldeepfile", "dir1", "subdir1", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_twoleveldeepfile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_twoleveldeepfile(iso2, os.stat(str(testout)).st_size)

def test_parse_joliet_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("joliet-nofilestest.iso")
    indir = tmpdir.mkdir("joliet")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_joliet_nofiles(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_joliet_nofiles(iso2, os.stat(str(testout)).st_size)

def test_parse_joliet_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("joliet-test.iso")
    indir = tmpdir.mkdir("joliet")
    tmpdir.mkdir('joliet/dir1')
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_joliet_onedir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_joliet_onedir(iso2, os.stat(str(testout)).st_size)

def test_parse_joliet_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("jolietfile-test.iso")
    indir = tmpdir.mkdir("jolietfile")
    with open(os.path.join(str(tmpdir), "jolietfile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_joliet_onefile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_joliet_onefile(iso2, os.stat(str(testout)).st_size)

def test_parse_eltorito(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("eltoritonofile-test.iso")
    indir = tmpdir.mkdir("eltoritonofile")
    with open(os.path.join(str(tmpdir), "eltoritonofile", "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_eltorito_nofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_eltorito_nofile(iso2, os.stat(str(testout)).st_size)

def test_parse_eltorito_twofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("eltoritotwofile-test.iso")
    indir = tmpdir.mkdir("eltoritotwofile")
    with open(os.path.join(str(tmpdir), "eltoritotwofile", "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    with open(os.path.join(str(tmpdir), "eltoritotwofile", "aa"), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_eltorito_twofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_eltorito_twofile(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_nofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrnofile-test.iso")
    indir = tmpdir.mkdir("rrnofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_nofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_nofile(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefile-test.iso")
    indir = tmpdir.mkdir("rronefile")
    with open(os.path.join(str(tmpdir), "rronefile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_onefile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_onefile(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_twofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrtwofile-test.iso")
    indir = tmpdir.mkdir("rrtwofile")
    with open(os.path.join(str(tmpdir), "rrtwofile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(tmpdir), "rrtwofile", "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_twofile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_twofile(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefileonedir-test.iso")
    indir = tmpdir.mkdir("rronefileonedir")
    with open(os.path.join(str(tmpdir), "rronefileonedir", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    tmpdir.mkdir("rronefileonedir/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_onefileonedir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_onefileonedir(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_onefileonedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefileonedirwithfile-test.iso")
    indir = tmpdir.mkdir("rronefileonedirwithfile")
    with open(os.path.join(str(tmpdir), "rronefileonedirwithfile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    tmpdir.mkdir("rronefileonedirwithfile/dir1")
    with open(os.path.join(str(tmpdir), "rronefileonedirwithfile", "dir1", "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_onefileonedirwithfile(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_onefileonedirwithfile(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_symlink(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrsymlink-test.iso")
    indir = tmpdir.mkdir("rrsymlink")
    with open(os.path.join(str(tmpdir), "rrsymlink", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    pwd = os.getcwd()
    os.chdir(os.path.join(str(tmpdir), "rrsymlink"))
    os.symlink("foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_symlink(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_symlink(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_symlink2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrsymlink2-test.iso")
    indir = tmpdir.mkdir("rrsymlink2")
    tmpdir.mkdir("rrsymlink2/dir1")
    with open(os.path.join(str(tmpdir), "rrsymlink2", "dir1", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    pwd = os.getcwd()
    os.chdir(os.path.join(str(tmpdir), "rrsymlink2"))
    os.symlink("dir1/foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_symlink2(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_symlink2(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_symlink_dot(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrsymlinkdot-test.iso")
    indir = tmpdir.mkdir("rrsymlinkdot")
    pwd = os.getcwd()
    os.chdir(os.path.join(str(tmpdir), "rrsymlinkdot"))
    os.symlink(".", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_symlink_dot(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_symlink_dot(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_symlink_broken(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrsymlinkbroken-test.iso")
    indir = tmpdir.mkdir("rrsymlinkbroken")
    pwd = os.getcwd()
    os.chdir(os.path.join(str(tmpdir), "rrsymlinkbroken"))
    os.symlink("foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_symlink_broken(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_rr_symlink_broken(iso2, os.stat(str(testout)).st_size)

def test_parse_alternating_subdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("alternating-test.iso")
    indir = tmpdir.mkdir("alternating")
    with open(os.path.join(str(tmpdir), "alternating", "bb"), 'wb') as outfp:
        outfp.write("bb\n")
    tmpdir.mkdir("alternating/cc")
    tmpdir.mkdir("alternating/aa")
    with open(os.path.join(str(tmpdir), "alternating", "dd"), 'wb') as outfp:
        outfp.write("dd\n")
    with open(os.path.join(str(tmpdir), "alternating", "cc", "sub2"), 'wb') as outfp:
        outfp.write("sub2\n")
    with open(os.path.join(str(tmpdir), "alternating", "aa", "sub1"), 'wb') as outfp:
        outfp.write("sub1\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_alternating_subdir(iso, os.stat(str(outfile)).st_size)

    # Now round-trip through write.
    testout = tmpdir.join("writetest.iso")
    iso.write(open(str(testout), "wb"))
    iso2 = pyiso.PyIso()
    iso2.open(open(str(testout), 'rb'))
    check_alternating_subdir(iso2, os.stat(str(testout)).st_size)

def test_parse_rr_verylongname(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrverylongname-test.iso")
    indir = tmpdir.mkdir("rrverylongname")
    with open(os.path.join(str(tmpdir), "rrverylongname", "a"*255), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))
    check_rr_verylongname(iso, os.stat(str(outfile)).st_size)
