from __future__ import absolute_import

import pytest
import os
import sys
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO
import struct

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pycdlib

# These are deep unit tests for the RockRidgeContinuationBlock and
# RockRidgeContinuationEntry classes.  The code in there has enough
# corner cases that they should have their own tests.

def test_rrcontentry_track_into_empty():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    assert(len(rr._entries) == 1)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)

def test_rrcontentry_track_at_end():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)
    rr.track_entry(23, 33)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_track_at_beginning():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(23, 33)
    rr.track_entry(0, 23)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_track_overlap():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO):
        rr.track_entry(22, 33)

def test_rrcontentry_track_rest():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)
    rr.track_entry(23, 2025)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 2025)

def test_rrcontentry_track_toolarge():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(0, 23)

    with pytest.raises(pycdlib.pycdlibexception.PyCdlibInvalidISO):
        rr.track_entry(23, 2026)

def test_rrcontentry_add_into_empty():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)

    assert(len(rr._entries) == 1)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)

def test_rrcontentry_add_at_end():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)
    assert(rr.add_entry(33) is not None)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_add_at_beginning():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    rr.track_entry(23, 33)
    assert(rr.add_entry(23) is not None)

    assert(len(rr._entries) == 2)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 33)

def test_rrcontentry_add_multiple():
    rr = pycdlib.rockridge.RockRidgeContinuationBlock(24, 2048)
    assert(rr.add_entry(23) is not None)
    rr.track_entry(40, 12)
    assert(rr.add_entry(12) is not None)

    assert(len(rr._entries) == 3)
    assert(rr._entries[0].offset == 0)
    assert(rr._entries[0].length == 23)
    assert(rr._entries[1].offset == 23)
    assert(rr._entries[1].length == 12)
    assert(rr._entries[2].offset == 40)
    assert(rr._entries[2].length == 12)
