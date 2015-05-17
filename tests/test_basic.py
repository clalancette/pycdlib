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

def test_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage
    outfile = tmpdir.join("no-file-test.iso")
    indir = tmpdir.mkdir("nofile")
    subprocess.call(["genisoimage", "-v", "-v", "-iso-level", "1", "-no-pad",
                     "-o", str(outfile), str(indir)])

    iso = pyiso.PyIso()
    iso.open(open(str(outfile), 'rb'))

    # With no files, the ISO should be exactly 24 extents long
    assert(iso.pvd.space_size == 24)
    assert(iso.pvd.log_block_size == 2048)
    assert(iso.pvd.path_tbl_size == 10)
