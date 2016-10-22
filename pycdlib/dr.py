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
The class to support ISO9660 Directory Records.
'''

from __future__ import absolute_import

import struct
import bisect

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
            raise pycdlibexception.PyCdlibException("This XARecord is already initialized!")

        (self.group_id, self.user_id, self.attributes, signature, self.filenum,
         unused) = struct.unpack_from("=HHH2sB5s", xastr, 0)

        if signature != b"XA":
            raise pycdlibexception.PyCdlibException("Invalid signature on the XARecord!")

        if unused != b'\x00\x00\x00\x00\x00':
            raise pycdlibexception.PyCdlibException("Unused fields should be 0")

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
            raise pycdlibexception.PyCdlibException("This XARecord is already initialized!")

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
            raise pycdlibexception.PyCdlibException("This XARecord is not yet initialized!")

        return struct.pack("=HHH2sB5s", self.group_id, self.user_id, self.attributes, b'XA', self.filenum, b'\x00'*5)

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

    def __init__(self):
        self.initialized = False
        self.new_extent_loc = None
        self.boot_info_table = None
        self.linked_records = []
        self.target = None
        self.fmt = "=BBLLLL7sBBBHHB"
        self.manage_fp = False
        self.hidden = False

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        if len(record) > 255:
            # Since the length is supposed to be 8 bits, this should never
            # happen.
            raise pycdlibexception.PyCdlibException("Directory record longer than 255 bytes!")

        (self.dr_len, self.xattr_len, extent_location_le, extent_location_be,
         data_length_le, data_length_be_unused, dr_date, self.file_flags,
         self.file_unit_size, self.interleave_gap_size, seqnum_le, seqnum_be,
         self.len_fi) = struct.unpack_from(self.fmt, record[:33], 0)

        # In theory we should have a check here that checks to make sure that
        # the length of the record we were passed in matches the data record
        # length.  However, we have seen ISOs in the wild where this is
        # incorrect, so we elide the check here.

        if extent_location_le != utils.swab_32bit(extent_location_be):
            raise pycdlibexception.PyCdlibException("Little-endian (%d) and big-endian (%d) extent location disagree" % (extent_location_le, utils.swab_32bit(extent_location_be)))
        self.orig_extent_loc = extent_location_le
        self.new_extent_loc = None

        # Theoretically, we should check to make sure that the little endian
        # data length is the same as the big endian data length.  In practice,
        # though, we've seen ISOs where this is wrong.  Skip the check, and just
        # pick the little-endian as the "actual" size, and hope for the best.

        self.data_length = data_length_le

        if seqnum_le != utils.swab_16bit(seqnum_be):
            raise pycdlibexception.PyCdlibException("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        self.date = dates.DirectoryRecordDate()
        self.date.parse(dr_date)

        # OK, we've unpacked what we can from the beginning of the string.  Now
        # we have to use the len_fi to get the rest.

        self.curr_length = 0
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
                raise pycdlibexception.PyCdlibException("Invalid root directory entry identifier")
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
                if record[record_offset+6:record_offset+8] == b'XA':
                    self.xa_record = XARecord()
                    self.xa_record.parse(record[record_offset:record_offset+14])
                    record_offset += 14

            if len(record[record_offset:]) >= 2 and record[record_offset:record_offset+2] in [b'SP', b'RR', b'CE', b'PX', b'ER', b'ES', b'PN', b'SL', b'NM', b'CL', b'PL', b'TF', b'SF', b'RE']:
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
                                      bytes_to_skip)

        if self.xattr_len != 0:
            if self.file_flags & (1 << self.FILE_FLAG_RECORD_BIT):
                raise pycdlibexception.PyCdlibException("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise pycdlibexception.PyCdlibException("Protection Bit not allowed with Extended Attributes")

        self.initialized = True

        if self.rock_ridge is None:
            ret = None
        else:
            ret = self.rock_ridge.rr_version

        return ret

    def _new(self, mangledname, parent, seqnum, isdir, length, rock_ridge,
             rr_name, rr_symlink_target, rr_relocated_child, rr_relocated,
             rr_relocated_parent, xa):
        '''
        Internal method to create a new Directory Record.

        Parameters:
         mangledname - The ISO9660 name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number to associate with this directory record.
         isdir - Whether this directory record represents a directory.
         length - The length of the data for this directory record.
         rock_ridge - Whether this directory record should have a Rock Ridge
                      entry associated with it.
         rr_name - The Rock Ridge name to associate with this directory record.
         rr_symlink_target - The target for the symlink, if this is a symlink
                             record (otherwise, None).
         rr_relocated_child - True if this is a directory record for a rock ridge relocated child.
         rr_relocated - True if this is a directory record for a relocated entry.
         rr_relocated_parent - True if this is a directory record for a rock ridge relocated parent.
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

        if length > 2**32-1:
            raise pycdlibexception.PyCdlibException("Maximum supported file length is 2^32-1")

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
        self.dr_len = struct.calcsize(self.fmt) + self.len_fi

        # When adding a new directory, we always add a full extent.  This number
        # tracks how much of that block we are using so that we can figure out
        # if we need to allocate a new block.
        self.curr_length = 0

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
        self.file_unit_size = 0 # FIXME: we don't support setting file unit size for now
        self.interleave_gap_size = 0 # FIXME: we don't support setting interleave gap size for now
        self.xattr_len = 0 # FIXME: we don't support xattrs for now
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
        if rock_ridge is not None:
            self.rock_ridge = rockridge.RockRidge()
            is_first_dir_record_of_root = self.file_ident == b'\x00' and parent.parent is None
            bytes_to_skip = 0
            if xa:
                bytes_to_skip = XARecord.length()
            self.dr_len = self.rock_ridge.new(is_first_dir_record_of_root,
                                              rr_name, self.isdir,
                                              rr_symlink_target, rock_ridge,
                                              rr_relocated_child,
                                              rr_relocated,
                                              rr_relocated_parent,
                                              bytes_to_skip,
                                              self.dr_len)

            if self.isdir:
                if parent.parent is not None:
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

        self.initialized = True

    def new_symlink(self, name, parent, rr_path, seqnum, rock_ridge, rr_name, xa):
        '''
        Create a new symlink Directory Record.  This implies that the new
        record will be Rock Ridge.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         rr_path - The symlink target for this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - The version of Rock Ridge to use for this directory record.
         rr_name - The Rock Ridge name for this directory record.
         xa - True if this is an Extended Attribute record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(name, parent, seqnum, False, 0, rock_ridge, rr_name, rr_path, False, False, False, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(name, parent, seqnum, False, 0, None, None, None, False, False, False, False)

    def new_fp(self, fp, manage_fp, length, isoname, parent, seqnum, rock_ridge, rr_name, xa):
        '''
        Create a new file Directory Record.

        Parameters:
         fp - A file object that contains the data for this directory record.
         manage_fp - True if pycdlib is managing the file object, False otherwise.
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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self.manage_fp = manage_fp
        self._new(isoname, parent, seqnum, False, length, rock_ridge, rr_name,
                  None, False, False, False, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(b'\x00', None, seqnum, True, log_block_size, None, None, None, False, False, False, False)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(b'\x00', root, seqnum, True, log_block_size, rock_ridge, None,
                  None, False, False, False, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(b'\x01', root, seqnum, True, log_block_size, rock_ridge, None,
                  None, False, False, rr_relocated_parent, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(name, parent, seqnum, True, log_block_size, rock_ridge,
                  rr_name, None, rr_relocated_child, rr_relocated, False, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self.target = target
        self._new(isoname, parent, seqnum, False, length, rock_ridge, rr_name, None, False, False, False, xa)

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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new("", parent, seqnum, False, length, None, "", None, False, False, False, False)
        self.data_fp = fp
        self.manage_fp = False
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
            raise pycdlibexception.PyCdlibException("Directory Record already initialized")

        self._new(b"", parent, seqnum, False, rec.data_length, None, b"", None, False, False, False, False)
        self.data_fp = rec.data_fp
        self.manage_fp = rec.manage_fp
        self.hidden = True
        self.original_data_location = rec.original_data_location
        self.orig_extent_loc = extent_loc

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self.data_length = length

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

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
                    raise pycdlibexception.PyCdlibException("Parent %s already has a child named %s" % (self.file_identifier(), child.file_identifier()))
        self.children.insert(index, child)

        # Check if child.dr_len will go over a boundary; if so, increase our
        # data length.
        overflowed = False
        self.curr_length += child.directory_record_length()
        if self.curr_length > self.data_length:
            overflowed = True
            # When we overflow our data length, we always add a full block.
            self.data_length += logical_block_size

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        underflow = False
        self.curr_length -= child.directory_record_length()
        if (self.data_length - self.curr_length) > logical_block_size:
            self.data_length -= logical_block_size
            underflow = True

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")
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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = dates.DirectoryRecordDate()
        self.date.new()

        padlen = struct.calcsize(self.fmt) + self.len_fi
        padstr = b'\x00' * (padlen % 2)

        extent_loc = self._extent_location()

        xa_rec = b""
        if self.xa_record is not None:
            xa_rec = self.xa_record.record()
        rr_rec = b""
        if self.rock_ridge is not None:
            rr_rec = self.rock_ridge.record()

        outlist = [b"%s%s%s%s%s" % (struct.pack(self.fmt, self.dr_len, self.xattr_len,
                                                extent_loc, utils.swab_32bit(extent_loc),
                                                self.data_length, utils.swab_32bit(self.data_length),
                                                self.date.record(), self.file_flags,
                                                self.file_unit_size, self.interleave_gap_size,
                                                self.seqnum, utils.swab_16bit(self.seqnum),
                                                self.len_fi), self.file_ident, padstr, xa_rec, rr_rec)]

        outlist.append(b'\x00' * (len(outlist[0]) % 2))

        return b"".join(outlist)

    def open_data(self, logical_block_size):
        '''
        A method to prepare the data file object for reading.  This is called
        when a higher layer wants to read data associated with this Directory
        Record, which implies that this directory record is a file.  The
        preparation consists of seeking to the appropriate location of the
        file object, based on whether this data is coming from the original
        ISO or was added later.

        Parameters:
         logical_block_size - The logical block size to use when seeking.
        Returns:
         A tuple containing a reference to the file object and the total length
         of the data for this Directory Record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        if self.isdir:
            raise pycdlibexception.PyCdlibException("Cannot write out a directory")

        if self.target is not None:
            return self.target.open_data(logical_block_size)

        if self.original_data_location == self.DATA_ON_ORIGINAL_ISO:
            self.data_fp.seek(self.orig_extent_loc * logical_block_size)
        else:
            self.data_fp.seek(0)

        return self.data_fp,self.data_length

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

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
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        self.boot_info_table = boot_info_table

    def close_managed_fp(self):
        '''
        A method to close file pointers that are being managed internally.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record not yet initialized")

        if self.manage_fp:
            self.data_fp.close()
            self.manage_fp = False

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
        return self.dr_len != other.dr_len or self.xattr_len != other.xattr_len or self._extent_location() != other._extent_location() or self.data_length != other.data_length or self.date != other.date or self.file_flags != other.file_flags or self.file_unit_size != other.file_unit_size or self.interleave_gap_size != other.interleave_gap_size or self.seqnum != other.seqnum or self.len_fi != other.len_fi

    def __eq__(self, other):
        return not self.__ne__(other)
