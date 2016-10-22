# Copyright (C) 2015-2016  Chris Lalancette <clalancette@gmail.com>

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

import struct
import collections
import os

import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.utils as utils
import pycdlib.eltorito as eltorito
import pycdlib.path_table_record as path_table_record
import pycdlib.dr as dr
import pycdlib.isohybrid as isohybrid
import pycdlib.headervd as headervd

# There are a number of specific ways that numerical data is stored in the
# ISO9660/Ecma-119 standard.  In the text these are reference by the section
# number they are stored in.  A brief synopsis:
#
# 7.1.1 - 8-bit number
# 7.2.3 - 16-bit number, stored first as little-endian then as big-endian (4 bytes total)
# 7.3.1 - 32-bit number, stored as little-endian
# 7.3.2 - 32-bit number ,stored as big-endian
# 7.3.3 - 32-bit number, stored first as little-endian then as big-endian (8 bytes total)

def pad(data_size, pad_size):
    '''
    A function to generate a string of padding zeros, if necessary.  Given the
    current data_size, and a target pad_size, this function will generate a string
    of zeros that will take the data_size up to the pad size.

    Parameters:
     data_size - The current size of the data.
     pad_size - The desired pad size.
    Returns:
     String containing the zero padding.
    '''
    padbytes = pad_size - (data_size % pad_size)
    if padbytes != pad_size:
        return b"\x00" * padbytes
    return b""

def check_d1_characters(name):
    '''
    A function to check that a name only uses d1 characters as defined by ISO9660.

    Parameters:
     name - The name to check.
    Returns:
     Nothing.
    '''
    for char in name:
        char = bytes(bytearray([char]))
        if char not in [b'A', b'B', b'C', b'D', b'E', b'F', b'G', b'H', b'I', b'J', b'K',
                        b'L', b'M', b'N', b'O', b'P', b'Q', b'R', b'S', b'T', b'U', b'V',
                        b'W', b'X', b'Y', b'Z', b'0', b'1', b'2', b'3', b'4', b'5', b'6',
                        b'7', b'8', b'9', b'_', b'.', b'-', b'+', b'(', b')', b'~', b'&',
                        b'!', b'@', b'$']:
            raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 filename (it contains invalid characters)" % (name))

def check_iso9660_filename(fullname, interchange_level):
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
    # First we split on the semicolon for the version number.
    namesplit = fullname.split(b';')

    # Ecma-119 says that filenames must end with a semicolon-number, but I have
    # found CDs (Ubuntu 14.04 Desktop i386, for instance) that do not follow
    # this.  Thus we allow for names both with and without the semi+version.
    if len(namesplit) == 2:
        version = namesplit[1]

        # Ecma-119 says that filenames must have a version number, but I have
        # found CDs (FreeBSD 10.1 amd64) that do not have any version number.
        # Allow for this.
        # The second entry should be the version number between 1 and 32767.
        if version != "" and (int(version) < 1 or int(version) > 32767):
            raise pycdlibexception.PyCdlibException("%s has an invalid version number (must be between 1 and 32767" % (fullname))
    elif len(namesplit) != 1:
        raise pycdlibexception.PyCdlibException("%s contains multiple semicolons!" % (fullname))

    name_plus_extension = namesplit[0]

    # The first entry should be x.y, so we split on the dot.
    dotsplit = name_plus_extension.split(b'.')
    if len(dotsplit) == 1:
        name = dotsplit[0]
        extension = ''
    else:
        name = b'.'.join(dotsplit[:-1])
        extension = dotsplit[-1]

    # Ecma-119 section 7.5.1 specifies that filenames must have at least one
    # character in either the name or the extension.
    if len(name) == 0 and len(extension) == 0:
        raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 filename (either the name or extension must be non-empty" % (fullname))

    if interchange_level == 1:
        # According to Ecma-119, section 10.1, at level 1 the filename can
        # only be up to 8 d-characters or d1-characters, and the extension can
        # only be up to 3 d-characters or 3 d1-characters.
        if len(name) > 8 or len(extension) > 3:
            raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 filename at interchange level 1" % (fullname))
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
    check_d1_characters(name.upper())
    check_d1_characters(extension.upper())

def check_iso9660_directory(fullname, interchange_level):
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
        raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 directory name (the name must be at least 1 character long)" % (fullname))

    if interchange_level == 1:
        # Ecma-119 section 10.1 says that directory identifiers lengths cannot
        # exceed 8 at interchange level 1.
        if len(fullname) > 8:
            raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 directory name at interchange level 1" % (fullname))
    else:
        # Ecma-119 section 7.6.3 says that directory identifiers lengths cannot
        # exceed 31.
        if len(fullname) > 207:
            raise pycdlibexception.PyCdlibException("%s is not a valid ISO9660 directory name (it is longer than 31 characters)" % (fullname))

    # Ecma-119 section 7.6.1 says that directory names consist of one or more
    # d-characters or d1-characters.  While the definition of d-characters and
    # d1-characters is not specified in Ecma-119,
    # http://wiki.osdev.org/ISO_9660 suggests that this consists of A-Z, 0-9, _
    # which seems to correlate with empirical evidence.  Thus we check for that
    # here.
    check_d1_characters(fullname.upper())

def check_interchange_level(identifier, is_dir):
    '''
    A function to determine the interchange level of an identifier on an ISO.
    Since ISO9660 doesn't encode the interchange level on the ISO itself,
    this is used to infer the interchange level of an ISO.

    Parameters:
     identifier - The identifier to figure out the interchange level for.
     is_dir - Whether this is a directory or a file.
    Returns:
     The interchange level as an integer.
    '''
    interchange_level = 1
    cmpfunc = check_iso9660_filename
    if is_dir:
        cmpfunc = check_iso9660_directory

    try_level_3 = False
    try:
        # First we try to check for interchange level 1; if
        # that fails, we fall back to interchange level 3
        # and check that.
        cmpfunc(identifier, 1)
    except pycdlibexception.PyCdlibException:
        try_level_3 = True

    if try_level_3:
        cmpfunc(identifier, 3)
        # If the above did not throw an exception, then this
        # is interchange level 3 and we should mark it.
        interchange_level = 3

    return interchange_level

class PyCdlib(object):
    '''
    The main class for manipulating ISOs.
    '''
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
        self.cdfp.seek(16 * 2048)
        done = False
        while not done:
            # All volume descriptors are exactly 2048 bytes long
            curr_extent = self.cdfp.tell() // 2048
            vd = self.cdfp.read(2048)
            if len(vd) != 2048:
                raise pycdlibexception.PyCdlibException("Failed to read entire volume descriptor")
            (desc_type,) = struct.unpack_from("=B", vd, 0)
            if desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvd = headervd.PrimaryVolumeDescriptor()
                pvd.parse(vd, self.cdfp, curr_extent)
                self.pvds.append(pvd)
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
                vdst = headervd.VolumeDescriptorSetTerminator()
                vdst.parse(vd, curr_extent)
                self.vdsts.append(vdst)
                # Once we see a set terminator, we stop parsing.  Oddly,
                # Ecma-119 says there may be multiple set terminators, but in
                # that case I don't know how to tell when we are done parsing
                # volume descriptors.  Leave this for now.
                done = True
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
                br = headervd.BootRecord()
                br.parse(vd, curr_extent)
                self.brs.append(br)
            elif desc_type == headervd.VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
                svd = headervd.SupplementaryVolumeDescriptor()
                svd.parse(vd, self.cdfp, curr_extent)
                self.svds.append(svd)
            else:
                raise pycdlibexception.PyCdlibException("Invalid volume descriptor type %d" % (desc_type))

        # The language in Ecma-119, p.8, Section 6.7.1 says:
        #
        # The sequence shall contain one Primary Volume Descriptor (see 8.4) recorded at least once.
        #
        # The important bit there is "at least one", which means that we have
        # to accept ISOs with more than one PVD.
        if len(self.pvds) < 1:
            raise pycdlibexception.PyCdlibException("Valid ISO9660 filesystems must have at least one PVD")
        if len(self.pvds) > 1:
            for pvd in self.pvds:
                for other in self.pvds:
                    if pvd != other:
                        raise pycdlibexception.PyCdlibException("Multiple occurrences of PVD did not agree!")

        if len(self.vdsts) < 1:
            raise pycdlibexception.PyCdlibException("Valid ISO9660 filesystems must have at least one Volume Descriptor Set Terminator")

        self.pvd = self.pvds[0]

    def _seek_to_extent(self, extent):
        '''
        An internal method to seek to a particular extent on the input ISO.

        Parameters:
         extent - The extent to seek to.
        Returns:
         Nothing.
        '''
        self.cdfp.seek(extent * self.pvd.logical_block_size())

    def _walk_directories(self, vd, do_check_interchange):
        '''
        An internal method to walk the directory records in a volume descriptor,
        starting with the root.  For each child in the directory record,
        we create a new dr.DirectoryRecord object and append it to the parent.

        Parameters:
         vd - The volume descriptor to walk.
         do_check_interchange - Whether to check the interchange level or not.
        Returns:
         The interchange level that this ISO conforms to.
        '''
        vd.set_ptr_dirrecord(vd.path_table_records[0], vd.root_directory_record())
        vd.root_directory_record().set_ptr(vd.path_table_records[0])
        interchange_level = 1
        dirs = collections.deque([vd.root_directory_record()])
        block_size = vd.logical_block_size()
        parent_links = []
        child_links = []
        while dirs:
            dir_record = dirs.popleft()

            self._seek_to_extent(dir_record.extent_location())
            length = dir_record.file_length()
            offset = 0
            while length > 0:
                # read the length byte for the directory record
                lenraw = self.cdfp.read(1)
                if len(lenraw) != 1:
                    raise pycdlibexception.PyCdlibException("Not enough data for the next directory record")
                (lenbyte,) = struct.unpack_from("=B", lenraw, 0)
                length -= 1
                offset += lenbyte
                if offset > block_size:
                    # Ecma-119 Section 6.8.1.2 says:
                    #
                    # "Each Directory Record shall end in the Logical Sector in which it begins.
                    raise pycdlibexception.PyCdlibException("Invalid directory record")
                elif offset == block_size:
                    # In this case, we read right to the end of the extent;
                    # reset offset back to 0
                    offset = 0

                if lenbyte == 0:
                    # If we saw zero length, this may be a padding byte; seek
                    # to the start of the next extent.
                    if length > 0:
                        padsize = block_size - (self.cdfp.tell() % block_size)
                        padbytes = self.cdfp.read(padsize)
                        if padbytes != b'\x00'*padsize:
                            # For now we are pedantic, and if the padding bytes
                            # are not all zero we throw an Exception.  Depending
                            # one what we see in the wild, we may have to loosen
                            # this check.
                            raise pycdlibexception.PyCdlibException("Invalid padding on ISO")
                        length -= padsize
                        offset = 0
                        if length < 0:
                            # For now we are pedantic, and if the length goes
                            # negative because of the padding we throw an
                            # exception.  Depending on what we see in the wild,
                            # we may have to loosen this check.
                            raise pycdlibexception.PyCdlibException("Invalid padding on ISO")
                    continue

                new_record = dr.DirectoryRecord()
                rr = new_record.parse(b"%s%s" % (lenraw, self.cdfp.read(lenbyte - 1)),
                                      self.cdfp, dir_record)
                # The parse method of dr.DirectoryRecord returns None if this
                # record doesn't have Rock Ridge extensions, or the version of
                # the extensions.  However, ISOs that have Rock Ridge extensions
                # don't necessarily have consistent extensions.  However, we
                # also don't allow mixed versions on the ISO.  This all boils
                # down to the fact that if the current version is None, we can
                # upgrade it to a version, but once we are on a particular
                # version, we only allow records of that version or None.
                if self.rock_ridge is None:
                    self.rock_ridge = rr
                elif self.rock_ridge == "1.09":
                    if rr is not None and rr != "1.09":
                        raise pycdlibexception.PyCdlibException("Inconsistent Rock Ridge versions on the ISO!")
                elif self.rock_ridge == "1.12":
                    if rr is not None and rr != "1.12":
                        raise pycdlibexception.PyCdlibException("Inconsistent Rock Ridge versions on the ISO!")

                length -= lenbyte - 1

                is_symlink = new_record.rock_ridge is not None and new_record.rock_ridge.is_symlink()

                # ISO generation programs generally use random extent locations
                # for zero-length files.  Thus, it is not valid for us to link
                # zero-length files to other files, as the linkage will be
                # essentially random.  Make sure we ignore zero-length files
                # (which includes symlinks) for linkage.
                if not new_record.is_dir() and new_record.data_length > 0 and not is_symlink:
                    if isinstance(vd, headervd.PrimaryVolumeDescriptor) and not new_record.extent_location() in self.pvd.extent_to_dr:
                        self.pvd.extent_to_dr[new_record.extent_location()] = new_record
                    else:
                        try:
                            self.pvd.extent_to_dr[new_record.extent_location()].linked_records.append(new_record)
                        except KeyError:
                            # There may be files that are hidden in the regular
                            # ISO, but not in Joliet.  For those, there will be
                            # a key error when trying to link it to the Primary
                            # record, so we just pass through here.
                            pass

                if new_record.rock_ridge is not None and new_record.rock_ridge.ce_record is not None:
                    orig_pos = self.cdfp.tell()
                    self._seek_to_extent(new_record.rock_ridge.ce_record.continuation_entry.extent_location())
                    self.cdfp.seek(new_record.rock_ridge.ce_record.continuation_entry.offset(), os.SEEK_CUR)
                    con_block = self.cdfp.read(new_record.rock_ridge.ce_record.continuation_entry.length())
                    new_record.rock_ridge.ce_record.continuation_entry.parse(con_block,
                                                                             new_record.rock_ridge.bytes_to_skip)
                    self.cdfp.seek(orig_pos)

                is_pvd = isinstance(vd, headervd.PrimaryVolumeDescriptor)
                has_eltorito = self.eltorito_boot_catalog is not None

                # See the discussion about about symlinks for why we don't try
                # to assign dirrecords for eltorito with symlinks.
                if is_pvd and has_eltorito and not is_symlink:
                    self.eltorito_boot_catalog.set_dirrecord_if_necessary(new_record)

                rr_cl = new_record.rock_ridge is not None and new_record.rock_ridge.has_child_link_record()

                if rr_cl:
                    child_links.append(new_record)

                if new_record.is_dir():
                    if new_record.is_dotdot() and new_record.rock_ridge is not None and new_record.rock_ridge.has_parent_link_record():
                        # If this is the dotdot record, and it has a parent
                        # link record, make sure to link up the parent link
                        # directory record.
                        parent_links.append(new_record)
                    dots = new_record.is_dot() or new_record.is_dotdot()
                    if not dots and not rr_cl:
                        if do_check_interchange:
                            interchange_level = max(interchange_level, check_interchange_level(new_record.file_identifier(), True))
                        dirs.append(new_record)
                        ptr = vd.lookup_ptr_from_dirrecord(new_record)
                        vd.set_ptr_dirrecord(ptr, new_record)
                        new_record.set_ptr(ptr)
                else:
                    if do_check_interchange:
                        interchange_level = max(interchange_level, check_interchange_level(new_record.file_identifier(), False))
                if dir_record.add_child(new_record, vd.logical_block_size()):
                    raise pycdlibexception.PyCdlibException("More records than fit into parent directory; ISO is corrupt")

        for pl in parent_links:
            (pl.rock_ridge.parent_link,index_unused) = self._find_record_by_extent(vd, pl.rock_ridge.pl_record.parent_log_block_num)

        for cl in child_links:
            (cl.rock_ridge.child_link,index_unused) = self._find_record_by_extent(vd, cl.rock_ridge.cl_record.child_log_block_num)

        return interchange_level

    def _initialize(self):
        '''
        An internal method to re-initialize the object.  Called from
        both __init__ and close.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        self.cdfp = None
        self.pvd = None
        self.svds = []
        self.brs = []
        self.vdsts = []
        self.eltorito_boot_catalog = None
        self.initialized = False
        self.rock_ridge = None
        self.isohybrid_mbr = None
        self.xa = False
        self.managing_fp = False
        self.managing_dr_fps = False
        self.pvds = []

    def _parse_path_table(self, vd, extent, little_or_big):
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
        left = vd.path_table_size()
        ptrs = []
        while left > 0:
            ptr = path_table_record.PathTableRecord()
            len_di_byte = self.cdfp.read(1)
            if len(len_di_byte) != 1:
                raise pycdlibexception.PyCdlibException("Not enough data for path table record")
            read_len = path_table_record.PathTableRecord.record_length(struct.unpack_from("=B", len_di_byte, 0)[0])
            data = b"%s%s" % (len_di_byte, self.cdfp.read(read_len - 1))
            left -= read_len

            ptr.parse(data, len(ptrs) + 1)
            depth = 1
            if little_or_big == "little":
                if len(ptrs) != 0:
                    # Here, we are going to index into the parent directory num
                    # minus one to find its depth, and then add one to get the
                    # current depth.  Before we do all of that, though, make
                    # sure that the parent_directory_num - 1 is sane and in
                    # the ptrs list.
                    offset = ptr.parent_directory_num - 1
                    if offset < 0 or offset > len(ptrs):
                        raise pycdlibexception.PyCdlibException("Invalid offset into Path Table Records array; ISO is probably corrupt")
                    depth = ptrs[offset].depth + 1
                ptr.set_depth(depth)
                vd.add_path_table_record(ptr)
            else:
                if len(ptrs) != 0:
                    offset = utils.swab_16bit(ptr.parent_directory_num) - 1
                    if offset < 0 or offset > len(ptrs):
                        raise pycdlibexception.PyCdlibException("Invalid offset into Path Table Records array; ISO is probably corrupt")
                    depth = ptrs[offset].depth + 1

                ptr.set_depth(depth)
                # The code below is equivalent to calling bisect.insort_left, but we call
                # the less_than_be() method instead of the implicit __lt__ so that we can
                # deal with big-endianness appropriately.
                lo = 0
                hi = len(self.tmp_be_path_table_records)
                while lo < hi:
                    mid = (lo+hi)//2
                    if self.tmp_be_path_table_records[mid].less_than_be(ptr):
                        lo = mid + 1
                    else:
                        hi = mid
                self.tmp_be_path_table_records.insert(lo, ptr)
            ptrs.append(ptr)

    def _find_record(self, vd, path, encoding='ascii'):
        '''
        An internal method to find an entry on the ISO given a Volume
        Descriptor, a full ISO path, and an encoding.  Once the entry is found,
        return the directory record object corresponding to that entry, as well
        as the index within the list of children for that particular parent.
        If the entry could not be found, a pycdlibexception.PyCdlibException is raised.

        Parameters:
         vd - The volume descriptor in which to look up the entry.
         path - The absolute path to look up in the volume descriptor.
         encoding - The encoding to use on the individual portions of the path.
        Returns:
         A tuple containing a directory record entry representing the entry on
         the ISO and the index of that entry into the parent's child list.
        '''
        if bytes(bytearray([path[0]])) != b'/':
            raise pycdlibexception.PyCdlibException("Must be a path starting with /")

        # If the path is just the slash, we just want the root directory, so
        # get the children there and quit.
        if path == b'/':
            return vd.root_directory_record(),0

        # Split the path along the slashes
        splitpath = path.split(b'/')
        # Skip past the first one, since it is always empty.
        splitindex = 1

        reloc_entries = []
        if isinstance(vd, headervd.PrimaryVolumeDescriptor) and self.rock_ridge is not None:
            dirs = collections.deque([vd.root_directory_record()])
            while dirs:
                dir_record = dirs.popleft()
                for child in dir_record.children:
                    # This is equivalent to child.is_dot() or child.is_dotdot(),
                    # but turns out to be much faster.
                    if child.file_ident in [b'\x00', b'\x01']:
                        continue

                    if child.rock_ridge.relocated_record():
                        reloc_entries.append(child)

                    if child.is_dir():
                        dirs.append(child)

        currpath = splitpath[splitindex].decode('utf-8').encode(encoding)
        splitindex += 1
        children = vd.root_directory_record().children
        index = 0
        while index < len(children):
            child = children[index]
            index += 1

            # This is equivalent to child.is_dot() or child.is_dotdot(),
            # but turns out to be much faster.
            if child.file_ident in [b'\x00', b'\x01']:
                continue

            if child.file_identifier() != currpath:
                if child.rock_ridge is None:
                    continue

                if child.rock_ridge.relocated_record():
                    continue

                if child.rock_ridge.name() != currpath:
                    continue

            if child.rock_ridge is not None and child.rock_ridge.has_child_link_record():
                # Here, the rock ridge extension has a child link, so we
                # need to follow it.
                found_deep = False
                for entry in reloc_entries:
                    if child.rock_ridge.child_link_block_num() == entry.extent_location():
                        child = entry
                        found_deep = True
                        break

                if not found_deep:
                    raise pycdlibexception.PyCdlibException("This should never happen")

            # We found the child, and it is the last one we are looking for;
            # return it.
            if splitindex == len(splitpath):
                # We have to remove one from the index since we incremented it
                # above.
                return child,index-1
            else:
                if child.is_dir():
                    children = child.children
                    index = 0
                    currpath = splitpath[splitindex].decode('utf-8').encode(encoding)
                    splitindex += 1

        raise pycdlibexception.PyCdlibException("Could not find path %s" % (path))

    def _split_path(self, iso_path):
        '''
        An internal method to take a fully-qualified iso path and split it into
        components.

        Parameters:
         iso_path - The path to split.
        Returns:
         The components of the path as a list.
        '''
        if bytes(bytearray([iso_path[0]])) != b'/':
            raise pycdlibexception.PyCdlibException("Must be a path starting with /")

        # First we need to find the parent of this directory, and add this
        # one as a child.
        splitpath = iso_path.split(b'/')
        # Pop off the front, as it is always blank.
        splitpath.pop(0)

        return splitpath

    def _check_path_depth(self, iso_path):
        '''
        An internal method to take a fully-qualified iso path and check whether
        it meets the path depth requirements of ISO9660/Ecma-119.

        Parameters:
         iso_path - The path to check.
        Returns:
         Nothing.
        '''
        if len(self._split_path(iso_path)) > 7:
            # Ecma-119 Section 6.8.2.1 says that the number of levels in the
            # hierarchy shall not exceed eight.  However, since the root
            # directory must always reside at level 1 by itself, this gives us
            # an effective maximum hierarchy depth of 7.
            raise pycdlibexception.PyCdlibException("Directory levels too deep (maximum is 7)")

    def _name_and_parent_from_path(self, vd, iso_path, encoding='ascii'):
        '''
        An internal method to find the parent directory record given a full
        ISO path and a Volume Descriptor.  If the parent is found, return the
        parent directory record object and the relative path of the original
        path.

        Parameters:
         vd - The volume descriptor in which to look up the entry.
         iso_path - The absolute path to the entry on the ISO.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''
        splitpath = self._split_path(iso_path)

        # Now take the name off.
        name = splitpath.pop()
        if len(splitpath) == 0:
            # This is a new directory under the root, add it there
            parent = vd.root_directory_record()
        else:
            parent,index_unused = self._find_record(vd, b"%s%s" % (b'/', b'/'.join(splitpath)), encoding)

        return (name, parent)

    def _check_and_parse_eltorito(self, br, logical_block_size):
        '''
        An internal method to examine a Boot Record and see if it is an
        El Torito Boot Record.  If it is, parse the El Torito Boot Catalog,
        verification entry, initial entry, and any additional section entries.

        Parameters:
         br - The boot record to examine for an El Torito signature.
         logical_block_size - The logical block size of the ISO.
        Returns:
         Nothing.
        '''
        if br.boot_system_identifier != b"EL TORITO SPECIFICATION".ljust(32, b'\x00'):
            return

        if self.eltorito_boot_catalog is not None:
            raise pycdlibexception.PyCdlibException("Only one El Torito boot record is allowed")

        # According to the El Torito specification, section 2.0, the El
        # Torito boot record must be at extent 17.
        if br.extent_location() != 17:
            raise pycdlibexception.PyCdlibException("El Torito Boot Record must be at extent 17")

        # Now that we have verified that the BootRecord is an El Torito one
        # and that it is sane, we go on to parse the El Torito Boot Catalog.
        # Note that the Boot Catalog is stored as a file in the ISO, though
        # we ignore that for the purposes of parsing.

        self.eltorito_boot_catalog = eltorito.EltoritoBootCatalog(br)
        eltorito_boot_catalog_extent, = struct.unpack_from("=L", br.boot_system_use[:4], 0)

        old = self.cdfp.tell()
        self.cdfp.seek(eltorito_boot_catalog_extent * logical_block_size)
        data = self.cdfp.read(32)
        while not self.eltorito_boot_catalog.parse(data):
            data = self.cdfp.read(32)
        self.cdfp.seek(old)

    def _reassign_vd_dirrecord_extents(self, vd, current_extent):
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
        # Here we re-walk the entire tree, re-assigning extents as necessary.
        root_dir_record = vd.root_directory_record()
        root_dir_record.new_extent_loc = current_extent
        log_block_size = vd.log_block_size
        # Equivalent to utils.ceiling_div(root_dir_record.data_length, log_block_size), but faster
        current_extent += -(-root_dir_record.data_length // log_block_size)

        rr_cont_extent = None
        rr_cont_offset = 0

        child_link_recs = []
        parent_link_recs = []

        # Walk through the list, assigning extents to all of the directories.
        file_list = []
        dirs = collections.deque([root_dir_record])
        while dirs:
            dir_record = dirs.popleft()

            # Some micro-optimizations to avoid repeating lookups below
            dir_record_rock_ridge = dir_record.rock_ridge
            dir_record_parent = dir_record.parent
            dir_record_isdir = dir_record.isdir
            dir_record_file_ident = dir_record.file_ident

            if dir_record.is_root:
                # The root directory record doesn't need an extent assigned,
                # so just add its children to the list and continue on
                dirs.extend(dir_record.children)
                continue

            # Equivalent to dir_record.is_dot(), but faster.
            if dir_record_isdir and dir_record_file_ident == b'\x00':
                dir_record.new_extent_loc = dir_record_parent._extent_location()
            # Equivalent to dir_record.is_dotdot(), but faster.
            elif dir_record_isdir and dir_record_file_ident == b'\x01':
                if dir_record_parent.is_root:
                    # Special case of the root directory record.  In this
                    # case, we assume that the dot record has already been
                    # added, and is the one before us.  We set the dotdot
                    # extent location to the same as the dot one.
                    dir_record.new_extent_loc = dir_record_parent._extent_location()
                else:
                    dir_record.new_extent_loc = dir_record_parent.parent._extent_location()
                if dir_record_rock_ridge is not None and dir_record_rock_ridge.parent_link is not None:
                    parent_link_recs.append(dir_record)
                if dir_record_parent.rock_ridge is not None:
                    if dir_record_parent.parent.is_root:
                        dir_record_rock_ridge.copy_file_links(dir_record_parent.parent.children[0].rock_ridge)
                    else:
                        dir_record_rock_ridge.copy_file_links(dir_record_parent.parent.rock_ridge)
            else:
                if dir_record_rock_ridge is not None and dir_record_rock_ridge.child_link is not None:
                    child_link_recs.append(dir_record)
                if dir_record_isdir:
                    dir_record.new_extent_loc = current_extent
                    # Equivalent to utils.ceiling_div(dir_record.data_length, log_block_size), but faster
                    if dir_record_rock_ridge is None or not dir_record_rock_ridge.has_child_link_record():
                        current_extent += -(-dir_record.data_length // log_block_size)
                    dirs.extend(dir_record.children)
                else:
                    file_list.append(dir_record)
                if dir_record_rock_ridge is not None and dir_record_rock_ridge.ce_record is not None:
                    rr_cont_len = dir_record_rock_ridge.ce_record.continuation_entry.length()
                    if rr_cont_extent is None or ((log_block_size - rr_cont_offset) < rr_cont_len):
                        dir_record_rock_ridge.ce_record.continuation_entry.new_extent_loc = current_extent
                        dir_record_rock_ridge.ce_record.continuation_entry.continue_offset = 0
                        rr_cont_extent = current_extent
                        rr_cont_offset = rr_cont_len
                        current_extent += 1
                    else:
                        dir_record_rock_ridge.ce_record.continuation_entry.new_extent_loc = rr_cont_extent
                        dir_record_rock_ridge.ce_record.continuation_entry.continue_offset = rr_cont_offset
                        rr_cont_offset += rr_cont_len

        # After we have reshuffled the extents, we need to update the rock ridge
        # links.
        for ch in child_link_recs:
            ch.rock_ridge.update_child_link()

        for p in parent_link_recs:
            p.rock_ridge.update_parent_link()

        # After we have reshuffled the extents we need to update the ptr
        # records.
        vd.update_ptr_records()

        return current_extent,file_list

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

        # Save off an extent for the version descriptor
        self.version_vd.new_extent_loc = current_extent
        current_extent += 1

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

        current_extent,pvd_files = self._reassign_vd_dirrecord_extents(self.pvd, current_extent)

        joliet_files = []
        if self.joliet_vd is not None:
            current_extent,joliet_files = self._reassign_vd_dirrecord_extents(self.joliet_vd, current_extent)

        # The rock ridge "ER" sector must be after all of the directory
        # entries but before the file contents.
        if self.rock_ridge is not None:
            self.pvd.root_directory_record().children[0].rock_ridge.ce_record.continuation_entry.new_extent_loc = current_extent
            current_extent += 1

        linked_records = {}
        if self.eltorito_boot_catalog is not None:
            self.eltorito_boot_catalog.update_catalog_extent(current_extent)
            current_extent += 1
            for rec in self.eltorito_boot_catalog.dirrecord.linked_records:
                linked_records[id(rec)] = True

            self.eltorito_boot_catalog.update_initial_entry_extent(current_extent)
            for rec in self.eltorito_boot_catalog.initial_entry.dirrecord.linked_records:
                linked_records[id(rec)] = True

            current_extent += -(-self.eltorito_boot_catalog.initial_entry.dirrecord.data_length // self.pvd.log_block_size)

            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    entry.update_extent(current_extent)
                    current_extent += -(-entry.dirrecord.data_length // self.pvd.log_block_size)

        for child in pvd_files + joliet_files:
            if self.eltorito_boot_catalog is not None:
                if self.eltorito_boot_catalog.contains_child(child):
                    continue

            if id(child) in linked_records:
                # We've already assigned an extent because it was linked to an
                # earlier entry.
                continue

            child.new_extent_loc = current_extent
            for rec in child.linked_records:
                rec.new_extent_loc = current_extent
                linked_records[id(rec)] = True

            # Equivalent to utils.ceiling_div(child.data_length, self.pvd.log_block_size), but faster
            current_extent += -(-child.data_length // self.pvd.log_block_size)

        if self.enhanced_vd is not None:
            self.enhanced_vd.root_directory_record().new_extent_loc = self.pvd.root_directory_record().new_extent_loc

    def _add_child_to_dr(self, parent, child, logical_block_size):
        '''
        An internal method to add a child to a directory record, expanding the
        space in the Volume Descriptor(s) if necessary.

        Parameters:
         parent - The parent of the new child.
         child - The new child.
         logical_block_size - The size of one logical block.
        Returns:
         Nothing.
        '''
        if parent.add_child(child, logical_block_size):
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())
            if self.joliet_vd is not None:
                self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

    def _remove_child_from_dr(self, child, index, logical_block_size):
        '''
        An internal method to remove a child from a directory record, shrinking
        the space in the Volume Descriptor if necessary.

        Parameters:
         child - The new child.
         index - The index of the child into the parent's child array.
         logical_block_size - The size of one logical block.
        Returns:
         Nothing.
        '''
        if child.parent.remove_child(child, index, logical_block_size):
            for pvd in self.pvds:
                pvd.remove_from_space_size(pvd.logical_block_size())
            if self.joliet_vd is not None:
                self.joliet_vd.remove_from_space_size(self.joliet_vd.logical_block_size())

    def _find_or_create_rr_moved(self):
        '''
        An internal method to find the /RR_MOVED directory on the ISO.  If it
        already exists, the directory record to it is returned.  If it doesn't
        yet exist, it is created and the directory record to it is returned.

        Parameters:
         None.
        Returns:
         The directory record entry matching the rr_moved directory.
        '''
        # Before we attempt this, check to see if there is already one.
        try:
            rr_moved_parent,index_unused = self._find_record(self.pvd, b"/RR_MOVED")
            found_rr_moved = True
        except pycdlibexception.PyCdlibException:
            found_rr_moved = False

        if found_rr_moved:
            # Found an existing rr_moved, return it.
            return rr_moved_parent

        # No rr_moved found, so we have to create it.
        rec = dr.DirectoryRecord()
        rec.new_dir(b'RR_MOVED', self.pvd.root_directory_record(),
                    self.pvd.sequence_number(), self.rock_ridge, b'rr_moved',
                    self.pvd.logical_block_size(), False, False, self.xa)
        self._add_child_to_dr(self.pvd.root_directory_record(), rec, self.pvd.logical_block_size())

        dot = dr.DirectoryRecord()
        dot.new_dot(rec, self.pvd.sequence_number(), self.rock_ridge,
                    self.pvd.logical_block_size(), self.xa)
        self._add_child_to_dr(rec, dot, self.pvd.logical_block_size())

        dotdot = dr.DirectoryRecord()
        dotdot.new_dotdot(rec, self.pvd.sequence_number(), self.rock_ridge,
                          self.pvd.logical_block_size(), False, self.xa)
        self._add_child_to_dr(rec, dotdot, self.pvd.logical_block_size())

        for pvd in self.pvds:
            pvd.add_to_ptr(path_table_record.PathTableRecord.record_length(len("RR_MOVED")))
        for pvd in self.pvds:
            pvd.add_to_space_size(pvd.logical_block_size())

        # We always need to add an entry to the path table record
        ptr = path_table_record.PathTableRecord()
        ptr.new_dir(b"RR_MOVED", rec, self.pvd.root_directory_record().ptr.directory_num, rec.parent.ptr.depth + 1)
        rec.set_ptr(ptr)

        self.pvd.add_path_table_record(ptr)

        self.pvd.update_ptr_dirnums()

        return rec

    def _find_record_by_extent(self, vd, extent):
        '''
        An internal method to find a directory record given an extent.

        Parameters:
         vd - The volume descriptor to look for the record in.
         extent - The extent to find the record for.
        Returns:
         A tuple containing a directory record entry representing the entry on
         the ISO and the index of that entry into the parent's child list.
        '''
        # Search through the filesystem, looking for the file that matches the
        # extent that the boot catalog lives at.
        dirs = [vd.root_directory_record()]
        while dirs:
            curr = dirs.pop(0)
            for index,child in enumerate(curr.children):
                # This is equivalent to child.is_dot() or child.is_dotdot(),
                # but turns out to be much faster.
                if child.file_ident in [b'\x00', b'\x01']:
                    continue

                if child._extent_location() == extent:
                    return child,index
                if child.is_dir():
                    dirs.append(child)

        raise pycdlibexception.PyCdlibException("Could not find file with specified extent!")

    def _find_child_link_by_extent(self, vd, extent):
        '''
        An internal method to find a directory record with a child link extent
        matching the passed in value.

        Parameters:
         vd - The volume descriptor to look for the record in.
         extent - The extent to find the record for.
        Returns:
         A tuple containing a directory record entry representing the entry on
         the ISO and the index of that entry into the parent's child list.
        '''
        # Search through the filesystem, looking for the file that matches the
        # extent that the boot catalog lives at.
        dirs = [vd.root_directory_record()]
        while dirs:
            curr = dirs.pop(0)
            for index,child in enumerate(curr.children):
                # This is equivalent to child.is_dot() or child.is_dotdot(),
                # but turns out to be much faster.
                if child.file_ident in [b'\x00', b'\x01']:
                    continue

                if child.is_dir():
                    dirs.append(child)
                else:
                    if child.rock_ridge is not None and child.rock_ridge.has_child_link_record():
                        cl_num = child.rock_ridge.child_link_block_num()
                        if cl_num == extent:
                            return child,index

        raise pycdlibexception.PyCdlibException("Could not find file with specified extent!")

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
            block = block.ljust(2048, b"\x00")
            i = 0
            if curr_sector == 0:
                # The first 64 bytes are not included in the checksum, so skip
                # them here.
                i = 64
            while i < len(block):
                tmp, = struct.unpack_from("=L", block[:i+4], i)
                csum += tmp
                csum = csum & 0xffffffff
                i += 4

            curr_sector += 1

        return csum

    def _check_for_eltorito_boot_info_table(self, rec):
        '''
        An internal method to check a boot directory record to see if it has
        an El Torito Boot Info Table embedded inside of it.

        Parameters:
         rec - The directory record to check for a Boot Info Table.
        Returns:
         Nothing.
        '''
        orig = self.cdfp.tell()
        data_fp,data_len = rec.open_data(self.pvd.logical_block_size())
        data_fp.seek(8, 1)
        bi_table = eltorito.EltoritoBootInfoTable()
        bi_table.parse(data_fp.read(eltorito.EltoritoBootInfoTable.header_length()), rec)

        if bi_table.pvd_extent == self.pvd.extent_location() and bi_table.rec_extent == rec.extent_location():
            data_fp.seek(-24, 1)
            # OK, the rest of the stuff checks out; do a final
            # check to make sure the checksum is reasonable.
            csum = self._calculate_eltorito_boot_info_table_csum(data_fp, data_len)

            if csum == bi_table.csum:
                rec.boot_info_table = bi_table

        self.cdfp.seek(orig)

    def _check_rr_name(self, rr_name):
        '''
        An internal method to check whether this ISO requires or does not
        require a RockRidge path.

        Parameters:
         rr_name - The RockRidge name.
        Returns:
         Nothing.
        '''
        if self.rock_ridge is not None:
            if rr_name is None:
                raise pycdlibexception.PyCdlibException("A rock ridge name must be passed for a rock-ridge ISO")

            if rr_name.count('/') != 0:
                raise pycdlibexception.PyCdlibException("A rock ridge name must be relative")

            return rr_name.encode('utf-8')
        else:
            if rr_name is not None:
                raise pycdlibexception.PyCdlibException("A rock ridge name can only be specified for a rock-ridge ISO")

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
                raise pycdlibexception.PyCdlibException("A Joliet path must be passed for a Joliet ISO")
            tmp_path = utils.normpath(joliet_path)
        else:
            if joliet_path is not None:
                raise pycdlibexception.PyCdlibException("A Joliet path can only be specified for a Joliet ISO")

        return tmp_path

    def _joliet_name_and_parent_from_path(self, joliet_path):
        '''
        An internal method to find the parent directory record and name from
        the Joliet volume descriptor.  If the parent is found, return the parent
        directory record object and the relative path of the original path.

        Parameters:
         joliet_path - The absolute Joliet path to the entry on the ISO.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''

        (joliet_name, joliet_parent) = self._name_and_parent_from_path(self.joliet_vd, joliet_path, 'utf-16_be')

        if len(joliet_name) > 64:
            raise pycdlibexception.PyCdlibException("Joliet names can be a maximum of 64 characters")

        joliet_name = joliet_name.decode('utf-8').encode('utf-16_be')

        return joliet_name,joliet_parent

########################### PUBLIC API #####################################
    def __init__(self):
        self._initialize()

    def new(self, interchange_level=1, sys_ident="", vol_ident="", set_size=1,
            seqnum=1, log_block_size=2048, vol_set_ident=" ", pub_ident_str="",
            preparer_ident_str="",
            app_ident_str="PyCdlib (C) 2015-2016 Chris Lalancette",
            copyright_file="", abstract_file="", bibli_file="",
            vol_expire_date=None, app_use="", joliet=False, rock_ridge=None,
            xa=False):
        '''
        Create a new ISO from scratch.

        Parameters:
         interchange_level - The ISO9660 interchange level to use; this dictates
                             the rules on the names of files.  Set to 1 (the most
                             conservative) by default.
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
         joliet - A boolean which controls whether to make this a Joliet ISO or not;
                  the default is False.
         rock_ridge - Whether to make this ISO have the Rock Ridge extensions or
                      not.  The default value of None does not add Rock Ridge
                      extensions.  A string value of "1.09" adds Rock Ridge
                      version 1.09 to the ISO.  A string value of "1.12" adds
                      Rock Ridge version 1.12 to the ISO.  If unsure, pass
                      "1.09"; this will have maximum compatibility.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("This object already has an ISO; either close it or create a new object")

        if interchange_level < 1 or interchange_level > 4:
            raise pycdlibexception.PyCdlibException("Invalid interchange level (must be between 1 and 4)")

        if rock_ridge is not None and rock_ridge != "1.09" and rock_ridge != "1.12":
            raise pycdlibexception.PyCdlibException("Rock Ridge value must be None (no Rock Ridge), 1.09, or 1.12")

        self.interchange_level = interchange_level

        self.xa = xa

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

        pvd = headervd.PrimaryVolumeDescriptor()
        pvd.new(0, sys_ident, vol_ident, set_size, seqnum, log_block_size,
                vol_set_ident, pub_ident_str, preparer_ident_str,
                app_ident_str, copyright_file, abstract_file, bibli_file,
                vol_expire_date, app_use, xa, 1, b'')
        self.pvds.append(pvd)
        self.pvd = self.pvds[0]

        # Now that we have the PVD, make the root path table record.
        ptr = path_table_record.PathTableRecord()
        ptr.new_root(self.pvd.root_directory_record())
        self.pvd.add_path_table_record(ptr)
        self.pvd.root_directory_record().set_ptr(ptr)

        self.svds = []

        self.enhanced_vd = None
        if self.interchange_level == 4:
            svd = headervd.SupplementaryVolumeDescriptor()
            svd.new(0, sys_ident, vol_ident, set_size, seqnum, log_block_size,
                    vol_set_ident, pub_ident_str, preparer_ident_str,
                    app_ident_str, copyright_file, abstract_file, bibli_file,
                    vol_expire_date, app_use, xa, 2, b'')
            self.svds.append(svd)

            for pvd in self.pvds:
                pvd.add_to_space_size(svd.logical_block_size())
            svd.add_to_space_size(svd.logical_block_size())

            self.enhanced_vd = svd

        self.joliet_vd = None
        if joliet:
            # If the user requested Joliet, make the SVD to represent it here.
            svd = headervd.SupplementaryVolumeDescriptor()
            svd.new(0, sys_ident, vol_ident, set_size, seqnum, log_block_size,
                    vol_set_ident, pub_ident_str, preparer_ident_str, app_ident_str,
                    copyright_file, abstract_file,
                    bibli_file, vol_expire_date, app_use, xa, 1, b'%/E')
            self.svds.append(svd)
            self.joliet_vd = svd

            ptr = path_table_record.PathTableRecord()
            ptr.new_root(svd.root_directory_record())
            svd.add_path_table_record(ptr)
            svd.root_directory_record().set_ptr(ptr)

            # Make the directory entries for dot and dotdot.
            dot = dr.DirectoryRecord()
            dot.new_dot(svd.root_directory_record(), svd.sequence_number(),
                        None, svd.logical_block_size(), False)
            self._add_child_to_dr(svd.root_directory_record(), dot, svd.logical_block_size())

            dotdot = dr.DirectoryRecord()
            dotdot.new_dotdot(svd.root_directory_record(),
                              svd.sequence_number(), None,
                              svd.logical_block_size(), False, False)
            self._add_child_to_dr(svd.root_directory_record(), dotdot, svd.logical_block_size())

            additional_size = svd.logical_block_size() + 2*svd.logical_block_size() + 2*svd.logical_block_size() + svd.logical_block_size()
            # Now that we have added joliet, we need to add the new space to the
            # PVD.  Here, we add one extent for the SVD itself, 2 for the little
            # endian path table records, 2 for the big endian path table
            # records, and one for the root directory record.
            for pvd in self.pvds:
                pvd.add_to_space_size(additional_size)
            # And we add the same amount of space to the SVD.
            svd.add_to_space_size(additional_size)
            if self.enhanced_vd is not None:
                svd.add_to_space_size(self.pvd.logical_block_size())

        # Also make the volume descriptor set terminator.
        vdst = headervd.VolumeDescriptorSetTerminator()
        vdst.new()
        self.vdsts = [vdst]
        for pvd in self.pvds:
            pvd.add_to_space_size(pvd.logical_block_size())
        if self.joliet_vd is not None:
            self.joliet_vd.add_to_space_size(self.pvd.logical_block_size())

        self.version_vd = headervd.VersionVolumeDescriptor()
        self.version_vd.new()
        for pvd in self.pvds:
            pvd.add_to_space_size(pvd.logical_block_size())

        if self.joliet_vd is not None:
            self.joliet_vd.add_to_space_size(self.pvd.logical_block_size())

        # Finally, make the directory entries for dot and dotdot.
        dot = dr.DirectoryRecord()
        dot.new_dot(self.pvd.root_directory_record(), self.pvd.sequence_number(), rock_ridge, self.pvd.logical_block_size(), self.xa)
        self._add_child_to_dr(self.pvd.root_directory_record(), dot, self.pvd.logical_block_size())

        dotdot = dr.DirectoryRecord()
        dotdot.new_dotdot(self.pvd.root_directory_record(), self.pvd.sequence_number(), rock_ridge, self.pvd.logical_block_size(), False, self.xa)
        self._add_child_to_dr(self.pvd.root_directory_record(), dotdot, self.pvd.logical_block_size())

        self.rock_ridge = rock_ridge
        if self.rock_ridge is not None:
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())
            if self.joliet_vd is not None:
                self.joliet_vd.add_to_space_size(self.pvd.logical_block_size())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

        self.initialized = True

    def open(self, filename):
        '''
        Open up an existing ISO for inspection and modification.

        Parameters:
         filename - The filename containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("This object already has an ISO; either close it or create a new object")

        fp = open(filename, 'r+b')
        self.managing_fp = True
        try:
            self.open_fp(fp)
        except:
            fp.close()
            raise

    def open_fp(self, fp):
        '''
        Open up an existing ISO for inspection and modification.  Note that the
        file object passed in here must stay open for the lifetime of this
        object, as the PyCdlib class uses it internally to do writing and reading
        operations.

        Parameters:
         fp - The file object containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("This object already has an ISO; either close it or create a new object")

        self.cdfp = fp

        # Get the Primary Volume Descriptor (pvd), the set of Supplementary
        # Volume Descriptors (svds), the set of Volume Partition
        # Descriptors (vpds), the set of Boot Records (brs), and the set of
        # Volume Descriptor Set Terminators (vdsts)
        self._parse_volume_descriptors()

        old = self.cdfp.tell()
        self.cdfp.seek(0)
        mbr = self.cdfp.read(512)
        if mbr[0:2] == b'\x33\xed':
            # All isolinux isohdpfx.bin files start with 0x33 0xed (the x86
            # instruction for xor %bp, %bp).  Therefore, if we see that we know
            # we have a valid isohybrid, so parse that.
            self.isohybrid_mbr = isohybrid.IsoHybrid()
            self.isohybrid_mbr.parse(mbr)
        self.cdfp.seek(old)

        if self.pvd.application_use[141:149] == b"CD-XA001":
            self.xa = True

        for br in self.brs:
            self._check_and_parse_eltorito(br, self.pvd.logical_block_size())

        # ISOs created with genisoimage all have a "version" volume descriptor.
        # However, this particular volume descriptor doesn't appear to have
        # any specification, and is in a weird place in the ISO (a volume
        # descriptor *after* the VDST).  ISOs not created with genisoimage may
        # or may not have it, but because it doesn't have any sort of regular
        # structure, we can't tell.  Thus, we *always* create one for the ISO to
        # be opened.  If it isn't used, it will be overwritten with other data,
        # and if any changes are made to the ISO, then we'll make a (useless)
        # version volume descriptor, which shouldn't hurt anything.
        self.version_vd = headervd.VersionVolumeDescriptor()
        self.version_vd.parse(self.vdsts[0].extent_location() + 1)

        # Now that we have the PVD, parse the Path Tables according to Ecma-119
        # section 9.4.  What we really want is a single representation of the
        # path table records, so we only place the little endian path table
        # records into the PVD class.  However, we want to ensure that the
        # big endian versions agree with the little endian ones (to make sure
        # it is a valid ISO).  To do this we collect the big endian records
        # into a sorted list (to mimic what the list is stored as in the PVD),
        # and then compare them at the end.

        # Little Endian first
        self._parse_path_table(self.pvd, self.pvd.path_table_location_le,
                               "little")

        # Big Endian next.
        self.tmp_be_path_table_records = []
        self._parse_path_table(self.pvd, self.pvd.path_table_location_be, "big")

        for index,ptr in enumerate(self.pvd.path_table_records):
            if not ptr.equal_to_be(self.tmp_be_path_table_records[index]):
                raise pycdlibexception.PyCdlibException("Little-endian and big-endian path table records do not agree")

        # OK, so now that we have the PVD, we start at its root directory
        # record and find all of the files
        self.interchange_level = self._walk_directories(self.pvd, True)

        # On El Torito ISOs, after we have walked the directories we look
        # to see if all of the entries in El Torito have corresponding
        # directory records.  If they don't, then it may be the case that
        # the El Torito bits of the system are "hidden" or "unlinked",
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
            if self.eltorito_boot_catalog.dirrecord is None:
                rec = dr.DirectoryRecord()
                rec.parse_hidden(self.cdfp,
                                 self.pvd.logical_block_size(),
                                 self.eltorito_boot_catalog.extent_location(),
                                 self.pvd.root_directory_record(),
                                 self.pvd.sequence_number())
                self.eltorito_boot_catalog.dirrecord = rec

            if self.eltorito_boot_catalog.initial_entry.dirrecord is None:
                rec = dr.DirectoryRecord()
                rec.parse_hidden(self.cdfp,
                                 self.eltorito_boot_catalog.initial_entry.length(),
                                 self.eltorito_boot_catalog.initial_entry.get_rba(),
                                 self.pvd.root_directory_record(),
                                 self.pvd.sequence_number())
                self.eltorito_boot_catalog.initial_entry.dirrecord = rec

            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    if entry.dirrecord is None:
                        rec = dr.DirectoryRecord()
                        rec.parse_hidden(self.cdfp,
                                         entry.length(),
                                         entry.get_rba(),
                                         self.pvd.root_directory_record(),
                                         self.pvd.sequence_number())
                        entry.dirrecord = rec

            # Now that everything has a dirrecord, see if we have a boot
            # info table.
            self._check_for_eltorito_boot_info_table(self.eltorito_boot_catalog.initial_entry.dirrecord)
            for sec in self.eltorito_boot_catalog.sections:
                for entry in sec.section_entries:
                    self._check_for_eltorito_boot_info_table(entry.dirrecord)

        # The PVD is finished.  Now look to see if we need to parse the SVD.
        self.joliet_vd = None
        self.enhanced_vd = None
        for svd in self.svds:
            if (svd.flags & 0x1) == 0 and svd.escape_sequences[:3] in [b'%/*', b'%/C', b'%/E']:
                if self.joliet_vd is not None:
                    raise pycdlibexception.PyCdlibException("Only a single Joliet SVD is supported")

                self.joliet_vd = svd

                self._parse_path_table(svd, svd.path_table_location_le,
                                       "little")

                self.tmp_be_path_table_records = []
                self._parse_path_table(svd, svd.path_table_location_be, "big")

                for index,ptr in enumerate(svd.path_table_records):
                    be_record = self.tmp_be_path_table_records[index]
                    if not ptr.equal_to_be(be_record):
                        raise pycdlibexception.PyCdlibException("Joliet Little-endian and big-endian path table records do not agree")

                self._walk_directories(svd, False)
            elif svd.version == 2 and svd.file_structure_version == 2:
                if self.enhanced_vd is not None:
                    raise pycdlibexception.PyCdlibException("Only a single enhanced VD is supported")
                self.enhanced_vd = svd

        self.initialized = True

    def get_and_write(self, iso_path, local_path, blocksize=8192):
        '''
        Fetch a single file from the ISO and write it out to the specified
        file.  Note that this will overwrite the contents of the local file if
        it already exists.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         outfp - The local filename to write the contents to.
         blocksize - The blocksize to use when copying data; the default is 8192.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        with open(local_path, 'wb') as fp:
            self.get_and_write_fp(iso_path, fp, blocksize)

    def get_and_write_fp(self, iso_path, outfp, blocksize=8192):
        '''
        Fetch a single file from the ISO and write it out to the file object.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         outfp - The file object to write data to.
         blocksize - The blocksize to use when copying data; the default is 8192.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        iso_path = utils.normpath(iso_path)

        try_iso9660 = True
        if self.joliet_vd is not None:
            try:
                found_record,index_unused = self._find_record(self.joliet_vd, iso_path, 'utf-16_be')
                try_iso9660 = False
            except pycdlibexception.PyCdlibException:
                pass

        if try_iso9660:
            found_record,index_unused = self._find_record(self.pvd, iso_path)
            if found_record.rock_ridge is not None:
                if found_record.rock_ridge.is_symlink():
                    # If this Rock Ridge record is a symlink, it has no data
                    # associated with it, so it makes no sense to try and get
                    # the data.  In theory, we could follow the symlink to the
                    # appropriate place and get the data of the thing it points
                    # to.  However, the symlinks are allowed to point *outside*
                    # of this ISO, so it is really not clear that this is
                    # something we want to do.  For now we make the user follow
                    # the symlink themselves if they want to get the data.  We
                    # can revisit this decision in the future if we need to.
                    raise pycdlibexception.PyCdlibException("Symlinks have no data associated with them")

        data_fp,data_length = found_record.open_data(self.pvd.logical_block_size())

        # Here we copy the data into the output file descriptor.  If a boot
        # info table is present, we overlay the table over bytes 8-64 of the
        # file.  Note, however, that we never return more bytes than the length
        # of the file, so the boot info table may get truncated.
        if found_record.boot_info_table is not None:
            header_len = min(data_length, 8)
            outfp.write(data_fp.read(header_len))
            data_length -= header_len
            if data_length > 0:
                rec = found_record.boot_info_table.record()
                table_len = min(data_length, len(rec))
                outfp.write(rec[:table_len])
                data_length -= table_len
                if data_length > 0:
                    data_fp.seek(len(rec), 1)
                    utils.copy_data(data_length, blocksize, data_fp, outfp)
        else:
            utils.copy_data(data_length, blocksize, data_fp, outfp)

    def write(self, filename, blocksize=8192, progress_cb=None):
        '''
        Write a properly formatted ISO out to the filename passed in.  This
        also goes by the name of "mastering".

        Parameters:
         filename - The filename to write the data to.
         blocksize - The blocksize to use when copying data; set to 8192 by default.
         progress_cb - If not None, a function to call as the write call does its
                       work.  The callback function must have a signature of:
                       def func(done, total).
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        with open(filename, 'wb') as fp:
            self.write_fp(fp, blocksize, progress_cb)

    def _output_directory_record(self, outfp, blocksize, child):
        '''
        Internal method to write a directory record entry out.

        Parameters:
         outfp - The file object to write the data to.
         blocksize - The blocksize to use when writing the data out.
         child - The directory record to write.
        Returns:
         The total number of bytes written out.
        '''
        data_fp,data_length = child.open_data(self.pvd.logical_block_size())
        outfp.seek(child.extent_location() * self.pvd.logical_block_size())
        tmp_start = outfp.tell()
        utils.copy_data(data_length, blocksize, data_fp, outfp)
        outfp.write(pad(data_length, self.pvd.logical_block_size()))
        # If this file is being used as a bootfile, and the user
        # requested that the boot info table be patched into it,
        # we patch the boot info table at offset 8 here.
        if child.boot_info_table is not None:
            old = outfp.tell()
            outfp.seek(tmp_start + 8)
            outfp.write(child.boot_info_table.record())
            outfp.seek(old)
        return outfp.tell() - tmp_start

    def write_fp(self, outfp, blocksize=8192, progress_cb=None):
        '''
        Write a properly formatted ISO out to the file object passed in.  This
        also goes by the name of "mastering".

        Parameters:
         outfp - The file object to write the data to.
         blocksize - The blocksize to use when copying data; set to 8192 by default.
         progress_cb - If not None, a function to call as the write call does its
                       work.  The callback function must have a signature of:
                       def func(done, total).
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        outfp.seek(0)

        class Progress(object):
            '''
            An inner class to deal with progress.
            '''
            def __init__(self, total):
                self.done = 0
                self.total = total
            def call(self, length):
                '''
                Add the length to done, then call progress_cb if it is not None.
                '''
                self.done += length
                if progress_cb is not None:
                    progress_cb(self.done, self.total)
            def finish(self):
                '''
                If the progress_cb is not None, call progress_cb with the
                final total.
                '''
                if progress_cb is not None:
                    progress_cb(self.total, self.total)

        progress = Progress(self.pvd.space_size * self.pvd.logical_block_size())
        progress.call(0)

        if self.isohybrid_mbr is not None:
            outfp.write(self.isohybrid_mbr.record(self.pvd.space_size * self.pvd.logical_block_size()))

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.  Thus
        # we skip the first 16 sectors.
        outfp.seek(self.pvd.extent_location() * self.pvd.logical_block_size())

        # First write out the PVD.
        for pvd in self.pvds:
            rec = pvd.record()
            outfp.write(rec)
            progress.call(len(rec))

        # Next write out the boot records.
        for br in self.brs:
            outfp.seek(br.extent_location() * self.pvd.logical_block_size())
            rec = br.record()
            outfp.write(rec)
            progress.call(len(rec))

        # Next we write out the SVDs.
        for svd in self.svds:
            outfp.seek(svd.extent_location() * self.pvd.logical_block_size())
            rec = svd.record()
            outfp.write(rec)
            progress.call(len(rec))

        # Next we write out the Volume Descriptor Terminators.
        for vdst in self.vdsts:
            outfp.seek(vdst.extent_location() * self.pvd.logical_block_size())
            rec = vdst.record()
            outfp.write(rec)
            progress.call(len(rec))

        # Next we write out the version block.
        # FIXME: In genisoimage, write.c:vers_write(), this "version descriptor"
        # is written out with the exact command line used to create the ISO
        # (if in debug mode, otherwise it is all zero).  However, there is no
        # mention of this in any of the specifications I've read so far.  Where
        # does it come from?
        outfp.seek(self.version_vd.extent_location() * self.pvd.logical_block_size())
        rec = self.version_vd.record(self.pvd.logical_block_size())
        outfp.write(rec)
        progress.call(len(rec))

        # Next we write out the Path Table Records, both in Little Endian and
        # Big-Endian formats.  We do this within the same loop, seeking back
        # and forth as necessary.
        le_offset = 0
        be_offset = 0
        for record in self.pvd.path_table_records:
            outfp.seek(self.pvd.path_table_location_le * self.pvd.logical_block_size() + le_offset)
            ret = record.record_little_endian()
            outfp.write(ret)
            le_offset += len(ret)

            outfp.seek(self.pvd.path_table_location_be * self.pvd.logical_block_size() + be_offset)
            ret = record.record_big_endian()
            outfp.write(ret)
            be_offset += len(ret)

        # Once we are finished with the loop, we need to pad out the Big
        # Endian version.  The Little Endian one was already properly padded
        # by the mere fact that we wrote things for the Big Endian version
        # in the right place.
        outfp.write(pad(be_offset, 4096))
        progress.call(self.pvd.path_table_num_extents * 2 * self.pvd.logical_block_size())

        # Now we write out the path table records for any SVDs.
        if self.joliet_vd is not None:
            le_offset = 0
            be_offset = 0
            for record in self.joliet_vd.path_table_records:
                outfp.seek(self.joliet_vd.path_table_location_le * self.joliet_vd.logical_block_size() + le_offset)
                ret = record.record_little_endian()
                outfp.write(ret)
                le_offset += len(ret)

                outfp.seek(self.joliet_vd.path_table_location_be * self.joliet_vd.logical_block_size() + be_offset)
                ret = record.record_big_endian()
                outfp.write(ret)
                be_offset += len(ret)

            # Once we are finished with the loop, we need to pad out the Big
            # Endian version.  The Little Endian one was already properly padded
            # by the mere fact that we wrote things for the Big Endian version
            # in the right place.
            outfp.write(pad(be_offset, 4096))
            progress.call(self.joliet_vd.path_table_num_extents * 2 * self.joliet_vd.logical_block_size())

        if self.eltorito_boot_catalog is not None:
            outfp.seek(self.eltorito_boot_catalog.extent_location() * self.pvd.logical_block_size())
            rec = self.eltorito_boot_catalog.record()
            outfp.write(rec)
            progress.call(len(rec))

            if self.eltorito_boot_catalog.initial_entry.dirrecord.hidden:
                # If the initial entry is hidden, we have to make sure to write
                # it out, since it won't be done below.
                progress.call(self._output_directory_record(outfp, blocksize,
                                                            self.eltorito_boot_catalog.initial_entry.dirrecord))

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        dirs = collections.deque([self.pvd.root_directory_record()])
        while dirs:
            curr = dirs.popleft()
            curr_dirrecord_offset = 0
            if curr.is_dir():
                progress.call(curr.file_length())

            dir_extent = curr.extent_location()
            for child in curr.children:
                # No matter what type the child is, we need to first write out
                # the directory record entry.
                recstr = child.record()
                if (curr_dirrecord_offset + len(recstr)) > self.pvd.logical_block_size():
                    dir_extent += 1
                    curr_dirrecord_offset = 0
                outfp.seek(dir_extent * self.pvd.logical_block_size() + curr_dirrecord_offset)
                # Now write out the child
                outfp.write(recstr)
                curr_dirrecord_offset += len(recstr)

                if child.rock_ridge is not None and child.rock_ridge.ce_record is not None:
                    # The child has a continue block, so write it out here.
                    offset = child.rock_ridge.ce_record.continuation_entry.offset()
                    outfp.seek(child.rock_ridge.ce_record.continuation_entry.extent_location() * self.pvd.logical_block_size() + offset)
                    tmp_start = outfp.tell()
                    rec = child.rock_ridge.ce_record.continuation_entry.record()
                    outfp.write(rec)
                    if offset == 0:
                        outfp.write(pad(len(rec), self.pvd.logical_block_size()))
                        progress.call(outfp.tell() - tmp_start)

                if child.rock_ridge is not None and child.rock_ridge.has_child_link_record():
                    continue

                matches_boot_catalog = self.eltorito_boot_catalog is not None and self.eltorito_boot_catalog.dirrecord == child
                is_symlink = child.rock_ridge is not None and child.rock_ridge.is_symlink()
                if child.is_dir():
                    # If the child is a directory, and is not dot or dotdot, we
                    # want to descend into it to look at the children.
                    if not child.is_dot() and not child.is_dotdot():
                        dirs.append(child)
                    outfp.write(pad(outfp.tell(), self.pvd.logical_block_size()))
                elif child.data_length > 0 and child.target is None and not matches_boot_catalog and not is_symlink:
                    # If the child is a file, then we need to write the
                    # data to the output file.
                    progress.call(self._output_directory_record(outfp, blocksize, child))

        if self.joliet_vd is not None:
            dirs = collections.deque([self.joliet_vd.root_directory_record()])
            while dirs:
                curr = dirs.popleft()
                curr_dirrecord_offset = 0
                if curr.is_dir():
                    progress.call(curr.file_length())

                dir_extent = curr.extent_location()
                for child in curr.children:
                    # No matter what type the child is, we need to first write
                    # out the directory record entry.
                    recstr = child.record()
                    if (curr_dirrecord_offset + len(recstr)) > self.joliet_vd.logical_block_size():
                        dir_extent += 1
                        curr_dirrecord_offset = 0
                    outfp.seek(dir_extent * self.joliet_vd.logical_block_size() + curr_dirrecord_offset)
                    # Now write out the child
                    outfp.write(recstr)
                    curr_dirrecord_offset += len(recstr)

                    if child.is_dir():
                        # If the child is a directory, and is not dot or dotdot,
                        # we want to descend into it to look at the children.
                        if not child.is_dot() and not child.is_dotdot():
                            dirs.append(child)
                        outfp.write(pad(outfp.tell(), self.joliet_vd.logical_block_size()))

        # We need to pad out to the total size of the disk, in the case that
        # the last thing we wrote is shorter than a full block size.  We used
        # to use the truncate method to do this, but it turns out that not all
        # file-like objects allow you to use truncate to grow the file.  Thus,
        # we do it the old-fashioned way by seeking to the end of the object,
        # calculating the difference between the end and what we want, and then
        # manually writing zeros for padding.
        outfp.seek(0, os.SEEK_END)
        outfp.write(pad(outfp.tell(), self.pvd.space_size * self.pvd.logical_block_size()))

        if self.isohybrid_mbr is not None:
            outfp.seek(0, os.SEEK_END)
            outfp.write(self.isohybrid_mbr.record_padding(self.pvd.space_size * self.pvd.logical_block_size()))

        progress.finish()

    def add_fp(self, fp, length, iso_path, rr_name=None, joliet_path=None):
        '''
        Add a file to the ISO.  If the ISO contains Joliet or
        RockRidge, then a Joliet name and/or a RockRidge name must also be
        provided.  Note that the caller must ensure that the file remains open
        for the lifetime of the ISO object, as the PyCdlib class uses the file
        descriptor internally when writing (mastering) the ISO.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the data for the new file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        self._add_fp(fp, length, False, iso_path, rr_name, joliet_path)

    def add_file(self, filename, iso_path, rr_name=None, joliet_path=None):
        '''
        Add a file to the ISO.  If the ISO contains Joliet or
        RockRidge, then a Joliet name and/or a RockRidge name must also be
        provided.

        Parameters:
         filename - The filename to use for the data contents for the new file.
         length - The length of the data for the new file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        fp = open(filename, 'rb')
        try:
            length = os.fstat(fp.fileno()).st_size

            self._add_fp(fp, length, True, iso_path, rr_name, joliet_path)

            self.managing_dr_fps = True
        except:
            fp.close()
            raise

    def _add_fp(self, fp, length, manage_fp, iso_path, rr_name, joliet_path):
        '''
        An internal method to add a file to the ISO.  If the ISO contains
        Joliet and/or RockRidge, then a Joliet name and/or a RockRidge name must
        also be provided.  Note that the caller must ensure that the file
        remains open for the lifetime of the ISO object, as the PyCdlib class
        uses the file descriptor internally when writing (mastering) the ISO.

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
        Returns:
         Nothing.
        '''

        iso_path = utils.normpath(iso_path)

        rr_name = self._check_rr_name(rr_name)

        # We call _normalize_joliet_path here even though we aren't going to
        # use the result.  This is to ensure that we throw an exception when
        # a joliet_path is passed for a non-Joliet ISO.
        self._normalize_joliet_path(joliet_path)

        if self.rock_ridge is None:
            self._check_path_depth(iso_path)
        (name, parent) = self._name_and_parent_from_path(self.pvd, iso_path)

        check_iso9660_filename(name, self.interchange_level)

        rec = dr.DirectoryRecord()
        rec.new_fp(fp, manage_fp, length, name, parent,
                   self.pvd.sequence_number(), self.rock_ridge, rr_name,
                   self.xa)
        self._add_child_to_dr(parent, rec, self.pvd.logical_block_size())
        for pvd in self.pvds:
            pvd.add_to_space_size(length)

        if self.joliet_vd is not None:
            # If this is a Joliet ISO, then we can re-use add_hard_link to
            # do most of the work, and just remember to expand the space size
            # of the Joliet file descriptor.  We also explicitly do *not* call
            # reshuffle_extents(), since that is done in _add_hard_link for us.
            self._add_hard_link(iso_old_path=iso_path, joliet_new_path=joliet_path)
            self.joliet_vd.add_to_space_size(length)
        else:
            # If this is not a Joliet ISO, we have to explicitly call
            # reshuffle_extents ourselves.
            if self.enhanced_vd is not None:
                self.enhanced_vd.copy_sizes(self.pvd)

            self._reshuffle_extents()

        # This needs to be *after* reshuffle_extents() so that the continuation
        # entry offsets are computed properly.
        if rec.rock_ridge is not None and rec.rock_ridge.ce_record is not None and rec.rock_ridge.ce_record.continuation_entry.continue_offset == 0:
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())
            if self.joliet_vd is not None:
                self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

    def modify_file_in_place(self, fp, length, iso_path, rr_name=None, joliet_path=None):
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
            a file, this is usually easy since the new contents can typically
            be padded out with zeros or newlines to meet the requirement.  If
            using this API to grow a file, the new contents can only grow up to
            the next extent boundary.

        Unlike all other APIs in PyCdlib, this API actually modifies the
        originally opened on-disk file, so use it with caution.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the new data for the file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_name - The Rock Ridge name of the file destination on the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        if not self.cdfp.mode.startswith(('r+', 'w', 'a', 'rb+')):
            raise pycdlibexception.PyCdlibException("To modify a file in place, the original ISO must have been opened in a write mode (r+, w, or a')")

        iso_path = utils.normpath(iso_path)

        if bytes(bytearray([iso_path[0]])) != b'/':
            raise pycdlibexception.PyCdlibException("Must be a path starting with /")

        rr_name = self._check_rr_name(rr_name)

        joliet_path = self._normalize_joliet_path(joliet_path)

        child,index_unused = self._find_record(self.pvd, iso_path)

        old_num_extents = utils.ceiling_div(child.file_length(), self.pvd.logical_block_size())
        new_num_extents = utils.ceiling_div(length, self.pvd.logical_block_size())

        if old_num_extents != new_num_extents:
            raise pycdlibexception.PyCdlibException("When modifying a file in-place, the number of extents for a file cannot change!")

        if not child.is_file():
            raise pycdlibexception.PyCdlibException("Cannot modify a directory with modify_file_in_place")

        child.update_fp(fp, length)

        # Remove the old size from the PVD size
        for pvd in self.pvds:
            pvd.remove_from_space_size(child.file_length())
        # And add the new size to the PVD size
        for pvd in self.pvds:
            pvd.add_to_space_size(length)

        if self.joliet_vd is not None:
            joliet_child,joliet_index_unused = self._find_record(self.joliet_vd, joliet_path, 'utf-16_be')

            joliet_child.update_fp(fp, length)

            self.joliet_vd.remove_from_space_size(joliet_child.file_length())
            self.joliet_vd.add_to_space_size(length)

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        # If we made it here, we have successfully updated all of the in-memory
        # metadata.  Now we can go and modify the on-disk file.

        self.cdfp.seek(self.pvd.extent_location() * self.pvd.logical_block_size())

        # First write out the PVD.
        rec = self.pvd.record()
        self.cdfp.write(rec)

        # Write out the joliet VD
        if self.joliet_vd is not None:
            self.cdfp.seek(self.joliet_vd.extent_location() * self.pvd.logical_block_size())
            rec = self.joliet_vd.record()
            self.cdfp.write(rec)

        # Write out the enhanced VD
        if self.enhanced_vd is not None:
            self.cdfp.seek(self.enhanced_vd.extent_location() * self.pvd.logical_block_size())
            rec = self.enhanced_vd.record()
            self.cdfp.write(rec)

        # Write out the actual file contents
        data_fp,data_length = child.open_data(self.pvd.logical_block_size())
        self.cdfp.seek(child.extent_location() * self.pvd.logical_block_size())
        utils.copy_data(data_length, self.pvd.logical_block_size(), data_fp, self.cdfp)
        self.cdfp.write(pad(data_length, self.pvd.logical_block_size()))

        # Finally write out the directory record entry.
        dir_extent = child.parent.extent_location()
        curr_dirrecord_offset = 0
        for c in child.parent.children:
            recstr = c.record()
            if (curr_dirrecord_offset + len(recstr)) > self.pvd.logical_block_size():
                dir_extent += 1
                curr_dirrecord_offset = 0

            if c == child:
                self.cdfp.seek(dir_extent * self.pvd.logical_block_size() + curr_dirrecord_offset)
                # Now write out the child
                self.cdfp.write(recstr)
                break
            else:
                curr_dirrecord_offset += len(recstr)

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
        Once this API has been used, this API and add_hard_link() should be
        preferred over rm_file() and add_file(), respectively.

        Parameters:
         iso_old_path - The old path on the ISO9660 filesystem to link from.
         iso_new_path - The new path on the ISO9660 filesystem to link to.
         joliet_old_path - The old path on the Joliet filesystem to link from.
         joliet_new_path - The new path on the Joliet filesystem to link to.
         rr_name - The Rock Ridge name to use for the new file if this is a Rock Ridge ISO and thew new path is on the ISO9660 filesystem.
         boot_catalog_old - Use the El Torito boot catalog as the old path.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        self._add_hard_link(**kwargs)

    def _add_hard_link(self, **kwargs):
        '''
        Add a hard link to the ISO.  Hard links are alternate names for the
        same file contents that don't take up any additional space on the the
        ISO.  This API can be used to create hard links between two files on
        the ISO9660 filesystem, between two files on the Joliet filesystem, or
        between a file on the ISO9660 filesystem and the Joliet filesystem.
        In all cases, exactly one old path must be specified, and exactly one
        new path must be specified.

        Parameters:
         iso_old_path - The old path on the ISO9660 filesystem to link from.
         iso_new_path - The new path on the ISO9660 filesystem to link to.
         joliet_old_path - The old path on the Joliet filesystem to link from.
         joliet_new_path - The new path on the Joliet filesystem to link to.
         rr_name - The Rock Ridge name to use for the new file if this is a Rock Ridge ISO and thew new path is on the ISO9660 filesystem.
         boot_catalog_old - Use the El Torito boot catalog as the old path.
        Returns:
         Nothing.
        '''
        # Here, check that we have a valid combination.  We must have exactly
        # one source and exactly one target.
        num_old = 0
        num_new = 0
        iso_old_path = None
        iso_new_path = None
        joliet_old_path = None
        joliet_new_path = None
        rr_name = None
        boot_catalog_old = False
        for key in kwargs:
            if key == "iso_old_path":
                num_old += 1
                iso_old_path = utils.normpath(kwargs[key])
            elif key == "iso_new_path":
                num_new += 1
                iso_new_path = utils.normpath(kwargs[key])
                if self.rock_ridge is None:
                    self._check_path_depth(iso_new_path)
            elif key == "joliet_old_path":
                num_old += 1
                joliet_old_path = self._normalize_joliet_path(kwargs[key])
            elif key == "joliet_new_path":
                num_new += 1
                joliet_new_path = self._normalize_joliet_path(kwargs[key])
            elif key == "rr_name":
                rr_name = self._check_rr_name(kwargs[key])
            elif key == "boot_catalog_old":
                num_old += 1
                boot_catalog_old = True
                if self.eltorito_boot_catalog is None:
                    raise pycdlibexception.PyCdlibException("Attempting to make link to non-existent El Torito boot catalog")
            else:
                raise pycdlibexception.PyCdlibException("Unknown keyword %s" % (key))

        if num_old != 1:
            raise pycdlibexception.PyCdlibException("Exactly one old path must be specified")
        if num_new != 1:
            raise pycdlibexception.PyCdlibException("Exactly one new path must be specified")
        if self.rock_ridge is not None and iso_new_path is not None and rr_name is None:
            raise pycdlibexception.PyCdlibException("Rock Ridge name must be supplied for a Rock Ridge new path")

        # It would be nice to allow the addition of a link to the El Torito
        # Initial/Default Entry.  Unfortunately, the information we need for
        # a "hidden" Initial entry just doesn't exist on the ISO.  In
        # particular, we don't know the real size that the file should be, we
        # only know the number of emulated sectors (512 bytes) that it will be
        # loaded into.  Since the true length and the number of sectors are not
        # the same thing, we can't actually add a hard link.

        if iso_old_path is not None:
            # A link from a file on the ISO9660 filesystem...
            old_rec,old_index_unused = self._find_record(self.pvd, iso_old_path)
        elif joliet_old_path is not None:
            # A link from a file on the Joliet filesystem...
            old_rec,old_index_unused = self._find_record(self.joliet_vd, joliet_old_path, encoding='utf-16_be')
        elif boot_catalog_old:
            # A link from the El Torito boot catalog...
            old_rec = self.eltorito_boot_catalog.dirrecord
        else:
            # This should be impossible
            raise pycdlibexception.PyCdlibException("Internal error!")

        if iso_new_path is not None:
            # ... to another file on the ISO9660 filesystem.
            (new_name, new_parent) = self._name_and_parent_from_path(self.pvd, iso_new_path)
            vd = self.pvd
            rr = self.rock_ridge
            xa = self.xa
        elif joliet_new_path is not None:
            # ... to a file on the Joliet filesystem.
            (new_name, new_parent) = self._joliet_name_and_parent_from_path(joliet_new_path)
            vd = self.joliet_vd
            rr = None
            xa = False
        else:
            # This should be impossible
            raise pycdlibexception.PyCdlibException("Internal error!")

        new_rec = dr.DirectoryRecord()
        if old_rec.hidden:
            # In this case, the old entry was hidden.  Hidden entries are fairly
            # empty containers, so we are going to want to convert it to a
            # "real" entry, rather than adding a new link.
            new_rec.new_fp(old_rec.data_fp, old_rec.manage_fp,
                           old_rec.data_length, new_name, new_parent,
                           vd.sequence_number(), rr, rr_name, xa)
        else:
            # Otherwise, this is a link, so we want to just add a new link.
            new_rec.new_link(old_rec, old_rec.data_length, new_name, new_parent,
                             vd.sequence_number(), rr, rr_name, xa)
            old_rec.linked_records.append(new_rec)
            new_rec.linked_records.append(old_rec)

        self._add_child_to_dr(new_parent, new_rec, vd.logical_block_size())

        if boot_catalog_old:
            self.eltorito_boot_catalog.dirrecord = new_rec

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def rm_hard_link(self, iso_path=None, joliet_path=None):
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
         iso_path - The iso_path to remove the link.
         joliet_path - The joliet_path to remove the link.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path is not None and joliet_path is not None:
            raise pycdlibexception.PyCdlibException("Only one of iso_path or joliet_path arguments can be passed")

        if iso_path is not None:
            # OK, we are removing an ISO path.
            iso_path = utils.normpath(iso_path)

            rec,index = self._find_record(self.pvd, iso_path)

            logical_block_size = self.pvd.logical_block_size()

        elif joliet_path is not None:
            if self.joliet_vd is None:
                raise pycdlibexception.PyCdlibException("Cannot remove Joliet link from non-Joliet ISO")
            joliet_path = self._normalize_joliet_path(joliet_path)

            rec,index = self._find_record(self.joliet_vd, joliet_path, 'utf-16_be')
            logical_block_size = self.joliet_vd.logical_block_size()

        else:
            raise pycdlibexception.PyCdlibException("Either the iso_path or the joliet_path argument must be passed")

        if not rec.is_file():
            raise pycdlibexception.PyCdlibException("Cannot remove a directory with rm_hard_link (try rm_directory instead)")

        self._remove_child_from_dr(rec, index, logical_block_size)

        for link in rec.linked_records:
            tmp = []
            for inner in link.linked_records:
                if inner == rec:
                    continue
                tmp.append(inner)
            link.linked_records = tmp

        # We only remove the size of the child from the ISO if there are no
        # other references to this file on the ISO.
        links = len(rec.linked_records)
        if self.eltorito_boot_catalog is not None:
            if self.eltorito_boot_catalog.dirrecord.extent_location() == rec.extent_location() and links == 0:
                links += 1
                newrec = dr.DirectoryRecord()
                newrec.new_hidden_from_old(rec,
                                           self.eltorito_boot_catalog.extent_location(),
                                           self.pvd.root_directory_record(),
                                           self.pvd.sequence_number())
                self.eltorito_boot_catalog.dirrecord = newrec

            if self.eltorito_boot_catalog.initial_entry.dirrecord.extent_location() == rec.extent_location() and links == 0:
                links += 1
                newrec = dr.DirectoryRecord()
                newrec.new_hidden_from_old(rec,
                                           self.eltorito_boot_catalog.initial_entry.get_rba(),
                                           self.pvd.root_directory_record(),
                                           self.pvd.sequence_number())
                self.eltorito_boot_catalog.initial_entry.dirrecord = newrec

        if links == 0:
            for pvd in self.pvds:
                pvd.remove_from_space_size(rec.file_length())
            if self.joliet_vd is not None:
                self.joliet_vd.remove_from_space_size(rec.file_length())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def add_directory(self, iso_path, rr_name=None, joliet_path=None):
        '''
        Add a directory to the ISO.  If the ISO contains Joliet or RockRidge (or
        both), then a Joliet name and/or a RockRidge name must also be provided.

        Parameters:
         iso_path - The ISO9660 absolute path to use for the directory.
         rr_name - The Rock Ridge name to use for the directory.
         joliet_path - The Joliet absolute path to use for the directory.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        iso_path = utils.normpath(iso_path)

        rr_name = self._check_rr_name(rr_name)

        depth = len(self._split_path(iso_path))

        joliet_path = self._normalize_joliet_path(joliet_path)

        if self.rock_ridge is None and self.enhanced_vd is None:
            self._check_path_depth(iso_path)
        (name, parent) = self._name_and_parent_from_path(self.pvd, iso_path)

        check_iso9660_directory(name, self.interchange_level)

        relocated = False
        fake_dir_rec = None
        orig_parent = None
        if self.rock_ridge is not None and (depth % 8) == 0 and self.enhanced_vd is None:
            # If the depth was a multiple of 8, then we are going to have to
            # make a relocated entry for this record.

            rr_moved_parent = self._find_or_create_rr_moved()

            # With a depth of 8, we have to add the directory both to the
            # original parent with a CL link, and to the new parent with an
            # RE link.  Here we make the "fake" record, as a child of the
            # original place; the real one will be done below.
            fake_dir_rec = dr.DirectoryRecord()
            fake_dir_rec.new_dir(name, parent, self.pvd.sequence_number(),
                                 self.rock_ridge, rr_name,
                                 self.pvd.logical_block_size(), True, False,
                                 self.xa)
            self._add_child_to_dr(parent, fake_dir_rec, self.pvd.logical_block_size())

            dot = dr.DirectoryRecord()
            dot.new_dot(fake_dir_rec, self.pvd.sequence_number(), self.rock_ridge,
                        self.pvd.logical_block_size(), self.xa)
            self._add_child_to_dr(fake_dir_rec, dot, self.pvd.logical_block_size())

            dotdot = dr.DirectoryRecord()
            dotdot.new_dotdot(fake_dir_rec, self.pvd.sequence_number(),
                              self.rock_ridge, self.pvd.logical_block_size(), False, self.xa)
            self._add_child_to_dr(fake_dir_rec, dotdot, self.pvd.logical_block_size())

            for pvd in self.pvds:
                pvd.add_to_ptr(path_table_record.PathTableRecord.record_length(len(name)))
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())

            # The fake dir record doesn't get an entry in the path table record.

            relocated = True
            orig_parent = parent
            parent = rr_moved_parent

        rec = dr.DirectoryRecord()
        rec.new_dir(name, parent, self.pvd.sequence_number(), self.rock_ridge,
                    rr_name, self.pvd.logical_block_size(), False, relocated,
                    self.xa)
        self._add_child_to_dr(parent, rec, self.pvd.logical_block_size())
        if rec.rock_ridge is not None and relocated:
            fake_dir_rec.rock_ridge.child_link = rec

        dot = dr.DirectoryRecord()
        dot.new_dot(rec, self.pvd.sequence_number(), self.rock_ridge,
                    self.pvd.logical_block_size(), self.xa)
        self._add_child_to_dr(rec, dot, self.pvd.logical_block_size())

        dotdot = dr.DirectoryRecord()
        dotdot.new_dotdot(rec, self.pvd.sequence_number(), self.rock_ridge,
                          self.pvd.logical_block_size(), relocated, self.xa)
        self._add_child_to_dr(rec, dotdot, self.pvd.logical_block_size())
        if dotdot.rock_ridge is not None and relocated:
            dotdot.rock_ridge.parent_link = orig_parent

        if rec.rock_ridge is None or not relocated:
            for pvd in self.pvds:
                pvd.add_to_ptr(path_table_record.PathTableRecord.record_length(len(name)))
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())

        # We always need to add an entry to the path table record
        ptr = path_table_record.PathTableRecord()
        ptr.new_dir(name, rec, parent.ptr.directory_num, rec.parent.ptr.depth + 1)
        rec.set_ptr(ptr)

        self.pvd.add_path_table_record(ptr)

        if self.joliet_vd is not None:
            (joliet_name, joliet_parent) = self._joliet_name_and_parent_from_path(joliet_path)

            rec = dr.DirectoryRecord()
            rec.new_dir(joliet_name, joliet_parent,
                        self.joliet_vd.sequence_number(), None, None,
                        self.joliet_vd.logical_block_size(), False, False,
                        False)
            self._add_child_to_dr(joliet_parent, rec, self.joliet_vd.logical_block_size())

            dot = dr.DirectoryRecord()
            dot.new_dot(rec, self.joliet_vd.sequence_number(), None,
                        self.joliet_vd.logical_block_size(), False)
            self._add_child_to_dr(rec, dot, self.joliet_vd.logical_block_size())

            dotdot = dr.DirectoryRecord()
            dotdot.new_dotdot(rec, self.joliet_vd.sequence_number(), None,
                              self.joliet_vd.logical_block_size(), False, False)
            self._add_child_to_dr(rec, dotdot, self.joliet_vd.logical_block_size())

            self.joliet_vd.add_to_ptr(path_table_record.PathTableRecord.record_length(len(joliet_name)))
            self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

            # We always need to add an entry to the path table record
            ptr = path_table_record.PathTableRecord()
            ptr.new_dir(joliet_name, rec, joliet_parent.ptr.directory_num, rec.parent.ptr.depth + 1)
            rec.set_ptr(ptr)

            self.joliet_vd.add_path_table_record(ptr)

            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())

            self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def rm_file(self, iso_path, rr_name=None, joliet_path=None):
        '''
        Remove a file from the ISO.

        Parameters:
         iso_path - The path to the file to remove.
         rr_name - The Rock Ridge name of the file to remove.
         joliet_path - The Joliet path to the file to remove.
        Returns:
         Nothing.
        '''

        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        iso_path = utils.normpath(iso_path)

        if bytes(bytearray([iso_path[0]])) != b'/':
            raise pycdlibexception.PyCdlibException("Must be a path starting with /")

        rr_name = self._check_rr_name(rr_name)

        joliet_path = self._normalize_joliet_path(joliet_path)

        child,index = self._find_record(self.pvd, iso_path)

        if not child.is_file():
            raise pycdlibexception.PyCdlibException("Cannot remove a directory with rm_file (try rm_directory instead)")

        self._remove_child_from_dr(child, index, self.pvd.logical_block_size())

        for pvd in self.pvds:
            pvd.remove_from_space_size(child.file_length())

        if self.joliet_vd is not None:
            jolietchild,jolietindex = self._find_record(self.joliet_vd, joliet_path, 'utf-16_be')
            self._remove_child_from_dr(jolietchild, jolietindex, self.joliet_vd.logical_block_size())
            self.joliet_vd.remove_from_space_size(child.file_length())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def rm_directory(self, iso_path, rr_name=None, joliet_path=None):
        '''
        Remove a directory from the ISO.

        Parameters:
         iso_path - The path to the directory to remove.
         rr_name - The Rock Ridge name of the file to remove.
         joliet_path - The Joliet path to the file to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        iso_path = utils.normpath(iso_path)

        if iso_path == b'/':
            raise pycdlibexception.PyCdlibException("Cannot remove base directory")

        rr_name = self._check_rr_name(rr_name)

        joliet_path = self._normalize_joliet_path(joliet_path)

        child,index = self._find_record(self.pvd, iso_path)

        if not child.is_dir():
            raise pycdlibexception.PyCdlibException("Cannot remove a file with rm_directory (try rm_file instead)")

        for c in child.children:
            if c.is_dot() or c.is_dotdot():
                continue
            raise pycdlibexception.PyCdlibException("Directory must be empty to use rm_directory")

        self._remove_child_from_dr(child, index, self.pvd.logical_block_size())

        for pvd in self.pvds:
            pvd.remove_from_space_size(child.file_length())
        for pvd in self.pvds:
            pvd.remove_from_ptr(child.file_ident)

        if child.rock_ridge is not None and child.rock_ridge.relocated_record():
            # OK, this child was relocated.  If the parent of this relocated
            # record is empty (only . and ..), we can remove it.
            parent = child.parent
            if len(parent.children) == 2:
                parent_index = None
                for index,c in enumerate(parent.parent.children):
                    if c.file_ident == parent.file_ident:
                        parent_index = index
                        break
                if parent_index is None:
                    raise pycdlibexception.PyCdlibException("Could not find parent in its own parent!")

                self._remove_child_from_dr(parent, parent_index, self.pvd.logical_block_size())
                for pvd in self.pvds:
                    pvd.remove_from_space_size(parent.file_length())
                for pvd in self.pvds:
                    pvd.remove_from_ptr(parent.file_ident)

            pl,plindex = self._find_child_link_by_extent(self.pvd, child.extent_location())
            if len(pl.children) != 0:
                raise pycdlibexception.PyCdlibException("Parent link should have no children!")
            if pl.file_ident != child.file_ident:
                raise pycdlibexception.PyCdlibException("Parent link should have same name as child link!")
            self._remove_child_from_dr(pl, plindex, self.pvd.logical_block_size())
            for pvd in self.pvds:
                pvd.remove_from_space_size(pl.file_length())

        if self.joliet_vd is not None:
            joliet_child,joliet_index = self._find_record(self.joliet_vd, joliet_path, 'utf-16_be')
            self._remove_child_from_dr(joliet_child, joliet_index, self.joliet_vd.logical_block_size())
            self.joliet_vd.remove_from_space_size(joliet_child.file_length())
            self.joliet_vd.remove_from_ptr(joliet_child.file_ident)
            for pvd in self.pvds:
                pvd.remove_from_space_size(pvd.logical_block_size())
            self.joliet_vd.remove_from_space_size(self.joliet_vd.logical_block_size())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def add_eltorito(self, bootfile_path, bootcatfile="/BOOT.CAT;1",
                     rr_bootcatname="boot.cat", joliet_bootcatfile="/boot.cat",
                     boot_load_size=None, platform_id=0, boot_info_table=False):
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
                          boot catalog entry; set to "boot.cat" by default.
         joliet_bootcatfile - The Joliet name for the fake file to use as the
                              boot catalog entry; set to "boot.cat" by default.
         boot_load_size - The number of sectors to use for the boot entry; if
                          set to None (the default), the number of sectors will
                          be calculated.
         platform_id - The platform ID to set for the El Torito entry; 0 is for
                       x86, 1 is for Power PC, and 2 is for Mac.  0 is the
                       default.
         boot_info_table - Whether to add a boot info table to the ISO.  The
                           default is False.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        # In order to add an El Torito boot, we need to do the following:
        # 1.  Find the boot file record (which must already exist).
        # 2.  Construct a BootRecord.
        # 3.  Construct a BootCatalog, and add it to the filesystem.
        # 4.  Add the boot record to the ISO.

        bootfile_path = utils.normpath(bootfile_path)
        bootcatfile = utils.normpath(bootcatfile)

        if self.joliet_vd is not None:
            if joliet_bootcatfile is None:
                raise pycdlibexception.PyCdlibException("A joliet path must be passed when adding El Torito to a Joliet ISO")

        # Step 1.
        child,index_unused = self._find_record(self.pvd, bootfile_path)

        if boot_load_size is None:
            sector_count = utils.ceiling_div(child.file_length(), self.pvd.logical_block_size()) * self.pvd.logical_block_size() // 512
        else:
            sector_count = boot_load_size

        if boot_info_table:
            orig_len = child.file_length()
            data_fp, data_len = child.open_data(self.pvd.logical_block_size())
            child.boot_info_table = eltorito.EltoritoBootInfoTable()
            child.boot_info_table.new(self.pvd.extent_location(), child,
                                      orig_len,
                                      self._calculate_eltorito_boot_info_table_csum(data_fp, data_len))

        if self.eltorito_boot_catalog is not None:
            # All right, we already created the boot catalog.  Add a new section
            # to the boot catalog
            child,index_unused = self._find_record(self.pvd, bootfile_path)
            self.eltorito_boot_catalog.add_section(child, sector_count)
            self._reshuffle_extents()
            return

        # Step 2.
        br = headervd.BootRecord()
        br.new(b"EL TORITO SPECIFICATION")
        self.brs.append(br)

        # Step 3.
        self.eltorito_boot_catalog = eltorito.EltoritoBootCatalog(br)
        self.eltorito_boot_catalog.new(br, child, sector_count, platform_id)

        # Step 4.
        length = self.pvd.logical_block_size()

        self._check_path_depth(bootcatfile)
        (name, parent) = self._name_and_parent_from_path(self.pvd, bootcatfile)

        check_iso9660_filename(name, self.interchange_level)

        bootcat_dirrecord = dr.DirectoryRecord()
        bootcat_dirrecord.new_fp(None, False, length, name, parent,
                                 self.pvd.sequence_number(), self.rock_ridge,
                                 rr_bootcatname.encode('utf-8'), self.xa)

        self._add_child_to_dr(parent, bootcat_dirrecord, self.pvd.logical_block_size())
        if bootcat_dirrecord.rock_ridge is not None and bootcat_dirrecord.rock_ridge.ce_record is not None:
            for pvd in self.pvds:
                pvd.add_to_space_size(pvd.logical_block_size())

        self.eltorito_boot_catalog.set_dirrecord(bootcat_dirrecord)

        for pvd in self.pvds:
            pvd.add_to_space_size(length)

        if self.joliet_vd is not None:
            self.joliet_vd.add_to_space_size(length)
            self.joliet_vd.add_to_space_size(length)

            self._add_hard_link(iso_old_path=bootcatfile, joliet_new_path=joliet_bootcatfile)

        for pvd in self.pvds:
            pvd.add_to_space_size(pvd.logical_block_size())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def rm_eltorito(self):
        '''
        Remove the El Torito boot record (and associated files) from the ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.eltorito_boot_catalog is None:
            raise pycdlibexception.PyCdlibException("This ISO doesn't have an El Torito Boot Record")

        eltorito_index = None
        for index,br in enumerate(self.brs):
            if br.boot_system_identifier == b"EL TORITO SPECIFICATION".ljust(32, b'\x00'):
                eltorito_index = index
                break

        if eltorito_index is None:
            # There was a boot catalog, but no corresponding boot record.  This
            # should never happen.
            raise pycdlibexception.PyCdlibException("El Torito boot catalog found with no corresponding boot record")

        extent, = struct.unpack_from("=L", self.brs[eltorito_index].boot_system_use[:4], 0)

        del self.brs[eltorito_index]

        self.eltorito_boot_catalog = None

        for pvd in self.pvds:
            pvd.remove_from_space_size(pvd.logical_block_size())
        if self.joliet_vd is not None:
            self.joliet_vd.remove_from_space_size(self.joliet_vd.logical_block_size())

        if self.enhanced_vd is not None:
            self.enhanced_vd.remove_from_space_size(self.enhanced_vd.logical_block_size())

        bootcat,index = self._find_record_by_extent(self.pvd, extent)

        # We found the child
        self._remove_child_from_dr(bootcat, index, self.pvd.logical_block_size())
        for pvd in self.pvds:
            pvd.remove_from_space_size(bootcat.file_length())
        if self.joliet_vd is not None:
            jolietbootcat,jolietindex = self._find_record_by_extent(self.joliet_vd, extent)
            self._remove_child_from_dr(jolietbootcat, jolietindex, self.joliet_vd.logical_block_size())
            self.joliet_vd.remove_from_space_size(bootcat.file_length())

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def add_symlink(self, symlink_path, rr_symlink_name, rr_path, joliet_path=None):
        '''
        Add a symlink from rr_symlink_name to the rr_path.  The non-RR name
        of the symlink must also be provided.

        Parameters:
         symlink_path - The ISO9660 name of the symlink itself on the ISO.
         rr_symlink_name - The Rock Ridge name of the symlink itself on the ISO.
         rr_path - The Rock Ridge name of the entry on the ISO that the symlink
                   points to.
         joliet_path - The Joliet name of the symlink (if this ISO has Joliet).
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.rock_ridge is None:
            raise pycdlibexception.PyCdlibException("Can only add symlinks to a Rock Ridge ISO")

        symlink_path = utils.normpath(symlink_path)
        rr_path = utils.normpath(rr_path)

        joliet_path = self._normalize_joliet_path(joliet_path)

        self._check_path_depth(symlink_path)
        (name, parent) = self._name_and_parent_from_path(self.pvd, symlink_path)

        if bytes(bytearray([rr_path[0]])) == b'/':
            raise pycdlibexception.PyCdlibException("Rock Ridge symlink target path must be relative")

        rec = dr.DirectoryRecord()
        rr_symlink_name = rr_symlink_name.encode('utf-8')
        rec.new_symlink(name, parent, rr_path, self.pvd.sequence_number(),
                        self.rock_ridge, rr_symlink_name, self.xa)
        self._add_child_to_dr(parent, rec, self.pvd.logical_block_size())

        if self.joliet_vd is not None:
            (joliet_name, joliet_parent) = self._name_and_parent_from_path(self.joliet_vd, joliet_path, 'utf-16_be')

            joliet_name = joliet_name.decode('utf-8').encode('utf-16_be')

            joliet_rec = dr.DirectoryRecord()
            joliet_rec.new_fake_symlink(joliet_name, joliet_parent, self.joliet_vd.sequence_number())
            self._add_child_to_dr(joliet_parent, joliet_rec, self.joliet_vd.logical_block_size())

            rec.linked_records.append(joliet_rec)

        if self.enhanced_vd is not None:
            self.enhanced_vd.copy_sizes(self.pvd)

        self._reshuffle_extents()

    def _get_entry(self, iso_path, joliet):
        '''
        Get the directory record for a particular path.

        Parameters:
         iso_path - The path on the ISO to look up information for.
         joliet - Whether to look for the path in the Joliet portion of the ISO.
        Returns:
         A dr.DirectoryRecord object representing the path.
        '''
        if joliet:
            joliet_path = self._normalize_joliet_path(iso_path)
            rec,index_unused = self._find_record(self.joliet_vd, joliet_path, 'utf-16_be')
        else:
            iso_path = utils.normpath(iso_path)
            rec,index_unused = self._find_record(self.pvd, iso_path)

        return rec

    def list_dir(self, iso_path, joliet=False):
        '''
        Generate a list of all of the file/directory objects in the specified
        location on the ISO.

        Parameters:
         iso_path - The path on the ISO to look up information for.
         joliet - Whether to look for the path in the Joliet portion of the ISO.
        Yields:
         Children of this path.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        rec = self._get_entry(iso_path, joliet)

        if not rec.is_dir():
            raise pycdlibexception.PyCdlibException("Record is not a directory!")

        for child in rec.children:
            yield child

    def get_entry(self, iso_path, joliet=False):
        '''
        Get the directory record for a particular path.

        Parameters:
         iso_path - The path on the ISO to look up information for.
         joliet - Whether to look for the path in the Joliet portion of the ISO.
        Returns:
         A dr.DirectoryRecord object representing the path.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        return self._get_entry(iso_path, joliet)

    def add_isohybrid(self, isohybrid_filename, part_entry=1, mbr_id=None,
                      part_offset=0, geometry_sectors=32, geometry_heads=64,
                      part_type=0x17):
        '''
        Make an ISO a "hybrid", which means that it can be booted either from a
        CD or from more traditional media (like a USB stick).  This requires
        passing in a file object that contains a bootable image, and has a
        certain signature (if using syslinux, this generally means the
        isohdpfx.bin files).

        Paramters:
         isohybrid_fp - A file object which points to the bootable image.
         part_entry - The partition entry to use; one by default.
         mbr_id - The mbr_id to use.  If set to None (the default), a random one
                  will be generated.
         part_offset - The partition offset to use; zero by default.
         geometry_sectors - The number of sectors to assign; thirty-two by default.
         geometry_heads - The number of heads to assign; sixty-four by default.
         part_type - The partition type to assign; twenty-three by default.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        fp = open(isohybrid_filename, 'rb')
        try:
            self.add_isohybrid_fp(fp, part_entry, mbr_id, part_offset,
                                  geometry_sectors, geometry_heads, part_type)
        finally:
            fp.close()

    def add_isohybrid_fp(self, isohybrid_fp, part_entry=1, mbr_id=None,
                         part_offset=0, geometry_sectors=32, geometry_heads=64,
                         part_type=0x17):
        '''
        Make an ISO a "hybrid", which means that it can be booted either from a
        CD or from more traditional media (like a USB stick).  This requires
        passing in a file object that contains a bootable image, and has a
        certain signature (if using syslinux, this generally means the
        isohdpfx.bin files).

        Paramters:
         isohybrid_fp - A file object which points to the bootable image.
         part_entry - The partition entry to use; one by default.
         mbr_id - The mbr_id to use.  If set to None (the default), a random one
                  will be generated.
         part_offset - The partition offset to use; zero by default.
         geometry_sectors - The number of sectors to assign; thirty-two by default.
         geometry_heads - The number of heads to assign; sixty-four by default.
         part_type - The partition type to assign; twenty-three by default.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        isohybrid_fp.seek(0, os.SEEK_END)
        size = isohybrid_fp.tell()
        if size != 432:
            raise pycdlibexception.PyCdlibException("The isohybrid file must be exactly 432 bytes")

        if self.eltorito_boot_catalog is None:
            raise pycdlibexception.PyCdlibException("The ISO must have an El Torito Boot Record to add isohybrid support")

        if self.eltorito_boot_catalog.initial_entry.sector_count != 4:
            raise pycdlibexception.PyCdlibException("El Torito Boot Catalog sector count must be 4 (was actually 0x%x)" % (self.eltorito_boot_catalog.initial_entry.sector_count))

        # Now check that the eltorito boot file contains the appropriate
        # signature (offset 0x40, '\xFB\xC0\x78\x70')
        bootfile_dirrecord = self.eltorito_boot_catalog.initial_entry.dirrecord
        data_fp,data_length_unused = bootfile_dirrecord.open_data(self.pvd.logical_block_size())
        data_fp.seek(0x40, os.SEEK_CUR)
        signature = data_fp.read(4)
        if signature != b'\xfb\xc0\x78\x70':
            raise pycdlibexception.PyCdlibException("Invalid signature on boot file for iso hybrid")

        isohybrid_fp.seek(0)
        self.isohybrid_mbr = isohybrid.IsoHybrid()
        self.isohybrid_mbr.new(isohybrid_fp.read(432),
                               self.eltorito_boot_catalog.initial_entry.load_rba,
                               part_entry,
                               mbr_id,
                               part_offset,
                               geometry_sectors,
                               geometry_heads,
                               part_type)

    def rm_isohybrid(self):
        '''
        Remove the "hybridization" of an ISO, making it a traditional ISO again.
        This means the ISO will no longer be able to be copied and booted off
        of traditional media (like USB sticks).

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        self.isohybrid_mbr = None

    def full_path_from_dirrecord(self, rec):
        '''
        A method to get the absolute path of a directory record.

        Parameters:
         dr - The directory record to get the full path for.
        Returns:
         A string representing the absolute path to the file on the ISO.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        ret = "/" + rec.file_identifier()
        parent = rec.parent
        while parent is not None:
            ret = "/" + parent.file_identifier() + ret
            parent = parent.parent

        return utils.normpath(ret)

    def duplicate_pvd(self):
        '''
        A method to add a duplicate PVD to the ISO.  This is a mostly useless
        feature allowed by Ecma-119 to have duplicate PVDs to avoid possible
        corruption.  However, there are CDs in the wild (Office 2000) that use
        this feature, so we allow it in pycdlib.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        pvd = headervd.PrimaryVolumeDescriptor()
        pvd.copy(self.pvd)

        self.pvds.append(pvd)
        self._reshuffle_extents()

    def close(self):
        '''
        Close a previously opened ISO, and re-initialize the object to the
        defaults.  After this call the object can be re-used for manipulation
        of another ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.managing_fp:
            # In this case, we are managing self.cdfp, so we need to close it
            self.cdfp.close()

        if self.managing_dr_fps:
            # In this case, we are managing at least one file pointer for a
            # file.  Walk all of the directory records, closing out the ones
            # that we are managing.  Note that we only walk the PVD here; since
            # we only have one file pointer for all directory record objects
            # pointing here, we only need to close out one of them.
            dirs = collections.deque([self.pvd.root_directory_record()])
            while dirs:
                curr = dirs.popleft()
                for child in curr.children:
                    if child.is_dot() or child.is_dotdot():
                        continue

                    if child.is_dir():
                        dirs.append(child)
                    else:
                        child.close_managed_fp()

        # now that we are closed, re-initialize everything
        self._initialize()
