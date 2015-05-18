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

def test_parse_invalid_file(tmpdir):
    iso = pyiso.PyIso()
    with pytest.raises(AttributeError):
        iso.open(None)

    with pytest.raises(AttributeError):
        iso.open('foo')

def check_pvd(pvd, size, path_table_size):
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(pvd.log_block_size == 2048)
    # The little endian version of the path table should start at extent 19.
    assert(pvd.path_table_location_le == 19)
    # The big endian version of the path table should start at extent 21.
    assert(pvd.path_table_location_be == 21)
    # genisoimage only supports setting the sequence number to 1
    assert(pvd.seqnum == 1)

    assert(pvd.space_size == size)
    assert(pvd.path_tbl_size == path_table_size)

def check_root_dir_record(root_dir_record, num_children):
    # The root_dir_record directory record length should be exactly 34.
    assert(root_dir_record.dr_len == 34)
    # The root directory should be the, erm, root.
    assert(root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(root_dir_record.file_ident == "\x00")

    assert(len(root_dir_record.children) == num_children)

def check_common_dot_dir_record(dot_record):
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34.
    assert(dot_record.dr_len == 34)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)

def check_common_dotdot_dir_record(dotdot_record):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == "\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34.
    assert(dotdot_record.dr_len == 34)
    # The "dotdot" directory record is not the root.
    assert(dotdot_record.is_root == False)
    # The "dotdot" directory record should have no children.
    assert(len(dotdot_record.children) == 0)

def check_file_contents(iso, path, contents):
    out = StringIO.StringIO()
    iso.get_and_write(path, out)
    assert(out.getvalue() == contents)

def test_parse_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("nofile-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.  With no files, the ISO should be 24 extents
    # (the metadata), and the path table should be exactly 10 bytes (the root
    # directory entry).
    check_pvd(iso.pvd, 24, 10)

    # Now check the root directory record.  With no files, the root directory
    # record should have "dot" and "dotdot" as children.
    check_root_dir_record(iso.pvd.root_dir_record, 2)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO", StringIO.StringIO())

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

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be exactly 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 25, 10)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 40)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")

    out = StringIO.StringIO()
    # Make sure trying to get a non-existent file raises an exception
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/BAR", out)

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
    check_pvd(iso.pvd, 26, 10)

    # Now check the root directory record.  With two files at the root, the
    # root directory record should have "dot", "dotdot", and the two files as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 4)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

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
    check_pvd(iso.pvd, 26, 22)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the one
    # file, and the one directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

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
    # The "dir1" directory record should have a valid "dot" record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

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
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")

    # Check to make sure accessing a directory raises an exception.
    out = StringIO.StringIO()
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/DIR1", out)

def test_parse_onefile_onedirwithfile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("onefileonedir-test.iso")
    indir = tmpdir.mkdir("onefileonedir")
    outfp = open(os.path.join(str(tmpdir), "onefileonedir", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    tmpdir.mkdir("onefileonedir/dir1")
    outfp = open(os.path.join(str(tmpdir), "onefileonedir", "dir1", "bar"), 'wb')
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
    check_pvd(iso.pvd, 27, 22)

    # Now check the root directory record.  With one file and one directory at
    # the root, the root directory record should have "dot", "dotdot", the file,
    # and the directory as children.
    check_root_dir_record(iso.pvd.root_dir_record, 4)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

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
    # The "dir1" directory record should have a valid "dot" record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[2].children[0])
    # The "dir1" directory record should have a valid "dotdot" record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[2].children[1])

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
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/DIR1/BAR", "bar\n")

def test_new_nofiles():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()

    # Do checks on the PVD.  With no files, the ISO should be 24 extents.
    # The path table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 24, 10)

    # Now check the root directory record.  With no files, the root directory
    # record should have "dot" and "dotdot" as children.
    check_root_dir_record(iso.pvd.root_dir_record, 2)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/FOO", StringIO.StringIO())

def test_new_onefile():
    # Create a new ISO.
    iso = pyiso.PyIso()
    iso.new()
    mystr = "foo\n"
    out = StringIO.StringIO(mystr)
    # Add a file.
    iso.add_fp(out, len(mystr), "/FOO")

    # Do checks on the PVD.  With one file, the ISO should be 25 extents (24
    # extents for the metadata, and 1 extent for the short file).  The path
    # table should be 10 bytes (for the root directory entry).
    check_pvd(iso.pvd, 25, 10)

    # Now check the root directory record.  With one file at the root, the
    # root directory record should have "dot", "dotdot", and the file as
    # children.
    check_root_dir_record(iso.pvd.root_dir_record, 3)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # The "foo" file should not have any children.
    assert(len(iso.pvd.root_dir_record.children[2].children) == 0)
    # The "foo" file should not be a directory.
    assert(iso.pvd.root_dir_record.children[2].isdir == False)
    # The "foo" file should not be the root.
    assert(iso.pvd.root_dir_record.children[2].is_root == False)
    # The "foo" file should have an ISO9660 mangled name of "FOO.;1".
    assert(iso.pvd.root_dir_record.children[2].file_ident == "FOO.;1")
    # The "foo" directory record should have a length of 40.
    assert(iso.pvd.root_dir_record.children[2].dr_len == 40)
    # Make sure getting the data from the foo file works, and returns the right
    # thing.
    check_file_contents(iso, "/FOO", "foo\n")
