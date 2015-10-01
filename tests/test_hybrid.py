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

def test_hybrid_eltorito_add(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("eltoritotwofile-test.iso")
    indir = tmpdir.mkdir("eltoritotwofile")
    with open(os.path.join(str(tmpdir), "eltoritotwofile", "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    with open(os.path.join(str(tmpdir), "eltoritotwofile", "aa"), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_eltorito_twofile(iso, len(out.getvalue()))

def test_hybrid_rr_nofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrnofile-test.iso")
    indir = tmpdir.mkdir("rrnofile")
    with open(os.path.join(str(tmpdir), "rrnofile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_file("/FOO.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_nofile(iso, len(out.getvalue()))

def test_hybrid_rr_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefile-test.iso")
    indir = tmpdir.mkdir("rronefile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefile(iso, len(out.getvalue()))

def test_hybrid_rr_rmfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rrrmfile-test.iso")
    indir = tmpdir.mkdir("rrrmfile")
    with open(os.path.join(str(tmpdir), "rrrmfile", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(tmpdir), "rrrmfile", "baz"), 'wb') as outfp:
        outfp.write("baz\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.rm_file("/BAZ.;1")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefile(iso, len(out.getvalue()))

def test_hybrid_rr_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefileonedir-test.iso")
    indir = tmpdir.mkdir("rronefileonedir")
    with open(os.path.join(str(tmpdir), "rronefileonedir", "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    iso.add_directory("/DIR1", rr_iso_path="/dir1")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefileonedir(iso, len(out.getvalue()))

def test_hybrid_rr_onefileonedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("rronefileonedirwithfile-test.iso")
    indir = tmpdir.mkdir("rronefileonedirwithfile")
    tmpdir.mkdir("rronefileonedirwithfile/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    foostr = "foo\n"
    iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

    barstr = "bar\n"
    iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1", "/dir1/bar")

    out = StringIO.StringIO()
    iso.write(out)

    check_rr_onefileonedirwithfile(iso, len(out.getvalue()))
