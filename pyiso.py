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

class VolumeDescriptorDate(object):
    # Ecma-119, 8.4.26.1 specifies the date format as:
    # 2015042412182211\xf0 (offset from GMT in 15min intervals, -16 for us)
    def __init__(self):
        self.initialized = False
        self.time_fmt = "%Y%m%d%H%M%S"

    def parse(self, datestr):
        if self.initialized:
            raise Exception("This Volume Descriptor Date object is already initialized")

        self.initialized = True
        self.year = 0
        self.month = 0
        self.dayofmonth = 0
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.hundredthsofsecond = 0
        self.gmtoffset = 0
        self.present = False
        self.date_str = datestr
        if len(datestr) != 17:
            raise Exception("Invalid ISO9660 date string")
        if datestr[:-1] == '0'*16 and datestr[-1] == '\x00':
            # if the string was all zero, it means it wasn't specified; this
            # is valid, but we can't do any further work, so just bail out of
            # here
            return
        self.present = True
        timestruct = time.strptime(datestr[:-3], self.time_fmt)
        self.year = timestruct.tm_year
        self.month = timestruct.tm_mon
        self.dayofmonth = timestruct.tm_mday
        self.hour = timestruct.tm_hour
        self.minute = timestruct.tm_min
        self.second = timestruct.tm_sec
        self.hundredthsofsecond = int(datestr[14:15])
        self.gmtoffset = struct.unpack("=b", datestr[16])

    def date_string(self):
        if not self.initialized:
            raise Exception("This Volume Descriptor Date is not yet initialized")

        return self.date_str

    def new(self, tm):
        if self.initialized:
            raise Exception("This Volume Descriptor Date object is already initialized")

        # We are expecting a struct_time structure as input, or None.  If it
        # is None, then this particular time field doesn't exist and we set
        # everything to zero.  Otherwise, we set the fields from the
        # struct_time structure passed in.

        self.initialized = True

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
            self.date_str = time.strftime(self.time_fmt, local)
            self.date_str += struct.pack("=H", self.hundredthsofsecond)
            self.date_str += struct.pack("=b", self.gmtoffset)
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
            self.date_str = '0'*16 + '\x00'
            self.present = False

    def __str__(self):
        if not self.initialized:
            raise Exception("This Volume Descriptor Date is not yet initialized")
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
    def __init__(self):
        self.initialized = False

    def parse(self, ident_str):
        if self.initialized:
            raise Exception("This File or Text identifier is already initialized")
        self.text = ident_str
        # According to Ecma-119, 8.4.20, 8.4.21, and 8.4.22, if the first
        # byte is a 0x5f, then the rest of the field specifies a filename.
        # It is not specified, but presumably if it is not a filename, then it
        # is an arbitrary text string.
        self.isfile = False
        if ident_str[0] == "\x5f":
            # If it is a file, Ecma-119 says that it must be at the Root
            # directory and it must be 8.3 (so 12 byte, plus one for the 0x5f)
            if len(ident_str) > 13:
                raise Exception("Filename for identifier is not in 8.3 format!")
            self.isfile = True
            self.text = ident_str[1:]

        self.initialized = True

    def new(self, text, isfile):
        if self.initialized:
            raise Exception("This File or Text identifier is already initialized")
        maxlength = 128
        if isfile:
            maxlength = 127
        if len(text) > maxlength:
            raise Exception("Length of text must be <= %d" % maxlength)

        self.initialized = True
        self.isfile = isfile
        self.text = "{0:{1}s}".format(text, maxlength)

    def is_file(self):
        if not self.initialized:
            raise Exception("This File or Text identifier is not yet initialized")
        return self.isfile

    def is_text(self):
        if not self.initialized:
            raise Exception("This File or Text identifier is not yet initialized")
        return not self.isfile

    def __str__(self):
        if not self.initialized:
            raise Exception("This File or Text identifier is not yet initialized")
        fileortext = "Text"
        if self.isfile:
            fileortext = "File"
        return "%s (%s)" % (self.text, fileortext)

    def identification_string(self):
        if not self.initialized:
            raise Exception("This File or Text identifier is not yet initialized")
        if self.isfile:
            return "\x5f" + self.text
        # implicitly a text identifier
        return self.text

class DirectoryRecordDate(object):
    def __init__(self):
        self.initialized = False

    def parse(self, years_since_1900, month, day_of_month, hour,
                    minute, second, gmtoffset):
        if self.initialized:
            raise Exception("Directory Record Date already initialized")

        self.initialized = True
        self.years_since_1900 = years_since_1900
        self.month = month
        self.day_of_month = day_of_month
        self.hour = hour
        self.minute = minute
        self.second = second
        self.gmtoffset = gmtoffset

    def new(self):
        if self.initialized:
            raise Exception("Directory Record Date already initialized")

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

class DirectoryRecord(object):
    FILE_FLAG_EXISTENCE_BIT = 0
    FILE_FLAG_DIRECTORY_BIT = 1
    FILE_FLAG_ASSOCIATED_FILE_BIT = 2
    FILE_FLAG_RECORD_BIT = 3
    FILE_FLAG_PROTECTION_BIT = 4
    FILE_FLAG_MULTI_EXTENT_BIT = 7

    DATA_ON_ORIGINAL_ISO = 1
    DATA_IN_MEMORY = 2
    DATA_IN_EXTERNAL_FILE = 3
    DATA_IN_EXTERNAL_FP = 4

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
        self.fmt = "=BBLLLLBBBBBBbBBBHHB"

    def parse(self, record, is_root):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        if len(record) > 255:
            # Since the length is supposed to be 8 bits, this should never
            # happen
            raise Exception("Directory record longer than 255 bytes!")

        (self.dr_len, self.xattr_len, extent_location_le, extent_location_be,
         data_length_le, data_length_be, years_since_1900, month, day_of_month,
         hour, minute, second, gmtoffset, self.file_flags, self.file_unit_size,
         self.interleave_gap_size, seqnum_le, seqnum_be,
         self.len_fi) = struct.unpack(self.fmt, record[:33])

        if len(record) != self.dr_len:
            # The record we were passed doesn't have the same information in it
            # as the directory entry thinks it should
            raise Exception("Length of directory entry doesn't match internal check")

        if extent_location_le != swab_32bit(extent_location_be):
            raise Exception("Little-endian and big-endian extent location disagree")
        self.original_extent_loc = extent_location_le

        if data_length_le != swab_32bit(data_length_be):
            raise Exception("Little-endian and big-endian data length disagree")
        self.data_length = data_length_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise Exception("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        self.date = DirectoryRecordDate()
        self.date.parse(years_since_1900, month, day_of_month, hour,
                              minute, second, gmtoffset)

        # OK, we've unpacked what we can from the beginning of the string.  Now
        # we have to use the len_fi to get the rest

        self.children = []
        self.is_root = is_root
        self.isdir = False
        self.parent = None
        if self.is_root:
            # A root directory entry should always be exactly 34 bytes
            if self.dr_len != 34:
                raise Exception("Root directory entry of invalid length!")
            # A root directory entry should always have 0 as the identifier
            if record[33] != '\x00':
                raise Exception("Invalid root directory entry identifier")
            self.file_ident = record[33]
            self.isdir = True
        else:
            self.file_ident = record[33:33 + self.len_fi]
            if self.file_flags & (1 << self.FILE_FLAG_DIRECTORY_BIT):
                self.isdir = True

        if self.xattr_len != 0:
            if self.file_flags & (1 << self.FILE_FLAG_RECORD_BIT):
                raise Exception("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise Exception("Protection Bit not allowed with Extended Attributes")

        self.original_data_location = self.DATA_ON_ORIGINAL_ISO
        self.initialized = True

    def _new(self, mangledname, parent, seqnum, isdir):
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

        self.file_ident = mangledname

        self.isdir = isdir

        self.parent = parent
        if parent is None:
            # If no parent, then this is the root
            self.is_root = True
            self.isdir = True
        else:
            self.is_root = False
            self.parent.add_child(self)

        self.seqnum = seqnum
        # For a new directory record entry, there is no original_extent_loc,
        # so we leave it at None.
        self.original_extent_loc = None
        self.len_fi = len(self.file_ident)
        self.dr_len = struct.calcsize(self.fmt) + self.len_fi
        if self.dr_len % 2 != 0:
            self.dr_len += 1

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
        # FIXME: for now, we just assume that this is a file that exists,
        # is a file, is not associated, does not have additional record,
        # has now owner and group, and is not multi-extent (so 0 for all of
        # the bits).  We probably want to allow these in the future.
        self.file_flags = 0
        if self.isdir:
            self.file_flags |= (1 << self.FILE_FLAG_DIRECTORY_BIT)
        self.file_unit_size = 0 # FIXME: we don't support setting file unit size for now
        self.interleave_gap_size = 0 # FIXME: we don't support setting interleave gap size for now
        self.xattr_len = 0 # FIXME: we don't support xattrs for now
        self.children = []
        self.initialized = True

    def new_file(self, orig_filename, isoname, parent, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = os.stat(orig_filename).st_size
        self.original_data_location = self.DATA_IN_EXTERNAL_FILE
        self.original_filename = orig_filename
        self._new(iso9660mangle(isoname), parent, seqnum, False)

    def new_data(self, data, isoname, parent, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data = data
        self.data_length = len(data)
        self.original_data_location = self.DATA_IN_MEMORY
        self._new(iso9660mangle(isoname), parent, seqnum, False)

    def new_fp(self, fp, isoname, parent, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = os.fstat(fp.fileno()).st_size
        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.fp = fp
        self._new(iso9660mangle(isoname), parent, seqnum, False)

    def new_root(self, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = 2048 # FIXME: why is this 2048?
        self.original_data_location = self.DATA_IN_MEMORY
        self._new('\x00', None, seqnum, True)

    def new_dot(self, root, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = 2048 # FIXME: why is this 2048?
        self.original_data_location = self.DATA_IN_MEMORY
        self._new('\x00', root, seqnum, True)

    def new_dotdot(self, root, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = 2048 # FIXME: why is this 2048?
        self.original_data_location = self.DATA_IN_MEMORY
        self._new('\x01', root, seqnum, True)

    def new_dir(self, name, parent, seqnum):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.data_length = 2048 # FIXME: why is this 2048?
        self.original_data_location = self.DATA_IN_MEMORY
        self._new(name, parent, seqnum, True)

    def add_child(self, child):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        child.parent = self
        self.children.append(child)

    def is_dir(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.isdir

    def is_file(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return not self.isdir

    def is_dot(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident == '\x00'

    def is_dotdot(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident == '\x01'

    def original_extent_location(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.original_extent_loc

    def file_identifier(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        if self.is_root:
            return '/'
        if self.file_ident == '\x00':
            return '.'
        if self.file_ident == '\x01':
            return '..'
        return self.file_ident

    def file_length(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.data_length

    def record(self, new_extent_loc):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = DirectoryRecordDate()
        self.date.new()

        pad = ""
        if (struct.calcsize(self.fmt) + self.len_fi) % 2 != 0:
            pad = "\x00"

        return struct.pack(self.fmt, self.dr_len, self.xattr_len,
                           new_extent_loc, swab_32bit(new_extent_loc),
                           self.data_length, swab_32bit(self.data_length),
                           self.date.years_since_1900, self.date.month,
                           self.date.day_of_month, self.date.hour,
                           self.date.minute, self.date.second,
                           self.date.gmtoffset, self.file_flags,
                           self.file_unit_size, self.interleave_gap_size,
                           self.seqnum, swab_16bit(self.seqnum),
                           self.len_fi) + self.file_ident + pad

    def write_record(self, outfp, new_extent):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        record = self.record(new_extent)
        outfp.write(record)
        return len(record)

    def write_data(self, outfp, orig_iso_fp, logical_block_size):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        if self.isdir:
            # For a directory, there is no data to write out; just quit
            return

        if self.original_data_location == self.DATA_IN_MEMORY:
            # If the data is already in memory, we really don't have to
            # do anything smart.  Just write the data out to the ISO.
            outfp.write(self.data)
        else:
            # FIXME: it would probably be better to figure out this whole
            # datafp thing during initialization of the object, then just do
            # the seeking and reading as needed in here.
            if self.original_data_location == self.DATA_ON_ORIGINAL_ISO:
                orig_iso_fp.seek(self.original_extent_loc * logical_block_size)
                datafp = orig_iso_fp
            elif self.original_data_location == self.DATA_IN_EXTERNAL_FILE:
                datafp = open(self.original_filename, 'rb')
            elif self.original_data_location == self.DATA_IN_EXTERNAL_FP:
                datafp = self.fp

            left = self.data_length
            readsize = 8192
            while left > 0:
                if left < readsize:
                    readsize = left
                outfp.write(datafp.read(readsize))
                left -= readsize

            if self.original_data_location == self.DATA_IN_EXTERNAL_FILE:
                datafp.close()
        outfp.write(pad(self.data_length, 2048))

    def __str__(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
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

class PrimaryVolumeDescriptor(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sBB32s32sQLLQQQQHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def parse(self, vd):
        if self.initialized:
            raise Exception("This Primary Volume Descriptor is already initialized")

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
         space_size_le, space_size_be, unused3dot1, unused3dot2, unused3dot3,
         unused3dot4, set_size_le, set_size_be, seqnum_le, seqnum_be,
         logical_block_size_le, logical_block_size_be, path_table_size_le,
         path_table_size_be, self.path_table_location_le,
         self.optional_path_table_location_le, self.path_table_location_be,
         self.optional_path_table_location_be, root_dir_record,
         self.volume_set_identifier, pub_ident_str, prepare_ident_str,
         app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, unused5) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.4.1, the primary volume descriptor type
        # should be 1
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_PRIMARY:
            raise Exception("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001"
        if self.identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        # According to Ecma-119, 8.4.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.4, the first unused field should be 0
        if unused1 != 0:
            raise Exception("data in unused field not zero")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0
        if unused2 != 0:
            raise Exception("data in 2nd unused field not zero")
        # According to Ecma-119, 8.4.9, the third unused field should be all 0
        if unused3dot1 != 0 or unused3dot2 != 0 or unused3dot3 != 0 or unused3dot4 != 0:
            raise Exception("data in 3rd unused field not zero")
        if self.file_structure_version != 1:
            raise Exception("File structure version expected to be 1")
        if unused4 != 0:
            raise Exception("data in 4th unused field not zero")
        if unused5 != '\x00'*653:
            raise Exception("data in 5th unused field not zero")

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other
        if space_size_le != swab_32bit(space_size_be):
            raise Exception("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != swab_16bit(set_size_be):
            raise Exception("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise Exception("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != swab_16bit(logical_block_size_be):
            raise Exception("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != swab_32bit(path_table_size_be):
            raise Exception("Little-endian and big-endian path table size disagree")
        self.path_tbl_size = path_table_size_le

        if self.file_structure_version != 1:
            raise Exception("File structure version was not 1")

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.parse(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.parse(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.parse(app_ident_str)
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, True)

        self.initialized = True

    def new(self, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            vol_effective_date, app_use):
        if self.initialized:
            raise Exception("This Primary Volume Descriptor is already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_PRIMARY
        self.identifier = "CD001"
        self.version = 1

        if len(sys_ident) > 32:
            raise Exception("The system identifer has a maximum length of 32")
        self.system_identifier = "{:<32}".format(sys_ident)

        if len(vol_ident) > 32:
            raise Exception("The volume identifier has a maximum length of 32")
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
            raise Exception("Sequence number must be less than or equal to set size")
        self.seqnum = seqnum
        self.log_block_size = log_block_size
        # The path table size is in bytes, and is always at least 10 bytes
        # (for the root directory record).
        self.path_tbl_size = 10
        # By default the Little Endian Path Table record starts at extent 19
        # (right after the Volume Terminator).
        self.path_table_location_le = 19*self.log_block_size
        # By default the Big Endian Path Table record starts at extent 21
        # (two extents after the Little Endian Path Table Record).
        self.path_table_location_be = 21*self.log_block_size
        # FIXME: we don't support the optional path table location right now
        self.optional_path_table_location_le = 0
        self.optional_path_table_location_be = 0
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.new_root(1)

        if len(vol_set_ident) > 128:
            raise Exception("The maximum length for the volume set identifier is 128")
        self.volume_set_identifier = "{:<128}".format(vol_set_ident)

        self.publisher_identifier = FileOrTextIdentifier()
        # FIXME: allow the user to specify whether this is a file or a string
        self.publisher_identifier.new(pub_ident, False)

        self.preparer_identifier = FileOrTextIdentifier()
        # FIXME: allow the user to specify whether this is a file or a string
        self.preparer_identifier.new(preparer_ident, False)

        self.application_identifier = FileOrTextIdentifier()
        # FIXME: allow the user to specify whether this is a file or a string
        self.application_identifier.new(app_ident, False)

        self.copyright_file_identifier = "{:<37}".format(copyright_file)
        self.abstract_file_identifier = "{:<37}".format(abstract_file)
        self.bibliographic_file_identifier = "{:<37}".format(bibli_file)

        # We make a valid volume creation and volume modification date here,
        # but they will get overwritten during writeout.
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.new(time.time())
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.new(time.time())
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.new(vol_expire_date)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.new(vol_effective_date)
        self.file_structure_version = 1

        if len(app_use) > 512:
            raise Exception("The maximum length for the application use is 512")
        self.application_use = app_use

        self.initialized = True

    def logical_block_size(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        return self.log_block_size

    def path_table_size(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        return self.path_tbl_size

    def root_directory_record(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def sequence_number(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        return self.seqnum

    def set_sequence_number(self, seqnum):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        if seqnum > self.set_size:
            raise Exception("Sequence number larger than volume set size")

        self.seqnum = seqnum

    def set_set_size(self, set_size):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        if set_size > (2**16 - 1):
            raise Exception("Set size too large to fit into 16-bit field")

        self.set_size = set_size

    def add_to_ptr_size(self, addition):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        self.path_tbl_size += addition

    def write(self, outfp, root_new_extent_loc, space_size_extent):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        vol_create_date = VolumeDescriptorDate()
        vol_create_date.new(time.time())

        vol_mod_date = VolumeDescriptorDate()
        vol_mod_date.new(time.time())

        outfp.write(struct.pack(self.fmt, self.descriptor_type,
                                self.identifier, self.version, 0,
                                self.system_identifier,
                                self.volume_identifier,
                                0, space_size_extent,
                                swab_32bit(space_size_extent), 0, 0, 0, 0,
                                self.set_size, swab_16bit(self.set_size),
                                self.seqnum, swab_16bit(self.seqnum),
                                self.log_block_size,
                                swab_16bit(self.log_block_size),
                                self.path_tbl_size,
                                swab_32bit(self.path_tbl_size),
                                self.path_table_location_le,
                                self.optional_path_table_location_le,
                                swab_32bit(self.path_table_location_be),
                                self.optional_path_table_location_be,
                                self.root_dir_record.record(root_new_extent_loc),
                                self.volume_set_identifier,
                                self.publisher_identifier.identification_string(),
                                self.preparer_identifier.identification_string(),
                                self.application_identifier.identification_string(),
                                self.copyright_file_identifier,
                                self.abstract_file_identifier,
                                self.bibliographic_file_identifier,
                                vol_create_date.date_string(),
                                vol_mod_date.date_string(),
                                self.volume_expiration_date.date_string(),
                                self.volume_effective_date.date_string(),
                                self.file_structure_version, 0,
                                "{:<512}".format(self.application_use),
                                "\x00" * 653))

    def __str__(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

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
            raise Exception("Volume Descriptor Set Terminator already initialized")

        (self.descriptor_type, self.identifier, self.version,
         unused) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.3.1, the volume descriptor set terminator
        # type should be 255
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.3.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.3.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")
        # According to Ecma-119, 8.3.4, the rest of the terminator should be 0
        if unused != '\x00'*2041:
            raise Exception("Invalid unused field")
        self.initialized = True

    def new(self):
        if self.initialized:
            raise Exception("Volume Descriptor Set Terminator already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR
        self.identifier = "CD001"
        self.version = 1
        self.initialized = True

    def write(self, outfp):
        if not self.initialized:
            raise Exception("Volume Descriptor Set Terminator not yet initialized")
        outfp.write(struct.pack(self.fmt, self.descriptor_type,
                                self.identifier, self.version, "\x00" * 2041))

class BootRecord(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=B5sB32s32s1977s"

    def parse(self, vd):
        if self.initialized:
            raise Exception("Boot Record already initialized")

        (self.descriptor_type, self.identifier, self.version,
         self.boot_system_identifier, self.boot_identifier,
         self.boot_system_use) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.2.1, the boot record type should be 0
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.2.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.2.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")
        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise Exception("Boot Record not yet initialized")

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

    def parse(self, vd):
        if self.initialized:
            raise Exception("Supplementary Volume Descriptor already initialized")

        (self.descriptor_type, self.identifier, self.version, self.flags,
         self.system_identifier, self.volume_identifier, unused2,
         space_size_le, space_size_be, self.escape_sequences, set_size_le,
         set_size_be, seqnum_le, seqnum_be, logical_block_size_le,
         logical_block_size_be, path_table_size_le, path_table_size_be,
         self.path_table_location_le, self.optional_path_table_location_le,
         self.path_table_location_be, self.optional_path_table_location_be,
         root_dir_record, self.volume_set_identifier, pub_ident_str,
         prepare_ident_str, app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, unused5) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.5.1, the primary volume descriptor type
        # should be 2
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
            raise Exception("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001"
        if self.identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        # According to Ecma-119, 8.5.2, the version should be 1
        if self.version != 1:
            raise Exception("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0
        if unused2 != 0:
            raise Exception("data in 2nd unused field not zero")
        if self.file_structure_version != 1:
            raise Exception("File structure version expected to be 1")
        if unused4 != 0:
            raise Exception("data in 4th unused field not zero")
        if unused5 != '\x00'*653:
            raise Exception("data in 5th unused field not zero")

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other
        if space_size_le != swab_32bit(space_size_be):
            raise Exception("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != swab_16bit(set_size_be):
            raise Exception("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise Exception("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != swab_16bit(logical_block_size_be):
            raise Exception("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != swab_32bit(path_table_size_be):
            raise Exception("Little-endian and big-endian path table size disagree")
        self.path_table_size = path_table_size_le

        self.publisher_identifier = FileOrTextIdentifier(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier(app_ident_str)
        self.volume_creation_date = VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_directory_record = DirectoryRecord()
        self.root_directory_record.parse(root_dir_record, True)

        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise Exception("Supplementary Volume Descriptor not initialized")

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
            raise Exception("Volume Partition already initialized")

        (self.descriptor_type, self.identifier, self.version, unused,
         self.system_identifier, self.volume_partition_identifier,
         volume_partition_location_le, volume_partition_location_be,
         volume_partition_size_le, volume_partition_size_be,
         self.system_use) = struct.unpack(self.fmt, vd)

        # According to Ecma-119, 8.6.1, the volume partition type should be 3
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
            raise Exception("Invalid descriptor type")
        # According to Ecma-119, 8.6.2, the identifier should be "CD001"
        if self.identifier != 'CD001':
            raise Exception("Invalid identifier")
        # According to Ecma-119, 8.6.3, the version should be 1
        if self.version != 1:
            raise Exception("Invalid version")
        # According to Ecma-119, 8.6.4, the unused field should be 0
        if unused != 0:
            raise Exception("Unused field should be zero")

        if volume_partition_location_le != swab_32bit(volume_partition_location_be):
            raise Exception("Little-endian and big-endian volume partition location disagree")
        self.volume_partition_location = volume_partition_location_le

        if volume_partition_size_le != swab_32bit(volume_partition_size_be):
            raise Exception("Little-endian and big-endian volume partition size disagree")
        self.volume_partition_size = volume_partition_size_le

        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise Exception("Volume Partition not initialized")

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
            raise Exception("Extended Attribute Record already initialized")

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
            raise Exception("Little-endian and big-endian owner identification disagree")
        self.owner_identification = owner_identification_le

        if group_identification_le != swab_16bit(group_identification_be):
            raise Exception("Little-endian and big-endian group identification disagree")
        self.group_identification = group_identification_le

        if record_length_le != swab_16bit(record_length_be):
            raise Exception("Little-endian and big-endian record length disagree")
        self.record_length = record_length_le

        if len_au_le != swab_16bit(len_au_be):
            raise Exception("Little-endian and big-endian record length disagree")
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
            raise Exception("Path Table Record already initialized")

        (self.len_di, self.xattr_length, self.extent_location,
         self.parent_directory_num) = struct.unpack(self.fmt, data[:8])

        if self.len_di % 2 != 0:
            self.directory_identifier = data[8:-1]
        else:
            self.directory_identifier = data[8:]
        self.initialized = True

    def _record(self, ext_loc, parent_dir_num):
        ret = struct.pack(self.fmt, self.len_di, self.xattr_length,
                          ext_loc, parent_dir_num)
        ret += self.directory_identifier
        len_pad = 0
        if self.len_di % 2 != 0:
            ret += "\x00"
            len_pad = 1

        return ret,struct.calcsize(self.fmt) + self.len_di + len_pad

    def record_little_endian(self, extent):
        if not self.initialized:
            raise Exception("Path Table Record not yet initialized")

        return self._record(extent, self.parent_directory_num)

    def record_big_endian(self, extent):
        if not self.initialized:
            raise Exception("Path Table Record not yet initialized")

        return self._record(swab_32bit(extent),
                            swab_16bit(self.parent_directory_num))

    def read_length(self, len_di):
        # This method can be called even if the object isn't initialized
        return struct.calcsize(self.fmt) + len_di + (len_di % 2)

    def _new(self, name):
        self.len_di = len(name)
        self.xattr_length = 0 # FIXME: we don't support xattr for now
        self.extent_location = 0 # FIXME: fix this
        self.parent_directory_num = 1 # FIXME: fix this
        self.directory_identifier = name
        self.initialized = True

    def new_root(self):
        if self.initialized:
            raise Exception("Path Table Record already initialized")

        self._new("\x00")

    def new_dir(self, name):
        if self.initialized:
            raise Exception("Path Table Record already initialized")

        self._new(name)

class File(object):
    """
    Objects of this class represent files on the ISO that we deal with through
    the external API.  These are converted to and from ISO9660 DirectoryRecord
    classes as necessary.
    """
    def __init__(self, dir_record):
        # strip off the version from the file identifier
        self.name = dir_record.file_identifier()[:-2]

    def __str__(self):
        return self.name

class Directory(object):
    """
    Objects of this class represent directories on the ISO that we deal with
    through the external API.  These are converted to and from ISO9660
    DirectoryRecord classes as necessary.
    """
    def __init__(self, dir_record):
        # strip off the version from the file identifier
        self.name = dir_record.file_identifier()

    def __str__(self):
        return self.name

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

def iso9660mangle(name):
    # ISO9660 ends up mangling names quite a bit.  First of all, they must
    # fit into 8.3.  Second, they *must* have a dot.  Third, they all have
    # a semicolon number attached to the end.  Here we mangle a name
    # according to ISO9660.
    ret = name
    if ret.rfind('.') == -1:
        ret += "."
    return ret.upper() + ";1"

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
        self.cdfd.seek(16 * 2048)
        done = False
        while not done:
            # All volume descriptors are exactly 2048 bytes long
            vd = self.cdfd.read(2048)
            (desc_type,) = struct.unpack("=B", vd[0])
            if desc_type == VOLUME_DESCRIPTOR_TYPE_PRIMARY:
                pvd = PrimaryVolumeDescriptor()
                pvd.parse(vd)
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
                svd.parse(vd)
                svds.append(svd)
            elif desc_type == VOLUME_DESCRIPTOR_TYPE_VOLUME_PARTITION:
                vpd = VolumePartition()
                vpd.parse(vd)
                vpds.append(vpd)
        return pvds, svds, vpds, brs, vdsts

    def _seek_to_extent(self, extent):
        self.cdfd.seek(extent * self.pvd.logical_block_size())

    def _walk_directories(self):
        dirs = [self.pvd.root_directory_record()]
        while dirs:
            dir_record = dirs.pop(0)
            self._seek_to_extent(dir_record.original_extent_location())
            while True:
                # read the length byte for the directory record
                (lenbyte,) = struct.unpack("=B", self.cdfd.read(1))
                if lenbyte == 0:
                    # if we saw 0 len, we are finished with this extent
                    break
                new_record = DirectoryRecord()
                new_record.parse(struct.pack("=B", lenbyte) + self.cdfd.read(lenbyte - 1), False)
                if new_record.is_dir() and not new_record.is_dot() and not new_record.is_dotdot():
                    dirs += [new_record]
                dir_record.add_child(new_record)

    def _initialize(self):
        self.cdfd = None
        self.opened_fd = False
        self.pvd = None
        self.svds = []
        self.vpds = []
        self.brs = []
        self.vdsts = []
        self.initialized = False
        self.path_table_records = []

    def __init__(self):
        self._initialize()

    def new(self, sys_ident="", vol_ident="", set_size=1, seqnum=1,
            log_block_size=2048, vol_set_ident="", pub_ident="",
            preparer_ident="", app_ident="PyIso (C) 2015 Chris Lalancette",
            copyright_file="", abstract_file="", bibli_file="",
            vol_expire_date=None, vol_effective_date=None, app_use=""):
        if self.initialized:
            raise Exception("This object already has an ISO; either close it or create a new object")
        self.pvd = PrimaryVolumeDescriptor()
        self.pvd.new(sys_ident, vol_ident, set_size, seqnum, log_block_size,
                     vol_set_ident, pub_ident, preparer_ident, app_ident,
                     copyright_file, abstract_file, bibli_file,
                     vol_expire_date, vol_effective_date, app_use)

        # Now that we have the PVD, make the root path table record
        ptr = PathTableRecord()
        ptr.new_root()
        self.path_table_records.append(ptr)

        # Also make the volume descriptor set terminator
        vdst = VolumeDescriptorSetTerminator()
        vdst.new()
        self.vdsts = [vdst]

        # Finally, make the directory entries for dot and dotdot
        dot = DirectoryRecord()
        dot.new_dot(self.pvd.root_directory_record(),
                    self.pvd.sequence_number())

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(self.pvd.root_directory_record(),
                          self.pvd.sequence_number())

        self.initialized = True

    def _parse_path_table(self, extent, callback):
        self._seek_to_extent(extent)
        left = self.pvd.path_table_size()
        while left > 0:
            ptr = PathTableRecord()
            (len_di,) = struct.unpack("=B", self.cdfd.read(1))
            read_len = ptr.read_length(len_di)
            # ptr.read_length() returns the length of the entire path table
            # record, but we've already read the len_di so read one less.
            ptr.parse(struct.pack("=B", len_di) + self.cdfd.read(read_len - 1))
            left -= read_len
            callback(ptr)

    def _little_endian_path_table(self, ptr):
        self.path_table_records.append(ptr)

    def _big_endian_path_table(self, ptr):
        if ptr.len_di != self.path_table_records[self.index].len_di or \
           ptr.xattr_length != self.path_table_records[self.index].xattr_length or \
           swab_32bit(ptr.extent_location) != self.path_table_records[self.index].extent_location or \
           swab_16bit(ptr.parent_directory_num) != self.path_table_records[self.index].parent_directory_num or \
           ptr.directory_identifier != self.path_table_records[self.index].directory_identifier:
            raise Exception("Little endian and big endian path table records do not agree")
        self.index += 1

    def _do_open(self):
        # Get the Primary Volume Descriptor (pvd), the set of Supplementary
        # Volume Descriptors (svds), the set of Volume Partition
        # Descriptors (vpds), the set of Boot Records (brs), and the set of
        # Volume Descriptor Set Terminators (vdsts)
        pvds, self.svds, self.vpds, self.brs, self.vdsts = self._parse_volume_descriptors()
        if len(pvds) != 1:
            raise Exception("Valid ISO9660 filesystems have one and only one Primary Volume Descriptors")
        if len(self.vdsts) < 1:
            raise Exception("Valid ISO9660 filesystems must have at least one Volume Descriptor Set Terminators")
        self.pvd = pvds[0]

        self.path_table_records = []
        # Now that we have the PVD, parse the Path Tables.
        # Section 9.4 (p. 43)
        # Little Endian first
        self._parse_path_table(self.pvd.path_table_location_le,
                               self._little_endian_path_table)

        self.index = 0

        self._parse_path_table(swab_32bit(self.pvd.path_table_location_be),
                               self._big_endian_path_table)

        # OK, so now that we have the PVD, we start at its root directory
        # record and find all of the files
        self._walk_directories()
        self.initialized = True

    def open_fd(self, fd):
        if self.initialized:
            raise Exception("This object already has an ISO; either close it or create a new object")

        self.cdfd = fd

        self._do_open()

    def open(self, filename):
        if self.initialized:
            raise Exception("This object already has an ISO; either close it or create a new object")
        self.cdfd = open(filename, "rb")
        self.opened_fd = True

        self._do_open()

    def print_tree(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")
        print("%s (extent %d)" % (self.pvd.root_directory_record().file_identifier(), self.pvd.root_directory_record().original_extent_location()))
        dirs = [(self.pvd.root_directory_record(), "/")]
        while dirs:
            curr,path = dirs.pop(0)
            for child in curr.children:
                if child.is_dot() or child.is_dotdot():
                    continue

            print("%s%s (extent %d)" % (path, child.file_identifier(), child.original_extent_location()))
            if child.is_dir():
                dirs.append((child, "%s%s/" % (path, child.file_identifier())))

    def _find_record(self, path):
        if path[0] != '/':
            raise Exception("Must be a path starting with /")

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

            if child.file_identifier() != currpath and child.file_identifier() != iso9660mangle(currpath):
                continue

            # FIXME: we should ensure that if this is a directory, the name is
            # *not* mangled and if it is a file, the name *is* mangled

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

        raise Exception("Could not find path")

    def list_files(self, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        record,index = self._find_record(iso_path)

        entries = []
        if record.is_file():
            entries.append(File(child))
        elif record.is_dir():
            for child in record.children:
                if child.is_dot() or child.is_dotdot():
                    continue

                if child.is_file():
                    entries.append(File(child))
                elif child.is_dir():
                    entries.append(Directory(child))
                else:
                    raise Exception("This should never happen")
        else:
            raise Exception("This should never happen")

        return entries

    def _find_record_and_seek(self, iso_path):
        found_record,index = self._find_record(iso_path)

        self._seek_to_extent(found_record.original_extent_location())

        return found_record

    def get_file(self, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record_and_seek(iso_path)

        return self.cdfd.read(found_record.file_length())

    def _write_fd_to_disk(self, found_record, outfp, blocksize):
        total = found_record.file_length()
        while total != 0:
            thisread = blocksize
            if total < thisread:
                thisread = total
            outfp.write(self.cdfd.read(thisread))
            total -= thisread

    def get_and_write_file(self, iso_path, outpath, overwrite=False,
                           blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        found_record = self._find_record_and_seek(iso_path)

        outfp = open(outpath, "wb")
        self._write_fd_to_disk(found_record, outfp, blocksize)
        outfp.close()

    def get_and_write_fd(self, iso_path, outfp, blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record_and_seek(iso_path)

        self._write_fd_to_disk(found_record, outfp, blocksize)

    def write(self, outpath, overwrite=False):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        # Here we open up the file and start writing.
        outfp = open(outpath, 'wb')

        # Ecma-119, 6.2.1 says that the Volume Space is divided into a System
        # Area and a Data Area, where the System Area is in logical sectors 0
        # to 15, and whose contents is not specified by the standard.  Thus
        # we skip the first 16 sectors.
        outfp.seek(16 * self.pvd.logical_block_size())

        # Nominally the first thing we write out is the PVD, which fits in one
        # 2048-byte block.  However, we don't yet know several key pieces of
        # information, so we skip it here and write it at the end instead.
        outfp.seek(2048, 1)

        # Next we write out the Volume Descriptor Terminators.
        for vdst in self.vdsts:
            vdst.write(outfp)
        outfp.write(pad(2048, 4096))

        # Next we write out the Path Table Records, both in Little Endian and
        # Big-Endian formats.  We do this within the same loop, seeking back
        # and forth as necessary.
        # To write out the path records we need to know the extent of the
        # directory record that each directory will start in.  The extent of
        # the first directory record is the start extent of the
        # Little Endian Path Table Record plus 2, plus 2 for the Big
        # Endian location.
        ptr_extent = self.pvd.path_table_location_le / self.pvd.logical_block_size() + 2 + 2
        le_offset = 0
        be_offset = 0
        for record in self.path_table_records:
            # FIXME: we are going to have to make the correct parent directory
            # number here.
            outfp.seek(self.pvd.path_table_location_le + le_offset)
            ret,length = record.record_little_endian(ptr_extent)
            outfp.write(ret)
            le_offset += length

            outfp.seek(self.pvd.path_table_location_be + be_offset)
            ret,length = record.record_big_endian(ptr_extent)
            outfp.write(ret)
            be_offset += length
            ptr_extent += 1
        # Once we are finished with the loop, we need to pad out the Big
        # Endian version.  The Little Endian one was already properly padded
        # by the mere fact that we wrote things for the Big Endian version
        # in the right place.
        outfp.write(pad(be_offset, 4096))

        # In order in the final ISO, the directory records are next.  However,
        # we don't necessarily know all of the extent locations for the
        # children at this point, so we save a pointer and during the main
        # loop below we'll write out the extents.
        dirrecords_extent = outfp.tell() / self.pvd.logical_block_size()

        # Each directory entry has its own extent (of the logical block size).
        # Luckily we have a list of the extents from the path table records,
        # so we can just seek forward by that much.
        length = len(self.path_table_records) * self.pvd.logical_block_size()
        outfp.write("\x00" * length)

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        dirs = [(self.pvd.root_directory_record(), dirrecords_extent, None)]
        next_dirrecord_extent = dirrecords_extent + 1
        while dirs:
            curr,curr_dirrecord_extent,parent_dirrecord_extent = dirs.pop(0)
            curr_dirrecord_offset = 0
            sorted_children = sorted(curr.children,
                                     key=lambda child: child.file_identifier())
            for child in sorted_children:
                if child.is_dir():
                    # If the child is a directory, there are 3 cases we have
                    # to deal with:
                    # 1.  The directory is the '.' one.  In that case we want
                    #     to write the directory record directory with the
                    #     extent of the parent, and do nothing more.
                    # 2.  The directory is the '..' one.  In that case we want
                    #     to write the directory record directory with the
                    #     extent of the parent, and do nothing more.
                    # 3.  The directory is a regular directory.  In that case
                    #     we want to increment the directory location to the
                    #     next free extent past the parent, set the child
                    #     extent to that extent, write the directory record
                    #     with the correct extent into the parent directory
                    #     record, and append this directory to the list of
                    #     dirs to descend into.

                    # First save off our location and seek to the right place.
                    orig_loc = outfp.tell()
                    outfp.seek((curr_dirrecord_extent * self.pvd.logical_block_size()) + curr_dirrecord_offset)
                    if child.is_dot():
                        length = child.write_record(outfp, curr_dirrecord_extent)
                    elif child.is_dotdot():
                        extent = parent_dirrecord_extent
                        # Special case; the root directory record has no
                        # parent, so the dotdot extent gets set to the same as
                        # the dot extent.
                        if parent_dirrecord_extent is None:
                            extent = curr_dirrecord_extent
                        length = child.write_record(outfp, extent)
                    else:
                        length = child.write_record(outfp, next_dirrecord_extent)
                        dirs.append((child, next_dirrecord_extent, curr_dirrecord_extent))
                        next_dirrecord_extent += 1

                    # Now that we are done, increment our dirrecord offset and
                    # seek back to where we came from.
                    curr_dirrecord_offset += length
                    outfp.seek(orig_loc)
                else:
                    # If the child is a file, then we need to do 2 things:
                    # 1.  Write the data to the next free extent in the output
                    #     file.
                    # 2.  Write the directory record with the correct extent
                    #     into the directory record extent of the child's
                    #     parent.
                    orig_loc = outfp.tell()
                    outfp.seek(curr_dirrecord_extent * self.pvd.logical_block_size() + curr_dirrecord_offset)
                    length = child.write_record(outfp, orig_loc / self.pvd.logical_block_size())
                    outfp.seek(orig_loc)
                    child.write_data(outfp, self.cdfd, self.pvd.logical_block_size())

        end_of_data = outfp.tell()

        # Now that we know all of the information we need, we can go back and
        # write out the PVD.
        outfp.seek(16 * 2048)
        self.pvd.write(outfp, dirrecords_extent,
                       end_of_data / self.pvd.logical_block_size())

        outfp.close()

    def _name_and_parent_from_path(self, iso_path):
        if iso_path[0] != '/':
            raise Exception("Must be a path starting with /")

        # First we need to find the parent of this directory, and add this
        # one as a child.
        splitpath = iso_path.split('/')
        # Pop off the front, as that always the blank
        splitpath.pop(0)
        # Now take the name off
        name = splitpath.pop()
        if len(splitpath) == 0:
            # This is a new directory under the root, add it there
            parent = self.pvd.root_directory_record()
        else:
            parent,index = self._find_record('/' + '/'.join(splitpath))

        return (name, parent)

    def add_file(self, local_filename, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        rec = DirectoryRecord()
        rec.new_file(local_filename, name, parent, self.pvd.sequence_number())

    def add_data(self, data, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        rec = DirectoryRecord()
        rec.new_data(data, name, parent, self.pvd.sequence_number())

    def add_fp(self, fp, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        rec = DirectoryRecord()
        rec.new_fp(fp, name, parent, self.pvd.sequence_number())

    def add_directory(self, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        (name, parent) = self._name_and_parent_from_path(iso_path)

        rec = DirectoryRecord()
        rec.new_dir(name, parent, self.pvd.sequence_number())

        dot = DirectoryRecord()
        dot.new_dot(rec, self.pvd.sequence_number())

        dotdot = DirectoryRecord()
        dotdot.new_dotdot(rec, self.pvd.sequence_number())

        # We always need to add an entry to the path table record
        ptr = PathTableRecord()
        ptr.new_dir(name)
        self.path_table_records.append(ptr)

        self.pvd.add_to_ptr_size(ptr.read_length(name))

    def rm_file(self, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path[0] != '/':
            raise Exception("Must be a path starting with /")

        child,index = self._find_record(iso_path)

        if not child.is_file():
            raise Exception("Cannot remove a directory with rm_file (try rm_dir instead(")

        del child.parent.children[index]

    def rm_dir(self, iso_path):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if iso_path == '/':
            raise Exception("Cannot remove base directory")

        child,index = self._find_record(iso_path)

        if not child.is_dir():
            raise Exception("Cannot remove a file with rm_dir (try rm_file instead)")

        for c in child.children:
            if c.is_dot() or c.is_dotdot():
                continue
            raise Exception("Directory must be empty to use rm_dir")

        del child.parent.children[index]

    def set_sequence_number(self, seqnum):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        self.pvd.set_sequence_number(seqnum)

    def set_set_size(self, set_size):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        self.pvd.set_set_size(set_size)

    def close(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")
        if self.opened_fd:
            self.cdfd.close()
        # now that we are closed, re-initialize everything
        self._initialize()
