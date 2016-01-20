import pytest
import subprocess
import os
import sys
import StringIO
import shutil

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

    iso2 = pyiso.PyIso()
    iso2.open(out)
    check_func(iso2, len(out.getvalue()))
    iso2.close()

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

        do_a_test(iso, check_nofiles)

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

        do_a_test(iso, check_onefile)

        iso.close()

def test_hybrid_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("onefile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        do_a_test(iso, check_onedir)

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

        do_a_test(iso, check_twofiles)

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

        do_a_test(iso, check_twofiles)

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

        do_a_test(iso, check_twofiles)

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

        do_a_test(iso, check_twofiles)

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

        do_a_test(iso, check_twodirs)

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

        do_a_test(iso, check_twodirs)

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

        do_a_test(iso, check_twodirs)

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

        do_a_test(iso, check_twodirs)

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

        do_a_test(iso, check_onefile)

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

        do_a_test(iso, check_onefile)

        iso.close()

def test_hybrid_onefileonedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        do_a_test(iso, check_onefileonedir)

        iso.close()

def test_hybrid_onefileonedir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        do_a_test(iso, check_onefileonedir)

        iso.close()

def test_hybrid_onefileonedir3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        do_a_test(iso, check_onefileonedir)

        iso.close()

def test_hybrid_onefileonedir4(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        iso.add_directory("/DIR1")

        do_a_test(iso, check_onefileonedir)

        iso.close()

def test_hybrid_onefile_onedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

        do_a_test(iso, check_onefile_onedirwithfile)

        iso.close()

def test_hybrid_onefile_onedirwithfile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    indir.mkdir('dir1')
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

        do_a_test(iso, check_onefile_onedirwithfile)

        iso.close()

def test_hybrid_onefile_onedirwithfile3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        iso.add_directory("/DIR1")

        barstr = "bar\n"
        iso.add_fp(StringIO.StringIO(barstr), len(barstr), "/DIR1/BAR.;1")

        do_a_test(iso, check_onefile_onedirwithfile)

        iso.close()

def test_hybrid_onefile_onedirwithfile4(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    dir1 = indir.mkdir('dir1')
    with open(os.path.join(str(dir1), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        do_a_test(iso, check_onefile_onedirwithfile)

        iso.close()

def test_hybrid_twoextentfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rmdir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        outstr = ""
        for j in range(0, 8):
            for i in range(0, 256):
                outstr += struct.pack("=B", i)
        outstr += struct.pack("=B", 0)

        iso.add_fp(StringIO.StringIO(outstr), len(outstr), "/BIGFILE.;1")

        do_a_test(iso, check_twoextentfile)

        iso.close()

def test_hybrid_ptr_extent(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("manydirs")
    outfile = str(indir)+".iso"
    numdirs = 293
    for i in range(1, 1+numdirs):
        indir.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR294")
        iso.add_directory("/DIR295")

        do_a_test(iso, check_dirs_overflow_ptr_extent)

        iso.close()

def test_hybrid_ptr_extent2(tmpdir):
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

        iso.rm_directory("/DIR294")
        iso.rm_directory("/DIR295")

        do_a_test(iso, check_dirs_just_short_ptr_extent)

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

        do_a_test(iso, check_onedir)

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

        do_a_test(iso, check_twoleveldeepdir)

        iso.close()

def test_hybrid_twoleveldeepdir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("twoleveldeep")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        iso.add_directory("/DIR1/SUBDIR1")

        do_a_test(iso, check_twoleveldeepdir)

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

        do_a_test(iso, check_onedir)

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

        do_a_test(iso, check_nofiles)

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

        do_a_test(iso, check_onefile_onedirwithfile)

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

        do_a_test(iso, check_eltorito_nofiles)

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

        iso.rm_eltorito()
        iso.rm_file("/BOOT.;1")

        do_a_test(iso, check_nofiles)

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

        do_a_test(iso, check_eltorito_twofile)

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

        do_a_test(iso, check_rr_nofiles)

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

        do_a_test(iso, check_rr_onefile)

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

        do_a_test(iso, check_rr_onefile)

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

        iso.add_directory("/DIR1", rr_path="/dir1")

        do_a_test(iso, check_rr_onefileonedir)

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

        do_a_test(iso, check_rr_onefileonedirwithfile)

        iso.close()

def test_hybrid_rr_and_joliet_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrjolietnofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file('/FOO.;1', joliet_path="/foo")

        do_a_test(iso, check_joliet_and_rr_nofiles)

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
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

        do_a_test(iso, check_joliet_and_rr_onefile)

        iso.close()

def test_hybrid_rr_and_eltorito_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritonofiles")
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

        do_a_test(iso, check_rr_and_eltorito_nofiles)

        iso.close()

def test_hybrid_rr_and_eltorito_nofiles2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritonofiles2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_rr_and_eltorito_nofiles)

        iso.close()

def test_hybrid_rr_and_eltorito_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonefile")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo")

        do_a_test(iso, check_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_rr_and_eltorito_onefile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonefile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_rr_and_eltorito_onefile3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonefile3")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo")

        do_a_test(iso, check_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_rr_and_eltorito_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonedir")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        iso.add_directory("/DIR1", rr_path="/dir1")

        do_a_test(iso, check_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_rr_and_eltorito_onedir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonedir2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", rr_path="/dir1")

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_rr_and_eltorito_onedir3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonedir3")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot")
        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_rr_and_eltorito_onedir4(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritoonedir4")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", rr_path="/dir1")

        do_a_test(iso, check_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_rr_and_eltorito_rmdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritormdir")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1")

        do_a_test(iso, check_rr_and_eltorito_nofiles)

        iso.close()

def test_hybrid_rr_and_eltorito_rmdir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rreltoritormdir2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    dir1 = indir.mkdir("dir1")
    dir1.mkdir("subdir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1/SUBDIR1")

        do_a_test(iso, check_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_joliet_and_eltorito_remove(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoremove")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_eltorito()

        iso.rm_file("/BOOT.;1", joliet_path="/boot")

        do_a_test(iso, check_joliet_nofiles)

        iso.close()

def test_hybrid_joliet_and_eltorito_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoonefile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

        do_a_test(iso, check_joliet_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_and_eltorito_onefile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoonefile2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_and_eltorito_onefile3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoonefile3")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_and_eltorito_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoonedir")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_and_eltorito_onedir)

        iso.close()

def test_hybrid_joliet_and_eltorito_onedir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolieteltoritoonedir2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", joliet_path="/dir1")

        do_a_test(iso, check_joliet_and_eltorito_onedir)

        iso.close()

def test_hybrid_isohybrid(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("isohybrid")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

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

        iso.close()

def test_hybrid_isohybrid2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("isohybrid")
    outfile = str(indir)+".iso"
    shutil.copyfile('/usr/share/syslinux/isolinux.bin', os.path.join(str(indir), 'isolinux.bin'))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "isolinux.bin", "-no-emul-boot",
                     "-boot-load-size", "4",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        # Now add the syslinux
        isohybrid_fp = open('/usr/share/syslinux/isohdpfx.bin', 'rb')
        iso.add_isohybrid(isohybrid_fp)

        do_a_test(iso, check_isohybrid)

        isohybrid_fp.close()

        iso.close()

def test_hybrid_isohybrid3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("isohybrid")
    outfile = str(indir)+".iso"
    shutil.copyfile('/usr/share/syslinux/isolinux.bin', os.path.join(str(indir), 'isolinux.bin'))
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "isolinux.bin", "-no-emul-boot",
                     "-boot-load-size", "4",
                     "-o", str(outfile), str(indir)])
    subprocess.call(["isohybrid", "-v", str(outfile)])

    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_isohybrid()

        iso.rm_eltorito()
        iso.rm_file('/ISOLINUX.BIN;1')

        do_a_test(iso, check_nofiles)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritonofiles")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/FOO.;1", joliet_path="/foo")

        do_a_test(iso, check_joliet_rr_and_eltorito_nofiles)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_nofiles2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritonofiles2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_rr_and_eltorito_nofiles)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonefile")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

        do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onefile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonefile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onefile3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonefile3")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", rr_path="/foo", joliet_path="/foo")

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_rr_and_eltorito_onefile)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonedir")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onedir2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonedir2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        bootstr = "boot\n"
        iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), "/BOOT.;1", rr_path="/boot", joliet_path="/boot")

        iso.add_eltorito("/BOOT.;1", "/BOOT.CAT;1")

        iso.add_directory("/DIR1", rr_path="/dir1", joliet_path="/dir1")

        do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_joliet_rr_and_eltorito_onedir3(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("jolietrreltoritoonedir2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "boot"), 'wb') as outfp:
        outfp.write("boot\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-c", "boot.cat", "-b", "boot", "-no-emul-boot",
                     "-J", "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", rr_path="/dir1", joliet_path="/dir1")

        do_a_test(iso, check_joliet_rr_and_eltorito_onedir)

        iso.close()

def test_hybrid_rr_rmfile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrrmfile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/FOO.;1", rr_path="/foo")

        do_a_test(iso, check_rr_nofiles)

        iso.close()

def test_hybrid_rr_rmdir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("rrrmfile2")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1", rr_path="/dir1")

        do_a_test(iso, check_rr_nofiles)

        iso.close()

def test_hybrid_xa_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    indir.mkdir("dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1")

        do_a_test(iso, check_xa_nofiles)

        iso.close()

def test_hybrid_xa_nofiles2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file("/FOO.;1")

        do_a_test(iso, check_xa_nofiles)

        iso.close()

def test_hybrid_xa_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1")

        do_a_test(iso, check_xa_onefile)

        iso.close()

def test_hybrid_xa_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1")

        do_a_test(iso, check_xa_onedir)

        iso.close()

def test_hybrid_sevendeepdirs(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("sevendeepdirs")
    outfile = str(indir)+".iso"
    numdirs = 8
    x = indir
    for i in range(1, 1+numdirs):
        x = x.mkdir("dir%d" % i)
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-rational-rock", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory("/DIR1/DIR2/DIR3/DIR4/DIR5/DIR6/DIR7/DIR8")

        do_a_test(iso, check_sevendeepdirs)

        iso.close()

def test_hybrid_xa_joliet_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.add_directory("/DIR1", joliet_path="/dir1")

        do_a_test(iso, check_xa_joliet_onedir)

        iso.close()

def test_hybrid_xa_joliet_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-xa", "-J", "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        foostr = "foo\n"
        iso.add_fp(StringIO.StringIO(foostr), len(foostr), "/FOO.;1", joliet_path="/foo")

        do_a_test(iso, check_xa_joliet_onefile)

        iso.close()

def test_hybrid_isolevel4_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    with open(os.path.join(str(indir), "bar"), 'wb') as outfp:
        outfp.write("bar\n")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "4", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_file('/bar')

        do_a_test(iso, check_isolevel4_onefile)

        iso.close()

def test_hybrid_isolevel4_onefile2(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir("xarmfile2")
    outfile = str(indir)+".iso"
    with open(os.path.join(str(indir), "foo"), 'wb') as outfp:
        outfp.write("foo\n")
    indir.mkdir('dir1')
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "4", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    with open(str(outfile), 'rb') as fp:
        iso.open(fp)

        iso.rm_directory('/dir1')

        do_a_test(iso, check_isolevel4_onefile)

        iso.close()
