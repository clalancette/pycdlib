# Copyright (C) 2015-2018  Chris Lalancette <clalancette@gmail.com>

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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

'''
Main PyCdlib class and support classes and utilities.
'''

from __future__ import absolute_import

import bisect
import collections
import inspect
import io
import os
import struct
import sys
try:
    from functools import lru_cache
except ImportError:
    from pycdlib.backport_functools import lru_cache
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO  # pylint: disable=ungrouped-imports

import pycdlib.dr as dr
import pycdlib.eltorito as eltorito
import pycdlib.headervd as headervd
import pycdlib.inode as inode
import pycdlib.isohybrid as isohybrid
import pycdlib.path_table_record as path_table_record
import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.udf as udfmod
import pycdlib.utils as utils

# There are a number of specific ways that numerical data is stored in the
# ISO9660/Ecma-119 standard.  In the text these are reference by the section
# number they are stored in.  A brief synopsis:
#
# 7.1.1 - 8-bit number
# 7.2.3 - 16-bit number, stored first as little-endian then as big-endian (4 bytes total)
# 7.3.1 - 32-bit number, stored as little-endian
# 7.3.2 - 32-bit number ,stored as big-endian
# 7.3.3 - 32-bit number, stored first as little-endian then as big-endian (8 bytes total)

# We allow A-Z, 0-9, and _ as "d1" characters.  The below is the fastest way to
# build that list as integers.
_allowed_d1_characters = tuple(range(65, 91)) + tuple(range(48, 58)) + tuple((ord(b'_'),))


def _check_d1_characters(name):
    '''
    A function to check that a name only uses d1 characters as defined by ISO9660.

    Parameters:
     name - The name to check.
    Returns:
     Nothing.
    '''
    bytename = bytearray(name)
    for char in bytename:
        if char not in _allowed_d1_characters:
            raise pycdlibexception.PyCdlibInvalidInput("%s is not a valid ISO9660 filename (it contains invalid characters)" % (name))


def _split_iso9660_filename(fullname):
    '''
    A function to split an ISO 9660 filename into its constituent parts.  This
    is the name, the extension, and the version number.

    Parameters:
     fullname - The name to split.
    Returns:
     A tuple containing the name, extension, and version.
    '''
    namesplit = fullname.split(b';')
    version = b''
    if len(namesplit) > 1:
        version = namesplit.pop()

    rest = b';'.join(namesplit)

    dotsplit = rest.split(b'.')
    if len(dotsplit) == 1:
        name = dotsplit[0]
        extension = b''
    else:
        name = b'.'.join(dotsplit[:-1])
        extension = dotsplit[-1]

    return (name, extension, version)


def _check_iso9660_filename(fullname, interchange_level):
    '''
    A function to check that a file identifier conforms to the ISO9660 rules
    for a particular interchange level.

    Parameters:
     fullname - The name to check.
     interchange_level - The interchange level to check against.
    Returns:
     Nothing.
    '''

    # Check to ensure the name is a valid filename for the ISO according to
    # Ecma-119 7.5.

    (name, extension, version) = _split_iso9660_filename(fullname)

    # Ecma-119 says that filenames must end with a semicolon-number, but I have
    # found CDs (Ubuntu 14.04 Desktop i386, for instance) that do not follow
    # this.  Thus we allow for names both with and without the semi+version.

    # Ecma-119 says that filenames must have a version number, but I have
    # found CDs (FreeBSD 10.1 amd64) that do not have any version number.
    # Allow for this.

    if version != b'' and (int(version) < 1 or int(version) > 32767):
        raise pycdlibexception.PyCdlibInvalidInput('%s has an invalid version number (must be between 1 and 32767' % (fullname))

    # Ecma-119 section 7.5.1 specifies that filenames must have at least one
    # character in either the name or the extension.
    if not name and not extension:
        raise pycdlibexception.PyCdlibInvalidInput('%s is not a valid ISO9660 filename (either the name or extension must be non-empty' % (fullname))

    if b';' in name or b';' in extension:
        raise pycdlibexception.PyCdlibInvalidInput('%s contains multiple semicolons!' % (fullname))

    if interchange_level == 1:
        # According to Ecma-119, section 10.1, at level 1 the filename can
        # only be up to 8 d-characters or d1-characters, and the extension can
        # only be up to 3 d-characters or 3 d1-characters.
        if len(name) > 8 or len(extension) > 3:
            raise pycdlibexception.PyCdlibInvalidInput('%s is not a valid ISO9660 filename at interchange level 1' % (fullname))
    else:
        # For all other interchange levels, the maximum filename length is
        # specified in Ecma-119 7.5.2.  However, I have found CDs (Ubuntu 14.04
        # Desktop i386, for instance) that don't conform to this.  Skip the
        # check until we know how long is allowed.
        pass

    # Ecma-119 section 7.5.1 says that the file name and extension each contain
    # zero or more d-characters or d1-characters.  While the definition of
    # d-characters and d1-characters is not specified in Ecma-119,
    # http://wiki.osdev.org/ISO_9660 suggests that this consists of A-Z, 0-9, _
    # which seems to correlate with empirical evidence.  Thus we check for that
    # here.
    if interchange_level < 4:
        _check_d1_characters(name)
        _check_d1_characters(extension)


def _check_iso9660_directory(fullname, interchange_level):
    '''
    A function to check that an directory identifier conforms to the ISO9660 rules
    for a particular interchange level.

    Parameters:
     fullname - The name to check.
     interchange_level - The interchange level to check against.
    Returns:
     Nothing.
    '''
    # Check to ensure the directory name is valid for the ISO according to
    # Ecma-119 7.6.

    # Ecma-119 section 7.6.1 says that a directory identifier needs at least one
    # character
    if len(fullname) < 1:
        raise pycdlibexception.PyCdlibInvalidInput('%s is not a valid ISO9660 directory name (the name must be at least 1 character long)' % (fullname))

    maxlen = float('inf')
    if interchange_level == 1:
        # Ecma-119 section 10.1 says that directory identifiers lengths cannot
        # exceed 8 at interchange level 1.
        maxlen = 8
    elif interchange_level in (2, 3):
        # Ecma-119 section 7.6.3 says that directory identifiers lengths cannot
        # exceed 207.
        maxlen = 207
    # for interchange_level 4, we allow any length

    if len(fullname) > maxlen:
        raise pycdlibexception.PyCdlibInvalidInput('%s is not a valid ISO9660 directory name (it is too long)' % (fullname))

    # Ecma-119 section 7.6.1 says that directory names consist of one or more
    # d-characters or d1-characters.  While the definition of d-characters and
    # d1-characters is not specified in Ecma-119,
    # http://wiki.osdev.org/ISO_9660 suggests that this consists of A-Z, 0-9, _
    # which seems to correlate with empirical evidence.  Thus we check for that
    # here.
    if interchange_level < 4:
        _check_d1_characters(fullname)


def _interchange_level_from_filename(fullname):
    '''
    A function to determine the ISO interchange level from the filename.
    In theory, there are 3 levels, but in practice we only deal with level 1
    and level 3.

    Parameters:
     name - The name to use to determine the interchange level.
    Returns:
     The interchange level determined from this filename.
    '''
    (name, extension, version) = _split_iso9660_filename(fullname)

    interchange_level = 1

    if version != b'' and (int(version) < 1 or int(version) > 32767):
        interchange_level = 3

    if b';' in name or b';' in extension:
        interchange_level = 3

    if len(name) > 8 or len(extension) > 3:
        interchange_level = 3

    try:
        _check_d1_characters(name)
        _check_d1_characters(extension)
    except pycdlibexception.PyCdlibInvalidInput:
        interchange_level = 3

    return interchange_level


def _interchange_level_from_directory(name):
    '''
    A function to determine the ISO interchange level from the directory name.
    In theory, there are 3 levels, but in practice we only deal with level 1
    and level 3.

    Parameters:
     name - The name to use to determine the interchange level.
    Returns:
     The interchange level determined from this filename.
    '''
    interchange_level = 1
    if len(name) > 8:
        interchange_level = 3

    try:
        _check_d1_characters(name)
    except pycdlibexception.PyCdlibInvalidInput:
        interchange_level = 3

    return interchange_level


def _reassign_vd_dirrecord_extents(vd, current_extent):
    '''
    An internal helper method for reassign_extents that assigns extents to
    directory records for the passed in Volume Descriptor.  The current
    extent is passed in, and this function returns the extent after the
    last one it assigned.

    Parameters:
     vd - The volume descriptor on which to operate.
     current_extent - The current extent before assigning extents to the
                      volume descriptor directory records.
    Returns:
     The current extent after assigning extents to the volume descriptor
     directory records.
    '''
    log_block_size = vd.logical_block_size()

    # Here we re-walk the entire tree, re-assigning extents as necessary.
    root_dir_record = vd.root_directory_record()
    root_dir_record.set_data_location(current_extent, 0)
    current_extent += utils.ceiling_div(root_dir_record.data_length, log_block_size)

    # Walk through the list, assigning extents to all of the directories.
    child_link_recs = []
    parent_link_recs = []
    file_list = []
    ptr_index = 1
    dirs = collections.deque([root_dir_record])
    while dirs:
        dir_record = dirs.popleft()

        if dir_record.is_root:
            # The root directory record doesn't need an extent assigned,
            # so just add its children to the list and continue on
            for child in dir_record.children:
                if child.ptr is not None:
                    child.ptr.update_parent_directory_number(ptr_index)
            ptr_index += 1
            dirs.extend(dir_record.children)
            continue

        dir_record_parent = dir_record.parent

        if dir_record.is_dot():
            dir_record.set_data_location(dir_record_parent.extent_location(), 0)
            continue

        dir_record_rock_ridge = dir_record.rock_ridge

        if dir_record.is_dotdot():
            if dir_record_parent.is_root:
                # Special case of the root directory record.  In this
                # case, we assume that the dot record has already been
                # added, and is the one before us.  We set the dotdot
                # extent location to the same as the dot one.
                extent_to_set = dir_record_parent.extent_location()
            else:
                extent_to_set = dir_record_parent.parent.extent_location()
            dir_record.set_data_location(extent_to_set, 0)
            if dir_record_rock_ridge is not None and dir_record_rock_ridge.parent_link is not None:
                parent_link_recs.append(dir_record)
            if dir_record_parent.rock_ridge is not None:
                if dir_record_parent.parent.is_root:
                    dir_record_rock_ridge.copy_file_links(dir_record_parent.parent.children[0].rock_ridge)
                else:
                    dir_record_rock_ridge.copy_file_links(dir_record_parent.parent.rock_ridge)
            continue

        if dir_record.is_dir():
            dir_record.new_extent_loc = current_extent
            dir_record.ptr.update_extent_location(dir_record.new_extent_loc)
            for child in dir_record.children:
                if child.ptr is not None:
                    child.ptr.update_parent_directory_number(ptr_index)
            ptr_index += 1
            if dir_record_rock_ridge is None or not dir_record_rock_ridge.child_link_record_exists():
                current_extent += utils.ceiling_div(dir_record.data_length, log_block_size)
            dirs.extend(dir_record.children)
        else:
            if dir_record.data_length == 0 or (dir_record_rock_ridge is not None and (dir_record_rock_ridge.child_link_record_exists() or dir_record_rock_ridge.is_symlink())):
                # If this is a child link record, the extent location really
                # doesn't matter, since it is fake.  We set it to zero.
                dir_record.new_extent_loc = 0
            else:
                if dir_record.inode is not None:
                    file_list.append(dir_record.inode)

        if dir_record_rock_ridge is not None:
            if dir_record_rock_ridge.dr_entries.ce_record is not None:
                if dir_record_rock_ridge.ce_block.extent_location() is None:
                    dir_record.rock_ridge.ce_block.set_extent_location(current_extent)
                    current_extent += 1
                dir_record.rock_ridge.dr_entries.ce_record.update_extent(dir_record.rock_ridge.ce_block.extent_location())
            if dir_record_rock_ridge.cl_to_moved_dr is not None:
                child_link_recs.append(dir_record)

    # After we have reshuffled the extents, we need to update the rock ridge
    # links.
    for ch in child_link_recs:
        ch.rock_ridge.child_link_update_from_dirrecord()

    for p in parent_link_recs:
        p.rock_ridge.parent_link_update_from_dirrecord()

    return current_extent, file_list


def _check_path_depth(iso_path):
    '''
    An internal method to take a fully-qualified iso path and check whether
    it meets the path depth requirements of ISO9660/Ecma-119.

    Parameters:
     iso_path - The path to check.
    Returns:
     Nothing.
    '''
    if len(utils.split_path(iso_path)) > 7:
        # Ecma-119 Section 6.8.2.1 says that the number of levels in the
        # hierarchy shall not exceed eight.  However, since the root
        # directory must always reside at level 1 by itself, this gives us
        # an effective maximum hierarchy depth of 7.
        raise pycdlibexception.PyCdlibInvalidInput('Directory levels too deep (maximum is 7)')


def _yield_children(rec):
    '''
    An internal function to gather and yield all of the children of a Directory
    Record.

    Parameters:
     rec - The Directory Record to get all of the children from (must be a
           directory)
    Yields:
     Children of this Directory Record.
    Returns:
     Nothing.
    '''
    if not rec.is_dir():
        raise pycdlibexception.PyCdlibInvalidInput('Record is not a directory!')

    last = b''
    for child in rec.children:
        # Check to see if the filename of this child is the same as the
        # last one, and if so, skip the child.  This can happen if we
        # have very large files with more than one directory entry.
        fi = child.file_identifier()
        if fi == last:
            continue

        last = fi
        if child.rock_ridge is not None and child.rock_ridge.child_link_record_exists():
            # If this is the case, this is a relocated entry.  We actually
            # want to go find the entry this was relocated to; we do that
            # by following the child_link, then going up to the parent and
            # finding the entry that links to the same one as this one.
            cl_parent = child.rock_ridge.cl_to_moved_dr.parent
            for cl_child in cl_parent.children:
                if cl_child.rock_ridge.name() == child.rock_ridge.name():
                    child = cl_child
                    break
            # If we ended up not finding the right one in the parent of the
            # moved entry, weird, but just return the one we would have
            # anyway.

        yield child


def _assign_udf_desc_extents(descs, start_extent):
    '''
    An internal function to assign a consecutive sequence of extents for the
    given set of UDF Descriptors, starting at the given extent.

    Parameters:
     descs - The PyCdlib.UDFDescriptors object to assign extents for.
     start_extent - The starting extent to assign from.
    Returns:
     Nothing.
    '''
    current_extent = start_extent

    descs.pvd.set_location(current_extent)
    current_extent += 1

    descs.impl_use.set_location(current_extent)
    current_extent += 1

    descs.partition.set_location(current_extent)
    current_extent += 1

    descs.logical_volume.set_location(current_extent)
    current_extent += 1

    descs.unallocated_space.set_location(current_extent)
    current_extent += 1

    descs.terminator.set_location(current_extent)
    current_extent += 1


class PyCdlib(object):
    '''
    The main class for manipulating ISOs.
    '''
    __slots__ = ('_initialized', '_cdfp', 'pvds', 'svds', 'vdsts', 'brs', 'pvd',
                 '_tmpdr', 'rock_ridge', '_always_consistent',
                 'eltorito_boot_catalog', 'isohybrid_mbr', 'xa', '_managing_fp',
                 '_needs_reshuffle', '_rr_moved_record', '_rr_moved_name',
                 '_rr_moved_rr_name', 'enhanced_vd', 'joliet_vd', 'version_vd',
                 'interchange_level', '_write_check_list', '_track_writes',
                 'udf_bea', 'udf_nsr', 'udf_tea', 'udf_anchors',
                 'udf_main_descs', 'udf_reserve_descs',
                 'udf_logical_volume_integrity',
                 'udf_logical_volume_integrity_terminator', 'udf_root',
                 'udf_file_set', 'udf_file_set_terminator', 'inodes')

    class UDFDescriptors(object):
        '''
        A class to represent a set of UDF Descriptors.
        '''
        __slots__ = ('pvd', 'impl_use', 'partition', 'logical_volume',
                     'unallocated_space', 'terminator')

        def __init__(self):
            self.pvd = None
            self.impl_use = None
            self.partition = None
            self.logical_volume = None
            self.unallocated_space = None
            self.terminator = None

    def _parse_volume_descriptors(self):
        '''
        An internal method to parse the volume descriptors on an ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        # Ecma-119 says that the Volume Descriptor set is a sequence of volume
        # descriptors recorded in consecutively numbered Logical Sectors
        # starting with Logical Sector Number 16.  Since sectors are 2048 bytes
        # in length, we start at sector 16 * 2048

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.
        self._cdfp.seek(16 * 2048)
        while True:
            # All volume descriptors are exactly 2048 bytes long
            curr_extent = self._cdfp.tell() // 2048
            vd = self._cdfp.read(2048)
            if len(vd) != 2048:
                raise pycdlibexception.PyCdlibInvalidISO('Failed to read entire volume descriptor')
            (desc_type, ident) = struct.unpack_from('=B5s', vd, 0)
            if desc_type not in (headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY,
                                 headervd.VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR,
                                 headervd.VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD,
                                 headervd.VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY) or ident not in (b'CD001', b'BEA01', b'NSR02', b'TEA01'):
                # We read the next extent, and it wasn't a descriptor.  Abort
                # the loop, remembering to back up the input file descriptor.
                self._cdfp.seek(-2048, os.SEEK_CUR)
                break
            if desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvd = headervd.PrimaryOrSupplementaryVD(headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY)
                pvd.parse(vd, curr_extent)
                self.pvds.append(pvd)
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
                vdst = headervd.VolumeDescriptorSetTerminator()
                vdst.parse(vd, curr_extent)
                self.vdsts.append(vdst)
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
                # Both an Ecma-119 Boot Record and a Ecma-TR 071 UDF-Bridge
                # Beginning Extended Area Descriptor have the first byte as 0,
                # so we can't tell which it is until we look at the next 5
                # bytes (Boot Record will have 'CD001', BEAD will have 'BEA01').
                if ident == b'CD001':
                    br = headervd.BootRecord()
                    br.parse(vd, curr_extent)
                    self.brs.append(br)
                elif ident == b'BEA01':
                    self.udf_bea = udfmod.BEAVolumeStructure()
                    self.udf_bea.parse(vd, curr_extent)
                elif ident == b'NSR02':
                    self.udf_nsr = udfmod.NSRVolumeStructure()
                    self.udf_nsr.parse(vd, curr_extent)
                elif ident == b'TEA01':
                    self.udf_tea = udfmod.TEAVolumeStructure()
                    self.udf_tea.parse(vd, curr_extent)
                else:
                    # This isn't really possible, since we would have aborted
                    # the loop above.
                    raise pycdlibexception.PyCdlibInvalidISO('Invalid volume identification type')
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
                svd = headervd.PrimaryOrSupplementaryVD(headervd.VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY)
                svd.parse(vd, curr_extent)
                self.svds.append(svd)
            # Since we checked for the valid descriptors above, it is impossible
            # to see an invalid desc_type here, so no check necessary.

        # The language in Ecma-119, p.8, Section 6.7.1 says:
        #
        # The sequence shall contain one Primary Volume Descriptor (see 8.4) recorded at least once.
        #
        # The important bit there is "at least one", which means that we have
        # to accept ISOs with more than one PVD.
        if len(self.pvds) < 1:
            raise pycdlibexception.PyCdlibInvalidISO('Valid ISO9660 filesystems must have at least one PVD')

        self.pvd = self.pvds[0]

        # Make sure any other PVDs agree with the first one.
        for pvd in self.pvds[1:]:
            if pvd != self.pvd:
                raise pycdlibexception.PyCdlibInvalidISO('Multiple occurrences of PVD did not agree!')

            pvd.root_dir_record = self.pvd.root_dir_record

        if len(self.vdsts) < 1:
            raise pycdlibexception.PyCdlibInvalidISO('Valid ISO9660 filesystems must have at least one Volume Descriptor Set Terminator')

    def _seek_to_extent(self, extent):
        '''
        An internal method to seek to a particular extent on the input ISO.

        Parameters:
         extent - The extent to seek to.
        Returns:
         Nothing.
        '''
        self._cdfp.seek(extent * self.pvd.logical_block_size())

    def _find_record(self, **kwargs):
        '''
        An internal method to find an directory record on the ISO given an ISO,
        Rock Ridge, or Joliet path.  If the entry is found, it returns the
        directory record object corresponding to that entry.  If the entry
        could not be found, a pycdlibexception.PyCdlibInvalidInput is raised.

        Parameters:
         iso_path - Look the entry up as the regular ISO9660 path.
         rr_path - Look the entry up as a Rock Ridge path.
         joliet_path - Look the entry up as a Joliet path.
        Returns:
         The directory record entry representing the entry on the ISO.
        '''
        def normal_lt(child, path):
            '''
            Internal method to see whether a directory record is less than the
            path.

            Parameters:
             child - The directory record to check.
             path - The path to check.
            Returns:
             -1 if the directory record is less than the path, 0 if they are
             equal, and 1 if the directory record is greater than the path.
            '''
            self._tmpdr.file_ident = path
            return child < self._tmpdr

        def normal_eq(child, path):
            '''
            Internal method to see whether a directory record equals the path.

            Parameters:
             child - The directory record to check.
             path - The path to check.
            Returns:
             True if the directory record name equals the path, False otherwise.
            '''
            return child.file_ident == path

        def rr_lt(child, path):
            '''
            Internal method to see whether a Rock Ridge directory record
            is less than the path.

            Parameters:
             child - The directory record to check.
             path - The path to check.
            Returns:
             -1 if the directory record is less than the path, 0 if they
             are equal, and 1 if the directory record is greater than the
             path.
            '''
            return child.rock_ridge.name() < path

        def rr_eq(child, path):
            '''
            Internal method to see whether a Rock Ridge directory record
            equals the path.

            Parameters:
             child - The directory record to check.
             path - The path to check.
            Returns:
             True if the directory record name equals the path, False otherwise.
            '''
            return child.rock_ridge.name() == path

        path = None
        num_paths = 0
        encoding = 'utf-8'
        self._tmpdr = dr.DirectoryRecord()
        lt_func = normal_lt
        eq_func = normal_eq
        start_offset = 2
        child_list = 'children'
        root_dir_record = self.pvd.root_directory_record()
        for key in kwargs:
            if key == 'iso_path' and kwargs[key] is not None:
                path = kwargs[key]
                num_paths += 1
            elif key == 'rr_path' and kwargs[key] is not None:
                path = kwargs[key]
                lt_func = rr_lt
                eq_func = rr_eq
                start_offset = 0
                child_list = 'rr_children'
                num_paths += 1
            elif key == 'joliet_path' and kwargs[key] is not None:
                path = kwargs[key]
                encoding = 'utf-16_be'
                root_dir_record = self.joliet_vd.root_directory_record()
                num_paths += 1
            else:
                raise pycdlibexception.PyCdlibInvalidInput('Unknown keyword %s' % (key))

        if num_paths != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Exactly one of iso_path, rr_path, or joliet_path must be passed')

        if not utils.starts_with_slash(path):
            raise pycdlibexception.PyCdlibInvalidInput('Must be a path starting with /')

        # If the path is just the slash, we just want the root directory, so
        # get the child there and quit.
        if path == b'/':
            return root_dir_record

        # Split the path along the slashes
        splitpath = utils.split_path(path)

        currpath = splitpath.pop(0).decode('utf-8').encode(encoding)

        entry = root_dir_record

        while True:
            child = None

            thelist = getattr(entry, child_list)
            lo = start_offset
            hi = len(thelist)
            while lo < hi:
                mid = (lo + hi) // 2
                if lt_func(thelist[mid], currpath):
                    lo = mid + 1
                else:
                    hi = mid
            index = lo
            if index != len(thelist) and eq_func(thelist[index], currpath):
                child = thelist[index]

            if child is None:
                # We failed to find this component of the path, so break out of the
                # loop and fail
                break

            if child.rock_ridge is not None and child.rock_ridge.child_link_record_exists():
                # Here, the rock ridge extension has a child link, so we
                # need to follow it.
                child = child.rock_ridge.cl_to_moved_dr

            # We found the child, and it is the last one we are looking for;
            # return it.
            if not splitpath:
                return child
            else:
                if not child.is_dir():
                    break
                entry = child
                currpath = splitpath.pop(0).decode('utf-8').encode(encoding)

        raise pycdlibexception.PyCdlibInvalidInput('Could not find path %s' % (path))

    @lru_cache(maxsize=256)
    def _find_iso_record(self, iso_path):
        '''
        An internal method to find an directory record on the ISO given an ISO
        path.  If the entry is found, it returns the directory record object
        corresponding to that entry.  If the entry could not be found, a
        pycdlibexception.PyCdlibInvalidInput is raised.

        Parameters:
         iso_path - The ISO9660 path to lookup.
        Returns:
         The directory record entry representing the entry on the ISO.
        '''
        return self._find_record(iso_path=iso_path)

    @lru_cache(maxsize=256)
    def _find_rr_record(self, rr_path):
        '''
        An internal method to find an directory record on the ISO given a Rock
        Ridge path.  If the entry is found, it returns the directory record
        object corresponding to that entry.  If the entry could not be found, a
        pycdlibexception.PyCdlibInvalidInput is raised.

        Parameters:
         rr_path - The Rock Ridge path to lookup.
        Returns:
         The directory record entry representing the entry on the ISO.
        '''
        return self._find_record(rr_path=rr_path)

    @lru_cache(maxsize=256)
    def _find_joliet_record(self, joliet_path):
        '''
        An internal method to find an directory record on the ISO given a Joliet
        path.  If the entry is found, it returns the directory record object
        corresponding to that entry.  If the entry could not be found, a
        pycdlibexception.PyCdlibInvalidInput is raised.

        Parameters:
         joliet_path - The Joliet path to lookup.
        Returns:
         The directory record entry representing the entry on the ISO.
        '''
        return self._find_record(joliet_path=joliet_path)

    @lru_cache(maxsize=256)
    def _find_udf_record(self, udf_path):
        '''
        An internal method to find an directory record on the ISO given a UDF
        path.  If the entry is found, it returns the directory record object
        corresponding to that entry.  If the entry could not be found, a
        pycdlibexception.PyCdlibInvalidInput is raised.

        Parameters:
         udf_path - The UDF path to lookup.
        Returns:
         The UDF File Entry representing the entry on the ISO.
        '''
        # If the path is just the slash, we just want the root directory, so
        # get the child there and quit.
        if udf_path == b'/':
            return self.udf_root

        # Split the path along the slashes
        splitpath = utils.split_path(udf_path)

        currpath = splitpath.pop(0)

        entry = self.udf_root

        while True:
            child = entry.find_file_ident_desc_by_name(currpath)

            if child is None:
                # We failed to find this component of the path, so break out of the
                # loop and fail
                break

            # We found the child, and it is the last one we are looking for;
            # return it.
            if not splitpath:
                return child.file_entry
            else:
                if not child.is_dir():
                    break
                entry = child.file_entry
                currpath = splitpath.pop(0)

        raise pycdlibexception.PyCdlibInvalidInput('Could not find path %s' % (udf_path))

    def _name_and_parent_from_path(self, **kwargs):
        '''
        An internal method to find the parent directory record and name give one
        of an ISO path, a Rock Ridge path, or Joliet path.  If the parent is
        found, return the parent directory record object and the relative path
        of the original path.

        Parameters:
         iso_path - The absolute ISO path to the entry on the ISO.
         rr_path - The absolute Rock Ridge path to the entry on the ISO.
         joliet_path - The absolute Joliet path to the entry on the ISO.
         udf_path - The absolute UDF path to the entry on the ISO.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''

        num_paths = 0
        encoding = 'utf-8'
        for key in kwargs:
            if num_paths != 0:
                raise pycdlibexception.PyCdlibInvalidInput('Exactly one of iso_path, rr_path, joliet_path, or udf_path must be passed')

            splitpath = utils.split_path(utils.normpath(kwargs[key]))
            name = splitpath.pop()
            num_paths += 1

            if key == 'iso_path' and kwargs[key] is not None:
                parent = self._find_iso_record(b'/' + b'/'.join(splitpath))
            elif key == 'joliet_path' and kwargs[key] is not None:
                if len(name) > 64:
                    raise pycdlibexception.PyCdlibInvalidInput('Joliet names can be a maximum of 64 characters')
                parent = self._find_joliet_record(b'/' + b'/'.join(splitpath))
                encoding = 'utf-16_be'
            elif key == 'rr_path' and kwargs[key] is not None:
                parent = self._find_rr_record(b'/' + b'/'.join(splitpath))
            elif key == 'udf_path' and kwargs[key] is not None:
                parent = self._find_udf_record(b'/' + b'/'.join(splitpath))
            else:
                raise pycdlibexception.PyCdlibInvalidInput('Unknown keyword %s' % (key))

        return (name.decode('utf-8').encode(encoding), parent)

    def _set_rock_ridge(self, rr):
        '''
        An internal method to set the Rock Ridge version of the ISO given the
        Rock Ridge version of the previous entry.

        Parameters:
         rr - The version of rr from the last directory record.
        Returns:
         Nothing.
        '''
        # We don't allow mixed Rock Ridge versions on the ISO, so apply some
        # checking.  If the current overall Rock Ridge version on the ISO is
        # None, we upgrade it to whatever version we were given.  Once we have
        # seen a particular version, we only allow records of that version or
        # None (to account for dotdot records which have no Rock Ridge).
        if self.rock_ridge is None:
            self.rock_ridge = rr
        else:
            for ver in ['1.09', '1.10', '1.12']:
                if self.rock_ridge == ver:
                    if rr is not None and rr != ver:
                        raise pycdlibexception.PyCdlibInvalidISO('Inconsistent Rock Ridge versions on the ISO!')

    def _walk_directories(self, vd, extent_to_ptr, extent_to_inode, path_table_records):
        '''
        An internal method to walk the directory records in a volume descriptor,
        starting with the root.  For each child in the directory record,
        we create a new dr.DirectoryRecord object and append it to the parent.

        Parameters:
         vd - The volume descriptor to walk.
         extent_to_ptr - A dictionary mapping extents to PTRs.
         extent_to_inode - A dictionary mapping extents to Inodes.
         path_table_records - The list of path table records.
        Returns:
         The interchange level that this ISO conforms to.
        '''
        cdfp = self._cdfp
        old_loc = cdfp.tell()
        cdfp.seek(0, os.SEEK_END)
        iso_file_length = cdfp.tell()
        cdfp.seek(old_loc)

        all_extent_to_dr = {}
        is_pvd = vd.is_pvd()
        root_dir_record = vd.root_directory_record()
        root_dir_record.set_ptr(path_table_records[0])
        interchange_level = 1
        block_size = vd.logical_block_size()
        parent_links = []
        child_links = []
        lastbyte = 0
        dirs = collections.deque([root_dir_record])
        while dirs:
            dir_record = dirs.popleft()

            self._seek_to_extent(dir_record.extent_location())
            length = dir_record.get_data_length()
            offset = 0
            last_record = None
            data = cdfp.read(length)
            while offset < length:
                if offset > (len(data) - 1):
                    # The data we read off of the ISO was shorter than what we
                    # expected.  The ISO is corrupt, throw an error.
                    raise pycdlibexception.PyCdlibInvalidISO('Invalid directory record')
                lenbyte = bytearray([data[offset]])[0]
                if lenbyte == 0:
                    # If we saw a zero length, this is probably the padding for
                    # the end of this extent.  Move the offset to the start of
                    # the next extent.
                    padsize = block_size - (offset % block_size)
                    if data[offset:offset + padsize] != b'\x00' * padsize:
                        # For now we are pedantic, and if the padding bytes
                        # are not all zero we throw an Exception.  Depending
                        # one what we see in the wild, we may have to loosen
                        # this check.
                        raise pycdlibexception.PyCdlibInvalidISO('Invalid padding on ISO')

                    offset = offset + padsize
                    continue

                new_record = dr.DirectoryRecord()
                rr = new_record.parse(vd, data[offset:offset + lenbyte],
                                      dir_record)
                offset += lenbyte

                # The parse method of dr.DirectoryRecord returns None if this
                # record doesn't have Rock Ridge extensions, or the version of
                # the Rock Ridge extension (as detected for this directory record).
                self._set_rock_ridge(rr)

                # Cache some properties of this record for later use.
                is_symlink = new_record.rock_ridge is not None and new_record.rock_ridge.is_symlink()
                dots = new_record.is_dot() or new_record.is_dotdot()
                rr_cl = new_record.rock_ridge is not None and new_record.rock_ridge.child_link_record_exists()
                is_dir = new_record.is_dir()
                data_length = new_record.get_data_length()
                new_extent_loc = new_record.extent_location()

                if is_pvd and not dots and not rr_cl and not is_symlink and new_extent_loc not in all_extent_to_dr:
                    all_extent_to_dr[new_extent_loc] = new_record

                # ISO generation programs sometimes use random extent locations
                # for zero-length files.  Thus, it is not valid for us to link
                # zero-length files to other files, as the linkage will be
                # essentially random.  Make sure we ignore zero-length files
                # (which includes symlinks) for linkage.  Similarly, we don't
                # do the lastbyte calculation on zero-length files for the same
                # reason.
                if not is_dir:
                    len_to_use = data_length
                    extent_to_use = new_extent_loc
                    # An important side-effect of this is that zero-length files
                    # or symlinks get an inode, but it is always set to length 0
                    # and location 0 and not actually written out.  This is so
                    # that we can 'link' everything through the Inode.
                    if len_to_use == 0 or is_symlink:
                        len_to_use = 0
                        extent_to_use = 0

                    # Directory Records that point to the El Torito Boot Catalog
                    # do not get Inodes since all of that is handled in-memory.
                    if self.eltorito_boot_catalog is not None and extent_to_use == self.eltorito_boot_catalog.extent_location():
                        self.eltorito_boot_catalog.add_dirrecord(new_record)
                    else:
                        # For all real files, we create an inode that points to
                        # the location on disk.
                        if extent_to_use in extent_to_inode:
                            ino = extent_to_inode[extent_to_use]
                        else:
                            ino = inode.Inode()
                            ino.parse(extent_to_use, len_to_use, cdfp,
                                      block_size)
                            extent_to_inode[extent_to_use] = ino
                            self.inodes.append(ino)

                        ino.linked_records.append(new_record)
                        new_record.inode = ino

                    new_end = extent_to_use * block_size + len_to_use
                    if new_end > iso_file_length:
                        # In this case, the end of the file is beyond the size
                        # of the file.  Since this can't possibly work, truncate
                        # the file size.
                        new_record.inode.data_length = iso_file_length - extent_to_use * block_size
                        for rec in new_record.inode.linked_records:
                            rec.data_length = new_end
                    else:
                        # In this case, the new end is still within the file
                        # size, but the PVD size is wrong.  Set the lastbyte
                        # appropriately, which will eventually be used to fix
                        # the PVD size.
                        lastbyte = max(lastbyte, new_end)

                if new_record.rock_ridge is not None and new_record.rock_ridge.dr_entries.ce_record is not None:
                    ce_record = new_record.rock_ridge.dr_entries.ce_record
                    orig_pos = cdfp.tell()
                    self._seek_to_extent(ce_record.bl_cont_area)
                    cdfp.seek(ce_record.offset_cont_area, os.SEEK_CUR)
                    con_block = cdfp.read(ce_record.len_cont_area)
                    new_record.rock_ridge.parse(con_block, False,
                                                new_record.rock_ridge.bytes_to_skip,
                                                True)
                    cdfp.seek(orig_pos)
                    block = self.pvd.track_rr_ce_entry(ce_record.bl_cont_area,
                                                       ce_record.offset_cont_area,
                                                       ce_record.len_cont_area)
                    new_record.rock_ridge.update_ce_block(block)

                if rr_cl:
                    child_links.append(new_record)

                if is_dir:
                    if new_record.rock_ridge is not None and new_record.rock_ridge.relocated_record():
                        self._rr_moved_record = new_record

                    if new_record.is_dotdot() and new_record.rock_ridge is not None and new_record.rock_ridge.parent_link_record_exists():
                        # If this is the dotdot record, and it has a parent
                        # link record, make sure to link up the parent link
                        # directory record.
                        parent_links.append(new_record)
                    if not dots and not rr_cl:
                        dirs.append(new_record)
                        new_record.set_ptr(extent_to_ptr[new_extent_loc])

                try_long_entry = False
                try:
                    new_record.parent.track_child(new_record, block_size)
                except pycdlibexception.PyCdlibInvalidInput:
                    # dir_record.track_child() may throw a PyCdlibInvalidInput if it
                    # saw a duplicate child.  However, we allow duplicate children
                    # iff this record is a file and the last child has the same name;
                    # this means we have a very long entry.  If that is not the case,
                    # re-raise the error, otherwise pass through to try with the
                    # allow_duplicates flag set to True.
                    if new_record.is_dir() or last_record is None or last_record.file_identifier() != new_record.file_identifier():
                        raise
                    else:
                        try_long_entry = True

                if try_long_entry:
                    new_record.parent.track_child(new_record, block_size, True)

                if is_pvd:
                    if new_record.is_dir():
                        new_level = _interchange_level_from_directory(new_record.file_identifier())
                    else:
                        new_level = _interchange_level_from_filename(new_record.file_identifier())
                    interchange_level = max(interchange_level, new_level)

                last_record = new_record

        for pl in parent_links:
            pl.rock_ridge.parent_link = all_extent_to_dr[pl.rock_ridge.parent_link_extent()]

        for cl in child_links:
            cl.rock_ridge.cl_to_moved_dr = all_extent_to_dr[cl.rock_ridge.child_link_extent()]
            cl.rock_ridge.cl_to_moved_dr.rock_ridge.moved_to_cl_dr = cl

        return interchange_level, lastbyte

    def _initialize(self):
        '''
        An internal method to re-initialize the object.  Called from
        both __init__ and close.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        self._cdfp = None
        self.pvd = None
        self.svds = []
        self.brs = []
        self.vdsts = []
        self.eltorito_boot_catalog = None
        self._initialized = False
        self.rock_ridge = None
        self.isohybrid_mbr = None
        self.xa = False
        self._managing_fp = False
        self.pvds = []
        self.udf_bea = None
        self.udf_nsr = None
        self.udf_tea = None
        self.udf_anchors = []
        self.udf_main_descs = None
        self.udf_reserve_descs = None
        self.udf_logical_volume_integrity = None
        self.udf_logical_volume_integrity_terminator = None
        self.udf_root = None
        self.udf_file_set = None
        self._needs_reshuffle = False
        self._rr_moved_record = None
        self._rr_moved_name = None
        self._rr_moved_rr_name = None
        self.enhanced_vd = None
        self.joliet_vd = None
        self._find_iso_record.cache_clear()  # pylint: disable=no-member
        self._find_rr_record.cache_clear()  # pylint: disable=no-member
        self._find_joliet_record.cache_clear()  # pylint: disable=no-member
        self._find_udf_record.cache_clear()  # pylint: disable=no-member
        self._write_check_list = []
        self.version_vd = None
        self.inodes = []

    def _parse_path_table(self, ptr_size, extent):
        '''
        An internal method to parse a path table on an ISO.  For each path
        table entry found, a Path Table Record object is created, and the
        callback is called.

        Parameters:
         vd - The volume descriptor that these path table records correspond to.
         extent - The extent at which this path table record starts.
         callback - The callback to call for each path table record.
        Returns:
         Nothing.
        '''
        self._seek_to_extent(extent)
        data = self._cdfp.read(ptr_size)
        offset = 0
        out = []
        extent_to_ptr = {}
        while offset < ptr_size:
            ptr = path_table_record.PathTableRecord()
            len_di_byte = bytearray([data[offset]])[0]
            read_len = path_table_record.PathTableRecord.record_length(len_di_byte)

            ptr.parse(data[offset:offset + read_len])
            out.append(ptr)
            extent_to_ptr[ptr.extent_location] = ptr
            offset += read_len

        return out, extent_to_ptr

    def _check_and_parse_eltorito(self, br):
        '''
        An internal method to examine a Boot Record and see if it is an
        El Torito Boot Record.  If it is, parse the El Torito Boot Catalog,
        verification entry, initial entry, and any additional section entries.

        Parameters:
         br - The boot record to examine for an El Torito signature.
        Returns:
         Nothing.
        '''
        if br.boot_system_identifier != b'EL TORITO SPECIFICATION'.ljust(32, b'\x00'):
            return

        if self.eltorito_boot_catalog is not None:
            raise pycdlibexception.PyCdlibInvalidISO('Only one El Torito boot record is allowed')

        # According to the El Torito specification, section 2.0, the El
        # Torito boot record must be at extent 17.
        if br.extent_location() != 17:
            raise pycdlibexception.PyCdlibInvalidISO('El Torito Boot Record must be at extent 17')

        # Now that we have verified that the BootRecord is an El Torito one
        # and that it is sane, we go on to parse the El Torito Boot Catalog.
        # Note that the Boot Catalog is stored as a file in the ISO, though
        # we ignore that for the purposes of parsing.

        self.eltorito_boot_catalog = eltorito.EltoritoBootCatalog(br)
        eltorito_boot_catalog_extent, = struct.unpack_from('=L', br.boot_system_use[:4], 0)

        old = self._cdfp.tell()
        self._cdfp.seek(eltorito_boot_catalog_extent * self.pvd.logical_block_size())
        data = self._cdfp.read(32)
        while not self.eltorito_boot_catalog.parse(data):
            data = self._cdfp.read(32)
        self._cdfp.seek(old)

    def _reshuffle_extents(self):
        '''
        An internal method that is one of the keys of PyCdlib's ability to keep
        the in-memory metadata consistent at all times.  After making any
        changes to the ISO, most API calls end up calling this method.  This
        method will run through the entire ISO, assigning extents to each of
        the pieces of the ISO that exist.  This includes the Primary Volume
        Descriptor (which is fixed at extent 16), the Boot Records (including
        El Torito), the Supplementary Volume Descriptors (including Joliet),
        the Volume Descriptor Terminators, the Version Descriptor, the Primary
        Volume Descriptor Path Table Records (little and big endian), the
        Supplementary Volume Descriptor Path Table Records (little and big
        endian), the Primary Volume Descriptor directory records, the
        Supplementary Volume Descriptor directory records, the Rock Ridge ER
        sector, the El Torito Boot Catalog, the El Torito Initial Entry, and
        finally the data for the files.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        current_extent = 16
        for pvd in self.pvds:
            pvd.new_extent_loc = current_extent
            current_extent += 1

        for br in self.brs:
            br.new_extent_loc = current_extent
            current_extent += 1

        for svd in self.svds:
            svd.new_extent_loc = current_extent
            current_extent += 1

        for vdst in self.vdsts:
            vdst.new_extent_loc = current_extent
            current_extent += 1

        if self.udf_bea is not None:
            self.udf_bea.new_extent_loc = current_extent
            current_extent += 1

            self.udf_nsr.new_extent_loc = current_extent
            current_extent += 1

            self.udf_tea.new_extent_loc = current_extent
            current_extent += 1

        if self.version_vd is not None:
            # Save off an extent for the version descriptor
            self.version_vd.new_extent_loc = current_extent
            current_extent += 1

        part_start = 0

        log_block_size = self.pvd.logical_block_size()

        udf_files = []
        linked_inodes = {}
        if self.udf_main_descs is not None:
            if current_extent > 32:
                # There is no *requirement* in the UDF specification that the
                # UDF Volume Descriptor Sequence starts at extent 32.  It can
                # start anywhere between extents 16 and 256, as long as the
                # ISO9660 volume descriptors, the UDF Bridge Volume Recognition
                # Sequence, Main Volume Descriptor Sequence, Reserve Volume
                # Descriptor Sequence, and Logical Volume Integrity Sequence all
                # all fit, in that order.  The only way that all of these volume
                # descriptors would not fit between extents 16 and 32 is in the
                # case of many duplicate PVDs, many VDSTs, or similar.  Since
                # that is unlikely, for now we maintain compatibility with
                # genisoimage and force the UDF Main Descriptor Sequence to
                # start at 32.  We can change this later if needed.
                raise pycdlibexception.PyCdlibInternalError('Too many ISO9660 volume descriptors to fit UDF')
            current_extent = 32
            _assign_udf_desc_extents(self.udf_main_descs, current_extent)

            # ECMA TR-071 2.6 says that the volume sequence will be exactly 16
            # extents long, and we know we started at 32, so make it exactly 48.
            current_extent = 48
            _assign_udf_desc_extents(self.udf_reserve_descs, current_extent)

            # ECMA TR-071 2.6 says that the volume sequence will be exactly 16
            # extents long, and we know we started at 48, so make it exactly 64.
            current_extent = 64

            self.udf_logical_volume_integrity.set_location(current_extent)
            self.udf_main_descs.logical_volume.set_integrity_location(current_extent)
            self.udf_reserve_descs.logical_volume.set_integrity_location(current_extent)
            current_extent += 1

            self.udf_logical_volume_integrity_terminator.set_location(current_extent)
            current_extent += 1

            # Now assign the first UDF anchor at 256
            if len(self.udf_anchors) != 2:
                raise pycdlibexception.PyCdlibInternalError('Expected 2 UDF anchors')

            # We know that the first anchor is hard-coded at extent 256.  We
            # will have to assign the other one at the end, since it is the
            # last extent
            current_extent = 256
            self.udf_anchors[0].set_location(current_extent,
                                             self.udf_main_descs.pvd.new_extent_loc,
                                             self.udf_reserve_descs.pvd.new_extent_loc)
            current_extent += 1

            # Now assign the UDF File Set Descriptor to the beginning of the partition.
            part_start = current_extent
            self.udf_file_set.new_extent_loc = part_start
            self.udf_main_descs.partition.set_start_location(part_start)
            self.udf_reserve_descs.partition.set_start_location(part_start)
            current_extent += 1

            self.udf_file_set_terminator.set_location(current_extent, current_extent - part_start)
            current_extent += 1

            # Assignment of extents to UDF is somewhat complicated.  UDF
            # filesystems are laid out by having one extent containing a
            # File Entry that describes a directory or a file, followed by
            # an extent that contains the entries in the case of a directory.
            # All File Entries and entries containing File Identifier
            # descriptors are laid out ahead of File Entries for files.  The
            # implementation below alternates assignment to File Entries and
            # File Descriptors for all directories, and then assigns to all
            # files.  Note that data for files is assigned in the 'normal'
            # file assignment below.

            # First assign directories.
            udf_file_assign_list = []
            udf_file_entries = collections.deque([(self.udf_root, None)])
            while udf_file_entries:
                udf_file_entry, fi_desc = udf_file_entries.popleft()

                # In theory we should check for and skip the work for files and
                # symlinks, but they will never be added to 'udf_file_entries'
                # to begin with so we can safely ignore them.

                # Set the location that the File Entry lives at, and update
                # the File Identifier Descriptor that points to it (for all
                # but the root).
                udf_file_entry.set_location(current_extent, current_extent - part_start)
                if fi_desc is not None:
                    fi_desc.set_icb(current_extent, current_extent - part_start)
                current_extent += 1

                # Now assign where the File Entry points to; for files this
                # is overwritten later, but for directories this tells us where
                # to find the extent containing the list of File Identifier
                # Descriptors that are in this directory.
                udf_file_entry.set_data_location(current_extent, current_extent - part_start)
                offset = 0
                for d in udf_file_entry.fi_descs:
                    if offset >= log_block_size:
                        # The offset has spilled over into a new extent.
                        # Increase the current extent by one, and update the
                        # offset.  Note that the offset does not go to 0, since
                        # UDF allows File Identifier Descs to span extents.
                        # Instead, it is the current offset minus the size of a
                        # block (say 2050 - 2048, leaving us at offset 2).
                        current_extent += 1
                        offset = offset - log_block_size

                    d.set_location(current_extent, current_extent - part_start)
                    if not d.is_parent():
                        if d.is_dir():
                            udf_file_entries.append((d.file_entry, d))
                        else:
                            udf_file_assign_list.append((d.file_entry, d))
                    offset += udfmod.UDFFileIdentifierDescriptor.length(len(d.fi))

                if offset > log_block_size:
                    current_extent += 1

                current_extent += 1

            # Now assign files (this includes symlinks).
            udf_file_entry_inodes_assigned = {}
            for udf_file_entry, fi_desc in udf_file_assign_list:
                if udf_file_entry.inode is not None and id(udf_file_entry.inode) in udf_file_entry_inodes_assigned:
                    continue

                udf_file_entry.set_location(current_extent, current_extent - part_start)
                fi_desc.set_icb(current_extent, current_extent - part_start)

                if udf_file_entry.inode is not None:
                    # The data location for files will be set later.
                    if udf_file_entry.inode.get_data_length() > 0:
                        udf_files.append(udf_file_entry.inode)
                    for rec in udf_file_entry.inode.linked_records:
                        if isinstance(rec, udfmod.UDFFileEntry):
                            rec.set_location(current_extent, current_extent - part_start)
                            rec.file_ident.set_icb(current_extent, current_extent - part_start)

                    udf_file_entry_inodes_assigned[id(udf_file_entry.inode)] = True

                current_extent += 1

            self.udf_logical_volume_integrity.logical_volume_contents_use.unique_id = current_extent

        # Next up, put the path table records in the right place.
        for pvd in self.pvds:
            pvd.path_table_location_le = current_extent
        current_extent += self.pvd.path_table_num_extents

        for pvd in self.pvds:
            pvd.path_table_location_be = current_extent
        current_extent += self.pvd.path_table_num_extents

        if self.enhanced_vd is not None:
            self.enhanced_vd.path_table_location_le = self.pvd.path_table_location_le
            self.enhanced_vd.path_table_location_be = self.pvd.path_table_location_be

        if self.joliet_vd is not None:
            self.joliet_vd.path_table_location_le = current_extent
            current_extent += self.joliet_vd.path_table_num_extents
            self.joliet_vd.path_table_location_be = current_extent
            current_extent += self.joliet_vd.path_table_num_extents

        self.pvd.clear_rr_ce_entries()
        current_extent, pvd_files = _reassign_vd_dirrecord_extents(self.pvd,
                                                                   current_extent)

        joliet_files = []
        if self.joliet_vd is not None:
            current_extent, joliet_files = _reassign_vd_dirrecord_extents(self.joliet_vd,
                                                                          current_extent)

        # The rock ridge 'ER' sector must be after all of the directory
        # entries but before the file contents.
        if self.rock_ridge is not None:
            self.pvd.root_directory_record().children[0].rock_ridge.dr_entries.ce_record.update_extent(current_extent)
            current_extent += 1

        def _set_inode(ino, current_extent, part_start):
            '''
            Internal method to set the location of an inode and update the
            metadata of all records attached to it.

            Parameters:
             ino - The inode to update.
             current_extent - The extent to set the inode to.
             part_start - The start of the partition that the inode is on.
            Returns:
             Nothing.
            '''
            ino.set_location(current_extent)
            for rec in ino.linked_records:
                rec.set_data_location(current_extent, current_extent - part_start)

        if self.eltorito_boot_catalog is not None:
            self.eltorito_boot_catalog.update_catalog_extent(current_extent)
            for rec in self.eltorito_boot_catalog.dirrecords:
                rec.set_data_location(current_extent, current_extent - part_start)
            current_extent += utils.ceiling_div(self.eltorito_boot_catalog.dirrecords[0].get_data_length(),
                                                log_block_size)

            entries_to_update = [self.eltorito_boot_catalog.initial_entry]
            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    entries_to_update.append(entry)

            for entry in entries_to_update:
                if id(entry.inode) in linked_inodes:
                    continue

                entry.set_data_location(current_extent, current_extent - part_start)
                if self.isohybrid_mbr is not None:
                    self.isohybrid_mbr.update_rba(current_extent)

                _set_inode(entry.inode, current_extent, part_start)
                linked_inodes[id(entry.inode)] = True
                current_extent += utils.ceiling_div(entry.inode.get_data_length(),
                                                    log_block_size)

        for ino in pvd_files + joliet_files + udf_files:
            if id(ino) in linked_inodes:
                # We've already assigned an extent because it was linked to an
                # earlier entry.
                continue

            _set_inode(ino, current_extent, part_start)

            linked_inodes[id(ino)] = True

            current_extent += utils.ceiling_div(ino.get_data_length(),
                                                log_block_size)

        if self.enhanced_vd is not None:
            self.enhanced_vd.root_directory_record().new_extent_loc = self.pvd.root_directory_record().new_extent_loc

        if self.udf_anchors:
            self.udf_anchors[1].set_location(current_extent,
                                             self.udf_main_descs.pvd.new_extent_loc,
                                             self.udf_reserve_descs.pvd.new_extent_loc)

        if current_extent > self.pvd.space_size:
            raise pycdlibexception.PyCdlibInternalError('Assigned an extent beyond the ISO (%d > %d)' % (current_extent, self.pvd.space_size))

        self._needs_reshuffle = False

    def _add_child_to_dr(self, child, logical_block_size):
        '''
        An internal method to add a child to a directory record, expanding the
        space in the Volume Descriptor(s) if necessary.

        Parameters:
         child - The new child.
         logical_block_size - The size of one logical block.
        Returns:
         The number of bytes to add for this directory record (this may be zero).
        '''
        try_long_entry = False
        try:
            ret = child.parent.add_child(child, logical_block_size)
        except pycdlibexception.PyCdlibInvalidInput:
            # dir_record.add_child() may throw a PyCdlibInvalidInput if
            # it saw a duplicate child.  However, we allow duplicate
            # children iff the last child is the same; this means that
            # we have a very long entry.  If that is the case, try again
            # with the allow_duplicates flag set to True.
            if not child.is_dir():
                try_long_entry = True
            else:
                raise

        if try_long_entry:
            ret = child.parent.add_child(child, logical_block_size, True)

        # The add_child() method returns True if the parent needs another extent
        # in order to fit the directory record for this child.  Add another
        # extent as appropriate here.
        if ret:
            return self.pvd.logical_block_size()

        return 0

    def _remove_child_from_dr(self, child, index, logical_block_size):
        '''
        An internal method to remove a child from a directory record, shrinking
        the space in the Volume Descriptor if necessary.

        Parameters:
         child - The new child.
         index - The index of the child into the parent's child array.
         logical_block_size - The size of one logical block.
        Returns:
         The number of bytes to remove for this directory record (this may be zero).
        '''

        self._find_iso_record.cache_clear()  # pylint: disable=no-member
        self._find_rr_record.cache_clear()  # pylint: disable=no-member
        self._find_joliet_record.cache_clear()  # pylint: disable=no-member

        # The remove_child() method returns True if the parent no longer needs
        # the extent that the directory record for this child was on.  Remove
        # the extent as appropriate here.
        if child.parent.remove_child(child, index, logical_block_size):
            return self.pvd.logical_block_size()

        return 0

    def _add_to_ptr_size(self, ptr):
        '''
        An internal method to add a PTR to a VD, adding space to the VD if
        necessary.

        Parameters:
         ptr - The PTR to add to the vd.
        Returns:
         The number of additional bytes that are needed to fit the new PTR
         (this may be zero).
        '''
        num_bytes_to_add = 0
        for pvd in self.pvds:
            # The add_to_ptr_size() method returns True if the PVD needs
            # additional space in the PTR to store this directory.  We always
            # add 4 additional extents for that (2 for LE, 2 for BE).
            if pvd.add_to_ptr_size(path_table_record.PathTableRecord.record_length(ptr.len_di)):
                num_bytes_to_add += 4 * self.pvd.logical_block_size()

        return num_bytes_to_add

    def _remove_from_ptr_size(self, ptr):
        '''
        An internal method to remove a PTR from a VD, removing space from the VD if
        necessary.

        Parameters:
         ptr - The PTR to remove from the VD.
        Returns:
         The number of bytes to remove from the VDs (this may be zero).
        '''
        num_bytes_to_remove = 0
        for pvd in self.pvds:
            # The remove_from_ptr_size() returns True if the PVD no longer
            # needs the extra extents in the PTR that stored this directory.
            # We always remove 4 additional extents for that.
            if pvd.remove_from_ptr_size(path_table_record.PathTableRecord.record_length(ptr.len_di)):
                num_bytes_to_remove += 4 * self.pvd.logical_block_size()

        return num_bytes_to_remove

    def _find_or_create_rr_moved(self):
        '''
        An internal method to find the /RR_MOVED directory on the ISO.  If it
        already exists, the directory record to it is returned.  If it doesn't
        yet exist, it is created and the directory record to it is returned.

        Parameters:
         None.
        Returns:
         A tuple consisting of the directory record entry matching the rr_moved
         directory and the number of additional bytes needed for the rr_moved
         directory (this may be zero).
        '''

        if self._rr_moved_record is not None:
            return self._rr_moved_record, 0

        if self._rr_moved_name is None:
            self._rr_moved_name = b'RR_MOVED'
        if self._rr_moved_rr_name is None:
            self._rr_moved_rr_name = b'rr_moved'

        # No rr_moved found, so we have to create it.
        rec = dr.DirectoryRecord()
        rec.new_dir(self.pvd, self._rr_moved_name,
                    self.pvd.root_directory_record(),
                    self.pvd.sequence_number(), self.rock_ridge,
                    self._rr_moved_rr_name, self.pvd.logical_block_size(),
                    False, False, self.xa, 0o040555)
        num_bytes_to_add = self._add_child_to_dr(rec,
                                                 self.pvd.logical_block_size())

        self._create_dot(self.pvd, rec, self.rock_ridge, self.xa, 0o040555)
        self._create_dotdot(self.pvd, rec, self.rock_ridge, False, self.xa,
                            0o040555)

        # We always need to add an entry to the path table record
        ptr = path_table_record.PathTableRecord()
        ptr.new_dir(self._rr_moved_name)
        num_bytes_to_add += self.pvd.logical_block_size() + self._add_to_ptr_size(ptr)

        rec.set_ptr(ptr)

        self._rr_moved_record = rec

        return rec, num_bytes_to_add

    def _calculate_eltorito_boot_info_table_csum(self, data_fp, data_len):
        '''
        An internal method to calculate the checksum for an El Torito Boot Info
        Table.  This checksum is a simple 32-bit checksum over all of the data
        in the boot file, starting right after the Boot Info Table itself.

        Parameters:
         data_fp - The file object to read the input data from.
         data_len - The length of the input file.
        Returns:
         An integer representing the 32-bit checksum for the boot info table.
        '''
        # Here we want to read the boot file so we can calculate the checksum
        # over it.
        num_sectors = utils.ceiling_div(data_len, self.pvd.logical_block_size())
        csum = 0
        curr_sector = 0
        while curr_sector < num_sectors:
            block = data_fp.read(self.pvd.logical_block_size())
            block = block.ljust(2048, b'\x00')
            i = 0
            if curr_sector == 0:
                # The first 64 bytes are not included in the checksum, so skip
                # them here.
                i = 64
            while i < len(block):
                tmp, = struct.unpack_from('=L', block[:i + 4], i)
                csum += tmp
                csum = csum & 0xffffffff
                i += 4

            curr_sector += 1

        return csum

    def _check_for_eltorito_boot_info_table(self, ino):
        '''
        An internal method to check a boot directory record to see if it has
        an El Torito Boot Info Table embedded inside of it.

        Parameters:
         ino - The Inode to check for a Boot Info Table.
        Returns:
         Nothing.
        '''
        orig = self._cdfp.tell()
        with inode.InodeOpenData(ino, self.pvd.logical_block_size()) as (data_fp, data_len):
            data_fp.seek(8, os.SEEK_CUR)
            bi_table = eltorito.EltoritoBootInfoTable()
            if bi_table.parse(self.pvd, data_fp.read(eltorito.EltoritoBootInfoTable.header_length()), ino):
                data_fp.seek(-24, os.SEEK_CUR)
                # OK, the rest of the stuff checks out; do a final
                # check to make sure the checksum is reasonable.
                csum = self._calculate_eltorito_boot_info_table_csum(data_fp, data_len)

                if csum == bi_table.csum:
                    ino.add_boot_info_table(bi_table)

        self._cdfp.seek(orig)

    def _check_rr_name(self, rr_name):
        '''
        An internal method to check whether this ISO requires or does not
        require a Rock Ridge path.

        Parameters:
         rr_name - The Rock Ridge name.
        Returns:
         Nothing.
        '''
        if self.rock_ridge is not None:
            if rr_name is None:
                raise pycdlibexception.PyCdlibInvalidInput('A rock ridge name must be passed for a rock-ridge ISO')

            if rr_name.count('/') != 0:
                raise pycdlibexception.PyCdlibInvalidInput('A rock ridge name must be relative')

            return rr_name.encode('utf-8')
        else:
            if rr_name is not None:
                raise pycdlibexception.PyCdlibInvalidInput('A rock ridge name can only be specified for a rock-ridge ISO')

            return None

    def _normalize_joliet_path(self, joliet_path):
        '''
        An internal method to check whether this ISO does or does not require
        a Joliet path.  If a Joliet path is required, the path is normalized
        and returned.

        Parameters:
         joliet_path - The joliet_path to normalize (if necessary).
        Returns:
         The normalized joliet_path if this ISO has Joliet, None otherwise.
        '''
        tmp_path = None
        if self.joliet_vd is not None:
            if joliet_path is None:
                raise pycdlibexception.PyCdlibInvalidInput('A Joliet path must be passed for a Joliet ISO')
            tmp_path = utils.normpath(joliet_path)
        else:
            if joliet_path is not None:
                raise pycdlibexception.PyCdlibInvalidInput('A Joliet path can only be specified for a Joliet ISO')

        return tmp_path

    def _link_eltorito(self, extent_to_inode):
        '''
        An internal method to link the El Torito entries into their
        corresponding Directory Records, creating new ones if they are
        'hidden'.  Should only be called on an El Torito ISO.

        Parameters:
         extent_to_inode - The map that maps extents to Inodes.
        Returns:
         Nothing.
        '''
        log_block_size = self.pvd.logical_block_size()

        entries_to_assign = [self.eltorito_boot_catalog.initial_entry]
        for sec in self.eltorito_boot_catalog.sections:
            for entry in sec.section_entries:
                entries_to_assign.append(entry)

        for entry in entries_to_assign:
            entry_extent = entry.get_rba()
            if entry_extent in extent_to_inode:
                ino = extent_to_inode[entry_extent]
            else:
                ino = inode.Inode()
                ino.parse(entry_extent, entry.length(), self._cdfp,
                          log_block_size)
                extent_to_inode[entry_extent] = ino
                self.inodes.append(ino)

            ino.linked_records.append(entry)
            entry.set_inode(ino)

    def _parse_udf_vol_descs(self, extent, length, descs):
        '''
        An internal method to parse a set of UDF Volume Descriptors.

        Parameters:
         extent - The extent at which to start parsing.
         length - The number of bytes to read from the incoming ISO.
         descs - The UDFDescriptors object to store parsed objects into.
        Returns:
         Nothing.
        '''
        # Read in the Volume Descriptor Sequence
        self._seek_to_extent(extent)
        vd_data = self._cdfp.read(length)

        # And parse it.  Since the sequence doesn't have to be in any set order,
        # and since some of the entries may be missing, we parse the Descriptor
        # Tag (the first 16 bytes) to find out what kind of descriptor it is,
        # then construct the correct type based on that.  We keep going until we
        # see a Terminating Descriptor.

        block_size = self.pvd.logical_block_size()
        offset = 0
        current_extent = extent
        done = False
        while not done:
            desc_tag = udfmod.UDFTag()
            desc_tag.parse(vd_data[offset:], current_extent)
            if desc_tag.tag_ident == 1:
                if descs.pvd is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF PVD; ISO is corrupt')
                descs.pvd = udfmod.UDFPrimaryVolumeDescriptor()
                descs.pvd.parse(vd_data[offset:offset + 512], current_extent, desc_tag)
            elif desc_tag.tag_ident == 4:
                if descs.impl_use is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF Impl Use; ISO is corrupt')
                descs.impl_use = udfmod.UDFImplementationUseVolumeDescriptor()
                descs.impl_use.parse(vd_data[offset:offset + 512], current_extent, desc_tag)
            elif desc_tag.tag_ident == 5:
                if descs.partition is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF Partition; ISO is corrupt')
                descs.partition = udfmod.UDFPartitionVolumeDescriptor()
                descs.partition.parse(vd_data[offset:offset + 512], current_extent, desc_tag)
            elif desc_tag.tag_ident == 6:
                if descs.logical_volume is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF Logical Volume; ISO is corrupt')
                descs.logical_volume = udfmod.UDFLogicalVolumeDescriptor()
                descs.logical_volume.parse(vd_data[offset:offset + 512], current_extent, desc_tag)
            elif desc_tag.tag_ident == 7:
                if descs.unallocated_space is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF Unallocated Space; ISO is corrupt')
                descs.unallocated_space = udfmod.UDFUnallocatedSpaceDescriptor()
                descs.unallocated_space.parse(vd_data[offset:offset + 512], current_extent, desc_tag)
            elif desc_tag.tag_ident == 8:
                if descs.terminator is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Duplicate UDF Terminator; ISO is corrupt')
                descs.terminator = udfmod.UDFTerminatingDescriptor()
                descs.terminator.parse(current_extent, desc_tag)
                done = True
            else:
                raise pycdlibexception.PyCdlibInvalidISO('UDF Tag identifier not %d' % (desc_tag.tag_ident))

            offset += block_size
            current_extent += 1

    def _parse_udf_descriptors(self):
        '''
        An internal method to parse the UDF descriptors on the ISO.  This should
        only be called if it the ISO has a valid UDF Volume Recognition Sequence
        at the beginning of the ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        block_size = self.pvd.logical_block_size()

        # Parse the anchors
        anchor_locations = [(256 * block_size, os.SEEK_SET), (-2048, os.SEEK_END)]
        for loc, whence in anchor_locations:
            self._cdfp.seek(loc, whence)
            extent = self._cdfp.tell() // 2048
            anchor_data = self._cdfp.read(2048)
            anchor_tag = udfmod.UDFTag()
            anchor_tag.parse(anchor_data, extent)
            if anchor_tag.tag_ident != 2:
                raise pycdlibexception.PyCdlibInvalidISO('UDF Anchor Tag identifier not 2')
            anchor = udfmod.UDFAnchorVolumeStructure()
            anchor.parse(anchor_data, extent, anchor_tag)
            self.udf_anchors.append(anchor)

        # Parse the Main Volume Descriptor Sequence
        self._parse_udf_vol_descs(self.udf_anchors[0].main_vd_extent,
                                  self.udf_anchors[0].main_vd_length,
                                  self.udf_main_descs)

        # Parse the Reserve Volume Descriptor Sequence
        self._parse_udf_vol_descs(self.udf_anchors[0].reserve_vd_extent,
                                  self.udf_anchors[0].reserve_vd_length,
                                  self.udf_reserve_descs)

        # Parse the Logical Volume Integrity Sequence
        self._seek_to_extent(self.udf_main_descs.logical_volume.integrity_sequence_extent)
        integrity_data = self._cdfp.read(self.udf_main_descs.logical_volume.integrity_sequence_length)

        offset = 0
        current_extent = self.udf_main_descs.logical_volume.integrity_sequence_extent
        desc_tag = udfmod.UDFTag()
        desc_tag.parse(integrity_data[offset:], current_extent)
        if desc_tag.tag_ident != 9:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Volume Integrity Tag identifier not 9')
        self.udf_logical_volume_integrity = udfmod.UDFLogicalVolumeIntegrityDescriptor()
        self.udf_logical_volume_integrity.parse(integrity_data[offset:offset + 512], current_extent, desc_tag)

        offset += block_size
        current_extent += 1
        desc_tag = udfmod.UDFTag()
        desc_tag.parse(integrity_data[offset:], current_extent)
        if desc_tag.tag_ident != 8:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Logical Volume Integrity Terminator Tag identifier not 8')
        self.udf_logical_volume_integrity_terminator = udfmod.UDFTerminatingDescriptor()
        self.udf_logical_volume_integrity_terminator.parse(current_extent, desc_tag)

        # Now look for the File Set Descriptor
        current_extent = self.udf_main_descs.partition.part_start_location
        self._seek_to_extent(current_extent)
        # Read the data for the File Set and File Terminator together
        file_set_and_term_data = self._cdfp.read(2 * block_size)

        desc_tag = udfmod.UDFTag()
        desc_tag.parse(file_set_and_term_data[:block_size], 0)
        if desc_tag.tag_ident != 256:
            raise pycdlibexception.PyCdlibInvalidISO('UDF File Set Tag identifier not 256')
        self.udf_file_set = udfmod.UDFFileSetDescriptor()
        self.udf_file_set.parse(file_set_and_term_data[:block_size],
                                current_extent, desc_tag)

        current_extent += 1
        desc_tag = udfmod.UDFTag()
        desc_tag.parse(file_set_and_term_data[block_size:],
                       current_extent - self.udf_main_descs.partition.part_start_location)
        if desc_tag.tag_ident != 8:
            raise pycdlibexception.PyCdlibInvalidISO('UDF File Set Terminator Tag identifier not 8')
        self.udf_file_set_terminator = udfmod.UDFTerminatingDescriptor()
        self.udf_file_set_terminator.parse(current_extent, desc_tag)

    def _parse_udf_file_entry(self, abs_file_entry_extent, icb, parent):
        '''
        An internal method to parse a single UDF File Entry and return the
        corresponding object.

        Parameters:
         part_start - The extent number the partition starts at.
         icb - The ICB object for the data.
         parent - The parent of the UDF File Entry.
        Returns:
         A UDF File Entry object corresponding to the on-disk File Entry.
        '''
        self._seek_to_extent(abs_file_entry_extent)
        icbdata = self._cdfp.read(icb.extent_length)

        desc_tag = udfmod.UDFTag()
        desc_tag.parse(icbdata, icb.log_block_num)
        if desc_tag.tag_ident != 261:
            raise pycdlibexception.PyCdlibInvalidISO('UDF File Entry Tag identifier not 261')

        file_entry = udfmod.UDFFileEntry()
        file_entry.parse(icbdata, abs_file_entry_extent, parent, desc_tag)

        return file_entry

    def _walk_udf_directories(self, extent_to_inode):
        '''
        An internal method to walk a UDF filesystem and add all the metadata
        to this object.

        Parameters:
         extent_to_inode - A map from extent numbers to Inodes.
        Returns:
         Nothing.
        '''
        part_start = self.udf_main_descs.partition.part_start_location
        self.udf_root = self._parse_udf_file_entry(part_start + self.udf_file_set.root_dir_icb.log_block_num,
                                                   self.udf_file_set.root_dir_icb,
                                                   None)

        log_block_size = self.pvd.logical_block_size()
        udf_file_entries = collections.deque([self.udf_root])
        while udf_file_entries:
            udf_file_entry = udf_file_entries.popleft()

            for desc_len, desc_pos in udf_file_entry.alloc_descs:
                abs_file_ident_extent = part_start + desc_pos
                self._seek_to_extent(abs_file_ident_extent)
                data = self._cdfp.read(desc_len)
                offset = 0
                while offset < len(data):
                    current_extent = (abs_file_ident_extent * log_block_size + offset) // log_block_size

                    desc_tag = udfmod.UDFTag()
                    desc_tag.parse(data[offset:], current_extent - part_start)
                    if desc_tag.tag_ident != 257:
                        raise pycdlibexception.PyCdlibInvalidISO('UDF File Identifier Tag identifier not 257')
                    file_ident = udfmod.UDFFileIdentifierDescriptor()
                    offset += file_ident.parse(data[offset:],
                                               current_extent,
                                               desc_tag)
                    if file_ident.is_parent():
                        # For a parent, no further work to do.
                        udf_file_entry.track_file_ident_desc(file_ident)
                        continue

                    abs_file_entry_extent = part_start + file_ident.icb.log_block_num
                    next_entry = self._parse_udf_file_entry(abs_file_entry_extent,
                                                            file_ident.icb,
                                                            udf_file_entry)
                    # For a non-parent, we delay adding this to the list of
                    # fi_descs until after we check whether this is a valid
                    # entry or not.
                    udf_file_entry.track_file_ident_desc(file_ident)

                    file_ident.file_entry = next_entry
                    next_entry.file_ident = file_ident

                    if file_ident.is_dir():
                        udf_file_entries.append(next_entry)
                    else:
                        if next_entry.get_data_length() > 0:
                            abs_file_data_extent = part_start + next_entry.alloc_descs[0][1]
                        else:
                            abs_file_data_extent = 0
                        if self.eltorito_boot_catalog is not None and abs_file_data_extent == self.eltorito_boot_catalog.extent_location():
                            self.eltorito_boot_catalog.add_dirrecord(next_entry)
                        else:
                            if abs_file_data_extent in extent_to_inode:
                                ino = extent_to_inode[abs_file_data_extent]
                            else:
                                ino = inode.Inode()
                                ino.parse(abs_file_data_extent,
                                          next_entry.get_data_length(), self._cdfp,
                                          log_block_size)
                                extent_to_inode[abs_file_data_extent] = ino
                                self.inodes.append(ino)

                            ino.linked_records.append(next_entry)
                            next_entry.inode = ino
                udf_file_entry.finish_directory_parse()

    def _open_fp(self, fp):
        '''
        An internal method to open an existing ISO for inspection and
        modification.  Note that the file object passed in here must stay open
        for the lifetime of this object, as the PyCdlib class uses it internally
        to do writing and reading operations.

        Parameters:
         fp - The file object containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if hasattr(fp, 'mode') and 'b' not in fp.mode:
            raise pycdlibexception.PyCdlibInvalidInput("The file to open must be in binary mode (add 'b' to the open flags)")

        self._cdfp = fp

        # Get the Primary Volume Descriptor (pvd), the set of Supplementary
        # Volume Descriptors (svds), the set of Volume Partition
        # Descriptors (vpds), the set of Boot Records (brs), and the set of
        # Volume Descriptor Set Terminators (vdsts)
        self._parse_volume_descriptors()

        old = self._cdfp.tell()
        self._cdfp.seek(0)
        tmp_mbr = isohybrid.IsoHybrid()
        if tmp_mbr.parse(self._cdfp.read(512)):
            # We only save the object if it turns out to be a valid IsoHybrid
            self.isohybrid_mbr = tmp_mbr
        self._cdfp.seek(old)

        if self.pvd.application_use[141:149] == b'CD-XA001':
            self.xa = True

        for br in self.brs:
            self._check_and_parse_eltorito(br)

        # Now that we have the PVD, parse the Path Tables according to Ecma-119
        # section 9.4.  We want to ensure that the big endian versions agree
        # with the little endian ones (to make sure it is a valid ISO).

        # Little Endian first
        le_ptrs, extent_to_ptr = self._parse_path_table(self.pvd.path_table_size(),
                                                        self.pvd.path_table_location_le)

        # Big Endian next.
        tmp_be_ptrs, e_unused = self._parse_path_table(self.pvd.path_table_size(),
                                                       self.pvd.path_table_location_be)

        for index, ptr in enumerate(le_ptrs):
            if not ptr.equal_to_be(tmp_be_ptrs[index]):
                raise pycdlibexception.PyCdlibInvalidISO('Little-endian and big-endian path table records do not agree')

        self.interchange_level = 1
        for svd in self.svds:
            if svd.version == 2 and svd.file_structure_version == 2:
                self.interchange_level = 4
                break

        extent_to_inode = {}

        # OK, so now that we have the PVD, we start at its root directory
        # record and find all of the files
        ic_level, lastbyte = self._walk_directories(self.pvd, extent_to_ptr,
                                                    extent_to_inode, le_ptrs)

        self.interchange_level = max(self.interchange_level, ic_level)

        # On El Torito ISOs, after we have walked the directories we look
        # to see if all of the entries in El Torito have corresponding
        # directory records.  If they don't, then it may be the case that
        # the El Torito bits of the system are 'hidden' or 'unlinked',
        # meaning that they take up space but have no corresponding directory
        # record in the ISO filesystem.  In order to accommodate the rest
        # of the system, which really expects these things to have directory
        # records, we use fake directory records that don't get written out.
        #
        # Note that we specifically do *not* add these to any sort of parent;
        # that way, we don't run afoul of any checks that adding a child to a
        # parent might have.  This means that if we do ever want to unhide this
        # entry, we'll have to do some additional work to give it a real name
        # and link it to the appropriate parent.
        if self.eltorito_boot_catalog is not None:
            self._link_eltorito(extent_to_inode)

            # Now that everything has a dirrecord, see if we have a boot
            # info table.
            self._check_for_eltorito_boot_info_table(self.eltorito_boot_catalog.initial_entry.inode)
            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    self._check_for_eltorito_boot_info_table(entry.inode)

        # The PVD is finished.  Now look to see if we need to parse the SVD.
        for svd in self.svds:
            if (svd.flags & 0x1) == 0 and svd.escape_sequences[:3] in (b'%/@', b'%/C', b'%/E'):
                if self.joliet_vd is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Only a single Joliet SVD is supported')

                self.joliet_vd = svd

                le_ptrs, joliet_extent_to_ptr = self._parse_path_table(svd.path_table_size(),
                                                                       svd.path_table_location_le)

                tmp_be_ptrs, j_unused = self._parse_path_table(svd.path_table_size(),
                                                               svd.path_table_location_be)

                for index, ptr in enumerate(le_ptrs):
                    if not ptr.equal_to_be(tmp_be_ptrs[index]):
                        raise pycdlibexception.PyCdlibInvalidISO('Joliet Little-endian and big-endian path table records do not agree')

                self._walk_directories(svd, joliet_extent_to_ptr,
                                       extent_to_inode, le_ptrs)
            elif svd.version == 2 and svd.file_structure_version == 2:
                if self.enhanced_vd is not None:
                    raise pycdlibexception.PyCdlibInvalidISO('Only a single enhanced VD is supported')
                self.enhanced_vd = svd

        # We've seen ISOs in the wild (Office XP) that have a PVD space size
        # that is smaller than the location of the last directory record
        # extent + length.  If we see this, automatically update the size in the
        # PVD (and any SVDs) so that subsequent operations will be correct.
        log_block_size = self.pvd.logical_block_size()
        if lastbyte > self.pvd.space_size * log_block_size:
            new_pvd_size = utils.ceiling_div(lastbyte, log_block_size)
            for pvd in self.pvds:
                pvd.space_size = new_pvd_size
            if self.joliet_vd is not None:
                self.joliet_vd.space_size = new_pvd_size
            if self.enhanced_vd is not None:
                self.enhanced_vd.space_size = new_pvd_size

        # Look to see if this is a UDF volume.  It is one if we have a UDF BEA,
        # UDF NSR, and UDF TEA, in which case we parse the UDF descriptors and
        # walk the filesystem.
        if self.udf_bea is not None and self.udf_nsr is not None and self.udf_tea is not None:
            self.udf_main_descs = self.UDFDescriptors()
            self.udf_reserve_descs = self.UDFDescriptors()
            self._parse_udf_descriptors()
            self._walk_udf_directories(extent_to_inode)

        # Now we look for the 'version' volume descriptor, common on ISOs made
        # with genisoimage or mkisofs.  This volume descriptor doesn't have any
        # specification, but from code inspection, it is either a completely
        # zero extent, or starts with 'MKI'.  Further, it starts directly after
        # the VDST, or directly after the UDF recognition sequence (if this is
        # a UDF ISO).  Thus, we go looking for it at those places, and add it
        # if we find it there.
        version_vd_extent = self.vdsts[0].extent_location() + 1
        if self.udf_bea is not None and self.udf_nsr is not None and self.udf_tea is not None:
            version_vd_extent = self.udf_tea.extent_location() + 1

        version_vd = headervd.VersionVolumeDescriptor()
        self._cdfp.seek(version_vd_extent * log_block_size)
        if version_vd.parse(self._cdfp.read(log_block_size), version_vd_extent):
            self.version_vd = version_vd

        self._initialized = True

    def _get_and_write_fp(self, iso_path, outfp, blocksize):
        '''
        An internal method to fetch a single file from the ISO and write it out
        to the file object.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         outfp - The file object to write data to.
         blocksize - The blocksize to use when copying data.
        Returns:
         Nothing.
        '''
        try:
            return self._get_file_from_iso_fp(outfp, joliet_path=iso_path, blocksize=blocksize)
        except pycdlibexception.PyCdlibException:
            pass

        try:
            return self._get_file_from_iso_fp(outfp, iso_path=iso_path, blocksize=blocksize)
        except pycdlibexception.PyCdlibException:
            pass

        self._get_file_from_iso_fp(outfp, rr_path=iso_path, blocksize=blocksize)

    def _get_file_from_iso_fp(self, outfp, **kwargs):
        '''
        An internal method to fetch a single file from the ISO and write it out
        to the file object.

        Parameters:
         outfp - The file object to write data to.
         blocksize - The number of bytes in each transfer.
         iso_path - The absolute ISO9660 path to lookup on the ISO (exclusive
                    with rr_path, joliet_path, and udf_path).
         rr_path - The absolute Rock Ridge path to lookup on the ISO (exclusive
                   with iso_path, joliet_path, and udf_path).
         joliet_path - The absolute Joliet path to lookup on the ISO (exclusive
                       with iso_path, rr_path, and udf_path).
         udf_path - The absolute UDF path to lookup on the ISO (exclusive with
                    iso_path, rr_path, and joliet_path).
        Returns:
         Nothing.
        '''
        blocksize = 8192
        joliet_path = None
        iso_path = None
        rr_path = None
        udf_path = None
        num_paths = 0
        for key in kwargs:
            if key == 'blocksize':
                blocksize = kwargs[key]
            elif key == 'iso_path' and kwargs[key] is not None:
                iso_path = utils.normpath(kwargs[key])
                num_paths += 1
            elif key == 'rr_path' and kwargs[key] is not None:
                rr_path = utils.normpath(kwargs[key])
                num_paths += 1
            elif key == 'joliet_path' and kwargs[key] is not None:
                joliet_path = utils.normpath(kwargs[key])
                num_paths += 1
            elif key == 'udf_path' and kwargs[key] is not None:
                udf_path = utils.normpath(kwargs[key])
                num_paths += 1
            else:
                raise pycdlibexception.PyCdlibInvalidInput('Unknown keyword %s' % (key))

        if num_paths != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Exactly one of iso_path, rr_path, or joliet_path must be passed')

        if udf_path is not None:
            if self.udf_root is None:
                raise pycdlibexception.PyCdlibInvalidInput('Cannot fetch a udf_path from a non-UDF ISO')
            found_file_entry = self._find_udf_record(udf_path)
            if not found_file_entry.is_file():
                raise pycdlibexception.PyCdlibInvalidInput('Can only write out a file')

            if found_file_entry.get_data_length() > 0:
                with inode.InodeOpenData(found_file_entry.inode, self.pvd.logical_block_size()) as (data_fp, data_len):
                    utils.copy_data(data_len, blocksize, data_fp, outfp)

        else:
            if joliet_path is not None:
                if self.joliet_vd is None:
                    raise pycdlibexception.PyCdlibInvalidInput('Cannot fetch a joliet_path from a non-Joliet ISO')
                found_record = self._find_joliet_record(joliet_path)
            elif rr_path is not None:
                if self.rock_ridge is None:
                    raise pycdlibexception.PyCdlibInvalidInput('Cannot fetch a rr_path from a non-Rock Ridge ISO')
                found_record = self._find_rr_record(rr_path)
            else:
                found_record = self._find_iso_record(iso_path)

            if found_record.is_dir():
                raise pycdlibexception.PyCdlibInvalidInput('Cannot write out a directory')

            if rr_path is not None or iso_path is not None:
                if found_record.rock_ridge is not None and found_record.rock_ridge.is_symlink():
                    # If this Rock Ridge record is a symlink, it has no data
                    # associated with it, so it makes no sense to try and get the
                    # data.  In theory, we could follow the symlink to the
                    # appropriate place and get the data of the thing it points to.
                    # However, Rock Ridge symlinks are allowed to point *outside*
                    # of this ISO, so it is really not clear that this is something
                    # we want to do.  For now we make the user follow the symlink
                    # themselves if they want to get the data.  We can revisit this
                    # decision in the future if we need to.
                    raise pycdlibexception.PyCdlibInvalidInput('Symlinks have no data associated with them')

            while found_record is not None and found_record.get_data_length() > 0:
                with inode.InodeOpenData(found_record.inode, self.pvd.logical_block_size()) as (data_fp, data_len):
                    # Here we copy the data into the output file descriptor.  If a boot
                    # info table is present, we overlay the table over bytes 8-64 of the
                    # file.  Note, however, that we never return more bytes than the length
                    # of the file, so the boot info table may get truncated.
                    if found_record.inode.boot_info_table is not None:
                        header_len = min(data_len, 8)
                        outfp.write(data_fp.read(header_len))
                        data_len -= header_len
                        if data_len > 0:
                            rec = found_record.inode.boot_info_table.record()
                            table_len = min(data_len, len(rec))
                            outfp.write(rec[:table_len])
                            data_len -= table_len
                            if data_len > 0:
                                data_fp.seek(len(rec), os.SEEK_CUR)
                                utils.copy_data(data_len, blocksize, data_fp, outfp)
                    else:
                        utils.copy_data(data_len, blocksize, data_fp, outfp)

                if found_record.data_continuation is not None:
                    found_record = found_record.data_continuation
                else:
                    found_record = None

    class _WriteRange(object):
        '''
        A class to store the offset and length of a written section of data.
        A sorted list of these is used to determine whether we are unintentionally
        spending time rewriting data that we have already written.
        '''
        __slots__ = ('offset', 'length')

        def __init__(self, start, end):
            self.offset = start
            self.length = start + (end - start)

        def __lt__(self, other):
            # When we go to insert this into the list, we determine if this one
            # overlaps with the one we are currently looking at.
            if range(max(other.offset, self.offset), min(other.length, self.length) + 1):
                raise pycdlibexception.PyCdlibInternalError('Overlapping write %s, %s' % (repr(self), repr(other)))
            return self.offset < other.offset

        def __repr__(self):
            return 'WriteRange: %s %s' % (self.offset, self.length)

    def _outfp_write_with_check(self, outfp, data, enable_overwrite_check=True):
        '''
        Internal method to write data out to the output file descriptor,
        ensuring that it doesn't go beyond the bounds of the ISO.

        Parameters:
         outfp - The file object to write to.
         data - The actual data to write.
         enable_overwrite_check - Whether to do overwrite checking if it is enabled.  Some pieces of code explicitly want to overwrite data, so this allows them to disable the checking.
        Returns:
         Nothing.
        '''
        start = outfp.tell()
        outfp.write(data)
        if self._track_writes:
            # After the write, double check that we didn't write beyond the
            # boundary of the PVD, and raise a PyCdlibException if we do.
            end = outfp.tell()
            if end > self.pvd.space_size * self.pvd.logical_block_size():
                raise pycdlibexception.PyCdlibInternalError('Wrote past the end of the ISO! (%d > %d)' % (end, self.pvd.space_size * self.pvd.logical_block_size()))

            if enable_overwrite_check:
                bisect.insort_left(self._write_check_list, self._WriteRange(start, end - 1))

    def _output_file_data(self, outfp, blocksize, ino):
        '''
        Internal method to write a directory record entry out.

        Parameters:
         outfp - The file object to write the data to.
         blocksize - The blocksize to use when writing the data out.
         ino - The Inode to write.
        Returns:
         The total number of bytes written out.
        '''
        log_block_size = self.pvd.logical_block_size()

        outfp.seek(ino.extent_location() * log_block_size)
        tmp_start = outfp.tell()
        with inode.InodeOpenData(ino, log_block_size) as (data_fp, data_len):
            utils.copy_data(data_len, blocksize, data_fp, outfp)
            utils.zero_pad(outfp, data_len, log_block_size)

        if self._track_writes:
            end = outfp.tell()
            bisect.insort_left(self._write_check_list, self._WriteRange(tmp_start, end - 1))

        # If this file is being used as a bootfile, and the user
        # requested that the boot info table be patched into it,
        # we patch the boot info table at offset 8 here.
        if ino.boot_info_table is not None:
            old = outfp.tell()
            outfp.seek(tmp_start + 8)
            self._outfp_write_with_check(outfp, ino.boot_info_table.record(),
                                         enable_overwrite_check=False)
            outfp.seek(old)
        return outfp.tell() - tmp_start

    def _write_directory_records(self, vd, outfp, progress):
        '''
        An internal method to write out the directory records from a particular
        Volume Descriptor.

        Parameters:
         vd - The Volume Descriptor to write the Directory Records from.
         outfp - The file object to write data to.
         progress - The Progress object to use for outputting progress.
        Returns:
         Nothing.
        '''
        log_block_size = vd.logical_block_size()
        le_ptr_offset = 0
        be_ptr_offset = 0
        dirs = collections.deque([vd.root_directory_record()])
        while dirs:
            curr = dirs.popleft()
            curr_dirrecord_offset = 0
            if curr.is_dir():
                # Little Endian PTR
                outfp.seek(vd.path_table_location_le * log_block_size + le_ptr_offset)
                ret = curr.ptr.record_little_endian()
                self._outfp_write_with_check(outfp, ret)
                le_ptr_offset += len(ret)

                # Big Endian PTR
                outfp.seek(vd.path_table_location_be * log_block_size + be_ptr_offset)
                ret = curr.ptr.record_big_endian()
                self._outfp_write_with_check(outfp, ret)
                be_ptr_offset += len(ret)
                progress.call(curr.get_data_length())

            dir_extent = curr.extent_location()
            for child in curr.children:
                # No matter what type the child is, we need to first write
                # out the directory record entry.
                recstr = child.record()
                if (curr_dirrecord_offset + len(recstr)) > log_block_size:
                    dir_extent += 1
                    curr_dirrecord_offset = 0
                outfp.seek(dir_extent * log_block_size + curr_dirrecord_offset)
                # Now write out the child
                self._outfp_write_with_check(outfp, recstr)
                curr_dirrecord_offset += len(recstr)

                if child.rock_ridge is not None:
                    if child.rock_ridge.dr_entries.ce_record is not None:
                        # The child has a continue block, so write it out here.
                        ce_rec = child.rock_ridge.dr_entries.ce_record
                        outfp.seek(ce_rec.bl_cont_area * self.pvd.logical_block_size() + ce_rec.offset_cont_area)
                        rec = child.rock_ridge.record_ce_entries()
                        self._outfp_write_with_check(outfp, rec)
                        progress.call(len(rec))

                    if child.rock_ridge.child_link_record_exists():
                        continue

                if child.is_dir():
                    # If the child is a directory, and is not dot or dotdot,
                    # we want to descend into it to look at the children.
                    if not child.is_dot() and not child.is_dotdot():
                        dirs.append(child)

    def _write_udf_descs(self, descs, outfp, progress):
        '''
        An internal method to write out a UDF Descriptor sequence.

        Parameters:
         descs - The UDF Descriptors object to write out.
         outfp - The output file descriptor to use for writing.
         progress - The Progress object to use for updating progress.
        Returns:
         Nothing.
        '''
        log_block_size = self.pvd.logical_block_size()

        outfp.seek(descs.pvd.extent_location() * log_block_size)
        rec = descs.pvd.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

        outfp.seek(descs.impl_use.extent_location() * log_block_size)
        rec = descs.impl_use.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

        outfp.seek(descs.partition.extent_location() * log_block_size)
        rec = descs.partition.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

        outfp.seek(descs.logical_volume.extent_location() * log_block_size)
        rec = descs.logical_volume.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

        outfp.seek(descs.unallocated_space.extent_location() * log_block_size)
        rec = descs.unallocated_space.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

        outfp.seek(descs.terminator.extent_location() * log_block_size)
        rec = descs.terminator.record()
        self._outfp_write_with_check(outfp, rec)
        progress.call(len(rec))

    def _write_fp(self, outfp, blocksize, progress_cb, progress_opaque):
        '''
        Write a properly formatted ISO out to the file object passed in.  This
        also goes by the name of 'mastering'.

        Parameters:
         outfp - The file object to write the data to.
         blocksize - The blocksize to use when copying data.
         progress_cb - If not None, a function to call as the write call does its
                       work.  The callback function must have a signature of:
                       def func(done, total).
         progress_opaque - User data to be passed to the progress callback.
        Returns:
         Nothing.
        '''
        if hasattr(outfp, 'mode') and 'b' not in outfp.mode:
            raise pycdlibexception.PyCdlibInvalidInput("The file to write out must be in binary mode (add 'b' to the open flags)")

        if self._needs_reshuffle:
            self._reshuffle_extents()

        self._write_check_list = []
        outfp.seek(0)

        class Progress(object):
            '''
            An inner class to deal with progress.
            '''
            __slots__ = ('done', 'total')

            def __init__(self, total):
                self.done = 0
                self.total = total

            def call(self, length):
                '''
                Add the length to done, then call progress_cb if it is not None.
                '''
                self.done += length
                if self.done > self.total:
                    self.done = self.total
                if progress_cb is not None:
                    if len(inspect.getargspec(progress_cb).args) == 2:  # pylint: disable=W1505
                        progress_cb(self.done, self.total)
                    else:
                        progress_cb(self.done, self.total, progress_opaque)

            def finish(self):
                '''
                If the progress_cb is not None, call progress_cb with the
                final total.
                '''
                # In almost all cases, this will cause self.done to wildly
                # overflow the total size.  However, with the hard cap in
                # call, this works just fine.
                self.call(self.total)

        log_block_size = self.pvd.logical_block_size()

        progress = Progress(self.pvd.space_size * log_block_size)
        progress.call(0)

        if self.isohybrid_mbr is not None:
            self._outfp_write_with_check(outfp,
                                         self.isohybrid_mbr.record(self.pvd.space_size * log_block_size))

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.  Thus
        # we skip the first 16 sectors.
        outfp.seek(self.pvd.extent_location() * log_block_size)

        # First write out the PVD.
        for pvd in self.pvds:
            rec = pvd.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Next write out the boot records.
        for br in self.brs:
            outfp.seek(br.extent_location() * log_block_size)
            rec = br.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Next we write out the SVDs.
        for svd in self.svds:
            outfp.seek(svd.extent_location() * log_block_size)
            rec = svd.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Next we write out the Volume Descriptor Terminators.
        for vdst in self.vdsts:
            outfp.seek(vdst.extent_location() * log_block_size)
            rec = vdst.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Next we write out the UDF Volume Recognition sequence (if we are a
        # UDF ISO).
        if self.udf_bea is not None:
            outfp.seek(self.udf_bea.extent_location() * log_block_size)
            rec = self.udf_bea.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

            outfp.seek(self.udf_nsr.extent_location() * log_block_size)
            rec = self.udf_nsr.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

            outfp.seek(self.udf_tea.extent_location() * log_block_size)
            rec = self.udf_tea.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Next we write out the version block if it exists.
        if self.version_vd is not None:
            outfp.seek(self.version_vd.extent_location() * log_block_size)
            rec = self.version_vd.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Now the UDF Main and Reserved Volume Descriptor Sequence
        if self.udf_main_descs is not None:
            self._write_udf_descs(self.udf_main_descs, outfp, progress)
            self._write_udf_descs(self.udf_reserve_descs, outfp, progress)

        # Now the UDF Logical Volume Integrity Sequence (if there is one).
        if self.udf_logical_volume_integrity is not None:
            outfp.seek(self.udf_logical_volume_integrity.extent_location() * log_block_size)
            rec = self.udf_logical_volume_integrity.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

            outfp.seek(self.udf_logical_volume_integrity_terminator.extent_location() * log_block_size)
            rec = self.udf_logical_volume_integrity_terminator.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Now the UDF Anchor Points (if there are any).
        for anchor in self.udf_anchors:
            outfp.seek(anchor.extent_location() * log_block_size)
            rec = anchor.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # In theory, the Path Table Records (for both the PVD and SVD) get
        # written out next.  Since we store them along with the Directory
        # Records, however, we will write them out along with the directory
        # records instead.

        # Now write out the El Torito Boot Catalog if it exists.
        if self.eltorito_boot_catalog is not None:
            outfp.seek(self.eltorito_boot_catalog.extent_location() * log_block_size)
            rec = self.eltorito_boot_catalog.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

        # Now write out the ISO9660 directory records.
        self._write_directory_records(self.pvd, outfp, progress)

        # Now write out the Joliet directory records, if they exist.
        if self.joliet_vd is not None:
            self._write_directory_records(self.joliet_vd, outfp, progress)

        # Now write out the UDF directory records, if they exist.
        if self.udf_root is not None:
            # Write out the UDF File Sets
            outfp.seek(self.udf_file_set.extent_location() * log_block_size)
            rec = self.udf_file_set.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

            outfp.seek(self.udf_file_set_terminator.extent_location() * log_block_size)
            rec = self.udf_file_set_terminator.record()
            self._outfp_write_with_check(outfp, rec)
            progress.call(len(rec))

            written_file_entry_inodes = {}
            udf_file_entries = collections.deque([(self.udf_root, True)])
            while udf_file_entries:
                udf_file_entry, isdir = udf_file_entries.popleft()

                if udf_file_entry.inode is None or not id(udf_file_entry.inode) in written_file_entry_inodes:
                    outfp.seek(udf_file_entry.extent_location() * log_block_size)
                    rec = udf_file_entry.record()
                    self._outfp_write_with_check(outfp, rec)
                    progress.call(len(rec))
                    written_file_entry_inodes[id(udf_file_entry.inode)] = True

                if isdir:
                    outfp.seek(udf_file_entry.fi_descs[0].extent_location() * log_block_size)
                    # FIXME: for larger directories, we'll actually need to
                    # iterate over the alloc_descs and write them
                    for fi_desc in udf_file_entry.fi_descs:
                        rec = fi_desc.record()
                        self._outfp_write_with_check(outfp, rec)
                        progress.call(len(rec))
                        if not fi_desc.is_parent():
                            udf_file_entries.append((fi_desc.file_entry, fi_desc.is_dir()))

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        for ino in self.inodes:
            if ino.get_data_length() > 0:
                progress.call(self._output_file_data(outfp, blocksize, ino))

        # We need to pad out to the total size of the disk, in the case that
        # the last thing we wrote is shorter than a full block size.  It turns
        # out that not all file-like objects allow you to use truncate() to
        # grow the file, so we do it the old-fashioned way by seeking to the
        # end - 1 and writing a padding '\x00' byte.
        outfp.seek(0, os.SEEK_END)
        total_size = self.pvd.space_size * log_block_size
        if outfp.tell() != total_size:
            outfp.seek(total_size - 1)
            outfp.write(b'\x00')

        if self.isohybrid_mbr is not None:
            outfp.seek(0, os.SEEK_END)
            # Note that we very specifically do not call
            # self._outfp_write_with_check here because this writes outside
            # the PVD boundaries.
            outfp.write(self.isohybrid_mbr.record_padding(self.pvd.space_size * log_block_size))

        progress.finish()

    def _update_rr_ce_entry(self, rec):
        '''
        An internal method to update the Rock Ridge CE entry for the given
        record.

        Parameters:
         rec - The record to update the Rock Ridge CE entry for (if it exists).
        Returns:
         The number of additional bytes needed for this Rock Ridge CE entry.
        '''
        if rec.rock_ridge is not None and rec.rock_ridge.dr_entries.ce_record is not None:
            celen = rec.rock_ridge.dr_entries.ce_record.len_cont_area
            added_block, block, offset = self.pvd.add_rr_ce_entry(celen)
            rec.rock_ridge.update_ce_block(block)
            rec.rock_ridge.dr_entries.ce_record.update_offset(offset)
            if added_block:
                return self.pvd.logical_block_size()

        return 0

    def _finish_add(self, num_bytes_to_add, num_partition_bytes_to_add):
        '''
        An internal method to do all of the accounting needed whenever
        something is added to the ISO.  This method should only be called by
        public API implementations.

        Parameters:
         num_bytes_to_add - The number of additional bytes to add to all
                            descriptors.
         num_partition_bytes_to_add - The number of additional bytes to add to
                                      the partition if this is a UDF file.
        Returns:
         Nothing.
        '''
        for pvd in self.pvds:
            pvd.add_to_space_size(num_bytes_to_add + num_partition_bytes_to_add)
        if self.joliet_vd is not None:
            self.joliet_vd.add_to_space_size(num_bytes_to_add + num_partition_bytes_to_add)

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        if self.udf_root is not None:
            num_extents_to_add = utils.ceiling_div(num_partition_bytes_to_add,
                                                   self.pvd.logical_block_size())

            self.udf_main_descs.partition.part_length += num_extents_to_add
            self.udf_reserve_descs.partition.part_length += num_extents_to_add
            self.udf_logical_volume_integrity.size_table += num_extents_to_add

        if self._always_consistent:
            self._reshuffle_extents()
        else:
            self._needs_reshuffle = True

    def _finish_remove(self, num_bytes_to_remove, is_partition):
        '''
        An internal method to do all of the accounting needed whenever
        something is removed from the ISO.  This method should only be called
        by public API implementations.

        Parameters:
         num_bytes_to_remove - The number of additional bytes to remove from the descriptors.
         is_partition - Whether these bytes are part of a UDF partition.
        Returns:
         Nothing.
        '''
        for pvd in self.pvds:
            pvd.remove_from_space_size(num_bytes_to_remove)
        if self.joliet_vd is not None:
            self.joliet_vd.remove_from_space_size(num_bytes_to_remove)

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        if self.udf_root is not None and is_partition:
            num_extents_to_remove = utils.ceiling_div(num_bytes_to_remove,
                                                      self.pvd.logical_block_size())

            self.udf_main_descs.partition.part_length -= num_extents_to_remove
            self.udf_reserve_descs.partition.part_length -= num_extents_to_remove
            self.udf_logical_volume_integrity.size_table -= num_extents_to_remove

        if self._always_consistent:
            self._reshuffle_extents()
        else:
            self._needs_reshuffle = True

    def _add_hard_link_to_rec(self, old_rec, boot_catalog_old, **kwargs):
        '''
        Add a hard link to the ISO.  Hard links are alternate names for the
        same file contents that don't take up any additional space on the ISO.
        This API can be used to create hard links between two files on the
        ISO9660 filesystem, between two files on the Joliet filesystem, or
        between a file on the ISO9660 filesystem and the Joliet filesystem.
        In all cases, exactly one old path must be specified, and exactly one
        new path must be specified.

        Parameters:
         old_rec - The old record to link against.
         boot_catalog_old - Whether this is a link to an old boot catalog.
         iso_new_path - The new path on the ISO9660 filesystem to link to.
         joliet_new_path - The new path on the Joliet filesystem to link to.
         rr_name - The Rock Ridge name to use for the new file if this is a
                   Rock Ridge ISO and the new path is on the ISO9660 filesystem.
         udf_new_path - The new path on the UDF filesystem to link to.
        Returns:
         The number of bytes to add to the descriptors.
        '''
        num_new = 0
        iso_new_path = None
        joliet_new_path = None
        rr_name = None
        udf_new_path = None
        for key in kwargs:
            if key == 'iso_new_path' and kwargs[key] is not None:
                num_new += 1
                iso_new_path = utils.normpath(kwargs[key])
                if self.rock_ridge is None:
                    _check_path_depth(iso_new_path)
            elif key == 'joliet_new_path' and kwargs[key] is not None:
                num_new += 1
                joliet_new_path = self._normalize_joliet_path(kwargs[key])
            elif key == 'rr_name' and kwargs[key] is not None:
                rr_name = self._check_rr_name(kwargs[key])
            elif key == 'udf_new_path' and kwargs[key] is not None:
                num_new += 1
                udf_new_path = utils.normpath(kwargs[key])
            else:
                raise pycdlibexception.PyCdlibInvalidInput('Unknown keyword %s' % (key))

        if num_new != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Exactly one new path must be specified')
        if self.rock_ridge is not None and iso_new_path is not None and rr_name is None:
            raise pycdlibexception.PyCdlibInvalidInput('Rock Ridge name must be supplied for a Rock Ridge new path')

        data_ino = old_rec.inode

        num_bytes_to_add = 0
        if udf_new_path is None:
            file_mode = None
            if iso_new_path is not None:
                # ... to another file on the ISO9660 filesystem.
                (new_name, new_parent) = self._name_and_parent_from_path(iso_path=iso_new_path)
                vd = self.pvd
                rr = self.rock_ridge
                xa = self.xa
                if self.rock_ridge:
                    file_mode = old_rec.rock_ridge.get_file_mode()
            elif joliet_new_path is not None:
                # ... to a file on the Joliet filesystem.
                (new_name, new_parent) = self._name_and_parent_from_path(joliet_path=joliet_new_path)
                vd = self.joliet_vd
                rr = None
                xa = False
            # Above we checked to make sure we got at least one new path, so we
            # don't need to worry about the else situation here.

            new_rec = dr.DirectoryRecord()
            new_rec.new_file(vd, old_rec.get_data_length(), new_name,
                             new_parent, vd.sequence_number(), rr, rr_name, xa,
                             file_mode)

            num_bytes_to_add += self._add_child_to_dr(new_rec,
                                                      vd.logical_block_size())
        else:
            if self.udf_root is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only specify a udf_path for a UDF ISO')

            log_block_size = self.pvd.logical_block_size()

            # UDF new path
            (udf_name, udf_parent) = self._name_and_parent_from_path(udf_path=udf_new_path)

            file_ident = udfmod.UDFFileIdentifierDescriptor()
            file_ident.new(False, False, udf_name)
            num_new_extents = udf_parent.add_file_ident_desc(file_ident, log_block_size)
            num_bytes_to_add += num_new_extents * log_block_size

            file_entry = udfmod.UDFFileEntry()
            file_entry.new(old_rec.get_data_length(), 'file', udf_parent,
                           log_block_size)
            file_ident.file_entry = file_entry
            file_entry.file_ident = file_ident
            if data_ino is None or data_ino.num_udf == 0:
                num_bytes_to_add += log_block_size

            if data_ino is not None:
                data_ino.num_udf += 1

            new_rec = file_entry

            self.udf_logical_volume_integrity.logical_volume_impl_use.num_files += 1

        if data_ino is not None:
            data_ino.linked_records.append(new_rec)
            new_rec.inode = data_ino

        if boot_catalog_old:
            self.eltorito_boot_catalog.add_dirrecord(new_rec)

        return num_bytes_to_add

    def _add_fp(self, fp, length, manage_fp, iso_path, rr_name, joliet_path,
                udf_path, file_mode, eltorito_catalog):
        '''
        An internal method to add a file to the ISO.  If the ISO contains Rock
        Ridge, then a Rock Ridge name must be provided.  If the ISO contains
        Joliet, then a Joliet path is not required but is highly recommended.
        Note that the caller must ensure that the file remains open for the
        lifetime of the ISO object, as the PyCdlib class uses the file
        descriptor internally when writing (mastering) the ISO.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the data for the new file.
         manage_fp - Whether or not pycdlib should internally manage the file
                     pointer.  It is faster to manage the file pointer
                     externally, but it is more convenient to have pycdlib do it
                     internally.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
         udf_path - The UDF absolute path to the file destination on the ISO.
         file_mode - The POSIX file_mode to apply to this file.  This only
                     applies if this is a Rock Ridge ISO.  If this is None (the
                     default), the permissions from the original file are used.
        Returns:
         The number of bytes to add to the descriptors.
        '''

        iso_path = utils.normpath(iso_path)

        rr_name = self._check_rr_name(rr_name)

        # We call _normalize_joliet_path here even though we aren't going to
        # use the result.  This is to ensure that we throw an exception when
        # a joliet_path is passed for a non-Joliet ISO.
        if joliet_path is not None:
            self._normalize_joliet_path(joliet_path)

        if udf_path is not None and self.udf_root is None:
            raise pycdlibexception.PyCdlibInvalidInput('Can only specify a UDF path for a UDF ISO')

        if self.rock_ridge is None:
            _check_path_depth(iso_path)
        (name, parent) = self._name_and_parent_from_path(iso_path=iso_path)

        _check_iso9660_filename(name, self.interchange_level)

        if file_mode is not None:
            if not self.rock_ridge:
                raise pycdlibexception.PyCdlibInvalidInput('Can only specify a file mode for Rock Ridge ISOs')
        else:
            if self.rock_ridge:
                # Python 3 implements the fileno method for all file-like objects, so
                # we can't just use the existence of the method to tell whether it is
                # available.  Instead, we try to assign it, and if we fail, then we
                # assume it is not available.
                try:
                    x_unused = fp.fileno()  # NOQA
                    file_mode = os.fstat(fp.fileno())
                except (AttributeError, io.UnsupportedOperation):
                    # We couldn't get the actual file mode of the file, so just assume
                    # a conservative 444
                    file_mode = 0o0100444

        left = length
        offset = 0
        done = False
        num_bytes_to_add = 0
        first_rec = None
        while not done:
            # The maximum length we allow in one directory record is 0xfffff800
            # (this is taken from xorriso, though I don't really know why).
            thislen = min(left, 0xfffff800)

            rec = dr.DirectoryRecord()
            rec.new_file(self.pvd, thislen, name, parent,
                         self.pvd.sequence_number(), self.rock_ridge, rr_name,
                         self.xa, file_mode)
            num_bytes_to_add += self._add_child_to_dr(rec,
                                                      self.pvd.logical_block_size())
            # El Torito Boot Catalogs have no inode, so only add it if this is
            # not a boot catalog.
            if eltorito_catalog and offset == 0:
                self.eltorito_boot_catalog.add_dirrecord(rec)
            else:
                # Zero-length files get a directory record but no Inode (there
                # is nothing to write out).
                ino = inode.Inode()
                ino.new(thislen, fp, manage_fp, offset)
                ino.linked_records.append(rec)
                rec.inode = ino
                self.inodes.append(ino)

            num_bytes_to_add += thislen
            if first_rec is None:
                first_rec = rec
            left -= thislen
            offset += thislen
            if left == 0:
                done = True

            num_bytes_to_add += self._update_rr_ce_entry(rec)

        if self.joliet_vd is not None and joliet_path is not None:
            # If this is a Joliet ISO, then we can re-use add_hard_link to do
            # most of the work.
            num_bytes_to_add += self._add_hard_link_to_rec(first_rec, eltorito_catalog,
                                                           joliet_new_path=joliet_path)

        if udf_path is not None:
            num_bytes_to_add += self._add_hard_link_to_rec(first_rec, eltorito_catalog,
                                                           udf_new_path=udf_path)

        return num_bytes_to_add

    def _rm_dr_link(self, rec):
        '''
        An internal method to remove a Directory Record link given the record.

        Parameters:
         rec - The Directory Record to remove.
        Returns:
         The number of bytes to remove from the ISO.
        '''
        if not rec.is_file():
            raise pycdlibexception.PyCdlibInvalidInput('Cannot remove a directory with rm_hard_link (try rm_directory instead)')

        num_bytes_to_remove = 0

        logical_block_size = rec.vd.logical_block_size()

        done = False
        while not done:
            num_bytes_to_remove += self._remove_child_from_dr(rec,
                                                              rec.index_in_parent,
                                                              logical_block_size)

            if rec.inode is not None:
                found_index = None
                for index, link in enumerate(rec.inode.linked_records):
                    if id(link) == id(rec):
                        found_index = index
                        break
                else:
                    # This should never happen
                    raise pycdlibexception.PyCdlibInternalError('Could not find inode corresponding to record')

                del rec.inode.linked_records[found_index]

                # We only remove the size of the child from the ISO if there are no
                # other references to this file on the ISO.
                if not rec.inode.linked_records:
                    found_index = None
                    for index, ino in enumerate(self.inodes):
                        if id(ino) == id(rec.inode):
                            found_index = index
                            break
                    else:
                        # This should never happen
                        raise pycdlibexception.PyCdlibInternalError('Could not find inode corresponding to record')
                    del self.inodes[found_index]

                    num_bytes_to_remove += rec.get_data_length()

            if rec.data_continuation is not None:
                rec = rec.data_continuation
            else:
                done = True

        return num_bytes_to_remove

    def _rm_udf_link(self, rec):
        '''
        An internal method to remove a UDF File Entry link.

        Parameters:
         rec - The UDF File Entry to remove.
        Returns:
         The number of bytes to remove from the ISO.
        '''
        if not rec.is_file() and not rec.is_symlink():
            raise pycdlibexception.PyCdlibInvalidInput('Cannot remove a directory with rm_hard_link (try rm_directory instead)')

        # To remove something from UDF, we have to:
        # 1.  Remove it from the list of linked_records on the Inode.
        # 2.  If the number of links to the Inode is now 0, remove the Inode.
        # 3.  If the number of links to the UDF File Entry this uses is 0,
        #     remove the UDF File Entry.
        # 4.  Remove the UDF File Identifier from the parent.

        logical_block_size = self.pvd.logical_block_size()

        num_bytes_to_remove = 0

        if rec.inode is not None:
            # Step 1.
            found_index = None
            for index, link in enumerate(rec.inode.linked_records):
                if id(link) == id(rec):
                    found_index = index
                    break
            else:
                # This should never happen
                raise pycdlibexception.PyCdlibInternalError('Could not find inode corresponding to record')

            del rec.inode.linked_records[found_index]
            rec.inode.num_udf -= 1

            # Step 2.
            if not rec.inode.linked_records:
                found_index = None
                for index, ino in enumerate(self.inodes):
                    if id(ino) == id(rec.inode):
                        found_index = index
                        break
                else:
                    # This should never happen
                    raise pycdlibexception.PyCdlibInternalError('Could not find inode corresponding to record')
                del self.inodes[found_index]

                num_bytes_to_remove += rec.get_data_length()

            # Step 3.
            if rec.inode.num_udf == 0:
                num_bytes_to_remove += logical_block_size
        else:
            # If rec.inode is None, then we are just removing the UDF File
            # Entry.
            num_bytes_to_remove += logical_block_size

        # Step 4.
        to_remove = rec.parent.remove_file_ident_desc_by_name(rec.file_ident.fi,
                                                              logical_block_size)
        num_bytes_to_remove += to_remove * logical_block_size
        self.udf_logical_volume_integrity.logical_volume_impl_use.num_files -= 1

        self._find_udf_record.cache_clear()  # pylint: disable=no-member

        return num_bytes_to_remove

    def _add_joliet_dir(self, joliet_path):
        '''
        An internal method to add a joliet directory to the ISO.

        Parameters:
         joliet_path - The path to add to the Joliet portion of the ISO.
        Returns:
         The number of additional bytes needed on the ISO to fit this directory.
        '''
        (joliet_name, joliet_parent) = self._name_and_parent_from_path(joliet_path=joliet_path)

        rec = dr.DirectoryRecord()
        rec.new_dir(self.joliet_vd, joliet_name, joliet_parent,
                    self.joliet_vd.sequence_number(), None, None,
                    self.joliet_vd.logical_block_size(), False, False,
                    False, None)
        num_bytes_to_add = self._add_child_to_dr(rec,
                                                 self.joliet_vd.logical_block_size())

        self._create_dot(self.joliet_vd, rec, None, False, None)
        self._create_dotdot(self.joliet_vd, rec, None, False, False, None)

        num_bytes_to_add += self.joliet_vd.logical_block_size()
        if self.joliet_vd.add_to_ptr_size(path_table_record.PathTableRecord.record_length(len(joliet_name))):
            num_bytes_to_add += 4 * self.joliet_vd.logical_block_size()

        # We always need to add an entry to the path table record
        ptr = path_table_record.PathTableRecord()
        ptr.new_dir(joliet_name)
        rec.set_ptr(ptr)

        return num_bytes_to_add

    def _rm_joliet_dir(self, joliet_path):
        '''
        An internal method to remove a directory from the Joliet portion of the ISO.

        Parameters:
         joliet_path - The Joliet directory to remove.
        Returns:
         The number of bytes to remove from the ISO for this Joliet directory.
        '''
        joliet_child = self._find_joliet_record(joliet_path)
        num_bytes_to_remove = joliet_child.get_data_length()
        num_bytes_to_remove += self._remove_child_from_dr(joliet_child,
                                                          joliet_child.index_in_parent,
                                                          self.joliet_vd.logical_block_size())
        if self.joliet_vd.remove_from_ptr_size(path_table_record.PathTableRecord.record_length(joliet_child.ptr.len_di)):
            num_bytes_to_remove += 4 * self.joliet_vd.logical_block_size()

        return num_bytes_to_remove

    def _get_entry(self, **kwargs):
        '''
        Internal method to get the directory record for a particular path.

        Parameters:
         iso_path - The path on the ISO filesystem to look up the record for.
         joliet_path - The path on the Joliet filesystem to look up the record
                       for.
         rr_path - The Rock Ridge path on the ISO filesystem to look up the
                   record for.
         udf_path - The path on the UDF filesystem to look up the record for.
        Returns:
         A dr.DirectoryRecord object representing the path.
        '''
        if self._needs_reshuffle:
            self._reshuffle_extents()

        if 'joliet_path' in kwargs:
            joliet_path = self._normalize_joliet_path(kwargs['joliet_path'])
            rec = self._find_joliet_record(joliet_path)
        elif 'udf_path' in kwargs:
            rec = self._find_udf_record(utils.normpath(kwargs['udf_path']))
        elif 'rr_path' in kwargs:
            rec = self._find_rr_record(utils.normpath(kwargs['rr_path']))
        else:
            rec = self._find_iso_record(utils.normpath(kwargs['iso_path']))

        return rec

    def _create_dot(self, vd, parent, rock_ridge, xa, file_mode):
        '''
        An internal method to create a new 'dot' Directory Record.

        Parameters:
         vd - The volume descriptor to attach the 'dot' Directory Record to.
         parent - The parent Directory Record for new Directory Record.
         rock_ridge - Whether this Directory Record should have Rock Ridge extensions.
         xa - Whether this Directory Record should have extended attributes.
         file_mode - The mode to assign to the dot directory (only applies to Rock Ridge).
        Returns:
         Nothing.
        '''
        dot = dr.DirectoryRecord()
        dot.new_dot(vd, parent, vd.sequence_number(), rock_ridge,
                    vd.logical_block_size(), xa, file_mode)
        self._add_child_to_dr(dot, vd.logical_block_size())

    def _create_dotdot(self, vd, parent, rock_ridge, relocated, xa, file_mode):
        '''
        An internal method to create a new 'dotdot' Directory Record.

        Parameters:
         vd - The volume descriptor to attach the 'dotdot' Directory Record to.
         parent - The parent Directory Record for new Directory Record.
         rock_ridge - Whether this Directory Record should have Rock Ridge extensions.
         relocated - Whether this Directory Record is a Rock Ridge relocated entry.
         xa - Whether this Directory Record should have extended attributes.
         file_mode - The mode to assign to the dot directory (only applies to Rock Ridge).
        Returns:
         Nothing.
        '''
        dotdot = dr.DirectoryRecord()
        dotdot.new_dotdot(vd, parent, vd.sequence_number(), rock_ridge,
                          vd.logical_block_size(), relocated, xa, file_mode)
        self._add_child_to_dr(dotdot, vd.logical_block_size())
        return dotdot


########################### PUBLIC API #####################################
    def __init__(self, always_consistent=False):
        self._always_consistent = always_consistent
        self._track_writes = os.getenv('PYCDLIB_TRACK_WRITES', False)
        self._initialize()

    def new(self, interchange_level=1, sys_ident='', vol_ident='', set_size=1,
            seqnum=1, log_block_size=2048, vol_set_ident=' ', pub_ident_str='',
            preparer_ident_str='', app_ident_str='', copyright_file='',
            abstract_file='', bibli_file='', vol_expire_date=None, app_use='',
            joliet=None, rock_ridge=None, xa=False, udf=None):
        '''
        Create a new ISO from scratch.

        Parameters:
         interchange_level - The ISO9660 interchange level to use; this dictates
                             the rules on the names of files.  Levels 1, 2, 3,
                             and 4 are supported.  Level 1 is the most
                             conservative, and is the default, but level 3 is
                             recommended.
         sys_ident - The system identification string to use on the new ISO.
         vol_ident - The volume identification string to use on the new ISO.
         set_size - The size of the set of ISOs this ISO is a part of.
         seqnum - The sequence number of the set of this ISO.
         log_block_size - The logical block size to use for the ISO.  While ISO9660
                          technically supports sizes other than 2048 (the default),
                          this almost certainly doesn't work.
         vol_set_ident - The volume set identification string to use on the new ISO.
         pub_ident_str - The publisher identification string to use on the new ISO.
         preparer_ident_str - The preparer identification string to use on the new ISO.
         app_ident_str - The application identification string to use on the new ISO.
         copyright_file - The name of a file at the root of the ISO to use as the
                          copyright file.
         abstract_file - The name of a file at the root of the ISO to use as the
                         abstract file.
         bibli_file - The name of a file at the root of the ISO to use as the
                      bibliographic file.
         vol_expire_date - The date that this ISO will expire at.
         app_use - Arbitrary data that the application can stuff into the primary
                   volume descriptor of this ISO.
         joliet - A integer that can have the value 1, 2, or 3 for Joliet
                  levels 1, 2, or 3 (3 is by far the most common), or None for
                  no Joliet support (the default).  For legacy reasons, this
                  parameter also accepts a boolean, where the value of 'False'
                  means no Joliet and a value of 'True' means level 3.
         rock_ridge - Whether to make this ISO have the Rock Ridge extensions or
                      not.  The default value of None does not add Rock Ridge
                      extensions.  A string value of '1.09', '1.10', or '1.12'
                      adds the specified Rock Ridge version to the ISO.  If
                      unsure, pass '1.09' to ensure maximum compatibility.
         xa - Whether to add the ISO9660 Extended Attribute extensions to this
              ISO.  The default is False.
         udf - Whether to add UDF support to this ISO.  If it is None (the
               default), no UDF support is added.  If it is "2.60", version
               2.60 of the UDF spec is used.  All other values are disallowed.
        Returns:
         Nothing.
        '''
        # Start out with argument checking.
        if self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object already has an ISO; either close it or create a new object')

        if interchange_level < 1 or interchange_level > 4:
            raise pycdlibexception.PyCdlibInvalidInput('Invalid interchange level (must be between 1 and 4)')

        if rock_ridge is not None and rock_ridge not in ['1.09', '1.10', '1.12']:
            raise pycdlibexception.PyCdlibInvalidInput('Rock Ridge value must be None (no Rock Ridge), 1.09, 1.10, or 1.12')

        if udf is not None and udf != '2.60':
            raise pycdlibexception.PyCdlibInvalidInput('UDF value must be None (no UDF), or 2.60')

        # Now save off the arguments we need to keep around.
        if not app_ident_str:
            app_ident_str = 'PyCdlib (C) 2015-2018 Chris Lalancette'

        self.interchange_level = interchange_level

        self.xa = xa

        if isinstance(joliet, bool):
            if joliet:
                joliet = 3
            else:
                joliet = None

        self.rock_ridge = rock_ridge

        sys_ident = sys_ident.encode('utf-8')
        vol_ident = vol_ident.encode('utf-8')
        vol_set_ident = vol_set_ident.encode('utf-8')
        pub_ident_str = pub_ident_str.encode('utf-8')
        preparer_ident_str = preparer_ident_str.encode('utf-8')
        app_ident_str = app_ident_str.encode('utf-8')
        copyright_file = copyright_file.encode('utf-8')
        abstract_file = abstract_file.encode('utf-8')
        bibli_file = bibli_file.encode('utf-8')
        app_use = app_use.encode('utf-8')

        # Now start creating the ISO.
        self.pvd = headervd.pvd_factory(sys_ident, vol_ident, set_size, seqnum,
                                        log_block_size, vol_set_ident,
                                        pub_ident_str, preparer_ident_str,
                                        app_ident_str, copyright_file,
                                        abstract_file, bibli_file,
                                        vol_expire_date, app_use, xa)
        self.pvds.append(self.pvd)

        pvd_log_block_size = self.pvd.logical_block_size()

        num_bytes_to_add = 0
        if self.interchange_level == 4:
            self.enhanced_vd = headervd.enhanced_vd_factory(sys_ident,
                                                            vol_ident,
                                                            set_size, seqnum,
                                                            log_block_size,
                                                            vol_set_ident,
                                                            pub_ident_str,
                                                            preparer_ident_str,
                                                            app_ident_str,
                                                            copyright_file,
                                                            abstract_file,
                                                            bibli_file,
                                                            vol_expire_date,
                                                            app_use, xa)
            self.svds.append(self.enhanced_vd)

            num_bytes_to_add += self.enhanced_vd.logical_block_size()

        if joliet is not None:
            self.joliet_vd = headervd.joliet_vd_factory(joliet, sys_ident,
                                                        vol_ident, set_size,
                                                        seqnum, log_block_size,
                                                        vol_set_ident,
                                                        pub_ident_str,
                                                        preparer_ident_str,
                                                        app_ident_str,
                                                        copyright_file,
                                                        abstract_file,
                                                        bibli_file,
                                                        vol_expire_date,
                                                        app_use, xa)
            self.svds.append(self.joliet_vd)

            # Now that we have added joliet, we need to add the new space to the
            # PVD for the VD itself.
            num_bytes_to_add += self.joliet_vd.logical_block_size()

        self.vdsts.append(headervd.vdst_factory())
        num_bytes_to_add += pvd_log_block_size

        if udf is not None:
            # Create the Bridge Recognition Volume Sequence
            self.udf_bea = udfmod.BEAVolumeStructure()
            self.udf_bea.new()

            self.udf_nsr = udfmod.NSRVolumeStructure()
            self.udf_nsr.new()

            self.udf_tea = udfmod.TEAVolumeStructure()
            self.udf_tea.new()

            num_bytes_to_add += 3 * pvd_log_block_size

        # We always create an empty version volume descriptor
        self.version_vd = headervd.version_vd_factory(pvd_log_block_size)
        num_bytes_to_add += pvd_log_block_size

        if udf is not None:
            self.udf_main_descs = self.UDFDescriptors()

            # We need to pad out to extent 32.  The padding should be the
            # distance between the current PVD space size and 32.
            additional_extents = 32 - (self.pvd.space_size + (num_bytes_to_add // pvd_log_block_size))
            num_bytes_to_add += additional_extents * pvd_log_block_size

            # Create the Main Volume Descriptor Sequence
            self.udf_main_descs.pvd = udfmod.UDFPrimaryVolumeDescriptor()
            self.udf_main_descs.pvd.new()

            self.udf_main_descs.impl_use = udfmod.UDFImplementationUseVolumeDescriptor()
            self.udf_main_descs.impl_use.new()

            self.udf_main_descs.partition = udfmod.UDFPartitionVolumeDescriptor()
            self.udf_main_descs.partition.new()

            self.udf_main_descs.logical_volume = udfmod.UDFLogicalVolumeDescriptor()
            self.udf_main_descs.logical_volume.new()

            self.udf_main_descs.unallocated_space = udfmod.UDFUnallocatedSpaceDescriptor()
            self.udf_main_descs.unallocated_space.new()

            self.udf_main_descs.terminator = udfmod.UDFTerminatingDescriptor()
            self.udf_main_descs.terminator.new()

            num_bytes_to_add += 16 * pvd_log_block_size

            self.udf_reserve_descs = self.UDFDescriptors()

            # Create the Reserve Volume Descriptor Sequence
            self.udf_reserve_descs.pvd = udfmod.UDFPrimaryVolumeDescriptor()
            self.udf_reserve_descs.pvd.new()

            self.udf_reserve_descs.impl_use = udfmod.UDFImplementationUseVolumeDescriptor()
            self.udf_reserve_descs.impl_use.new()

            self.udf_reserve_descs.partition = udfmod.UDFPartitionVolumeDescriptor()
            self.udf_reserve_descs.partition.new()

            self.udf_reserve_descs.logical_volume = udfmod.UDFLogicalVolumeDescriptor()
            self.udf_reserve_descs.logical_volume.new()

            self.udf_reserve_descs.unallocated_space = udfmod.UDFUnallocatedSpaceDescriptor()
            self.udf_reserve_descs.unallocated_space.new()

            self.udf_reserve_descs.terminator = udfmod.UDFTerminatingDescriptor()
            self.udf_reserve_descs.terminator.new()

            num_bytes_to_add += 16 * pvd_log_block_size

            # Create the Logical Volume Integrity Sequence
            self.udf_logical_volume_integrity = udfmod.UDFLogicalVolumeIntegrityDescriptor()
            self.udf_logical_volume_integrity.new()

            self.udf_logical_volume_integrity_terminator = udfmod.UDFTerminatingDescriptor()
            self.udf_logical_volume_integrity_terminator.new()

            num_bytes_to_add += 192 * pvd_log_block_size

            # Create the Anchor
            anchor1 = udfmod.UDFAnchorVolumeStructure()
            anchor1.new()
            self.udf_anchors.append(anchor1)

            num_bytes_to_add += pvd_log_block_size

            # Create the File Set
            self.udf_file_set = udfmod.UDFFileSetDescriptor()
            self.udf_file_set.new()

            self.udf_file_set_terminator = udfmod.UDFTerminatingDescriptor()
            self.udf_file_set_terminator.new()

            num_bytes_to_add += 2 * pvd_log_block_size

            # Create the root directory, and the 'parent' entry inside.
            self.udf_root = udfmod.UDFFileEntry()
            self.udf_root.new(0, 'dir', None, pvd_log_block_size)
            num_bytes_to_add += pvd_log_block_size

            parent = udfmod.UDFFileIdentifierDescriptor()
            parent.new(True, True, b'')
            num_new_extents = self.udf_root.add_file_ident_desc(parent, pvd_log_block_size)
            num_bytes_to_add += num_new_extents * pvd_log_block_size

        num_partition_bytes_to_add = 0
        # Create the PTR, and add the 4 extents that comprise of the LE PTR and
        # BE PTR to the number of bytes to add.
        ptr = path_table_record.PathTableRecord()
        ptr.new_root()
        self.pvd.root_directory_record().set_ptr(ptr)
        num_partition_bytes_to_add += 4 * pvd_log_block_size

        # Also add one extent to the size for the root directory record.
        num_partition_bytes_to_add += pvd_log_block_size

        self._create_dot(self.pvd, self.pvd.root_directory_record(),
                         self.rock_ridge, self.xa, 0o040555)
        self._create_dotdot(self.pvd, self.pvd.root_directory_record(),
                            self.rock_ridge, False, self.xa, 0o040555)

        if self.joliet_vd is not None:
            # Create the PTR, and add the 4 extents that comprise of the LE PTR and
            # BE PTR to the number of bytes to add.
            ptr = path_table_record.PathTableRecord()
            ptr.new_root()
            self.joliet_vd.root_directory_record().set_ptr(ptr)
            num_partition_bytes_to_add += 4 * pvd_log_block_size

            # Also add one extent to the size for the root directory record.
            num_partition_bytes_to_add += pvd_log_block_size

            self._create_dot(self.joliet_vd,
                             self.joliet_vd.root_directory_record(), None,
                             False, None)
            self._create_dotdot(self.joliet_vd,
                                self.joliet_vd.root_directory_record(), None,
                                False, False, None)

        if self.rock_ridge is not None:
            num_partition_bytes_to_add += pvd_log_block_size

        if udf is not None:
            anchor2 = udfmod.UDFAnchorVolumeStructure()
            anchor2.new()
            self.udf_anchors.append(anchor2)

            num_partition_bytes_to_add += pvd_log_block_size

        self._finish_add(num_bytes_to_add, num_partition_bytes_to_add)

        self._initialized = True

    def open(self, filename):
        '''
        Open up an existing ISO for inspection and modification.

        Parameters:
         filename - The filename containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object already has an ISO; either close it or create a new object')

        fp = open(filename, 'r+b')
        self._managing_fp = True
        try:
            self._open_fp(fp)
        except:
            fp.close()
            raise

    def open_fp(self, fp):
        '''
        Open up an existing ISO for inspection and modification.  Note that the
        file object passed in here must stay open for the lifetime of this
        object, as the PyCdlib class uses it internally to do writing and reading
        operations.  If you want PyCdlib to manage this for you, use 'open'
        instead.

        Parameters:
         fp - The file object containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object already has an ISO; either close it or create a new object')

        self._open_fp(fp)

    def get_file_from_iso(self, local_path, **kwargs):
        '''
        A method to fetch a single file from the ISO and write it out
        to a local file.

        Parameters:
         local_path - The local file to write to.
         blocksize - The number of bytes in each transfer.
         iso_path - The absolute ISO9660 path to lookup on the ISO (exclusive
                    with rr_path and joliet_path).
         rr_path - The absolute Rock Ridge path to lookup on the ISO (exclusive
                   with iso_path and joliet_path).
         joliet_path - The absolute Joliet path to lookup on the ISO (exclusive
                       with iso_path and rr_path).
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        with open(local_path, 'wb') as fp:
            self._get_file_from_iso_fp(fp, **kwargs)

    def get_file_from_iso_fp(self, outfp, **kwargs):
        '''
        A method to fetch a single file from the ISO and write it out
        to the file object.

        Parameters:
         outfp - The file object to write data to.
         blocksize - The number of bytes in each transfer.
         iso_path - The absolute ISO9660 path to lookup on the ISO (exclusive
                    with rr_path and joliet_path).
         rr_path - The absolute Rock Ridge path to lookup on the ISO (exclusive
                   with iso_path and joliet_path).
         joliet_path - The absolute Joliet path to lookup on the ISO (exclusive
                       with iso_path and rr_path).
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        self._get_file_from_iso_fp(outfp, **kwargs)

    def get_and_write(self, iso_path, local_path, blocksize=8192):
        '''
        (deprecated) Fetch a single file from the ISO and write it out to the
        specified file.  Note that this will overwrite the contents of the local
        file if it already exists.  Also note that 'iso_path' must be an
        absolute path to the file.  Finally, the 'iso_path' can be an ISO9660
        path, a Rock Ridge path, or a Joliet path.  In the case of ambiguity,
        the Joliet path is tried first, followed by the ISO9660 path, followed
        by the Rock Ridge path.  It is recommended to use the get_file_from_iso
        API instead to resolve this ambiguity.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         local_path - The local filename to write the contents to.
         blocksize - The blocksize to use when copying data; the default is 8192.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        with open(local_path, 'wb') as fp:
            self._get_and_write_fp(iso_path, fp, blocksize)

    def get_and_write_fp(self, iso_path, outfp, blocksize=8192):
        '''
        (deprecated) Fetch a single file from the ISO and write it out to the
        file object.  Note that 'iso_path' must be an absolute path to the file.
        Also note that the 'iso_path' can be an ISO9660 path, a Rock Ridge path,
        or a Joliet path.  In the case of ambiguity, the Joliet path is tried
        first, followed by the ISO9660 path, followed by the Rock Ridge path.
        It is recommend to use the get_file_from_iso_fp API instead to resolve
        this ambiguity.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         outfp - The file object to write data to.
         blocksize - The blocksize to use when copying data; the default is 8192.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        self._get_and_write_fp(iso_path, outfp, blocksize)

    def write(self, filename, blocksize=32768, progress_cb=None, progress_opaque=None):
        '''
        Write a properly formatted ISO out to the filename passed in.  This
        also goes by the name of 'mastering'.

        Parameters:
         filename - The filename to write the data to.
         blocksize - The blocksize to use when copying data; set to 32768 by default.
         progress_cb - If not None, a function to call as the write call does its
                       work.  The callback function must have a signature of:
                       def func(done, total, opaque).
         progress_opaque - User data to be passed to the progress callback.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        with open(filename, 'wb') as fp:
            self._write_fp(fp, blocksize, progress_cb, progress_opaque)

    def write_fp(self, outfp, blocksize=32768, progress_cb=None, progress_opaque=None):
        '''
        Write a properly formatted ISO out to the file object passed in.  This
        also goes by the name of 'mastering'.

        Parameters:
         outfp - The file object to write the data to.
         blocksize - The blocksize to use when copying data; set to 32768 by default.
         progress_cb - If not None, a function to call as the write call does its
                       work.  The callback function must have a signature of:
                       def func(done, total, opaque).
         progress_opaque - User data to be passed to the progress callback.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        self._write_fp(outfp, blocksize, progress_cb, progress_opaque)

    def add_fp(self, fp, length, iso_path, rr_name=None, joliet_path=None,
               file_mode=None, udf_path=None):
        '''
        Add a file to the ISO.  If the ISO is a Rock Ridge one, then a Rock
        Ridge name must also be provided.  If the ISO is a Joliet one, then a
        Joliet path may also be provided; while it is optional to do so, it is
        highly recommended.  Note that the caller must ensure that 'fp' remains
        open for the lifetime of the PyCdlib object, as the PyCdlib class uses
        the file descriptor internally when writing (mastering) the ISO.  If
        you want PyCdlib to manage this for you, use 'add_file' instead.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the data for the new file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
         file_mode - The POSIX file_mode to apply to this file.  This only
                     applies if this is a Rock Ridge ISO.  If this is None (the
                     default), the permissions from the original file are used.
         udf_path - The UDF name of the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if not utils.file_object_supports_binary(fp):
            raise pycdlibexception.PyCdlibInvalidInput('The fp argument must be in binary mode')

        num_bytes_to_add = self._add_fp(fp, length, False, iso_path, rr_name,
                                        joliet_path, udf_path, file_mode, False)

        self._finish_add(0, num_bytes_to_add)

    def add_file(self, filename, iso_path, rr_name=None, joliet_path=None,
                 file_mode=None, udf_path=None):
        '''
        Add a file to the ISO.  If the ISO is a Rock Ridge one, then a Rock
        Ridge name must also be provided.  If the ISO is a Joliet one, then a
        Joliet path may also be provided; while it is optional to do so, it is
        highly recommended.

        Parameters:
         filename - The filename to use for the data contents for the new file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
         file_mode - The POSIX file_mode to apply to this file.  This only
                     applies if this is a Rock Ridge ISO.  If this is None (the
                     default), the permissions from the original file are used.
         udf_path - The UDF name of the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        num_bytes_to_add = self._add_fp(filename, os.stat(filename).st_size,
                                        True, iso_path, rr_name, joliet_path,
                                        udf_path, file_mode, False)

        self._finish_add(0, num_bytes_to_add)

    def modify_file_in_place(self, fp, length, iso_path, rr_name=None,  # pylint: disable=unused-argument
                             joliet_path=None, udf_path=None):          # pylint: disable=unused-argument
        '''
        An API to modify a file in place on the ISO.  This can be extremely fast
        (much faster than calling the write method), but has many restrictions.

        1.  The original ISO file pointer must have been opened for reading
            and writing.
        2.  Only an existing *file* can be modified; directories cannot be
            changed.
        3.  Only an existing file can be *modified*; no new files can be added
            or removed.
        4.  The new file contents must use the same number of extents (typically
            2048 bytes) as the old file contents.  If using this API to shrink
            a file, this is usually easy since the new contents can be padded
            out with zeros or newlines to meet the requirement.  If using this
            API to grow a file, the new contents can only grow up to the next
            extent boundary.

        Unlike all other APIs in PyCdlib, this API actually modifies the
        originally opened on-disk file, so use it with caution.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the new data for the file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
         udf_path - The UDF absolute path to the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if hasattr(self._cdfp, 'mode') and not self._cdfp.mode.startswith(('r+', 'w', 'a', 'rb+')):
            raise pycdlibexception.PyCdlibInvalidInput('To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a)')

        log_block_size = self.pvd.logical_block_size()

        iso_path = utils.normpath(iso_path)

        child = self._find_iso_record(iso_path)

        old_num_extents = utils.ceiling_div(child.get_data_length(), log_block_size)
        new_num_extents = utils.ceiling_div(length, log_block_size)

        if old_num_extents != new_num_extents:
            raise pycdlibexception.PyCdlibInvalidInput('When modifying a file in-place, the number of extents for a file cannot change!')

        if not child.is_file():
            raise pycdlibexception.PyCdlibInvalidInput('Cannot modify a directory with modify_file_in_place')

        child.inode.update_fp(fp, length)

        # Remove the old size from the PVD size
        for pvd in self.pvds:
            pvd.remove_from_space_size(child.get_data_length())
        # And add the new size to the PVD size
        for pvd in self.pvds:
            pvd.add_to_space_size(length)

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        # If we made it here, we have successfully updated all of the in-memory
        # metadata.  Now we can go and modify the on-disk file.

        self._cdfp.seek(self.pvd.extent_location() * log_block_size)

        # First write out the PVD.
        rec = self.pvd.record()
        self._cdfp.write(rec)

        # Write out the joliet VD
        if self.joliet_vd is not None:
            self._cdfp.seek(self.joliet_vd.extent_location() * log_block_size)
            rec = self.joliet_vd.record()
            self._cdfp.write(rec)

        # Write out the enhanced VD
        if self.enhanced_vd is not None:
            self._cdfp.seek(self.enhanced_vd.extent_location() * log_block_size)
            rec = self.enhanced_vd.record()
            self._cdfp.write(rec)

        # We don't have to write anything out for UDF since it only tracks
        # extents, and we know we aren't changing the number of extents.

        # Write out the actual file contents
        self._cdfp.seek(child.extent_location() * log_block_size)
        with inode.InodeOpenData(child.inode, log_block_size) as (data_fp, data_len):
            utils.copy_data(data_len, log_block_size, data_fp, self._cdfp)
            utils.zero_pad(self._cdfp, data_len, log_block_size)

        # Finally write out the directory record entry.
        # This is a little tricky because of what things mean.  First of all,
        # child.extents_to_here represents the total number of extents up to
        # this child in the parent.  Thus, to get the absolute extent offset,
        # we start with the parent's extent location, add on the number of
        # extents to here, and remove 1 (since our offset will be zero-based).
        # Second, child.offset_to_here is the *last* byte that the child uses,
        # so to get the start of it we subtract off the length of the child.
        # Then we can multiple the extent location by the logical block size,
        # add on the offset, and get to the absolute location in the file.
        first_joliet = True
        for rec in child.inode.linked_records:
            if isinstance(rec, dr.DirectoryRecord):
                if id(rec.vd) == id(self.joliet_vd) and first_joliet:
                    first_joliet = False
                    self.joliet_vd.remove_from_space_size(rec.get_data_length())
                    self.joliet_vd.add_to_space_size(length)
                abs_extent_loc = rec.parent.extent_location() + rec.extents_to_here - 1
                offset = rec.offset_to_here - rec.dr_len
                abs_offset = abs_extent_loc * log_block_size + offset
            elif isinstance(rec, udfmod.UDFFileEntry):
                abs_offset = rec.extent_location() * log_block_size

            rec.set_data_length(length)
            self._cdfp.seek(abs_offset)
            self._cdfp.write(rec.record())

    def add_hard_link(self, **kwargs):
        '''
        Add a hard link to the ISO.  Hard links are alternate names for the
        same file contents that don't take up any additional space on the the
        ISO.  This API can be used to create hard links between two files on
        the ISO9660 filesystem, between two files on the Joliet filesystem, or
        between a file on the ISO9660 filesystem and the Joliet filesystem.
        In all cases, exactly one old path must be specified, and exactly one
        new path must be specified.
        Note that this is an advanced API, so using it in combination with the
        higher-level APIs (like rm_file) may result in unexpected behavior.
        Once this API has been used, this API and rm_hard_link() should be
        preferred over add_file() and rm_file(), respectively.

        Parameters:
         iso_old_path - The old path on the ISO9660 filesystem to link from.
         iso_new_path - The new path on the ISO9660 filesystem to link to.
         joliet_old_path - The old path on the Joliet filesystem to link from.
         joliet_new_path - The new path on the Joliet filesystem to link to.
         rr_name - The Rock Ridge name to use for the new file if this is a Rock
                   Ridge ISO and the new path is on the ISO9660 filesystem.
         boot_catalog_old - Use the El Torito boot catalog as the old path.
         udf_old_path - The old path on the UDF filesystem to link from.
         udf_new_path - The new path on the UDF filesystem to link to.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        num_old = 0
        iso_old_path = None
        joliet_old_path = None
        boot_catalog_old = False
        udf_old_path = None
        keys_to_remove = []
        for key in kwargs:
            if key == 'iso_old_path' and kwargs[key] is not None:
                num_old += 1
                iso_old_path = utils.normpath(kwargs[key])
                keys_to_remove.append(key)
            elif key == 'joliet_old_path' and kwargs[key] is not None:
                num_old += 1
                joliet_old_path = self._normalize_joliet_path(kwargs[key])
                keys_to_remove.append(key)
            elif key == 'boot_catalog_old' and kwargs[key] is not None:
                num_old += 1
                boot_catalog_old = True
                if self.eltorito_boot_catalog is None:
                    raise pycdlibexception.PyCdlibInvalidInput('Attempting to make link to non-existent El Torito boot catalog')
                keys_to_remove.append(key)
            elif key == 'udf_old_path' and kwargs[key] is not None:
                num_old += 1
                udf_old_path = utils.normpath(kwargs[key])
                keys_to_remove.append(key)

        if num_old != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Exactly one old path must be specified')

        # Once we've iterated over the keys we know about, remove them from
        # the map so that _add_hard_link_to_rec() can parse the rest.
        for key in keys_to_remove:
            del kwargs[key]

        # It would be nice to allow the addition of a link to the El Torito
        # Initial/Default Entry.  Unfortunately, the information we need for
        # a 'hidden' Initial entry just doesn't exist on the ISO.  In
        # particular, we don't know the real size that the file should be, we
        # only know the number of emulated sectors (512 bytes) that it will be
        # loaded into.  Since the true length and the number of sectors are not
        # the same thing, we can't actually add a hard link.

        if iso_old_path is not None:
            # A link from a file on the ISO9660 filesystem...
            old_rec = self._find_iso_record(iso_old_path)
        elif joliet_old_path is not None:
            # A link from a file on the Joliet filesystem...
            old_rec = self._find_joliet_record(joliet_old_path)
        elif boot_catalog_old:
            # A link from the El Torito boot catalog...
            old_rec = self.eltorito_boot_catalog.dirrecords[0]
        elif udf_old_path is not None:
            # A link from a file on the UDF filesystem...
            old_rec = self._find_udf_record(udf_old_path)

        # Above we checked to make sure we got at least one old path, so we
        # don't need to worry about the else situation here.

        num_bytes_to_add = self._add_hard_link_to_rec(old_rec, boot_catalog_old,
                                                      **kwargs)

        self._finish_add(0, num_bytes_to_add)

    def rm_hard_link(self, iso_path=None, joliet_path=None, udf_path=None):
        '''
        Remove a hard link from the ISO.  If the number of links to a piece of
        data drops to zero, then the contents will be removed from the ISO.
        Thus, this can be thought of as a lower-level interface to rm_file.
        Either an ISO9660 path or a Joliet path must be passed to this API, but
        not both.  Thus, this interface can be used to hide files from either
        the ISO9660 filesystem, the Joliet filesystem, or both (if there is
        another reference to the data on the ISO, such as in El Torito).
        Note that this is an advanced API, so using it in combination with the
        higher-level APIs (like rm_file) may result in unexpected behavior.
        Once this API has been used, this API and add_hard_link() should be
        preferred over rm_file() and add_file(), respectively.

        Parameters:
         iso_path - The ISO link path to remove.
         joliet_path - The Joliet link path to remove.
         udf_path - The UDF link path to remove.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if len([x for x in (iso_path, joliet_path, udf_path) if x is not None]) != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Must provide exactly one of iso_path, joliet_path, or udf_path')

        num_bytes_to_remove = 0

        if iso_path is not None:
            rec = self._find_iso_record(utils.normpath(iso_path))
            num_bytes_to_remove += self._rm_dr_link(rec)
        elif joliet_path is not None:
            if self.joliet_vd is None:
                raise pycdlibexception.PyCdlibInvalidInput('Cannot remove Joliet link from non-Joliet ISO')
            joliet_path = self._normalize_joliet_path(joliet_path)
            rec = self._find_joliet_record(joliet_path)
            num_bytes_to_remove += self._rm_dr_link(rec)
        else:
            # UDF hard link removal
            if self.udf_root is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only specify a udf_path for a UDF ISO')

            rec = self._find_udf_record(utils.normpath(udf_path))
            num_bytes_to_remove += self._rm_udf_link(rec)

        self._finish_remove(num_bytes_to_remove, True)

    def add_directory(self, iso_path=None, rr_name=None, joliet_path=None,
                      file_mode=None, udf_path=None):
        '''
        Add a directory to the ISO.  Either an iso_path or a joliet_path (or
        both) must be provided.  Providing joliet_path on a non-Joliet ISO is
        an error.  If the ISO contains Rock Ridge, then a Rock Ridge name must
        be provided.

        Parameters:
         iso_path - The ISO9660 absolute path to use for the directory.
         rr_name - The Rock Ridge name to use for the directory.
         joliet_path - The Joliet absolute path to use for the directory.
         file_mode - The POSIX file mode to use for the directory.  This only
                     applies for Rock Ridge ISOs.
         udf_path - The UDF absolute path to use for the directory.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if iso_path is None and joliet_path is None and udf_path is None:
            raise pycdlibexception.PyCdlibInvalidInput('Either iso_path or joliet_path must be passed')

        if file_mode is not None and not self.rock_ridge:
            raise pycdlibexception.PyCdlibInvalidInput('A file mode can only be specified for Rock Ridge ISOs')

        # For backwards-compatibility reasons, if the mode was not specified we
        # just assume 555.  We should probably eventually make file_mode
        # required for Rock Ridge and remove this assumption.
        if file_mode is None:
            file_mode = 0o040555

        num_bytes_to_add = 0
        if iso_path is not None:
            iso_path = utils.normpath(iso_path)

            rr_name = self._check_rr_name(rr_name)

            depth = len(utils.split_path(iso_path))

            if self.rock_ridge is None and self.enhanced_vd is None:
                _check_path_depth(iso_path)
            (name, parent) = self._name_and_parent_from_path(iso_path=iso_path)

            _check_iso9660_directory(name, self.interchange_level)

            relocated = False
            fake_dir_rec = None
            orig_parent = None
            iso9660_name = name
            if self.rock_ridge is not None and (depth % 8) == 0 and self.enhanced_vd is None:
                # If the depth was a multiple of 8, then we are going to have to
                # make a relocated entry for this record.

                rr_moved, add = self._find_or_create_rr_moved()
                num_bytes_to_add += add

                # With a depth of 8, we have to add the directory both to the
                # original parent with a CL link, and to the new parent with an
                # RE link.  Here we make the 'fake' record, as a child of the
                # original place; the real one will be done below.
                fake_dir_rec = dr.DirectoryRecord()
                fake_dir_rec.new_dir(self.pvd, name, parent,
                                     self.pvd.sequence_number(),
                                     self.rock_ridge, rr_name,
                                     self.pvd.logical_block_size(), True, False,
                                     self.xa, file_mode)
                num_bytes_to_add += self._add_child_to_dr(fake_dir_rec,
                                                          self.pvd.logical_block_size())

                # The fake dir record doesn't get an entry in the path table record.

                relocated = True
                orig_parent = parent
                parent = rr_moved

                # Since we are moving the entry underneath the RR_MOVED
                # directory, there is now the chance of a name collision (this
                # can't happen without relocation since _add_child_to_dr() below
                # won't allow duplicate names).  Check for that here and
                # generate a new name.
                index = 0
                while True:
                    for child in rr_moved.children:
                        if child.file_ident == iso9660_name:
                            # Python 3.4 doesn't support substitution with a byte
                            # array, so we do it as a string and encode to bytes.
                            iso9660_name = name + ('%03d' % (index)).encode()
                            index += 1
                            break
                    else:
                        break

            rec = dr.DirectoryRecord()
            rec.new_dir(self.pvd, iso9660_name, parent,
                        self.pvd.sequence_number(), self.rock_ridge, rr_name,
                        self.pvd.logical_block_size(), False, relocated,
                        self.xa, file_mode)
            num_bytes_to_add += self._add_child_to_dr(rec, self.pvd.logical_block_size())
            if rec.rock_ridge is not None:
                if relocated:
                    fake_dir_rec.rock_ridge.cl_to_moved_dr = rec
                    rec.rock_ridge.moved_to_cl_dr = fake_dir_rec
                num_bytes_to_add += self._update_rr_ce_entry(rec)

            self._create_dot(self.pvd, rec, self.rock_ridge, self.xa, file_mode)

            parent_file_mode = None
            if parent.rock_ridge is not None:
                parent_file_mode = parent.rock_ridge.get_file_mode()
            else:
                if parent.is_root:
                    parent_file_mode = file_mode

            dotdot = self._create_dotdot(self.pvd, rec, self.rock_ridge,
                                         relocated, self.xa, parent_file_mode)
            if dotdot.rock_ridge is not None and relocated:
                dotdot.rock_ridge.parent_link = orig_parent

            # We always need to add an entry to the path table record
            ptr = path_table_record.PathTableRecord()
            ptr.new_dir(iso9660_name)

            num_bytes_to_add += self._add_to_ptr_size(ptr) + self.pvd.logical_block_size()

            rec.set_ptr(ptr)

        if joliet_path is not None:
            num_bytes_to_add += self._add_joliet_dir(self._normalize_joliet_path(joliet_path))

        if udf_path is not None:
            if self.udf_root is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only specify a udf_path for a UDF ISO')

            log_block_size = self.pvd.logical_block_size()

            udf_path = utils.normpath(udf_path)
            (name, parent) = self._name_and_parent_from_path(udf_path=udf_path)

            file_ident = udfmod.UDFFileIdentifierDescriptor()
            file_ident.new(True, False, name)
            num_new_extents = parent.add_file_ident_desc(file_ident, log_block_size)
            num_bytes_to_add += num_new_extents * log_block_size

            file_entry = udfmod.UDFFileEntry()
            file_entry.new(0, 'dir', parent, log_block_size)
            file_ident.file_entry = file_entry
            file_entry.file_ident = file_ident
            num_bytes_to_add += log_block_size

            dotdot = udfmod.UDFFileIdentifierDescriptor()
            dotdot.new(True, True, b'')
            num_new_extents = file_ident.file_entry.add_file_ident_desc(dotdot, log_block_size)
            num_bytes_to_add += num_new_extents * log_block_size

            self.udf_logical_volume_integrity.logical_volume_impl_use.num_dirs += 1

        self._finish_add(0, num_bytes_to_add)

    def add_joliet_directory(self, joliet_path):
        '''
        (deprecated) Add a directory to the Joliet portion of the ISO.  Since
        Joliet occupies a completely different namespace than ISO9660, this
        method can be invoked to create a completely different directory
        structure in the Joliet namespace, though that is generally not advised.
        It is recommended to use the 'joliet_path' argument of the
        'add_directory' instead of this method.

        Parameters:
         joliet_path - The Joliet directory to create.
        Returns:
         Nothing.
        '''
        self.add_directory(joliet_path=joliet_path)

    def rm_file(self, iso_path, rr_name=None, joliet_path=None, udf_path=None):  # pylint: disable=unused-argument
        '''
        Remove a file from the ISO.

        Parameters:
         iso_path - The path to the file to remove.
         rr_name - The Rock Ridge name of the file to remove.
         joliet_path - The Joliet path to the file to remove.
         udf_path - The UDF path to the file to remove.
        Returns:
         Nothing.
        '''

        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        iso_path = utils.normpath(iso_path)

        if not utils.starts_with_slash(iso_path):
            raise pycdlibexception.PyCdlibInvalidInput('Must be a path starting with /')

        child = self._find_iso_record(iso_path)

        if not child.is_file():
            raise pycdlibexception.PyCdlibInvalidInput('Cannot remove a directory with rm_file (try rm_directory instead)')

        # We also want to check to see if this Directory Record is currently
        # being used as an El Torito Boot Catalog, Initial Entry, or Section
        # Entry.  If it is, we throw an exception; we don't know if the user
        # meant to remove El Torito from this ISO, or if they meant to 'hide'
        # the entry, but we need them to call the correct API to let us know.
        if self.eltorito_boot_catalog is not None:
            if any([id(child) == id(rec) for rec in self.eltorito_boot_catalog.dirrecords]):
                raise pycdlibexception.PyCdlibInvalidInput("Cannot remove a file that is referenced by El Torito; either use 'rm_eltorito' to remove El Torito first, or use 'rm_hard_link' to hide the entry")

            eltorito_entries = {}
            eltorito_entries[id(self.eltorito_boot_catalog.initial_entry.inode)] = True
            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    eltorito_entries[id(entry.inode)] = True

            if id(child.inode) in eltorito_entries:
                raise pycdlibexception.PyCdlibInvalidInput("Cannot remove a file that is referenced by El Torito; either use 'rm_eltorito' to remove El Torito first, or use 'rm_hard_link' to hide the entry")

        num_bytes_to_remove = 0

        # If the child is a Rock Ridge symlink, then it has no inodes since
        # there is no data attached to it.
        if child.inode is None:
            num_bytes_to_remove += self._remove_child_from_dr(child,
                                                              child.index_in_parent,
                                                              self.pvd.logical_block_size())
        else:
            while child.inode.linked_records:
                rec = child.inode.linked_records[0]

                if isinstance(rec, dr.DirectoryRecord):
                    num_bytes_to_remove += self._rm_dr_link(rec)
                elif isinstance(rec, udfmod.UDFFileEntry):
                    num_bytes_to_remove += self._rm_udf_link(rec)
                else:
                    # This should never happen
                    raise pycdlibexception.PyCdlibInternalError('Saw a linked record that was neither ISO or UDF')

        self._finish_remove(num_bytes_to_remove, True)

    def rm_directory(self, iso_path=None, rr_name=None, joliet_path=None, udf_path=None):
        '''
        Remove a directory from the ISO.

        Parameters:
         iso_path - The path to the directory to remove.
         rr_name - The Rock Ridge name of the directory to remove.
         joliet_path - The Joliet path to the directory to remove.
         udf_path - The UDF absolute path to the directory to remove.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if iso_path is None and joliet_path is None and udf_path is None:
            raise pycdlibexception.PyCdlibInvalidInput('Either iso_path or joliet_path must be passed')

        num_bytes_to_remove = 0

        if iso_path is not None:
            iso_path = utils.normpath(iso_path)

            if iso_path == b'/':
                raise pycdlibexception.PyCdlibInvalidInput('Cannot remove base directory')

            rr_name = self._check_rr_name(rr_name)

            child = self._find_iso_record(iso_path)

            if not child.is_dir():
                raise pycdlibexception.PyCdlibInvalidInput('Cannot remove a file with rm_directory (try rm_file instead)')

            if len(child.children) > 2:
                raise pycdlibexception.PyCdlibInvalidInput('Directory must be empty to use rm_directory')

            num_bytes_to_remove += self._remove_child_from_dr(child,
                                                              child.index_in_parent,
                                                              self.pvd.logical_block_size())

            num_bytes_to_remove += self._remove_from_ptr_size(child.ptr)

            # Remove space for the directory itself.
            num_bytes_to_remove += child.get_data_length()

            if child.rock_ridge is not None and child.rock_ridge.relocated_record():
                # OK, this child was relocated.  If the parent of this relocated
                # record is empty (only . and ..), we can remove it.
                parent = child.parent
                if len(parent.children) == 2:
                    for index, c in enumerate(parent.parent.children):
                        if c.file_ident == parent.file_ident:
                            parent_index = index
                            break
                    else:
                        raise pycdlibexception.PyCdlibInvalidISO('Could not find parent in its own parent!')

                    num_bytes_to_remove += self._remove_child_from_dr(parent,
                                                                      parent_index,
                                                                      self.pvd.logical_block_size())
                    num_bytes_to_remove += parent.get_data_length()
                    num_bytes_to_remove += self._remove_from_ptr_size(parent.ptr)

                cl = child.rock_ridge.moved_to_cl_dr
                for index, c in enumerate(cl.parent.children):
                    if cl.file_ident == c.file_ident:
                        clindex = index
                        break
                else:
                    raise pycdlibexception.PyCdlibInvalidISO('CL record does not exist')

                if cl.children:
                    raise pycdlibexception.PyCdlibInvalidISO('Parent link should have no children!')
                num_bytes_to_remove += self._remove_child_from_dr(cl, clindex,
                                                                  self.pvd.logical_block_size())
                # Note that we do not remove additional space from the PVD for the child_link
                # record because it is a 'fake' record that has no real size.

            if child.rock_ridge is not None and child.rock_ridge.dr_entries.ce_record is not None:
                child.rock_ridge.ce_block.remove_entry(child.rock_ridge.dr_entries.ce_record.offset_cont_area,
                                                       child.rock_ridge.dr_entries.ce_record.len_cont_area)

        if joliet_path is not None:
            num_bytes_to_remove += self._rm_joliet_dir(self._normalize_joliet_path(joliet_path))

        if udf_path is not None:
            if self.udf_root is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only specify a udf_path for a UDF ISO')

            udf_path = utils.normpath(udf_path)

            if udf_path == b'/':
                raise pycdlibexception.PyCdlibInvalidInput('Cannot remove base directory')

            (udf_name, udf_parent) = self._name_and_parent_from_path(udf_path=udf_path)

            to_remove = udf_parent.remove_file_ident_desc_by_name(udf_name, self.pvd.logical_block_size())
            # Remove space (if necessary) in the parent File Identifier
            # Descriptor area.
            num_bytes_to_remove += to_remove * self.pvd.logical_block_size()
            # Remove space for the File Entry.
            num_bytes_to_remove += self.pvd.logical_block_size()
            # Remove space for the list of File Identifier Descriptors.
            num_bytes_to_remove += self.pvd.logical_block_size()

            self.udf_logical_volume_integrity.logical_volume_impl_use.num_dirs -= 1

            self._find_udf_record.cache_clear()  # pylint: disable=no-member

        self._finish_remove(num_bytes_to_remove, True)

    def rm_joliet_directory(self, joliet_path):
        '''
        (deprecated) Remove a Joliet directory from the ISO.  It is recommended
        to use the 'joliet_path' parameter to 'rm_directory' instead.

        Parameters:
         joliet_path - The Joliet path to the directory to remove.
        Returns:
         Nothing.
        '''
        self.rm_directory(joliet_path=joliet_path)

    def add_eltorito(self, bootfile_path, bootcatfile=None,
                     rr_bootcatname=None, joliet_bootcatfile=None,
                     boot_load_size=None, platform_id=0, boot_info_table=False,
                     efi=False, media_name='noemul', bootable=True,
                     boot_load_seg=0, udf_bootcatfile=None):
        '''
        Add an El Torito Boot Record, and associated files, to the ISO.  The
        file that will be used as the bootfile must be passed into this function
        and must already be present on the ISO.

        Parameters:
         bootfile_path - The file to use as the boot file; it must already
                         exist on this ISO.
         bootcatfile - The fake file to use as the boot catalog entry; set to
                       BOOT.CAT;1 by default.
         rr_bootcatname - The Rock Ridge name for the fake file to use as the
                          boot catalog entry; set to 'boot.cat' by default.
         joliet_bootcatfile - The Joliet name for the fake file to use as the
                              boot catalog entry; set to 'boot.cat' by default.
         boot_load_size - The number of sectors to use for the boot entry; if
                          set to None (the default), the number of sectors will
                          be calculated.
         platform_id - The platform ID to set for the El Torito entry; 0 is for
                       x86, 1 is for Power PC, and 2 is for Mac.  0 is the
                       default.
         boot_info_table - Whether to add a boot info table to the ISO.  The
                           default is False.
         efi - Whether this is an EFI entry for El Torito.  The default is False.
         media_name - The name of the media type, one of 'noemul', 'floppy', or 'hdemul'.
         bootable - Whether the boot media is bootable.  The default is True.
         boot_load_seg - The load segment address of the boot image.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        # In order to add an El Torito boot, we need to do the following:
        # 1.  Find the boot file record (which must already exist).
        # 2.  Construct a BootRecord.
        # 3.  Construct a BootCatalog, and add it to the filesystem.
        # 4.  Add the boot record to the ISO.

        if bootcatfile is None:
            bootcatfile = '/BOOT.CAT;1'

        bootfile_path = utils.normpath(bootfile_path)
        bootcatfile = utils.normpath(bootcatfile)

        if self.joliet_vd is not None:
            if joliet_bootcatfile is None:
                joliet_bootcatfile = '/boot.cat'
        else:
            if joliet_bootcatfile is not None:
                raise pycdlibexception.PyCdlibInvalidInput('A joliet path must not be passed when adding El Torito to a non-Joliet ISO')

        if self.udf_root is not None:
            if udf_bootcatfile is None:
                udf_bootcatfile = '/boot.cat'
        else:
            if udf_bootcatfile is not None:
                raise pycdlibexception.PyCdlibInvalidInput('A UDF path must not be passed when adding El Torito to a non-UDF ISO')

        log_block_size = self.pvd.logical_block_size()

        # Step 1.
        boot_dirrecord = self._find_iso_record(bootfile_path)

        if boot_load_size is None:
            sector_count = utils.ceiling_div(boot_dirrecord.get_data_length(),
                                             log_block_size) * log_block_size // 512
        else:
            sector_count = boot_load_size

        if boot_info_table:
            orig_len = boot_dirrecord.get_data_length()
            bi_table = eltorito.EltoritoBootInfoTable()
            with inode.InodeOpenData(boot_dirrecord.inode, log_block_size) as (data_fp, data_len):
                bi_table.new(self.pvd, boot_dirrecord.inode, orig_len,
                             self._calculate_eltorito_boot_info_table_csum(data_fp, data_len))

            boot_dirrecord.inode.add_boot_info_table(bi_table)

        system_type = 0
        if media_name == 'hdemul':
            with inode.InodeOpenData(boot_dirrecord.inode, log_block_size) as (data_fp, data_len):
                disk_mbr = data_fp.read(512)
                if len(disk_mbr) != 512:
                    raise pycdlibexception.PyCdlibInvalidInput('Could not read entire HD MBR, must be at least 512 bytes')
                system_type = eltorito.hdmbrcheck(disk_mbr, sector_count, bootable)

        num_bytes_to_add = 0
        if self.eltorito_boot_catalog is not None:
            # All right, we already created the boot catalog.  Add a new section
            # to the boot catalog
            self.eltorito_boot_catalog.add_section(boot_dirrecord.inode,
                                                   sector_count, boot_load_seg,
                                                   media_name, system_type, efi,
                                                   bootable)
        else:
            # Step 2.
            br = headervd.BootRecord()
            br.new(b'EL TORITO SPECIFICATION')
            self.brs.append(br)
            # On a UDF ISO, adding a new Boot Record doesn't actually increase
            # the size, since there are a bunch of gaps at the beginning.
            if self.udf_main_descs is None:
                num_bytes_to_add += log_block_size

            # Step 3.
            self.eltorito_boot_catalog = eltorito.EltoritoBootCatalog(br)
            self.eltorito_boot_catalog.new(br, boot_dirrecord.inode, sector_count,
                                           boot_load_seg, media_name, system_type,
                                           platform_id, bootable)

            # Step 4.
            rrname = None
            if self.rock_ridge is not None:
                if rr_bootcatname is None:
                    rrname = 'boot.cat'
                else:
                    rrname = rr_bootcatname

            num_bytes_to_add += self._add_fp(None, log_block_size, False, bootcatfile,
                                             rrname, joliet_bootcatfile,
                                             udf_bootcatfile, None, True)

        self._finish_add(0, num_bytes_to_add)

    def rm_eltorito(self):
        '''
        Remove the El Torito boot record (and Boot Catalog) from the ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if self.eltorito_boot_catalog is None:
            raise pycdlibexception.PyCdlibInvalidInput('This ISO does not have an El Torito Boot Record')

        for brindex, br in enumerate(self.brs):
            if br.boot_system_identifier == b'EL TORITO SPECIFICATION'.ljust(32, b'\x00'):
                eltorito_index = brindex
                break
        else:
            # There was a boot catalog, but no corresponding boot record.  This
            # should never happen.
            raise pycdlibexception.PyCdlibInternalError('El Torito boot catalog found with no corresponding boot record')

        del self.brs[eltorito_index]

        num_bytes_to_remove = 0

        # On a UDF ISO, removing the Boot Record doesn't actually decrease
        # the size, since there are a bunch of gaps at the beginning.
        if self.udf_main_descs is None:
            num_bytes_to_remove += self.pvd.logical_block_size()

        # Remove all of the DirectoryRecord/UDFFileEntries associated with
        # the Boot Catalog
        for rec in self.eltorito_boot_catalog.dirrecords:
            if isinstance(rec, dr.DirectoryRecord):
                num_bytes_to_remove += self._rm_dr_link(rec)
            elif isinstance(rec, udfmod.UDFFileEntry):
                num_bytes_to_remove += self._rm_udf_link(rec)
            else:
                # This should never happen
                raise pycdlibexception.PyCdlibInternalError('Saw an El Torito record that was neither ISO nor UDF')

        # Remove the linkage from the El Torito Entries to the inodes
        entries_to_remove = [self.eltorito_boot_catalog.initial_entry]
        for sec in self.eltorito_boot_catalog.sections:
            for entry in sec.section_entries:
                entries_to_remove.append(entry)

        for entry in entries_to_remove:
            if entry.inode is not None:
                new_list = []
                for rec in entry.inode.linked_records:
                    if id(rec) != id(entry):
                        new_list.append(rec)
                entry.inode.linked_records = new_list

        num_bytes_to_remove += len(self.eltorito_boot_catalog.record())

        self.eltorito_boot_catalog = None

        self._finish_remove(num_bytes_to_remove, True)

    def add_symlink(self, symlink_path, rr_symlink_name=None, rr_path=None,
                    joliet_path=None, udf_symlink_path=None, udf_target=None):
        '''
        Add a symlink from rr_symlink_name to the rr_path.  The ISO must have
        either Rock Ridge or UDF support (or both).

        Parameters:
         symlink_path - The ISO9660 name of the symlink itself on the ISO.
         rr_symlink_name - The Rock Ridge name of the symlink itself on the ISO.
         rr_path - The Rock Ridge name of the entry on the ISO that the symlink
                   points to.
         joliet_path - The Joliet name of the symlink (if this ISO has Joliet).
         udf_symlink_path - The UDF path of the symlink itself on the ISO.
         udf_target - The UDF name of the entry on the ISO that the symlink
                      points to.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        # There are actually quite a few combinations and rules to think about
        # here.  Rules:
        #
        # 1.  All symlinks must have an ISO9660 name.
        # 2.  If the ISO is Rock Ridge, it must have a Rock Ridge name for the
        #     ISO9660 Directory Record (rr_symlink_name).
        # 3.  Conversely, rr_symlink_name must not be provided for a
        #     non-Rock Ridge ISO.
        # 4.  rr_path is the optional target for the symlink; if it is provided,
        #     then the ISO must be a Rock Ridge one.
        # 5.  udf_symlink_path is the optional UDF name for the symlink; if it
        #     is provided, then this must be a UDF ISO and udf_target must also
        #     be provided.
        # 6.  Conversely, if this is a non-UDF ISO, udf_symlink_path must not
        #     be provided.
        # 7.  udf_target is the optional UDF target for the symlink; if it is
        #     provided, then this must be a UDF ISO and udf_symlink_path must
        #     also be provided.
        # 8.  Conversely, if this is a non-UDF ISO, udf_target must not be
        #     provided.
        # 9.  joliet_path is the optional path on the Joliet filesystem; if it
        #     is provided, the ISO must be a Joliet one.
        # 10. Conversely, if this is a non-Joliet ISO, joliet_path must not be
        #     provided.
        # 11. At least one of rr_path and the pair of
        #     udf_symlink_path, udf_target must be provided.

        if self.rock_ridge is not None:
            # Rule 2
            if rr_symlink_name is None:
                raise pycdlibexception.PyCdlibInvalidInput('A Rock Ridge name must be passed for a Rock Ridge ISO')
        else:
            # Rule 3
            if rr_symlink_name is not None:
                raise pycdlibexception.PyCdlibInvalidInput('A Rock Ridge name can only be passed for a Rock Ridge ISO')

        if rr_path is not None:
            # Rule 4
            if self.rock_ridge is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only add a symlink to a Rock Ridge or UDF ISO')

        if udf_symlink_path is not None:
            # Rule 5/6/7/8
            if self.udf_main_descs is None:
                raise pycdlibexception.PyCdlibInvalidInput('Can only add a UDF symlink to a UDF ISO')
            if udf_target is None:
                raise pycdlibexception.PyCdlibInvalidInput('A udf_target must be supplied along with a udf_symlink_path')

        if joliet_path is not None:
            # Rule 9/10
            if self.joliet_vd is None:
                raise pycdlibexception.PyCdlibInvalidInput('A Joliet path can only be specified for a Joliet ISO')

        if rr_path is None and udf_symlink_path is None:
            # Rule 11
            raise pycdlibexception.PyCdlibInvalidInput('At least one of a Rock Ridge or a UDF target must be specified')

        symlink_path = utils.normpath(symlink_path)
        (name, parent) = self._name_and_parent_from_path(iso_path=symlink_path)

        log_block_size = self.pvd.logical_block_size()

        # The ISO9660 directory record; this will be added in all cases.
        rec = dr.DirectoryRecord()

        num_bytes_to_add = 0
        if rr_path is not None:
            # We specifically do *not* normalize rr_path here, since that
            # potentially changes the meaning of what the user wanted.

            rr_symlink_name = rr_symlink_name.encode('utf-8')
            rec.new_symlink(self.pvd, name, parent, rr_path.encode('utf-8'),
                            self.pvd.sequence_number(), self.rock_ridge,
                            rr_symlink_name, self.xa)
            num_bytes_to_add += self._add_child_to_dr(rec, log_block_size)

            num_bytes_to_add += self._update_rr_ce_entry(rec)

        if udf_symlink_path is not None and udf_target is not None:
            # If we aren't making a Rock Ridge symlink at the same time, we need
            # to add a new zero-byte file to the ISO.
            if rr_path is None:
                rrname = name
                if self.rock_ridge is None:
                    rrname = None
                num_bytes_to_add += self._add_fp(None, 0, False, symlink_path,
                                                 rrname, joliet_path, None, None, False)

            udf_symlink_path = utils.normpath(udf_symlink_path)

            # We specifically do *not* normalize udf_target here, since that
            # potentially changes the meaning of what the user wanted.

            (udf_name, udf_parent) = self._name_and_parent_from_path(udf_path=udf_symlink_path)
            file_ident = udfmod.UDFFileIdentifierDescriptor()
            file_ident.new(False, False, udf_name)
            num_new_extents = udf_parent.add_file_ident_desc(file_ident, log_block_size)
            num_bytes_to_add += num_new_extents * log_block_size

            # Generate the bytearry representing the symlink
            symlink_bytearray = udfmod.symlink_to_bytes(udf_target)

            # The UDF File Entry
            file_entry = udfmod.UDFFileEntry()
            file_entry.new(len(symlink_bytearray), 'symlink', udf_parent,
                           log_block_size)
            file_ident.file_entry = file_entry
            file_entry.file_ident = file_ident
            num_bytes_to_add += log_block_size
            num_bytes_to_add += file_entry.info_len

            # The inode for the symlink array.
            ino = inode.Inode()
            ino.new(len(symlink_bytearray), BytesIO(symlink_bytearray), False, 0)
            ino.linked_records.append(file_entry)
            ino.num_udf += 1
            file_entry.inode = ino
            self.inodes.append(ino)

            self.udf_logical_volume_integrity.logical_volume_impl_use.num_files += 1

            # Note that we explicitly do *not* link this record to the ISO9660
            # record; that's because there is no way to correlate them during
            # parse time.  Instead, we treat them as individual entries, which
            # has the knock-on effect of requiring two operations to remove;
            # rm_file() to remove the ISO9660 record, and rm_hard_link() to
            # remove the UDF record.

        if joliet_path is not None:
            joliet_path = self._normalize_joliet_path(joliet_path)
            (joliet_name, joliet_parent) = self._name_and_parent_from_path(joliet_path=joliet_path)

            # Add in a "fake" symlink entry for Joliet.
            joliet_rec = dr.DirectoryRecord()
            joliet_rec.new_file(self.joliet_vd, 0, joliet_name, joliet_parent,
                                self.joliet_vd.sequence_number(), None, None,
                                self.xa, None)
            num_bytes_to_add += self._add_child_to_dr(joliet_rec,
                                                      self.joliet_vd.logical_block_size())

        self._finish_add(0, num_bytes_to_add)

    def list_dir(self, iso_path, joliet=False):
        '''
        (deprecated) Generate a list of all of the file/directory objects in the
        specified location on the ISO.  It is recommended to use the
        'list_children' API instead.

        Parameters:
         iso_path - The path on the ISO to look up information for.
         joliet - Whether to look for the path in the Joliet portion of the ISO.
        Yields:
         Children of this path.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if joliet:
            rec = self._get_entry(joliet_path=iso_path)
        else:
            try_rr = False
            try:
                rec = self._get_entry(iso_path=iso_path)
            except pycdlibexception.PyCdlibInvalidInput:
                try_rr = True

            if try_rr:
                rec = self._find_rr_record(utils.normpath(iso_path))

        for c in _yield_children(rec):
            yield c

    def list_children(self, **kwargs):
        '''
        Generate a list of all of the file/directory objects in the
        specified location on the ISO.

        Parameters:
         iso_path - The absolute path on the ISO to list the children for.
         rr_path - The absolute Rock Ridge path on the ISO to list the children for.
         joliet_path - The absolute Joliet path on the ISO to list the children for.
         udf_path - The absolute UDF path on the ISO to list the children for.
        Yields:
         Children of this path.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        iso_path = None
        rr_path = None
        joliet_path = None
        udf_path = None
        num_paths = 0
        for key in kwargs:
            if key == 'joliet_path':
                joliet_path = kwargs[key]
            elif key == 'rr_path':
                rr_path = kwargs[key]
            elif key == 'iso_path':
                iso_path = kwargs[key]
            elif key == 'udf_path':
                udf_path = kwargs[key]
            else:
                raise pycdlibexception.PyCdlibInvalidInput("Invalid keyword, must be one of 'iso_path', 'rr_path', or 'joliet_path'")
            if kwargs[key] is not None:
                num_paths += 1

        if num_paths != 1:
            raise pycdlibexception.PyCdlibInvalidInput("Must specify one, and only one of 'iso_path', 'rr_path', or 'joliet_path'")

        if udf_path is not None:
            rec = self._get_entry(udf_path=udf_path)

            if not rec.is_dir():
                raise pycdlibexception.PyCdlibInvalidInput('UDF File Entry is not a directory!')

            for fi_desc in rec.fi_descs:
                yield fi_desc.file_entry
        else:
            if joliet_path is not None:
                rec = self._get_entry(joliet_path=joliet_path)
            elif rr_path is not None:
                rec = self._get_entry(rr_path=rr_path)
            else:
                rec = self._get_entry(iso_path=iso_path)

            for c in _yield_children(rec):
                yield c

    def get_entry(self, iso_path, joliet=False):
        '''
        (deprecated) Get the directory record for a particular path.  It is
        recommended to use the 'get_record' API instead.

        Parameters:
         iso_path - The path on the ISO to look up information for.
         joliet - Whether to look for the path in the Joliet portion of the ISO.
        Returns:
         A dr.DirectoryRecord object representing the path.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if joliet:
            return self._get_entry(joliet_path=iso_path)
        return self._get_entry(iso_path=iso_path)

    def get_record(self, **kwargs):
        '''
        Get the directory record for a particular path.

        Parameters:
         iso_path - The absolute path on the ISO9660 filesystem to get the
                    record for.
         rr_path - The absolute path on the Rock Ridge filesystem to get the
                   record for.
         joliet_path - The absolute path on the Joliet filesystem to get the
                       record for.
         udf_path - The absolute path on the UDF filesystem to get the record
                    for.
        Returns:
         An object that represents the path.  This may be a dr.DirectoryRecord
         object (in the cases of iso_path, rr_path, or joliet_path), or a
         udf.UDFFileEntry object (in the case of udf_path).
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        iso_path = None
        rr_path = None
        joliet_path = None
        udf_path = None
        num_paths = 0
        for key in kwargs:
            if key == 'joliet_path':
                joliet_path = kwargs[key]
            elif key == 'rr_path':
                rr_path = kwargs[key]
            elif key == 'iso_path':
                iso_path = kwargs[key]
            elif key == 'udf_path':
                udf_path = kwargs[key]
            else:
                raise pycdlibexception.PyCdlibInvalidInput("Invalid keyword, must be one of 'iso_path', 'rr_path', or 'joliet_path'")
            if kwargs[key] is not None:
                num_paths += 1

        if num_paths != 1:
            raise pycdlibexception.PyCdlibInvalidInput("Must specify one, and only one of 'iso_path', 'rr_path', or 'joliet_path'")

        if joliet_path is not None:
            return self._get_entry(joliet_path=joliet_path)
        elif rr_path is not None:
            return self._get_entry(rr_path=rr_path)
        elif udf_path is not None:
            return self._get_entry(udf_path=udf_path)
        return self._get_entry(iso_path=iso_path)

    def add_isohybrid(self, part_entry=1, mbr_id=None, part_offset=0,
                      geometry_sectors=32, geometry_heads=64, part_type=0x17,
                      mac=False):
        '''
        Make an ISO a 'hybrid', which means that it can be booted either from a
        CD or from more traditional media (like a USB stick).  This requires
        that the ISO already have El Torito, and will use the El Torito boot
        file as a bootable image.  That image must contain a certain signature
        in order to work as a hybrid (if using syslinux, this generally means
        the isohdpfx.bin files).

        Paramters:
         part_entry - The partition entry to use; one by default.
         mbr_id - The mbr_id to use.  If set to None (the default), a random one
                  will be generated.
         part_offset - The partition offset to use; zero by default.
         geometry_sectors - The number of sectors to assign; thirty-two by default.
         geometry_heads - The number of heads to assign; sixty-four by default.
         part_type - The partition type to assign; twenty-three by default.
         mac - Add support for Mac; False by default.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if self.eltorito_boot_catalog is None:
            raise pycdlibexception.PyCdlibInvalidInput('The ISO must have an El Torito Boot Record to add isohybrid support')

        if self.eltorito_boot_catalog.initial_entry.sector_count != 4:
            raise pycdlibexception.PyCdlibInvalidInput('El Torito Boot Catalog sector count must be 4 (was actually 0x%x)' % (self.eltorito_boot_catalog.initial_entry.sector_count))

        # Now check that the eltorito boot file contains the appropriate
        # signature (offset 0x40, '\xFB\xC0\x78\x70')
        with inode.InodeOpenData(self.eltorito_boot_catalog.initial_entry.inode, self.pvd.logical_block_size()) as (data_fp, data_len_unused):
            data_fp.seek(0x40, os.SEEK_CUR)
            signature = data_fp.read(4)

        if signature != b'\xfb\xc0\x78\x70':
            raise pycdlibexception.PyCdlibInvalidInput('Invalid signature on boot file for iso hybrid')

        self.isohybrid_mbr = isohybrid.IsoHybrid()
        self.isohybrid_mbr.new(mac, part_entry, mbr_id, part_offset,
                               geometry_sectors, geometry_heads, part_type)

    def rm_isohybrid(self):
        '''
        Remove the 'hybridization' of an ISO, making it a traditional ISO again.
        This means the ISO will no longer be able to be copied and booted off
        of traditional media (like USB sticks).

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        self.isohybrid_mbr = None

    def full_path_from_dirrecord(self, rec, rockridge=False):
        '''
        A method to get the absolute path of a directory record.

        Parameters:
         rec - The directory record to get the full path for.
         rockridge - Whether to get the rock ridge full path.
        Returns:
         A string representing the absolute path to the file on the ISO.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if isinstance(rec, dr.DirectoryRecord):
            encoding = 'utf-8'
            if self.joliet_vd is not None and id(rec.vd) == id(self.joliet_vd):
                encoding = 'utf-16_be'
            slash = '/'.encode(encoding)

            # A root entry has no Rock Ridge entry, even on a Rock Ridge ISO.  Just
            # always return / here.
            if rec.is_root:
                return slash

            if rockridge and rec.rock_ridge is None:
                raise pycdlibexception.PyCdlibInvalidInput('Cannot generate a Rock Ridge path on a non-Rock Ridge ISO')

            parent = rec
            ret = b''
            while parent is not None:
                if not parent.is_root:
                    if rockridge and parent.rock_ridge is not None:
                        ret = slash + parent.rock_ridge.name() + ret
                    else:
                        ret = slash + parent.file_identifier() + ret
                parent = parent.parent
        else:
            encoding = rec.file_ident.encoding
            slash = '/'.encode(encoding)
            parent = rec
            ret = b''
            while parent is not None:
                ident = parent.file_identifier()
                if ident != b'/':
                    ret = slash + ident + ret
                parent = parent.parent

        if sys.version_info >= (3, 0):
            # Python 3, just return the encoded version
            return ret.decode(encoding)

        # Python 2.
        return ret.decode(encoding).encode('utf-8')

    def duplicate_pvd(self):
        '''
        A method to add a duplicate PVD to the ISO.  This is a mostly useless
        feature allowed by Ecma-119 to have duplicate PVDs to avoid possible
        corruption.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        pvd = headervd.PrimaryOrSupplementaryVD(headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY)
        pvd.copy(self.pvd)
        self.pvds.append(pvd)

        self._finish_add(self.pvd.logical_block_size(), 0)

    def set_hidden(self, iso_path=None, rr_path=None, joliet_path=None):
        '''
        Set the ISO9660 hidden attribute on a file or directory.  This will
        cause the file or directory not to show up when listing entries on the
        ISO.  Exactly one of iso_path, rr_path, or joliet_path must be specified.

        Parameters:
         iso_path - The path on the ISO to set the hidden bit on.
         rr_path - The Rock Ridge path on the ISO to set the hidden bit on.
         joliet_path - The Joliet path on the ISO to set the hidden bit on.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if len([x for x in (iso_path, rr_path, joliet_path) if x is not None]) != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Must provide exactly one of iso_path, rr_path, or joliet_path')

        if iso_path is not None:
            rec = self._find_iso_record(utils.normpath(iso_path))
        elif rr_path is not None:
            rec = self._find_rr_record(utils.normpath(rr_path))
        elif joliet_path is not None:
            joliet_path = self._normalize_joliet_path(joliet_path)
            rec = self._find_joliet_record(joliet_path)

        rec.change_existence(True)

    def clear_hidden(self, iso_path=None, rr_path=None, joliet_path=None):
        '''
        Clear the ISO9660 hidden attribute on a file or directory.  This will
        cause the file or directory to show up when listing entries on the ISO.
        Exactly one of iso_path, rr_path, or joliet_path must be specified.

        Parameters:
         iso_path - The path on the ISO to clear the hidden bit from.
         rr_path - The Rock Ridge path on the ISO to clear the hidden bit from.
         joliet_path - The Joliet path on the ISO to clear the hidden bit from.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if len([x for x in (iso_path, rr_path, joliet_path) if x is not None]) != 1:
            raise pycdlibexception.PyCdlibInvalidInput('Must provide exactly one of iso_path, rr_path, or joliet_path')

        if iso_path is not None:
            rec = self._find_iso_record(utils.normpath(iso_path))
        elif rr_path is not None:
            rec = self._find_rr_record(utils.normpath(rr_path))
        elif joliet_path is not None:
            joliet_path = self._normalize_joliet_path(joliet_path)
            rec = self._find_joliet_record(joliet_path)

        rec.change_existence(False)

    def force_consistency(self):
        '''
        Make sure the ISO object is fully consistent.  PyCdlib typically delays
        doing work until it is necessary, and this detail is usually hidden
        from users.  However, there are times that a user may want a fully
        consistent view of the ISO without calling one of the methods that
        forces consistency.  This method allows the user to force a consistent
        view of this object.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        self._reshuffle_extents()

    def set_relocated_name(self, name, rr_name):
        '''
        Set the name of the relocated directory on a Rock Ridge ISO.  The ISO
        must be a Rock Ridge one, and must not have previously had the relocated
        name set.

        Parameters:
         name - The name for a relocated directory.
         rr_name - The Rock Ridge name for a relocated directory.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if self.rock_ridge is None:
            raise pycdlibexception.PyCdlibInvalidInput('Can only set the relocated name on a Rock Ridge ISO')

        encoded_name = name.encode('utf-8')
        encoded_rr_name = rr_name.encode('utf-8')
        if self._rr_moved_name is not None:
            if self._rr_moved_name == encoded_name and self._rr_moved_rr_name == encoded_rr_name:
                return
            raise pycdlibexception.PyCdlibInvalidInput('Changing the existing rr_moved name is not allowed')

        _check_iso9660_directory(encoded_name, self.interchange_level)
        self._rr_moved_name = encoded_name
        self._rr_moved_rr_name = encoded_rr_name

    def close(self):
        '''
        Close the PyCdlib object, and re-initialize the object to the defaults.
        The object can then be re-used for manipulation of another ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInvalidInput('This object is not yet initialized; call either open() or new() to create an ISO')

        if self._managing_fp:
            # In this case, we are managing self._cdfp, so we need to close it
            self._cdfp.close()

        self._initialize()
