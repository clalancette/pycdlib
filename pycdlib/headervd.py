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
Base class for Primary and Supplementary Volume Descriptor.
'''

from __future__ import absolute_import

import struct
import time

import pycdlib.dates as dates
import pycdlib.dr as dr
import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.rockridge as rockridge
import pycdlib.utils as utils

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
        self._initialized = False
        self.space_size = None
        self.log_block_size = None
        self.root_dir_record = None
        self.path_tbl_size = None
        self.path_table_num_extents = None
        self.seqnum = None
        self.new_extent_loc = None
        self.orig_extent_loc = None

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
        # pylint: disable=unused-argument,no-self-use
        raise pycdlibexception.PyCdlibInternalError("Child class must implement parse")

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident_str, preparer_ident_str, app_ident_str,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use, xa, version, escape_sequence):
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
         xa - Whether to embed XA data into the volume descriptor.
         version - What version to assign to the header.
         escape_sequence - The escape sequence to assign to this volume descriptor.
        Returns:
         Nothing.
        '''
        # pylint: disable=unused-argument,no-self-use
        raise pycdlibexception.PyCdlibInternalError("Child class must implement new")

    def path_table_size(self):
        '''
        A method to get the path table size of the Volume Descriptor.

        Parameters:
         None.
        Returns:
         Path table size in bytes.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        return self.path_tbl_size

    def add_to_space_size(self, addition_bytes):
        '''
        A method to add bytes to the space size tracked by this Volume
        Descriptor.

        Parameters:
         addition_bytes - The number of bytes to add to the space size.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")
        # The "addition" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size += utils.ceiling_div(addition_bytes, self.log_block_size)

    def remove_from_space_size(self, removal_bytes):
        '''
        Remove bytes from the volume descriptor.

        Parameters:
         removal_bytes - The number of bytes to remove.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")
        # The "removal" parameter is expected to be in bytes, but the space
        # size we track is in extents.  Round up to the next extent.
        self.space_size -= utils.ceiling_div(removal_bytes, self.log_block_size)

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
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def logical_block_size(self):
        '''
        A method to get this Volume Descriptor's logical block size.

        Parameters:
         None.
        Returns:
         Size of this Volume Descriptor's logical block size in bytes.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        return self.log_block_size

    def add_to_ptr_size(self, ptr_size):
        '''
        Add the space for a path table record to the volume descriptor.

        Parameters:
         ptr_size - The length of the Path Table Record being added to this Volume Descriptor.
        Returns:
         True if extents need to be added to the Volume Descriptor, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        # First add to the path table size.
        self.path_tbl_size += ptr_size
        if (utils.ceiling_div(self.path_tbl_size, 4096) * 2) > self.path_table_num_extents:
            # If we overflowed the path table size, then we need to update the
            # space size.  Since we always add two extents for the little and
            # two for the big, add four total extents.  The locations will be
            # fixed up during reshuffle_extents.
            self.path_table_num_extents += 2
            return True
        return False

    def remove_from_ptr_size(self, ptr_size):
        '''
        Remove the space for a path table record from the volume descriptor.

        Parameters:
         ptr_size - The length of the Path Table Record being removed from this Volume Descriptor.
        Returns:
         True if extents need to be removed from the Volume Descriptor, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        # Next remove from the Path Table Record size.
        self.path_tbl_size -= ptr_size
        new_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2

        need_remove_extents = False
        if new_extents > self.path_table_num_extents:
            # This should never happen.
            raise pycdlibexception.PyCdlibInvalidInput("This should never happen")
        elif new_extents < self.path_table_num_extents:
            self.path_table_num_extents -= 2
            need_remove_extents = True

        return need_remove_extents

    def sequence_number(self):
        '''
        A method to get this Volume Descriptor's sequence number.

        Parameters:
         None.
        Returns:
         This Volume Descriptor's sequence number.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        return self.seqnum

    def copy_sizes(self, othervd):
        '''
        Copy the path_tbl_size, path_table_num_extents, and space_size from
        another volume descriptor.

        Parameters:
         othervd - The other volume descriptor to copy from.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        self.space_size = othervd.space_size
        self.path_tbl_size = othervd.path_tbl_size
        self.path_table_num_extents = othervd.path_table_num_extents

    def extent_location(self):
        '''
        A method to get this Volume Descriptor's extent location.

        Parameters:
         None.
        Returns:
         Integer of this Volume Descriptor's extent location.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Volume Descriptor is not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


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
        self._initialized = False

    def parse(self, ident_str):
        '''
        Parse a file or text identifier out of a string.

        Parameters:
          ident_str  - The string to parse the file or text identifier from.
        Returns:
          Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This File or Text identifier is already initialized")
        self.text = ident_str

        # FIXME: we do not support a file identifier here.  In the future, we
        # might want to implement this.

        self._initialized = True

    def new(self, text):
        '''
        Create a new file or text identifier.

        Parameters:
          text   - The text to store into the identifier.
        Returns:
          Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This File or Text identifier is already initialized")

        if len(text) != 128:
            raise pycdlibexception.PyCdlibInvalidInput("Length of text must be 128")

        self.text = text

        self._initialized = True

    def record(self):
        '''
        Returns the file or text identification string suitable for recording.

        Parameters:
          None.
        Returns:
          The text representing this identifier.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This File or Text identifier is not yet initialized")
        return self.text

    def __ne__(self, other):
        return self.text != other.text

    def __eq__(self, other):
        return not self.__ne__(other)


class PrimaryVolumeDescriptor(HeaderVolumeDescriptor):
    '''
    A class representing the Primary Volume Descriptor of this ISO.  Note that
    there can be one, and only one, Primary Volume Descriptor per ISO.  This is
    the first thing on the ISO that is parsed, and contains all of the basic
    information about the ISO.
    '''

    FMT = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def __init__(self):
        HeaderVolumeDescriptor.__init__(self)

        self.rr_ce_blocks = []

    def parse(self, vd, data_fp, extent_loc):
        '''
        Parse a primary volume descriptor out of a string.

        Parameters:
         vd - The string containing the Primary Volume Descriptor.
         data_fp - A file object containing the root directory record.
         extent_loc - The location on the ISO of this PVD.  This always has to be 16 for
                      the first PVD, but there can be multiple copies that exist at other
                      locations.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is already initialized")

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
         space_size_le, space_size_be, third_unused, set_size_le, set_size_be,
         seqnum_le, seqnum_be, logical_block_size_le, logical_block_size_be,
         path_table_size_le, path_table_size_be, self.path_table_location_le,
         self.optional_path_table_location_le, self.path_table_location_be,
         self.optional_path_table_location_be, root_dir_record,
         self.volume_set_identifier, pub_ident_str, prepare_ident_str,
         app_ident_str, self.copyright_file_identifier,
         self.abstract_file_identifier, self.bibliographic_file_identifier,
         vol_create_date_str, vol_mod_date_str, vol_expire_date_str,
         vol_effective_date_str, self.file_structure_version, unused4,
         self.application_use, zero5_unused) = struct.unpack_from(self.FMT, vd, 0)

        # According to Ecma-119, 8.4.1, the primary volume descriptor type
        # should be 1.
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_PRIMARY:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001".
        if self.identifier != b"CD001":
            raise pycdlibexception.PyCdlibInvalidISO("invalid CD isoIdentification")
        # According to Ecma-119, 8.4.3, the version should be 1.
        if self.version != 1:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid primary volume descriptor version %d" % (self.version))
        # According to Ecma-119, 8.4.4, the first unused field should be 0.
        if unused1 != 0:
            raise pycdlibexception.PyCdlibInvalidISO("data in unused field not zero")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0.
        if unused2 != 0:
            raise pycdlibexception.PyCdlibInvalidISO("data in 2nd unused field not zero")
        # According to Ecma-119, 8.4.9, the third unused field should be all 0.
        # However, we have seen ISOs in the wild (Fantastic Night Dreams -
        # Cotton Original (Japan).cue from the psx redump collection) that
        # don't have this set to 0, so allow anything here.

        # According to Ecma-119, 8.4.30, the file structure version should be 1.
        # However, we have seen ISOs in the wild that that don't have this
        # properly set to one.  In those cases, forcibly set it to one and let
        # it pass.
        if self.file_structure_version != 1:
            self.file_structure_version = 1
        # According to Ecma-119, 8.4.31, the fourth unused field should be 0.
        if unused4 != 0:
            raise pycdlibexception.PyCdlibInvalidISO("data in 4th unused field not zero")
        # According to Ecma-119, the last 653 bytes of the PVD should be all 0.
        # However, we have seen ISOs in the wild that do not follow this, so
        # relax the check.

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other.
        if space_size_le != utils.swab_32bit(space_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != utils.swab_16bit(set_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != utils.swab_16bit(seqnum_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != utils.swab_16bit(logical_block_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != utils.swab_32bit(path_table_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian path table size disagree")
        self.path_tbl_size = path_table_size_le
        self.path_table_num_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2

        self.path_table_location_be = utils.swab_32bit(self.path_table_location_be)

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.parse(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.parse(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.parse(app_ident_str)
        self.volume_creation_date = dates.VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = dates.VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = dates.VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = dates.VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_dir_record = dr.DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, data_fp, None)

        self.orig_extent_loc = extent_loc
        self.new_extent_loc = None

        self._initialized = True

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident_str, preparer_ident_str, app_ident_str,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use, xa, version, escape_sequence):
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
         pub_ident_str - The publisher identification string to use on the new ISO.
         preparer_ident_str - The preparer identification string to use on the new
                              ISO.
         app_ident_str - The application identification string to use on the new
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
         xa - Whether to embed XA data into the volume descriptor.
         version - What version to assign to the header (ignored).
         escape_sequence - The escape sequence to assign to this volume descriptor (ignored).
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is already initialized")

        if flags != 0:
            raise pycdlibexception.PyCdlibInvalidInput("Non-zero flags not allowed for a PVD")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_PRIMARY
        self.identifier = b"CD001"
        self.version = 1

        if len(sys_ident) > 32:
            raise pycdlibexception.PyCdlibInvalidInput("The system identifer has a maximum length of 32")
        self.system_identifier = sys_ident.ljust(32, b' ')

        if len(vol_ident) > 32:
            raise pycdlibexception.PyCdlibInvalidInput("The volume identifier has a maximum length of 32")
        self.volume_identifier = vol_ident.ljust(32, b' ')

        # The space_size is the number of extents (2048-byte blocks) in the
        # ISO.  We know we will at least have the system area (16 extents),
        # the PVD (1 extent), the little endian path table record (2 extents),
        # the big endian path table record (2 extents), and the root directory
        # record (1 extent), for a total of 22 extents to start with.
        self.space_size = 22
        self.set_size = set_size
        if seqnum > set_size:
            raise pycdlibexception.PyCdlibInvalidInput("Sequence number must be less than or equal to set size")
        self.seqnum = seqnum
        self.log_block_size = log_block_size
        # The path table size is in bytes, and is always at least 10 bytes
        # (for the root directory record).
        self.path_tbl_size = 10
        self.path_table_num_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2
        # By default the Little Endian Path Table record starts at extent 19
        # (right after the Volume Terminator).
        self.path_table_location_le = 19
        # By default the Big Endian Path Table record starts at extent 21
        # (two extents after the Little Endian Path Table Record).
        self.path_table_location_be = 21
        # FIXME: we don't support the optional path table location right now
        self.optional_path_table_location_le = 0
        self.optional_path_table_location_be = 0
        self.root_dir_record = dr.DirectoryRecord()
        self.root_dir_record.new_root(seqnum, self.log_block_size)

        if len(vol_set_ident) > 128:
            raise pycdlibexception.PyCdlibInvalidInput("The maximum length for the volume set identifier is 128")
        self.volume_set_identifier = vol_set_ident.ljust(128, b' ')

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.new(pub_ident_str.ljust(128, b' '))

        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.new(preparer_ident_str.ljust(128, b' '))

        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.new(app_ident_str.ljust(128, b' '))

        self.copyright_file_identifier = copyright_file.ljust(37, b' ')
        self.abstract_file_identifier = abstract_file.ljust(37, b' ')
        self.bibliographic_file_identifier = bibli_file.ljust(37, b' ')

        now = time.time()
        self.volume_creation_date = dates.VolumeDescriptorDate()
        self.volume_creation_date.new(now)
        # We make a valid volume modification date here, but it will get
        # overwritten during record().
        self.volume_modification_date = dates.VolumeDescriptorDate()
        self.volume_modification_date.new(now)
        self.volume_expiration_date = dates.VolumeDescriptorDate()
        self.volume_expiration_date.new(vol_expire_date)
        self.volume_effective_date = dates.VolumeDescriptorDate()
        self.volume_effective_date.new(now)
        self.file_structure_version = 1

        if xa:
            if len(app_use) > 141:
                raise pycdlibexception.PyCdlibInvalidInput("Cannot have XA and an app_use of > 140 bytes")
            self.application_use = app_use.ljust(141, b' ')
            self.application_use += b"CD-XA001" + b"\x00" * 18
            self.application_use = self.application_use.ljust(512, b' ')
        else:
            if len(app_use) > 512:
                raise pycdlibexception.PyCdlibInvalidInput("The maximum length for the application use is 512")
            self.application_use = app_use.ljust(512, b' ')

        self.orig_extent_loc = None
        # This is wrong but will be set by reshuffle_extents
        self.new_extent_loc = 0

        self._initialized = True

    def copy(self, orig_pvd):
        '''
        A method to copy the contents of an old PVD into a new PVD.

        Parameters:
         orig_pvd - The original PVD to copy data from.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is already initialized")

        self.descriptor_type = orig_pvd.descriptor_type
        self.identifier = orig_pvd.identifier
        self.version = orig_pvd.version
        self.system_identifier = orig_pvd.system_identifier
        self.volume_identifier = orig_pvd.volume_identifier
        self.space_size = orig_pvd.space_size
        self.set_size = orig_pvd.set_size
        self.seqnum = orig_pvd.seqnum
        self.log_block_size = orig_pvd.log_block_size
        self.path_tbl_size = orig_pvd.path_tbl_size
        self.path_table_location_le = orig_pvd.path_table_location_le
        self.optional_path_table_location_le = orig_pvd.optional_path_table_location_le
        self.path_table_location_be = orig_pvd.path_table_location_be
        self.optional_path_table_location_be = orig_pvd.optional_path_table_location_be
        # Root dir record is a DirectoryRecord object, and we want this copy to hold
        # onto exactly the same reference as the original
        self.root_dir_record = orig_pvd.root_dir_record
        self.volume_set_identifier = orig_pvd.volume_set_identifier
        # publisher_identifier is a FileOrTextIdentifier object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.publisher_identifier = orig_pvd.publisher_identifier
        # preparer_identifier is a FileOrTextIdentifier object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.preparer_identifier = orig_pvd.preparer_identifier
        # application_identifier is a FileOrTextIdentifier object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.application_identifier = orig_pvd.application_identifier
        self.copyright_file_identifier = orig_pvd.copyright_file_identifier
        self.abstract_file_identifier = orig_pvd.abstract_file_identifier
        self.bibliographic_file_identifier = orig_pvd.bibliographic_file_identifier
        # volume_creation_date is a VolumeDescriptorDate object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.volume_creation_date = orig_pvd.volume_creation_date
        # volume_expiration_date is a VolumeDescriptorDate object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.volume_expiration_date = orig_pvd.volume_expiration_date
        # volume_effective_date is a VolumeDescriptorDate object, and we want this copy to
        # hold onto exactly the same reference as the original
        self.volume_effective_date = orig_pvd.volume_effective_date
        self.file_structure_version = orig_pvd.file_structure_version
        self.application_use = orig_pvd.application_use

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this Primary Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this Primary Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is not yet initialized")

        vol_mod_date = dates.VolumeDescriptorDate()
        vol_mod_date.new(time.time())

        return struct.pack(self.FMT, self.descriptor_type, self.identifier,
                           self.version, 0, self.system_identifier,
                           self.volume_identifier, 0, self.space_size,
                           utils.swab_32bit(self.space_size), b'\x00' * 32,
                           self.set_size, utils.swab_16bit(self.set_size),
                           self.seqnum, utils.swab_16bit(self.seqnum),
                           self.log_block_size, utils.swab_16bit(self.log_block_size),
                           self.path_tbl_size, utils.swab_32bit(self.path_tbl_size),
                           self.path_table_location_le,
                           self.optional_path_table_location_le,
                           utils.swab_32bit(self.path_table_location_be),
                           self.optional_path_table_location_be,
                           self.root_dir_record.record(),
                           self.volume_set_identifier,
                           self.publisher_identifier.record(),
                           self.preparer_identifier.record(),
                           self.application_identifier.record(),
                           self.copyright_file_identifier,
                           self.abstract_file_identifier,
                           self.bibliographic_file_identifier,
                           self.volume_creation_date.record(),
                           vol_mod_date.record(),
                           self.volume_expiration_date.record(),
                           self.volume_effective_date.record(),
                           self.file_structure_version, 0, self.application_use,
                           b"\x00" * 653)

    def track_rr_ce_entry(self, extent, offset, length):
        '''
        Starting tracking a new Rock Ridge Continuation Entry entry in this PVD,
        at the extent, offset, and length provided.  Since Rock Ridge
        Continuation Blocks are shared across multiple Rock Ridge Directory
        Records, the most logical place to track them is in the PVD.  This
        method is expected to be used during parse time, when an extent, offset
        and length are already assigned to the entry.

        Parameters:
         extent - The extent that this Continuation Entry lives at.
         offset - The offset within the extent that this Continuation Entry
                  lives at.
         length - The length of this Continuation Entry.
        Returns:
         The object representing the block in which the Continuation Entry was
         placed in.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is not yet initialized")

        for block in self.rr_ce_blocks:
            if block.extent_location() == extent:
                break
        else:
            # We didn't find it in the list, add it
            block = rockridge.RockRidgeContinuationBlock(extent, self.log_block_size)
            self.rr_ce_blocks.append(block)

        block.track_entry(offset, length)

        return block

    def add_rr_ce_entry(self, length):
        '''
        Adds a new Rock Ridge Continuation Entry to this PVD; see
        track_rr_ce_entry() above for why we track these in the PVD.  This
        method is used to add a new Continuation Entry anywhere it fits in the
        list of Continuation Blocks.  If it doesn't fit in any of the existing
        blocks, a new block for it is allocated.

        Parameters:
         length - The length of the Continuation Entry that should be added.
        Returns:
         A 3-tuple consisting of whether we added a new block, the object
         representing the block that this entry was added to, and the offset
         within the block that the entry was added to.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is not yet initialized")

        added_block = False
        for block in self.rr_ce_blocks:
            offset = block.add_entry(length)
            if offset is not None:
                break
        else:
            # We didn't find a block this would fit in; add one.
            block = rockridge.RockRidgeContinuationBlock(0, self.log_block_size)
            self.rr_ce_blocks.append(block)
            offset = block.add_entry(length)
            added_block = True

        return (added_block, block, offset)

    def clear_rr_ce_entries(self):
        '''
        A method to clear out all of the extent locations of all Rock Ridge
        Continuation Entries that the PVD is tracking.  This can be used to
        reset all data before assigning new data.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Primary Volume Descriptor is not yet initialized")

        for block in self.rr_ce_blocks:
            block.set_extent_location(None)

    def __ne__(self, other):
        return self.descriptor_type != other.descriptor_type or self.identifier != other.identifier or self.version != other.version or self.system_identifier != other.system_identifier or self.volume_identifier != other.volume_identifier or self.space_size != other.space_size or self.set_size != other.set_size or self.seqnum != other.seqnum or self.log_block_size != other.log_block_size or self.path_tbl_size != other.path_tbl_size or self.path_table_location_le != other.path_table_location_le or self.optional_path_table_location_le != other.optional_path_table_location_le or self.path_table_location_be != other.path_table_location_be or self.optional_path_table_location_be != other.optional_path_table_location_be or self.root_dir_record != other.root_dir_record or self.volume_set_identifier != other.volume_set_identifier or self.publisher_identifier != other.publisher_identifier or self.preparer_identifier != other.preparer_identifier or self.application_identifier != other.application_identifier or self.copyright_file_identifier != other.copyright_file_identifier or self.abstract_file_identifier != other.abstract_file_identifier or self.bibliographic_file_identifier != other.bibliographic_file_identifier or self.volume_creation_date != other.volume_creation_date or self.volume_modification_date != other.volume_modification_date or self.volume_expiration_date != other.volume_expiration_date or self.volume_effective_date != other.volume_effective_date or self.file_structure_version != other.file_structure_version or self.application_use != other.application_use


class VolumeDescriptorSetTerminator(object):
    '''
    A class that represents a Volume Descriptor Set Terminator.  The VDST
    signals the end of volume descriptors on the ISO.
    '''
    FMT = "=B5sB2041s"

    def __init__(self):
        self._initialized = False

    def parse(self, vd, extent_loc):
        '''
        A method to parse a Volume Descriptor Set Terminator out of a string.

        Parameters:
         vd - The string to parse.
         extent_loc - The extent this VDST is currently located at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Volume Descriptor Set Terminator already initialized")

        (self.descriptor_type, self.identifier, self.version,
         zero_unused) = struct.unpack_from(self.FMT, vd, 0)

        # According to Ecma-119, 8.3.1, the volume descriptor set terminator
        # type should be 255
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid descriptor type")
        # According to Ecma-119, 8.3.2, the identifier should be "CD001"
        if self.identifier != b'CD001':
            raise pycdlibexception.PyCdlibInvalidISO("Invalid identifier")
        # According to Ecma-119, 8.3.3, the version should be 1
        if self.version != 1:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid version")
        # According to Ecma-119, 8.3.4, the rest of the terminator should be 0;
        # however, we have seen ISOs in the wild that put stuff into this field.
        # Just ignore it.

        self.orig_extent_loc = extent_loc
        self.new_extent_loc = None

        self._initialized = True

    def new(self):
        '''
        A method to create a new Volume Descriptor Set Terminator.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Volume Descriptor Set Terminator already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SET_TERMINATOR
        self.identifier = b"CD001"
        self.version = 1
        self.orig_extent_loc = None
        # This will get set during reshuffle_extents.
        self.new_extent_loc = 0

        self._initialized = True

    def record(self):
        '''
        A method to generate a string representing this Volume Descriptor Set
        Terminator.

        Parameters:
         None.
        Returns:
         String representing this Volume Descriptor Set Terminator.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Volume Descriptor Set Terminator not yet initialized")
        return struct.pack(self.FMT, self.descriptor_type,
                           self.identifier, self.version, b"\x00" * 2041)

    def extent_location(self):
        '''
        A method to get this Volume Descriptor Set Terminator's extent location.

        Parameters:
         None.
        Returns:
         Integer extent location.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Volume Descriptor Set Terminator not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


class BootRecord(object):
    '''
    A class representing an ISO9660 Boot Record.
    '''
    FMT = "=B5sB32s32s1977s"

    def __init__(self):
        self._initialized = False

    def parse(self, vd, extent_loc):
        '''
        A method to parse a Boot Record out of a string.

        Parameters:
         vd - The string to parse the Boot Record out of.
         extent_loc - The extent location this Boot Record is current at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Boot Record already initialized")

        (self.descriptor_type, self.identifier, self.version,
         self.boot_system_identifier, self.boot_identifier,
         self.boot_system_use) = struct.unpack_from(self.FMT, vd, 0)

        # According to Ecma-119, 8.2.1, the boot record type should be 0
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid descriptor type")
        # According to Ecma-119, 8.2.2, the identifier should be "CD001"
        if self.identifier != b'CD001':
            raise pycdlibexception.PyCdlibInvalidISO("Invalid identifier")
        # According to Ecma-119, 8.2.3, the version should be 1
        if self.version != 1:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid version")

        self.orig_extent_loc = extent_loc
        self.new_extent_loc = None

        self._initialized = True

    def new(self, boot_system_id):
        '''
        A method to create a new Boot Record.

        Parameters:
         boot_system_id - The system identifier to associate with this Boot
                          Record.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise Exception("Boot Record already initialized")

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_BOOT_RECORD
        self.identifier = b"CD001"
        self.version = 1
        self.boot_system_identifier = boot_system_id.ljust(32, b'\x00')
        self.boot_identifier = b"\x00" * 32
        self.boot_system_use = b"\x00" * 197  # This will be set later

        self.orig_extent_loc = None
        # This is wrong, but will be corrected at reshuffle_extents time.
        self.new_extent_loc = 0

        self._initialized = True

    def record(self):
        '''
        A method to generate a string representing this Boot Record.

        Parameters:
         None.
        Returns:
         A string representing this Boot Record.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Boot Record not yet initialized")

        return struct.pack(self.FMT, self.descriptor_type, self.identifier,
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
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Boot Record not yet initialized")

        self.boot_system_use = boot_sys_use.ljust(197, b'\x00')

    def extent_location(self):
        '''
        A method to get the extent location of this Boot Record.

        Parameters:
         None.
        Returns:
         Integer extent location of this Boot Record.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Boot Record not yet initialized")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


class SupplementaryVolumeDescriptor(HeaderVolumeDescriptor):
    '''
    A class that represents an ISO9660 Supplementary Volume Descriptor (used
    for Joliet records, among other things).
    '''
    FMT = "=B5sBB32s32sQLL32sHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"

    def __init__(self):
        HeaderVolumeDescriptor.__init__(self)

    def parse(self, vd, data_fp, extent_loc):
        '''
        A method to parse a Supplementary Volume Descriptor from a string.

        Parameters:
         vd - The string to parse the Supplementary Volume Descriptor from.
         data_fp - The file object to associate with the root directory record.
         extent_loc - The extent location of this Supplementary Volume Descriptor.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("Supplementary Volume Descriptor already initialized")

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
         self.application_use, unused3) = struct.unpack_from(self.FMT, vd, 0)

        # According to Ecma-119, 8.5.1, the supplementary volume descriptor type
        # should be 2.
        if self.descriptor_type != VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid supplementary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001".
        if self.identifier != b"CD001":
            raise pycdlibexception.PyCdlibInvalidISO("invalid CD isoIdentification")
        # According to Ecma-119, 8.5.2, the version should be 1.
        if self.version not in [1, 2]:
            raise pycdlibexception.PyCdlibInvalidISO("Invalid supplementary volume descriptor version %d" % self.version)
        # According to Ecma-119, 8.4.5, the first unused field (after the
        # system identifier and volume identifier) should be 0.
        if unused1 != 0:
            raise pycdlibexception.PyCdlibInvalidISO("data in 1st unused field not zero")
        if self.file_structure_version not in [1, 2]:
            raise pycdlibexception.PyCdlibInvalidISO("File structure version expected to be 1")
        if unused2 != 0:
            raise pycdlibexception.PyCdlibInvalidISO("data in 2nd unused field not zero")
        if unused3 != b'\x00' * 653:
            raise pycdlibexception.PyCdlibInvalidISO("data in 3rd unused field not zero")

        # Check to make sure that the little-endian and big-endian versions
        # of the parsed data agree with each other
        if space_size_le != utils.swab_32bit(space_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian space size disagree")
        self.space_size = space_size_le

        if set_size_le != utils.swab_16bit(set_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian set size disagree")
        self.set_size = set_size_le

        if seqnum_le != utils.swab_16bit(seqnum_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian seqnum disagree")
        self.seqnum = seqnum_le

        if logical_block_size_le != utils.swab_16bit(logical_block_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian logical block size disagree")
        self.log_block_size = logical_block_size_le

        if path_table_size_le != utils.swab_32bit(path_table_size_be):
            raise pycdlibexception.PyCdlibInvalidISO("Little-endian and big-endian path table size disagree")
        self.path_tbl_size = path_table_size_le
        self.path_table_num_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2

        self.path_table_location_be = utils.swab_32bit(self.path_table_location_be)

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.parse(pub_ident_str)
        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.parse(prepare_ident_str)
        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.parse(app_ident_str)
        self.volume_creation_date = dates.VolumeDescriptorDate()
        self.volume_creation_date.parse(vol_create_date_str)
        self.volume_modification_date = dates.VolumeDescriptorDate()
        self.volume_modification_date.parse(vol_mod_date_str)
        self.volume_expiration_date = dates.VolumeDescriptorDate()
        self.volume_expiration_date.parse(vol_expire_date_str)
        self.volume_effective_date = dates.VolumeDescriptorDate()
        self.volume_effective_date.parse(vol_effective_date_str)
        self.root_dir_record = dr.DirectoryRecord()
        self.root_dir_record.parse(root_dir_record, data_fp, None)

        self.orig_extent_loc = extent_loc
        self.new_extent_loc = None

        self._initialized = True

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident_str, preparer_ident_str, app_ident_str,
            copyright_file, abstract_file, bibli_file, vol_expire_date,
            app_use, xa, version, escape_sequence):
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
         xa - Whether to embed XA data into the volume descriptor.
         version - What version to assign to the header.
         escape_sequence - The escape sequence to assign to this volume descriptor.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Supplementary Volume Descriptor is already initialized")

        encoding = 'ascii'
        if escape_sequence in [b'%/@', b'%/C', b'%/E']:
            encoding = 'utf-16_be'

        self.descriptor_type = VOLUME_DESCRIPTOR_TYPE_SUPPLEMENTARY
        self.identifier = b"CD001"
        self.version = version
        self.flags = flags

        if len(sys_ident) > 32:
            raise pycdlibexception.PyCdlibInvalidInput("The system identifer has a maximum length of 32")
        self.system_identifier = sys_ident.decode('utf-8').encode(encoding).ljust(32, b' ')

        if len(vol_ident) > 32:
            raise pycdlibexception.PyCdlibInvalidInput("The volume identifier has a maximum length of 32")
        self.volume_identifier = vol_ident.decode('utf-8').encode(encoding).ljust(32, b' ')

        # The space_size is the number of extents (2048-byte blocks) in the
        # ISO.  We know we will at least have the system area (16 extents),
        # the PVD (1 extent), the little endian path table record (2 extents),
        # the big endian path table record (2 extents), and 1 extent for the
        # root directory record, for a total of 22 extents to start with.
        self.space_size = 22
        self.set_size = set_size
        if seqnum > set_size:
            raise pycdlibexception.PyCdlibInvalidInput("Sequence number must be less than or equal to set size")
        self.seqnum = seqnum
        self.log_block_size = log_block_size
        # The path table size is in bytes, and is always at least 10 bytes
        # (for the root directory record).
        self.path_tbl_size = 10
        self.path_table_num_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2
        # By default the Little Endian Path Table record starts at extent 19
        # (right after the Volume Terminator).
        self.path_table_location_le = 19
        # By default the Big Endian Path Table record starts at extent 21
        # (two extents after the Little Endian Path Table Record).
        self.path_table_location_be = 21
        # FIXME: we don't support the optional path table location right now
        self.optional_path_table_location_le = 0
        self.optional_path_table_location_be = 0
        self.root_dir_record = dr.DirectoryRecord()
        self.root_dir_record.new_root(seqnum, self.log_block_size)

        if len(vol_set_ident) > 128:
            raise pycdlibexception.PyCdlibInvalidInput("The maximum length for the volume set identifier is 128")

        self.volume_set_identifier = utils.encode_space_pad(vol_set_ident, 128, encoding)

        self.publisher_identifier = FileOrTextIdentifier()
        self.publisher_identifier.new(utils.encode_space_pad(pub_ident_str, 128, encoding))

        self.preparer_identifier = FileOrTextIdentifier()
        self.preparer_identifier.new(utils.encode_space_pad(preparer_ident_str, 128, encoding))

        self.application_identifier = FileOrTextIdentifier()
        self.application_identifier.new(utils.encode_space_pad(app_ident_str, 128, encoding))

        self.copyright_file_identifier = utils.encode_space_pad(copyright_file, 37, encoding)
        self.abstract_file_identifier = utils.encode_space_pad(abstract_file, 37, encoding)
        self.bibliographic_file_identifier = utils.encode_space_pad(bibli_file, 37, encoding)

        now = time.time()
        self.volume_creation_date = dates.VolumeDescriptorDate()
        self.volume_creation_date.new(now)
        # We make a valid volume modification date here, but it will get
        # overwritten during record().
        self.volume_modification_date = dates.VolumeDescriptorDate()
        self.volume_modification_date.new(now)
        self.volume_expiration_date = dates.VolumeDescriptorDate()
        self.volume_expiration_date.new(vol_expire_date)
        self.volume_effective_date = dates.VolumeDescriptorDate()
        self.volume_effective_date.new(now)
        self.file_structure_version = version

        self.orig_extent_loc = None
        # This is wrong but will be set by reshuffle_extents
        self.new_extent_loc = 0

        self.escape_sequences = escape_sequence.ljust(32, b'\x00')

        if xa:
            if len(app_use) > 141:
                raise pycdlibexception.PyCdlibInvalidInput("Cannot have XA and an app_use of > 140 bytes")
            self.application_use = app_use.ljust(141, b' ')
            self.application_use += b"CD-XA001" + b"\x00" * 18
            self.application_use = self.application_use.ljust(512, b' ')
        else:
            if len(app_use) > 512:
                raise pycdlibexception.PyCdlibInvalidInput("The maximum length for the application use is 512")
            self.application_use = app_use.ljust(512, b' ')

        self._initialized = True

    def record(self):
        '''
        A method to generate a string representing this Supplementary Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this Supplementary Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Supplementary Volume Descriptor is not yet initialized")

        vol_mod_date = dates.VolumeDescriptorDate()
        vol_mod_date.new(time.time())

        return struct.pack(self.FMT, self.descriptor_type, self.identifier,
                           self.version, self.flags, self.system_identifier,
                           self.volume_identifier, 0, self.space_size,
                           utils.swab_32bit(self.space_size), self.escape_sequences,
                           self.set_size, utils.swab_16bit(self.set_size),
                           self.seqnum, utils.swab_16bit(self.seqnum),
                           self.log_block_size, utils.swab_16bit(self.log_block_size),
                           self.path_tbl_size, utils.swab_32bit(self.path_tbl_size),
                           self.path_table_location_le, self.optional_path_table_location_le,
                           utils.swab_32bit(self.path_table_location_be),
                           self.optional_path_table_location_be,
                           self.root_dir_record.record(),
                           self.volume_set_identifier,
                           self.publisher_identifier.record(),
                           self.preparer_identifier.record(),
                           self.application_identifier.record(),
                           self.copyright_file_identifier,
                           self.abstract_file_identifier,
                           self.bibliographic_file_identifier,
                           self.volume_creation_date.record(),
                           vol_mod_date.record(),
                           self.volume_expiration_date.record(),
                           self.volume_effective_date.record(),
                           self.file_structure_version, 0,
                           self.application_use, b'\x00' * 653)


class VersionVolumeDescriptor(object):
    '''
    A class representing a Version Volume Descriptor.  This volume descriptor is
    not mentioned in any of the standards, but is included by genisoimage, so it
    is modeled here.
    '''
    def __init__(self):
        self.orig_extent_loc = None
        self.new_extent_loc = None
        self._initialized = False

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
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Version Volume Descriptor is already initialized")

        self.orig_extent_loc = extent_location
        self._initialized = True

    def new(self):
        '''
        Create a new Version Volume Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Version Volume Descriptor is already initialized")

        self._initialized = True

    def record(self, log_block_size):
        '''
        Generate a string representing this Version Volume Descriptor.  Note that
        right now, this is always a string of zeros.

        Parameters:
         log_block_size - The logical block size to use when generating this string.
        Returns:
         A string representing this Version Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Version Volume Descriptor is not yet initialized")

        return b"\x00" * log_block_size

    def extent_location(self):
        '''
        Get the extent location of this Version Volume Descriptor.

        Parameters:
         None.
        Returns:
         An integer representing the extent location of this Version Volume
         Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError("This Version Volume Descriptor is not yet initialized")

        if self.new_extent_loc is not None:
            return self.new_extent_loc
        return self.orig_extent_loc
