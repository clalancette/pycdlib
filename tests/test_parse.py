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

    check_nofile(iso)

def test_parse_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefile-test.iso")
    indir = tmpdir.mkdir("onefile")
    outfp = open(os.path.join(str(tmpdir), "onefile", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    check_onefile(iso)

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

    check_onedir(iso)

def test_parse_twofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("twofile-test.iso")
    indir = tmpdir.mkdir("twofile")
    outfp = open(os.path.join(str(tmpdir), "twofile", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    outfp = open(os.path.join(str(tmpdir), "twofile", "bar"), 'wb')
    outfp.write("bar\n")
    outfp.close()
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.  With two files, the ISO should be 26 extents (24
    # extents for the metadata, and 1 extent for each of the two short files).
    # The path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 26, 10, 21)

    # Now check the root directory record.  With two files at the root, the
    # root directory record should have "dot", "dotdot", and the two files as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")

    # The "bar" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "bar" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "bar" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "bar" file should have an ISO9660 mangled name of "BAR.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "BAR.;1")
    # The "bar" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 40)
    # The "bar" data should start at extent 24.
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # Make sure getting the data from the bar file works, and returns the right
    # thing.
    check_file_contents(iso, "/BAR", "bar\n")

def test_parse_onefile_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefileonedir-test.iso")
    indir = tmpdir.mkdir("onefileonedir")
    outfp = open(os.path.join(str(tmpdir), "onefileonedir", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    tmpdir.mkdir("onefileonedir/dir1")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.  With one file and one directory, the ISO should be
    # 26 extents (24 extents for the metadata, 1 extent for the file, and 1
    # extent for the extra directory).  The path table should be 22 bytes (10
    # bytes for the root directory entry, and 12 bytes for the "dir1" entry).
    check_pvd(iso.pvd, 26, 22, 21)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the one
    # file, and the one directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # The "dir1" directory should have two children (the "dot" and the "dotdot"
    # entries).
    assert(len(iso.pvd.root_dir_record.children[2].children) == 2)
    # The "dir1" directory should be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == True)
    # The "dir1" directory should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "DIR1")
    # The "dir1" directory record should have a length of 38.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 38)
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")

    # Check to make sure accessing a directory raises an exception.
    out = StringIO.StringIO()
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/DIR1", out)

def test_parse_onefile_onedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefileonedirwithfile-test.iso")
    indir = tmpdir.mkdir("onefileonedirwithfile")
    outfp = open(os.path.join(str(tmpdir), "onefileonedirwithfile", "foo"),
                 'wb')
    outfp.write("foo\n")
    outfp.close()
    tmpdir.mkdir("onefileonedirwithfile/dir1")
    outfp = open(os.path.join(str(tmpdir), "onefileonedirwithfile", "dir1",
                              "bar"), 'wb')
    outfp.write("bar\n")
    outfp.close()
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.  With one file and one directory with a file, the
    # ISO should be 27 extents (24 extents for the metadata, 1 extent for the
    # file, 1 extent for the directory, and 1 more extent for the file.  The
    # path table should be 22 bytes (10 bytes for the root directory entry, and
    # 12 bytes for the "dir1" entry).
    check_pvd(iso.pvd, 27, 22, 21)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the file,
    # and the directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # The "dir1" directory should have three children (the "dot", the "dotdot"
    # and the "bar" entries).
    assert(len(iso.pvd.root_dir_record.children[2].children) == 3)
    # The "dir1" directory should be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == True)
    # The "dir1" directory should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "dir1" directory should have an ISO9660 mangled name of "DIR1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "DIR1")
    # The "dir1" directory record should have a length of 38.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 38)
    # The "dir1" directory record should be at extent 24 (right after the little
    # endian and big endian path table entries).
    assert(iso.pvd.root_dir_record.children[2].extent_location() == 24)
    # The "dir1" directory record should have a valid "dot" record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[3].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[3].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[3].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[3].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[3].dr_len == 40)
    # The "foo" data should start at extent 25.
    assert(iso.pvd.root_dir_record.children[3].extent_location() == 25)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")

    # The "bar" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children[2].children) == 0)
    # The "bar" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].children[2].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].children[2].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "BAR.;1".
    assert(iso.pvd.root_dir_record.children[2].children[2].file_ident == "BAR.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].children[2].dr_len == 40)
    # The "bar" data should start at extent 26.
    assert(iso.pvd.root_dir_record.children[2].children[2].extent_location() == 26)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/DIR1/BAR", "bar\n")

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

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 34, 132, 21)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 12, 2048, 23)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append("DIR%d" % i)
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    for index in range(2, 2+numdirs):
        # The "dir?" directory should have two children (the "dot", and the
        # "dotdot" entries).
        assert(len(iso.pvd.root_dir_record.children[index].children) == 2)
        # The "dir?" directory should be a directory.
        assert(iso.pvd.root_dir_record.children[index].isdir == True)
        # The "dir?" directory should not be the root.
        assert(iso.pvd.root_dir_record.children[index].is_root == False)
        # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
        assert(iso.pvd.root_dir_record.children[index].file_ident == names[index])
        # The "dir?" directory record should have a length of 38.
        assert(iso.pvd.root_dir_record.children[index].dr_len == 38)
        # The "dir?" directory record should have a valid "dot" record.
        check_dot_dir_record(iso.pvd.root_dir_record.children[index].children[0])
        # The "dir?" directory record should have a valid "dotdot" record.
        check_dotdot_dir_record(iso.pvd.root_dir_record.children[index].children[1])

def test_parse_manydirs(tmpdir):
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

    # Do checks on the PVD.  With ten directories, the ISO should be 35 extents
    # (24 extents for the metadata, and 1 extent for each of the ten
    # directories).  The path table should be 132 bytes (10 bytes for the root
    # directory entry, and 12 bytes for each of the first nine "dir?" records,
    # and 14 bytes for the last "dir10" record).
    check_pvd(iso.pvd, 328, 4122, 23)

    # Now check the root directory record.  With ten directories at at the root,
    # the root directory record should have "dot", "dotdot", and the ten
    # directories as children.
    check_root_dir_record(iso.pvd.root_dir_record, 297, 12288, 27)

    # Now check the "dot" directory record.
    check_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    tmp = []
    for i in range(1, 1+numdirs):
        tmp.append("DIR%d" % i)
    names = sorted(tmp)
    names.insert(0, None)
    names.insert(0, None)
    for index in range(2, 2+numdirs):
        # The "dir?" directory should have two children (the "dot", and the
        # "dotdot" entries).
        assert(len(iso.pvd.root_dir_record.children[index].children) == 2)
        # The "dir?" directory should be a directory.
        assert(iso.pvd.root_dir_record.children[index].isdir == True)
        # The "dir?" directory should not be the root.
        assert(iso.pvd.root_dir_record.children[index].is_root == False)
        # The "dir?" directory should have an ISO9660 mangled name of "DIR?".
        assert(iso.pvd.root_dir_record.children[index].file_ident == names[index])
        # The "dir?" directory record should have a length of 38.
        assert(iso.pvd.root_dir_record.children[index].dr_len == (33 + len(names[index]) + (1 - (len(names[index]) % 2))))
        # The "dir?" directory record should have a valid "dot" record.
        check_dot_dir_record(iso.pvd.root_dir_record.children[index].children[0])
        # The "dir?" directory record should have a valid "dotdot" record.
        check_dotdot_dir_record(iso.pvd.root_dir_record.children[index].children[1])
