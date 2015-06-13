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
import os
import bisect

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

class PyIsoException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class VolumeDescriptorDate(object):
    '''
    A class to represent a Volume Descriptor Date as described in Ecma-119
    section 8.4.26.1.  The Volume Descriptor Date consists of a year (from 1 to
    9999), month (from 1 to 12), day of month (from 1 to 31), hour (from 0
    to 23), minute (from 0 to 59), second (from 0 to 59), hundredths of second,
    and offset from GMT in 15-minute intervals (from -48 to +52) fields.  There
    are two main ways to use this class: either to instantiate and then parse a
    string to fill in the fields (the parse() method), or to create a new entry
    with a tm structure (the new() method).
    '''
    def __init__(self):
        self.initialized = False
        self.time_fmt = "%Y%m%d%H%M%S"
        self.empty_string = '0'*16 + '\x00'

    def parse(self, datestr):
        '''
        Parse a Volume Descriptor Date out of a string.  A string of all zeros
        is valid, which means that the date in this field was not specified.
        '''
        if self.initialized:
            raise PyIsoException("This Volume Descriptor Date object is already initialized")

        if len(datestr) != 17:
            raise PyIsoException("Invalid ISO9660 date string")

        if datestr == self.empty_string:
            # Ecma-119, 8.4.26.1 specifies that if the string was all zero, the
            # time wasn't specified.  This is valid, but we can't do any
            # further work, so just bail out of here.
            self.year = 0
            self.month = 0
            self.dayofmonth = 0
            self.hour = 0
            self.minute = 0
            self.second = 0
            self.hundredthsofsecond = 0
            self.gmtoffset = 0
            self.present = False
        else:
            timestruct = time.strptime(datestr[:-3], self.time_fmt)
            self.year = timestruct.tm_year
            self.month = timestruct.tm_mon
            self.dayofmonth = timestruct.tm_mday
            self.hour = timestruct.tm_hour
            self.minute = timestruct.tm_min
            self.second = timestruct.tm_sec
            self.hundredthsofsecond = int(datestr[14:15])
            self.gmtoffset = struct.unpack("=b", datestr[16])
            self.present = True

        self.initialized = True
        self.date_str = datestr

    def record(self):
        '''
        Return the date string for this object.
        '''
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor Date is not yet initialized")

        return self.date_str

    def new(self, tm):
        '''
        Create a new Volume Descriptor Date.  If tm is None, then this Volume
        Descriptor Date will be full of zeros (meaning not specified).  If tm
        is not None, it is expected to be a struct_time object, at which point
        this Volume Descriptor Date object will be filled in with data from that
        struct_time.
        '''
        if self.initialized:
            raise PyIsoException("This Volume Descriptor Date object is already initialized")

        if tm is not None:
            local = time.localtime(tm)
            self.year = local.tm_year
            self.month = local.tm_mon
            self.day_of_month = local.tm_mday
            self.hour = local.tm_hour
            self.minute = local.tm_min
            self.second = local.tm_sec
            self.hundredthsofsecond = 0
            self.gmtoffset = gmtoffset_from_tm(tm, local)
            self.date_str = time.strftime(self.time_fmt, local) + "{:0<2}".format(self.hundredthsofsecond) + struct.pack("=b", self.gmtoffset)
            self.present = True
        else:
            self.year = 0
            self.month = 0
            self.dayofmonth = 0
            self.hour = 0
            self.minute = 0
            self.second = 0
            self.hundredthsofsecond = 0
            self.gmtoffset = 0
            self.date_str = self.empty_string
            self.present = False

        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("This Volume Descriptor Date is not yet initialized")
        if self.present:
            return "%.4d/%.2d/%.2d %.2d:%.2d:%.2d.%.2d" % (self.year,
                                                           self.month,
                                                           self.dayofmonth,
                                                           self.hour,
                                                           self.minute,
                                                           self.second,
                                                           self.hundredthsofsecond)
        else:
            return "N/A"

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
        '''
        if self.initialized:
            raise PyIsoException("This File or Text identifier is already initialized")

        if len(text) > 128:
            raise PyIsoException("Length of text must be <= 128")

        if isfile:
            self.text = "{:<127}".format(text)
            self.filename = text
        else:
            self.text = "{:<128}".format(text)

        self.isfile = isfile
        self.initialized = True

    def is_file(self):
        '''
        Return True if this is a file identifier, False otherwise.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        return self.isfile

    def is_text(self):
        '''
        Returns True if this is a text identifier, False otherwise.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        return not self.isfile

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        fileortext = "Text"
        if self.isfile:
            fileortext = "File"
        return "%s (%s)" % (self.text, fileortext)

    def record(self):
        '''
        Returns the file or text identification string suitable for recording.
        '''
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")
        if self.isfile:
            return "\x5f" + self.text
        # implicitly a text identifier
        return self.text

    def _check_filename(self, is_primary):
        if not self.initialized:
            raise PyIsoException("This File or Text identifier is not yet initialized")

        if self.isfile:
            interchange_level = 1
            if not is_primary:
                interchange_level = 3
            check_iso9660_filename(self.filename, interchange_level)

class DirectoryRecordDate(object):
    '''
    A class to represent a Directory Record date as described in Ecma-119
    section 9.1.5.  The Directory Record date consists of the number of years
    since 1900, the month, the day of the month, the hour, the minute, the
    second, and the offset from GMT in 15 minute intervals.  There are two main
    ways to use this class: either to instantiate and then parse a string to
    fill in the fields (the parse() method), or to create a new entry with a
    tm structure (the new() method).
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=BBBBBBb"

    def parse(self, datestr):
        '''
        Parse a Directory Record date out of a string.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record Date already initialized")

        (self.years_since_1900, self.month, self.day_of_month, self.hour,
         self.minute, self.second,
         self.gmtoffset) = struct.unpack(self.fmt, datestr)

        self.initialized = True

    def new(self):
        '''
        Create a new Directory Record date based on the current time.
        '''
        if self.initialized:
            raise PyIsoException("Directory Record Date already initialized")

        # This algorithm was ported from cdrkit, genisoimage.c:iso9660_date()
        tm = time.time()
        local = time.localtime(tm)
        self.years_since_1900 = local.tm_year - 1900
        self.month = local.tm_mon
        self.day_of_month = local.tm_mday
        self.hour = local.tm_hour
        self.minute = local.tm_min
        self.second = local.tm_sec
        self.gmtoffset = gmtoffset_from_tm(tm, local)
        self.initialized = True

    def record(self):
        '''
        Return a string representation of the Directory Record date.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record Date not initialized")

        return struct.pack(self.fmt, self.years_since_1900, self.month,
                           self.day_of_month, self.hour, self.minute,
                           self.second, self.gmtoffset)

class DirectoryRecord(object):
    FILE_FLAG_EXISTENCE_BIT = 0
    FILE_FLAG_DIRECTORY_BIT = 1
    FILE_FLAG_ASSOCIATED_FILE_BIT = 2
    FILE_FLAG_RECORD_BIT = 3
    FILE_FLAG_PROTECTION_BIT = 4
    FILE_FLAG_MULTI_EXTENT_BIT = 7

    DATA_ON_ORIGINAL_ISO = 1
    DATA_IN_EXTERNAL_FP = 2

    # 22 00 17 00 00 00 00 00 00 17 00 08 00 00 00 00 08 00 73 04 18 0c 0d 08 f0 02 00 00 01 00 00 01 01 00'
    # Len: 0x22 (34 bytes)
    # Xattr Len: 0x0
    # Extent Location: 0x17 (23)
    # Data Length: 0x800 (2048)
    # Years since 1900: 0x73 (115)
    # Month: 0x4 (4, April)
    # Day of Month: 0x18 (24)
    # Hour: 0xc (12)
    # Minute: 0xd (13)
    # Second: 0x08 (8)
    # GMT Offset: 0xf0 (-16)
    # File Flags: 0x2 (No existence, no directory, associated file, no record, no protection, no multi-extent)
    # File Unit Size: 0x0 (0)
    # Interleave Gap Size: 0x0 (0)
    # SeqNum: 0x1 (1)
    # Len Fi: 0x1 (1)
    # File Identifier: 0x0 (0, root directory)

    def __init__(self):
        self.initialized = False
        self.fmt = "=BBLLLL7sBBBHHB"

    def parse(self, record, data_fp, parent):
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

        if len(record) != self.dr_len:
            # The record we were passed doesn't have the same information in it
            # as the directory entry thinks it should
            raise PyIsoException("Length of directory entry doesn't match internal check")

        if extent_location_le != swab_32bit(extent_location_be):
            raise PyIsoException("Little-endian (%d) and big-endian (%d) extent location disagree" % (extent_location_le, swab_32bit(extent_location_be)))
        self.original_extent_loc = extent_location_le
        self.new_extent_loc = None

        if data_length_le != swab_32bit(data_length_be):
            raise PyIsoException("Little-endian and big-endian data length disagree")
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
        if self.parent is None:
            self.is_root = True
            # A root directory entry should always be exactly 34 bytes.
            if self.dr_len != 34:
                raise PyIsoException("Root directory entry of invalid length!")
            # A root directory entry should always have 0 as the identifier.
            if record[33] != '\x00':
                raise PyIsoException("Invalid root directory entry identifier")
            self.file_ident = record[33]
            self.isdir = True
        else:
            self.file_ident = record[33:33 + self.len_fi]
            if self.file_flags & (1 << self.FILE_FLAG_DIRECTORY_BIT):
                self.isdir = True

        if self.xattr_len != 0:
            if self.file_flags & (1 << self.FILE_FLAG_RECORD_BIT):
                raise PyIsoException("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise PyIsoException("Protection Bit not allowed with Extended Attributes")

        self.original_data_location = self.DATA_ON_ORIGINAL_ISO
        self.data_fp = data_fp
        self.initialized = True

    def _new(self, mangledname, parent, seqnum, isdir, pvd, length):
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

        self.data_length = length

        self.file_ident = mangledname

        self.isdir = isdir

        self.seqnum = seqnum
        # For a new directory record entry, there is no original_extent_loc,
        # so we leave it at None.
        self.original_extent_loc = None
        self.len_fi = len(self.file_ident)
        self.dr_len = struct.calcsize(self.fmt) + self.len_fi
        self.dr_len += (self.dr_len % 2)

        # When adding a new directory, we always add a full extent.  This number
        # tracks how much of that block we are using so that we can figure out
        # if we need to allocate a new block.
        # FIXME: to be more consistent with what we have done elsewhere in the
        # code, we should probably just add the actual size that the directory
        # is using, and then pad it out as necessary.
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
        # Note: it is important that this object be initialized *before* we do
        # the extent shuffle below, otherwise we'll throw exceptions when trying
        # to set the extent for this new entry.
        self.initialized = True

        self.parent = parent
        if parent is None:
            # If no parent, then this is the root
            self.is_root = True
            self.new_extent_loc = 23
        else:
            self.is_root = False
            self.parent.add_child(self, pvd, False)

    def new_fp(self, fp, length, isoname, parent, seqnum, pvd):
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self._new(isoname, parent, seqnum, False, pvd, length)

    def new_root(self, seqnum, pvd):
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new('\x00', None, seqnum, True, pvd, 2048)

    def new_dot(self, root, seqnum, pvd):
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new('\x00', root, seqnum, True, pvd, 2048)

    def new_dotdot(self, root, seqnum, pvd):
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new('\x01', root, seqnum, True, pvd, 2048)

    def new_dir(self, name, parent, seqnum, pvd):
        if self.initialized:
            raise PyIsoException("Directory Record already initialized")

        self._new(name, parent, seqnum, True, pvd, 2048)

    def add_child(self, child, pvd, parsing):
        '''
        A method to add a child to this object.  Note that this is called both
        during parsing and when adding a new object to the system, so it
        it shouldn't have any functionality that is not appropriate for both.
        '''
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        if not self.isdir:
            raise Exception("Trying to add a child to a record that is not a directory")

        # First ensure that this is not a duplicate.
        for c in self.children:
            if c.file_ident == child.file_ident:
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
            self.data_length += pvd.logical_block_size()
            # This also increases the size of the complete volume, so update
            # that here.
            pvd.add_to_space_size(pvd.logical_block_size())

    def remove_child(self, child, index, pvd):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        self.curr_length -= child.directory_record_length()
        if (self.data_length - self.curr_length) > pvd.logical_block_size():
            self.data_length -= pvd.logical_block_size()
            pvd.remove_from_space_size(pvd.logical_block_size())

        del self.children[index]

    def is_dir(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.isdir

    def is_file(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return not self.isdir

    def is_dot(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.file_ident == '\x00'

    def is_dotdot(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.file_ident == '\x01'

    def directory_record_length(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.dr_len

    def extent_location(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        if self.new_extent_loc is None:
            return self.original_extent_loc
        return self.new_extent_loc

    def file_identifier(self):
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
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        return self.data_length

    def record(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = DirectoryRecordDate()
        self.date.new()

        pad = '\x00' * ((struct.calcsize(self.fmt) + self.len_fi) % 2)

        new_extent_loc = self.original_extent_loc
        if new_extent_loc is None:
            new_extent_loc = self.new_extent_loc

        return struct.pack(self.fmt, self.dr_len, self.xattr_len,
                           new_extent_loc, swab_32bit(new_extent_loc),
                           self.data_length, swab_32bit(self.data_length),
                           self.date.record(), self.file_flags,
                           self.file_unit_size, self.interleave_gap_size,
                           self.seqnum, swab_16bit(self.seqnum),
                           self.len_fi) + self.file_ident + pad

    def open_data(self, logical_block_size):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        if self.isdir:
            raise PyIsoException("Cannot write out a directory")

        if self.original_data_location == self.DATA_ON_ORIGINAL_ISO:
            self.data_fp.seek(self.original_extent_loc * logical_block_size)
        else:
            self.data_fp.seek(0)

        return self.data_fp,self.data_length

    def add_to_location(self, extents):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        if self.new_extent_loc is None:
            self.new_extent_loc = self.original_extent_loc
        self.new_extent_loc += extents
        # FIXME: we really need to recurse into all subdirectories and files to
        # change their locations.

    def remove_from_location(self, extents):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")

        if self.new_extent_loc is None:
            self.new_extent_loc = self.original_extent_loc
        self.new_extent_loc -= extents
        # FIXME: we really need to recurse into all subdirectories and files to
        # change their locations.

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("Directory Record not yet initialized")
        retstr  = "Directory Record Length:   %d\n" % self.dr_len
        retstr += "Extended Attribute Length: %d\n" % self.xattr_len
        retstr += "Extent Location:           %d\n" % self.original_extent_loc
        retstr += "Data Length:               %d\n" % self.data_length
        retstr += "Date and Time:             %.2d/%.2d/%.2d %.2d:%.2d:%.2d (%d)\n" % (self.date.years_since_1900 + 1900, self.date.month, self.date.day_of_month, self.date.hour, self.date.minute, self.date.second, self.date.gmtoffset)
        retstr += "File Flags:                %d\n" % self.file_flags
        retstr += "File Unit Size:            %d\n" % self.file_unit_size
        retstr += "Interleave Gap Size:       %d\n" % self.interleave_gap_size
        retstr += "Seqnum:                    %d\n" % self.seqnum
        retstr += "Len FI                     %d\n" % self.len_fi
        retstr += "File Identifier:           '%s'\n" % self.file_ident
        return retstr

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
        # order.
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

class PrimaryVolumeDescriptor(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def parse(self, vd, data_fp):
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
        self.root_dir_record.parse(root_dir_record, data_fp, None)

        self.initialized = True

    def new(self, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use):
        if self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is already initialized")

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
        self.root_dir_record.new_root(seqnum, self)

        if len(vol_set_ident) > 128:
            raise PyIsoException("The maximum length for the volume set identifier is 128")
        self.volume_set_identifier = "{:<128}".format(vol_set_ident)

        self.publisher_identifier = pub_ident
        self.publisher_identifier._check_filename(True)

        self.preparer_identifier = preparer_ident
        self.preparer_identifier._check_filename(True)

        self.application_identifier = app_ident
        self.application_identifier._check_filename(True)

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

    def logical_block_size(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        return self.log_block_size

    def path_table_size(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        return self.path_tbl_size

    def root_directory_record(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def sequence_number(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        return self.seqnum

    def set_sequence_number(self, seqnum):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        if seqnum > self.set_size:
            raise PyIsoException("Sequence number larger than volume set size")

        self.seqnum = seqnum

    def set_set_size(self, set_size):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        if set_size > (2**16 - 1):
            raise PyIsoException("Set size too large to fit into 16-bit field")

        self.set_size = set_size

    def add_to_ptr_size(self, additional_bytes):
        '''
        Increase the size of the path table by "addition" bytes.
        '''
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        self.path_tbl_size += additional_bytes
        # path_table_location_be minus path_table_location_le gives us the
        # number of extents the path table is taking up.  We multiply that by
        # block size to get the number of bytes to determine if we will overflow
        # the extent.
        if self.path_tbl_size > (self.path_table_location_be - self.path_table_location_le) * self.log_block_size:
            # If we overflowed the little endian path table location, then we
            # need to move the big endian one down.  We always move down in
            # multiples of 4096, so 2 extents.
            self.path_table_location_be += 2
            # We also need to update the space size with this; since we are
            # adding two extents for the little and two for the big, add four
            # total extents.
            self.add_to_space_size(4 * self.log_block_size)
            # We also need to move the starting extent for the root directory
            # record down.
            self.root_dir_record.add_to_location(4)

    def remove_from_ptr_size(self, removal_bytes):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        self.path_tbl_size -= removal_bytes
        current_extents = self.path_table_location_be - self.path_table_location_le
        new_extents = ceiling_div(self.path_tbl_size, 4096) * 2

        if new_extents > current_extents:
            # This should never happen.
            raise PyIsoException("This should never happen")

        if new_extents == current_extents:
            # No change in the number of extents, just get out of here.
            return

        self.path_table_location_be -= 2
        self.remove_from_space_size(4 * self.log_block_size)
        self.root_dir_record.remove_from_location(4)

    def add_to_space_size(self, addition_bytes):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")
        # The "addition" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size += ceiling_div(addition_bytes, self.log_block_size)

    def remove_from_space_size(self, removal_bytes):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")
        # The "removal" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size -= ceiling_div(removal_bytes, self.log_block_size)

    def record(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        now = time.time()

        vol_create_date = VolumeDescriptorDate()
        vol_create_date.new(now)

        vol_mod_date = VolumeDescriptorDate()
        vol_mod_date.new(now)

        vol_effective_date = VolumeDescriptorDate()
        vol_effective_date.new(now)

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

    def reshuffle_extents(self):
        # Here we re-walk the entire tree, re-assigning extents as necessary.
        dirs = [(self.root_directory_record(), True)]
        current_extent = self.root_directory_record().extent_location()
        while dirs:
            dir_record,root_record = dirs.pop(0)
            for index,child in enumerate(dir_record.children):
                if child.is_dot():
                    # With a normal directory, the extent for itself was already
                    # assigned when the parent assigned extents to all of the
                    # children, so we don't increment the extent.  The root
                    # directory record is a special case, where there was no
                    # parent so we need to manually move the extent forward one.
                    if root_record:
                        child.new_extent_loc = current_extent
                        current_extent += ceiling_div(self.root_directory_record().data_length, self.log_block_size)
                    else:
                        child.new_extent_loc = child.parent.extent_location()
                elif child.is_dotdot():
                    if root_record:
                        # Special case of the root directory record.  In this
                        # case, we assume that the dot record has already been
                        # added, and is the one before us.  We set the dotdot
                        # extent location to the same as the dot one.
                        child.new_extent_loc = child.parent.extent_location()
                    else:
                        child.new_extent_loc = child.parent.parent.extent_location()
                else:
                    child.new_extent_loc = current_extent
                    if child.is_dir():
                        dirs.append((child, False))
                    current_extent += ceiling_div(child.data_length, self.log_block_size)

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("This Primary Volume Descriptor is not yet initialized")

        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Identifier:             '%s'\n" % self.volume_identifier
        retstr += "Space Size:                    %d\n" % self.space_size
        retstr += "Set Size:                      %d\n" % self.set_size
        retstr += "SeqNum:                        %d\n" % self.seqnum
        retstr += "Logical Block Size:            %d\n" % self.log_block_size
        retstr += "Path Table Size:               %d\n" % self.path_tbl_size
        retstr += "Path Table Location:           %d\n" % self.path_table_location_le
        retstr += "Optional Path Table Location:  %d\n" % self.optional_path_table_location_le
        retstr += "Root Directory Record:         '%s'\n" % self.root_dir_record
        retstr += "Volume Set Identifier:         '%s'\n" % self.volume_set_identifier
        retstr += "Publisher Identifier:          '%s'\n" % self.publisher_identifier
        retstr += "Preparer Identifier:           '%s'\n" % self.preparer_identifier
        retstr += "Application Identifier:        '%s'\n" % self.application_identifier
        retstr += "Copyright File Identifier:     '%s'\n" % self.copyright_file_identifier
        retstr += "Abstract File Identifier:      '%s'\n" % self.abstract_file_identifier
        retstr += "Bibliographic File Identifier: '%s'\n" % self.bibliographic_file_identifier
        retstr += "Volume Creation Date:          '%s'\n" % self.volume_creation_date
        retstr += "Volume Modification Date:      '%s'\n" % self.volume_modification_date
        retstr += "Volume Expiration Date:        '%s'\n" % self.volume_expiration_date
        retstr += "Volume Effective Date:         '%s'\n" % self.volume_effective_date
        retstr += "File Structure Version:        %d\n" % self.file_structure_version
        retstr += "Application Use:               '%s'" % self.application_use
        return retstr

class VolumeDescriptorSetTerminator(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sB2041s"

    def parse(self, vd):
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
        # According to Ecma-119, 8.3.4, the rest of the terminator should be 0
        if unused != '\x00'*2041:
            raise PyIsoException("Invalid unused field")
        self.initialized = True

    def new(self):
        if self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR
        self.identifier = "CD001"
        self.version = 1
        self.initialized = True

    def record(self):
        if not self.initialized:
            raise PyIsoException("Volume Descriptor Set Terminator not yet initialized")
        return struct.pack(self.fmt, self.descriptor_type,
                           self.identifier, self.version, "\x00" * 2041)

class BootRecord(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sB32s32s1977s"

    def parse(self, vd):
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
        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("Boot Record not yet initialized")

        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "Boot System Identifier:        '%s'\n" % self.boot_system_identifier
        retstr += "Boot Identifier:               '%s'\n" % self.boot_identifier
        retstr += "Boot System Use:               '%s'\n" % self.boot_system_use
        return retstr

class SupplementaryVolumeDescriptor(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def parse(self, vd, data_fp):
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
        self.path_table_size = path_table_size_le

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
        self.root_directory_record = DirectoryRecord()
        self.root_directory_record.parse(root_dir_record, data_fp, None)

        self.joliet = False
        if (self.flags & 0x1) == 0 and self.escape_sequences[:3] in ['%/@', '%/C', '%/E']:
            self.joliet = True
        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("Supplementary Volume Descriptor not initialized")

        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "Flags:                         %d\n" % self.flags
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Identifier:             '%s'\n" % self.volume_identifier
        retstr += "Space Size:                    %d\n" % self.space_size
        retstr += "Escape Sequences:              '%s'\n" % self.escape_sequences
        retstr += "Set Size:                      %d\n" % self.set_size
        retstr += "SeqNum:                        %d\n" % self.seqnum
        retstr += "Logical Block Size:            %d\n" % self.log_block_size
        retstr += "Path Table Size:               %d\n" % self.path_table_size
        retstr += "Path Table Location:           %d\n" % self.path_table_location_le
        retstr += "Optional Path Table Location:  %d\n" % self.optional_path_table_location_le
        retstr += "Volume Set Identifier:         '%s'\n" % self.volume_set_identifier
        retstr += "Publisher Identifier:          '%s'\n" % self.publisher_identifier
        retstr += "Preparer Identifier:           '%s'\n" % self.preparer_identifier
        retstr += "Application Identifier:        '%s'\n" % self.application_identifier
        retstr += "Copyright File Identifier:     '%s'\n" % self.copyright_file_identifier
        retstr += "Abstract File Identifier:      '%s'\n" % self.abstract_file_identifier
        retstr += "Bibliographic File Identifier: '%s'\n" % self.bibliographic_file_identifier
        retstr += "Volume Creation Date:          '%s'\n" % self.volume_creation_date
        retstr += "Volume Modification Date:      '%s'\n" % self.volume_modification_date
        retstr += "Volume Expiration Date:        '%s'\n" % self.volume_expiration_date
        retstr += "Volume Effective Date:         '%s'\n" % self.volume_effective_date
        retstr += "File Structure Version:        %d\n" % self.file_structure_version
        retstr += "Application Use:               '%s'" % self.application_use
        return retstr

class VolumePartition(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sBB32s32sLLLL1960s"

    def parse(self, vd):
        if self.initialized:
            raise PyIsoException("Volume Partition already initialized")

        (self.descriptor_type, self.identifier, self.version, unused,
         self.system_identifier, self.volume_partition_identifier,
         volume_partition_location_le, volume_partition_location_be,
         volume_partition_size_le, volume_partition_size_be,
         self.system_use) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.6.1, the volume partition type should be 3
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
            raise PyIsoException("Invalid descriptor type")
        # According to Ecma-119, 8.6.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise PyIsoException("Invalid identifier")
        # According to Ecma-119, 8.6.3, the version should be 1
        if self.version != 1:
            raise PyIsoException("Invalid version")
        # According to Ecma-119, 8.6.4, the unused field should be 0
        if unused != 0:
            raise PyIsoException("Unused field should be zero")

        if volume_partition_location_le != swab_32bit(volume_partition_location_be):
            raise PyIsoException("Little-endian and big-endian volume partition location disagree")
        self.volume_partition_location = volume_partition_location_le

        if volume_partition_size_le != swab_32bit(volume_partition_size_be):
            raise PyIsoException("Little-endian and big-endian volume partition size disagree")
        self.volume_partition_size = volume_partition_size_le

        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise PyIsoException("Volume Partition not initialized")

        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Partition Identifier:   '%s'\n" % self.volume_partition_identifier
        retstr += "Volume Partition Location:     %d\n" % self.volume_partition_location
        retstr += "Volume Partition Size:         %d\n" % self.volume_partition_size
        retstr += "System Use:                    '%s'" % self.system_use
        return retstr

class ExtendedAttributeRecord(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=HHHHH17s17s17s17sBBHH32s64sBB64sHH"

    def parse(self, record):
        if self.initialized:
            raise PyIsoException("Extended Attribute Record already initialized")

        (owner_identification_le, owner_identification_be,
         group_identification_le, group_identification_be,
         self.permissions, file_create_date_str, file_mod_date_str,
         file_expire_date_str, file_effective_date_str,
         self.record_format, self.record_attributes, record_length_le,
         record_length_be, self.system_identifier, self.system_use,
         self.extended_attribute_record_version,
         self.length_of_escape_sequences, unused,
         len_au_le, len_au_be) = struct.unpack(self.fmt, record)

        if owner_identification_le != swab_16bit(owner_identification_be):
            raise PyIsoException("Little-endian and big-endian owner identification disagree")
        self.owner_identification = owner_identification_le

        if group_identification_le != swab_16bit(group_identification_be):
            raise PyIsoException("Little-endian and big-endian group identification disagree")
        self.group_identification = group_identification_le

        if record_length_le != swab_16bit(record_length_be):
            raise PyIsoException("Little-endian and big-endian record length disagree")
        self.record_length = record_length_le

        if len_au_le != swab_16bit(len_au_be):
            raise PyIsoException("Little-endian and big-endian record length disagree")
        self.len_au = len_au_le

        self.file_creation_date = VolumeDescriptorDate(file_create_date_str)
        self.file_modification_date = VolumeDescriptorDate(file_mod_date_str)
        self.file_expiration_date = VolumeDescriptorDate(file_expire_date_str)
        self.file_effective_date = VolumeDescriptorDate(file_effective_date_str)

        self.application_use = record[250:250 + self.len_au]
        self.escape_sequences = record[250 + self.len_au:250 + self.len_au + self.length_of_escape_sequences]

class PathTableRecord(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=BBLH"

    def parse(self, data):
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        (self.len_di, self.xattr_length, self.extent_location,
         self.parent_directory_num) = struct.unpack(self.fmt, data[:8])

        if self.len_di % 2 != 0:
            self.directory_identifier = data[8:-1]
        else:
            self.directory_identifier = data[8:]
        self.dirrecord = None
        self.initialized = True

    def _record(self, ext_loc, parent_dir_num):
        ret = struct.pack(self.fmt, self.len_di, self.xattr_length,
                          ext_loc, parent_dir_num)
        ret += self.directory_identifier + '\x00'*(self.len_di % 2)

        return ret

    def record_little_endian(self):
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        return self._record(self.extent_location, self.parent_directory_num)

    def record_big_endian(self):
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        return self._record(swab_32bit(self.extent_location),
                            swab_16bit(self.parent_directory_num))

    def record_length(self, len_di):
        # This method can be called even if the object isn't initialized
        return struct.calcsize(self.fmt) + len_di + (len_di % 2)

    def _new(self, name, dirrecord):
        self.len_di = len(name)
        self.xattr_length = 0 # FIXME: we don't support xattr for now
        self.extent_location = dirrecord.extent_location()
        self.parent_directory_num = 1 # FIXME: fix this
        self.directory_identifier = name
        self.dirrecord = dirrecord
        self.initialized = True

    def new_root(self, dirrecord):
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        self._new("\x00", dirrecord)

    def new_dir(self, name, dirrecord):
        if self.initialized:
            raise PyIsoException("Path Table Record already initialized")

        self._new(name, dirrecord)

    def set_dirrecord(self, dirrecord):
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        self.dirrecord = dirrecord

    def update_extent_location_from_dirrecord(self):
        if not self.initialized:
            raise PyIsoException("Path Table Record not yet initialized")

        self.extent_location = self.dirrecord.extent_location()

    def __lt__(self, other):
        return ptr_lt(self.directory_identifier, other.directory_identifier)

def ptr_lt(str1, str2):
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

# FIXME: is there no better way to do this swab?
def swab_32bit(input_int):
    return struct.unpack("<L", struct.pack(">L", input_int))[0]

def swab_16bit(input_int):
    return struct.unpack("<H", struct.pack(">H", input_int))[0]

def pad(data_size, pad_size):
    pad = pad_size - (data_size % pad_size)
    if pad != pad_size:
        return "\x00" * pad
    return ""

def gmtoffset_from_tm(tm, local):
    gmtime = time.gmtime(tm)
    tmpyear = gmtime.tm_year - local.tm_year
    tmpyday = gmtime.tm_yday - local.tm_yday
    tmphour = gmtime.tm_hour - local.tm_hour
    tmpmin = gmtime.tm_min - local.tm_min

    if tmpyday < 0:
        tmpyday = -1
    else:
        if tmpyear > 0:
            tmpyday = 1
    return -(tmpmin + 60 * (tmphour + 24 * tmpyday)) / 15

def ceiling_div(numer, denom):
    # Doing division and then getting the ceiling is tricky; we do upside-down
    # floor division to make this happen.
    # See https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python.
    return -(-numer // denom)

def check_d1_characters(name):
    for char in name:
        if not char in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                        'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                        'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6',
                        '7', '8', '9', '_']:
            raise PyIsoException("%s is not a valid ISO9660 filename (it contains invalid characters)" % (name))

def check_iso9660_filename(fullname, interchange_level):
    # Check to ensure the name is a valid filename for the ISO according to
    # Ecma-119 7.5.
    # First we split on the semicolon for the version number.
    namesplit = fullname.split(';')

    if len(namesplit) != 2:
        raise PyIsoException("%s is not a valid ISO9660 filename (it must have a version number at the end)" % (fullname))

    name_plus_extension = namesplit[0]
    version = namesplit[1]

    # The second entry should be the version number between 1 and 32767.
    if int(version) < 1 or int(version) > 32767:
        raise PyIsoException("%s has an invalid version number (must be between 1 and 32767" % (fullname))

    # The first entry should be x.y, so we split on the dot.
    dotsplit = name_plus_extension.split('.')
    if len(dotsplit) != 2:
        raise PyIsoException("%s is not a valid ISO9660 filename (it must have a dot)" % (fullname))

    name = dotsplit[0]
    extension = dotsplit[1]

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
        # specified in Ecma-119 7.5.2.
        if len(name) + len(extension) > 30:
            raise PyIsoException("%s is not a valid ISO9660 filename (the length of the name plus extension cannot exceed 30)" % (fullname))

    # Ecma-119 section 7.5.1 says that the file name and extension each contain
    # zero or more d-characters or d1-characters.  While the definition of
    # d-characters and d1-characters is not specified in Ecma-119,
    # http://wiki.osdev.org/ISO_9660 suggests that this consists of A-Z, 0-9, _
    # which seems to correlate with empirical evidence.  Thus we check for that
    # here.
    check_d1_characters(name)
    check_d1_characters(extension)

def check_iso9660_directory(fullname, interchange_level):
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
        if len(fullname) > 31:
            raise PyIsoException("%s is not a valid ISO9660 directory name (it is longer than 31 characters)" % (fullname))

    # Ecma-119 section 7.6.1 says that directory names consist of one or more
    # d-characters or d1-characters.  While the definition of d-characters and
    # d1-characters is not specified in Ecma-119,
    # http://wiki.osdev.org/ISO_9660 suggests that this consists of A-Z, 0-9, _
    # which seems to correlate with empirical evidence.  Thus we check for that
    # here.
    check_d1_characters(fullname)

def check_interchange_level(identifier, is_dir):
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
        try_level_3 = False
    except PyIsoException:
        try_level_3 = True

    if try_level_3:
        cmpfunc(identifier, 3)
        # If the above did not throw an exception, then this
        # is interchange level 3 and we should mark it.
        interchange_level = 3

    return interchange_level

def copy_data(data_length, blocksize, infp, outfp):
    left = data_length
    readsize = blocksize
    while left > 0:
        if left < readsize:
            readsize = left
        outfp.write(infp.read(readsize))
        left -= readsize

class PyIso(object):
    def _parse_volume_descriptors(self):
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
            vd = self.cdfp.read(2048)
            (desc_type,) = struct.unpack("=B", vd[0])
            if desc_type == VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvd = PrimaryVolumeDescriptor()
                pvd.parse(vd, self.cdfp)
                pvds.append(pvd)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
                vdst = VolumeDescriptorSetTerminator()
                vdst.parse(vd)
                vdsts.append(vdst)
                # Once we see a set terminator, we stop parsing.  Oddly,
                # Ecma-119 says there may be multiple set terminators, but in
                # that case I don't know how to tell when we are done parsing
                # volume descriptors.  Leave this for now.
                done = True
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
                br = BootRecord()
                br.parse(vd)
                brs.append(br)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
                svd = SupplementaryVolumeDescriptor()
                svd.parse(vd, self.cdfp)
                svds.append(svd)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
                vpd = VolumePartition()
                vpd.parse(vd)
                vpds.append(vpd)
        return pvds, svds, vpds, brs, vdsts

    def _seek_to_extent(self, extent):
        self.cdfp.seek(extent * self.pvd.logical_block_size())

    def _check_ident(self, fileortext, errmsg):
        if fileortext.is_file():
            try:
                self._find_record("/" + fileortext.filename)
            except PyIsoException:
                raise PyIsoException("%s specifies a file of %s, but that file does not exist at the root level" % (errmsg, fileortext.filename))

    def _walk_iso9660_directories(self):
        interchange_level = 1
        dirs = [self.pvd.root_directory_record()]
        while dirs:
            dir_record = dirs.pop(0)
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
                        padsize = self.pvd.logical_block_size() - (self.cdfp.tell() % self.pvd.logical_block_size())
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
                new_record.parse(struct.pack("=B", lenbyte) + self.cdfp.read(lenbyte - 1), self.cdfp, dir_record)
                length -= lenbyte - 1
                if new_record.is_dir():
                    if not new_record.is_dot() and not new_record.is_dotdot():
                        tmp = check_interchange_level(new_record.file_identifier(), new_record.is_dir())
                        if tmp > interchange_level:
                            interchange_level = tmp
                        dirs.append(new_record)
                    if not new_record.is_dot() and not new_record.is_dotdot():
                        lo = 1
                        hi = len(self.path_table_records)
                        while lo < hi:
                            mid = (lo + hi) // 2
                            if ptr_lt(self.path_table_records[mid].directory_identifier, new_record.file_ident):
                                lo = mid + 1
                            else:
                                hi = mid
                        if lo == len(self.path_table_records):
                            # We didn't find the entry in the ptr, we should abort
                            raise PyIsoException("Directory Records did not match Path Table Records; ISO is corrupt")
                        ptr_index = lo
                        self.path_table_records[ptr_index].set_dirrecord(new_record)
                else:
                    tmp = check_interchange_level(new_record.file_identifier(), new_record.is_dir())
                    if tmp > interchange_level:
                        interchange_level = tmp
                dir_record.add_child(new_record, self.pvd, True)

        return interchange_level

    def _initialize(self):
        self.cdfp = None
        self.pvd = None
        self.svds = []
        self.vpds = []
        self.brs = []
        self.vdsts = []
        self.initialized = False
        self.path_table_records = []

    def _parse_path_table(self, extent, callback):
        self._seek_to_extent(extent)
        left = self.pvd.path_table_size()
        index = 0
        while left > 0:
            ptr = PathTableRecord()
            (len_di,) = struct.unpack("=B", self.cdfp.read(1))
            read_len = ptr.record_length(len_di)
            # ptr.record_length() returns the length of the entire path table
            # record, but we've already read the len_di so read one less.
            ptr.parse(struct.pack("=B", len_di) + self.cdfp.read(read_len - 1))
            left -= read_len
            callback(ptr, index)
            index += 1

    def _little_endian_path_table(self, ptr, index):
        self.path_table_records.append(ptr)

    def _big_endian_path_table(self, ptr, index):
        if ptr.len_di != self.path_table_records[index].len_di or \
           ptr.xattr_length != self.path_table_records[index].xattr_length or \
           swab_32bit(ptr.extent_location) != self.path_table_records[index].extent_location or \
           swab_16bit(ptr.parent_directory_num) != self.path_table_records[index].parent_directory_num or \
           ptr.directory_identifier != self.path_table_records[index].directory_identifier:
            raise PyIsoException("Little endian and big endian path table records do not agree")

    def _find_record(self, path):
        if path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        # If the path is just the slash, we just want the root directory, so
        # get the children there and quit.
        if path == '/':
            return self.pvd.root_directory_record(),0

        # Split the path along the slashes
        splitpath = path.split('/')
        # And remove the first one, since it is always empty
        splitpath.pop(0)

        entries = []
        currpath = splitpath.pop(0)
        children = self.pvd.root_directory_record().children
        index = 0
        while index < len(children):
            child = children[index]
            index += 1

            if child.is_dot() or child.is_dotdot():
                continue

            if child.file_identifier() != currpath:
                continue

            # We found the child, and it is the last one we are looking for;
            # return it.
            if len(splitpath) == 0:
                # We have to remove one from the index since we incremented it
                # above.
                return child,index-1
            else:
                if child.is_dir():
                    children = child.children
                    index = 0
                    currpath = splitpath.pop(0)

        raise PyIsoException("Could not find path %s" % (path))

    def _name_and_parent_from_path(self, iso_path):
        if iso_path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        # First we need to find the parent of this directory, and add this
        # one as a child.
        splitpath = iso_path.split('/')
        # Pop off the front, as that always blank.
        splitpath.pop(0)
        if len(splitpath) > 7:
            # Ecma-119 Section 6.8.2.1 says that the number of levels in the
            # hierarchy shall not exceed eight.  However, since the root
            # directory must always reside at level 1 by itself, this gives us
            # an effective maximum hierarchy depth of 7.
            raise PyIsoException("Directory levels too deep (maximum is 7)")
        # Now take the name off.
        name = splitpath.pop()
        if len(splitpath) == 0:
            # This is a new directory under the root, add it there
            parent = self.pvd.root_directory_record()
        else:
            parent,index = self._find_record('/' + '/'.join(splitpath))

        return (name, parent)

########################### PUBLIC API #####################################
    def __init__(self):
        self._initialize()

    def new(self, interchange_level=1, sys_ident="", vol_ident="", set_size=1,
            seqnum=1, log_block_size=2048, vol_set_ident="", pub_ident=None,
            preparer_ident=None, app_ident=None, copyright_file="",
            abstract_file="", bibli_file="", vol_expire_date=None, app_use=""):
        if self.initialized:
            raise PyIsoException("This object already has an ISO; either close it or create a new object")

        if interchange_level < 1 or interchange_level > 3:
            raise PyIsoException("Invalid interchange level (must be between 1 and 3)")

        self.interchange_level = interchange_level

        # First create the new PVD.
        if pub_ident is None:
            pub_ident = FileOrTextIdentifier()
            pub_ident.new("", False)
        if preparer_ident is None:
            preparer_ident = FileOrTextIdentifier()
            preparer_ident.new("", False)
        if app_ident is None:
            app_ident = FileOrTextIdentifier()
            app_ident.new("PyIso (C) 2015 Chris Lalancette", False)

        self.pvd = PrimaryVolumeDescriptor()
        self.pvd.new(sys_ident, vol_ident, set_size, seqnum, log_block_size,
                     vol_set_ident, pub_ident, preparer_ident, app_ident,
                     copyright_file, abstract_file, bibli_file,
                     vol_expire_date, app_use)

        # Now that we have the PVD, make the root path table record.
        ptr = PathTableRecord()
        ptr.new_root(self.pvd.root_directory_record())
        self.path_table_records.append(ptr)

        # Also make the volume descriptor set terminator.
        vdst = VolumeDescriptorSetTerminator()
        vdst.new()
        self.vdsts = [vdst]

        # Finally, make the directory entries for dot and dotdot.
        dot = DirectoryRecord()
        dot.new_dot(self.pvd.root_directory_record(),
                    self.pvd.sequence_number(), self.pvd)

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(self.pvd.root_directory_record(),
                          self.pvd.sequence_number(), self.pvd)

        self.pvd.reshuffle_extents()

        self.initialized = True

    def open(self, fp):
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

        self.path_table_records = []
        # Now that we have the PVD, parse the Path Tables according to Ecma-119
        # section 9.4.
        # Little Endian first
        self._parse_path_table(self.pvd.path_table_location_le,
                               self._little_endian_path_table)

        self.path_table_records[0].set_dirrecord(self.pvd.root_directory_record())

        # Big Endian next.
        self._parse_path_table(self.pvd.path_table_location_be,
                               self._big_endian_path_table)

        # OK, so now that we have the PVD, we start at its root directory
        # record and find all of the files
        self.interchange_level = self._walk_iso9660_directories()

        self.initialized = True

    def print_tree(self):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")
        print("%s (extent %d)" % (self.pvd.root_directory_record().file_identifier(), self.pvd.root_directory_record().extent_location()))
        dirs = [(self.pvd.root_directory_record(), "/")]
        while dirs:
            curr,path = dirs.pop(0)
            for child in curr.children:
                if child.is_dot() or child.is_dotdot():
                    continue

            print("%s%s (extent %d)" % (path, child.file_identifier(), child.extent_location()))
            if child.is_dir():
                dirs.append((child, "%s%s/" % (path, child.file_identifier())))

    def get_and_write(self, iso_path, outfp, blocksize=8192):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record,index = self._find_record(iso_path)

        data_fp,data_length = found_record.open_data(self.pvd.logical_block_size())

        copy_data(data_length, blocksize, data_fp, outfp)

    def write(self, outfp):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        # Before we do anything here, we need to make sure that the files
        # for the PVD and SVD(s) publisher, data preparer, and application
        # fields exist (if they were specified as files).
        self._check_ident(self.pvd.publisher_identifier,
                          "Primary Volume Descriptor Publisher Identifier")
        self._check_ident(self.pvd.preparer_identifier,
                          "Primary Volume Descriptor Data Preparer Identifier")
        self._check_ident(self.pvd.application_identifier,
                          "Primary Volume Descriptor Application Identifier")

        for svd in self.svds:
            self._check_ident(svd.publisher_identifier,
                              "Supplementary Volume Descriptor Publisher Identifier")
            self._check_ident(svd.preparer_identifier,
                              "Supplementary Volume Descriptor Data Preparer Identifier")
            self._check_ident(svd.application_identifier,
                              "Supplementary Volume Descriptor Application Identifier")

        outfp.seek(0)

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.  Thus
        # we skip the first 16 sectors.
        outfp.seek(16 * self.pvd.logical_block_size())

        # First write out the PVD.
        outfp.write(self.pvd.record())

        # Next we write out the Volume Descriptor Terminators.
        for vdst in self.vdsts:
            outfp.write(vdst.record())

        # Next we write out the version block.
        # FIXME: In genisoimage, write.c:vers_write(), this "version descriptor"
        # is written out with the exact command line used to create the ISO
        # (if in debug mode, otherwise it is all zero).  However, there is no
        # mention of this in any of the specifications I've read so far.  Where
        # does it come from?
        outfp.write("\x00" * 2048)

        # Next we write out the Path Table Records, both in Little Endian and
        # Big-Endian formats.  We do this within the same loop, seeking back
        # and forth as necessary.
        le_offset = 0
        be_offset = 0
        for record in self.path_table_records:
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

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        dirs = [self.pvd.root_directory_record()]
        while dirs:
            curr = dirs.pop(0)
            curr_dirrecord_offset = 0
            for child in curr.children:
                # Now matter what type the child is, we need to first write out
                # the directory record entry.
                dir_extent = child.parent.extent_location()

                outfp.seek(dir_extent * self.pvd.logical_block_size() + curr_dirrecord_offset)
                # Now write out the child
                recstr = child.record()
                outfp.write(recstr)
                curr_dirrecord_offset += len(recstr)

                if child.is_dir():
                    # If the child is a directory, and is not dot or dotdot, we
                    # want to descend into it to look at the children.
                    if not child.is_dot() and not child.is_dotdot():
                        dirs.append(child)
                    outfp.write(pad(outfp.tell(), self.pvd.logical_block_size()))
                else:
                    # If the child is a file, then we need to write the data to
                    # the output file.
                    data_fp,data_length = child.open_data(self.pvd.logical_block_size())
                    outfp.seek(child.extent_location() * self.pvd.logical_block_size())
                    copy_data(data_length, 8192, data_fp, outfp)
                    outfp.write(pad(data_length, self.pvd.logical_block_size()))

    def add_fp(self, fp, length, iso_path):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        check_iso9660_filename(name, self.interchange_level)

        rec = DirectoryRecord()
        rec.new_fp(fp, length, name, parent, self.pvd.sequence_number(), self.pvd)

        self.pvd.reshuffle_extents()

        self.pvd.add_to_space_size(length)

        # After we've reshuffled the extents, we have to run through the list
        # of path table records and reset their extents appropriately.
        for ptr in self.path_table_records:
            ptr.update_extent_location_from_dirrecord()

    def add_directory(self, iso_path):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        check_iso9660_directory(name, self.interchange_level)

        rec = DirectoryRecord()
        rec.new_dir(name, parent, self.pvd.sequence_number(), self.pvd)

        dot = DirectoryRecord()
        dot.new_dot(rec, self.pvd.sequence_number(), self.pvd)

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(rec, self.pvd.sequence_number(), self.pvd)

        self.pvd.reshuffle_extents()

        # We always need to add an entry to the path table record
        ptr = PathTableRecord()
        ptr.new_dir(name, rec)

        # We keep the list of children in sorted order, based on the __lt__
        # method of the PathTableRecord object.
        bisect.insort_left(self.path_table_records, ptr)

        self.pvd.add_to_ptr_size(ptr.record_length(len(name)))

        # A new directory will take up at least one extent, so start with that
        # here.
        self.pvd.add_to_space_size(self.pvd.logical_block_size())

    def rm_file(self, iso_path):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path[0] != '/':
            raise PyIsoException("Must be a path starting with /")

        child,index = self._find_record(iso_path)

        if not child.is_file():
            raise PyIsoException("Cannot remove a directory with rm_file (try rm_directory instead(")

        self.pvd.remove_from_space_size(child.file_length())

        child.parent.remove_child(child, index, self.pvd)

        self.pvd.reshuffle_extents()

        # After we've reshuffled the extents, we have to run through the list
        # of path table records and reset their extents appropriately.
        for ptr in self.path_table_records:
            ptr.update_extent_location_from_dirrecord()

    def rm_directory(self, iso_path):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path == '/':
            raise PyIsoException("Cannot remove base directory")

        child,index = self._find_record(iso_path)

        if not child.is_dir():
            raise PyIsoException("Cannot remove a file with rm_directory (try rm_file instead)")

        for c in child.children:
            if c.is_dot() or c.is_dotdot():
                continue
            raise PyIsoException("Directory must be empty to use rm_directory")

        # This is equivalent to bisect.bisect_left() (and in fact the code is
        # modified from there).  However, we already overrode the __lt__ method
        # in PathTableRecord(), and we wanted our own comparison between two
        # strings, so we open-code it here.
        lo = 0
        hi = len(self.path_table_records)
        while lo < hi:
            mid = (lo + hi) // 2
            if ptr_lt(self.path_table_records[mid].directory_identifier, child.file_ident):
                lo = mid + 1
            else:
                hi = mid
        saved_ptr_index = lo

        if saved_ptr_index == -1:
            raise PyIsoException("Could not find path table record!")

        ptr = self.path_table_records[saved_ptr_index]

        self.pvd.remove_from_space_size(child.file_length())

        self.pvd.remove_from_ptr_size(ptr.record_length(ptr.len_di))

        del self.path_table_records[saved_ptr_index]

        child.parent.remove_child(child, index, self.pvd)

        self.pvd.reshuffle_extents()

        # After we've reshuffled the extents, we have to run through the list
        # of path table records and reset their extents appropriately.
        import binascii
        for ptr in self.path_table_records:
            ptr.update_extent_location_from_dirrecord()

    def set_sequence_number(self, seqnum):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        self.pvd.set_sequence_number(seqnum)

        # FIXME: if this changes, we need to propagate it to all of the
        # Directory Record entries

    def set_set_size(self, set_size):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        self.pvd.set_set_size(set_size)

    # FIXME: we might need an API call to manipulate permission bits on
    # individual files.

    def close(self):
        if not self.initialized:
            raise PyIsoException("This object is not yet initialized; call either open() or new() to create an ISO")

        # now that we are closed, re-initialize everything
        self._initialize()
