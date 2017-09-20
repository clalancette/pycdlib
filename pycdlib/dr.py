# Copyright (C) 2015-2017  Chris Lalancette <clalancette@gmail.com>

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
The class to support ISO9660 Directory Records.
'''

from __future__ import absolute_import

import bisect
import struct

import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.utils as utils
import pycdlib.dates as dates
import pycdlib.rockridge as rockridge


class XARecord(object):
    '''
    A class that represents an ISO9660 Extended Attribute record as defined
    in the Phillips Yellow Book standard.
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, xastr):
        '''
        Parse an Extended Attribute Record out of a string.

        Parameters:
         xastr - The string to parse.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("This XARecord is already initialized!")

        (self.group_id, self.user_id, self.attributes, signature, self.filenum,
         unused) = struct.unpack_from("=HHH2sB5s", xastr, 0)

        if signature != b"XA":
            raise pycdlibexception.PyCdlibInvalidISO("Invalid signature on the XARecord!")

        if unused != b'\x00\x00\x00\x00\x00':
            raise pycdlibexception.PyCdlibInvalidISO("Unused fields should be 0")

        self.initialized = True

    def new(self):
        '''
        Create a new Extended Attribute Record.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("This XARecord is already initialized!")

        # FIXME: we should allow the user to set these
        self.group_id = 0
        self.user_id = 0
        self.attributes = 0
        self.filenum = 0
        self.initialized = True

    def record(self):
        '''
        Record this Extended Attribute Record.

        Parameters:
         None.
        Returns:
         A string representing this Extended Attribute Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("This XARecord is not yet initialized!")

        return struct.pack("=HHH2sB5s", self.group_id, self.user_id, self.attributes, b'XA', self.filenum, b'\x00' * 5)

    @staticmethod
    def length():
        '''
        A static method to return the size of an Extended Attribute Record.
        '''
        return 14


class DirectoryRecord(object):
    '''
    A class that represents an ISO9660 directory record.
    '''
    FILE_FLAG_EXISTENCE_BIT = 0
    FILE_FLAG_DIRECTORY_BIT = 1
    FILE_FLAG_ASSOCIATED_FILE_BIT = 2
    FILE_FLAG_RECORD_BIT = 3
    FILE_FLAG_PROTECTION_BIT = 4
    FILE_FLAG_MULTI_EXTENT_BIT = 7

    DATA_ON_ORIGINAL_ISO = 1
    DATA_IN_EXTERNAL_FP = 2

    FMT = "=BBLLLL7sBBBHHB"

    def __init__(self):
        self.initialized = False
        self.new_extent_loc = None
        self.boot_info_table = None
        self.linked_records = []
        self.target = None
        self.data_fp = None
        self.manage_fp = False
        self.hidden = False
        self.extents_to_here = 1
        self.offset_to_here = 0

    def parse(self, record, data_fp, parent):
        '''
        Parse a directory record out of a string.

        Parameters:
         record - The string to parse for this record.
         data_fp - The file object to associate with this record.
         parent - The parent of this record.
        Returns:
         True if this Directory Record has Rock Ridge extensions, False otherwise.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        if len(record) > 255:
            # Since the length is supposed to be 8 bits, this should never
            # happen.
            raise pycdlibexception.PyCdlibInvalidISO("Directory record longer than 255 bytes!")

        (self.dr_len, self.xattr_len, extent_location_le, extent_location_be,
         data_length_le, data_length_be_unused, dr_date, self.file_flags,
         self.file_unit_size, self.interleave_gap_size, seqnum_le, seqnum_be,
         self.len_fi) = struct.unpack_from(self.FMT, record[:33], 0)

        # In theory we should have a check here that checks to make sure that
        # the length of the record we were passed in matches the data record
        # length.  However, we have seen ISOs in the wild where this is
        # incorrect, so we elide the check here.

        if extent_location_le != utils.swab_32bit(extent_location_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian (%d) and big-endian (%d) extent location disagree" % (extent_location_le, utils.swab_32bit(extent_location_be)))
        self.orig_extent_loc = extent_location_le
        self.new_extent_loc = None

        # Theoretically, we should check to make sure that the little endian
        # data length is the same as the big endian data length.  In practice,
        # though, we've seen ISOs where this is wrong.  Skip the check, and just
        # pick the little-endian as the "actual" size, and hope for the best.

        self.data_length = data_length_le

        if seqnum_le != utils.swab_16bit(seqnum_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        self.date = dates.DirectoryRecordDate()
        self.date.parse(dr_date)

        # OK, we've unpacked what we can from the beginning of the string.  Now
        # we have to use the len_fi to get the rest.

        self.children = []
        self.is_root = False
        self.isdir = False
        self.parent = parent
        self.data_fp = data_fp

        self.rock_ridge = None

        self.xa_record = None

        if self.parent is None:
            self.is_root = True

            # A root directory entry should always be exactly 34 bytes.
            # However, we have seen ISOs in the wild that get this wrong, so we
            # elide a check for it.

            self.file_ident = bytes(bytearray([record[33]]))

            # A root directory entry should always have 0 as the identifier.
            if self.file_ident != b'\x00':
                raise pycdlibexception.PyCdlibInvalidISO("Invalid root directory entry identifier")
            self.isdir = True
        else:
            record_offset = 33
            self.file_ident = record[record_offset:record_offset + self.len_fi]
            record_offset += self.len_fi
            if self.file_flags & (1 << self.FILE_FLAG_DIRECTORY_BIT):
                self.isdir = True
            else:
                self.original_data_location = self.DATA_ON_ORIGINAL_ISO

            if self.len_fi % 2 == 0:
                record_offset += 1

            if len(record[record_offset:]) >= 14:
                if record[record_offset + 6:record_offset + 8] == b'XA':
                    self.xa_record = XARecord()
                    self.xa_record.parse(record[record_offset:record_offset + 14])
                    record_offset += 14

            if len(record[record_offset:]) >= 2 and record[record_offset:record_offset + 2] in [b'SP', b'RR', b'CE', b'PX', b'ER', b'ES', b'PN', b'SL', b'NM', b'CL', b'PL', b'TF', b'SF', b'RE']:
                self.rock_ridge = rockridge.RockRidge()
                is_first_dir_record_of_root = self.file_ident == b'\x00' and parent.parent is None

                if is_first_dir_record_of_root:
                    bytes_to_skip = 0
                elif parent.parent is None:
                    bytes_to_skip = parent.children[0].rock_ridge.bytes_to_skip
                else:
                    bytes_to_skip = parent.rock_ridge.bytes_to_skip

                self.rock_ridge.parse(record[record_offset:],
                                      is_first_dir_record_of_root,
                                      bytes_to_skip,
                                      False)

        if self.xattr_len != 0:
            if self.file_flags & (1 << self.FILE_FLAG_RECORD_BIT):
                raise pycdlibexception.PyCdlibInvalidISO("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise pycdlibexception.PyCdlibInvalidISO("Protection Bit not allowed with Extended Attributes")

        self.initialized = True

        if self.rock_ridge is None:
            ret = None
        else:
            ret = self.rock_ridge.rr_version

        return ret

    def _rr_new(self, rr_version, rr_name, rr_symlink_target, rr_relocated_child,
                rr_relocated, rr_relocated_parent):
        '''
        Internal method to add Rock Ridge to a Directory Record.

        Parameters:
         rr_version - A string containing the version of Rock Ridge to use for
                      this record.
         rr_name - The Rock Ridge name to associate with this directory record.
         rr_symlink_target - The target for the symlink, if this is a symlink
                             record (otherwise, None).
         rr_relocated_child - True if this is a directory record for a rock
                              ridge relocated child.
         rr_relocated - True if this is a directory record for a relocated
                        entry.
         rr_relocated_parent - True if this is a directory record for a rock
                               ridge relocated parent.
        Returns:
         Nothing.
        '''

        self.rock_ridge = rockridge.RockRidge()
        is_first_dir_record_of_root = self.file_ident == b'\x00' and self.parent.parent is None
        bytes_to_skip = 0
        if self.xa_record is not None:
            bytes_to_skip = XARecord.length()
        self.dr_len = self.rock_ridge.new(is_first_dir_record_of_root,
                                          rr_name, self.isdir,
                                          rr_symlink_target, rr_version,
                                          rr_relocated_child,
                                          rr_relocated,
                                          rr_relocated_parent,
                                          bytes_to_skip,
                                          self.dr_len)

        if self.isdir:
            if self.parent.parent is not None:
                if self.file_ident == b'\x00':
                    self.parent.rock_ridge.add_to_file_links()
                    self.rock_ridge.add_to_file_links()
                elif self.file_ident == b'\x01':
                    self.rock_ridge.copy_file_links(self.parent.parent.children[1].rock_ridge)
                else:
                    self.parent.rock_ridge.add_to_file_links()
                    self.parent.children[0].rock_ridge.add_to_file_links()
            else:
                if self.file_ident != b'\x00' and self.file_ident != b'\x01':
                    self.parent.children[0].rock_ridge.add_to_file_links()
                    self.parent.children[1].rock_ridge.add_to_file_links()
                else:
                    self.rock_ridge.add_to_file_links()

    def _new(self, mangledname, parent, seqnum, isdir, length, xa):
        '''
        Internal method to create a new Directory Record.

        Parameters:
         mangledname - The ISO9660 name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number to associate with this directory record.
         isdir - Whether this directory record represents a directory.
         length - The length of the data for this directory record.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''

        # Adding a new time should really be done when we are going to write
        # the ISO (in record()).  Ecma-119 9.1.5 says:
        #
        # "This field shall indicate the date and the time of the day at which
        # the information in the Extent described by the Directory Record was
        # recorded."
        #
        # We create it here just to have something in the field, but we'll
        # redo the whole thing when we are mastering.
        self.date = dates.DirectoryRecordDate()
        self.date.new()

        if length > 2**32 - 1:
            raise pycdlibexception.PyCdlibInvalidInput("Maximum supported file length is 2^32-1")

        self.data_length = length
        # FIXME: if the length of the item is more than 2^32 - 1, and the
        # interchange level is 3, we should make duplicate directory record
        # entries so we can represent the whole file (see
        # http://wiki.osdev.org/ISO_9660, Size Limitations for a discussion of
        # this).

        self.file_ident = mangledname

        self.isdir = isdir

        self.seqnum = seqnum
        # For a new directory record entry, there is no original_extent_loc,
        # so we leave it at None.
        self.orig_extent_loc = None
        self.len_fi = len(self.file_ident)
        self.dr_len = struct.calcsize(self.FMT) + self.len_fi

        # From Ecma-119, 9.1.6, the file flag bits are:
        #
        # Bit 0 - Existence - 0 for existence known, 1 for hidden
        # Bit 1 - Directory - 0 for file, 1 for directory
        # Bit 2 - Associated File - 0 for not associated, 1 for associated
        # Bit 3 - Record - 0 for structure not in xattr, 1 for structure in xattr
        # Bit 4 - Protection - 0 for no owner and group in xattr, 1 for owner and group in xattr
        # Bit 5 - Reserved
        # Bit 6 - Reserved
        # Bit 7 - Multi-extent - 0 for final directory record, 1 for not final directory record
        # FIXME: We probably want to allow the existence, associated file, xattr
        # record, and multi-extent bits to be set by the caller.
        self.file_flags = 0
        if self.isdir:
            self.file_flags |= (1 << self.FILE_FLAG_DIRECTORY_BIT)
        self.file_unit_size = 0  # FIXME: we don't support setting file unit size for now
        self.interleave_gap_size = 0  # FIXME: we don't support setting interleave gap size for now
        self.xattr_len = 0  # FIXME: we don't support xattrs for now
        self.children = []

        self.parent = parent
        self.is_root = False
        if parent is None:
            # If no parent, then this is the root
            self.is_root = True

        self.xa_record = None
        if xa:
            self.xa_record = XARecord()
            self.xa_record.new()
            self.dr_len += XARecord.length()

        self.dr_len += (self.dr_len % 2)

        self.rock_ridge = None

        self.initialized = True

    def new_symlink(self, name, parent, rr_target, seqnum, rock_ridge, rr_name, xa):
        '''
        Create a new symlink Directory Record.  This implies that the new
        record will be Rock Ridge.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         rr_target - The symlink target for this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - The version of Rock Ridge to use for this directory record.
         rr_name - The Rock Ridge name for this directory record.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(name, parent, seqnum, False, 0, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, rr_name, rr_target, False, False, False)

    def new_fake_symlink(self, name, parent, seqnum):
        '''
        Create a new symlink Directory Record.  This implies that the new
        record will be Rock Ridge.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(name, parent, seqnum, False, 0, False)

    def new_file(self, length, isoname, parent, seqnum, rock_ridge, rr_name, xa):
        '''
        Create a new file Directory Record.

        Parameters:
         length - The length of the data.
         isoname - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         rr_name - The Rock Ridge name for this directory record.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self._new(isoname, parent, seqnum, False, length, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, rr_name, None, False, False, False)

    def new_root(self, seqnum, log_block_size):
        '''
        Create a new root Directory Record.

        Parameters:
         seqnum - The sequence number for this directory record.
         log_block_size - The logical block size to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(b'\x00', None, seqnum, True, log_block_size, False)

    def new_dot(self, root, seqnum, rock_ridge, log_block_size, xa):
        '''
        Create a new "dot" Directory Record.

        Parameters:
         root - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         log_block_size - The logical block size to use.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(b'\x00', root, seqnum, True, log_block_size, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, None, None, False, False, False)

    def new_dotdot(self, root, seqnum, rock_ridge, log_block_size, rr_relocated_parent, xa):
        '''
        Create a new "dotdot" Directory Record.

        Parameters:
         root - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         log_block_size - The logical block size to use.
         rr_relocated_parent - True if this is a Rock Ridge relocated parent.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(b'\x01', root, seqnum, True, log_block_size, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, None, None, False, False, rr_relocated_parent)

    def new_dir(self, name, parent, seqnum, rock_ridge, rr_name, log_block_size,
                rr_relocated_child, rr_relocated, xa):
        '''
        Create a new directory Directory Record.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         rr_name - The Rock Ridge name for this directory record.
         log_block_size - The logical block size to use.
         rr_relocated_child - True if this is a Rock Ridge relocated child.
         rr_relocated - True if this is a Rock Ridge relocated entry.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(name, parent, seqnum, True, log_block_size, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, rr_name, None, rr_relocated_child, rr_relocated, False)
            if rr_relocated_child:
                # Relocated Rock Ridge entries are not exactly treated as directories, so
                # fix things up here.
                self.isdir = False
                self.file_flags = 0
                self.rock_ridge.add_to_file_links()

    def new_link(self, target, length, isoname, parent, seqnum, rock_ridge, rr_name, xa):
        '''
        Create a new linked Directory Record.  These are directory records that
        are somehow linked to another record.

        Parameters:
         target - The target directory record.
         length - The length of the data.
         isoname - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         rr_name - The Rock Ridge name for this directory record.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self.target = target
        self._new(isoname, parent, seqnum, False, length, xa)
        if rock_ridge is not None:
            self._rr_new(rock_ridge, rr_name, None, False, False, False)

    def parse_hidden(self, fp, length, extent_loc, parent, seqnum):
        '''
        Create a new hidden Directory Record.  These are file directory records
        that act as containers for information that is hidden from the normal
        filesystems, but still has data on the final ISO.  While we are creating
        a new object here, the API is actually called "parse" because we only
        use this while parsing the original ISO.

        Parameters:
         fp - A file object that contains the data for this directory record.
         length - The length of the data.
         extent_loc - The location of the data on the ISO.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new("", parent, seqnum, False, length, False)
        self.set_data_fp(fp, False)
        self.hidden = True
        self.original_data_location = self.DATA_ON_ORIGINAL_ISO
        self.orig_extent_loc = extent_loc

    def new_hidden_from_old(self, rec, extent_loc, parent, seqnum):
        '''
        Create a new hidden directory record using information from an old one.

        Parameters:
         rec - The old DirectoryRecord object to copy data out of.
         extent_loc - The location of the data on the ISO.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record already initialized")

        self._new(b"", parent, seqnum, False, rec.data_length, False)
        self.set_data_fp(rec.data_fp, rec.manage_fp)
        self.hidden = True
        self.original_data_location = rec.original_data_location
        self.orig_extent_loc = extent_loc

    def set_data_fp(self, fp, manage_fp):
        '''
        Set the data_fp to a file object.

        Parameters:
         fp - A file object that contains the data for this directory record.
         manage_fp - True if pycdlib is managing the file object, False otherwise.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        self.data_fp = fp
        self.manage_fp = manage_fp

    def update_fp(self, fp, length):
        '''
        Update a file Directory Record.

        Parameters:
         fp - A file object that contains the data for this directory record.
         length - The length of the data.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self.data_length = length

    def change_existence(self, is_hidden):
        '''
        Change the ISO9660 existence flag of this Directory Record.

        Parameters:
         is_hidden - True if this Directory Record should be hidden, False otherwise.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        if is_hidden:
            self.file_flags |= (1 << self.FILE_FLAG_EXISTENCE_BIT)
        else:
            self.file_flags &= ~(1 << self.FILE_FLAG_EXISTENCE_BIT)

    def add_child(self, child, logical_block_size):
        '''
        A method to add a child to this object.  Note that this is called both
        during parsing and when adding a new object to the system, so it
        it shouldn't have any functionality that is not appropriate for both.

        Parameters:
         child - The child directory record object to add.
         logical_block_size - The size of a logical block for this volume descriptor.
        Returns:
         True if adding this child caused the directory to overflow into another
         extent, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        if not self.isdir:
            raise Exception("Trying to add a child to a record that is not a directory")

        # First ensure that this is not a duplicate.  For speed purposes, we
        # recognize that bisect_left will always choose an index to the *left*
        # of a duplicate child.  Thus, to check for duplicates we only need to
        # see if the child to be added is a duplicate with the entry that
        # bisect_left returned.
        index = bisect.bisect_left(self.children, child)
        if index != len(self.children):
            if self.children[index].file_ident == child.file_ident:
                if not self.children[index].is_associated_file() and not child.is_associated_file():
                    if not (self.rock_ridge is not None and self.file_identifier() == b"RR_MOVED"):
                        raise pycdlibexception.PyCdlibInvalidInput("Parent %s already has a child named %s" % (self.file_identifier(), child.file_identifier()))
        self.children.insert(index, child)

        # We now have to check if we need to add another logical block.
        # We have to iterate over the entire list again, because where we
        # placed this last entry may rearrange the empty spaces in the blocks
        # that we've already allocated.
        if index == 0:
            dirrecord_offset = 0
            num_extents = 1
        else:
            dirrecord_offset = self.children[index - 1].offset_to_here
            num_extents = self.children[index - 1].extents_to_here

        for i in range(index, len(self.children)):
            c = self.children[i]
            dirrecord_len = c.directory_record_length()
            if (dirrecord_offset + dirrecord_len) > logical_block_size:
                num_extents += 1
                dirrecord_offset = 0
            dirrecord_offset += dirrecord_len
            c.extents_to_here = num_extents
            c.offset_to_here = dirrecord_offset

        overflowed = False
        if num_extents * logical_block_size > self.data_length:
            overflowed = True
            # When we overflow our data length, we always add a full block.
            self.data_length += logical_block_size
            # We also have to make sure to update the length of the dot child,
            # as that should always reflect the length.
            self.children[0].data_length = self.data_length

        return overflowed

    def remove_child(self, child, index, logical_block_size):
        '''
        A method to remove a child from this Directory Record.

        Parameters:
         child - The child DirectoryRecord object to remove.
         index - The index of the child into this DirectoryRecord children list.
         logical_block_size - The size of a logical block on this volume descriptor.
        Returns:
         True if removing this child caused an underflow, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        # Unfortunately, Rock Ridge specifies that a CL "directory" is replaced
        # by a *file*, not another directory.  Thus, we can't just depend on
        # whether this child is marked as a directory by the file flags during
        # parse time.  Instead, we check if this is either a true directory,
        # or a Rock Ridge CL entry, and in either case try to manipulate the
        # file links.
        if child.isdir or (child.rock_ridge is not None and child.rock_ridge.has_child_link_record()):
            if child.rock_ridge is not None:
                if self.parent is None:
                    self.children[0].rock_ridge.remove_from_file_links()
                    self.children[1].rock_ridge.remove_from_file_links()
                else:
                    self.rock_ridge.remove_from_file_links()
                    self.children[0].rock_ridge.remove_from_file_links()

        del self.children[index]

        # We now have to check if we need to remove a logical block.
        # We have to iterate over the entire list again, because where we
        # removed this last entry may rearrange the empty spaces in the blocks
        # that we've already allocated.
        if index == 0:
            dirrecord_offset = 0
            num_extents = 1
        else:
            dirrecord_offset = self.children[index - 1].offset_to_here
            num_extents = self.children[index - 1].extents_to_here

        for i in range(index, len(self.children)):
            c = self.children[i]
            dirrecord_len = c.directory_record_length()
            if (dirrecord_offset + dirrecord_len) > logical_block_size:
                num_extents += 1
                dirrecord_offset = 0
            dirrecord_offset += dirrecord_len
            c.extents_to_here = num_extents
            c.offset_to_here = dirrecord_offset

        underflow = False
        total_size = (num_extents - 1) * logical_block_size + dirrecord_offset
        if (self.data_length - total_size) > logical_block_size:
            self.data_length -= logical_block_size
            # We also have to make sure to update the length of the dot child,
            # as that should always reflect the length.
            self.children[0].data_length = self.data_length
            underflow = True

        return underflow

    def is_dir(self):
        '''
        A method to determine whether this Directory Record is a directory.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a directory, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return self.isdir

    def is_file(self):
        '''
        A method to determine whether this Directory Record is a file.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a file, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return not self.isdir

    def is_dot(self):
        '''
        A method to determine whether this Directory Record is a "dot" entry.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a "dot" entry, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return self.file_ident == b'\x00'

    def is_dotdot(self):
        '''
        A method to determine whether this Directory Record is a "dotdot" entry.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a "dotdot" entry, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return self.file_ident == b'\x01'

    def directory_record_length(self):
        '''
        A method to determine the length of this Directory Record.

        Parameters:
         None.
        Returns:
         The length of this Directory Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return self.dr_len

    def _extent_location(self):
        '''
        An internal method to get the location of this Directory Record on the
        ISO.

        Parameters:
         None.
        Returns:
         Extent location of this Directory Record on the ISO.
        '''
        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def extent_location(self):
        '''
        A method to get the location of this Directory Record on the ISO.

        Parameters:
         None.
        Returns:
         Extent location of this Directory Record on the ISO.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        return self._extent_location()

    def file_identifier(self):
        '''
        A method to get the identifier of this Directory Record.

        Parameters:
         None.
        Returns:
         String representing the identifier of this Directory Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        if self.is_root:
            return b'/'
        if self.file_ident == b'\x00':
            return b'.'
        if self.file_ident == b'\x01':
            return b'..'
        return self.file_ident

    def file_length(self):
        '''
        A method to get the file length of this Directory Record.

        Parameters:
         None.
        Returns:
         Integer file length of this Directory Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")
        ret = self.data_length
        if self.boot_info_table is not None:
            ret = self.boot_info_table.orig_len
        return ret

    def record(self):
        '''
        A method to generate the string representing this Directory Record.

        Parameters:
         None.
        Returns:
         String representing this Directory Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = dates.DirectoryRecordDate()
        self.date.new()

        padlen = struct.calcsize(self.FMT) + self.len_fi
        padstr = b'\x00' * (padlen % 2)

        extent_loc = self._extent_location()

        xa_rec = b""
        if self.xa_record is not None:
            xa_rec = self.xa_record.record()
        rr_rec = b""
        if self.rock_ridge is not None:
            rr_rec = self.rock_ridge.record_dr_entries()

        outlist = [struct.pack(self.FMT, self.dr_len, self.xattr_len,
                               extent_loc, utils.swab_32bit(extent_loc),
                               self.data_length, utils.swab_32bit(self.data_length),
                               self.date.record(), self.file_flags,
                               self.file_unit_size, self.interleave_gap_size,
                               self.seqnum, utils.swab_16bit(self.seqnum),
                               self.len_fi) + self.file_ident + padstr + xa_rec + rr_rec]

        outlist.append(b'\x00' * (len(outlist[0]) % 2))

        return b"".join(outlist)

    def is_associated_file(self):
        '''
        A method to determine whether this file is "associated" with another file
        on the ISO.

        Parameters:
         None.
        Returns:
         True if this file is associated with another file on the ISO, False
         otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        return self.file_flags & (1 << self.FILE_FLAG_ASSOCIATED_FILE_BIT)

    def set_ptr(self, ptr):
        '''
        A method to set the Path Table Record associated with this Directory
        Record.

        Parameters:
         ptr - The path table record to associate with this Directory Record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        self.ptr = ptr

    def add_boot_info_table(self, boot_info_table):
        '''
        A method to add a boot info table to this Directory Record.

        Parameters:
         boot_info_table - The Boot Info Table object to add to this Directory Record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibInternalError("Directory Record not yet initialized")

        self.boot_info_table = boot_info_table

    def __lt__(self, other):
        # This method is used for the bisect.insort_left() when adding a child.
        # It needs to return whether self is less than other.  Here we use the
        # ISO9660 sorting order which is essentially:
        #
        # 1.  The \x00 is always the "dot" record, and is always first.
        # 2.  The \x01 is always the "dotdot" record, and is always second.
        # 3.  Other entries are sorted lexically; this does not exactly match
        #     the sorting method specified in Ecma-119, but does OK for now.
        #
        # Ecma-119 Section 9.3 specifies that we need to pad out the shorter of
        # the two files with 0x20 (spaces), then compare byte-by-byte until
        # they differ.  However, we can more easily just do the string equality
        # comparison, since it will always be the case that 0x20 will be less
        # than any of the other allowed characters in the strings.
        if self.file_ident == b'\x00':
            if other.file_ident == b'\x00':
                return False
            return True
        if other.file_ident == b'\x00':
            return False

        if self.file_ident == b'\x01':
            if other.file_ident == b'\x00':
                return False
            return True

        if other.file_ident == b'\x01':
            # If self.file_ident was '\x00', it would have been caught above.
            return False
        return self.file_ident < other.file_ident

    def __ne__(self, other):
        # Note that we very specifically do not check the extent_location when comparing
        # directory records.  In a lazy-extent assigning world, the extents are not
        # reliable, so we just rely on the rest of the fields to tell us if two
        # directory records are the same.
        return self.dr_len != other.dr_len or self.xattr_len != other.xattr_len or self.data_length != other.data_length or self.date != other.date or self.file_flags != other.file_flags or self.file_unit_size != other.file_unit_size or self.interleave_gap_size != other.interleave_gap_size or self.seqnum != other.seqnum or self.len_fi != other.len_fi or self.file_ident != other.file_ident

    def __eq__(self, other):
        return not self.__ne__(other)


class DROpenData(object):
    '''
    A class to be a contextmanager for opening data on a DirectoryRecord object.
    '''
    def __init__(self, drobj, logical_block_size):
        self.drobj = drobj
        while self.drobj.target is not None:
            self.drobj = self.drobj.target
        self.logical_block_size = logical_block_size

    def __enter__(self):
        if self.drobj.isdir:
            raise pycdlibexception.PyCdlibInternalError("Cannot write out a directory")

        if self.drobj.manage_fp:
            # In the case that we are managing the FP, the data_fp member
            # actually contains the filename, not the fp.  Use that to
            # our advantage here.
            self.data_fp = open(self.drobj.data_fp, 'rb')
        else:
            self.data_fp = self.drobj.data_fp

        if self.drobj.original_data_location == self.drobj.DATA_ON_ORIGINAL_ISO:
            self.data_fp.seek(self.drobj.orig_extent_loc * self.logical_block_size)
        else:
            self.data_fp.seek(0)

        return self.data_fp, self.drobj.data_length

    def __exit__(self, *args):
        if self.drobj.manage_fp:
            self.data_fp.close()
