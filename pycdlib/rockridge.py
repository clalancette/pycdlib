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
Classes and utilities to support Rock Ridge extensions.
'''

from __future__ import absolute_import

import struct

import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.dates as dates
import pycdlib.utils as utils

SU_ENTRY_VERSION = 1

class RRSPRecord(object):
    '''
    A class that represents a Rock Ridge Sharing Protocol record.  This record
    indicates that the sharing protocol is in use, and how many bytes to skip
    prior to parsing a Rock Ridge entry out of a directory record.
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Sharing Protocol record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SP record already initialized!")

        (su_len, su_entry_version_unused, check_byte1, check_byte2,
         self.bytes_to_skip) = struct.unpack_from("=BBBBB", rrstr[:7], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if su_len != RRSPRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")
        if check_byte1 != 0xbe or check_byte2 != 0xef:
            raise pycdlibexception.PyCdlibException("Invalid check bytes on rock ridge extension")

        self.initialized = True

    def new(self, bytes_to_skip):
        '''
        Create a new Rock Ridge Sharing Protocol record.

        Parameters:
        bytes_to_skip - The number of bytes to skip.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SP record already initialized!")

        self.bytes_to_skip = bytes_to_skip
        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Sharing Protocol record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SP record not yet initialized!")

        return b"%s%s" % (b'SP', struct.pack("=BBBBB", RRSPRecord.length(), SU_ENTRY_VERSION, 0xbe, 0xef, self.bytes_to_skip))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Sharing Protocol
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 7

class RRRRRecord(object):
    '''
    A class that represents a Rock Ridge Rock Ridge record.  This optional
    record indicates which other Rock Ridge fields are present.
    '''
    def __init__(self):
        self.rr_flags = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Rock Ridge record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("RR record already initialized!")

        (su_len, su_entry_version_unused, self.rr_flags) = struct.unpack_from("=BBB",
                                                                              rrstr[:5], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if su_len != RRRRRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        self.initialized = True

    def new(self):
        '''
        Create a new Rock Ridge Rock Ridge record.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("RR record already initialized!")

        self.rr_flags = 0
        self.initialized = True

    def append_field(self, fieldname):
        '''
        Mark a field as present in the Rock Ridge records.

        Parameters:
         fieldname - The name of the field to mark as present; should be one
                     of "PX", "PN", "SL", "NM", "CL", "PL", "RE", or "TF".
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("RR record not yet initialized!")

        if fieldname == "PX":
            bit = 0
        elif fieldname == "PN":
            bit = 1
        elif fieldname == "SL":
            bit = 2
        elif fieldname == "NM":
            bit = 3
        elif fieldname == "CL":
            bit = 4
        elif fieldname == "PL":
            bit = 5
        elif fieldname == "RE":
            bit = 6
        elif fieldname == "TF":
            bit = 7
        else:
            raise pycdlibexception.PyCdlibException("Unknown RR field name %s" % (fieldname))

        self.rr_flags |= (1 << bit)

    def record(self):
        '''
        Generate a string representing the Rock Ridge Rock Ridge record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("RR record not yet initialized!")

        return b"%s%s" % (b'RR', struct.pack("=BBB", RRRRRecord.length(), SU_ENTRY_VERSION, self.rr_flags))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Rock Ridge
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 5

class RRCERecord(object):
    '''
    A class that represents a Rock Ridge Continuation Entry record.  This
    record represents additional information that did not fit in the standard
    directory record.
    '''
    def __init__(self):
        self.continuation_entry = None
        self.initialized = False

    def parse(self, rrstr, rr_version):
        '''
        Parse a Rock Ridge Continuation Entry record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
         rr_version - The Rock Ridge version to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("CE record already initialized!")

        (su_len, su_entry_version_unused, bl_cont_area_le, bl_cont_area_be,
         offset_cont_area_le, offset_cont_area_be,
         len_cont_area_le, len_cont_area_be) = struct.unpack_from("=BBLLLLLL", rrstr[:28], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if su_len != RRCERecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        if bl_cont_area_le != utils.swab_32bit(bl_cont_area_be):
            raise pycdlibexception.PyCdlibException("CE record big and little endian continuation area do not agree")

        if offset_cont_area_le != utils.swab_32bit(offset_cont_area_be):
            raise pycdlibexception.PyCdlibException("CE record big and little endian continuation area offset do not agree")

        if len_cont_area_le != utils.swab_32bit(len_cont_area_be):
            raise pycdlibexception.PyCdlibException("CE record big and little endian continuation area length do not agree")

        self.continuation_entry = RockRidgeContinuation(rr_version)
        self.continuation_entry.orig_extent_loc = bl_cont_area_le
        self.continuation_entry.continue_offset = offset_cont_area_le
        self.continuation_entry.increment_length(len_cont_area_le)

        self.initialized = True

    def new(self, rr_version):
        '''
        Create a new Rock Ridge Continuation Entry record.

        Parameters:
         rr_version - The Rock Ridge version to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("CE record already initialized!")

        self.continuation_entry = RockRidgeContinuation(rr_version)

        self.initialized = True

    def add_record(self, record_name, obj, length):
        '''
        Set the record named 'record_name' to the input object, and increment
        the length accordingly.

        Parameters:
         record_name - The name of the record to set.
         obj - The object to set the record to.
         length - The amount of space to add to the continuation entry.
        Returns:
         Nothing.
        '''
        setattr(self.continuation_entry, record_name, obj)
        self.continuation_entry.increment_length(length)

    def record(self):
        '''
        Generate a string representing the Rock Ridge Continuation Entry record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("CE record not yet initialized!")

        loc = self.continuation_entry.extent_location()
        offset = self.continuation_entry.offset()
        cont_len = self.continuation_entry.length()

        return b"%s%s" % (b'CE', struct.pack("=BBLLLLLL", RRCERecord.length(),
                                             SU_ENTRY_VERSION, loc, utils.swab_32bit(loc),
                                             offset, utils.swab_32bit(offset),
                                             cont_len, utils.swab_32bit(cont_len)))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Continuation Entry
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 28

class RRPXRecord(object):
    '''
    A class that represents a Rock Ridge POSIX File Attributes record.  This
    record contains information about the POSIX file mode, file links,
    user ID, group ID, and serial number of a directory record.
    '''
    def __init__(self):
        self.posix_file_mode = None
        self.posix_file_links = None
        self.posix_user_id = None
        self.posix_group_id = None
        self.posix_serial_number = None

        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge POSIX File Attributes record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         A string representing the RR version, either 1.09 or 1.12.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PX record already initialized!")

        (su_len, su_entry_version_unused, posix_file_mode_le, posix_file_mode_be,
         posix_file_links_le, posix_file_links_be, posix_file_user_id_le,
         posix_file_user_id_be, posix_file_group_id_le,
         posix_file_group_id_be) = struct.unpack_from("=BBLLLLLLLL", rrstr[:38], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if posix_file_mode_le != utils.swab_32bit(posix_file_mode_be):
            raise pycdlibexception.PyCdlibException("PX record big and little-endian file mode do not agree")

        if posix_file_links_le != utils.swab_32bit(posix_file_links_be):
            raise pycdlibexception.PyCdlibException("PX record big and little-endian file links do not agree")

        if posix_file_user_id_le != utils.swab_32bit(posix_file_user_id_be):
            raise pycdlibexception.PyCdlibException("PX record big and little-endian file user ID do not agree")

        if posix_file_group_id_le != utils.swab_32bit(posix_file_group_id_be):
            raise pycdlibexception.PyCdlibException("PX record big and little-endian file group ID do not agree")

        # In Rock Ridge 1.09, the su_len here should be 36, while for
        # 1.12, the su_len here should be 44.
        if su_len == 36:
            posix_file_serial_number_le = 0
            rr_version = "1.09"
        elif su_len == 44:
            (posix_file_serial_number_le,
             posix_file_serial_number_be) = struct.unpack_from("=LL",
                                                               rrstr[:44], 36)
            if posix_file_serial_number_le != utils.swab_32bit(posix_file_serial_number_be):
                raise pycdlibexception.PyCdlibException("PX record big and little-endian file serial number do not agree")

            rr_version = "1.12"
        else:
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        self.posix_file_mode = posix_file_mode_le
        self.posix_file_links = posix_file_links_le
        self.posix_user_id = posix_file_user_id_le
        self.posix_group_id = posix_file_group_id_le
        self.posix_serial_number = posix_file_serial_number_le

        self.initialized = True

        return rr_version

    def new(self, isdir, symlink_path):
        '''
        Create a new Rock Ridge POSIX File Attributes record.

        Parameters:
         isdir - Whether this new entry is a directory.
         symlink_path - A symlink_path; None if this is not a symlink.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PX record already initialized!")

        if isdir:
            self.posix_file_mode = 0o040555
        elif symlink_path is not None:
            self.posix_file_mode = 0o0120555
        else:
            self.posix_file_mode = 0o0100444

        self.posix_file_links = 1
        self.posix_user_id = 0
        self.posix_group_id = 0
        self.posix_serial_number = 0

        self.initialized = True

    def record(self, rr_version):
        '''
        Generate a string representing the Rock Ridge POSIX File Attributes
        record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("PX record not yet initialized!")

        outlist = [b'PX', struct.pack("=BBLLLLLLLL", RRPXRecord.length(rr_version),
                                      SU_ENTRY_VERSION, self.posix_file_mode,
                                      utils.swab_32bit(self.posix_file_mode),
                                      self.posix_file_links,
                                      utils.swab_32bit(self.posix_file_links),
                                      self.posix_user_id,
                                      utils.swab_32bit(self.posix_user_id),
                                      self.posix_group_id,
                                      utils.swab_32bit(self.posix_group_id))]
        if rr_version == "1.12":
            outlist.append(struct.pack("=LL", self.posix_serial_number,
                                       utils.swab_32bit(self.posix_serial_number)))
        elif rr_version != "1.09":
            raise pycdlibexception.PyCdlibException("Invalid rr_version")

        return b"".join(outlist)

    @staticmethod
    def length(rr_version):
        '''
        Static method to return the length of the Rock Ridge POSIX File
        Attributes record.

        Parameters:
         rr_version - The version of Rock Ridge in use; must be "1.09" or "1.12".
        Returns:
         The length of this record in bytes.
        '''
        if rr_version == "1.09":
            return 36
        elif rr_version == "1.12":
            return 44
        else:
            raise pycdlibexception.PyCdlibException("Invalid rr_version")

class RRERRecord(object):
    '''
    A class that represents a Rock Ridge Extensions Reference record.
    '''
    def __init__(self):
        self.ext_id = None
        self.ext_des = None
        self.ext_src = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Extensions Reference record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("ER record already initialized!")

        (su_len, su_entry_version_unused, len_id, len_des, len_src,
         self.ext_ver) = struct.unpack_from("=BBBBBB", rrstr[:8], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        # Ensure that the length isn't crazy
        if su_len > len(rrstr):
            raise pycdlibexception.PyCdlibException("Length of ER record much too long")

        # Also ensure that the combination of len_id, len_des, and len_src doesn't overrun
        # either su_len or rrstr.
        total_length = len_id + len_des + len_src
        if total_length > su_len or total_length > len(rrstr):
            raise pycdlibexception.PyCdlibException("Combined length of ER ID, des, and src longer than record")

        fmtstr = "=%ds%ds%ds" % (len_id, len_des, len_src)
        (self.ext_id, self.ext_des, self.ext_src) = struct.unpack_from(fmtstr, rrstr, 8)

        self.initialized = True

    def new(self, ext_id, ext_des, ext_src):
        '''
        Create a new Rock Ridge Extensions Reference record.

        Parameters:
         ext_id - The extension identifier to use.
         ext_des - The extension descriptor to use.
         ext_src - The extension specification source to use.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("ER record already initialized!")

        self.ext_id = ext_id
        self.ext_des = ext_des
        self.ext_src = ext_src
        self.ext_ver = 1

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Extensions Reference
        record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("ER record not yet initialized!")

        return b"%s%s%s%s%s" % (b'ER', struct.pack("=BBBBBB", RRERRecord.length(self.ext_id, self.ext_des, self.ext_src), SU_ENTRY_VERSION, len(self.ext_id), len(self.ext_des), len(self.ext_src), self.ext_ver), self.ext_id, self.ext_des, self.ext_src)

    @staticmethod
    def length(ext_id, ext_des, ext_src):
        '''
        Static method to return the length of the Rock Ridge Extensions Reference
        record.

        Parameters:
         ext_id - The extension identifier to use.
         ext_des - The extension descriptor to use.
         ext_src - The extension specification source to use.
        Returns:
         The length of this record in bytes.
        '''
        return 8+len(ext_id)+len(ext_des)+len(ext_src)

class RRESRecord(object):
    '''
    A class that represents a Rock Ridge Extension Selector record.
    '''
    def __init__(self):
        self.extension_sequence = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Extension Selector record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("ES record already initialized!")

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        (su_len, su_entry_version_unused, self.extension_sequence) = struct.unpack_from("=BBB", rrstr[:5], 2)
        if su_len != RRESRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        self.initialized = True

    def new(self, extension_sequence):
        '''
        Create a new Rock Ridge Extension Selector record.

        Parameters:
         extension_sequence - The sequence number of this extension.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("ES record already initialized!")

        self.extension_sequence = extension_sequence
        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Extension Selector record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("ES record not yet initialized!")

        return b"%s%s" % (b'ES', struct.pack("=BBB", RRESRecord.length(), SU_ENTRY_VERSION, self.extension_sequence))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Extensions Selector
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 5

class RRPNRecord(object):
    '''
    A class that represents a Rock Ridge POSIX Device Number record.  This
    record represents a device major and minor special file.
    '''
    def __init__(self):
        self.dev_t_high = None
        self.dev_t_low = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge POSIX Device Number record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PN record already initialized!")

        (su_len, su_entry_version_unused, dev_t_high_le, dev_t_high_be,
         dev_t_low_le, dev_t_low_be) = struct.unpack_from("=BBLLLL", rrstr[:20], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if su_len != RRPNRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        if dev_t_high_le != utils.swab_32bit(dev_t_high_be):
            raise pycdlibexception.PyCdlibException("Dev_t high little-endian does not match big-endian")

        if dev_t_low_le != utils.swab_32bit(dev_t_low_be):
            raise pycdlibexception.PyCdlibException("Dev_t low little-endian does not match big-endian")

        self.dev_t_high = dev_t_high_le
        self.dev_t_low = dev_t_low_le

        self.initialized = True

    def new(self, dev_t_high, dev_t_low):
        '''
        Create a new Rock Ridge POSIX device number record.

        Parameters:
         dev_t_high - The high-order 32-bits of the device number.
         dev_t_low - The low-order 32-bits of the device number.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PN record already initialized!")

        self.dev_t_high = dev_t_high
        self.dev_t_low = dev_t_low

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge POSIX Device Number
        record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("PN record not yet initialized!")

        return b"%s%s" % (b'PN', struct.pack("=BBLLLL", RRPNRecord.length(), SU_ENTRY_VERSION, self.dev_t_high, utils.swab_32bit(self.dev_t_high), self.dev_t_low, utils.swab_32bit(self.dev_t_low)))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge POSIX Device Number
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 20

class RRSLRecord(object):
    '''
    A class that represents a Rock Ridge Symbolic Link record.  This record
    represents some or all of a symbolic link.  For a symbolic link, Rock Ridge
    specifies that each component (part of path separated by /) be in a separate
    component entry, and individual components may be split across multiple
    Symbolic Link records.  This class takes care of all of those details.
    '''
    def __init__(self):
        self.symlink_components = []
        self.flags = 0
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Symbolic Link record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SL record already initialized!")

        (su_len, su_entry_version_unused, self.flags) = struct.unpack_from("=BBB", rrstr[:5], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        cr_offset = 5
        name = b""
        data_len = su_len - 5
        while data_len > 0:
            (cr_flags, len_cp) = struct.unpack_from("=BB", rrstr[:cr_offset+2], cr_offset)

            data_len -= 2
            cr_offset += 2

            if not cr_flags in [0, 1, 2, 4, 8]:
                raise pycdlibexception.PyCdlibException("Invalid Rock Ridge symlink flags 0x%x" % (cr_flags))

            if (cr_flags & (1 << 1) or cr_flags & (1 << 2) or cr_flags &(1 << 3)) and len_cp != 0:
                raise pycdlibexception.PyCdlibException("Rock Ridge symlinks to dot or dotdot should have zero length")

            if (cr_flags & (1 << 1) or cr_flags & (1 << 2) or cr_flags & (1 << 3)) and name != b"":
                raise pycdlibexception.PyCdlibException("Cannot have RockRidge symlink that is both a continuation and dot or dotdot")

            if cr_flags & (1 << 1):
                name += b"."
            elif cr_flags & (1 << 2):
                name += b".."
            elif cr_flags & (1 << 3):
                name += b"/"
            else:
                name += rrstr[cr_offset:cr_offset+len_cp]

            if not cr_flags & (1 << 0):
                self.symlink_components.append(name)
                name = b''

            cr_offset += len_cp
            data_len -= len_cp

        self.initialized = True

    def new(self, symlink_path=None):
        '''
        Create a new Rock Ridge Symbolic Link record.

        Parameters:
         symlink_path - An optional path for the symbolic link.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SL record already initialized!")

        if symlink_path is not None:
            self.symlink_components = symlink_path.split(b'/')

        self.initialized = True

    def add_component(self, symlink_comp):
        '''
        Add a new component to this symlink record.

        Parameters:
         symlink_comp - The string to add to this symlink record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SL record not yet initialized!")

        if (self.current_length() + 2 + len(symlink_comp)) > 255:
            raise pycdlibexception.PyCdlibException("Symlink would be longer than 255")

        self.symlink_components.append(symlink_comp)

    def current_length(self):
        '''
        Calculate the current length of this symlink record.

        Parameters:
         None.
        Returns:
         Length of this symlink record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SL record not yet initialized!")

        return RRSLRecord.length(self.symlink_components)

    def record(self):
        '''
        Generate a string representing the Rock Ridge Symbolic Link record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SL record not yet initialized!")

        outlist = [b'SL', struct.pack("=BBB", RRSLRecord.length(self.symlink_components), SU_ENTRY_VERSION, self.flags)]
        for comp in self.symlink_components:
            if comp == b'.':
                outlist.append(struct.pack("=BB", (1 << 1), 0))
            elif comp == b"..":
                outlist.append(struct.pack("=BB", (1 << 2), 0))
            elif comp == b"/":
                outlist.append(struct.pack("=BB", (1 << 3), 0))
            else:
                outlist.append(struct.pack("=BB", 0, len(comp)))
                outlist.append(comp)

        return b"".join(outlist)

    def name(self):
        '''
        Generate a string that contains all components of the symlink.

        Parameters:
         None
        Returns:
         String containing all components of the symlink.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SL record not yet initialized!")

        return b"".join(self.symlink_components)

    @staticmethod
    def component_length(symlink_component):
        '''
        Static method to compute the length of one symlink component.

        Parameters:
         symlink_component - String representing one symlink component.
        Returns:
         Length of symlink component plus overhead.
        '''
        length = 2
        if symlink_component not in [b'.', b'..', b'/']:
            length += len(symlink_component)

        return length

    @staticmethod
    def length(symlink_components):
        '''
        Static method to return the length of the Rock Ridge Symbolic Link
        record.

        Parameters:
         symlink_components - A list containing a string for each of the
                              symbolic link components.
        Returns:
         The length of this record in bytes.
        '''
        length = 5
        for comp in symlink_components:
            length += RRSLRecord.component_length(comp)
        return length

class RRNMRecord(object):
    '''
    A class that represents a Rock Ridge Alternate Name record.
    '''
    def __init__(self):
        self.initialized = False
        self.posix_name_flags = None
        self.posix_name = b''

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Alternate Name record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("NM record already initialized!")

        (su_len, su_entry_version_unused, self.posix_name_flags) = struct.unpack_from("=BBB", rrstr[:5], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        name_len = su_len - 5
        if (self.posix_name_flags & 0x7) not in [0, 1, 2, 4]:
            raise pycdlibexception.PyCdlibException("Invalid Rock Ridge NM flags")

        if name_len != 0:
            if (self.posix_name_flags & (1 << 1)) or (self.posix_name_flags & (1 << 2)) or (self.posix_name_flags & (1 << 5)):
                raise pycdlibexception.PyCdlibException("Invalid name in Rock Ridge NM entry (0x%x %d)" % (self.posix_name_flags, name_len))
            self.posix_name += rrstr[5:5+name_len]

        self.initialized = True

    def new(self, rr_name):
        '''
        Create a new Rock Ridge Alternate Name record.

        Parameters:
         rr_name - The name for the new record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("NM record already initialized!")

        self.posix_name = rr_name
        self.posix_name_flags = 0

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Alternate Name record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("NM record not yet initialized!")

        return b"%s%s%s" % (b'NM', struct.pack(b"=BBB", RRNMRecord.length(self.posix_name), SU_ENTRY_VERSION, self.posix_name_flags), self.posix_name)

    def set_continued(self):
        '''
        Mark this alternate name record as continued.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("NM record not yet initialized!")

        self.posix_name_flags |= (1 << 0)

    @staticmethod
    def length(rr_name):
        '''
        Static method to return the length of the Rock Ridge Alternate Name
        record.

        Parameters:
         rr_name - The name to use.
        Returns:
         The length of this record in bytes.
        '''
        return 5 + len(rr_name)

class RRCLRecord(object):
    '''
    A class that represents a Rock Ridge Child Link record.  This record
    represents the logical block where a deeply nested directory was relocated
    to.
    '''
    def __init__(self):
        self.child_log_block_num = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Child Link record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("CL record already initialized!")

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        (su_len, su_entry_version_unused, child_log_block_num_le, child_log_block_num_be) = struct.unpack_from("=BBLL", rrstr[:12], 2)
        if su_len != RRCLRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        if child_log_block_num_le != utils.swab_32bit(child_log_block_num_be):
            raise pycdlibexception.PyCdlibException("Little endian block num does not equal big endian; corrupt ISO")
        self.child_log_block_num = child_log_block_num_le

        self.initialized = True

    def new(self):
        '''
        Create a new Rock Ridge Child Link record.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("CL record already initialized!")

        self.child_log_block_num = 0 # This gets set later

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Child Link record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("CL record not yet initialized!")

        return b"%s%s" % (b'CL', struct.pack("=BBLL", RRCLRecord.length(), SU_ENTRY_VERSION, self.child_log_block_num, utils.swab_32bit(self.child_log_block_num)))

    def set_log_block_num(self, bl):
        '''
        Set the logical block number for the child.

        Parameters:
         bl - Logical block number of the child.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("CL record not yet initialized!")

        self.child_log_block_num = bl

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Child Link
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 12

class RRPLRecord(object):
    '''
    A class that represents a Rock Ridge Parent Link record.  This record
    represents the logical block where a deeply nested directory was located
    from.
    '''
    def __init__(self):
        self.parent_log_block_num = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Parent Link record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PL record already initialized!")

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        (su_len, su_entry_version_unused, parent_log_block_num_le, parent_log_block_num_be) = struct.unpack_from("=BBLL", rrstr[:12], 2)
        if su_len != RRPLRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")
        if parent_log_block_num_le != utils.swab_32bit(parent_log_block_num_be):
            raise pycdlibexception.PyCdlibException("Little endian block num does not equal big endian; corrupt ISO")
        self.parent_log_block_num = parent_log_block_num_le

        self.initialized = True

    def new(self):
        '''
        Generate a string representing the Rock Ridge Parent Link record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("PL record already initialized!")

        self.parent_log_block_num = 0 # This will get set later

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Child Link record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("PL record not yet initialized!")

        return b"%s%s" % (b'PL', struct.pack("=BBLL", RRPLRecord.length(), SU_ENTRY_VERSION, self.parent_log_block_num, utils.swab_32bit(self.parent_log_block_num)))

    def set_log_block_num(self, bl):
        '''
        Set the logical block number for the parent.

        Parameters:
         bl - Logical block number of the parent.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("PL record not yet initialized!")

        self.parent_log_block_num = bl

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Parent Link
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 12

class RRTFRecord(object):
    '''
    A class that represents a Rock Ridge Time Stamp record.  This record
    represents the creation timestamp, the access time timestamp, the
    modification time timestamp, the attribute change time timestamp, the
    backup time timestamp, the expiration time timestamp, and the effective time
    timestamp.  Each of the timestamps can be selectively enabled or disabled.
    Additionally, the timestamps can be configured to be Directory Record
    style timestamps (7 bytes) or Volume Descriptor style timestamps (17 bytes).
    '''
    def __init__(self):
        self.creation_time = None
        self.access_time = None
        self.modification_time = None
        self.attribute_change_time = None
        self.backup_time = None
        self.expiration_time = None
        self.effective_time = None
        self.time_flags = None
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Time Stamp record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("TF record already initialized!")

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        (su_len, su_entry_version_unused, self.time_flags,) = struct.unpack_from("=BBB", rrstr[:5], 2)
        if su_len < 5:
            raise pycdlibexception.PyCdlibException("Not enough bytes in the TF record")

        tflen = 7
        datetype = dates.DirectoryRecordDate
        if self.time_flags & (1 << 7):
            tflen = 17
            datetype = dates.VolumeDescriptorDate
        tmp = 5
        if self.time_flags & (1 << 0):
            self.creation_time = datetype()
            self.creation_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 1):
            self.access_time = datetype()
            self.access_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 2):
            self.modification_time = datetype()
            self.modification_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 3):
            self.attribute_change_time = datetype()
            self.attribute_change_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 4):
            self.backup_time = datetype()
            self.backup_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 5):
            self.expiration_time = datetype()
            self.expiration_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen
        if self.time_flags & (1 << 6):
            self.effective_time = datetype()
            self.effective_time.parse(rrstr[tmp:tmp+tflen])
            tmp += tflen

        self.initialized = True

    def new(self, time_flags):
        '''
        Create a new Rock Ridge Time Stamp record.

        Parameters:
         time_flags - The flags to use for this time stamp record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("TF record already initialized!")

        self.time_flags = time_flags

        datetype = dates.DirectoryRecordDate
        if self.time_flags & (1 << 7):
            datetype = dates.VolumeDescriptorDate

        if self.time_flags & (1 << 0):
            self.creation_time = datetype()
            self.creation_time.new()
        if self.time_flags & (1 << 1):
            self.access_time = datetype()
            self.access_time.new()
        if self.time_flags & (1 << 2):
            self.modification_time = datetype()
            self.modification_time.new()
        if self.time_flags & (1 << 3):
            self.attribute_change_time = datetype()
            self.attribute_change_time.new()
        if self.time_flags & (1 << 4):
            self.backup_time = datetype()
            self.backup_time.new()
        if self.time_flags & (1 << 5):
            self.expiration_time = datetype()
            self.expiration_time.new()
        if self.time_flags & (1 << 6):
            self.effective_time = datetype()
            self.effective_time.new()

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Time Stamp record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("TF record not yet initialized!")

        outlist = [b'TF', struct.pack("=BBB", RRTFRecord.length(self.time_flags), SU_ENTRY_VERSION, self.time_flags)]
        if self.creation_time is not None:
            outlist.append(self.creation_time.record())
        if self.access_time is not None:
            outlist.append(self.access_time.record())
        if self.modification_time is not None:
            outlist.append(self.modification_time.record())
        if self.attribute_change_time is not None:
            outlist.append(self.attribute_change_time.record())
        if self.backup_time is not None:
            outlist.append(self.backup_time.record())
        if self.expiration_time is not None:
            outlist.append(self.expiration_time.record())
        if self.effective_time is not None:
            outlist.append(self.effective_time.record())

        return b"".join(outlist)

    @staticmethod
    def length(time_flags):
        '''
        Static method to return the length of the Rock Ridge Time Stamp
        record.

        Parameters:
         time_flags - Integer representing the flags to use.
        Returns:
         The length of this record in bytes.
        '''
        tf_each_size = 7
        if time_flags & (1 << 7):
            tf_each_size = 17
        tf_num = 0
        for i in range(0, 7):
            if time_flags & (1 << i):
                tf_num += 1

        return 5 + tf_each_size*tf_num

class RRSFRecord(object):
    '''
    A class that represents a Rock Ridge Sparse File record.  This record
    represents the full file size of a sparsely-populated file.
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Sparse File record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SF record already initialized!")

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        (su_len, su_entry_version_unused, virtual_file_size_high_le,
         virtual_file_size_high_be, virtual_file_size_low_le,
         virtual_file_size_low_be, self.table_depth) = struct.unpack_from("=BBLLLLB", rrstr[:21], 2)
        if su_len != RRSFRecord.length():
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        if virtual_file_size_high_le != utils.swab_32bit(virtual_file_size_high_be):
            raise pycdlibexception.PyCdlibException("Virtual file size high little-endian does not match big-endian")

        if virtual_file_size_low_le != utils.swab_32bit(virtual_file_size_low_be):
            raise pycdlibexception.PyCdlibException("Virtual file size low little-endian does not match big-endian")

        self.virtual_file_size_high = virtual_file_size_high_le
        self.virtual_file_size_low = virtual_file_size_low_le

        self.initialized = True

    def new(self, file_size_high, file_size_low, table_depth):
        '''
        Create a new Rock Ridge Sparse File record.

        Parameters:
         file_size_high - The high-order 32-bits of the file size.
         file_size_low - The low-order 32-bits of the file size.
         table_depth - The maximum virtual file size.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("SF record already initialized!")

        self.virtual_file_size_high = file_size_high
        self.virtual_file_size_low = file_size_low
        self.table_depth = table_depth

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Sparse File record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("SF record not yet initialized!")

        return b"%s%s" % (b'SF', struct.pack("=BBLLLLB", RRSFRecord.length(), SU_ENTRY_VERSION, self.virtual_file_size_high, utils.swab_32bit(self.virtual_file_size_high), self.virtual_file_size_low, utils.swab_32bit(self.virtual_file_size_low), self.table_depth))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Sparse File
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 21

class RRRERecord(object):
    '''
    A class that represents a Rock Ridge Relocated Directory record.  This
    record is used to mark an entry as having been relocated because it was
    deeply nested.
    '''
    def __init__(self):
        self.initialized = False

    def parse(self, rrstr):
        '''
        Parse a Rock Ridge Relocated Directory record out of a string.

        Parameters:
         rrstr - The string to parse the record out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("RE record already initialized!")

        (su_len, su_entry_version_unused) = struct.unpack_from("=BB", rrstr[:4], 2)

        # We assume that the caller has already checked the su_entry_version,
        # so we don't bother.

        if su_len != 4:
            raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")

        self.initialized = True

    def new(self):
        '''
        Create a new Rock Ridge Relocated Directory record.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("RE record already initialized!")

        self.initialized = True

    def record(self):
        '''
        Generate a string representing the Rock Ridge Relocated Directory
        record.

        Parameters:
         None.
        Returns:
         String containing the Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("RE record not yet initialized")

        return b"%s%s" % (b'RE', struct.pack("=BB", RRRERecord.length(), SU_ENTRY_VERSION))

    @staticmethod
    def length():
        '''
        Static method to return the length of the Rock Ridge Relocated Directory
        record.

        Parameters:
         None.
        Returns:
         The length of this record in bytes.
        '''
        return 4

# This is the class that implements the Rock Ridge extensions for PyCdlib.  The
# Rock Ridge extensions are a set of extensions for embedding POSIX semantics
# on an ISO9660 filesystem.  Rock Ridge works by utilizing the "System Use"
# area of the directory record to store additional metadata about files.  This
# includes things like POSIX users, groups, ctime, mtime, atime, etc., as well
# as the ability to have directory structures deeper than 8 and filenames longer
# than 8.3.  Rock Ridge depends on the System Use and Sharing Protocol (SUSP),
# which defines some standards on how to use the System Area.
#
# A note about versions.  PyCdlib implements version 1.12 of SUSP.  It implements
# both version 1.09 and 1.12 of Rock Ridge itself.  This is slightly strange,
# but genisoimage (which is what pycdlib compares itself against) implements 1.09,
# so we keep support for both.
class RockRidgeBase(object):
    '''
    A base class representing Rock Ridge entries; both RockRidge and
    RockRidgeContinuation inherit from this class.
    '''
    def __init__(self):
        self.sp_record = None
        self.rr_record = None
        self.ce_record = None
        self.px_record = None
        self.er_record = None
        self.es_record = None
        self.pn_record = None
        self.sl_records = []
        self.nm_record = None
        self.cl_record = None
        self.pl_record = None
        self.tf_record = None
        self.sf_record = None
        self.re_record = None
        self.child_link = None
        self.parent_link = None
        self.rr_version = None
        self.initialized = False

    def _parse(self, record, bytes_to_skip, is_first_dir_record_of_root):
        '''
        Internal method to parse a rock ridge record.

        Parameters:
         record - The record to parse.
         bytes_to_skip - The number of bytes to skip at the beginning of the
                         record.
         is_first_dir_record_of_root - Whether this is the first directory
                                       record of the root directory record;
                                       certain Rock Ridge entries are only
                                       valid there.
        Returns:
         Nothing.
        '''
        self.bytes_to_skip = bytes_to_skip
        offset = 0 + bytes_to_skip
        left = len(record)
        while True:
            if left == 0:
                break
            elif left == 1:
                # There may be a padding byte on the end.
                if bytes(bytearray([record[offset]])) != b'\x00':
                    raise pycdlibexception.PyCdlibException("Invalid pad byte")
                break
            elif left < 4:
                raise pycdlibexception.PyCdlibException("Not enough bytes left in the System Use field")

            (rtype, su_len, su_entry_version) = struct.unpack_from("=2sBB", record[:offset+4], offset)
            if su_entry_version != SU_ENTRY_VERSION:
                raise pycdlibexception.PyCdlibException("Invalid RR version %d!" % su_entry_version)

            if rtype == b'SP':
                if left < 7 or not is_first_dir_record_of_root:
                    raise pycdlibexception.PyCdlibException("Invalid SUSP SP record")

                # OK, this is the first Directory Record of the root
                # directory, which means we should check it for the SUSP/RR
                # extension, which is exactly 7 bytes and starts with 'SP'.

                self.sp_record = RRSPRecord()
                self.sp_record.parse(record[offset:])
            elif rtype == b'RR':
                self.rr_record = RRRRRecord()
                self.rr_record.parse(record[offset:])
                # The RR Record only exists in the 1.09 specification.  However,
                # we have seen ISOs in the wild (OpenSolaris 2008) that put an
                # RR Record into a 1.12 ISO.  Therefore, if no previous version
                # has been seen, then we assign this to version 1.09.  If a
                # previous version has been seen, and is 1.12, then we don't
                # downgrade it, but just leave it as 1.12.
                if self.rr_version is None:
                    self.rr_version = "1.09"
            elif rtype == b'CE':
                self.ce_record = RRCERecord()
                self.ce_record.parse(record[offset:], self.rr_version)
            elif rtype == b'PX':
                self.px_record = RRPXRecord()
                version = self.px_record.parse(record[offset:])
                # See the comment above in the RR handling for why the logic
                # is as follows.
                if self.rr_version is None:
                    self.rr_version = version
                else:
                    if self.rr_version == "1.09" and version == "1.12":
                        self.rr_version = "1.12"
                    elif self.rr_version != version:
                        raise pycdlibexception.PyCdlibException("PX record doesn't agree with Rock Ridge version")
            elif rtype == b'PD':
                # no work to do here
                pass
            elif rtype == b'ST':
                if su_len != 4:
                    raise pycdlibexception.PyCdlibException("Invalid length on rock ridge extension")
            elif rtype == b'ER':
                self.er_record = RRERRecord()
                self.er_record.parse(record[offset:])
            elif rtype == b'ES':
                self.es_record = RRESRecord()
                self.es_record.parse(record[offset:])
            elif rtype == b'PN':
                self.pn_record = RRPNRecord()
                self.pn_record.parse(record[offset:])
            elif rtype == b'SL':
                new_sl_record = RRSLRecord()
                new_sl_record.parse(record[offset:])
                self.sl_records.append(new_sl_record)
            elif rtype == b'NM':
                self.nm_record = RRNMRecord()
                self.nm_record.parse(record[offset:])
            elif rtype == b'CL':
                self.cl_record = RRCLRecord()
                self.cl_record.parse(record[offset:])
            elif rtype == b'PL':
                self.pl_record = RRPLRecord()
                self.pl_record.parse(record[offset:])
            elif rtype == b'RE':
                self.re_record = RRRERecord()
                self.re_record.parse(record[offset:])
            elif rtype == b'TF':
                self.tf_record = RRTFRecord()
                self.tf_record.parse(record[offset:])
            elif rtype == b'SF':
                self.sf_record = RRSFRecord()
                self.sf_record.parse(record[offset:])
            else:
                raise pycdlibexception.PyCdlibException("Unknown SUSP record")
            offset += su_len
            left -= su_len

        if self.rr_version is None:
            # If we didn't see either the RR record or the PX record, we assume
            # that this is a 1.12 version of Rock Ridge.
            self.rr_version = "1.12"
        self.su_entry_version = 1
        self.initialized = True

    def record(self):
        '''
        Return a string representing the Rock Ridge entry.

        Parameters:
         None.
        Returns:
         A string representing the Rock Ridge entry.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        outlist = []
        if self.sp_record is not None:
            outlist.append(self.sp_record.record())

        if self.rr_record is not None:
            outlist.append(self.rr_record.record())

        if self.nm_record is not None:
            outlist.append(self.nm_record.record())

        if self.px_record is not None:
            outlist.append(self.px_record.record(self.rr_version))

        for sl_record in self.sl_records:
            outlist.append(sl_record.record())

        if self.tf_record is not None:
            outlist.append(self.tf_record.record())

        if self.cl_record is not None:
            outlist.append(self.cl_record.record())

        if self.pl_record is not None:
            outlist.append(self.pl_record.record())

        if self.re_record is not None:
            outlist.append(self.re_record.record())

        if self.er_record is not None:
            outlist.append(self.er_record.record())

        if self.ce_record is not None:
            outlist.append(self.ce_record.record())

        return b"".join(outlist)

class RockRidgeContinuation(RockRidgeBase):
    '''
    A class representing a Rock Ridge continuation entry (inherits from
    RockRigeBase).
    '''
    def __init__(self, rr_version):
        RockRidgeBase.__init__(self)

        # The new extent location will be set by _reshuffle_extents().
        self.orig_extent_loc = None
        self.new_extent_loc = None

        # The offset will get updated during _reshuffle_extents().
        self.continue_offset = 0

        self.continue_length = 0

        self.su_entry_version = 1

        self.rr_version = rr_version

        self.initialized = True

    def extent_location(self):
        '''
        Get the extent location of this Rock Ridge Continuation entry.

        Parameters:
         None.
        Returns:
         An integer extent location for this continuation entry.
        '''
        if self.new_extent_loc is None and self.orig_extent_loc is None:
            raise pycdlibexception.PyCdlibException("No extent assigned to Rock Ridge Continuation!")

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def offset(self):
        '''
        Get the offset from the beginning of the extent for this Rock Ridge
        Continuation entry.

        Parameters:
         None.
        Returns:
         An integer representing the offset from the beginning of the extent.
        '''
        return self.continue_offset

    def length(self):
        '''
        Get the length of this continuation entry.

        Parameters:
         None.
        Returns:
         An integer representing the length of this continuation entry.
        '''
        return self.continue_length

    def increment_length(self, length):
        '''
        Add a certain amount to the length of this continuation entry.

        Parameters:
         length - The length to add to this continuation entry.
        Returns:
         Nothing.
        '''
        self.continue_length += length

    def parse(self, record, bytes_to_skip):
        '''
        Parse a Rock Ridge continuation entry out of a string.

        Parameters:
         record - The string to parse.
         bytes_to_skip - The number of bytes to skip before parsing.
        Returns:
         Nothing.
        '''
        self.new_extent_loc = None

        self._parse(record, bytes_to_skip, False)

class RockRidge(RockRidgeBase):
    '''
    A class representing a Rock Ridge entry.
    '''
    def parse(self, record, is_first_dir_record_of_root, bytes_to_skip):
        '''
        A method to parse a rock ridge record.

        Parameters:
         record - The record to parse.
         is_first_dir_record_of_root - Whether this is the first directory
                                       record of the root directory record;
                                       certain Rock Ridge entries are only
                                       valid there.
         bytes_to_skip - The number of bytes to skip at the beginning of the
                         record.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension already initialized")

        self._parse(record, bytes_to_skip, is_first_dir_record_of_root)

    def new(self, is_first_dir_record_of_root, rr_name, isdir, symlink_path,
            rr_version, rr_relocated_child, rr_relocated, rr_relocated_parent,
            bytes_to_skip, curr_dr_len):
        '''
        Create a new Rock Ridge record.

        Parameters:
         is_first_dir_record_of_root - Whether this is the first directory
                                       record of the root directory record;
                                       certain Rock Ridge entries are only
                                       valid there.
         rr_name - The alternate name for this Rock Ridge entry.
         isdir - Whether this Rock Ridge entry is for a directory or not.
         symlink_path - The path to the target of the symlink, or None if this
                        is not a symlink.
         rr_version - The version of Rock Ridge to use; must be "1.09"
                      or "1.12".
         rr_relocated_child - Whether this is a relocated child entry.
         rr_relocated - Whether this is a relocated entry.
         rr_relocated_parent - Whether this is a relocated parent entry.
         bytes_to_skip - The number of bytes to skip for the record.
         curr_dr_len - The current length of the directory record; this is used
                       when figuring out whether a continuation entry is needed.
        Returns:
         The length of the directory record after the Rock Ridge extension has
         been added.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension already initialized")

        if rr_version != "1.09" and rr_version != "1.12":
            raise pycdlibexception.PyCdlibException("Only Rock Ridge versions 1.09 and 1.12 are implemented")

        self.rr_version = rr_version

        ALLOWED_DR_SIZE = 254
        TF_FLAGS = 0x0e
        EXT_ID = b"RRIP_1991A"
        EXT_DES = b"THE ROCK RIDGE INTERCHANGE PROTOCOL PROVIDES SUPPORT FOR POSIX FILE SYSTEM SEMANTICS"
        EXT_SRC = b"PLEASE CONTACT DISC PUBLISHER FOR SPECIFICATION SOURCE.  SEE PUBLISHER IDENTIFIER IN PRIMARY VOLUME DESCRIPTOR FOR CONTACT INFORMATION."

        class dr_len(object):
            '''
            An internal class to make the directory record length have the same
            interface as a continuation entry.
            '''
            def __init__(self, _length):
                self._length = _length

            def length(self):
                '''
                Get the length of the directory record.

                Parameters:
                 None.
                Returns:
                 An integer representing the length of the directory record.
                '''
                return self._length

            def increment_length(self, _length):
                '''
                Add a certain amount to the length of the directory record.

                Parameters:
                 length - The length to add to the directory record.
                Returns:
                 Nothing.
                '''
                self._length += _length

        self.su_entry_version = 1

        # First we calculate the total length that this RR extension will take.
        # If it fits into the current DirectoryRecord, we stuff it directly in
        # here, and we are done.  If not, we know we'll have to add a
        # continuation entry.
        tmp_dr_len = curr_dr_len

        if is_first_dir_record_of_root:
            tmp_dr_len += RRSPRecord.length()

        if rr_version == "1.09":
            tmp_dr_len += RRRRRecord.length()

        if rr_name is not None:
            tmp_dr_len += RRNMRecord.length(rr_name)

        tmp_dr_len += RRPXRecord.length(self.rr_version)

        if symlink_path is not None:
            tmp_dr_len += RRSLRecord.length(symlink_path.split(b'/'))

        tmp_dr_len += RRTFRecord.length(TF_FLAGS)

        if rr_relocated_child:
            tmp_dr_len += RRCLRecord.length()

        if rr_relocated:
            tmp_dr_len += RRRERecord.length()

        if rr_relocated_parent:
            tmp_dr_len += RRPLRecord.length()

        if is_first_dir_record_of_root:
            tmp_dr_len += RRERRecord.length(EXT_ID, EXT_DES, EXT_SRC)

        this_dr_len = dr_len(curr_dr_len)

        if tmp_dr_len > ALLOWED_DR_SIZE:
            self.ce_record = RRCERecord()
            self.ce_record.new(self.rr_version)
            this_dr_len.increment_length(RRCERecord.length())

        # For SP record
        if is_first_dir_record_of_root:
            new_sp = RRSPRecord()
            new_sp.new(bytes_to_skip)
            thislen = RRSPRecord.length()
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.add_record('sp_record', new_sp, thislen)
            else:
                self.sp_record = new_sp
                this_dr_len.increment_length(thislen)

        # For RR record
        if rr_version == "1.09":
            new_rr = RRRRRecord()
            new_rr.new()
            thislen = RRRRRecord.length()
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.add_record('rr_record', new_rr, thislen)
            else:
                self.rr_record = new_rr
                this_dr_len.increment_length(thislen)

        # For NM record
        if rr_name is not None:
            if this_dr_len.length() + RRNMRecord.length(rr_name) > ALLOWED_DR_SIZE:
                # The length we are putting in this object (as opposed to
                # the continuation entry) is the maximum, minus how much is
                # already in the DR, minus 5 for the NM metadata.
                # FIXME: if len_here is 0, we shouldn't bother with the local
                # NM record.
                # FIXME: if the name is 255, and we are near the end of a block,
                # the name could spill into a follow-on continuation block.
                len_here = ALLOWED_DR_SIZE - this_dr_len.length() - 5
                self.nm_record = RRNMRecord()
                self.nm_record.new(rr_name[:len_here])
                self.nm_record.set_continued()
                this_dr_len.increment_length(RRNMRecord.length(rr_name[:len_here]))

                self.ce_record.continuation_entry.nm_record = RRNMRecord()
                self.ce_record.continuation_entry.nm_record.new(rr_name[len_here:])
                self.ce_record.continuation_entry.increment_length(RRNMRecord.length(rr_name[len_here:]))
            else:
                self.nm_record = RRNMRecord()
                self.nm_record.new(rr_name)
                this_dr_len.increment_length(RRNMRecord.length(rr_name))

            if self.rr_record is not None:
                self.rr_record.append_field("NM")

        # For PX record
        new_px = RRPXRecord()
        new_px.new(isdir, symlink_path)
        thislen = RRPXRecord.length(self.rr_version)
        if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
            self.ce_record.add_record('px_record', new_px, thislen)
        else:
            self.px_record = new_px
            this_dr_len.increment_length(thislen)

        if self.rr_record is not None:
            self.rr_record.append_field("PX")

        # For SL record
        if symlink_path is not None:
            curr_sl = RRSLRecord()
            curr_sl.new()
            if this_dr_len.length() + 5 + 2 + 1 < ALLOWED_DR_SIZE:
                self.sl_records.append(curr_sl)
                meta_record_len = this_dr_len
            else:
                self.ce_record.continuation_entry.sl_records.append(curr_sl)
                meta_record_len = self.ce_record.continuation_entry

            meta_record_len.increment_length(5)

            for comp in symlink_path.split(b'/'):
                if curr_sl.current_length() + 2 + len(comp) < 255:
                    # OK, this entire component fits into this symlink record,
                    # so add it.
                    curr_sl.add_component(comp)
                    meta_record_len.increment_length(RRSLRecord.component_length(comp))
                elif curr_sl.current_length() + 2 + 1 < 255:
                    # OK, at least part of this component fits into this symlink
                    # record, so add it, then add another one.
                    len_here = 255 - curr_sl.current_length() - 2
                    curr_sl.add_component(comp[:len_here])
                    meta_record_len.increment_length(RRSLRecord.component_length(comp[:len_here]))

                    curr_sl = RRSLRecord()
                    curr_sl.new(comp[len_here:])
                    self.ce_record.continuation_entry.sl_records.append(curr_sl)
                    meta_record_len = self.ce_record.continuation_entry
                    meta_record_len.increment_length(5 + RRSLRecord.component_length(comp[len_here:]))
                else:
                    # None of the this component fits into this symlink record,
                    # so add a continuation one.
                    curr_sl = RRSLRecord()
                    curr_sl.new(comp)
                    self.ce_record.continuation_entry.sl_records.append(curr_sl)
                    meta_record_len = self.ce_record.continuation_entry
                    meta_record_len.increment_length(5 + RRSLRecord.component_length(comp))

            if self.rr_record is not None:
                self.rr_record.append_field("SL")

        # For TF record
        new_tf = RRTFRecord()
        new_tf.new(TF_FLAGS)
        thislen = RRTFRecord.length(TF_FLAGS)
        if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
            self.ce_record.add_record('tf_record', new_tf, thislen)
        else:
            self.tf_record = new_tf
            this_dr_len.increment_length(thislen)

        if self.rr_record is not None:
            self.rr_record.append_field("TF")

        # For CL record
        if rr_relocated_child:
            new_cl = RRCLRecord()
            new_cl.new()
            thislen = RRCLRecord.length()
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.continuation_entry.cl_record = new_cl
                self.ce_record.continuation_entry.increment_length(thislen)
            else:
                self.cl_record = new_cl
                this_dr_len.increment_length(thislen)

        # For RE record
        if rr_relocated:
            new_re = RRRERecord()
            new_re.new()
            thislen = RRRERecord.length()
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.continuation_entry.re_record = new_re
                self.ce_record.continuation_entry.increment_length(thislen)
            else:
                self.re_record = new_re
                this_dr_len.increment_length(thislen)

        # For PL record
        if rr_relocated_parent:
            new_pl = RRPLRecord()
            new_pl.new()
            thislen = RRPLRecord.length()
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.continuation_entry.pl_record = new_pl
                self.ce_record.continuation_entry.increment_length(thislen)
            else:
                self.pl_record = new_pl
                this_dr_len.increment_length(thislen)

        # For ER record
        if is_first_dir_record_of_root:
            new_er = RRERRecord()
            new_er.new(EXT_ID, EXT_DES, EXT_SRC)
            thislen = RRERRecord.length(EXT_ID, EXT_DES, EXT_SRC)
            if this_dr_len.length() + thislen > ALLOWED_DR_SIZE:
                self.ce_record.add_record('er_record', new_er, thislen)
            else:
                self.er_record = new_er
                this_dr_len.increment_length(thislen)

        self.initialized = True

        this_dr_len.increment_length(this_dr_len.length() % 2)

        return this_dr_len.length()

    def add_to_file_links(self):
        '''
        Increment the number of POSIX file links on this entry by one.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.px_record is None:
            if self.ce_record is None:
                raise pycdlibexception.PyCdlibException("No Rock Ridge file links and no continuation entry")
            self.ce_record.continuation_entry.px_record.posix_file_links += 1
        else:
            self.px_record.posix_file_links += 1

    def remove_from_file_links(self):
        '''
        Decrement the number of POSIX file links on this entry by one.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.px_record is None:
            if self.ce_record is None:
                raise pycdlibexception.PyCdlibException("No Rock Ridge file links and no continuation entry")
            self.ce_record.continuation_entry.px_record.posix_file_links -= 1
        else:
            self.px_record.posix_file_links -= 1

    def copy_file_links(self, src):
        '''
        Copy the number of file links from the source Rock Ridge entry into
        this Rock Ridge entry.

        Parameters:
         src - The source Rock Ridge entry to copy from.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        # First, get the src data
        if src.px_record is None:
            if src.ce_record is None:
                raise pycdlibexception.PyCdlibException("No Rock Ridge file links and no continuation entry")
            num_links = src.ce_record.continuation_entry.px_record.posix_file_links
        else:
            num_links = src.px_record.posix_file_links

        # Now apply it to this record.
        if self.px_record is None:
            if self.ce_record is None:
                raise pycdlibexception.PyCdlibException("No Rock Ridge file links and no continuation entry")
            self.ce_record.continuation_entry.px_record.posix_file_links = num_links
        else:
            self.px_record.posix_file_links = num_links

    def name(self):
        '''
        Get the alternate name from this Rock Ridge entry.

        Parameters:
         None.
        Returns:
         The alternate name from this Rock Ridge entry.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        outlist = []
        if self.nm_record is not None:
            outlist.append(self.nm_record.posix_name)
        if self.ce_record is not None and self.ce_record.continuation_entry.nm_record is not None:
            outlist.append(self.ce_record.continuation_entry.nm_record.posix_name)

        return b"".join(outlist)

    def is_symlink(self):
        '''
        Determine whether this Rock Ridge entry describes a symlink.

        Parameters:
         None.
        Returns:
         True if this Rock Ridge entry describes a symlink, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.sl_records:
            return True

        if self.ce_record is not None and self.ce_record.continuation_entry.sl_records:
            return True

        return False

    def symlink_path(self):
        '''
        Get the path as a string of the symlink target of this Rock Ridge entry
        (if this is a symlink).

        Parameters:
         None.
        Returns:
         Symlink path as a string.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if not self.sl_records or (self.ce_record is not None and not self.ce_record.continuation_entry.sl_records):
            raise pycdlibexception.PyCdlibException("Entry is not a symlink!")

        recs = self.sl_records
        if self.ce_record is not None:
            recs += self.ce_record.continuation_entry.sl_records

        outlist = []
        for rec in recs:
            outlist.append(rec.name())

        return b"/".join(outlist)

    def has_child_link_record(self):
        '''
        Determine whether this Rock Ridge entry has a child link record (used
        for relocating deep directory records).

        Parameters:
         None.
        Returns:
         True if this Rock Ridge entry has a child link record, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        ret = self.cl_record is not None
        if self.ce_record is not None:
            ret = ret or self.ce_record.continuation_entry.cl_record is not None

        return ret

    def has_parent_link_record(self):
        '''
        Determine whether this Rock Ridge entry has a parent link record (used
        for relocating deep directory records).

        Parameters:
         None:
        Returns:
         True if this Rock Ridge entry has a parent link record, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        ret = self.pl_record is not None
        if self.ce_record is not None:
            ret = ret or self.ce_record.continuation_entry.pl_record is not None

        return ret

    def relocated_record(self):
        '''
        Determine whether this Rock Ridge entry has a relocated record (used for
        relocating deep directory records).

        Parameters:
         None.
        Returns:
         True if this Rock Ridge entry has a relocated record, False otherwise.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        ret = self.re_record is not None
        if self.ce_record is not None:
            ret = ret or self.ce_record.continuation_entry.re_record is not None

        return ret

    def update_child_link(self):
        '''
        Update the logical extent number stored in the child link record (if
        there is one), from the directory record entry that was stored in
        the child_link member.  This is used at the end of reshuffling extents
        to properly update the child link records.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.child_link is None:
            raise pycdlibexception.PyCdlibException("No child link found!")

        if self.cl_record is not None:
            self.cl_record.set_log_block_num(self.child_link.extent_location())
        else:
            if self.ce_record is not None and self.ce_record.continuation_entry.cl_record is not None:
                self.ce_record.continuation_entry.cl_record.set_log_block_num(self.child_link.extent_location())
            else:
                raise pycdlibexception.PyCdlibException("Could not find child link record!")

    def update_parent_link(self):
        '''
        Update the logical extent number stored in the parent link record (if
        there is one), from the directory record entry that was stored in
        the parent_link member.  This is used at the end of reshuffling extents
        to properly update the parent link records.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.parent_link is None:
            raise pycdlibexception.PyCdlibException("No parent link found!")

        if self.pl_record is not None:
            self.pl_record.set_log_block_num(self.parent_link.extent_location())
        else:
            if self.ce_record is not None and self.ce_record.continuation_entry.pl_record is not None:
                self.ce_record.continuation_entry.pl_record.set_log_block_num(self.parent_link.extent_location())
            else:
                raise pycdlibexception.PyCdlibException("Could not find parent link record!")

    def child_link_block_num(self):
        '''
        Fetch the extent number of the child link for this Rock Ridge record
        if one exists.

        Parameters:
         None.
        Returns:
         Extent number of the child link for this Rock Ridge record.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Rock Ridge extension not yet initialized")

        if self.cl_record is not None:
            return self.cl_record.child_log_block_num
        else:
            if self.ce_record is not None:
                if self.ce_record.continuation_entry.cl_record is not None:
                    return self.ce_record.continuation_entry.cl_record.child_log_block_num

        raise pycdlibexception.PyCdlibException("This RR record has no child link record")
