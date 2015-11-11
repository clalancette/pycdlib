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
    indir = tmpdir.mkdir("nofile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_nofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_nofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_onefile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_onefile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onedir")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_onedir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_onedir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_twofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(indir), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_twofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_twofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_twodirs(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefileonedir")
    outfile = str(indir)+".iso"
    indir.mkdir("bb")
    indir.mkdir("aa")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_twodirs(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_twodirs(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefileonedir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_onefileonedir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_onefileonedir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_onefile_onedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefileonedirwithfile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    dir1 = indir.mkdir("dir1")
    with open(os.path.join(str(dir1), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_onefile_onedirwithfile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_onefile_onedirwithfile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_tendirs(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("tendirs")
    outfile = str(indir)+".iso"
    numdirs = 10
    for i in range(1, 1+numdirs):
        indir.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_tendirs(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_tendirs(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_dirs_overflow_ptr_extent(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("manydirs")
    outfile = str(indir)+".iso"
    numdirs = 295
    for i in range(1, 1+numdirs):
        indir.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_dirs_overflow_ptr_extent(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_dirs_overflow_ptr_extent(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_dirs_just_short_ptr_extent(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("manydirs")
    outfile = str(indir)+".iso"
    numdirs = 293
    for i in range(1, 1+numdirs):
        indir.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_dirs_just_short_ptr_extent(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_dirs_just_short_ptr_extent(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_twoextentfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("bigfile")
    outfile = str(indir)+".iso"
    outstr = ""
    for j in range(0, 8):
        for i in range(0, 256):
            outstr += struct.pack("=B", i)
    outstr += struct.pack("=B", 0)
    with open(os.path.join(str(indir), "bigfile"), 'wb') as outfp:
        outfp.write(outstr)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_twoextentfile(iso, outstr)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_twoextentfile(iso2, outstr)
        iso2.close()

def test_parse_twoleveldeepdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir("dir1")
    dir1.mkdir("subdir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_twoleveldeepdir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_twoleveldeepdir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_twoleveldeepfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeepfile")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir("dir1")
    subdir1 = dir1.mkdir("subdir1")
    with open(os.path.join(str(subdir1), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_twoleveldeepfile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_twoleveldeepfile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_joliet_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("joliet")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_joliet_nofiles(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_joliet_nofiles(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_joliet_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("joliet")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_joliet_onedir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_joliet_onedir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_joliet_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietfile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_joliet_onefile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_joliet_onefile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_joliet_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietfile")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_joliet_onefileonedir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_joliet_onefileonedir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_eltorito(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritonofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_eltorito_nofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_eltorito_nofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_eltorito_twofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritotwofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    with open(os.path.join(str(indir), "aa"), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_eltorito_twofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_eltorito_twofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_nofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrnofile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_nofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_nofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_onefile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_onefile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_twofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrtwofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(indir), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_twofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_twofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefileonedir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_onefileonedir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_onefileonedir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_onefileonedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefileonedirwithfile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    dir1 = indir.mkdir("dir1")
    with open(os.path.join(str(dir1), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_onefileonedirwithfile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_onefileonedirwithfile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_symlink(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrsymlink")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    pwd = os.getcwd()
    os.chdir(str(indir))
    os.symlink("foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_symlink(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_symlink(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_symlink2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrsymlink2")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir("dir1")
    with open(os.path.join(str(dir1), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    pwd = os.getcwd()
    os.chdir(str(indir))
    os.symlink("dir1/foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_symlink2(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_symlink2(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_symlink_dot(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrsymlinkdot")
    outfile = str(indir)+".iso"
    pwd = os.getcwd()
    os.chdir(str(indir))
    os.symlink(".", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_symlink_dot(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_symlink_dot(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_symlink_dotdot(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrsymlinkdotdot")
    outfile = str(indir)+".iso"
    pwd = os.getcwd()
    os.chdir(str(indir))
    os.symlink("..", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_symlink_dotdot(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_symlink_dotdot(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_symlink_broken(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrsymlinkbroken")
    outfile = str(indir)+".iso"
    pwd = os.getcwd()
    os.chdir(str(indir))
    os.symlink("foo", "sym")
    os.chdir(pwd)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_symlink_broken(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_symlink_broken(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_alternating_subdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("alternating")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "bb"), 'wb') as outfp:
        outfp.write("bb\n")
    cc = indir.mkdir("cc")
    aa = indir.mkdir("aa")
    with open(os.path.join(str(indir), "dd"), 'wb') as outfp:
        outfp.write("dd\n")
    with open(os.path.join(str(cc), "sub2"), 'wb') as outfp:
        outfp.write("sub2\n")
    with open(os.path.join(str(aa), "sub1"), 'wb') as outfp:
        outfp.write("sub1\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_alternating_subdir(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_alternating_subdir(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_verylongname(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrverylongname")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "a"*255), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_verylongname(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_verylongname(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_manylongname(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrmanylongname")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "a"*255), 'wb') as outfp:
        outfp.write("aa\n")
    with open(os.path.join(str(indir), "b"*255), 'wb') as outfp:
        outfp.write("bb\n")
    with open(os.path.join(str(indir), "c"*255), 'wb') as outfp:
        outfp.write("cc\n")
    with open(os.path.join(str(indir), "d"*255), 'wb') as outfp:
        outfp.write("dd\n")
    with open(os.path.join(str(indir), "e"*255), 'wb') as outfp:
        outfp.write("ee\n")
    with open(os.path.join(str(indir), "f"*255), 'wb') as outfp:
        outfp.write("ff\n")
    with open(os.path.join(str(indir), "g"*255), 'wb') as outfp:
        outfp.write("gg\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_manylongname(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_manylongname(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_manylongname2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrmanylongname2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "a"*255), 'wb') as outfp:
        outfp.write("aa\n")
    with open(os.path.join(str(indir), "b"*255), 'wb') as outfp:
        outfp.write("bb\n")
    with open(os.path.join(str(indir), "c"*255), 'wb') as outfp:
        outfp.write("cc\n")
    with open(os.path.join(str(indir), "d"*255), 'wb') as outfp:
        outfp.write("dd\n")
    with open(os.path.join(str(indir), "e"*255), 'wb') as outfp:
        outfp.write("ee\n")
    with open(os.path.join(str(indir), "f"*255), 'wb') as outfp:
        outfp.write("ff\n")
    with open(os.path.join(str(indir), "g"*255), 'wb') as outfp:
        outfp.write("gg\n")
    with open(os.path.join(str(indir), "h"*255), 'wb') as outfp:
        outfp.write("hh\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_manylongname2(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_manylongname2(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_joliet_rr_nofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrjolietnofile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-J", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_joliet_rr_nofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_joliet_rr_nofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()

def test_parse_rr_and_eltorito_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritonofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    testout = tmpdir.join("writetest.iso")

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)
        check_rr_and_eltorito_nofile(iso, os.fstat(fp.fileno()).st_size)

        with open(str(testout), 'wb') as outfp:
            iso.write(outfp)
        iso.close()

    # Now round-trip through write.
    iso2 = pyiso.PyIso()
    with open(str(testout), 'rb') as fp:
        iso2.open(fp)
        check_rr_and_eltorito_nofile(iso2, os.fstat(fp.fileno()).st_size)
        iso2.close()
