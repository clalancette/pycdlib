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
    indir = tmpdir.mkdir("nofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()

    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/FOO.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_twofile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twofiles2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_twofile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twofiles3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_twofile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twofiles4(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/BAR.;1")

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_twofile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twodirs(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twodir")
    outfile = str(indir)+".iso"
    indir.mkdir("aa")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/BB")

        out = StringIO.StringIO()
        iso.write(out)

        check_twodirs(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twodirs2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twodir")
    outfile = str(indir)+".iso"
    indir.mkdir("bb")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/AA")

        out = StringIO.StringIO()
        iso.write(out)

        check_twodirs(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twodirs3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twodir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/AA")
        iso.add_directory("/BB")

        out = StringIO.StringIO()
        iso.write(out)

        check_twodirs(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twodirs4(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twodir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/BB")
        iso.add_directory("/AA")

        out = StringIO.StringIO()
        iso.write(out)

        check_twodirs(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rmfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(indir), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/BAR.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rmdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1")

        out = StringIO.StringIO()
        iso.write(out)

        check_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_remove_many(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("manydirs")
    outfile = str(indir)+".iso"
    numdirs = 295
    for i in range(1, 1+numdirs):
        indir.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        # Now remove all but one of the entries.
        for i in range(2, 1+numdirs):
            iso.rm_directory("/DIR" + str(i))

        out = StringIO.StringIO()
        iso.write(out)

        check_onedir(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_twoleveldeepdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1/SUBDIR1")

        out = StringIO.StringIO()
        iso.write(out)

        check_twoleveldeepdir(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rmsubdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir("dir1")
    dir1.mkdir("subdir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1/SUBDIR1")

        out = StringIO.StringIO()
        iso.write(out)

        check_onedir(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_removeall(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir("dir1")
    dir1.mkdir("subdir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1/SUBDIR1")
        iso.rm_directory("/DIR1")

        out = StringIO.StringIO()
        iso.write(out)

        check_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_add_new_file_to_subdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_onefile_onedirwithfile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_eltorito_add(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritohybrid")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        # Now add the eltorito stuff
        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_eltorito_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_eltorito_remove(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritonofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.remove_eltorito()
        iso.rm_file("/BOOT.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_eltorito_add(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritotwofile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    with open(os.path.join(str(indir), "aa"), 'wb') as outfp:
        outfp.write("aa\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_eltorito_twofile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrnofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/FOO.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_rmfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrrmfile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(indir), "baz"), 'wb') as outfp:
        outfp.write("baz\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/BAZ.;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefileonedir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", rr_iso_path="/dir1")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_onefileonedir(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_onefileonedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rronefileonedirwithfile")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", "/foo")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1", "/dir1/bar")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_onefileonedirwithfile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_and_joliet_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrjolietonefile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file('/FOO.;1')

        out = StringIO.StringIO()
        iso.write(out)

        check_joliet_rr_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_and_joliet_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrjolietonefile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo", rr_iso_path="/foo")

        out = StringIO.StringIO()
        iso.write(out)

        check_joliet_rr_onefile(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_and_eltorito_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritonofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_and_eltorito_nofiles(iso, len(out.getvalue()))

        iso.close()

def test_hybrid_rr_and_eltorito_nofiles2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("eltoritonofiles")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_iso_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        out = StringIO.StringIO()
        iso.write(out)

        check_rr_and_eltorito_nofiles(iso, len(out.getvalue()))

        iso.close()
