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
