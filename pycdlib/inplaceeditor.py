# Copyright (c) 2015-2026 Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
Focused in-place editing of an existing ISO.

This module hosts the implementation behind PyCdlib's older
``modify_file_in_place`` method, together with a context-manager-shaped
public API (:class:`InPlaceEditor`).

The split exists because in-place editing is a fundamentally different
concept from the mastering APIs on :class:`pycdlib.PyCdlib` (``add_*`` /
``rm_*`` / ``write_fp``) and combining the two on the same PyCdlib
object has historically produced silent disk corruption.  Keeping the
in-place primitives on their own focused class makes the misuse
impossible to express at the API level: the editor doesn't expose any
of the mastering methods, so you can't accidentally interleave them.
"""

import time
from typing import TYPE_CHECKING

from pycdlib import dr
from pycdlib import inode
from pycdlib import pycdlibexception
from pycdlib import udf as udfmod
from pycdlib import utils
from pycdlib.pycdlib import PyCdlib

if TYPE_CHECKING:
    from typing import BinaryIO, Literal, Optional, Union  # noqa: F401


def _do_modify_file_in_place(iso, fp, length, iso_path, rr_name=None,  # pylint: disable=unused-argument
                             joliet_path=None, udf_path=None):          # pylint: disable=unused-argument
    # type: (PyCdlib, BinaryIO, int, str, Optional[str], Optional[str], Optional[str]) -> None
    """
    Implementation of in-place modification of a file's bytes.  Operates
    on an open :class:`pycdlib.PyCdlib` object's internal state; not a
    public API.  Used by both :class:`InPlaceEditor` and the deprecated
    :meth:`pycdlib.PyCdlib.modify_file_in_place` wrapper.

    The constraints documented on the public-facing wrappers apply here:
    the file must exist on the ISO, must not be a directory, and the new
    content must occupy the same number of extents as the old content.
    """
    if not iso._initialized:  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('This object is not initialized; call either open() or new() to create an ISO')

    if hasattr(iso._cdfp, 'mode') and not iso._cdfp.mode.startswith(('r+', 'w', 'a', 'rb+')):  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

    child = iso._find_iso_record(utils.normpath(iso_path))  # pylint: disable=protected-access

    old_num_extents = utils.ceiling_div(child.get_data_length(),
                                        iso.logical_block_size)
    new_num_extents = utils.ceiling_div(length, iso.logical_block_size)

    # Growing the file's extent count is rejected: the next on-disk
    # extent belongs to whatever sits after this file in the volume
    # layout, and writing into it would corrupt that data.  Shrinking
    # is allowed -- the orphaned extents inside the file's original
    # allocation get zeroed below so we don't leak the old content.
    if new_num_extents > old_num_extents:
        raise pycdlibexception.PyCdlibInvalidInput('When modifying a file in-place, the number of extents for a file cannot grow!')

    if not child.is_file():
        raise pycdlibexception.PyCdlibInvalidInput('Cannot modify a directory with modify_file_in_place')

    if child.inode is None:
        raise pycdlibexception.PyCdlibInternalError('Child file found without inode')

    child.inode.update_fp(fp, length)

    # The file's on-disk extent allocation does not change: even on a
    # shrink, the orphaned extents stay part of the volume (just
    # unreferenced).  So we deliberately do not adjust PVD or Joliet
    # space_size here -- decreasing them would tell the parser the
    # volume is smaller than it is, truncating any file laid out past
    # the file we just shrunk.

    # If we made it here, we have successfully updated all of the in-memory
    # metadata.  Now we can go and modify the on-disk file.

    iso._seek_to_extent(iso.pvd.extent_location())  # pylint: disable=protected-access

    # First write out the PVD.
    rec = iso.pvd.record()
    iso._cdfp.write(rec)  # pylint: disable=protected-access

    # Write out the joliet VD.
    if iso.joliet_vd is not None:
        iso._seek_to_extent(iso.joliet_vd.extent_location())  # pylint: disable=protected-access
        rec = iso.joliet_vd.record()
        iso._cdfp.write(rec)  # pylint: disable=protected-access

    # Write out the enhanced VD.
    if iso.enhanced_vd is not None:
        iso._seek_to_extent(iso.enhanced_vd.extent_location())  # pylint: disable=protected-access
        rec = iso.enhanced_vd.record()
        iso._cdfp.write(rec)  # pylint: disable=protected-access

    # The UDF anchors, descriptors, and partition length aren't
    # affected -- the file's on-disk extent allocation is unchanged.
    # Only the UDF File Entry's data_length needs updating, which we
    # handle below alongside the ISO9660/Joliet records.

    # Write out the actual file contents.
    iso._seek_to_extent(child.extent_location())  # pylint: disable=protected-access
    with inode.InodeOpenData(child.inode, iso.logical_block_size) as (data_fp, data_len):
        utils.copy_data(data_len, iso.logical_block_size, data_fp, iso._cdfp)  # pylint: disable=protected-access
        utils.zero_pad(iso._cdfp, data_len, iso.logical_block_size)  # pylint: disable=protected-access

    # If the new content uses fewer extents than the old, the file's
    # original allocation still holds the tail of the old content past
    # the new (now shorter) data length.  Zero those orphaned extents
    # so we don't leak the old data into the volume.
    if new_num_extents < old_num_extents:
        orphan_extents = old_num_extents - new_num_extents
        iso._cdfp.write(b'\x00' * (orphan_extents * iso.logical_block_size))  # pylint: disable=protected-access

    # Finally update the directory record entries that reference this
    # file with the new length.  For UDF the file entry has its own
    # extent, so we can write it directly.  For ISO9660/Joliet the
    # record lives inside its parent's directory extent; we used to
    # compute that record's byte offset from extents_to_here /
    # offset_to_here (which reflect pycdlib's in-memory sorted order
    # of children), but the on-disk order doesn't always match the
    # sorted order -- writing to the computed offset then corrupts
    # whichever sibling actually sits at that on-disk position
    # (issue #122).  Rewrite the parent's full child list instead.
    rewritten_parents = set()  # type: set
    for record, is_pvd_unused in child.inode.linked_records:
        if isinstance(record, dr.DirectoryRecord):
            if record.parent is None:
                raise pycdlibexception.PyCdlibInternalError('Modifying file with empty parent')
            record.set_data_length(length)
            # Walk up the parent chain, rewriting each ancestor's
            # extent.  The immediate parent's rewrite captures the
            # modified file's new data_length; each higher
            # ancestor's rewrite captures the data_length of its
            # child (which may have shrunk via _remove_child's
            # underflow handler when a sibling was removed).
            # Without the up-walk, an in-memory data_length change
            # never reaches the on-disk record that the parser
            # uses to bound the data extent, and the parser reads
            # stale bytes from a dropped extent.  We stop at the
            # root: the root's data_length lives in the PVD's
            # root_directory_record, which is already written out
            # earlier in this function.
            node = record.parent  # type: Optional[dr.DirectoryRecord]
            while node is not None and id(node) not in rewritten_parents:
                rewritten_parents.add(id(node))
                iso._rewrite_dir_record_extent(node)  # pylint: disable=protected-access
                # Each subdirectory of `node` has a dotdot record
                # (in its own extent) whose data_length carries
                # node.data_length.  _add_child / _remove_child
                # keep those dotdots in sync in memory, but the
                # bytes on disk haven't been touched unless we
                # rewrite them here.
                iso._rewrite_subdir_dotdots(node)  # pylint: disable=protected-access
                node = node.parent
        elif isinstance(record, udfmod.UDFFileEntry):
            record.set_data_length(length)
            abs_offset = record.extent_location() * iso.logical_block_size
            iso._cdfp.seek(abs_offset)  # pylint: disable=protected-access
            iso._cdfp.write(record.record())  # pylint: disable=protected-access
        else:
            # This should never happen
            raise pycdlibexception.PyCdlibInternalError('Invalid record type')


def _do_rm_file(iso, iso_path):
    # type: (PyCdlib, str) -> None
    """
    Implementation of in-place file removal.  Operates on an open
    :class:`pycdlib.PyCdlib` object's internal state; not a public API.
    Used by :meth:`InPlaceEditor.rm_file`.

    Removes the file's directory record(s) from every tree the file
    is linked into (ISO9660 and Joliet) and rewrites the affected
    parent extents on disk.  The file's data extent stays as orphaned
    bytes inside the volume -- PVD ``space_size`` is not adjusted
    because the on-disk extent allocation doesn't change.

    Refuses on:
     - UDF (out of scope for v1).
     - Directories.
     - Files referenced by El Torito (the boot catalog itself or any
       boot image entry).
    """
    if not iso._initialized:  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('This object is not initialized; call either open() or new() to create an ISO')

    if hasattr(iso._cdfp, 'mode') and not iso._cdfp.mode.startswith(('r+', 'w', 'a', 'rb+')):  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

    if iso.udf_root is not None:
        raise pycdlibexception.PyCdlibInvalidInput('InPlaceEditor.rm_file does not support UDF ISOs yet; use PyCdlib.rm_file + write_fp() to produce a new ISO instead')

    child = iso._find_iso_record(utils.normpath(iso_path))  # pylint: disable=protected-access

    if not child.is_file():
        raise pycdlibexception.PyCdlibInvalidInput('Cannot remove a directory with rm_file')

    if iso.eltorito_boot_catalog is not None:
        if any(id(child) == id(rec) for rec in iso.eltorito_boot_catalog.dirrecords):
            raise pycdlibexception.PyCdlibInvalidInput("Cannot remove a file that is the El Torito boot catalog; use PyCdlib.rm_eltorito + write_fp() to produce a new ISO instead")
        if child.inode is not None:
            iso._check_inode_against_eltorito(child.inode)  # pylint: disable=protected-access

    # Collect each linked record's parent before removal -- after
    # _rm_dr_link runs, the record is no longer in inode.linked_records
    # so we'd lose track of which parents got affected.
    affected_parents = []
    seen_parents = set()  # type: set
    if child.inode is not None:
        for record, _is_pvd in child.inode.linked_records:
            if isinstance(record, dr.DirectoryRecord):
                parent = record.parent
                if id(parent) not in seen_parents:
                    seen_parents.add(id(parent))
                    affected_parents.append(parent)
            else:
                raise pycdlibexception.PyCdlibInternalError('Unsupported linked record type for in-place rm_file')

    # Remove from the in-memory tree.  _rm_dr_link does the per-record
    # bookkeeping (removes from parent.children, removes from
    # inode.linked_records, drops the inode when no more references
    # remain, walks data_continuation chains for multi-extent files).
    if child.inode is None:
        iso._remove_child_from_dr(child, child.index_in_parent)  # pylint: disable=protected-access
        if id(child.parent) not in seen_parents:
            seen_parents.add(id(child.parent))
            affected_parents.append(child.parent)
    else:
        while child.inode.linked_records:
            rec = child.inode.linked_records[0][0]
            if isinstance(rec, dr.DirectoryRecord):
                iso._rm_dr_link(rec)  # pylint: disable=protected-access
            else:
                raise pycdlibexception.PyCdlibInternalError('Unsupported linked record type for in-place rm_file')

    # Commit the change to disk.  Rewrite each affected parent's
    # directory extent (the existing _rewrite_dir_record_extent
    # zero-pads trailing bytes so the removed record's tail doesn't
    # leak through), then walk up each parent's ancestor chain to
    # propagate any data_length shrinkage from _remove_child's
    # underflow handler.
    rewritten = set()  # type: set
    for parent in affected_parents:
        node = parent  # type: Optional[dr.DirectoryRecord]
        while node is not None and id(node) not in rewritten:
            rewritten.add(id(node))
            iso._rewrite_dir_record_extent(node)  # pylint: disable=protected-access
            iso._rewrite_subdir_dotdots(node)  # pylint: disable=protected-access
            node = node.parent

    # Write the updated PVDs and Joliet VD back to disk.  The on-disk
    # space_size is unchanged (the data extent is orphaned, not
    # freed) but other fields embedded in the VDs -- the root
    # directory record's data_length, for instance -- may have shifted
    # if the up-walk reached root.
    iso._seek_to_extent(iso.pvd.extent_location())  # pylint: disable=protected-access
    iso._cdfp.write(iso.pvd.record())  # pylint: disable=protected-access

    if iso.joliet_vd is not None:
        iso._seek_to_extent(iso.joliet_vd.extent_location())  # pylint: disable=protected-access
        iso._cdfp.write(iso.joliet_vd.record())  # pylint: disable=protected-access

    if iso.enhanced_vd is not None:
        iso.enhanced_vd.copy_sizes(iso.pvd)
        iso._seek_to_extent(iso.enhanced_vd.extent_location())  # pylint: disable=protected-access
        iso._cdfp.write(iso.enhanced_vd.record())  # pylint: disable=protected-access


def _do_add_fp(iso, data_source, length, manage_fp, iso_path,
               rr_name=None, joliet_path=None, file_mode=None):
    # type: (PyCdlib, Union[BinaryIO, str], int, bool, str, Optional[str], Optional[str], Optional[int]) -> None
    """
    Implementation of in-place file addition.  Operates on an open
    :class:`pycdlib.PyCdlib` object's internal state; not a public API.
    Used by :meth:`InPlaceEditor.add_fp` and :meth:`InPlaceEditor.add_file`.

    The new file's data extent is allocated at the current end of the
    ISO (``pvd.space_size``), so the on-disk file grows by exactly the
    space the new content needs.  The new file's directory record is
    inserted into the parent's existing extent on disk; the parent
    extent must have enough slack to hold one more record.

    Refuses on:
     - UDF or El Torito ISOs (out of scope for v1).
     - A target path whose parent's directory extent would need to
       grow to fit the new record (would require relocating the parent,
       cascading layout changes).
     - Rock Ridge metadata that would require allocating a new
       Continuation Entry (CE) block -- this happens when the SUSP
       fields don't fit inside the directory record (e.g., very long
       ``rr_name``).  Short-name Rock Ridge is supported.
    """
    if not iso._initialized:  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('This object is not initialized; call either open() or new() to create an ISO')

    if hasattr(iso._cdfp, 'mode') and not iso._cdfp.mode.startswith(('r+', 'w', 'a', 'rb+')):  # pylint: disable=protected-access
        raise pycdlibexception.PyCdlibInvalidInput('To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

    if iso.udf_root is not None:
        raise pycdlibexception.PyCdlibInvalidInput('InPlaceEditor.add_fp does not support UDF ISOs yet; use PyCdlib.add_fp + write_fp() to produce a new ISO instead')
    if iso.eltorito_boot_catalog is not None:
        raise pycdlibexception.PyCdlibInvalidInput('InPlaceEditor.add_fp does not support El Torito ISOs yet; use PyCdlib.add_fp + write_fp() to produce a new ISO instead')

    # Rock Ridge: rr_name must be present iff the ISO is Rock Ridge,
    # matching PyCdlib.add_fp's contract.
    if iso.rock_ridge and rr_name is None:
        raise pycdlibexception.PyCdlibInvalidInput('Must specify an rr_name when adding a file to a Rock Ridge ISO')
    if not iso.rock_ridge and rr_name is not None:
        raise pycdlibexception.PyCdlibInvalidInput('Cannot specify an rr_name on a non-Rock-Ridge ISO')

    # Resolve the ISO9660 path's parent and leaf name.
    iso_path_bytes = utils.normpath(iso_path)
    (iso_name, iso_parent) = iso._iso_name_and_parent_from_path(iso_path_bytes)  # pylint: disable=protected-access

    # Resolve the Joliet path's parent and leaf name (if provided).
    joliet_parent = None  # type: Optional[dr.DirectoryRecord]
    joliet_name = None  # type: Optional[bytes]
    if joliet_path is not None:
        if iso.joliet_vd is None:
            raise pycdlibexception.PyCdlibInvalidInput('Cannot use joliet_path on a non-Joliet ISO')
        joliet_path_bytes = iso._normalize_joliet_path(joliet_path)  # pylint: disable=protected-access
        (joliet_name, joliet_parent) = iso._joliet_name_and_parent_from_path(joliet_path_bytes)  # pylint: disable=protected-access

    # Reserve the new file's data extent at the current end of the ISO.
    new_data_extent = iso.pvd.space_size

    # Default Rock Ridge file mode matches PyCdlib's add_fp default
    # for managed-fp callers (regular file, r--r--r--).
    if file_mode is None:
        fmode = 0o0100444 if iso.rock_ridge else 0
    else:
        fmode = file_mode

    # Create the shared Inode that backs every linked record.
    ino = inode.Inode()
    ino.new(length, data_source, manage_fp, 0)
    ino.set_extent_location(new_data_extent)

    # Create the ISO9660 directory record.  For a Rock Ridge ISO we
    # pass the version and rr_name through so the SUSP entries land in
    # the record; for a plain ISO9660 ISO we pass empty placeholders.
    rr_version = iso.rock_ridge if iso.rock_ridge else ''
    rr_name_bytes = rr_name.encode('utf-8') if rr_name is not None else b''

    new_iso_rec = dr.DirectoryRecord()
    new_iso_rec.new_file(iso.pvd, length, iso_name, iso_parent,
                         iso.pvd.sequence_number(),
                         rr_version, rr_name_bytes, iso.xa, fmode,
                         time.time(), None)
    new_iso_rec.set_data_location(new_data_extent, 0)
    new_iso_rec.inode = ino

    # If Rock Ridge couldn't fit all its SUSP fields inline, the
    # record now has a CE (Continuation Entry) referencing a separate
    # block.  In-place add can't grow the on-disk RR CE allocation, so
    # we refuse the add up front.  Catch this *before* mutating the
    # parent so there's nothing to roll back.
    if new_iso_rec.rock_ridge is not None and new_iso_rec.rock_ridge.dr_entries.ce_record is not None:
        raise pycdlibexception.PyCdlibInvalidInput("Adding this file requires a Rock Ridge Continuation Entry (CE) block, which in-place add cannot allocate; use PyCdlib.add_fp + write_fp() to produce a new ISO instead")

    iso_overflowed = iso_parent.add_child(new_iso_rec, iso.logical_block_size)
    if iso_overflowed:
        iso_parent.remove_child(new_iso_rec, new_iso_rec.index_in_parent, iso.logical_block_size)
        raise pycdlibexception.PyCdlibInvalidInput("Adding this file would overflow the parent directory's extent; use PyCdlib.add_fp + write_fp() to produce a new ISO instead")
    ino.linked_records.append((new_iso_rec, True))

    # Joliet record, if requested.  Same overflow check.
    if joliet_parent is not None and iso.joliet_vd is not None and joliet_name is not None:
        new_joliet_rec = dr.DirectoryRecord()
        new_joliet_rec.new_file(iso.joliet_vd, length, joliet_name, joliet_parent,
                                iso.joliet_vd.sequence_number(),
                                '', b'', False, 0, time.time(), None)
        new_joliet_rec.set_data_location(new_data_extent, 0)
        new_joliet_rec.inode = ino

        joliet_overflowed = joliet_parent.add_child(new_joliet_rec, iso.logical_block_size)
        if joliet_overflowed:
            joliet_parent.remove_child(new_joliet_rec, new_joliet_rec.index_in_parent, iso.logical_block_size)
            # Roll the ISO9660 side back too so the failure is atomic.
            iso_parent.remove_child(new_iso_rec, new_iso_rec.index_in_parent, iso.logical_block_size)
            ino.linked_records.remove((new_iso_rec, True))
            raise pycdlibexception.PyCdlibInvalidInput("Adding this file would overflow the Joliet parent directory's extent; use PyCdlib.add_fp + write_fp() to produce a new ISO instead")
        ino.linked_records.append((new_joliet_rec, False))

    # The in-memory tree update succeeded; register the inode.
    iso.inodes.append(ino)

    # Grow PVD / Joliet / Enhanced VD space_size to cover the new
    # file's data extent.  These take bytes and round up internally.
    iso.pvd.add_to_space_size(length)
    if iso.joliet_vd is not None:
        iso.joliet_vd.add_to_space_size(length)
    if iso.enhanced_vd is not None:
        iso.enhanced_vd.copy_sizes(iso.pvd)

    # Commit to disk: write the file data at the reserved extent.
    iso._seek_to_extent(new_data_extent)  # pylint: disable=protected-access
    if isinstance(data_source, str):
        with open(data_source, 'rb') as fp:
            utils.copy_data(length, iso.logical_block_size, fp, iso._cdfp)  # pylint: disable=protected-access
    else:
        utils.copy_data(length, iso.logical_block_size, data_source, iso._cdfp)  # pylint: disable=protected-access
    utils.zero_pad(iso._cdfp, length, iso.logical_block_size)  # pylint: disable=protected-access

    # Rewrite each affected parent's directory extent on disk so the
    # new record becomes visible to a future parser.
    iso._rewrite_dir_record_extent(iso_parent)  # pylint: disable=protected-access
    iso._rewrite_subdir_dotdots(iso_parent)  # pylint: disable=protected-access
    if joliet_parent is not None:
        iso._rewrite_dir_record_extent(joliet_parent)  # pylint: disable=protected-access
        iso._rewrite_subdir_dotdots(joliet_parent)  # pylint: disable=protected-access

    # Write the updated PVD / Joliet VD / Enhanced VD back so the
    # bumped space_size lands on disk.
    iso._seek_to_extent(iso.pvd.extent_location())  # pylint: disable=protected-access
    iso._cdfp.write(iso.pvd.record())  # pylint: disable=protected-access

    if iso.joliet_vd is not None:
        iso._seek_to_extent(iso.joliet_vd.extent_location())  # pylint: disable=protected-access
        iso._cdfp.write(iso.joliet_vd.record())  # pylint: disable=protected-access

    if iso.enhanced_vd is not None:
        iso._seek_to_extent(iso.enhanced_vd.extent_location())  # pylint: disable=protected-access
        iso._cdfp.write(iso.enhanced_vd.record())  # pylint: disable=protected-access


class InPlaceEditor:
    """
    Context manager for editing files in place on an existing ISO.

    Open the ISO, modify one or more files in place, and close.  The
    new content is written to the *original* ISO file -- there is no
    separate output file the way ``write_fp`` produces.
    """

    __slots__ = ('_iso',)

    def __init__(self, filename, mode='rb+'):
        # type: (str, str) -> None
        """
        Open `filename` for in-place editing.

        Parameters:
         filename - The local filesystem path to the ISO file to edit.
         mode - The mode to open the ISO file in.  Must permit writing;
                defaults to ``'rb+'``.
        Returns:
         Nothing.
        """
        self._iso = PyCdlib()
        self._iso.open(filename, mode=mode)

    def __enter__(self):
        # type: () -> InPlaceEditor
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (object, object, object) -> Literal[False]
        self._iso.close()
        return False  # don't suppress exceptions

    def modify_file(self, fp, length, iso_path, rr_name=None,  # pylint: disable=unused-argument
                    joliet_path=None, udf_path=None):          # pylint: disable=unused-argument
        # type: (BinaryIO, int, str, Optional[str], Optional[str], Optional[str]) -> None
        """
        Replace the bytes of an existing file on the ISO with new content.

        Constraints:
         - The file must already exist on the ISO.
         - The file must not be a directory.
         - The new content cannot occupy more extents than the old
           content.  Within that ceiling the new length is free: a
           file currently sized to N extents may be replaced with any
           content from 0 bytes up through N*logical_block_size bytes.
           Shrinking past an extent boundary zeroes the orphaned
           extents inside the file's original on-disk allocation.

        Parameters:
         fp - A file-like object containing the new contents.
         length - The length of the new contents.
         iso_path - The ISO9660 absolute path identifying the file.
         rr_name - Rock Ridge name (accepted for API symmetry; not used
                   for lookup).
         joliet_path - Joliet absolute path (accepted for API symmetry;
                       not used for lookup).
         udf_path - UDF absolute path (accepted for API symmetry; not
                    used for lookup).
        Returns:
         Nothing.
        """
        _do_modify_file_in_place(self._iso, fp, length, iso_path,
                                 rr_name=rr_name,
                                 joliet_path=joliet_path,
                                 udf_path=udf_path)

    def rm_file(self, iso_path):
        # type: (str) -> None
        """
        Remove a file from the ISO in place.

        The file's directory record is removed from every tree the
        file is linked into (ISO9660 and Joliet) and the affected
        parent extents are rewritten on disk.  The file's data extent
        stays as orphaned bytes inside the volume -- the volume's
        on-disk size doesn't shrink.

        Constraints:
         - The path must identify an existing file.
         - The file must not be a directory.
         - The file must not be referenced by El Torito (use
           :meth:`pycdlib.PyCdlib.rm_eltorito` first).
         - The ISO must not be a UDF ISO (UDF in-place rm is not
           supported yet).

        Parameters:
         iso_path - The ISO9660 absolute path identifying the file.
        Returns:
         Nothing.
        """
        _do_rm_file(self._iso, iso_path)

    def add_fp(self, fp, length, iso_path, rr_name=None, joliet_path=None,
               file_mode=None):
        # type: (BinaryIO, int, str, Optional[str], Optional[str], Optional[int]) -> None
        """
        Add a new file to the ISO in place, reading the content from
        a file-like object.

        The new file's data extent is appended to the end of the ISO
        (the underlying file on disk grows by the rounded-up content
        length).  The directory record is inserted into the parent's
        existing extent on disk.

        Constraints:
         - The ISO must not be a UDF or El Torito ISO (out of scope
           for v1).
         - On a Rock Ridge ISO, ``rr_name`` must be provided.  Rock
           Ridge SUSP fields whose serialized length would require a
           new Continuation Entry block are refused (this typically
           means very long ``rr_name`` values; short names are fine).
         - The target's parent directory must already exist on the ISO.
         - The parent's directory extent must have enough slack to
           hold one more record; if not, this raises and you must use
           :meth:`pycdlib.PyCdlib.add_fp` + ``write_fp`` instead.
         - The caller is responsible for keeping ``fp`` open for the
           lifetime of this editor (until the with-block exits).

        Parameters:
         fp - A file-like object containing the new file's content.
         length - The length of the new content.
         iso_path - The ISO9660 absolute path identifying where to
                    insert the file.
         rr_name - Rock Ridge name; required on Rock Ridge ISOs and
                   rejected on non-Rock-Ridge ISOs.
         joliet_path - The Joliet absolute path; if provided, a Joliet
                       directory record is also inserted.
         file_mode - File-mode bits (Rock Ridge only).
        Returns:
         Nothing.
        """
        _do_add_fp(self._iso, fp, length, False, iso_path,
                   rr_name=rr_name,
                   joliet_path=joliet_path,
                   file_mode=file_mode)

    def add_file(self, filename, iso_path, rr_name=None, joliet_path=None,
                 file_mode=None):
        # type: (str, str, Optional[str], Optional[str], Optional[int]) -> None
        """
        Add a new file to the ISO in place, reading the content from
        a file on the local filesystem.

        Same semantics and constraints as :meth:`add_fp` except that
        pycdlib opens and closes ``filename`` itself, the same way
        :meth:`pycdlib.PyCdlib.add_file` does relative to
        :meth:`pycdlib.PyCdlib.add_fp`.

        Parameters:
         filename - The local filename whose content becomes the new
                    file's content on the ISO.
         iso_path - The ISO9660 absolute path identifying where to
                    insert the file.
         rr_name - Rock Ridge name; required on Rock Ridge ISOs and
                   rejected on non-Rock-Ridge ISOs.
         joliet_path - The Joliet absolute path; if provided, a Joliet
                       directory record is also inserted.
         file_mode - File-mode bits (Rock Ridge only).
        Returns:
         Nothing.
        """
        import os  # pylint: disable=import-outside-toplevel
        _do_add_fp(self._iso, filename, os.stat(filename).st_size, True,
                   iso_path,
                   rr_name=rr_name,
                   joliet_path=joliet_path,
                   file_mode=file_mode)
