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
        self.is_file = False
        if ident_str[0] == "\x5f":
            # If it is a file, Ecma-119 says that it must be at the Root
            # directory and it must be 8.3 (so 12 byte, plus one for the 0x5f)
            if len(ident_str) > 13:
                raise Exception("Filename for identifier is not in 8.3 format!")
            self.is_file = True
            self.text = ident_str[1:]

    def isfile(self):
        return self.is_file

    def istext(self):
        return not self.is_file

    def __str__(self):
        fileortext = "Text"
        if self.is_file:
            fileortext = "File"
        return "%s (%s)" % (self.text, fileortext)

    def identification_string(self):
        if self.is_file:
            return "\x5f" + self.text
        # implicitly a text identifier
        return self.text

class DirectoryRecord(object):
    FILE_FLAG_EXISTENCE_BIT = 0
    FILE_FLAG_DIRECTORY_BIT = 1
    FILE_FLAG_ASSOCIATED_FILE_BIT = 2
    FILE_FLAG_RECORD_BIT = 3
    FILE_FLAG_PROTECTION_BIT = 4
    FILE_FLAG_MULTI_EXTENT_BIT = 7

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

        (self.dr_len, self.xattr_len, self.extent_location_le,
         self.extent_location_be, self.data_length_le, self.data_length_be,
         self.years_since_1900, self.month, self.day_of_month, self.hour,
         self.minute, self.second, self.gmtoffset, self.file_flags,
         self.file_unit_size, self.interleave_gap_size, self.seqnum_le,
         self.seqnum_be, self.len_fi) = struct.unpack(self.fmt, record[:33])

        if len(record) != self.dr_len:
            # The record we were passed doesn't have the same information in it
            # as the directory entry thinks it should
            raise Exception("Length of directory entry doesn't match internal check")

        # FIXME: we should really make an object for the date and time

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

        self.initialized = True

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
        return self.file_ident == '.'

    def is_dotdot(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident == '..'

    def extent_location(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.extent_location_le

    def file_identifier(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.file_ident

    def file_length(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        return self.data_length_le

    def record(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")

        name = self.file_ident
        if self.is_root or self.file_ident == '.':
            name = "\x00"
        elif self.file_ident == '..':
            name = "\x01"

        return struct.pack(self.fmt, self.dr_len, self.xattr_len,
                           self.extent_location_le, self.extent_location_be,
                           self.data_length_le, self.data_length_be,
                           self.years_since_1900, self.month, self.day_of_month,
                           self.hour, self.minute, self.second, self.gmtoffset,
                           self.file_flags, self.file_unit_size,
                           self.interleave_gap_size, self.seqnum_le,
                           self.seqnum_be, self.len_fi) + name

    def write_record(self, out):
        out.write(self.record())

    def __str__(self):
        if not self.initialized:
            raise Exception("Directory Record not yet initialized")
        retstr  = "Directory Record Length:   %d\n" % self.dr_len
        retstr += "Extended Attribute Length: %d\n" % self.xattr_len
        retstr += "Extent Location:           %d\n" % self.extent_location_le
        retstr += "Data Length:               %d\n" % self.data_length_le
        retstr += "Date and Time:             %.2d/%.2d/%.2d %.2d:%.2d:%.2d (%d)\n" % (self.years_since_1900 + 1900, self.month, self.day_of_month, self.hour, self.minute, self.second, self.gmtoffset)
        retstr += "File Flags:                %d\n" % self.file_flags
        retstr += "File Unit Size:            %d\n" % self.file_unit_size
        retstr += "Interleave Gap Size:       %d\n" % self.interleave_gap_size
        retstr += "Seqnum:                    %d\n" % self.seqnum_le
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

        (self.descriptor_type, self.identifier, self.version, unused1,
         self.system_identifier, self.volume_identifier, unused2,
         self.space_size_le, self.space_size_be, unused3dot1, unused3dot2,
         unused3dot3, unused3dot4, self.set_size_le, self.set_size_be,
         self.seqnum_le, self.seqnum_be, self.logical_block_size_le,
         self.logical_block_size_be, self.path_table_size_le,
         self.path_table_size_be, self.path_table_location_le,
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

        return self.logical_block_size_le

    def root_directory_record(self):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def write(self, out):
        if not self.initialized:
            raise Exception("This Primary Volume Descriptor is not yet initialized")

        out.write(struct.pack(self.fmt, self.descriptor_type, self.identifier,
                              self.version, 0, self.system_identifier,
                              self.volume_identifier, 0, self.space_size_le,
                              self.space_size_be, 0, 0, 0, 0, self.set_size_le,
                              self.set_size_be, self.seqnum_le, self.seqnum_be,
                              self.logical_block_size_le,
                              self.logical_block_size_be,
                              self.path_table_size_le, self.path_table_size_be,
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
        retstr += "Space Size:                    %d\n" % self.space_size_le
        retstr += "Set Size:                      %d\n" % self.set_size_le
        retstr += "SeqNum:                        %d\n" % self.seqnum_le
        retstr += "Logical Block Size:            %d\n" % self.logical_block_size_le
        retstr += "Path Table Size:               %d\n" % self.path_table_size_le
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

    def write(self, out):
        if not self.initialized:
            raise Exception("Volume Descriptor Set Terminator not yet initialized")
        out.write(struct.pack(self.fmt, self.descriptor_type, self.identifier,
                              self.version, "\x00" * 2041))

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
         self.space_size_le, self.space_size_be, self.escape_sequences,
         self.set_size_le, self.set_size_be, self.seqnum_le, self.seqnum_be,
         self.logical_block_size_le, self.logical_block_size_be,
         self.path_table_size_le, self.path_table_size_be,
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
        retstr += "Space Size:                    %d\n" % self.space_size_le
        retstr += "Escape Sequences:              '%s'\n" % self.escape_sequences
        retstr += "Set Size:                      %d\n" % self.set_size_le
        retstr += "SeqNum:                        %d\n" % self.seqnum_le
        retstr += "Logical Block Size:            %d\n" % self.logical_block_size_le
        retstr += "Path Table Size:               %d\n" % self.path_table_size_le
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
         self.volume_partition_location_le, self.volume_partition_location_be,
         self.volume_partition_size_le, self.volume_partition_size_be,
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

        self.initialized = True

    def __str__(self):
        if not self.initialized:
            raise Exception("Volume Partition not initialized")

        retstr  = "Desc:                          %d\n" % self.descriptor_type
        retstr += "Identifier:                    '%s'\n" % self.identifier
        retstr += "Version:                       %d\n" % self.version
        retstr += "System Identifier:             '%s'\n" % self.system_identifier
        retstr += "Volume Partition Identifier:   '%s'\n" % self.volume_partition_identifier
        retstr += "Volume Partition Location:     %d\n" % self.volume_partition_location_le
        retstr += "Volume Partition Size:         %d\n" % self.volume_partition_size_le
        retstr += "System Use:                    '%s'" % self.system_use
        return retstr

class ExtendedAttributeRecord(object):
    def __init__(self):
        self.initialized = False
        self.fmt = "=HHHHH17s17s17s17sBBHH32s64sBB64sHH"

    def parse(self, record):
        if self.initialized:
            raise Exception("Volume Partition already initialized")

        (self.owner_identification_le, self.owner_identification_be,
         self.group_identification_le, self.group_identification_be,
         self.permissions, file_create_date_str, file_mod_date_str,
         file_expire_date_str, file_effective_date_str,
         self.record_format, self.record_attributes, self.record_length_le,
         self.record_length_be, self.system_identifier,
         self.system_use, self.extended_attribute_record_version,
         self.length_of_escape_sequences, unused,
         self.len_au_le, self.len_au_be) = struct.unpack(self.fmt, record)

        self.file_creation_date = VolumeDescriptorDate(file_create_date_str)
        self.file_modification_date = VolumeDescriptorDate(file_mod_date_str)
        self.file_expiration_date = VolumeDescriptorDate(file_expire_date_str)
        self.file_effective_date = VolumeDescriptorDate(file_effective_date_str)

        self.application_use = record[250:250 + self.len_au]
        self.escape_sequences = record[250 + self.len_au:250 + self.len_au + self.length_of_escape_sequences]

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
def swab(input_int):
    tmp = struct.pack(">L", input_int)
    (ret,) = struct.unpack("<L", tmp)
    return ret

def pad(out, size, pad_size):
    pad = pad_size - size % pad_size
    if pad != pad_size:
        out.seek(pad, 1) # 1 means "seek from here"

def write_data_and_pad(out, data, size, pad_size):
    out.write(data)
    # we need to pad out
    pad(out, size, pad_size)

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

    def _walk_directories(self):
        dirs = [(self.pvd.root_directory_record(), self.pvd.root_directory_record())]
        while dirs:
            (root, dir_record) = dirs.pop(0)
            self.cdfd.seek(dir_record.extent_location() * self.pvd.logical_block_size())
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
        self.cdfd.seek(self.pvd.path_table_location_le * self.pvd.logical_block_size())
        self.path_table_le = self.cdfd.read(self.pvd.path_table_size_le)

        self.cdfd.seek(swab(self.pvd.path_table_location_be) * self.pvd.logical_block_size())
        self.path_table_be = self.cdfd.read(swab(self.pvd.path_table_size_be))

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

    def _iso9660mangle(self, split):
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
            name = self._iso9660mangle(split)
            for child in root.children:
                # FIXME: what happens when we have files that end up with ;2, ;3?
                if child.file_identifier() == name:
                    if len(split) == 0:
                        found_record = child
                    else:
                        if not child.is_dir():
                            raise Exception("Intermediate path not a directory")
                        root = child
                        name = self._iso9660mangle(split)
                    break

        if not found_record:
            raise Exception("File not found")

        self.cdfd.seek(found_record.extent_location() * self.pvd.logical_block_size())

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

    def _write_fd_to_disk(self, found_record, out, blocksize):
        total = found_record.file_length()
        while total != 0:
            thisread = blocksize
            if total < thisread:
                thisread = total
            data = self.cdfd.read(thisread)
            out.write(data)
            total -= thisread

    def get_and_write_file(self, isopath, outpath, overwrite=False,
                           blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record(isopath)

        # FIXME: what happens when we fall off the end of the extent?
        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        out = open(outpath, "w")
        self._write_fd_to_disk(found_record, out, blocksize)
        out.close()

    def get_and_write_fd(self, isopath, outfd, blocksize=8192):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        found_record = self._find_record(isopath)

        self._write_fd_to_disk(found_record, outfd, blocksize)

    def write(self, outpath, overwrite=False):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")

        if self.pvd is None:
            raise Exception("This object does not have a Primary Volume Descriptor yet")

        if not overwrite and os.path.exists(outpath):
            raise Exception("Output file already exists")

        out = open(outpath, 'w')
        out.seek(16 * self.pvd.logical_block_size())
        # First write out the PVD.
        self.pvd.write(out)
        # Now write out the Volume Descriptor Terminators
        for vdst in self.vdsts:
            vdst.write(out)
        # Now we have to write out the Path Table Records
        # Little-Endian
        # FIXME: we should generate the path table records
        # FIXME: what if len(self.path_table_le) and
        # self.pvd.path_table_size_le don't agree?
        # FIXME: what if path_table_size_le and path_table_size_be
        # don't agree?
        out.seek(self.pvd.path_table_location_le * self.pvd.logical_block_size())
        write_data_and_pad(out, self.path_table_le,
                           self.pvd.path_table_size_le, 4096)

        # Big-Endian
        out.seek(swab(self.pvd.path_table_location_be) * self.pvd.logical_block_size())
        write_data_and_pad(out, self.path_table_be,
                           swab(self.pvd.path_table_size_be), 4096)

        # Now we need to write out the directory records
        for child in self.pvd.root_directory_record().children:
            # FIXME: we need to recurse into subdirectories
            child.write_record(out)

        # we need to pad out
        pad(out, out.tell(), 2048)

        # Finally we need to write out the actual files.  Note that in
        # many cases, we haven't yet read the file out of the original
        # ISO, so we need to do that here.
        for child in self.pvd.root_directory_record().children:
            if child.is_dot() or child.is_dotdot():
                continue
            self.cdfd.seek(child.extent_location() * self.pvd.logical_block_size())
            # FIXME: this reads the entire file into memory; we really only
            # want to read a bit at a time
            data = self.cdfd.read(child.file_length())
            # FIXME: calculating the length here is probably expensive
            write_data_and_pad(out, data, len(data), 2048)
            # FIXME: we need to recurse into subdirectories

        out.close()

    def close(self):
        if not self.initialized:
            raise Exception("This object is not yet initialized; call either open() or new() to create an ISO")
        if self.opened_fd:
            self.cdfd.close()
        # now that we are closed, re-initialize everything
        self._initialize()
