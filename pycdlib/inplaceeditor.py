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

from typing import TYPE_CHECKING

from pycdlib import dr
from pycdlib import inode
from pycdlib import pycdlibexception
from pycdlib import udf as udfmod
from pycdlib import utils
from pycdlib.pycdlib import PyCdlib

if TYPE_CHECKING:
    from typing import BinaryIO, Literal, Optional  # noqa: F401


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

    if old_num_extents != new_num_extents:
        raise pycdlibexception.PyCdlibInvalidInput('When modifying a file in-place, the number of extents for a file cannot change!')

    if not child.is_file():
        raise pycdlibexception.PyCdlibInvalidInput('Cannot modify a directory with modify_file_in_place')

    if child.inode is None:
        raise pycdlibexception.PyCdlibInternalError('Child file found without inode')

    child.inode.update_fp(fp, length)

    # Remove the old size from the PVD size.
    for pvd in iso.pvds:
        pvd.remove_from_space_size(child.get_data_length())
    # And add the new size to the PVD size.
    for pvd in iso.pvds:
        pvd.add_to_space_size(length)

    if iso.enhanced_vd is not None:
        iso.enhanced_vd.copy_sizes(iso.pvd)

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

    # We don't have to write anything out for UDF since it only tracks
    # extents, and we know we aren't changing the number of extents.

    # Write out the actual file contents.
    iso._seek_to_extent(child.extent_location())  # pylint: disable=protected-access
    with inode.InodeOpenData(child.inode, iso.logical_block_size) as (data_fp, data_len):
        utils.copy_data(data_len, iso.logical_block_size, data_fp, iso._cdfp)  # pylint: disable=protected-access
        utils.zero_pad(iso._cdfp, data_len, iso.logical_block_size)  # pylint: disable=protected-access

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
    first_joliet = True
    rewritten_parents = set()  # type: set
    for record, is_pvd_unused in child.inode.linked_records:
        if isinstance(record, dr.DirectoryRecord):
            if iso.joliet_vd is not None and id(record.vd) == id(iso.joliet_vd) and first_joliet:
                first_joliet = False
                iso.joliet_vd.remove_from_space_size(record.get_data_length())
                iso.joliet_vd.add_to_space_size(length)
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
         - The new content must occupy the same number of extents as
           the old content.

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
