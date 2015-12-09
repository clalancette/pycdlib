# Copyright (C) 2015  Chris Lalancette <clalancette@gmail.com>

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

import struct
import time
import bisect
import collections
import StringIO
import random
import os

from dates import *
from rockridge import *
from pyisoexception import *
from utils import *
from eltorito import *

# There are a number of specific ways that numerical data is stored in the
# ISO9660/Ecma-119 standard.  In the text these are reference by the section
# number they are stored in.  A brief synopsis:
#
# 7.1.1 - 8-bit number
# 7.2.3 - 16-bit number, stored first as little-endian then as big-endian (4 bytes total)
# 7.3.1 - 32-bit number, stored as little-endian
# 7.3.2 - 32-bit number ,stored as big-endian
# 7.3.3 - 32-bit number, stored first as little-endian then as big-endian (8 bytes total)

VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD = 0
VOLUME_DESCRIPTOR_TYPE_PRIMARY = 1
VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY = 2
VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION = 3
VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR = 255

class HeaderVolumeDescriptor(object):
    '''
    A parent class for Primary and Supplementary Volume Descriptors.  The two
    types of descriptors share much of the same functionality, so this is the
    parent class that both classes derive from.
    '''
    def __init__(self):
        self.initialized = False
        self.path_table_records = []

    def parse(self, vd, data_fp, extent_loc):
        '''
        The unimplemented parse method for the parent class.  The child class
        is expected to implement this.

        Parameters:
         vd - The string to parse.
         data_fp - The file descriptor to associate with the root directory
                   record of the volume descriptor.
         extent_loc - The extent location that this Header Volume Descriptor resides
                      in on the original ISO.
        Returns:
         Nothing.
        '''
        raise PyIsoException("Child class must implement parse")

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use):
        '''
        The unimplemented new method for the parent class.  The child class is
        expected to implement this.

        Parameters:
         flags - Optional flags to set for the header.
         sys_ident - The system identification string to use on the new ISO.
         vol_ident - The volume identification string to use on the new ISO.
         set_size - The size of the set of ISOs this ISO is a part of.
         seqnum - The sequence number of the set of this ISO.
         log_block_size - The logical block size to use for the ISO.  While
                          ISO9660 technically supports sizes other than 2048
                          (the default), this almost certainly doesn't work.
         vol_set_ident - The volume set identification string to use on the
                         new ISO.
         pub_ident_str - The publisher identification string to use on the
                         new ISO.
         preparer_ident_str - The preparer identification string to use on the
                              new ISO.
         app_ident_str - The application identification string to use on the
                         new ISO.
         copyright_file - The name of a file at the root of the ISO to use as
                          the copyright file.
         abstract_file - The name of a file at the root of the ISO to use as the
                         abstract file.
         bibli_file - The name of a file at the root of the ISO to use as the
                      bibliographic file.
         vol_expire_date - The date that this ISO will expire at.
         app_use - Arbitrary data that the application can stuff into the
                   primary volume descriptor of this ISO.
        Returns:
         Nothing.
        '''
        raise PyIsoException("Child class must implement new")

    def path_table_size(self):
        '''
        A method to get the path table size of the Volume Descriptor.

        Parameters:
         None.
        Returns:
         Path table size in bytes.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        return self.path_tbl_size

    def add_path_table_record(self, ptr):
        '''
        A method to add a new path table record to the Volume Descriptor.

        Parameters:
         ptr - The new path table record object to add to the list of path
               table records.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")
        # We keep the list of children in sorted order, based on the __lt__
        # method of the PathTableRecord object.
        bisect.insort_left(self.path_table_records, ptr)

    def path_table_record_be_equal_to_le(self, le_index, be_record):
        '''
        A method to compare a little-endian path table record to its
        big-endian counterpart.  This is used to ensure that the ISO is sane.

        Parameters:
         le_index - The index of the little-endian path table record in this
                    object's path_table_records.
         be_record - The big-endian object to compare with the little-endian
                     object.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        le_record = self.path_table_records[le_index]
        if be_record.len_di != le_record.len_di or \
           be_record.xattr_length != le_record.xattr_length or \
           swab_32bit(be_record.extent_location) != le_record.extent_location or \
           swab_16bit(be_record.parent_directory_num) != le_record.parent_directory_num or \
           be_record.directory_identifier != le_record.directory_identifier:
            return False
        return True

    def set_ptr_dirrecord(self, dirrecord):
        '''
        A method to store a directory record that is associated with a path
        table record.  This will be used during extent reshuffling to update
        all of the path table records with the correct values from the directory
        records.  Note that a path table record is said to be associated with
        a directory record when the file identification of the two match.

        Parameters:
         dirrecord - The directory record object to associate with a path table
                     record with the same file identification.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")
        if dirrecord.is_root:
            ptr_index = 0
        else:
            ptr_index = self.find_ptr_index_matching_ident(dirrecord.file_ident)
        self.path_table_records[ptr_index].set_dirrecord(dirrecord)

    def find_ptr_index_matching_ident(self, child_ident):
        '''
        A method to find a path table record index that matches a particular
        filename.

        Parameters:
         child_ident - The name of the file to find.
        Returns:
         Path table record index corresponding to the filename.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        # This is equivalent to bisect.bisect_left() (and in fact the code is
        # modified from there).  However, we already overrode the __lt__ method
        # in PathTableRecord(), and we wanted our own comparison between two
        # strings, so we open-code it here.  Also note that the first entry in
        # self.path_table_records is always the root, and since we can't remove
        # the root we don't have to look at it.
        lo = 1
        hi = len(self.path_table_records)
        while lo < hi:
            mid = (lo + hi) // 2
            if ptr_lt(self.path_table_records[mid].directory_identifier, child_ident):
                lo = mid + 1
            else:
                hi = mid
        saved_ptr_index = lo

        if saved_ptr_index == len(self.path_table_records):
            raise PyIsoException("Could not find path table record!")

        return saved_ptr_index

    def add_to_space_size(self, addition_bytes):
        '''
        A method to add bytes to the space size tracked by this Volume
        Descriptor.

        Parameters:
         addition_bytes - The number of bytes to add to the space size.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")
        # The "addition" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size += ceiling_div(addition_bytes, self.log_block_size)

    def remove_from_space_size(self, removal_bytes):
        '''
        Remove bytes from the volume descriptor.

        Parameters:
         removal_bytes - The number of bytes to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")
        # The "removal" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size -= ceiling_div(removal_bytes, self.log_block_size)

    def root_directory_record(self):
        '''
        A method to get a handle to this Volume Descriptor's root directory
        record.

        Parameters:
         None.
        Returns:
         DirectoryRecord object representing this Volume Descriptor's root
         directory record.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def logical_block_size(self):
        '''
        A method to get this Volume Descriptor's logical block size.

        Parameters:
         None.
        Returns:
         Size of this Volume Descriptor's logical block size in bytes.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        return self.log_block_size

    def add_entry(self, flen, ptr_size=0):
        '''
        Add the length of a new file to the volume descriptor.

        Parameters:
         flen - The length of the file to add.
         ptr_size - The length to add to the path table record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        # First add to the path table size.
        self.path_tbl_size += ptr_size
        if (ceiling_div(self.path_tbl_size, 4096) * 2) > self.path_table_num_extents:
            # If we overflowed the path table size, then we need to update the
            # space size.  Since we always add two extents for the little and
            # two for the big, add four total extents.  The locations will be
            # fixed up during reshuffle_extents.
            self.add_to_space_size(4 * self.log_block_size)
            self.path_table_num_extents += 2

        # Now add to the space size.
        self.add_to_space_size(flen)

    def remove_entry(self, flen, directory_ident=None):
        '''
        Remove an entry from the volume descriptor.

        Parameters:
         flen - The number of bytes to remove.
         directory_ident - The identifier for the directory to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        # First remove from our space size.
        self.remove_from_space_size(flen)

        if directory_ident != None:
            ptr_index = self.find_ptr_index_matching_ident(directory_ident)

            # Next remove from the Path Table Record size.
            self.path_tbl_size -= PathTableRecord.record_length(self.path_table_records[ptr_index].len_di)
            new_extents = ceiling_div(self.path_tbl_size, 4096) * 2

            if new_extents > self.path_table_num_extents:
                # This should never happen.
                raise PyIsoException("This should never happen")
            elif new_extents < self.path_table_num_extents:
                self.remove_from_space_size(4 * self.log_block_size)
                self.path_table_num_extents -= 2
            # implicit else, no work to do

            del self.path_table_records[ptr_index]

    def sequence_number(self):
        '''
        A method to get this Volume Descriptor's sequence number.

        Parameters:
         None.
        Returns:
         This Volume Descriptor's sequence number.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        return self.seqnum

    def find_parent_dirnum(self, parent):
        '''
        A method to find the directory number corresponding to the parent.

        Parameters:
         parent - The parent to find the directory number fo.
        Returns:
         An integer directory number corresponding to the parent.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        if parent.is_root:
            ptr_index = 0
        else:
            ptr_index = self.find_ptr_index_matching_ident(parent.file_ident)

        return self.path_table_records[ptr_index].directory_num

    def update_ptr_extent_locations(self):
        '''
        Walk the path table records, updating the extent locations for each one
        based on the directory record.  This is used after reassigning extents
        on the ISO so that the path table records will all be up-to-date.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor is not yet initialized")

        for ptr in self.path_table_records:
            ptr.update_extent_location_from_dirrecord()

class FileOrTextIdentifier(object):
    '''
    A class to represent a file or text identifier as specified in Ecma-119
    section 8.4.20 (Primary Volume Descriptor Publisher Identifier),
    section 8.4.21 (Primary Volume Descriptor Data Preparer Identifier),
    and section 8.4.22 (Primary Volume Descriptor Application Identifier).  This
    identifier can either be a text string or the name of a file.  If it is a
    file, then the first byte will be 0x5f, the file should exist in the root
    directory record, and the file should be ISO level 1 interchange compliant
    (no more than 8 characters for the name and 3 characters for the extension).
    There are two main ways to use this class: either to instantiate and then
    parse a string to fill in the fields (the parse() method), or to create a
    new entry with a text string and whether this is a filename or not (the
    new() method).
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, ident_str, is_primary):
        '''
        Parse a file or text identifier out of a string.

        Parameters:
          ident_str  - The string to parse the file or text identifier from.
          is_primary - Boolean describing whether this identifier is part of the
                       primary volume descriptor.  If it is, and it describes
                       a file (not a free-form string), it must be in ISO
                       interchange level 1 (MS-DOS style 8.3 format).
        Returns:
          Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This File or Text identifier is already initialized")
        self.text = ident_str
        # According to Ecma-119, 8.4.20, 8.4.21, and 8.4.22, if the first
        # byte is a 0x5f, then the rest of the field specifies a filename.
        # Ecma-119 is vague, but presumably if it is not a filename, then it
        # is an arbitrary text string.
        self.isfile = False
        if ident_str[0] == "\x5f":
            # If the identifier is in the PVD, Ecma-119 says that it must
            # specify a file at the root directory and the identifier must
            # be 8.3 (so interchange level 1).  If the identifier is in an SVD,
            # Ecma-119 places no restrictions on the length of the filename
            # (though it implicitly has to be less than 31 so it can fit in
            # a directory record).

            # First find the end of the filename, which should be a space.
            space_index = -1
            for index,val in enumerate(ident_str[1:]):
                if ident_str[index] == ' ':
                    # Once we see a space, we know we are at the end of the
                    # filename.
                    space_index = index
                    break

            if is_primary:
                if space_index == -1:
                    # Never found the end of the filename, throw an exception.
                    raise PyIsoException("Invalid filename for file identifier")

                interchange_level = 1
            else:
                if space_index == -1:
                    space_index = None
                interchange_level = 3

            self.filename = ident_str[1:space_index]
            check_iso9660_filename(self.filename, interchange_level)

            self.isfile = True
            self.text = ident_str[1:]

        self.initialized = True

    def new(self, text, isfile):
        '''
        Create a new file or text identifier.  If isfile is True, then this is
        expected to be the name of a file at the root directory (as specified
        in Ecma-119), and to conform to ISO interchange level 1 (for the PVD),
        or ISO interchange level 3 (for an SVD).

        Parameters:
          text   - The text to store into the identifier.
          isfile - Whether this identifier is free-form text, or refers to a
                   file.
        Returns:
          Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This File or Text identifier is already initialized")

        if len(text) > 128:
            raise PyIsoException("Length of text must be <= 128")

        if isfile:
            # Note that we do not check for whether this file identifier is in
            # 8.3 format (a requirement for primary volume descriptors).  This
            # is because we don't want to expose this to an outside user of the
            # API, so instead we have the check_filename() method below that
            # we call to do the checking at a later time.
            self.text = "{:<127}".format(text)
            self.filename = text
        else:
            self.text = "{:<128}".format(text)

        self.isfile = isfile
        self.initialized = True

    def is_file(self):
        '''
        Return True if this is a file identifier, False otherwise.

        Parameters:
          None.
        Returns:
          True if this identifier is a file, False if it is a free-form string.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        return self.isfile

    def is_text(self):
        '''
        Returns True if this is a text identifier, False otherwise.

        Parameters:
          None.
        Returns:
          True if this identifier is a free-form file, False if it is a file.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        return not self.isfile

    def record(self):
        '''
        Returns the file or text identification string suitable for recording.

        Parameters:
          None.
        Returns:
          The text representing this identifier.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        if self.isfile:
            return "\x5f" + self.text
        # implicitly a text identifier
        return self.text

    def check_filename(self, is_primary):
        '''
        Checks whether the identifier stored in this object is a file, and if
        so, checks whether this filename conforms to the rules for the correct
        interchange level.

        Parameters:
         is_primary - A boolean that should be True if this is the Primay Volume
                      Descriptor, False otherwise.  This controls whether the
                      rules for interchange level 1 or interchange level 3
                      should be followed.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")

        if self.isfile:
            interchange_level = 1
            if not is_primary:
                interchange_level = 3
            check_iso9660_filename(self.filename, interchange_level)

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
        self.fmt = "=BBLLLL7sBBBHHB"

    def parse(self, record, data_fp, parent, logical_block_size):
        '''
        Parse a directory record out of a string.

        Parameters:
         record - The string to parse for this record.
         data_fp - The file object to associate with this record.
         parent - The parent of this record.
         logical_block_size - The logical block size for the ISO.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        if len(record) > 255:
            # Since the length is supposed to be 8 bits, this should never
            # happen.
            raise PyIsoException("Directory record longer than 255 bytes!")

        (self.dr_len, self.xattr_len, extent_location_le, extent_location_be,
         data_length_le, data_length_be, dr_date, self.file_flags,
         self.file_unit_size, self.interleave_gap_size, seqnum_le, seqnum_be,
         self.len_fi) = struct.unpack(self.fmt, record[:33])

        # In theory we should have a check here that checks to make sure that
        # the length of the record we were passed in matches the data record
        # length.  However, we have seen ISOs in the wild where this is
        # incorrect, so we elide the check here.

        if extent_location_le != swab_32bit(extent_location_be):
            raise PyIsoException("Little-endian (%d) and big-endian (%d) extent location disagree" % (extent_location_le, swab_32bit(extent_location_be)))
        self.orig_extent_loc = extent_location_le
        self.new_extent_loc = None

        # Theoretically, we should check to make sure that the little endian
        # data length is the same as the big endian data length.  In practice,
        # though, we've seen ISOs where this is wrong.  Skip the check, and just
        # pick the little-endian as the "actual" size, and hope for the best.

        self.data_length = data_length_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise PyIsoException("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        self.date = DirectoryRecordDate()
        self.date.parse(dr_date)

        # OK, we've unpacked what we can from the beginning of the string.  Now
        # we have to use the len_fi to get the rest.

        self.curr_length = 0
        self.children = []
        self.is_root = False
        self.isdir = False
        self.parent = parent
        self.original_data_location = self.DATA_ON_ORIGINAL_ISO
        self.data_fp = data_fp

        self.rock_ridge = None

        if self.parent is None:
            self.is_root = True

            # A root directory entry should always be exactly 34 bytes.
            # However, we have seen ISOs in the wild that get this wrong, so we
            # elide a check for it.

            # A root directory entry should always have 0 as the identifier.
            if record[33] != '\x00':
                raise PyIsoException("Invalid root directory entry identifier")
            self.file_ident = record[33]
            self.isdir = True
        else:
            record_offset = 33
            self.file_ident = record[record_offset:record_offset + self.len_fi]
            record_offset += self.len_fi
            if self.file_flags & (1 << self.FILE_FLAG_DIRECTORY_BIT):
                self.isdir = True

            if self.len_fi % 2 == 0:
                record_offset += 1

            if len(record[record_offset:]) >= 2 and record[record_offset:record_offset+2] in ['SP', 'RR', 'CE', 'PX', 'ER', 'ES', 'PN', 'SL', 'NM', 'CL', 'PL', 'TF', 'SF', 'RE']:
                self.rock_ridge = RockRidge()
                is_first_dir_record_of_root = self.file_ident == '\x00' and parent.parent is None

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
                raise PyIsoException("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise PyIsoException("Protection Bit not allowed with Extended Attributes")

        self.initialized = True

        return self.rock_ridge != None

    def _new(self, mangledname, parent, seqnum, isdir, length, rock_ridge,
             rr_name, rr_symlink_target):
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
        self.date = DirectoryRecordDate()
        self.date.new()

        if length > 2**32-1:
            raise PyIsoException("Maximum supported file length is 2^32-1")

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

        self.dr_len += (self.dr_len % 2)

        self.rock_ridge = None
        if rock_ridge:
            self.rock_ridge = RockRidge()
            is_first_dir_record_of_root = self.file_ident == '\x00' and parent.parent is None
            # FIXME: allow the user to set the rock ridge version
            self.dr_len = self.rock_ridge.new(is_first_dir_record_of_root,
                                              rr_name, self.isdir,
                                              rr_symlink_target, "1.09",
                                              self.dr_len)

            if self.isdir:
                if parent.parent is not None:
                    if self.file_ident == '\x00':
                        self.parent.rock_ridge.add_to_file_links()
                        self.rock_ridge.add_to_file_links()
                    elif self.file_ident == '\x01':
                        self.rock_ridge.copy_file_links(self.parent.parent.children[1].rock_ridge)
                    else:
                        self.parent.rock_ridge.add_to_file_links()
                        self.parent.children[0].rock_ridge.add_to_file_links()
                else:
                    if self.file_ident != '\x00' and self.file_ident != '\x01':
                        self.parent.children[0].rock_ridge.add_to_file_links()
                        self.parent.children[1].rock_ridge.add_to_file_links()
                    else:
                        self.rock_ridge.add_to_file_links()

        self.initialized = True

    def new_symlink(self, name, parent, rr_path, seqnum, rr_name):
        '''
        Create a new symlink Directory Record.  This implies that the new
        record will be Rock Ridge.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         rr_path - The symlink target for this directory record.
         seqnum - The sequence number for this directory record.
         rr_name - The Rock Ridge name for this directory record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new(name, parent, seqnum, False, 0, True, rr_name, rr_path)

    def new_fp(self, fp, length, isoname, parent, seqnum, rock_ridge, rr_name):
        '''
        Create a new file Directory Record.

        Parameters:
         fp - A file object that contains the data for this directory record.
         length - The length of the data.
         isoname - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         rr_name - The Rock Ridge name for this directory record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self._new(isoname, parent, seqnum, False, length, rock_ridge, rr_name, None)

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
            raise PyIsoException("Directory Record already initialized")

        self._new('\x00', None, seqnum, True, log_block_size, False, None, None)

    def new_dot(self, root, seqnum, rock_ridge, log_block_size):
        '''
        Create a new "dot" Directory Record.

        Parameters:
         root - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         log_block_size - The logical block size to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new('\x00', root, seqnum, True, log_block_size, rock_ridge, None, None)

    def new_dotdot(self, root, seqnum, rock_ridge, log_block_size):
        '''
        Create a new "dotdot" Directory Record.

        Parameters:
         root - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         log_block_size - The logical block size to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new('\x01', root, seqnum, True, log_block_size, rock_ridge, None, None)

    def new_dir(self, name, parent, seqnum, rock_ridge, rr_name, log_block_size):
        '''
        Create a new directory Directory Record.

        Parameters:
         name - The name for this directory record.
         parent - The parent of this directory record.
         seqnum - The sequence number for this directory record.
         rock_ridge - Whether to make this a Rock Ridge directory record.
         rr_name - The Rock Ridge name for this directory record.
         log_block_size - The logical block size to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new(name, parent, seqnum, True, log_block_size, rock_ridge, rr_name, None)

    def add_child(self, child, vd, parsing):
        '''
        A method to add a child to this object.  Note that this is called both
        during parsing and when adding a new object to the system, so it
        it shouldn't have any functionality that is not appropriate for both.

        Parameters:
         child - The child directory record object to add.
         vd - The volume descriptor to update when adding this child.
         parsing - Whether we are parsing or not; certain functionality in here
                   only works while not parsing.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        if not self.isdir:
            raise Exception("Trying to add a child to a record that is not a directory")

        # First ensure that this is not a duplicate.
        for c in self.children:
            if c.file_ident == child.file_ident:
                if not c.is_associated_file() and not child.is_associated_file():
                    raise PyIsoException("Parent %s already has a child named %s" % (self.file_ident, child.file_ident))

        # We keep the list of children in sorted order, based on the __lt__
        # method of this object.
        bisect.insort_left(self.children, child)

        # Check if child.dr_len will go over a boundary; if so, increase our
        # data length.
        self.curr_length += child.directory_record_length()
        if self.curr_length > self.data_length:
            if parsing:
                raise PyIsoException("More records than fit into parent directory record; ISO is corrupt")
            # When we overflow our data length, we always add a full block.
            self.data_length += vd.logical_block_size()
            # This also increases the size of the complete volume, so update
            # that here.
            vd.add_to_space_size(vd.logical_block_size())

    def remove_child(self, child, index, pvd):
        '''
        A method to remove a child from this Directory Record.

        Parameters:
         child - The child DirectoryRecord object to remove.
         index - The index of the child into this DirectoryRecord children list.
         pvd - The volume descriptor to update after removing the child.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        self.curr_length -= child.directory_record_length()
        if (self.data_length - self.curr_length) > pvd.logical_block_size():
            self.data_length -= pvd.logical_block_size()
            pvd.remove_from_space_size(pvd.logical_block_size())

        if child.isdir and child.rock_ridge is not None:
            if self.parent is None:
                self.children[0].rock_ridge.remove_from_file_links()
                self.children[1].rock_ridge.remove_from_file_links()
            else:
                self.rock_ridge.remove_from_file_links()
                self.children[0].rock_ridge.remove_from_file_links()

        del self.children[index]

    def is_dir(self):
        '''
        A method to determine whether this Directory Record is a directory.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a directory, False otherwise.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
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
            raise PyIsoException("Directory Record not yet initialized")
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
            raise PyIsoException("Directory Record not yet initialized")
        return self.file_ident == '\x00'

    def is_dotdot(self):
        '''
        A method to determine whether this Directory Record is a "dotdot" entry.

        Parameters:
         None.
        Returns:
         True if this DirectoryRecord object is a "dotdot" entry, False otherwise.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.file_ident == '\x01'

    def directory_record_length(self):
        '''
        A method to determine the length of this Directory Record.

        Parameters:
         None.
        Returns:
         The length of this Directory Record.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
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
            raise PyIsoException("Directory Record not yet initialized")
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
            raise PyIsoException("Directory Record not yet initialized")
        if self.is_root:
            return '/'
        if self.file_ident == '\x00':
            return '.'
        if self.file_ident == '\x01':
            return '..'
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
            raise PyIsoException("Directory Record not yet initialized")
        return self.data_length

    def record(self):
        '''
        A method to generate the string representing this Directory Record.

        Parameters:
         None.
        Returns:
         String representing this Directory Record.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = DirectoryRecordDate()
        self.date.new()

        padstr = '\x00' * ((struct.calcsize(self.fmt) + self.len_fi) % 2)

        extent_loc = self._extent_location()

        ret = struct.pack(self.fmt, self.dr_len, self.xattr_len,
                          extent_loc, swab_32bit(extent_loc),
                          self.data_length, swab_32bit(self.data_length),
                          self.date.record(), self.file_flags,
                          self.file_unit_size, self.interleave_gap_size,
                          self.seqnum, swab_16bit(self.seqnum),
                          self.len_fi) + self.file_ident + padstr

        if self.rock_ridge is not None:
            ret += self.rock_ridge.record()

        ret += '\x00' * (len(ret) % 2)

        return ret

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
            raise PyIsoException("Directory Record not yet initialized")

        if self.isdir:
            raise PyIsoException("Cannot write out a directory")

        if self.original_data_location == self.DATA_ON_ORIGINAL_ISO:
            self.data_fp.seek(self.orig_extent_loc * logical_block_size)
        else:
            self.data_fp.seek(0)

        return self.data_fp,self.data_length

    def update_location(self, extent):
        '''
        Set the extent location of this Directory Record on the ISO.

        Parameters:
         extent - The new extent to set for this Directory Record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        self.new_extent_loc = extent

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
            raise PyIsoException("Directory Record not yet initialized")

        return self.file_flags & (1 << self.FILE_FLAG_ASSOCIATED_FILE_BIT)

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
        # FIXME: we need to implement Ecma-119 section 9.3 for the sorting
        # order; this essentially means padding out the shorter of the two with
        # 0x20 (spaces), then comparing byte-by-byte until they differ.
        if self.file_ident == '\x00':
            if other.file_ident == '\x00':
                return False
            return True
        if other.file_ident == '\x00':
            return False

        if self.file_ident == '\x01':
            if other.file_ident == '\x00':
                return False
            return True

        if other.file_ident == '\x01':
            # If self.file_ident was '\x00', it would have been caught above.
            return False
        return self.file_ident < other.file_ident

class PrimaryVolumeDescriptor(HeaderVolumeDescriptor):
    '''
    A class representing the Primary Volume Descriptor of this ISO.  Note that
    there can be one, and only one, Primary Volume Descriptor per ISO.  This is
    the first thing on the ISO that is parsed, and contains all of the basic
    information about the ISO.
    '''
    def __init__(self):
        HeaderVolumeDescriptor.__init__(self)
        self.fmt = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def parse(self, vd, data_fp, extent_loc):
        '''
        Parse a primary volume descriptor out of a string.

        Parameters:
         vd - The string containing the Primary Volume Descriptor.
         data_fp - A file object containing the root directory record.
         extent_loc - Ignored, extent location is fixed for the Primary Volume
                      Descriptor.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is already initialized")

        # According to Ecma-119, we have to parse both the
        # little-endian and bit-endian versions of:
        #
        # Space Size
        # Set Size
        # Seq Num
        # Logical Block Size
        # Path Table Size
        # Path Table Location
        # Optional Path Table Location
        #
        # In doing this, we:
        # a) Check to make sure that the little-endian and big-endian
        # versions agree with each other.
        # b) Only store one type in the class, and generate the other one
        # as necessary.
        (self.descriptor_type, self.identifier, self.version, unused1,
         self.system_identifier, self.volume_identifier, unused2,
         space_size_le, space_size_be, unused3, set_size_le, set_size_be,
         seqnum_le, seqnum_be, logical_block_size_le, logical_block_size_be,
         path_table_size_le, path_table_size_be, self.path_table_location_le,
         self.optional_path_table_location_le, self.path_table_location_be,
         self.optional_path_table_location_be, root_dir_record,
         self.volume_set_identifier, pub_ident_str, prepare_ident_str,
         app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, unused5) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.4.1, the primary volume descriptor type
        # should be 1.
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_PRIMARY:
            raise PyIsoException("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001".
        if self.identifier != "CD001":
            raise PyIsoException("invalid CD isoIdentification")
        # According to Ecma-119, 8.4.3, the version should be 1.
        if self.version != 1:
            raise PyIsoException("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.4, the first unused field should be 0.
        if unused1 != 0:
            raise PyIsoException("data in unused field not zero")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0.
        if unused2 != 0:
            raise PyIsoException("data in 2nd unused field not zero")
        # According to Ecma-119, 8.4.9, the third unused field should be all 0.
        if unused3 != '\x00'*32:
            raise PyIsoException("data in 3rd unused field not zero")
        # According to Ecma-119, 8.4.30, the file structure version should be 1.
        if self.file_structure_version != 1:
            raise PyIsoException("File structure version expected to be 1")
        # According to Ecma-119, 8.4.31, the fourth unused field should be 0.
        if unused4 != 0:
            raise PyIsoException("data in 4th unused field not zero")
        # According to Ecma-119, the last 653 bytes of the PVD should be all 0.
        if unused5 != '\x00'*653:
            raise PyIsoException("data in 5th unused field not zero")

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other.
        if space_size_le != swab_32bit(space_size_be):
            raise PyIsoException("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != swab_16bit(set_size_be):
            raise PyIsoException("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise PyIsoException("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != swab_16bit(logical_block_size_be):
            raise PyIsoException("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != swab_32bit(path_table_size_be):
            raise PyIsoException("Little-endian and big-endian path table size disagree")
        self.path_tbl_size = path_table_size_le
        self.path_table_num_extents = ceiling_div(self.path_tbl_size, 4096) * 2

        self.path_table_location_be = swab_32bit(self.path_table_location_be)

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.parse(pub_ident_str, True)
        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.parse(prepare_ident_str, True)
        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.parse(app_ident_str, True)
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, data_fp, None, self.log_block_size)

        self.initialized = True

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use):
        '''
        Create a new Primary Volume Descriptor.

        Parameters:
         flags - Ignored.
         sys_ident - The system identification string to use on the new ISO.
         vol_ident - The volume identification string to use on the new ISO.
         set_size - The size of the set of ISOs this ISO is a part of.
         seqnum - The sequence number of the set of this ISO.
         log_block_size - The logical block size to use for the ISO.  While
                          ISO9660 technically supports sizes other than 2048
                          (the default), this almost certainly doesn't work.
         vol_set_ident - The volume set identification string to use on the
                         new ISO.
         pub_ident - The publisher identification string to use on the new ISO.
         preparer_ident - The preparer identification string to use on the new
                          ISO.
         app_ident - The application identification string to use on the new
                     ISO.
         copyright_file - The name of a file at the root of the ISO to use as
                          the copyright file.
         abstract_file - The name of a file at the root of the ISO to use as the
                         abstract file.
         bibli_file - The name of a file at the root of the ISO to use as the
                      bibliographic file.
         vol_expire_date - The date that this ISO will expire at.
         app_use - Arbitrary data that the application can stuff into the
                   primary volume descriptor of this ISO.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is already initialized")

        if flags != 0:
            raise PyIsoException("Non-zero flags not allowed for a PVD")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_PRIMARY
        self.identifier = "CD001"
        self.version = 1

        if len(sys_ident) > 32:
            raise PyIsoException("The system identifer has a maximum length of 32")
        self.system_identifier = "{:<32}".format(sys_ident)

        if len(vol_ident) > 32:
            raise PyIsoException("The volume identifier has a maximum length of 32")
        self.volume_identifier = "{:<32}".format(vol_ident)

        # The space_size is the number of extents (2048-byte blocks) in the
        # ISO.  We know we will at least have the system area (16 extents),
        # the PVD (1 extent), the Volume Terminator (2 extents), 2 extents
        # for the little endian path table record, 2 extents for the big endian
        # path table record, and 1 extent for the root directory record,
        # for a total of 24 extents to start with.
        self.space_size = 24
        self.set_size = set_size
        if seqnum > set_size:
            raise PyIsoException("Sequence number must be less than or equal to set size")
        self.seqnum = seqnum
        self.log_block_size = log_block_size
        # The path table size is in bytes, and is always at least 10 bytes
        # (for the root directory record).
        self.path_tbl_size = 10
        self.path_table_num_extents = ceiling_div(self.path_tbl_size, 4096) * 2
        # By default the Little Endian Path Table record starts at extent 19
        # (right after the Volume Terminator).
        self.path_table_location_le = 19
        # By default the Big Endian Path Table record starts at extent 21
        # (two extents after the Little Endian Path Table Record).
        self.path_table_location_be = 21
        # FIXME: we don't support the optional path table location right now
        self.optional_path_table_location_le = 0
        self.optional_path_table_location_be = 0
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.new_root(seqnum, self.log_block_size)

        if len(vol_set_ident) > 128:
            raise PyIsoException("The maximum length for the volume set identifier is 128")
        self.volume_set_identifier = "{:<128}".format(vol_set_ident)

        self.publisher_identifier = pub_ident
        self.publisher_identifier.check_filename(True)

        self.preparer_identifier = preparer_ident
        self.preparer_identifier.check_filename(True)

        self.application_identifier = app_ident
        self.application_identifier.check_filename(True)

        self.copyright_file_identifier = "{:<37}".format(copyright_file)
        self.abstract_file_identifier = "{:<37}".format(abstract_file)
        self.bibliographic_file_identifier = "{:<37}".format(bibli_file)

        # We make a valid volume creation and volume modification date here,
        # but they will get overwritten during writeout.
        now = time.time()
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.new(now)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.new(now)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.new(vol_expire_date)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.new(now)
        self.file_structure_version = 1

        if len(app_use) > 512:
            raise PyIsoException("The maximum length for the application use is 512")
        self.application_use = "{:<512}".format(app_use)

        self.initialized = True

    def record(self):
        '''
        A method to generate the string representing this Primary Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this Primary Volume Descriptor.
        '''
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        now = time.time()

        vol_create_date = VolumeDescriptorDate()
        vol_create_date.new(now)

        vol_mod_date = VolumeDescriptorDate()
        vol_mod_date.new(now)

        return struct.pack(self.fmt, self.descriptor_type, self.identifier,
                           self.version, 0, self.system_identifier,
                           self.volume_identifier, 0, self.space_size,
                           swab_32bit(self.space_size), '\x00'*32,
                           self.set_size, swab_16bit(self.set_size),
                           self.seqnum, swab_16bit(self.seqnum),
                           self.log_block_size, swab_16bit(self.log_block_size),
                           self.path_tbl_size, swab_32bit(self.path_tbl_size),
                           self.path_table_location_le,
                           self.optional_path_table_location_le,
                           swab_32bit(self.path_table_location_be),
                           self.optional_path_table_location_be,
                           self.root_dir_record.record(),
                           self.volume_set_identifier,
                           self.publisher_identifier.record(),
                           self.preparer_identifier.record(),
                           self.application_identifier.record(),
                           self.copyright_file_identifier,
                           self.abstract_file_identifier,
                           self.bibliographic_file_identifier,
                           vol_create_date.record(),
                           vol_mod_date.record(),
                           self.volume_expiration_date.record(),
                           self.volume_effective_date.record(),
                           self.file_structure_version, 0, self.application_use,
                           "\x00" * 653)

    @staticmethod
    def extent_location():
        '''
        A class method to return the Primary Volume Descriptors extent location.
        '''
        return 16

class VolumeDescriptorSetTerminator(object):
    '''
    A class that represents a Volume Descriptor Set Terminator.  The VDST
    signals the end of volume descriptors on the ISO.
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sB2041s"

    def parse(self, vd, extent):
        '''
        A method to parse a Volume Descriptor Set Terminator out of a string.

        Parameters:
         vd - The string to parse.
         extent - The extent this VDST is currently located at.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator already initialized")

        (self.descriptor_type, self.identifier, self.version,
         unused) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.3.1, the volume descriptor set terminator
        # type should be 255
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
            raise PyIsoException("Invalid descriptor type")
        # According to Ecma-119, 8.3.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise PyIsoException("Invalid identifier")
        # According to Ecma-119, 8.3.3, the version should be 1
        if self.version != 1:
            raise PyIsoException("Invalid version")
        # According to Ecma-119, 8.3.4, the rest of the terminator should be 0;
        # however, we have seen ISOs in the wild that put stuff into this field.
        # Just ignore it.

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self.initialized = True

    def new(self):
        '''
        A method to create a new Volume Descriptor Set Terminator.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR
        self.identifier = "CD001"
        self.version = 1
        self.orig_extent_loc = None
        # This will get set during reshuffle_extent.
        self.new_extent_loc = 0

        self.initialized = True

    def record(self):
        '''
        A method to generate a string representing this Volume Descriptor Set
        Terminator.

        Parameters:
         None.
        Returns:
         String representing this Volume Descriptor Set Terminator.
        '''
        if not self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator not yet initialized")
        return struct.pack(self.fmt, self.descriptor_type,
                           self.identifier, self.version, "\x00" * 2041)

    def extent_location(self):
        '''
        A method to get this Volume Descriptor Set Terminator's extent location.

        Parameters:
         None.
        Returns:
         Integer extent location.
        '''
        if not self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

class BootRecord(object):
    '''
    A class representing an ISO9660 Boot Record.
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sB32s32s1977s"

    def parse(self, vd, extent_loc):
        '''
        A method to parse a Boot Record out of a string.

        Parameters:
         vd - The string to parse the Boot Record out of.
         extent_loc - The extent location this Boot Record is current at.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Boot Record already initialized")

        (self.descriptor_type, self.identifier, self.version,
         self.boot_system_identifier, self.boot_identifier,
         self.boot_system_use) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.2.1, the boot record type should be 0
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
            raise PyIsoException("Invalid descriptor type")
        # According to Ecma-119, 8.2.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise PyIsoException("Invalid identifier")
        # According to Ecma-119, 8.2.3, the version should be 1
        if self.version != 1:
            raise PyIsoException("Invalid version")

        self.orig_extent_loc = extent_loc
        self.new_extent_loc = None

        self.initialized = True

    def new(self, boot_system_id):
        '''
        A method to create a new Boot Record.

        Parameters:
         boot_system_id - The system identifier to associate with this Boot
                          Record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise Exception("Boot Record already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD
        self.identifier = "CD001"
        self.version = 1
        self.boot_system_identifier = "{:\x00<32}".format(boot_system_id)
        self.boot_identifier = "\x00"*32 # FIXME: we may want to allow the user to set this
        self.boot_system_use = "\x00"*197 # This will be set later

        self.orig_extent_loc = None
        # This is wrong, but will be corrected at reshuffle_extent time.
        self.new_extent_loc = 0

        self.initialized = True

    def record(self):
        '''
        A method to generate a string representing this Boot Record.

        Parameters:
         None.
        Returns:
         A string representing this Boot Record.
        '''
        if not self.initialized:
            raise PyIsoException("Boot Record not yet initialized")

        return struct.pack(self.fmt, self.descriptor_type, self.identifier,
                           self.version, self.boot_system_identifier,
                           self.boot_identifier, self.boot_system_use)

    def update_boot_system_use(self, boot_sys_use):
        '''
        A method to update the boot system use field of this Boot Record.

        Parameters:
         boot_sys_use - The new boot system use field for this Boot Record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Boot Record not yet initialized")

        self.boot_system_use = "{:\x00<197}".format(boot_sys_use)

    def extent_location(self):
        '''
        A method to get the extent locaion of this Boot Record.

        Parameters:
         None.
        Returns:
         Integer extent location of this Boot Record.
        '''
        if not self.initialized:
            raise PyIsoException("Boot Record not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

class SupplementaryVolumeDescriptor(HeaderVolumeDescriptor):
    '''
    A class that represents an ISO9660 Supplementary Volume Descriptor (used
    for Joliet records, among other things).
    '''
    def __init__(self):
        HeaderVolumeDescriptor.__init__(self)
        self.fmt = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def parse(self, vd, data_fp, extent):
        '''
        A method to parse a Supplementary Volume Descriptor from a string.

        Parameters:
         vd - The string to parse the Supplementary Volume Descriptor from.
         data_fp - The file object to associate with the root directory record.
         extent - The extent location of this Supplementary Volume Descriptor.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Supplementary Volume Descriptor already initialized")

        (self.descriptor_type, self.identifier, self.version, self.flags,
         self.system_identifier, self.volume_identifier, unused1,
         space_size_le, space_size_be, self.escape_sequences, set_size_le,
         set_size_be, seqnum_le, seqnum_be, logical_block_size_le,
         logical_block_size_be, path_table_size_le, path_table_size_be,
         self.path_table_location_le, self.optional_path_table_location_le,
         self.path_table_location_be, self.optional_path_table_location_be,
         root_dir_record, self.volume_set_identifier, pub_ident_str,
         prepare_ident_str, app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused2,
         self.application_use, unused3) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.5.1, the supplementary volume descriptor type
        # should be 2.
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
            raise PyIsoException("Invalid supplementary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001".
        if self.identifier != "CD001":
            raise PyIsoException("invalid CD isoIdentification")
        # According to Ecma-119, 8.5.2, the version should be 1.
        if self.version != 1:
            raise PyIsoException("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.5, the first unused field (after the
        # system identifier and volume identifier) should be 0.
        if unused1 != 0:
            raise PyIsoException("data in 2nd unused field not zero")
        if self.file_structure_version != 1:
            raise PyIsoException("File structure version expected to be 1")
        if unused2 != 0:
            raise PyIsoException("data in 4th unused field not zero")
        if unused3 != '\x00'*653:
            raise PyIsoException("data in 5th unused field not zero")

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other
        if space_size_le != swab_32bit(space_size_be):
            raise PyIsoException("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != swab_16bit(set_size_be):
            raise PyIsoException("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise PyIsoException("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != swab_16bit(logical_block_size_be):
            raise PyIsoException("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != swab_32bit(path_table_size_be):
            raise PyIsoException("Little-endian and big-endian path table size disagree")
        self.path_tbl_size = path_table_size_le
        self.path_table_num_extents = ceiling_div(self.path_tbl_size, 4096) * 2

        self.path_table_location_be = swab_32bit(self.path_table_location_be)

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.parse(pub_ident_str, False)
        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.parse(prepare_ident_str, False)
        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.parse(app_ident_str, False)
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, data_fp, None, self.log_block_size)

        self.joliet = False
        if (self.flags & 0x1) == 0 and self.escape_sequences[:3] in ['%/@', '%/C', '%/E']:
            self.joliet = True

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self.initialized = True

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use):
        '''
        A method to create a new Supplementary Volume Descriptor.

        Parameters:
         flags - Optional flags to set for the header.
         sys_ident - The system identification string to use on the new ISO.
         vol_ident - The volume identification string to use on the new ISO.
         set_size - The size of the set of ISOs this ISO is a part of.
         seqnum - The sequence number of the set of this ISO.
         log_block_size - The logical block size to use for the ISO.  While
                          ISO9660 technically supports sizes other than 2048
                          (the default), this almost certainly doesn't work.
         vol_set_ident - The volume set identification string to use on the
                         new ISO.
         pub_ident_str - The publisher identification string to use on the
                         new ISO.
         preparer_ident_str - The preparer identification string to use on the
                              new ISO.
         app_ident_str - The application identification string to use on the
                         new ISO.
         copyright_file - The name of a file at the root of the ISO to use as
                          the copyright file.
         abstract_file - The name of a file at the root of the ISO to use as the
                         abstract file.
         bibli_file - The name of a file at the root of the ISO to use as the
                      bibliographic file.
         vol_expire_date - The date that this ISO will expire at.
         app_use - Arbitrary data that the application can stuff into the
                   primary volume descriptor of this ISO.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This Supplementary Volume Descriptor is already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY
        self.identifier = "CD001"
        self.version = 1
        self.flags = flags

        if len(sys_ident) > 32:
            raise PyIsoException("The system identifer has a maximum length of 32")
        self.system_identifier = "{:<32}".format(sys_ident.encode('utf-16_be'))

        if len(vol_ident) > 32:
            raise PyIsoException("The volume identifier has a maximum length of 32")
        self.volume_identifier = "{:<32}".format(vol_ident.encode('utf-16_be'))

        # The space_size is the number of extents (2048-byte blocks) in the
        # ISO.  We know we will at least have the system area (16 extents),
        # the PVD (1 extent), the Volume Terminator (2 extents), 2 extents
        # for the little endian path table record, 2 extents for the big endian
        # path table record, and 1 extent for the root directory record,
        # for a total of 24 extents to start with.
        self.space_size = 24
        self.set_size = set_size
        if seqnum > set_size:
            raise PyIsoException("Sequence number must be less than or equal to set size")
        self.seqnum = seqnum
        self.log_block_size = log_block_size
        # The path table size is in bytes, and is always at least 10 bytes
        # (for the root directory record).
        self.path_tbl_size = 10
        self.path_table_num_extents = ceiling_div(self.path_tbl_size, 4096) * 2
        # By default the Little Endian Path Table record starts at extent 19
        # (right after the Volume Terminator).
        self.path_table_location_le = 19
        # By default the Big Endian Path Table record starts at extent 21
        # (two extents after the Little Endian Path Table Record).
        self.path_table_location_be = 21
        # FIXME: we don't support the optional path table location right now
        self.optional_path_table_location_le = 0
        self.optional_path_table_location_be = 0
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.new_root(seqnum, self.log_block_size)

        if len(vol_set_ident) > 128:
            raise PyIsoException("The maximum length for the volume set identifier is 128")
        self.volume_set_identifier = "{:<128}".format(vol_set_ident.encode('utf-16_be'))

        self.publisher_identifier = pub_ident
        self.publisher_identifier.check_filename(True)

        self.preparer_identifier = preparer_ident
        self.preparer_identifier.check_filename(True)

        self.application_identifier = app_ident
        self.application_identifier.check_filename(True)

        self.copyright_file_identifier = "{:<37}".format(copyright_file.encode('utf-16_be'))
        self.abstract_file_identifier = "{:<37}".format(abstract_file.encode('utf-16_be'))
        self.bibliographic_file_identifier = "{:<37}".format(bibli_file.encode('utf-16_be'))

        # We make a valid volume creation and volume modification date here,
        # but they will get overwritten during writeout.
        now = time.time()
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.new(now)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.new(now)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.new(vol_expire_date)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.new(now)
        self.file_structure_version = 1

        if len(app_use) > 512:
            raise PyIsoException("The maximum length for the application use is 512")
        self.application_use = "{:<512}".format(app_use)

        self.orig_extent_loc = None
        # This is wrong but will be set by reshuffle_extents
        self.new_extent_loc = 0

        self.escape_sequences = '%/E' # FIXME: we should allow the user to set this

        self.initialized = True

    def record(self):
        '''
        A method to generate a string representing this Supplementary Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this Supplementary Volume Descriptor.
        '''
        if not self.initialized:
            raise PyIsoException("This Supplementary Volume Descriptor is not yet initialized")

        now = time.time()

        vol_create_date = VolumeDescriptorDate()
        vol_create_date.new(now)

        vol_mod_date = VolumeDescriptorDate()
        vol_mod_date.new(now)

        return struct.pack(self.fmt, self.descriptor_type, self.identifier,
                           self.version, self.flags, self.system_identifier,
                           self.volume_identifier, 0, self.space_size,
                           swab_32bit(self.space_size), self.escape_sequences,
                           self.set_size, swab_16bit(self.set_size),
                           self.seqnum, swab_16bit(self.seqnum),
                           self.log_block_size, swab_16bit(self.log_block_size),
                           self.path_tbl_size, swab_32bit(self.path_tbl_size),
                           self.path_table_location_le, self.optional_path_table_location_le,
                           swab_32bit(self.path_table_location_be),
                           self.optional_path_table_location_be,
                           self.root_dir_record.record(),
                           self.volume_set_identifier,
                           self.publisher_identifier.record(),
                           self.preparer_identifier.record(),
                           self.application_identifier.record(),
                           self.copyright_file_identifier,
                           self.abstract_file_identifier,
                           self.bibliographic_file_identifier,
                           vol_create_date.record(),
                           vol_mod_date.record(),
                           self.volume_expiration_date.record(),
                           self.volume_effective_date.record(),
                           self.file_structure_version, 0,
                           self.application_use, '\x00'*653)

    def extent_location(self):
        '''
        A method to get this Supplementary Volume Descriptor's extent location.

        Parameters:
         None.
        Returns:
         Integer of this Supplementary Volume Descriptor's extent location.
        '''
        if not self.initialized:
            raise PyIsoException("This Supplementary Volume Descriptor is not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

class PathTableRecord(object):
    '''
    A class that represents a single ISO9660 Path Table Record.
    '''
    FMT = "=BBLH"

    def __init__(self):
        self.initialized = False

    def parse(self, data):
        '''
        Parse an ISO9660 Path Table Record out of a string.

        Parameters:
         data - The string to parse.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        (self.len_di, self.xattr_length, self.extent_location,
         self.parent_directory_num) = struct.unpack(self.FMT, data[:8])

        if self.len_di % 2 != 0:
            self.directory_identifier = data[8:-1]
        else:
            self.directory_identifier = data[8:]
        self.dirrecord = None
        if self.directory_identifier == '\x00':
            # For the root path table record, it's own directory num is 1
            self.directory_num = 1
        else:
            self.directory_num = self.parent_directory_num + 1
        self.initialized = True

    def _record(self, ext_loc, parent_dir_num):
        '''
        An internal method to generate a string representing this Path Table Record.

        Parameters:
         ext_loc - The extent location to place in this Path Table Record.
         parent_dir_num - The parent directory number to place in this Path Table
                          Record.
        Returns:
         A string representing this Path Table Record.
        '''
        return struct.pack(self.FMT, self.len_di, self.xattr_length,
                           ext_loc, parent_dir_num) + self.directory_identifier + '\x00'*(self.len_di % 2)

    def record_little_endian(self):
        '''
        A method to generate a string representing the little endian version of
        this Path Table Record.

        Parameters:
         None.
        Returns:
         A string representing the little endian version of this Path Table Record.
        '''
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        return self._record(self.extent_location, self.parent_directory_num)

    def record_big_endian(self):
        '''
        A method to generate a string representing the big endian version of
        this Path Table Record.

        Parameters:
         None.
        Returns:
         A string representing the big endian version of this Path Table Record.
        '''
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        return self._record(swab_32bit(self.extent_location),
                            swab_16bit(self.parent_directory_num))

    @classmethod
    def record_length(cls, len_di):
        '''
        A class method to calculate the length of this Path Table Record.
        '''
        # This method can be called even if the object isn't initialized
        return struct.calcsize(cls.FMT) + len_di + (len_di % 2)

    def _new(self, name, dirrecord, parent_dir_num):
        '''
        An internal method to create a new Path Table Record.

        Parameters:
         name - The name for this Path Table Record.
         dirrecord - The directory record to associate with this Path Table Record.
         parent_dir_num - The directory number of the parent of this Path Table
                          Record.
        Returns:
         Nothing.
        '''
        self.len_di = len(name)
        self.xattr_length = 0 # FIXME: we don't support xattr for now
        self.extent_location = 0
        self.parent_directory_num = parent_dir_num
        self.directory_identifier = name
        self.dirrecord = dirrecord
        if self.directory_identifier == '\x00':
            # For the root path table record, it's own directory num is 1
            self.directory_num = 1
        else:
            self.directory_num = self.parent_directory_num + 1
        self.initialized = True

    def new_root(self, dirrecord):
        '''
        A method to create a new root Path Table Record.

        Parameters:
         dirrecord - The directory record to associate with this Path Table Record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        self._new("\x00", dirrecord, 1)

    def new_dir(self, name, dirrecord, parent_dir_num):
        '''
        A method to create a new Path Table Record.

        Parameters:
         name - The name for this Path Table Record.
         dirrecord - The directory record to associate with this Path Table Record.
         parent_dir_num - The directory number of the parent of this Path Table
                          Record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        self._new(name, dirrecord, parent_dir_num)

    def set_dirrecord(self, dirrecord):
        '''
        A method to set the directory record associated with this Path Table
        Record.

        Parameters:
         dirrecord - The directory record to associate with this Path Table Record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        self.dirrecord = dirrecord

    def update_extent_location_from_dirrecord(self):
        '''
        A method to update the extent location for this Path Table Record from
        the corresponding directory record.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        self.extent_location = self.dirrecord.extent_location()

    def __lt__(self, other):
        return ptr_lt(self.directory_identifier, other.directory_identifier)

def ptr_lt(str1, str2):
    '''
    A function to compare two identifiers according to hte ISO9660 Path Table Record
    sorting order.

    Parameters:
     str1 - The first identifier.
     str2 - The second identifier.
    Returns:
     True if str1 is less than or equal to str2, False otherwise.
    '''
    # This method is used for the bisect.insort_left() when adding a child.
    # It needs to return whether str1 is less than str2.  Here we use the
    # ISO9660 sorting order which is essentially:
    #
    # 1.  The \x00 is always the "dot" record, and is always first.
    # 2.  The \x01 is always the "dotdot" record, and is always second.
    # 3.  Other entries are sorted lexically; this does not exactly match
    #     the sorting method specified in Ecma-119, but does OK for now.
    #
    # FIXME: we need to implement Ecma-119 section 9.3 for the sorting
    # order.
    if str1 == '\x00':
        # If both str1 and str2 are 0, then they are not strictly less.
        if str2 == '\x00':
            return False
        return True
    if str2 == '\x00':
        return False

    if str1 == '\x01':
        if str2 == '\x00':
            return False
        return True

    if str2 == '\x01':
        # If str1 was '\x00', it would have been caught above.
        return False
    return str1 < str2

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
        return "\x00" * padbytes
    return ""

def check_d1_characters(name):
    '''
    A function to check that a name only uses d1 characters as defined by ISO9660.

    Parameters:
     name - The name to check.
    Returns:
     Nothing.
    '''
    for char in name:
        if not char in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                        'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                        'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6',
                        '7', '8', '9', '_', '.', '-', '+', '(', ')', '~', '&',
                        '!', '@', '$']:
            raise PyIsoException("%s is not a valid ISO9660 filename (it contains invalid characters)" % (name))

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
    namesplit = fullname.split(';')

    # Ecma-119 says that filenames must end with a semicolon-number, but I have
    # found CDs (Ubuntu 14.04 Desktop i386, for instance) that do not follow
    # this.  Thus we allow for names both with and without the semi+version.
    if len(namesplit) == 2:
        version = namesplit[1]

        # The second entry should be the version number between 1 and 32767.
        if int(version) < 1 or int(version) > 32767:
            raise PyIsoException("%s has an invalid version number (must be between 1 and 32767" % (fullname))
    elif len(namesplit) != 1:
        raise PyIsoException("%s contains multiple semicolons!" % (fullname))

    name_plus_extension = namesplit[0]

    # The first entry should be x.y, so we split on the dot.
    dotsplit = name_plus_extension.split('.')
    if len(dotsplit) == 1:
        name = dotsplit[0]
        extension = ''
    else:
        name = '.'.join(dotsplit[:-1])
        extension = dotsplit[-1]

    # Ecma-119 section 7.5.1 specifies that filenames must have at least one
    # character in either the name or the extension.
    if len(name) == 0 and len(extension) == 0:
        raise PyIsoException("%s is not a valid ISO9660 filename (either the name or extension must be non-empty" % (fullname))

    if interchange_level == 1:
        # According to Ecma-119, section 10.1, at level 1 the filename can
        # only be up to 8 d-characters or d1-characters, and the extension can
        # only be up to 3 d-characters or 3 d1-characters.
        if len(name) > 8 or len(extension) > 3:
            raise PyIsoException("%s is not a valid ISO9660 filename at interchange level 1" % (fullname))
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
        raise PyIsoException("%s is not a valid ISO9660 directory name (the name must have at least 1 character long)" % (fullname))

    if interchange_level == 1:
        # Ecma-119 section 10.1 says that directory identifiers lengths cannot
        # exceed 8 at interchange level 1.
        if len(fullname) > 8:
            raise PyIsoException("%s is not a valid ISO9660 directory name at interchange level 1" % (fullname))
    else:
        # Ecma-119 section 7.6.3 says that directory identifiers lengths cannot
        # exceed 31.
        if len(fullname) > 207:
            raise PyIsoException("%s is not a valid ISO9660 directory name (it is longer than 31 characters)" % (fullname))

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
    except PyIsoException:
        try_level_3 = True

    if try_level_3:
        cmpfunc(identifier, 3)
        # If the above did not throw an exception, then this
        # is interchange level 3 and we should mark it.
        interchange_level = 3

    return interchange_level

class IsoHybrid(object):
    '''
    A class that represents an ISO hybrid; that is, an ISO that can be booted via
    CD or via an alternate boot mechanism (such as USB).
    '''
    def __init__(self):
        self.fmt = "=432sLLLH"
        self.initialized = False

    def parse(self, instr):
        '''
        A method to parse ISO hybridization info out of an existing ISO.

        Parameters:
         instr - The data for the ISO hybridization.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This IsoHybrid object is already initialized")

        if len(instr) != 512:
            raise PyIsoException("Invalid size of the instr")

        (self.mbr, self.rba, unused1, self.mbr_id, unused2) = struct.unpack(self.fmt, instr[:struct.calcsize(self.fmt)])

        if unused1 != 0:
            raise PyIsoException("Invalid IsoHybrid section")

        if unused2 != 0:
            raise PyIsoException("Invalid IsoHybrid section")

        offset = struct.calcsize(self.fmt)
        self.part_entry = None
        for i in range(1, 5):
            if instr[offset] == '\x80':
                self.part_entry = i
                (const, self.bhead, self.bsect, self.bcyle, self.ptype,
                 self.ehead, self.esect, self.ecyle, self.part_offset,
                 self.psize) = struct.unpack("=BBBBBBBBLL", instr[offset:offset+16])
                break
            offset += 16

        if self.part_entry is None:
            raise PyIsoException("No valid partition found in IsoHybrid!")

        if instr[-2] != '\x55' or instr[-1] != '\xaa':
            raise PyIsoException("Invalid tail on isohybrid section")

        self.geometry_heads = self.ehead + 1
        # FIXME: I can't see anyway to compute the number of sectors from the
        # available information.  For now, we just hard-code this at 32 and
        # hope for the best.
        self.geometry_sectors = 32

        self.initialized = True

    def new(self, instr, rba, part_entry, mbr_id, part_offset,
            geometry_sectors, geometry_heads, part_type):
        '''
        A method to add ISO hybridization to an ISO.

        Parameters:
         instr - The data to be put into the MBR.
         rba - The address at which to put the data.
         part_entry - The partition entry for the hybridization.
         mbr_id - The mbr_id to use for the hybridization.
         part_offset - The partition offset to use for the hybridization.
         geometry_sectors - The number of sectors to use for the hybridization.
         geometry_heads - The number of heads to use for the hybridization.
         part_type - The partition type for the hybridization.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This IsoHybrid object is already initialized")

        self.mbr = instr
        self.rba = rba
        self.mbr_id = mbr_id
        if self.mbr_id is None:
            self.mbr_id = random.getrandbits(32)

        self.part_entry = part_entry
        self.bhead = (part_offset / geometry_sectors) % geometry_heads
        self.bsect = (part_offset % geometry_sectors) + 1
        self.bcyle = part_offset / (geometry_heads * geometry_sectors)
        self.bsect += (self.bcyle & 0x300) >> 2
        self.bcyle &= 0xff
        self.ptype = part_type
        self.ehead = geometry_heads - 1
        self.part_offset = part_offset
        self.geometry_heads = geometry_heads
        self.geometry_sectors = geometry_sectors

        self.initialized = True

    def _calc_cc(self, iso_size):
        '''
        A method to calculate the "cc" and the "padding" values for this
        hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A tuple containing the cc value and the padding.
        '''
        cylsize = self.geometry_heads * self.geometry_sectors * 512
        frac = iso_size % cylsize
        padding = 0
        if frac > 0:
            padding = cylsize - frac
        cc = (iso_size + padding) / cylsize
        if cc > 1024:
            cc = 1024

        return (cc,padding)

    def record(self, iso_size):
        '''
        A method to generate a string containing the ISO hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A string containing the ISO hybridization.
        '''
        if not self.initialized:
            raise PyIsoException("This IsoHybrid object is not yet initialized")

        ret = struct.pack("=432sLLLH", self.mbr, self.rba, 0, self.mbr_id, 0)

        for i in range(1, 5):
            if i == self.part_entry:
                cc,padding = self._calc_cc(iso_size)
                esect = self.geometry_sectors + (((cc - 1) & 0x300) >> 2)
                ecyle = (cc - 1) & 0xff
                psize = cc * self.geometry_heads * self.geometry_sectors - self.part_offset
                ret += struct.pack("=BBBBBBBBLL", 0x80, self.bhead, self.bsect,
                                   self.bcyle, self.ptype, self.ehead,
                                   esect, ecyle, self.part_offset, psize)
            else:
                ret += '\x00'*16
        ret += '\x55\xaa'

        return ret

    def record_padding(self, iso_size):
        '''
        A method to record padding for the ISO hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A string of zeros the right size to pad the ISO.
        '''
        if not self.initialized:
            raise PyIsoException("This IsoHybrid object is not yet initialized")

        return '\x00'*self._calc_cc(iso_size)[1]

class VersionVolumeDescriptor(object):
    '''
    A class representing a Version Volume Descriptor.  This volume descriptor is
    not mentioned in any of the standards, but is included by genisoimage, so it
    is modeled here.
    '''
    def __init__(self):
        self.orig_extent_loc = None
        self.new_extent_loc = None
        self.initialized = False

    def parse(self, extent_location):
        '''
        Do a "parse" of a Version Volume Descriptor.  This consists of just setting
        the extent location of the Version Volume Descriptor properly.

        Parameters:
         extent_location - The location of the extent on the original ISO of this
                           Version Volume Descriptor.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This Version Volume Descriptor is already initialized")

        self.orig_extent_loc = extent_location
        self.initialized = True

    def new(self):
        '''
        Create a new Version Volume Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This Version Volume Descriptor is already initialized")

        self.initialized = True

    def record(self, log_block_size):
        '''
        Generate a string representing this Version Volume Descriptor.  Note that
        right now, this is always a string of zeros.

        Parameters:
         log_block_size - The logical block size to use when generating this string.
        Returns:
         A string representing this Version Volume Descriptor.
        '''
        if not self.initialized:
            raise PyIsoException("This Version Volume Descriptor is not yet initialized")

        return "\x00" * log_block_size

    def extent_location(self):
        '''
        Get the extent location of this Version Volume Descriptor.

        Parameters:
         None.
        Returns:
         An integer representing the extent location of this Version Volume
         Descriptor.
        '''
        if not self.initialized:
            raise PyIsoException("This Version Volume Descriptor is not yet initialized")

        if self.new_extent_loc is not None:
            return self.new_extent_loc
        return self.orig_extent_loc

class PyIso(object):
    '''
    The main class for manipulating ISOs.
    '''
    def _parse_volume_descriptors(self):
        '''
        An internal method to parse the volume descriptors on an ISO.

        Parameters:
         None.
        Returns:
         A tuple containing the PVDs, SVDs, VPDs, BRs, and VDSTs on the ISO.
        '''
        # Ecma-119 says that the Volume Descriptor set is a sequence of volume
        # descriptors recorded in consecutively numbered Logical Sectors
        # starting with Logical Sector Number 16.  Since sectors are 2048 bytes
        # in length, we start at sector 16 * 2048
        pvds = []
        vdsts = []
        brs = []
        svds = []
        vpds = []
        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.
        self.cdfp.seek(16 * 2048)
        done = False
        while not done:
            # All volume descriptors are exactly 2048 bytes long
            curr_extent = self.cdfp.tell() / 2048
            vd = self.cdfp.read(2048)
            (desc_type,) = struct.unpack("=B", vd[0])
            if desc_type == VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvd = PrimaryVolumeDescriptor()
                pvd.parse(vd, self.cdfp, 16)
                pvds.append(pvd)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
                vdst = VolumeDescriptorSetTerminator()
                vdst.parse(vd, curr_extent)
                vdsts.append(vdst)
                # Once we see a set terminator, we stop parsing.  Oddly,
                # Ecma-119 says there may be multiple set terminators, but in
                # that case I don't know how to tell when we are done parsing
                # volume descriptors.  Leave this for now.
                done = True
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
                br = BootRecord()
                br.parse(vd, curr_extent)
                brs.append(br)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
                svd = SupplementaryVolumeDescriptor()
                svd.parse(vd, self.cdfp, curr_extent)
                svds.append(svd)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
                raise PyIsoException("Unimplemented Volume Partition descriptor!")
            else:
                raise PyIsoException("Invalid volume descriptor type %d" % (desc_type))
        return pvds, svds, vpds, brs, vdsts

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
        we create a new DirectoryRecord object and append it to the parent.

        Parameters:
         vd - The volume descriptor to walk.
         do_check_interchange - Whether to check the interchange level or not.
        Returns:
         The interchange level that this ISO conforms to.
        '''
        vd.set_ptr_dirrecord(vd.root_directory_record())
        interchange_level = 1
        dirs = collections.deque([vd.root_directory_record()])
        block_size = vd.logical_block_size()
        while dirs:
            dir_record = dirs.popleft()

            self._seek_to_extent(dir_record.extent_location())
            length = dir_record.file_length()
            while length > 0:
                # read the length byte for the directory record
                (lenbyte,) = struct.unpack("=B", self.cdfp.read(1))
                length -= 1
                if lenbyte == 0:
                    # If we saw zero length, this may be a padding byte; seek
                    # to the start of the next extent.
                    if length > 0:
                        padsize = block_size - (self.cdfp.tell() % block_size)
                        padbytes = self.cdfp.read(padsize)
                        if padbytes != '\x00'*padsize:
                            # For now we are pedantic, and if the padding bytes
                            # are not all zero we throw an Exception.  Depending
                            # one what we see in the wild, we may have to loosen
                            # this check.
                            raise PyIsoException("Invalid padding on ISO")
                        length -= padsize
                        if length < 0:
                            # For now we are pedantic, and if the length goes
                            # negative because of the padding we throw an
                            # exception.  Depending on what we see in the wild,
                            # we may have to loosen this check.
                            raise PyIsoException("Invalid padding on ISO")
                    continue
                new_record = DirectoryRecord()
                self.rock_ridge |= new_record.parse(struct.pack("=B", lenbyte) + self.cdfp.read(lenbyte - 1),
                                                    self.cdfp, dir_record,
                                                    self.pvd.logical_block_size())

                if new_record.rock_ridge is not None and new_record.rock_ridge.ce_record is not None:
                    orig_pos = self.cdfp.tell()
                    self._seek_to_extent(new_record.rock_ridge.ce_record.continuation_entry.extent_location())
                    self.cdfp.seek(new_record.rock_ridge.ce_record.continuation_entry.offset(), os.SEEK_CUR)
                    con_block = self.cdfp.read(new_record.rock_ridge.ce_record.continuation_entry.length())
                    new_record.rock_ridge.ce_record.continuation_entry.parse(con_block,
                                                                             new_record.rock_ridge.bytes_to_skip)
                    self.cdfp.seek(orig_pos)

                if isinstance(vd, PrimaryVolumeDescriptor) and self.eltorito_boot_catalog is not None:
                    if new_record.extent_location() == self.eltorito_boot_catalog.extent_location():
                        self.eltorito_boot_catalog.set_dirrecord(new_record)
                    elif new_record.extent_location() == self.eltorito_boot_catalog.initial_entry.load_rba:
                        self.eltorito_boot_catalog.set_initial_entry_dirrecord(new_record)

                length -= lenbyte - 1
                if new_record.is_dir():
                    if not new_record.is_dot() and not new_record.is_dotdot():
                        if do_check_interchange:
                            interchange_level = max(interchange_level, check_interchange_level(new_record.file_identifier(), True))
                        dirs.append(new_record)
                        vd.set_ptr_dirrecord(new_record)
                else:
                    if do_check_interchange:
                        interchange_level = max(interchange_level, check_interchange_level(new_record.file_identifier(), False))
                dir_record.add_child(new_record, vd, True)

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
        self.vpds = []
        self.brs = []
        self.vdsts = []
        self.eltorito_boot_catalog = None
        self.initialized = False
        self.rock_ridge = False
        self.isohybrid_mbr = None

    def _parse_path_table(self, vd, extent, callback):
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
        while left > 0:
            ptr = PathTableRecord()
            (len_di,) = struct.unpack("=B", self.cdfp.read(1))
            read_len = PathTableRecord.record_length(len_di)
            # PathTableRecord.record_length() returns the length of the entire
            # path table record, but we've already read the len_di so read one
            # less.
            ptr.parse(struct.pack("=B", len_di) + self.cdfp.read(read_len - 1))
            left -= read_len
            callback(vd, ptr)

    def _little_endian_path_table(self, vd, ptr):
        '''
        The callback that is used when parsing the little-endian path tables.
        In this case, we actually store the path table record inside the
        passed in Volume Descriptor.

        Parameters:
         vd - The volume descriptor that this callback is for.
         ptr - A Path Table Record object.
        Returns:
         Nothing.
        '''
        vd.add_path_table_record(ptr)

    def _big_endian_path_table(self, vd, ptr):
        '''
        The callback that is used when parsing the big-endian path tables.
        In this case, we store the path table record inside a temporary list
        of path table records; it will eventually be used to ensure consistency
        between the big-endian and little-endian path tables.

        Parameters:
         vd - The volume descriptor that this callback is for.
         ptr - A Path Table Record object.
        Returns:
         Nothing.
        '''
        bisect.insort_left(self.tmp_be_path_table_records, ptr)

    def _find_record(self, vd, path, encoding='ascii'):
        '''
        An internal method to find an entry on the ISO given a Volume
        Descriptor, a full ISO path, and an encoding.  Once the entry is found,
        return the directory record object corresponding to that entry, as well
        as the index within the list of children for that particular parent.
        If the entry could not be found, a PyIsoException is raised.

        Parameters:
         vd - The volume descriptor in which to look up the entry.
         path - The absolute path to look up in the volume descriptor.
         encoding - The encoding to use on the individual portions of the path.
        Returns:
         A tuple containing a directory record entry representing the entry on
         the ISO and the index of that entry into the parent's child list.
        '''
        if path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        # If the path is just the slash, we just want the root directory, so
        # get the children there and quit.
        if path == '/':
            return vd.root_directory_record(),0

        # Split the path along the slashes
        splitpath = path.split('/')
        # Skip past the first one, since it is always empty.
        splitindex = 1

        currpath = splitpath[splitindex].encode(encoding)
        splitindex += 1
        children = vd.root_directory_record().children
        index = 0
        while index < len(children):
            child = children[index]
            index += 1

            if child.is_dot() or child.is_dotdot():
                continue

            if child.file_identifier() != currpath:
                if child.rock_ridge is None:
                    continue

                if child.rock_ridge.name() != currpath:
                    continue

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
                    currpath = splitpath[splitindex].encode(encoding)
                    splitindex += 1

        raise PyIsoException("Could not find path %s" % (path))

    def _internal_name_and_parent_from_path(self, iso_path, vd):
        '''
        An internal method to find the parent directory record given a full
        ISO path and a Volume Descriptor.  If the parent is found, return the
        parent directory record object and the relative path of the original
        path.

        Parameters:
         iso_path - The absolute path to the entry on the ISO.
         vd - The volume descriptor in which to look up the entry.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''
        if iso_path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        # First we need to find the parent of this directory, and add this
        # one as a child.
        splitpath = iso_path.split('/')
        # Pop off the front, as it is always blank.
        splitpath.pop(0)
        if isinstance(vd, PrimaryVolumeDescriptor) and len(splitpath) > 7:
            # Ecma-119 Section 6.8.2.1 says that the number of levels in the
            # hierarchy shall not exceed eight.  However, since the root
            # directory must always reside at level 1 by itself, this gives us
            # an effective maximum hierarchy depth of 7.
            raise PyIsoException("Directory levels too deep (maximum is 7)")
        # Now take the name off.
        name = splitpath.pop()
        if len(splitpath) == 0:
            # This is a new directory under the root, add it there
            parent = vd.root_directory_record()
        else:
            parent,index = self._find_record(vd, '/' + '/'.join(splitpath))

        return (name, parent)

    def _name_and_parent_from_path(self, iso_path):
        '''
        An internal method to find the parent directory record in the Primary
        Volume Descriptor of a full ISO path.  If the parent is found, return
        the parent directory record object and the relative path of the
        original path.

        Parameters:
         iso_path - The absolute path to the entry on the ISO.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''
        return self._internal_name_and_parent_from_path(iso_path, self.pvd)

    def _joliet_name_and_parent_from_path(self, joliet_path):
        '''
        An internal method to find the parent directory record in the Joliet
        Volume Descriptor of a full ISO path.  If the parent is found, return
        the parent directory record object and the relative path of the
        original path.

        Parameters:
         joliet_path - The absolute path to the Joliet entry on the ISO.
        Returns:
         A tuple containing just the name of the entry and a Directory Record
         object representing the parent of the entry.
        '''
        return self._internal_name_and_parent_from_path(joliet_path, self.joliet_vd)

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
        if br.boot_system_identifier != "{:\x00<32}".format("EL TORITO SPECIFICATION"):
            return

        if self.eltorito_boot_catalog is not None:
            raise PyIsoException("Only one El Torito boot record is allowed")

        # According to the El Torito specification, section 2.0, the El
        # Torito boot record must be at extent 17.
        if br.extent_location() != 17:
            raise PyIsoException("El Torito Boot Record must be at extent 17")

        # Now that we have verified that the BootRecord is an El Torito one
        # and that it is sane, we go on to parse the El Torito Boot Catalog.
        # Note that the Boot Catalog is stored as a file in the ISO, though
        # we ignore that for the purposes of parsing.

        self.eltorito_boot_catalog = EltoritoBootCatalog(br)
        eltorito_boot_catalog_extent, = struct.unpack("=L", br.boot_system_use[:4])

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
        root_dir_record.update_location(current_extent)
        # Equivalent to ceiling_div(root_dir_record.data_length, self.pvd.log_block_size), but faster
        current_extent += -(-root_dir_record.data_length // vd.log_block_size)

        rr_cont_extent = None
        rr_cont_offset = 0

        # Walk through the list, assigning extents to all of the directories.
        dirs = collections.deque([root_dir_record])
        while dirs:
            dir_record = dirs.popleft()
            for child in dir_record.children:
                # Equivalent to child.is_dot(), but faster.
                if child.isdir and child.file_ident == '\x00':
                    child.new_extent_loc = child.parent.extent_location()
                # Equivalent to child.is_dotdot(), but faster.
                elif child.isdir and child.file_ident == '\x01':
                    if child.parent.is_root:
                        # Special case of the root directory record.  In this
                        # case, we assume that the dot record has already been
                        # added, and is the one before us.  We set the dotdot
                        # extent location to the same as the dot one.
                        child.new_extent_loc = child.parent.extent_location()
                    else:
                        child.new_extent_loc = child.parent.parent.extent_location()
                else:
                    if child.isdir:
                        child.new_extent_loc = current_extent
                        # Equivalent to ceiling_div(child.data_length, vd.log_block_size), but faster
                        current_extent += -(-child.data_length // vd.log_block_size)
                        dirs.append(child)
                    if child.rock_ridge is not None and child.rock_ridge.ce_record is not None:
                        rr_cont_len = child.rock_ridge.ce_record.continuation_entry.length()
                        if rr_cont_extent is None or ((vd.log_block_size - rr_cont_offset) < rr_cont_len):
                            child.rock_ridge.ce_record.continuation_entry.new_extent_loc = current_extent
                            child.rock_ridge.ce_record.continuation_entry.continue_offset = 0
                            rr_cont_extent = current_extent
                            rr_cont_offset = rr_cont_len
                            current_extent += 1
                        else:
                            child.rock_ridge.ce_record.continuation_entry.new_extent_loc = rr_cont_extent
                            child.rock_ridge.ce_record.continuation_entry.continue_offset = rr_cont_offset
                            rr_cont_offset += rr_cont_len

        # After we have reshuffled the extents we need to update the ptr
        # records.
        vd.update_ptr_extent_locations()

        return current_extent

    def _reshuffle_extents(self):
        '''
        An internal method that is one of the keys of PyIso's ability to keep
        the in-memory metadata consistent at all times.  After making any
        changes to the ISO, most API calls end up calling this method.  This
        method will run through the entire ISO, assigning extents to each of
        the pieces of the ISO that exist.  This includes the Primary Volume
        Descriptor (which is fixed at extent 16), the Boot Records (including
        El Torito), the Supplementary Volume Descriptors (including Joliet),
        the Volume Descriptor Terminators, the Version Descriptor, the Primary
        Volume Descriptor Path Table Records (little and big endian), the
        Supplementary Vollume Descriptor Path Table Records (little and big
        endian), the Primary Volume Descriptor directory records, the
        Supplementary Volume Descriptor directory records, the Rock Ridge ER
        sector, the El Torito Boot Catalog, the El Torito Initial Entry, and
        finally the data for the files.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        current_extent = self.pvd.extent_location()
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
        self.pvd.path_table_location_le = current_extent
        current_extent += self.pvd.path_table_num_extents
        self.pvd.path_table_location_be = current_extent
        current_extent += self.pvd.path_table_num_extents

        for svd in self.svds:
            svd.path_table_location_le = current_extent
            current_extent += svd.path_table_num_extents
            svd.path_table_location_be = current_extent
            current_extent += svd.path_table_num_extents

        current_extent = self._reassign_vd_dirrecord_extents(self.pvd, current_extent)

        for svd in self.svds:
            current_extent = self._reassign_vd_dirrecord_extents(svd, current_extent)

        # The rock ridge "ER" sector must be after all of the directory
        # entries but before the file contents.
        if self.rock_ridge:
            self.pvd.root_directory_record().children[0].rock_ridge.ce_record.continuation_entry.new_extent_loc = current_extent
            current_extent += 1

        if self.eltorito_boot_catalog is not None:
            self.eltorito_boot_catalog.br.boot_system_use = struct.pack("=L", current_extent)
            self.eltorito_boot_catalog.dirrecord.new_extent_loc = current_extent
            current_extent += 1

            self.eltorito_boot_catalog.initial_entry_dirrecord.new_extent_loc = current_extent
            self.eltorito_boot_catalog.update_initial_entry_location(current_extent)
            current_extent += 1

        # Then we can walk the list, assigning extents to the files.
        dirs = collections.deque([self.pvd.root_directory_record()])
        while dirs:
            dir_record = dirs.popleft()
            for child in dir_record.children:
                if child.isdir:
                    if not child.file_ident == '\x00' and not child.file_ident == '\x01':
                        dirs.append(child)
                    continue

                if self.eltorito_boot_catalog:
                    if self.eltorito_boot_catalog.dirrecord == child or self.eltorito_boot_catalog.initial_entry_dirrecord == child:
                        continue

                child.new_extent_loc = current_extent
                # Equivalent to ceiling_div(child.data_length, self.pvd.log_block_size), but faster
                current_extent += -(-child.data_length // self.pvd.log_block_size)

########################### PUBLIC API #####################################
    def __init__(self):
        self._initialize()

    def new(self, interchange_level=1, sys_ident="", vol_ident="", set_size=1,
            seqnum=1, log_block_size=2048, vol_set_ident="", pub_ident_str="",
            preparer_ident_str="",
            app_ident_str="PyIso (C) 2015 Chris Lalancette", copyright_file="",
            abstract_file="", bibli_file="", vol_expire_date=None, app_use="",
            joliet=False, rock_ridge=False):
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
         rock_ridge - A boolean which controls whether to make this a Rock Ridge
                      ISO or not; the default is False.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This object already has an ISO; either close it or create a new object")

        if interchange_level < 1 or interchange_level > 3:
            raise PyIsoException("Invalid interchange level (must be between 1 and 3)")

        self.interchange_level = interchange_level

        # First create the new PVD.
        pub_ident = FileOrTextIdentifier()
        pub_ident.new(pub_ident_str, False)
        preparer_ident = FileOrTextIdentifier()
        preparer_ident.new(preparer_ident_str, False)
        app_ident = FileOrTextIdentifier()
        app_ident.new(app_ident_str, False)

        self.pvd = PrimaryVolumeDescriptor()
        self.pvd.new(0, sys_ident, vol_ident, set_size, seqnum, log_block_size,
                     vol_set_ident, pub_ident, preparer_ident, app_ident,
                     copyright_file, abstract_file, bibli_file,
                     vol_expire_date, app_use)

        # Now that we have the PVD, make the root path table record.
        ptr = PathTableRecord()
        ptr.new_root(self.pvd.root_directory_record())
        self.pvd.add_path_table_record(ptr)

        self.joliet_vd = None
        if joliet:
            joliet_pub_ident = FileOrTextIdentifier()
            joliet_pub_ident.new(pub_ident_str.encode("utf-16_be"), False)
            joliet_preparer_ident = FileOrTextIdentifier()
            joliet_preparer_ident.new(preparer_ident_str.encode("utf-16_be"), False)
            joliet_app_ident = FileOrTextIdentifier()
            joliet_app_ident.new(app_ident_str.encode("utf-16_be"), False)

            # If the user requested Joliet, make the SVD to represent it here.
            svd = SupplementaryVolumeDescriptor()
            svd.new(0, sys_ident, vol_ident, set_size, seqnum, log_block_size,
                    vol_set_ident, joliet_pub_ident, joliet_preparer_ident,
                    joliet_app_ident, copyright_file, abstract_file,
                    bibli_file, vol_expire_date, app_use)
            self.svds = [svd]
            self.joliet_vd = svd
            ptr = PathTableRecord()
            ptr.new_root(svd.root_directory_record())
            svd.add_path_table_record(ptr)
            # Finally, make the directory entries for dot and dotdot.
            dot = DirectoryRecord()
            dot.new_dot(svd.root_directory_record(), svd.sequence_number(), False, svd.logical_block_size())
            svd.root_directory_record().add_child(dot, svd, False)

            dotdot = DirectoryRecord()
            dotdot.new_dotdot(svd.root_directory_record(), svd.sequence_number(), False, svd.logical_block_size())
            svd.root_directory_record().add_child(dotdot, svd, False)

            additional_size = svd.logical_block_size() + 2*svd.logical_block_size() + 2*svd.logical_block_size() + svd.logical_block_size()
            # Now that we have added joliet, we need to add the new space to the
            # PVD.  Here, we add one extent for the SVD itself, 2 for the little
            # endian path table records, 2 for the big endian path table
            # records, and one for the root directory record.
            self.pvd.add_to_space_size(additional_size)
            # And we add the same amount of space to the SVD.
            svd.add_to_space_size(additional_size)

        # Also make the volume descriptor set terminator.
        vdst = VolumeDescriptorSetTerminator()
        vdst.new()
        self.vdsts = [vdst]

        self.version_vd = VersionVolumeDescriptor()
        self.version_vd.new()

        # Finally, make the directory entries for dot and dotdot.
        dot = DirectoryRecord()
        dot.new_dot(self.pvd.root_directory_record(), self.pvd.sequence_number(), rock_ridge, self.pvd.logical_block_size())
        self.pvd.root_directory_record().add_child(dot, self.pvd, False)

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(self.pvd.root_directory_record(), self.pvd.sequence_number(), rock_ridge, self.pvd.logical_block_size())
        self.pvd.root_directory_record().add_child(dotdot, self.pvd, False)

        self.rock_ridge = rock_ridge
        if self.rock_ridge:
            self.pvd.add_to_space_size(self.pvd.logical_block_size())
            if joliet:
                self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

        self._reshuffle_extents()

        self.initialized = True

    def open(self, fp):
        '''
        Open up an existing ISO for inspection and modification.  Note that the
        file object passed in here must stay open for the lifetime of this
        object, as the PyIso class uses it internally to do writing and reading
        operations.

        Parameters:
         fp - The file object containing the ISO to open up.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise PyIsoException("This object already has an ISO; either close it or create a new object")

        self.cdfp = fp

        # Get the Primary Volume Descriptor (pvd), the set of Supplementary
        # Volume Descriptors (svds), the set of Volume Partition
        # Descriptors (vpds), the set of Boot Records (brs), and the set of
        # Volume Descriptor Set Terminators (vdsts)
        pvds, self.svds, self.vpds, self.brs, self.vdsts = self._parse_volume_descriptors()
        if len(pvds) != 1:
            raise PyIsoException("Valid ISO9660 filesystems have one and only one Primary Volume Descriptors")
        if len(self.vdsts) < 1:
            raise PyIsoException("Valid ISO9660 filesystems must have at least one Volume Descriptor Set Terminators")

        self.pvd = pvds[0]

        old = self.cdfp.tell()
        self.cdfp.seek(0)
        mbr = self.cdfp.read(512)
        if mbr[0:2] == '\x33\xed':
            # All isolinux isohdpfx.bin files start with 0x33 0xed (the x86
            # instruction for xor %bp, %bp).  Therefore, if we see that we know
            # we have a valid isohybrid, so parse that.
            self.isohybrid_mbr = IsoHybrid()
            self.isohybrid_mbr.parse(mbr)
        self.cdfp.seek(old)

        for br in self.brs:
            self._check_and_parse_eltorito(br, self.pvd.logical_block_size())

        self.version_vd = VersionVolumeDescriptor()
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
                               self._little_endian_path_table)

        # Big Endian next.
        self.tmp_be_path_table_records = []
        self._parse_path_table(self.pvd, self.pvd.path_table_location_be,
                               self._big_endian_path_table)

        for index,ptr in enumerate(self.tmp_be_path_table_records):
            if not self.pvd.path_table_record_be_equal_to_le(index, ptr):
                raise PyIsoException("Little-endian and big-endian path table records do not agree")

        # OK, so now that we have the PVD, we start at its root directory
        # record and find all of the files
        self.interchange_level = self._walk_directories(self.pvd, True)

        # The PVD is finished.  Now look to see if we need to parse the SVD.
        self.joliet_vd = None
        for svd in self.svds:
            if svd.joliet:
                if self.joliet_vd is not None:
                    raise PyIsoException("Only a single Joliet SVD is supported")
                self.joliet_vd = svd

                self._parse_path_table(svd, svd.path_table_location_le,
                                       self._little_endian_path_table)

                self._parse_path_table(svd, svd.path_table_location_be,
                                       self._big_endian_path_table)

                self._walk_directories(svd, False)

        self.initialized = True

    def print_tree(self):
        '''
        Print out the tree.  This is useful for debugging.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")
        print("%s (extent %d)" % (self.pvd.root_directory_record().file_identifier(), self.pvd.root_directory_record().extent_location()))

        dirs = collections.deque([(self.pvd.root_directory_record(), 0)])
        visited = set()
        while dirs:
            dir_record,depth = dirs.pop()
            if dir_record not in visited:
                visited.add(dir_record)
                for child in dir_record.children:
                    if child.is_dot() or child.is_dotdot():
                        continue
                    if child not in visited:
                        dirs.append((child, depth+1))
                print("%s%s (extent %d)" % ('    '*depth, dir_record.file_identifier(), dir_record.extent_location()))

    def get_and_write(self, iso_path, outfp, blocksize=8192):
        """
        Fetch a single file from the ISO and write it out to the file object.

        Parameters:
         iso_path - The absolute path to the file to get data from.
         outfp - The file object to write data to.
         blocksize - The blocksize to use when copying data; the default is 8192.
        Returns:
         Nothing.
        """
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        try_iso9660 = True
        if self.joliet_vd is not None:
            try:
                found_record,index = self._find_record(self.joliet_vd, iso_path, 'utf-16_be')
                try_iso9660 = False
            except PyIsoException:
                pass

        if try_iso9660:
            found_record,index = self._find_record(self.pvd, iso_path)
            if found_record.rock_ridge is not None:
                if found_record.rock_ridge.is_symlink():
                    # If this Rock Ridge record is a symlink, it has no data
                    # associated with it, so it makes no sense to try and get the
                    # data.  In theory, we could follow the symlink to the
                    # the appropriate place and get the data of the thing it points
                    # to.  However, the symlinks are allowed to point *outside* of
                    # this ISO, so its really not clear that this is something we
                    # want to do.  For now we make the user follow the symlink
                    # themselves if they want to get the data.  We can revisit this
                    # decision in the future if we need to.
                    raise PyIsoException("Symlinks have no data associated with them")

        data_fp,data_length = found_record.open_data(self.pvd.logical_block_size())

        copy_data(data_length, blocksize, data_fp, outfp)

    def write(self, outfp, blocksize=8192, progress_cb=None):
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
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        outfp.seek(0)

        if progress_cb is not None:
            done = 0
            total = self.pvd.space_size * self.pvd.logical_block_size()
            progress_cb(done, total)

        if self.isohybrid_mbr is not None:
            outfp.write(self.isohybrid_mbr.record(self.pvd.space_size * self.pvd.logical_block_size()))

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.  Thus
        # we skip the first 16 sectors.
        outfp.seek(self.pvd.extent_location() * self.pvd.logical_block_size())

        # First write out the PVD.
        rec = self.pvd.record()
        outfp.write(rec)

        if progress_cb is not None:
            done += len(rec)
            progress_cb(done, total)

        # Next write out the boot records.
        for br in self.brs:
            outfp.seek(br.extent_location() * self.pvd.logical_block_size())
            rec = br.record()
            outfp.write(rec)

            if progress_cb is not None:
                done += len(rec)
                progress_cb(done, total)

        # Next we write out the SVDs.
        for svd in self.svds:
            outfp.seek(svd.extent_location() * self.pvd.logical_block_size())
            rec = svd.record()
            outfp.write(rec)

            if progress_cb is not None:
                done += len(rec)
                progress_cb(done, total)

        # Next we write out the Volume Descriptor Terminators.
        for vdst in self.vdsts:
            outfp.seek(vdst.extent_location() * self.pvd.logical_block_size())
            rec = vdst.record()
            outfp.write(rec)

            if progress_cb is not None:
                done += len(rec)
                progress_cb(done, total)

        # Next we write out the version block.
        # FIXME: In genisoimage, write.c:vers_write(), this "version descriptor"
        # is written out with the exact command line used to create the ISO
        # (if in debug mode, otherwise it is all zero).  However, there is no
        # mention of this in any of the specifications I've read so far.  Where
        # does it come from?
        if self.version_vd is not None:
            outfp.seek(self.version_vd.extent_location() * self.pvd.logical_block_size())
            rec = self.version_vd.record(self.pvd.logical_block_size())
            outfp.write(rec)

            if progress_cb is not None:
                done += len(rec)
                progress_cb(done, total)

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

        if progress_cb is not None:
            done += self.pvd.path_table_num_extents * 2 * self.pvd.logical_block_size()
            progress_cb(done, total)

        # Now we write out the path table records for any SVDs.
        for svd in self.svds:
            le_offset = 0
            be_offset = 0
            for record in svd.path_table_records:
                outfp.seek(svd.path_table_location_le * svd.logical_block_size() + le_offset)
                ret = record.record_little_endian()
                outfp.write(ret)
                le_offset += len(ret)

                outfp.seek(svd.path_table_location_be * svd.logical_block_size() + be_offset)
                ret = record.record_big_endian()
                outfp.write(ret)
                be_offset += len(ret)

            # Once we are finished with the loop, we need to pad out the Big
            # Endian version.  The Little Endian one was already properly padded
            # by the mere fact that we wrote things for the Big Endian version
            # in the right place.
            outfp.write(pad(be_offset, 4096))

            if progress_cb is not None:
                done += svd.path_table_num_extents * 2 * svd.logical_block_size()
                progress_cb(done, total)

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        dirs = collections.deque([self.pvd.root_directory_record()])
        while dirs:
            curr = dirs.popleft()
            curr_dirrecord_offset = 0
            if progress_cb is not None and curr.is_dir():
                done += curr.file_length()
                progress_cb(done, total)

            for child in curr.children:
                # Now matter what type the child is, we need to first write out
                # the directory record entry.
                dir_extent = child.parent.extent_location()

                outfp.seek(dir_extent * self.pvd.logical_block_size() + curr_dirrecord_offset)
                # Now write out the child
                recstr = child.record()
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
                        if progress_cb is not None:
                            done += outfp.tell() - tmp_start
                            progress_cb(done, total)

                if child.is_dir():
                    # If the child is a directory, and is not dot or dotdot, we
                    # want to descend into it to look at the children.
                    if not child.is_dot() and not child.is_dotdot():
                        dirs.append(child)
                    outfp.write(pad(outfp.tell(), self.pvd.logical_block_size()))
                elif child.data_length > 0:
                    # If the child is a file, then we need to write the data to
                    # the output file.
                    data_fp,data_length = child.open_data(self.pvd.logical_block_size())
                    outfp.seek(child.extent_location() * self.pvd.logical_block_size())
                    tmp_start = outfp.tell()
                    copy_data(data_length, blocksize, data_fp, outfp)
                    outfp.write(pad(data_length, self.pvd.logical_block_size()))

                    if progress_cb is not None:
                        done += outfp.tell() - tmp_start
                        progress_cb(done, total)

        for svd in self.svds:
            dirs = collections.deque([svd.root_directory_record()])
            while dirs:
                curr = dirs.popleft()
                curr_dirrecord_offset = 0
                if progress_cb is not None and curr.is_dir():
                    done += curr.file_length()
                    progress_cb(done, total)

                for child in curr.children:
                    # Now matter what type the child is, we need to first write
                    # out the directory record entry.
                    dir_extent = child.parent.extent_location()

                    outfp.seek(dir_extent * svd.logical_block_size() + curr_dirrecord_offset)
                    # Now write out the child
                    recstr = child.record()
                    outfp.write(recstr)
                    curr_dirrecord_offset += len(recstr)

                    if child.is_dir():
                        # If the child is a directory, and is not dot or dotdot,
                        # we want to descend into it to look at the children.
                        if not child.is_dot() and not child.is_dotdot():
                            dirs.append(child)
                        outfp.write(pad(outfp.tell(), svd.logical_block_size()))

        outfp.truncate(self.pvd.space_size * self.pvd.logical_block_size())

        if self.isohybrid_mbr is not None:
            outfp.seek(0, os.SEEK_END)
            outfp.write(self.isohybrid_mbr.record_padding(self.pvd.space_size * self.pvd.logical_block_size()))

        if progress_cb is not None:
            outfp.seek(0, os.SEEK_END)
            progress_cb(outfp.tell(), total)

    def add_fp(self, fp, length, iso_path, rr_path=None, joliet_path=None):
        '''
        Add a file to the ISO.  If the ISO contains Joliet or
        RockRidge, then a Joliet name and/or a RockRidge name must also be
        provided.  Note that the caller must ensure that the file remains open
        for the lifetime of the ISO object, as the PyIso class uses the file
        descriptor internally when writing (mastering) the ISO.

        Parameters:
         fp - The file object to use for the contents of the new file.
         length - The length of the data for the new file.
         iso_path - The ISO9660 absolute path to the file destination on the ISO.
         rr_path - The Rock Ridge absolute path to the file destination on
                       the ISO.
         joliet_path - The Joliet absolute path to the file destination on the ISO.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        rr_name = None
        if self.rock_ridge:
            if rr_path is None:
                raise PyIsoException("A rock ridge path must be passed for a rock-ridge ISO")
            splitpath = rr_path.split('/')
            rr_name = splitpath[-1]
        else:
            if rr_path is not None:
                raise PyIsoException("A rock ridge path can only be specified for a rock-ridge ISO")

        if self.joliet_vd is not None:
            if joliet_path is None:
                raise PyIsoException("A Joliet path must be passed for a Joliet ISO")
        else:
            if joliet_path is not None:
                raise PyIsoException("A Joliet path can only be specified for a Joliet ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        check_iso9660_filename(name, self.interchange_level)

        rec = DirectoryRecord()
        rec.new_fp(fp, length, name, parent, self.pvd.sequence_number(), self.rock_ridge, rr_name)
        parent.add_child(rec, self.pvd, False)
        self.pvd.add_entry(length)

        if self.joliet_vd is not None:
            (joliet_name, joliet_parent) = self._joliet_name_and_parent_from_path(joliet_path)

            joliet_name = joliet_name.encode('utf-16_be')

            joliet_rec = DirectoryRecord()
            joliet_rec.new_fp(fp, length, joliet_name, joliet_parent, self.joliet_vd.sequence_number(), False, None)
            joliet_parent.add_child(joliet_rec, self.joliet_vd, False)
            self.joliet_vd.add_entry(length)

        self._reshuffle_extents()

        if self.joliet_vd is not None:
            # If we are doing Joliet, then we must update the joliet record with
            # the new extent location *after* having done the reshuffle.
            joliet_rec.new_extent_loc = rec.new_extent_loc

        # This needs to be *after* reshuffle_extents() so that the continuation
        # entry offsets are computed properly.
        if rec.rock_ridge is not None and rec.rock_ridge.ce_record is not None and rec.rock_ridge.ce_record.continuation_entry.continue_offset == 0:
            self.pvd.add_to_space_size(self.pvd.logical_block_size())

    def add_directory(self, iso_path, rr_path=None, joliet_path=None):
        '''
        Add a directory to the ISO.  If the ISO contains Joliet or RockRidge (or
        both), then a Joliet name and/or a RockRidge name must also be provided.

        Parameters:
         iso_path - The ISO9660 absolute path to use for the directory.
         rr_path - The Rock Ridge absolute path to use for the directory.
         joliet_path - The Joliet absolute path to use for the directory.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        rr_name = None
        if self.rock_ridge:
            if rr_path is None:
                raise PyIsoException("A rock ridge path must be passed for a rock-ridge ISO")
            splitpath = rr_path.split('/')
            rr_name = splitpath[-1]
        else:
            if rr_path is not None:
                raise PyIsoException("A rock ridge path can only be specified for a rock-ridge ISO")

        if self.joliet_vd is not None:
            if joliet_path is None:
                raise PyIsoException("A Joliet path must be passed for a Joliet ISO")
        else:
            if joliet_path is not None:
                raise PyIsoException("A Joliet path can only be specified for a Joliet ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        check_iso9660_directory(name, self.interchange_level)

        rec = DirectoryRecord()
        rec.new_dir(name, parent, self.pvd.sequence_number(), self.rock_ridge, rr_name, self.pvd.logical_block_size())
        parent.add_child(rec, self.pvd, False)

        dot = DirectoryRecord()
        dot.new_dot(rec, self.pvd.sequence_number(), self.rock_ridge, self.pvd.logical_block_size())
        rec.add_child(dot, self.pvd, False)

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(rec, self.pvd.sequence_number(), self.rock_ridge, self.pvd.logical_block_size())
        rec.add_child(dotdot, self.pvd, False)

        self.pvd.add_entry(self.pvd.logical_block_size(),
                           PathTableRecord.record_length(len(name)))

        # We always need to add an entry to the path table record
        ptr = PathTableRecord()
        ptr.new_dir(name, rec, self.pvd.find_parent_dirnum(parent))

        self.pvd.add_path_table_record(ptr)

        if self.joliet_vd is not None:
            (joliet_name, joliet_parent) = self._joliet_name_and_parent_from_path(joliet_path)

            joliet_name = joliet_name.encode('utf-16_be')
            rec = DirectoryRecord()
            rec.new_dir(joliet_name, joliet_parent, self.joliet_vd.sequence_number(), False, None, self.joliet_vd.logical_block_size())
            joliet_parent.add_child(rec, self.joliet_vd, False)

            dot = DirectoryRecord()
            dot.new_dot(rec, self.joliet_vd.sequence_number(), False, self.joliet_vd.logical_block_size())
            rec.add_child(dot, self.joliet_vd, False)

            dotdot = DirectoryRecord()
            dotdot.new_dotdot(rec, self.joliet_vd.sequence_number(), False, self.joliet_vd.logical_block_size())
            rec.add_child(dotdot, self.joliet_vd, False)

            self.joliet_vd.add_entry(self.joliet_vd.logical_block_size(),
                                     PathTableRecord.record_length(len(joliet_name)))

            # We always need to add an entry to the path table record
            ptr = PathTableRecord()
            ptr.new_dir(joliet_name, rec, self.joliet_vd.find_parent_dirnum(joliet_parent))

            self.joliet_vd.add_path_table_record(ptr)

            self.pvd.add_to_space_size(self.pvd.logical_block_size())

            self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

        self._reshuffle_extents()

    def rm_file(self, iso_path, rr_path=None):
        '''
        Remove a file from the ISO.

        Parameters:
         iso_path - The path to the file to remove.
         rr_path - The Rock Ridge path to the file to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        child,index = self._find_record(self.pvd, iso_path)

        # FIXME: what if this is a joliet file?

        if not child.is_file():
            raise PyIsoException("Cannot remove a directory with rm_file (try rm_directory instead(")

        child.parent.remove_child(child, index, self.pvd)

        self.pvd.remove_entry(child.file_length())
        if self.joliet_vd is not None:
            self.joliet_vd.remove_entry(child.file_length())

        self._reshuffle_extents()

    def rm_directory(self, iso_path, rr_path=None):
        '''
        Remove a directory from the ISO.

        Parameters:
         iso_path - The path to the directory to remove.
         rr_path - The Rock Ridge path to the file to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path == '/':
            raise PyIsoException("Cannot remove base directory")

        child,index = self._find_record(self.pvd, iso_path)

        # FIXME: what if this is a joliet directory?

        if not child.is_dir():
            raise PyIsoException("Cannot remove a file with rm_directory (try rm_file instead)")

        for c in child.children:
            if c.is_dot() or c.is_dotdot():
                continue
            raise PyIsoException("Directory must be empty to use rm_directory")

        child.parent.remove_child(child, index, self.pvd)

        self.pvd.remove_entry(child.file_length(), child.file_ident)
        self._reshuffle_extents()

    def add_eltorito(self, bootfile_path, bootcatfile="/BOOT.CAT;1",
                     rr_bootcatfile="boot.cat", joliet_bootcatfile="/boot.cat",
                     boot_load_size=None):
        '''
        Add an El Torito Boot Record, and associated files, to the ISO.  The
        file that will be used as the bootfile must be passed into this function
        and must already be present on the ISO.

        Parameters:
         bootfile_path - The file to use as the boot file; it must already exist on
                         this ISO.
         bootcatfile - The fake file to use as the boot catalog entry; set to
                       BOOT.CAT;1 by default.
         rr_bootcatfile - The Rock Ridge name for the fake file to use as the boot
                          catalog entry; set to "boot.cat" by default.
         joliet_bootcatfile - The Joliet name for the fake file to use as the boot
                              catalog entry; set to "boot.cat" by default.
         boot_load_size - The number of sectors to use for the boot entry; if set
                          to None (the default), the number of sectors will be
                          calculated.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.eltorito_boot_catalog is not None:
            raise PyIsoException("This ISO already has an El Torito Boot Record")

        # In order to add an El Torito boot, we need to do the following:
        # 1.  Find the boot file record (which must already exist).
        # 2.  Construct a BootCatalog.
        # 3.  Add the BootCatalog file to the filesystem.  When this step is
        #     over, we will know the extent that the file lives at.
        # 4.  Add the boot record to the ISO.

        # Step 1.
        child,index = self._find_record(self.pvd, bootfile_path)

        if boot_load_size is None:
            sector_count = ceiling_div(child.file_length(), self.pvd.logical_block_size()) * self.pvd.logical_block_size()/512
        else:
            sector_count = boot_load_size

        # Step 2.
        br = BootRecord()
        br.new("EL TORITO SPECIFICATION")
        self.brs.append(br)

        # Step 3.
        self.eltorito_boot_catalog = EltoritoBootCatalog(br)
        self.eltorito_boot_catalog.new(br, sector_count)
        self.eltorito_boot_catalog.set_initial_entry_dirrecord(child)

        # Step 4.
        fp = StringIO.StringIO()
        fp.write(self.eltorito_boot_catalog.record())
        fp.seek(0)
        (name, parent) = self._name_and_parent_from_path(bootcatfile)

        check_iso9660_filename(name, self.interchange_level)

        bootcat_dirrecord = DirectoryRecord()
        length = len(fp.getvalue())
        bootcat_dirrecord.new_fp(fp, length, name, parent,
                                 self.pvd.sequence_number(), self.rock_ridge,
                                 rr_bootcatfile)
        parent.add_child(bootcat_dirrecord, self.pvd, False)
        self.pvd.add_entry(length)
        if bootcat_dirrecord.rock_ridge is not None and bootcat_dirrecord.rock_ridge.ce_record is not None:
            self.pvd.add_to_space_size(self.pvd.logical_block_size())

        self.eltorito_boot_catalog.set_dirrecord(bootcat_dirrecord)

        if self.joliet_vd is not None:
            (joliet_name, joliet_parent) = self._joliet_name_and_parent_from_path(joliet_bootcatfile)

            joliet_name = joliet_name.encode('utf-16_be')

            joliet_rec = DirectoryRecord()
            joliet_rec.new_fp(fp, length, joliet_name, joliet_parent, self.joliet_vd.sequence_number(), False, None)
            joliet_parent.add_child(joliet_rec, self.joliet_vd, False)
            self.joliet_vd.add_entry(length)
            self.joliet_vd.add_to_space_size(self.joliet_vd.logical_block_size())

        self.pvd.add_to_space_size(self.pvd.logical_block_size())
        self._reshuffle_extents()

        if self.joliet_vd is not None:
            # If we are doing Joliet, then we must update the joliet record with
            # the new extent location *after* having done the reshuffle.
            joliet_rec.new_extent_loc = bootcat_dirrecord.new_extent_loc

    def rm_eltorito(self):
        '''
        Remove the El Torito boot record (and associated files) from the ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.eltorito_boot_catalog is None:
            raise PyIsoException("This ISO doesn't have an El Torito Boot Record")

        eltorito_index = None
        for index,br in enumerate(self.brs):
            if br.boot_system_identifier == "{:\x00<32}".format("EL TORITO SPECIFICATION"):
                eltorito_index = index
                break

        if eltorito_index is None:
            # There was a boot catalog, but no corresponding boot record.  This
            # should never happen.
            raise PyIsoException("El Torito boot catalog found with no corresponding boot record")

        extent, = struct.unpack("=L", br.boot_system_use[:4])

        del self.brs[eltorito_index]

        self.eltorito_boot_catalog = None

        self.pvd.remove_from_space_size(self.pvd.logical_block_size())
        if self.joliet_vd is not None:
            self.joliet_vd.remove_from_space_size(self.joliet_vd.logical_block_size())

        # Search through the filesystem, looking for the file that matches the
        # extent that the boot catalog lives at.
        dirs = [self.pvd.root_directory_record()]
        while dirs:
            curr = dirs.pop(0)
            for index,child in enumerate(curr.children):
                if child.is_dot() or child.is_dotdot():
                    continue

                if child.is_dir():
                    dirs.append(child)
                else:
                    if child.extent_location() == extent:
                        # We found the child
                        child.parent.remove_child(child, index, self.pvd)
                        self.pvd.remove_entry(child.file_length())
                        if self.joliet_vd is not None:
                            self.joliet_vd.remove_entry(child.file_length())
                        self._reshuffle_extents()
                        return

        raise PyIsoException("Could not find boot catalog file to remove!")

    def add_symlink(self, symlink_path, rr_symlink_name, rr_path):
        '''
        Add a symlink from rr_symlink_name to the rr_path.  The non-RR name
        of the symlink must also be provided.

        Parameters:
         symlink_path - The ISO9660 name of the symlink itself on the ISO.
         rr_symlink_name - The Rock Ridge name of the symlink itself on the ISO.
         rr_path - The Rock Ridge name of the entry on the ISO that the symlink
                       points to.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if not self.rock_ridge:
            raise PyIsoException("Can only add symlinks to a Rock Ridge ISO")

        (name, parent) = self._name_and_parent_from_path(symlink_path)

        if rr_path[0] == '/':
            raise PyIsoException("Rock Ridge symlink target path must be relative")

        rec = DirectoryRecord()
        rec.new_symlink(name, parent, rr_path, self.pvd.sequence_number(),
                        rr_symlink_name)
        parent.add_child(rec, self.pvd, False)
        self._reshuffle_extents()

    def list_dir(self, iso_path):
        '''
        Generate a list of all of the file/directory objects in the specified
        location on the ISO.

        Parameters:
         iso_path - The path on the ISO to look up information for.
        Yields:
         Children of this path.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        rec,index = self._find_record(self.pvd, iso_path)

        if not rec.is_dir():
            raise PyIsoException("Record is not a directory!")

        for child in rec.children:
            yield child

    def get_entry(self, iso_path):
        '''
        Get information about whether a particular iso_path is a directory or a
        regular file.

        Parameters:
         iso_path - The path on the ISO to look up information for.
        Returns:
         A DirectoryRecord object representing the path.
        '''
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        rec,index = self._find_record(self.pvd, iso_path)

        return rec

    def add_isohybrid(self, isohybrid_fp, part_entry=1, mbr_id=None,
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
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        isohybrid_fp.seek(0, os.SEEK_END)
        size = isohybrid_fp.tell()
        if size != 432:
            raise PyIsoException("The isohybrid file must be exactly 432 bytes")

        if self.eltorito_boot_catalog is None:
            raise PyIsoException("The ISO must have an El Torito Boot Record to add isohybrid support")

        if self.eltorito_boot_catalog.initial_entry.sector_count != 4:
            raise PyIsoException("El Torito Boot Catalog sector count must be 4 (was actually 0x%x)" % (self.eltorito_boot_catalog.initial_entry.sector_count))

        # Now check that the eltorito boot file contains the appropriate
        # signature (offset 0x40, '\xFB\xC0\x78\x70')
        bootfile_dirrecord = self.eltorito_boot_catalog.initial_entry_dirrecord
        data_fp,data_length = bootfile_dirrecord.open_data(self.pvd.logical_block_size())
        data_fp.seek(0x40, os.SEEK_CUR)
        signature = data_fp.read(4)
        if signature != '\xfb\xc0\x78\x70':
            raise PyIsoException("Invalid signature on boot file for iso hybrid")

        isohybrid_fp.seek(0)
        self.isohybrid_mbr = IsoHybrid()
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
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        self.isohybrid_mbr = None

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
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        # now that we are closed, re-initialize everything
        self._initialize()

    # FIXME: we might need an API call to manipulate permission bits on
    # individual files.
    # FIXME: it is possible, though possibly complicated, to add
    # Joliet/RockRidge to an ISO that doesn't currently have it.  We may want
    # to investigate adding this support.
