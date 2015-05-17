import pytest
import subprocess
import os
import sys

prefix = '.'
for i in range(0,3):
    if os.path.exists(os.path.join(prefix, 'pyiso.py')):
        sys.path.insert(0, prefix)
        break
    else:
        prefix = '../' + prefix

import pyiso

def test_parse_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    outfile = tmpdir.join("no-file-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    # Now open up the ISO with pyiso and check some things out.
    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # With no files, the ISO should be exactly 24 extents long.
    assert(iso.pvd.space_size == 24)
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(iso.pvd.log_block_size == 2048)
    # With no files, the path table should be exactly 10 bytes (just for the
    # root directory entry).
    assert(iso.pvd.path_tbl_size == 10)
    # The little endian version of the path table should start at extent 19.
    assert(iso.pvd.path_table_location_le == 19)
    # The big endian version of the path table should start at extent 21.
    assert(iso.pvd.path_table_location_be == 21)
    # genisoimage only supports setting the sequence number to 1
    assert(iso.pvd.seqnum == 1)
    # The root_dir_record directory record length should be exactly 34.
    assert(iso.pvd.root_dir_record.dr_len == 34)
    # The root directory should be the, erm, root.
    assert(iso.pvd.root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(iso.pvd.root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(iso.pvd.root_dir_record.file_ident == "\x00")
    # With no files, the root directory record should only have children of the
    # "dot" record and the "dotdot" record.
    assert(len(iso.pvd.root_dir_record.children) == 2)
