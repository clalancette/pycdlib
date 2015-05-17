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

def check_common_pvd(pvd):
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(pvd.log_block_size == 2048)
    # The little endian version of the path table should start at extent 19.
    assert(pvd.path_table_location_le == 19)
    # The big endian version of the path table should start at extent 21.
    assert(pvd.path_table_location_be == 21)
    # genisoimage only supports setting the sequence number to 1
    assert(pvd.seqnum == 1)

def check_common_root_dir_record(root_dir_record):
    # The root_dir_record directory record length should be exactly 34.
    assert(root_dir_record.dr_len == 34)
    # The root directory should be the, erm, root.
    assert(root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(root_dir_record.file_ident == "\x00")

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

def test_parse_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("no-file-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.
    check_common_pvd(iso.pvd)
    # With no files, the ISO should be exactly 24 extents long.
    assert(iso.pvd.space_size == 24)
    # With no files, the path table should be exactly 10 bytes (just for the
    # root directory entry).
    assert(iso.pvd.path_tbl_size == 10)

    # Now check the root directory record.
    check_common_root_dir_record(iso.pvd.root_dir_record)
    # With no files, the root directory record should only have children of the
    # "dot" record and the "dotdot" record.
    assert(len(iso.pvd.root_dir_record.children) == 2)

    # Now check the "dot" directory record.
    check_common_dot_dir_record(iso.pvd.root_dir_record.children[0])

    # Now check the "dotdot" directory record.
    check_common_dotdot_dir_record(iso.pvd.root_dir_record.children[1])

    # Check to make sure accessing a missing file results in an exception.
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/foo", StringIO.StringIO())

def test_parse_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("one-file-test.iso")
    indir = tmpdir.mkdir("onefile")
    outfp = open(os.path.join(str(tmpdir), "onefile", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.
    check_common_pvd(iso.pvd)
    # With one file, the ISO should be exactly 25 extents long (24 extents for
    # all of the metadata, then 1 extent for the short file).
    assert(iso.pvd.space_size == 25)
    # With one file, the path table should be exactly 10 bytes (just for the
    # root directory entry).
    assert(iso.pvd.path_tbl_size == 10)

    # Now check the root directory record.
    check_common_root_dir_record(iso.pvd.root_dir_record)
    # With one file at the root, the root directory record should have children
    # of the "dot" record, the "dotdot" record, and the file.
    assert(len(iso.pvd.root_dir_record.children) == 3)

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
    out = StringIO.StringIO()
    iso.get_and_write("/foo", out)
    assert(out.getvalue() == "foo\n")

    # Make sure trying to get a non-existent file raises an exception
    with pytest.raises(pyiso.PyIsoException):
        iso.get_and_write("/bar", out)

def test_parse_twofile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("one-file-test.iso")
    indir = tmpdir.mkdir("onefile")
    outfp = open(os.path.join(str(tmpdir), "onefile", "foo"), 'wb')
    outfp.write("foo\n")
    outfp.close()
    outfp = open(os.path.join(str(tmpdir), "onefile", "bar"), 'wb')
    outfp.write("bar\n")
    outfp.close()
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # Do checks on the PVD.
    check_common_pvd(iso.pvd)
    # With two files, the ISO should be exactly 26 extents long (24 extents for
    # all of the metadata, then 1 extent for each of the two short files).
    assert(iso.pvd.space_size == 26)
    # With one file, the path table should be exactly 10 bytes (just for the
    # root directory entry).
    assert(iso.pvd.path_tbl_size == 10)

    # Now check the root directory record.
    check_common_root_dir_record(iso.pvd.root_dir_record)
    # With one file at the root, the root directory record should have children
    # of the "dot" record, the "dotdot" record, and the file.
    assert(len(iso.pvd.root_dir_record.children) == 4)

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
    out = StringIO.StringIO()
    iso.get_and_write("/foo", out)
    assert(out.getvalue() == "foo\n")

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
    out = StringIO.StringIO()
    iso.get_and_write("/bar", out)
    assert(out.getvalue() == "bar\n")
