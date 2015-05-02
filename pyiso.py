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
    # Ecma-119, 8.4.26.1 specifies the date format as: 20150424121822110xf0 (offset from GMT in 15min intervals, -16 for us)
    def __init__(self, datestr):
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
        timestruct = time.strptime(datestr[:-3], "%Y%m%d%H%M%S")
        self.year = timestruct.tm_year
        self.month = timestruct.tm_mon
        self.dayofmonth = timestruct.tm_mday
        self.hour = timestruct.tm_hour
        self.minute = timestruct.tm_min
        self.second = timestruct.tm_sec
        self.hundredthsofsecond = int(datestr[14:15])
        self.gmtoffset = struct.unpack("=b", datestr[16])

    def __str__(self):
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

    def date_string(self):
        return self.date_str

class FileOrTextIdentifier(object):
    def __init__(self, ident_str):
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

    def is_file(self):
        return self.isfile

    def is_text(self):
        return not self.isfile

    def __str__(self):
        fileortext = "Text"
        if self.isfile:
            fileortext = "File"
        return "%s (%s)" % (self.text, fileortext)

    def identification_string(self):
        if self.isfile:
            return "\x5f" + self.text
        # implicitly a text identifier
        return self.text

class DirectoryRecordDate(object):
    def __init__(self):
        self.initialized = False

    def from_record(self, years_since_1900, month, day_of_month, hour,
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
        self.gmtoffset = -(tmpmin + 60 * (tmphour + 24 * tmpyday)) / 15
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
        self.extent_loc = extent_location_le

        if data_length_le != swab_32bit(data_length_be):
            raise Exception("Little-endian and big-endian data length disagree")
        self.data_length = data_length_le

        if seqnum_le != swab_16bit(seqnum_be):
            raise Exception("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        self.date = DirectoryRecordDate()
        self.date.from_record(years_since_1900, month, day_of_month, hour,
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
            self.file_ident = '/'
            self.isdir = True
        else:
            self.file_ident = record[33:33 + self.len_fi]
            if self.file_flags & (1 << self.FILE_FLAG_DIRECTORY_BIT):
                self.isdir = True
                if self.len_fi == 1:
                    if record[33] == "\x00":
                        self.file_ident = '.'
                    elif record[33] == "\x01":
                        self.file_ident = '..'

        if self.xattr_len != 0:
            if self.file_flags & (1 << self.FILE_FLAG_RECORD_BIT):
                raise Exception("Record Bit not allowed with Extended Attributes")
            if self.file_flags & (1 << self.FILE_FLAG_PROTECTION_BIT):
                raise Exception("Protection Bit not allowed with Extended Attributes")

        self.original_data_location = self.DATA_ON_ORIGINAL_ISO
        self.initialized = True

    def _new(self, isoname, parent):
        if self.initialized:
            raise Exception("Directory Record already initialized")

        self.parent = parent

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

        self.file_ident = iso9660mangle([isoname])
        self.seqnum = 1 # FIXME: we don't support setting the seqnum for now
        self.extent_loc = 0 # FIXME: this is wrong, we may have to calculate this at writeout time
        self.len_fi = len(self.file_ident)
        self.dr_len = struct.calcsize(self.fmt) + self.len_fi
        if self.dr_len % 2 != 0:
            self.dr_len += 1

        self.file_flags = 0 # FIXME: we don't support setting file flags for now
        self.file_unit_size = 0 # FIXME: we don't support setting file unit size for now
        self.interleave_gap_size = 0 # FIXME: we don't support setting interleave gap size for now
        self.xattr_len = 0 # FIXME: we don't support xattrs for now
        self.children = []
        self.is_root = False
        self.isdir = False
        self.parent.add_child(self)
        self.initialized = True

    def new_file(self, orig_filename, isoname, parent):
        self.data_length = os.stat(orig_filename).st_size
        self.original_data_location = self.DATA_IN_EXTERNAL_FILE
        self.original_filename = orig_filename
        self._new(isoname, parent)

    def new_data(self, data, isoname, parent):
        # FIXME: we might want to have the length passed in, which could be
        # faster
        self.data = data
        self.data_length = len(data)
        self.original_data_location = self.DATA_IN_MEMORY
        self._new(isoname, parent)

    def new_fp(self, fp, isoname, parent):
        self.data_length = os.fstat(fp.fileno()).st_size
        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.fp = fp
        self._new(isoname, parent)

    def add_child(self, child):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        child.parent = self
        self.children.append(child)
        print("Appending child %s to parent %s" % (child.file_ident, self.file_ident))

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
        return self.file_ident == '.'

    def is_dotdot(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident == '..'

    def extent_location(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.extent_loc

    def file_identifier(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident

    def file_length(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.data_length

    def record(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        name = self.file_ident
        if self.is_root or self.file_ident == '.':
            name = "\x00"
        elif self.file_ident == '..':
            name = "\x01"

        # Ecma-119 9.1.5 says the date should reflect the time when the
        # record was written, so we make a new date now and use that to
        # write out the record.
        self.date = DirectoryRecordDate()
        self.date.new()

        pad = ""
        if (struct.calcsize(self.fmt) + self.len_fi) % 2 != 0:
            pad = "\x00"
        return struct.pack(self.fmt, self.dr_len, self.xattr_len,
                           self.extent_loc, swab_32bit(self.extent_loc),
                           self.data_length, swab_32bit(self.data_length),
                           self.date.years_since_1900, self.date.month,
                           self.date.day_of_month, self.date.hour,
                           self.date.minute, self.date.second,
                           self.date.gmtoffset, self.file_flags,
                           self.file_unit_size, self.interleave_gap_size,
                           self.seqnum, swab_16bit(self.seqnum),
                           self.len_fi) + name + pad

    def write_record(self, outfp):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        record = self.record()
        outfp.write(record)
        return len(record)

    def __str__(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        retstr  = "Directory Record Length:   %d\n" % self.dr_len
        retstr += "Extended Attribute Length: %d\n" % self.xattr_len
        retstr += "Extent Location:           %d\n" % self.extent_loc
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

        # FIXME: According to Ecma-119, we have to parse both the
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
        # In doing this, we should:
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

        self.publisher_identifier = FileOrTextIdentifier(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier(app_ident_str)
        self.volume_creation_date = VolumeDescriptorDate(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate(vol_effective_date_str)
        self.root_dir_record = DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, True)

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

    def write(self, outfp):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        outfp.write(struct.pack(self.fmt, self.descriptor_type,
                                self.identifier, self.version, 0,
                                self.system_identifier, self.volume_identifier,
                                0, self.space_size,
                                swab_32bit(self.space_size), 0, 0, 0, 0,
                                self.set_size, swab_16bit(self.set_size),
                                self.seqnum, swab_16bit(self.seqnum),
                                self.log_block_size,
                                swab_16bit(self.log_block_size),
                                self.path_tbl_size,
                                swab_32bit(self.path_tbl_size),
                                self.path_table_location_le,
                                self.optional_path_table_location_le,
                                self.path_table_location_be,
                                self.optional_path_table_location_be,
                                self.root_dir_record.record(),
                                self.volume_set_identifier,
                                self.publisher_identifier.identification_string(),
                                self.preparer_identifier.identification_string(),
                                "{:<128}".format("PyIso (C) 2015 Chris Lalancette"),
                                self.copyright_file_identifier,
                                self.abstract_file_identifier,
                                self.bibliographic_file_identifier,
                                # FIXME: we want a new creation and modification date
                                self.volume_creation_date.date_string(),
                                self.volume_modification_date.date_string(),
                                self.volume_expiration_date.date_string(),
                                self.volume_effective_date.date_string(),
                                self.file_structure_version, 0,
                                self.application_use, "\x00" * 653))

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
        self.volume_creation_date = VolumeDescriptorDate(vol_create_date_str)
        self.volume_modification_date = VolumeDescriptorDate(vol_mod_date_str)
        self.volume_expiration_date = VolumeDescriptorDate(vol_expire_date_str)
        self.volume_effective_date = VolumeDescriptorDate(vol_effective_date_str)
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

    def _write(self, outfp, ext_loc, parent_dir_num):
        if not self.initialized:
            raise Exception("Path Table Record not yet initialized")

        outfp.write(struct.pack(self.fmt, self.len_di, self.xattr_length,
                              ext_loc, parent_dir_num))
        outfp.write(self.directory_identifier)
        len_pad = 0
        if self.len_di % 2 != 0:
            outfp.write("\x00")
            len_pad = 1

        return struct.calcsize(self.fmt) + self.len_di + len_pad

    def write_little_endian(self, outfp):
        return self._write(outfp, self.extent_location, self.parent_directory_num)

    def write_big_endian(self, outfp):
        return self._write(outfp, swab_32bit(self.extent_location),
                           swab_16bit(self.parent_directory_num))

class File(object):
    """
    Objects of this class represent files on the ISO that we deal with through
    the external API.  These are converted to and from ISO9660 DirectoryRecord
    classes as necessary.
    """
    def __init__(self, dir_record):
        # strip off the version form the file identifier
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
        self.name = dir_record.file_identifier()[:-2]

    def __str__(self):
        return self.name

# FIXME: is there no better way to do this swab?
def swab_32bit(input_int):
    return struct.unpack("<L", struct.pack(">L", input_int))[0]

def swab_16bit(input_int):
    return struct.unpack("<H", struct.pack(">H", input_int))[0]

def pad(outfp, data_size, pad_size, do_write=False):
    pad = pad_size - (data_size % pad_size)
    if pad != pad_size:
        # There are times when we actually want to write the zeros to disk;
        # in that case, we use the write.  Otherwise we use seek, which should
        # be faster in general.
        if do_write:
            outfp.write("\x00" * pad)
        else:
            outfp.seek(pad, 1) # 1 means "seek from here"

def iso9660mangle(split):
    # ISO9660 ends up mangling names quite a bit.  First of all, they must
    # fit into 8.3.  Second, they *must* have a dot.  Third, they all have
    # a semicolon number attached to the end.  Here we mangle a name
    # according to ISO9660
    if len(split) != 1:
        # this is a directory, so just return it
        return split.pop(0)

    ret = split.pop(0)
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
        # Area and a Data Area, where the System Area is in logical sectors 0 to
        # 15, and whose contents is not specified by the standard.
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

    def seek_to_extent(self, extent):
        self.cdfd.seek(extent * self.pvd.logical_block_size())

    def _walk_directories(self):
        dirs = [(self.pvd.root_directory_record(), self.pvd.root_directory_record())]
        while dirs:
            (root, dir_record) = dirs.pop(0)
            self.seek_to_extent(dir_record.extent_location())
            while True:
                # read the length byte for the directory record
                (lenbyte,) = struct.unpack("=B", self.cdfd.read(1))
                if lenbyte == 0:
                    # if we saw 0 len, we are finished with this extent
                    break
                new_record = DirectoryRecord()
                new_record.parse(struct.pack("=B", lenbyte) + self.cdfd.read(lenbyte - 1), False)
                if new_record.is_dir() and not new_record.is_dot() and not new_record.is_dotdot():
                    dirs += [(root, new_record)]
                root.add_child(new_record)

    def _initialize(self):
        self.cdfd = None
        self.opened_fd = False
        self.pvd = None
        self.svds = []
        self.vpds = []
        self.brs = []
        self.vdsts = []
        self.initialized = False

    def __init__(self):
        self._initialize()

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
        print(self.pvd)

        # Now that we have the PVD, parse the Path Tables.
        # Section 9.4 (p. 43)
        self.seek_to_extent(self.pvd.path_table_location_le)
        self.path_table_records = []
        left = self.pvd.path_table_size()
        while left > 0:
            ptr = PathTableRecord()
            (len_di,) = struct.unpack("=B", self.cdfd.read(1))
            pad = len_di % 2
            read_len = 1 + 4 + 2 + len_di + pad
            ptr.parse(struct.pack("=B", len_di) + self.cdfd.read(read_len))
            self.path_table_records.append(ptr)
            left -= (read_len + 1)

        # here we read all of the big endian path table records and make
        # sure they agree with the little endian ones
        self.seek_to_extent(swab_32bit(self.pvd.path_table_location_be))
        index = 0
        left = self.pvd.path_table_size()
        while left > 0:
            ptr = PathTableRecord()
            (len_di,) = struct.unpack("=B", self.cdfd.read(1))
            pad = len_di % 2
            read_len = 1 + 4 + 2 + len_di + pad
            ptr.parse(struct.pack("=B", len_di) + self.cdfd.read(read_len))

            if ptr.len_di != self.path_table_records[index].len_di or \
               ptr.xattr_length != self.path_table_records[index].xattr_length or \
               swab_32bit(ptr.extent_location) != self.path_table_records[index].extent_location or \
               swab_16bit(ptr.parent_directory_num) != self.path_table_records[index].parent_directory_num or \
               ptr.directory_identifier != self.path_table_records[index].directory_identifier:
                raise Exception("Little endian and big endian path table records do not agree")
            index += 1
            left -= (read_len + 1)

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
        self.cdfd = open(filename, "r")
        self.opened_fd = True

        self._do_open()

    def print_tree(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")
        print("%s (extent %d)" % (self.pvd.root_directory_record().file_identifier(), self.pvd.root_directory_record().extent_location()))
        for child in self.pvd.root_directory_record().children:
            print("%s (extent %d)" % (child.file_identifier(), child.extent_location()))

    def _find_record(self, isopath):
        if isopath[0] != '/':
            raise Exception("Must be a path starting with /")

        split = isopath.split('/')
        split.pop(0)

        found_record = None
        root = self.pvd.root_directory_record()
        while found_record is None:
            name = iso9660mangle(split)
            for child in root.children:
                # FIXME: what happens when we have files that end up with ;2, ;3?
                if child.file_identifier() == name:
                    if len(split) == 0:
                        found_record = child
                    else:
                        if not child.is_dir():
                            raise Exception("Intermediate path not a directory")
                        root = child
                        name = iso9660mangle(split)
                    break

        if not found_record:
            raise Exception("File not found")

        self.seek_to_extent(found_record.extent_location())

        return found_record

    def list_files(self, path, recurse=False):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if path[0] != '/':
            raise Exception("Must be a path starting with /")

        split = path.split('/')
        split.pop(0)

        entries = []
        for child in self.pvd.root_directory_record().children:
            if child.is_dot() or child.is_dotdot():
                continue

            if child.is_dir():
                entries.append(Directory(child))
                # FIXME: deal with recursion into subdirectories
            elif child.is_file():
                entries.append(File(child))
            else:
                # This should never happen
                raise Exception("Entry is not a file or a directory")

        return entries

    def get_file(self, isopath):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record(isopath)

        return self.cdfd.read(found_record.file_length())

    def _write_fd_to_disk(self, found_record, outfp, blocksize):
        total = found_record.file_length()
        while total != 0:
            thisread = blocksize
            if total < thisread:
                thisread = total
            outfp.write(self.cdfd.read(thisread))
            total -= thisread

    def get_and_write_file(self, isopath, outpath, overwrite=False,
                           blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record(isopath)

        # FIXME: what happens when we fall off the end of the extent?
        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        outfp = open(outpath, "w")
        self._write_fd_to_disk(found_record, outfp, blocksize)
        outfp.close()

    def get_and_write_fd(self, isopath, outfp, blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record(isopath)

        self._write_fd_to_disk(found_record, outfp, blocksize)

    def write(self, outpath, overwrite=False):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.pvd is None:
            raise Exception("This object does not have a Primary Volume Descriptor yet")

        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        outfp = open(outpath, 'w')
        outfp.seek(16 * self.pvd.logical_block_size())
        # First write out the PVD.
        self.pvd.write(outfp)
        # Now write out the Volume Descriptor Terminators
        for vdst in self.vdsts:
            vdst.write(outfp)
        # Now we have to write out the Path Table Records
        # Little-Endian
        # FIXME: what if len(self.path_table_le) and
        # self.pvd.path_table_size don't agree?
        outfp.seek(self.pvd.path_table_location_le * self.pvd.logical_block_size())
        length = 0
        for record in self.path_table_records:
            length += record.write_little_endian(outfp)
        pad(outfp, length, 4096)

        # Big-Endian
        outfp.seek(swab_32bit(self.pvd.path_table_location_be) * self.pvd.logical_block_size())
        length = 0
        for record in self.path_table_records:
            length += record.write_big_endian(outfp)
        pad(outfp, length, 4096)

        # In order in the final ISO, the directory records are next.  However,
        # we don't necessarily know all of the extent locations for the
        # children at this point, so we save a pointer and we'll seek back
        # and write the directory records at the end.
        dirrecords_location = outfp.tell()
        # FIXME: what happens if the directory records are longer than one
        # extent?
        outfp.seek(2048, 1)

        root_child_list = sorted(self.pvd.root_directory_record().children,
                                 key=lambda child: child.file_ident)

        # Now we need to write out the actual files.  Note that in many cases,
        # we haven't yet read the file out of the original, so we need to do
        # that here.
        for child in root_child_list:
            if child.is_dot() or child.is_dotdot():
                continue

            extent_loc = outfp.tell() / self.pvd.logical_block_size()

            if child.original_data_location == child.DATA_IN_MEMORY:
                # If the data is already in memory, we really don't have to
                # do anything smart.  Just write the data out to the ISO.
                outfp.write(child.data)
            else:
                if child.original_data_location == child.DATA_ON_ORIGINAL_ISO:
                    self.seek_to_extent(child.extent_location())
                    datafp = self.cdfd
                elif child.original_data_location == child.DATA_IN_EXTERNAL_FILE:
                    datafp = open(child.original_filename, 'rb')
                elif child.original_data_location == child.DATA_IN_EXTERNAL_FP:
                    datafp = child.fp

                print("Writing child %s" % (child.file_ident))
                left = child.file_length()
                readsize = 8192
                while left > 0:
                    if left < readsize:
                        readsize = left
                    outfp.write(datafp.read(readsize))
                    left -= readsize

                if child.original_data_location == child.DATA_IN_EXTERNAL_FILE:
                    datafp.close()
            child.extent_loc = extent_loc
            pad(outfp, child.file_length(), 2048, do_write=True)

        # Now that we have written the children, all of the extent locations
        # should be correct so we need to write out the directory records.
        # FIXME: what happens if this goes over a single extent?
        outfp.seek(dirrecords_location)
        length = 0
        for child in root_child_list:
            # FIXME: we need to recurse into subdirectories
            length += child.write_record(outfp)

        outfp.close()

    def add_file(self, local_filename, iso_path):
        # FIXME: the prototype for new_file looks like this:
        #def new_file(self, orig_filename, isoname, parent):
        # We really need to figure out the isoname from the iso_path (really
        # just the last part of the full path), and the parent directory object
        # it belongs to
        rec = DirectoryRecord()
        rec.new_file(local_filename, iso_path.split("/")[1], self.pvd.root_directory_record())

    def add_data(self, data, iso_path):
        # FIXME: the prototype for new_data looks like this:
        #def new_data(self, data, isoname, parent):
        # We really need to figure out the isoname from the iso_path (really
        # just the last part of the full path), and the parent directory object
        # it belongs to
        rec = DirectoryRecord()
        rec.new_data(data, iso_path.split("/")[1], self.pvd.root_directory_record())

    def add_fp(self, fp, iso_path):
        # FIXME: the prototype for new_fp looks like this:
        #def new_fp(self, fp, isoname, parent):
        # We really need to figure out the isoname from the iso_path (really
        # just the last part of the full path), and the parent directory object
        # it belongs to
        rec = DirectoryRecord()
        rec.new_fp(fp, iso_path.split("/")[1], self.pvd.root_directory_record())

    def add_directory(self, iso_path, recurse=False):
        pass

    def close(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")
        if self.opened_fd:
            self.cdfd.close()
        # now that we are closed, re-initialize everything
        self._initialize()
