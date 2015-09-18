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

def test_hybrid_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("nofile-test.iso")
    indir = tmpdir.mkdir("nofile")
    with open(os.path.join(str(tmpdir), "nofile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_file("/FOO.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_nofile(iso, len(out.getvalue()))

def test_hybrid_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("nofile-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

def test_hybrid_twofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twofile-test.iso")
    indir = tmpdir.mkdir("twofile")
    with open(os.path.join(str(tmpdir), "twofile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_twofile(iso, len(out.getvalue()))

def test_hybrid_rmfile(tmpdir):
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

    iso.rm_file("/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

def test_hybrid_rmdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rmdir-test.iso")
    indir = tmpdir.mkdir("rmdir")
    with open(os.path.join(str(tmpdir), "rmdir", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    tmpdir.mkdir("rmdir/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_directory("/DIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile(iso, len(out.getvalue()))

def test_hybrid_remove_many(tmpdir):
    numdirs = 295
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("hybrid-manydirs-test.iso")
    indir = tmpdir.mkdir("manydirs")
    for i in range(1, 1+numdirs):
        tmpdir.mkdir("manydirs/dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Now remove all but one of the entries.
    for i in range(2, 1+numdirs):
        iso.rm_directory("/DIR" + str(i))

    out = StringIO.StringIO()
    iso.write(out)

    check_onedir(iso, len(out.getvalue()))

def test_hybrid_twoleveldeepdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeepdir-test.iso")
    indir = tmpdir.mkdir("twoleveldeep")
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1"))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.add_directory("/DIR1/SUBDIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_twoleveldeepdir(iso, len(out.getvalue()))

def test_hybrid_rmsubdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeepdir-test.iso")
    indir = tmpdir.mkdir("twoleveldeep")
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1"))
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1", "subdir1"))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_directory("/DIR1/SUBDIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onedir(iso, len(out.getvalue()))

def test_hybrid_removeall(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeepdir-test.iso")
    indir = tmpdir.mkdir("twoleveldeep")
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1"))
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1", "subdir1"))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_directory("/DIR1/SUBDIR1")
    iso.rm_directory("/DIR1")

    out = StringIO.StringIO()
    iso.write(out)

    check_nofile(iso, len(out.getvalue()))

def test_hybrid_add_new_file_to_subdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twoleveldeepdir-test.iso")
    indir = tmpdir.mkdir("twoleveldeep")
    tmpdir.mkdir(os.path.join("twoleveldeep", "dir1"))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_onefile_onedirwithfile(iso, len(out.getvalue()))

def test_hybrid_eltorito_add(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("eltoritohybrid-test.iso")
    indir = tmpdir.mkdir("eltoritohybrid")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Now add the eltorito stuff
    bootstr = "boot\n"
    iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_eltorito_nofile(iso, len(out.getvalue()))

def test_hybrid_eltorito_remove(tmpdir):
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

    iso.remove_eltorito()
    iso.rm_file("/BOOT.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_nofile(iso, len(out.getvalue()))
