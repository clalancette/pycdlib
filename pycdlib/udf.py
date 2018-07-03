# Copyright (C) 2018  Chris Lalancette <clalancette@gmail.com>

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
Classes to support UDF.
'''

from __future__ import absolute_import

import bisect
import random
import struct
import sys
import time

import pycdlib.pycdlibexception as pycdlibexception
import pycdlib.utils as utils

# This is the CRC CCITT table generated with a polynomial of 0x11021 and
# 16-bits.  The following code will re-generate the table:
#
# def _bytecrc(crc, poly, n):
#    mask = 1<<(n-1)
#    for i in range(8):
#        if crc & mask:
#            crc = (crc << 1) ^ poly
#        else:
#            crc = crc << 1
#    mask = (1<<n) - 1
#    crc = crc & mask
#    return crc
#
# def _mkTable(poly, n):
#    mask = (1<<n) - 1
#    poly = poly & mask
#    table = [_bytecrc(i<<(n-8),poly,n) for i in range(256)]
#    return table

crc_ccitt_table = (0, 4129, 8258, 12387, 16516, 20645, 24774, 28903, 33032,
                   37161, 41290, 45419, 49548, 53677, 57806, 61935, 4657, 528,
                   12915, 8786, 21173, 17044, 29431, 25302, 37689, 33560, 45947,
                   41818, 54205, 50076, 62463, 58334, 9314, 13379, 1056, 5121,
                   25830, 29895, 17572, 21637, 42346, 46411, 34088, 38153,
                   58862, 62927, 50604, 54669, 13907, 9842, 5649, 1584, 30423,
                   26358, 22165, 18100, 46939, 42874, 38681, 34616, 63455, 59390,
                   55197, 51132, 18628, 22757, 26758, 30887, 2112, 6241, 10242,
                   14371, 51660, 55789, 59790, 63919, 35144, 39273, 43274, 47403,
                   23285, 19156, 31415, 27286, 6769, 2640, 14899, 10770, 56317,
                   52188, 64447, 60318, 39801, 35672, 47931, 43802, 27814, 31879,
                   19684, 23749, 11298, 15363, 3168, 7233, 60846, 64911, 52716,
                   56781, 44330, 48395, 36200, 40265, 32407, 28342, 24277, 20212,
                   15891, 11826, 7761, 3696, 65439, 61374, 57309, 53244, 48923,
                   44858, 40793, 36728, 37256, 33193, 45514, 41451, 53516, 49453,
                   61774, 57711, 4224, 161, 12482, 8419, 20484, 16421, 28742,
                   24679, 33721, 37784, 41979, 46042, 49981, 54044, 58239, 62302,
                   689, 4752, 8947, 13010, 16949, 21012, 25207, 29270, 46570,
                   42443, 38312, 34185, 62830, 58703, 54572, 50445, 13538, 9411,
                   5280, 1153, 29798, 25671, 21540, 17413, 42971, 47098, 34713,
                   38840, 59231, 63358, 50973, 55100, 9939, 14066, 1681, 5808,
                   26199, 30326, 17941, 22068, 55628, 51565, 63758, 59695,
                   39368, 35305, 47498, 43435, 22596, 18533, 30726, 26663, 6336,
                   2273, 14466, 10403, 52093, 56156, 60223, 64286, 35833, 39896,
                   43963, 48026, 19061, 23124, 27191, 31254, 2801, 6864, 10931,
                   14994, 64814, 60687, 56684, 52557, 48554, 44427, 40424, 36297,
                   31782, 27655, 23652, 19525, 15522, 11395, 7392, 3265, 61215,
                   65342, 53085, 57212, 44955, 49082, 36825, 40952, 28183, 32310,
                   20053, 24180, 11923, 16050, 3793, 7920)


have_py_3 = True
if sys.version_info.major == 2:
    have_py_3 = False


def crc_ccitt(data):
    '''
    Calculate the CRC over a range of bytes using the CCITT polynomial.

    Parameters:
     data - The array of bytes to calculate the CRC over.
    Returns:
     The CCITT CRC of the data.
    '''
    crc = 0
    if not have_py_3:
        for x in data:
            crc = crc_ccitt_table[ord(x) ^ ((crc >> 8) & 0xFF)] ^ ((crc << 8) & 0xFF00)
    else:
        mv = memoryview(data)
        for x in mv.tobytes():
            crc = crc_ccitt_table[x ^ ((crc >> 8) & 0xFF)] ^ ((crc << 8) & 0xFF00)

    return crc


def _ostaunicode(src):
    '''
    Internal function to create an OSTA byte string from a source string.
    '''
    if have_py_3:
        bytename = src
    else:
        bytename = src.decode('utf-8')

    try:
        enc = bytename.encode('latin-1')
        encbyte = b'\x08'
    except (UnicodeEncodeError, UnicodeDecodeError):
        enc = bytename.encode('utf-16_be')
        encbyte = b'\x10'
    return encbyte + enc


def _ostaunicode_zero_pad(src, fulllen):
    '''
    Internal function to create a zero-padded Identifier byte string from a
    source string.

    Parameters:
     src - The src string to start from.
     fulllen - The padded out length of the result.
    Returns:
     A full identifier byte string containing the source string.
    '''
    byte_src = _ostaunicode(src)
    return byte_src + b'\x00' * (fulllen - 1 - len(byte_src)) + (struct.pack('=B', len(byte_src)))


def _unicodecharset():
    '''
    Internal function to generate the 'OSTA Compressed Unicode' full byte-string.

    Parameters:
     None.
    Return:
     The padded byte-string containing 'OSTA Compressed Unicode'.
    '''
    return b'\x00OSTA Compressed Unicode' + b'\x00' * 40


class BEAVolumeStructure(object):
    '''
    A class representing a UDF Beginning Extended Area Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc')

    FMT = '=B5sB2041s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent):
        '''
        Parse the passed in data into a UDF BEA Volume Structure.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('BEA Volume Structure already initialized')

        (structure_type, standard_ident, structure_version,
         reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        if structure_type != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure type')

        if standard_ident != b'BEA01':
            raise pycdlibexception.PyCdlibInvalidISO('Invalid standard identifier')

        if structure_version != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure version')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF BEA Volume
        Structure.

        Parameters:
         None.
        Returns:
         A string representing this UDF BEA Volume Strucutre.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('BEA Volume Structure not initialized')
        return struct.pack(self.FMT, 0, b'BEA01', 1, b'\x00' * 2041)

    def new(self):
        '''
        A method to create a new UDF BEA Volume Structure.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('BEA Volume Structure already initialized')

        self._initialized = True

    def extent_location(self):
        '''
        A method to get the extent location of this UDF BEA Volume Structure.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF BEA Volume Structure.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF BEA Volume Structure not yet initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


class NSRVolumeStructure(object):
    '''
    A class representing a UDF NSR Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc')

    FMT = '=B5sB2041s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent):
        '''
        Parse the passed in data into a UDF NSR Volume Structure.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF NSR Volume Structure already initialized')

        (structure_type, standard_ident, structure_version,
         reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        if structure_type != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure type')

        if standard_ident != b'NSR02':
            raise pycdlibexception.PyCdlibInvalidISO('Invalid standard identifier')

        if structure_version != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure version')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF NSR Volume
        Structure.

        Parameters:
         None.
        Returns:
         A string representing this UDF BEA Volume Strucutre.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF NSR Volume Structure not initialized')
        return struct.pack(self.FMT, 0, b'NSR02', 1, b'\x00' * 2041)

    def new(self):
        '''
        A method to create a new UDF NSR Volume Structure.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF NSR Volume Structure already initialized')

        self._initialized = True

    def extent_location(self):
        '''
        A method to get the extent location of this UDF NSR Volume Structure.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF NSR Volume Structure.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF NSR Volume Structure not yet initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


class TEAVolumeStructure(object):
    '''
    A class representing a UDF Terminating Extended Area Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc')

    FMT = '=B5sB2041s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent):
        '''
        Parse the passed in data into a UDF TEA Volume Structure.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('TEA Volume Structure already initialized')

        (structure_type, standard_ident, structure_version,
         reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        if structure_type != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure type')

        if standard_ident != b'TEA01':
            raise pycdlibexception.PyCdlibInvalidISO('Invalid standard identifier')

        if structure_version != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid structure version')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF TEA Volume
        Structure.

        Parameters:
         None.
        Returns:
         A string representing this UDF TEA Volume Strucutre.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF TEA Volume Structure not initialized')
        return struct.pack(self.FMT, 0, b'TEA01', 1, b'\x00' * 2041)

    def new(self):
        '''
        A method to create a new UDF TEA Volume Structure.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF TEA Volume Structure already initialized')

        self._initialized = True

    def extent_location(self):
        '''
        A method to get the extent location of this UDF TEA Volume Structure.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF TEA Volume Structure.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF TEA Volume Structure not yet initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc


def _compute_csum(data):
    '''
    A method to compute a simple checksum over the given data.

    Parameters:
     data - The data to compute the checksum over.
    Returns:
     The checksum.
    '''
    def identity(x):
        '''
        The identity function so we can use a function for python2/3
        compatibility.
        '''
        return x

    if isinstance(data, str):
        myord = ord
    elif isinstance(data, bytes):
        myord = identity
    elif isinstance(data, bytearray):
        myord = identity
    csum = 0
    for byte in data:
        csum += myord(byte)
    csum -= myord(data[4])
    csum %= 256

    return csum


class UDFTag(object):
    '''
    A class representing a UDF 167 7.2 Descriptor Tag.
    '''
    __slots__ = ('_initialized', 'tag_ident', 'desc_version',
                 'tag_serial_number', 'tag_location', 'desc_crc_length')

    FMT = '=HHBBHHHL'

    def __init__(self):
        self.desc_crc_length = None
        self._initialized = False

    def parse(self, data, extent):
        '''
        Parse the passed in data into a UDF Descriptor tag.

        Parameters:
         data - The data to parse.
         extent - The extent to compare against for the tag location.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Tag already initialized')

        (self.tag_ident, self.desc_version, tag_checksum, reserved,
         self.tag_serial_number, desc_crc, self.desc_crc_length,
         self.tag_location) = struct.unpack_from(self.FMT, data, 0)

        if reserved != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Reserved data not 0!')

        if _compute_csum(data[:16]) != tag_checksum:
            raise pycdlibexception.PyCdlibInvalidISO('Tag checksum does not match!')

        if self.tag_location != extent:
            # In theory, we should abort (throw an exception) if we see that a
            # tag location that doesn't match an actual location.  However, we
            # have seen UDF ISOs in the wild (most notably PS2 GT4 ISOs) that
            # have an invalid tag location for the second anchor and File Set
            # Terminator.  So that we can support those ISOs, just silently
            # fix it up.  We lose a little bit of detection of whether this is
            # "truly" a UDFTag, but it is really not a big risk.
            self.tag_location = extent

        if self.desc_version not in (2, 3):
            raise pycdlibexception.PyCdlibInvalidISO('Tag version not 2 or 3')

        if (len(data) - 16) < self.desc_crc_length:
            raise pycdlibexception.PyCdlibInternalError('Not enough CRC bytes to compute (expected at least %d, got %d)' % (self.desc_crc_length, len(data) - 16))

        if desc_crc != crc_ccitt(data[16:16 + self.desc_crc_length]):
            raise pycdlibexception.PyCdlibInvalidISO('Tag CRC does not match!')

        self._initialized = True

    def record(self, crc_bytes):
        '''
        A method to generate the string representing this UDF Descriptor Tag.

        Parameters:
         crc_bytes - The string to compute the CRC over.
        Returns:
         A string representing this UDF Descriptor Tag.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Descriptor Tag not initialized')

        crc_byte_len = len(crc_bytes)
        if self.desc_crc_length is not None:
            crc_byte_len = self.desc_crc_length

        # We need to compute the checksum, but we'll do that by first creating
        # the output buffer with the csum field set to 0, computing the csum,
        # and then setting that record back as usual.
        rec = bytearray(struct.pack(self.FMT, self.tag_ident, self.desc_version,
                                    0, 0, self.tag_serial_number,
                                    crc_ccitt(crc_bytes[:crc_byte_len]),
                                    crc_byte_len, self.tag_location))

        rec[4] = _compute_csum(rec)

        return bytes(rec)

    def new(self, tag_ident, tag_serial=0):
        '''
        A method to create a new UDF Descriptor Tag.

        Parameters:
         tag_ident - The tag identifier number for this tag.
         tag_serial - The tag serial number for this tag.
        Returns:
         Nothing
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Tag already initialized')

        self.tag_ident = tag_ident
        self.desc_version = 2
        self.tag_serial_number = tag_serial
        self.tag_location = 0  # This will be set later.

        self._initialized = True


class UDFAnchorVolumeStructure(object):
    '''
    A class representing a UDF Anchor Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'main_vd_length', 'main_vd_extent', 'reserve_vd_length',
                 'reserve_vd_extent', 'desc_tag')

    FMT = '=16sLLLL'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Anchor Volume Structure.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Anchor Volume Structure already initialized')

        (tag_unused, self.main_vd_length, self.main_vd_extent,
         self.reserve_vd_length,
         self.reserve_vd_extent) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Anchor Volume
        Structure.

        Parameters:
         None.
        Returns:
         A string representing this UDF Anchor Volume Structure.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Anchor Volume Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16, self.main_vd_length,
                          self.main_vd_extent, self.reserve_vd_length,
                          self.reserve_vd_extent)[16:] + b'\x00' * 480

        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Anchor Volume Structure.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Anchor Volume Structure.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Anchor Volume Structure not yet initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Anchor Volume Structure.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Anchor Volume Structure already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(2)  # FIXME: we should let the user set serial_number
        self.main_vd_length = 32768
        self.main_vd_extent = 0  # This will get set later.
        self.reserve_vd_length = 32768
        self.reserve_vd_extent = 0  # This will get set later.

        self._initialized = True

    def set_location(self, new_location, main_vd_extent, reserve_vd_extent):
        '''
        A method to set a new location for this Anchor Volume Structure.

        Parameters:
         new_location - The new extent that this Anchor Volume Structure should be located at.
         main_vd_extent - The extent containing the main Volume Descriptors.
         reserve_vd_extent - The extent containing the reserve Volume Descriptors.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Anchor Volume Structure not yet initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location
        self.main_vd_extent = main_vd_extent
        self.reserve_vd_extent = reserve_vd_extent


class UDFTimestamp(object):
    '''
    A class representing a UDF timestamp.
    '''
    __slots__ = ('_initialized', 'year', 'month', 'day', 'hour', 'minute',
                 'second', 'centiseconds', 'hundreds_microseconds',
                 'microseconds', 'timetype', 'tz')

    FMT = '=BBHBBBBBBBB'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Timestamp.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Timestamp already initialized')

        (tz, timetype, self.year, self.month, self.day, self.hour, self.minute,
         self.second, self.centiseconds, self.hundreds_microseconds,
         self.microseconds) = struct.unpack_from(self.FMT, data, 0)

        self.timetype = timetype >> 4

        def twos_comp(val, bits):
            '''
            Compute the 2's complement of int value val
            '''
            if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
                val = val - (1 << bits)         # compute negative value
            return val                          # return positive value as is
        self.tz = twos_comp(((timetype & 0xf) << 8) | tz, 12)
        if self.tz < -1440 or self.tz > 1440:
            if self.tz != -2047:
                raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF timezone')

        if self.year < 1 or self.year > 9999:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF year')
        if self.month < 1 or self.month > 12:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF month')
        if self.day < 1 or self.day > 31:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF day')
        if self.hour < 0 or self.hour > 23:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF hour')
        if self.minute < 0 or self.minute > 59:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF minute')
        if self.second < 0 or self.second > 59:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid UDF second')

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Timestamp.

        Parameters:
         None.
        Returns:
         A string representing this UDF Timestamp.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Timestamp not initialized')

        tmp = ((1 << 16) - 1) & self.tz
        newtz = tmp & 0xff
        newtimetype = ((tmp >> 8) & 0x0f) | (self.timetype << 4)

        return struct.pack(self.FMT, newtz, newtimetype, self.year, self.month,
                           self.day, self.hour, self.minute, self.second,
                           self.centiseconds, self.hundreds_microseconds,
                           self.microseconds)

    def new(self):
        '''
        A method to create a new UDF Timestamp.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Timestamp already initialized')

        tm = time.time()
        local = time.localtime(tm)

        self.tz = utils.gmtoffset_from_tm(tm, local)
        # FIXME: for the timetype, 0 is UTC, 1 is local, 2 is 'agreement'.
        # We should let the user set this.
        self.timetype = 1
        self.year = local.tm_year
        self.month = local.tm_mon
        self.day = local.tm_mon
        self.hour = local.tm_hour
        self.minute = local.tm_min
        self.second = local.tm_sec
        self.centiseconds = 0
        self.hundreds_microseconds = 0
        self.microseconds = 0

        self._initialized = True


class UDFEntityID(object):
    '''
    A class representing a UDF Entity ID.
    '''
    __slots__ = ('_initialized', 'flags', 'identifier', 'suffix')

    FMT = '=B23s8s'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Entity ID.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Entity ID already initialized')

        (self.flags, self.identifier, self.suffix) = struct.unpack_from(self.FMT, data, 0)

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Entity ID.

        Parameters:
         None.
        Returns:
         A string representing this UDF Entity ID.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Entity ID not initialized')

        return struct.pack(self.FMT, self.flags, self.identifier, self.suffix)

    def new(self, flags=0, identifier=b'', suffix=b''):
        '''
        A method to create a new UDF Entity ID.

        Parameters:
         flags - The flags to set for this Entity ID.
         identifier - The identifier to set for this Entity ID.
         suffix - The suffix to set for this Entity ID.
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Entity ID already initialized')

        if len(identifier) > 23:
            raise pycdlibexception.PyCdlibInvalidInput('UDF Entity ID identifer must be less than 23 characters')

        if len(suffix) > 8:
            raise pycdlibexception.PyCdlibInvalidInput('UDF Entity ID suffix must be less than 8 characters')

        self.flags = flags
        self.identifier = identifier + b'\x00' * (23 - len(identifier))
        self.suffix = suffix + b'\x00' * (8 - len(suffix))

        self._initialized = True


class UDFPrimaryVolumeDescriptor(object):
    '''
    A class representing a UDF Primary Volume Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'vol_desc_seqnum', 'desc_num', 'vol_ident', 'vol_set_ident',
                 'desc_char_set', 'explanatory_char_set', 'vol_abstract_length',
                 'vol_abstract_extent', 'vol_copyright_length',
                 'vol_copyright_extent', 'implementation_use',
                 'predecessor_vol_desc_location', 'desc_tag', 'recording_date',
                 'app_ident', 'impl_ident', 'max_interchange_level')

    FMT = '=16sLL32sHHHHLL128s64s64sLLLL32s12s32s64sLH22s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Primary Volume Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Primary Volume Descriptor already initialized')

        (tag_unused, self.vol_desc_seqnum, self.desc_num, self.vol_ident,
         vol_seqnum, max_vol_seqnum, interchange_level,
         self.max_interchange_level, char_set_list,
         max_char_set_list, self.vol_set_ident, self.desc_char_set,
         self.explanatory_char_set, self.vol_abstract_length, self.vol_abstract_extent,
         self.vol_copyright_length, self.vol_copyright_extent, app_ident,
         recording_date, impl_ident, self.implementation_use,
         self.predecessor_vol_desc_location, flags,
         reserved) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        if vol_seqnum != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if max_vol_seqnum != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if interchange_level != 2:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if char_set_list != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if max_char_set_list != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if flags != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')

        if reserved != b'\x00' * 22:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Primary Volume Descriptor reserved data not 0')

        self.recording_date = UDFTimestamp()
        self.recording_date.parse(recording_date)

        self.app_ident = UDFEntityID()
        self.app_ident.parse(app_ident)

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Primary Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Primary Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Primary Volume Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.vol_desc_seqnum, self.desc_num,
                          self.vol_ident, 1, 1, 2, self.max_interchange_level, 1, 1,
                          self.vol_set_ident,
                          self.desc_char_set, self.explanatory_char_set,
                          self.vol_abstract_length, self.vol_abstract_extent,
                          self.vol_copyright_length, self.vol_copyright_extent,
                          self.app_ident.record(), self.recording_date.record(),
                          self.impl_ident.record(), self.implementation_use,
                          self.predecessor_vol_desc_location, 0, b'\x00' * 22)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Primary Volume Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Primary Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Primary Volume Descriptor not yet initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Primary Volume Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Primary Volume Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(1)  # FIXME: we should let the user set serial_number

        self.vol_desc_seqnum = 0  # FIXME: we should let the user set this
        self.desc_num = 0  # FIXME: we should let the user set this
        self.vol_ident = _ostaunicode_zero_pad('CDROM', 32)
        # According to UDF 2.60, 2.2.2.5, the VolumeSetIdentifier should have
        # at least the first 16 characters be a unique value.  Further, the
        # first 8 bytes of that should be a time value in ASCII hexadecimal
        # representation.  To make it truly unique, we use that time plus a
        # random value, all ASCII encoded.
        unique = format(int(time.time()), '08x') + format(random.getrandbits(26), '08x')
        self.vol_set_ident = _ostaunicode_zero_pad(unique, 128)
        self.desc_char_set = _unicodecharset()
        self.explanatory_char_set = _unicodecharset()
        self.vol_abstract_length = 0  # FIXME: we should let the user set this
        self.vol_abstract_extent = 0  # FIXME: we should let the user set this
        self.vol_copyright_length = 0  # FIXME: we should let the user set this
        self.vol_copyright_extent = 0  # FIXME: we should let the user set this
        self.app_ident = UDFEntityID()
        self.app_ident.new()
        self.recording_date = UDFTimestamp()
        self.recording_date.new()
        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*pycdlib')
        self.implementation_use = b'\x00' * 64  # FIXME: we should let the user set this
        self.predecessor_vol_desc_location = 0  # FIXME: we should let the user set this
        self.max_interchange_level = 2

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set the new location for this UDF Primary Volume Descriptor.

        Parameters:
         new_location - The extent that this Primary Volume Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Primary Volume Descriptor not yet initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location


class UDFImplementationUseVolumeDescriptorImplementationUse(object):
    '''
    A class representing the Implementation Use field of the Implementation Use Volume Descriptor.
    '''
    __slots__ = ('_initialized', 'char_set', 'log_vol_ident', 'lv_info1',
                 'lv_info2', 'lv_info3', 'impl_ident', 'impl_use')

    FMT = '=64s128s36s36s36s32s128s'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Implementation Use Volume
        Descriptor Implementation Use field.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor Implementation Use field already initialized')

        (self.char_set, self.log_vol_ident, self.lv_info1, self.lv_info2,
         self.lv_info3, impl_ident,
         self.impl_use) = struct.unpack_from(self.FMT, data, 0)

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Implementation Use
        Volume Descriptor Implementation Use field.

        Parameters:
         None.
        Returns:
         A string representing this UDF Implementation Use Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor Implementation Use field not initialized')

        return struct.pack(self.FMT, self.char_set, self.log_vol_ident,
                           self.lv_info1, self.lv_info2, self.lv_info3,
                           self.impl_ident.record(), self.impl_use)

    def new(self):
        '''
        A method to create a new UDF Implementation Use Volume Descriptor Implementation Use field.

        Parameters:
         None:
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor Implementation Use field already initialized')

        self.char_set = _unicodecharset()
        self.log_vol_ident = _ostaunicode_zero_pad('CDROM', 128)
        self.lv_info1 = b'\x00' * 36
        self.lv_info2 = b'\x00' * 36
        self.lv_info3 = b'\x00' * 36
        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*pycdlib', b'')
        self.impl_use = b'\x00' * 128

        self._initialized = True


class UDFImplementationUseVolumeDescriptor(object):
    '''
    A class representing a UDF Implementation Use Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'vol_desc_seqnum', 'impl_use', 'desc_tag', 'impl_ident')

    FMT = '=16sL32s460s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Implementation Use Volume
        Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor already initialized')

        (tag_unused, self.vol_desc_seqnum, impl_ident,
         impl_use) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)
        if self.impl_ident.identifier[:12] != b'*UDF LV Info':
            raise pycdlibexception.PyCdlibInvalidISO("Implementation Use Identifier not '*UDF LV Info'")

        self.impl_use = UDFImplementationUseVolumeDescriptorImplementationUse()
        self.impl_use.parse(impl_use)

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Implementation Use
        Volume Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Implementation Use Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.vol_desc_seqnum, self.impl_ident.record(),
                          self.impl_use.record())[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Implementation Use
        Volume Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Implementation Use Volume
         Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Implementation Use Volume Descriptor.

        Parameters:
         None:
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(4)  # FIXME: we should let the user set serial_number

        self.vol_desc_seqnum = 1

        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*UDF LV Info', b'\x02\x01')

        self.impl_use = UDFImplementationUseVolumeDescriptorImplementationUse()
        self.impl_use.new()

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set thet new location for this UDF Implementation Use Volume Descriptor.

        Parameters:
         new_location - The new extent this UDF Implementation Use Volume Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Implementation Use Volume Descriptor not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location


class UDFPartitionHeaderDescriptor(object):
    '''
    A class representing a UDF Partition Header Descriptor.
    '''
    __slots__ = ('_initialized',)

    FMT = '=LLLLLLLLLL88s'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Partition Header Descriptor.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Header Descriptor already initialized')
        (unalloc_table_length, unalloc_table_pos, unalloc_bitmap_length,
         unalloc_bitmap_pos, part_integrity_table_length,
         part_integrity_table_pos, freed_table_length, freed_table_pos,
         freed_bitmap_length, freed_bitmap_pos,
         reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        if unalloc_table_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header unallocated table length not 0')
        if unalloc_table_pos != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header unallocated table position not 0')
        if unalloc_bitmap_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header unallocated bitmap length not 0')
        if unalloc_bitmap_pos != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header unallocated bitmap position not 0')
        if part_integrity_table_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header partition integrity length not 0')
        if part_integrity_table_pos != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header partition integrity position not 0')
        if freed_table_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header freed table length not 0')
        if freed_table_pos != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header freed table position not 0')
        if freed_bitmap_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header freed bitmap length not 0')
        if freed_bitmap_pos != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Partition Header freed bitmap position not 0')

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Partition Header
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Partition Header Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Header Descriptor not initialized')

        return struct.pack(self.FMT, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, b'\x00' * 88)

    def new(self):
        '''
        A method to create a new UDF Partition Header Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Header Descriptor already initialized')

        self._initialized = True


class UDFPartitionVolumeDescriptor(object):
    '''
    A class representing a UDF Partition Volume Structure.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'vol_desc_seqnum', 'part_flags', 'part_num', 'access_type',
                 'part_start_location', 'part_length', 'implementation_use',
                 'desc_tag', 'part_contents', 'impl_ident', 'part_contents_use')

    FMT = '=16sLHH32s128sLLL32s128s156s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Partition Volume Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor already initialized')

        (tag_unused, self.vol_desc_seqnum, self.part_flags, self.part_num,
         part_contents, part_contents_use, self.access_type,
         self.part_start_location, self.part_length, impl_ident,
         self.implementation_use, reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.part_contents = UDFEntityID()
        self.part_contents.parse(part_contents)
        if self.part_contents.identifier[:6] != b'+NSR02':
            raise pycdlibexception.PyCdlibInvalidISO("Partition Contents Identifier not '+NSR02'")

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)

        self.part_contents_use = UDFPartitionHeaderDescriptor()
        self.part_contents_use.parse(part_contents_use)

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Partition Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Partition Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.vol_desc_seqnum, self.part_flags,
                          self.part_num, self.part_contents.record(),
                          self.part_contents_use.record(), self.access_type,
                          self.part_start_location, self.part_length,
                          self.impl_ident.record(), self.implementation_use,
                          b'\x00' * 156)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Partition Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Partition Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Partition Volume Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(5)  # FIXME: we should let the user set serial_number

        self.vol_desc_seqnum = 2
        self.part_flags = 1  # FIXME: how should we set this?
        self.part_num = 0  # FIXME: how should we set this?

        self.part_contents = UDFEntityID()
        self.part_contents.new(2, b'+NSR02')

        self.part_contents_use = UDFPartitionHeaderDescriptor()
        self.part_contents_use.new()

        self.access_type = 1
        self.part_start_location = 0  # This will get set later
        self.part_length = 3  # This will get set later

        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*pycdlib')

        self.implementation_use = b'\x00' * 128  # FIXME: we should let the user set this

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set the location of this UDF Partition Volume Descriptor.

        Parameters:
         new_location - The new extent this UDF Partition Volume Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor not initialized')
        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location

    def set_start_location(self, new_location):
        '''
        A method to set the location of the start of the partition.

        Parameters:
         new_location - The new extent the UDF partition should start at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Volume Descriptor not initialized')
        self.part_start_location = new_location


class UDFPartitionMap(object):
    '''
    A class representing a UDF Partition Map.
    '''
    __slots__ = ('_initialized', 'part_num')

    FMT = '=BBHH'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Partition Map.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Map already initialized')

        (map_type, map_length, vol_seqnum,
         self.part_num) = struct.unpack_from(self.FMT, data, 0)

        if map_type != 1:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Partition Map type is not 1')
        if map_length != 6:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Partition Map length is not 6')
        if vol_seqnum != 1:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Partition Volume Sequence Number is not 1')

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Partition Map.

        Parameters:
         None.
        Returns:
         A string representing this UDF Partition Map.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Map not initialized')

        return struct.pack(self.FMT, 1, 6, 1, self.part_num)

    def new(self):
        '''
        A method to create a new UDF Partition Map.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Partition Map already initialized')

        self.part_num = 0  # FIXME: we should let the user set this

        self._initialized = True


class UDFLongAD(object):
    '''
    A class representing a UDF Long Allocation Descriptor.
    '''
    __slots__ = ('_initialized', 'extent_length', 'log_block_num',
                 'part_ref_num', 'impl_use')

    FMT = '=LLH6s'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Long AD.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Long Allocation descriptor already initialized')
        (self.extent_length, self.log_block_num, self.part_ref_num,
         self.impl_use) = struct.unpack_from(self.FMT, data, 0)

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Long AD.

        Parameters:
         None.
        Returns:
         A string representing this UDF Long AD.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Long AD not initialized')

        return struct.pack(self.FMT, self.extent_length, self.log_block_num,
                           self.part_ref_num, self.impl_use)

    def new(self, length, blocknum):
        '''
        A method to create a new UDF Long AD.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Long AD already initialized')

        self.extent_length = length
        self.log_block_num = blocknum
        self.part_ref_num = 0  # FIXME: we should let the user set this
        self.impl_use = b'\x00' * 6

        self._initialized = True

    def set_location(self, new_location, tag_location):
        '''
        A method to set the location fields of this UDF Long AD.

        Parameters:
         new_location - The new relative extent that this UDF Long AD references.
         tag_location - The new absolute extent that this UDF Long AD references.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Long AD not initialized')

        self.log_block_num = tag_location
        self.impl_use = b'\x00\x00' + struct.pack('=L', new_location)


class UDFLogicalVolumeDescriptor(object):
    '''
    A class representing a UDF Logical Volume Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'vol_desc_seqnum', 'desc_char_set', 'logical_vol_ident',
                 'implementation_use', 'integrity_sequence_length',
                 'integrity_sequence_extent', 'desc_tag', 'domain_ident',
                 'impl_ident', 'partition_map', 'logical_volume_contents_use')

    FMT = '=16sL64s128sL32s16sLL32s128sLL6s66s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Logical Volume Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor already initialized')

        (tag_unused, self.vol_desc_seqnum, self.desc_char_set,
         self.logical_vol_ident, logical_block_size, domain_ident,
         logical_volume_contents_use, map_table_length, num_partition_maps,
         impl_ident, self.implementation_use, self.integrity_sequence_length,
         self.integrity_sequence_extent, partition_map,
         end_unused) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        if logical_block_size != 2048:
            raise pycdlibexception.PyCdlibInvalidISO('Volume Descriptor block size is not 2048')

        self.domain_ident = UDFEntityID()
        self.domain_ident.parse(domain_ident)
        if self.domain_ident.identifier[:19] != b'*OSTA UDF Compliant':
            raise pycdlibexception.PyCdlibInvalidISO("Volume Descriptor Identifier not '*OSTA UDF Compliant'")

        if map_table_length != 6:
            raise pycdlibexception.PyCdlibInvalidISO('Volume Descriptor map table length not 6')

        if num_partition_maps != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Volume Descriptor number of partition maps not 1')

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)

        self.partition_map = UDFPartitionMap()
        self.partition_map.parse(partition_map)

        self.logical_volume_contents_use = UDFLongAD()
        self.logical_volume_contents_use.parse(logical_volume_contents_use)

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Logical Volume Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Logical Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.vol_desc_seqnum, self.desc_char_set,
                          self.logical_vol_ident, 2048,
                          self.domain_ident.record(),
                          self.logical_volume_contents_use.record(), 6, 1,
                          self.impl_ident.record(), self.implementation_use,
                          self.integrity_sequence_length,
                          self.integrity_sequence_extent,
                          self.partition_map.record(), b'\x00' * 66)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Logical Volume
        Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Logical Volume Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Logical Volume Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(6)  # FIXME: we should let the user set serial_number

        self.vol_desc_seqnum = 3
        self.desc_char_set = _unicodecharset()

        self.logical_vol_ident = _ostaunicode_zero_pad('CDROM', 128)

        self.domain_ident = UDFEntityID()
        self.domain_ident.new(0, b'*OSTA UDF Compliant', b'\x02\x01\x03')

        self.logical_volume_contents_use = UDFLongAD()
        self.logical_volume_contents_use.new(4096, 0)

        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*pycdlib')

        self.implementation_use = b'\x00' * 128  # FIXME: let the user set this
        self.integrity_sequence_length = 4096
        self.integrity_sequence_extent = 0  # This will get set later

        self.partition_map = UDFPartitionMap()
        self.partition_map.new()

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set the location of this UDF Logical Volume Descriptor.

        Parameters:
         new_location - The new extent this UDF Logical Volume Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location

    def set_integrity_location(self, integrity_extent):
        '''
        A method to set the location of the UDF Integrity sequence that this descriptor references.

        Parameters:
         integrity_extent - The new extent that the UDF Integrity sequence should start at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Descriptor not initialized')

        self.integrity_sequence_extent = integrity_extent


class UDFUnallocatedSpaceDescriptor(object):
    '''
    A class representing a UDF Unallocated Space Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'vol_desc_seqnum', 'desc_tag')

    FMT = '=16sLL488s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Unallocated Space Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Unallocated Space Descriptor already initialized')

        (tag_unused, self.vol_desc_seqnum,
         num_alloc_descriptors, end_unused) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        if num_alloc_descriptors != 0:
            raise pycdlibexception.PyCdlibInvalidISO('UDF Unallocated Space Descriptor allocated descriptors is not 0')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Unallocated Space
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Unallocated Space Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Unallocated Space Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.vol_desc_seqnum, 0, b'\x00' * 488)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Unallocated Space
        Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Unallocated Space Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Unallocated Space Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Unallocated Space Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Unallocated Space Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(7)  # FIXME: we should let the user set serial_number

        self.vol_desc_seqnum = 4

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set the location of this UDF Unallocated Space Descriptor.

        Parameters:
         new_location - The new extent this UDF Unallocated Space Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Unallocated Space Descriptor not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location


class UDFTerminatingDescriptor(object):
    '''
    A class representing a UDF Unallocated Space Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'desc_tag')

    FMT = '=16s496s'

    def __init__(self):
        self._initialized = False

    def parse(self, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Terminating Descriptor.

        Parameters:
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Terminating Descriptor already initialized')

        self.desc_tag = desc_tag

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Terminating
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Terminating Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Terminating Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16, b'\x00' * 496)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Terminating Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Terminating Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Terminating Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Terminating Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Terminating Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(8)  # FIXME: we should let the user set serial_number

        self._initialized = True

    def set_location(self, new_location, tag_location=None):
        '''
        A method to set the location of this UDF Terminating Descriptor.

        Parameters:
         new_location - The new extent this UDF Terminating Descriptor should be located at.
         tag_location - The tag location to set for this UDF Terminator Descriptor.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Terminating Descriptor not initialized')

        self.new_extent_loc = new_location
        if tag_location is None:
            tag_location = new_location
        self.desc_tag.tag_location = tag_location


class UDFLogicalVolumeHeaderDescriptor(object):
    '''
    A class representing a UDF Logical Volume Header Descriptor.
    '''
    __slots__ = ('_initialized', 'unique_id')

    FMT = '=Q24s'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Logical Volume Header Descriptor.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Header Descriptor already initialized')
        (self.unique_id, reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Logical Volume
        Header Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Logical Volume Header Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Header Descriptor not initialized')

        return struct.pack(self.FMT, self.unique_id, b'\x00' * 24)

    def new(self):
        '''
        A method to create a new UDF Logical Volume Header Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Header Descriptor already initialized')

        self.unique_id = 261

        self._initialized = True


class UDFLogicalVolumeImplementationUse(object):
    '''
    A class representing a UDF Logical Volume Implementation Use.
    '''
    __slots__ = ('_initialized', 'num_files', 'num_dirs',
                 'min_udf_read_revision', 'min_udf_write_revision',
                 'max_udf_write_revision', 'impl_id', 'impl_use')

    FMT = '=32sLLHHH'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF Logical Volume Implementation Use.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Implementation Use already initialized')

        (impl_id, self.num_files, self.num_dirs, self.min_udf_read_revision,
         self.min_udf_write_revision,
         self.max_udf_write_revision) = struct.unpack_from(self.FMT, data, 0)

        self.impl_id = UDFEntityID()
        self.impl_id.parse(impl_id)

        self.impl_use = data[46:]

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Logical Volume
        Implementation Use.

        Parameters:
         None.
        Returns:
         A string representing this UDF Logical Volume Implementation Use.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Implementation Use not initialized')

        return struct.pack(self.FMT, self.impl_id.record(),
                           self.num_files, self.num_dirs,
                           self.min_udf_read_revision,
                           self.min_udf_write_revision,
                           self.max_udf_write_revision) + self.impl_use

    def new(self):
        '''
        A method to create a new UDF Logical Volume Implementation Use.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Implementation Use already initialized')

        self.impl_id = UDFEntityID()
        self.impl_id.new(0, b'*pycdlib')

        self.num_files = 0
        self.num_dirs = 1
        self.min_udf_read_revision = 258
        self.min_udf_write_revision = 258
        self.max_udf_write_revision = 258

        self.impl_use = b'\x00' * 378

        self._initialized = True


class UDFLogicalVolumeIntegrityDescriptor(object):
    '''
    A class representing a UDF Logical Volume Integrity Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'length_impl_use', 'free_space_table', 'size_table',
                 'desc_tag', 'recording_date', 'logical_volume_contents_use',
                 'logical_volume_impl_use')

    FMT = '=16s12sLLL32sLLLL424s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF Logical Volume Integrity Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Integrity Descriptor already initialized')

        (tag_unused, recording_date, integrity_type,
         next_integrity_extent_length, next_integrity_extent_extent,
         logical_volume_contents_use, num_partitions,
         self.length_impl_use, self.free_space_table,
         self.size_table, impl_use) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.recording_date = UDFTimestamp()
        self.recording_date.parse(recording_date)

        if integrity_type != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity Type not 1')
        if next_integrity_extent_length != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity Extent length not 1')
        if next_integrity_extent_extent != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity Extent extent not 1')
        if num_partitions != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity number partitions not 1')
        # For now, we only support an implementation use field of up to 424
        # bytes (the 'rest' of the 512 byte sector we get here).  If we run
        # across ones that are larger, we can go up to 2048, but anything
        # larger than that is invalid (I'm not quite sure why UDF defines
        # this as a 32-bit quantity, since there are no situations in which
        # this can be larger than 2048 minus 88).
        if self.length_impl_use > 424:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity implementation use length too large')
        if self.free_space_table != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Logical Volume Integrity free space table not 0')

        self.logical_volume_contents_use = UDFLogicalVolumeHeaderDescriptor()
        self.logical_volume_contents_use.parse(logical_volume_contents_use)

        self.logical_volume_impl_use = UDFLogicalVolumeImplementationUse()
        self.logical_volume_impl_use.parse(impl_use)

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF Logical Volume
        Integrity Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF Logical Volume Integrity Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Integrity Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.recording_date.record(), 1, 0, 0,
                          self.logical_volume_contents_use.record(), 1,
                          self.length_impl_use, self.free_space_table,
                          self.size_table,
                          self.logical_volume_impl_use.record())[16:]
        return self.desc_tag.record(rec[:118]) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF Logical Volume Integrity
        Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF Logical Volume Integrity Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Integrity Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF Logical Volume Integrity Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Integrity Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(9)  # FIXME: we should let the user set serial_number

        self.recording_date = UDFTimestamp()
        self.recording_date.new()

        self.length_impl_use = 46
        self.free_space_table = 0  # FIXME: let the user set this
        self.size_table = 3

        self.logical_volume_contents_use = UDFLogicalVolumeHeaderDescriptor()
        self.logical_volume_contents_use.new()

        self.logical_volume_impl_use = UDFLogicalVolumeImplementationUse()
        self.logical_volume_impl_use.new()

        self._initialized = True

    def set_location(self, new_location):
        '''
        A method to set the location of this UDF Logical Volume Integrity Descriptor.

        Parameters:
         new_location - The new extent this UDF Logical Volume Integrity Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF Logical Volume Integrity Descriptor not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = new_location


class UDFFileSetDescriptor(object):
    '''
    A class representing a UDF File Set Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'file_set_num', 'log_vol_char_set', 'log_vol_ident',
                 'file_set_char_set', 'file_set_ident', 'copyright_file_ident',
                 'abstract_file_ident', 'desc_tag', 'recording_date',
                 'domain_ident', 'root_dir_icb')

    FMT = '=16s12sHHLLLL64s128s64s32s32s32s16s32s16s48s'

    def __init__(self):
        self._initialized = False

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF File Set Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Set Descriptor already initialized')

        (tag_unused, recording_date, interchange_level, max_interchange_level,
         char_set_list, max_char_set_list, self.file_set_num, file_set_desc_num,
         self.log_vol_char_set, self.log_vol_ident,
         self.file_set_char_set, self.file_set_ident, self.copyright_file_ident,
         self.abstract_file_ident, root_dir_icb, domain_ident, next_extent,
         reserved_unused) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.recording_date = UDFTimestamp()
        self.recording_date.parse(recording_date)

        if interchange_level != 3:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if max_interchange_level != 3:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if char_set_list != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if max_char_set_list != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')
        if file_set_desc_num != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')

        self.domain_ident = UDFEntityID()
        self.domain_ident.parse(domain_ident)
        if self.domain_ident.identifier[:19] != b'*OSTA UDF Compliant':
            raise pycdlibexception.PyCdlibInvalidISO("File Set Descriptor Identifier not '*OSTA UDF Compliant'")

        self.root_dir_icb = UDFLongAD()
        self.root_dir_icb.parse(root_dir_icb)

        if next_extent != b'\x00' * 16:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-Only disks are supported')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF File Set
        Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF File Set Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Set Descriptor not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.recording_date.record(), 3, 3, 1, 1,
                          self.file_set_num, 0, self.log_vol_char_set,
                          self.log_vol_ident, self.file_set_char_set,
                          self.file_set_ident, self.copyright_file_ident,
                          self.abstract_file_ident, self.root_dir_icb.record(),
                          self.domain_ident.record(), b'\x00' * 16,
                          b'\x00' * 48)[16:]
        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF File Set Descriptor.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF File Set Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Set Descriptor not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self):
        '''
        A method to create a new UDF File Set Descriptor.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Set Descriptor already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(256)  # FIXME: we should let the user set serial_number

        self.recording_date = UDFTimestamp()
        self.recording_date.new()

        self.domain_ident = UDFEntityID()
        self.domain_ident.new(0, b'*OSTA UDF Compliant', b'\x02\x01\x03')

        self.root_dir_icb = UDFLongAD()
        self.root_dir_icb.new(2048, 2)

        self.file_set_num = 0
        self.log_vol_char_set = _unicodecharset()
        self.log_vol_ident = _ostaunicode_zero_pad('CDROM', 128)
        self.file_set_char_set = _unicodecharset()
        self.file_set_ident = _ostaunicode_zero_pad('CDROM', 32)
        self.copyright_file_ident = b'\x00' * 32  # FIXME: let the user set this
        self.abstract_file_ident = b'\x00' * 32  # FIXME: let the user set this

        self._initialized = True


class UDFICBTag(object):
    '''
    A class representing a UDF ICB Tag.
    '''
    __slots__ = ('_initialized', 'prior_num_direct_entries', 'strategy_type',
                 'strategy_param', 'max_num_entries', 'file_type',
                 'parent_icb_log_block_num', 'parent_icb_part_ref_num', 'flags')

    FMT = '=LHHHBBLHH'

    def __init__(self):
        self._initialized = False

    def parse(self, data):
        '''
        Parse the passed in data into a UDF ICB Tag.

        Parameters:
         data - The data to parse.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF ICB Tag already initialized')

        (self.prior_num_direct_entries, self.strategy_type, self.strategy_param,
         self.max_num_entries, reserved, self.file_type,
         self.parent_icb_log_block_num, self.parent_icb_part_ref_num,
         self.flags) = struct.unpack_from(self.FMT, data, 0)

        if self.strategy_type not in (4, 4096):
            raise pycdlibexception.PyCdlibInvalidISO('UDF ICB Tag invalid strategy type')

        if reserved != 0:
            raise pycdlibexception.PyCdlibInvalidISO('UDF ICB Tag reserved not 0')

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF ICB Tag.

        Parameters:
         None.
        Returns:
         A string representing this UDF ICB Tag.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF ICB Tag not initialized')

        return struct.pack(self.FMT, self.prior_num_direct_entries,
                           self.strategy_type, self.strategy_param,
                           self.max_num_entries, 0, self.file_type,
                           self.parent_icb_log_block_num,
                           self.parent_icb_part_ref_num, self.flags)

    def new(self, file_type):
        '''
        A method to create a new UDF ICB Tag.

        Parameters:
         file_type - What file type this represents, one of 'dir', 'file', or 'symlink'.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF ICB Tag already initialized')

        self.prior_num_direct_entries = 0  # FIXME: let the user set this
        self.strategy_type = 4
        self.strategy_param = 0  # FIXME: let the user set this
        self.max_num_entries = 1
        if file_type == 'dir':
            self.file_type = 4
        elif file_type == 'file':
            self.file_type = 5
        elif file_type == 'symlink':
            self.file_type = 12
        else:
            raise pycdlibexception.PyCdlibInternalError("Invalid file type for ICB; must be one of 'dir', 'file', or 'symlink'")

        self.parent_icb_log_block_num = 0  # FIXME: let the user set this
        self.parent_icb_part_ref_num = 0  # FIXME: let the user set this
        self.flags = 560  # hex 0x230 == binary 0010 0011 0000

        self._initialized = True


class UDFFileEntry(object):
    '''
    A class representing a UDF File Entry.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc', 'uid',
                 'gid', 'perms', 'file_link_count', 'info_len', 'hidden',
                 'log_block_recorded', 'unique_id', 'len_extended_attrs',
                 'desc_tag', 'icb_tag', 'alloc_descs', 'fi_descs', 'parent',
                 'access_time', 'mod_time', 'attr_time', 'extended_attr_icb',
                 'impl_ident', 'extended_attrs', 'file_ident', 'inode',
                 'is_sorted')

    FMT = '=16s20sLLLHBBLQQ12s12s12sL16s32sQLL'

    def __init__(self):
        self.alloc_descs = []
        self.fi_descs = []
        self._initialized = False
        self.parent = None
        self.hidden = False
        self.file_ident = None
        self.inode = None
        self.is_sorted = False

    def parse(self, data, extent, parent, desc_tag):
        '''
        Parse the passed in data into a UDF File Entry.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         parent - The parent File Entry for this file (may be None).
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry already initialized')

        (tag_unused, icb_tag, self.uid, self.gid, self.perms, self.file_link_count,
         record_format, record_display_attrs, record_len,
         self.info_len, self.log_block_recorded, access_time, mod_time,
         attr_time, checkpoint, extended_attr_icb, impl_ident, self.unique_id,
         self.len_extended_attrs, len_alloc_descs) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        self.icb_tag = UDFICBTag()
        self.icb_tag.parse(icb_tag)

        if record_format != 0:
            raise pycdlibexception.PyCdlibInvalidISO('File Entry record format is not 0')

        if record_display_attrs != 0:
            raise pycdlibexception.PyCdlibInvalidISO('File Entry record display attributes is not 0')

        if record_len != 0:
            raise pycdlibexception.PyCdlibInvalidISO('File Entry record length is not 0')

        self.access_time = UDFTimestamp()
        self.access_time.parse(access_time)

        self.mod_time = UDFTimestamp()
        self.mod_time.parse(mod_time)

        self.attr_time = UDFTimestamp()
        self.attr_time.parse(attr_time)

        if checkpoint != 1:
            raise pycdlibexception.PyCdlibInvalidISO('Only DVD Read-only disks supported')

        self.extended_attr_icb = UDFLongAD()
        self.extended_attr_icb.parse(extended_attr_icb)

        self.impl_ident = UDFEntityID()
        self.impl_ident.parse(impl_ident)

        offset = struct.calcsize(self.FMT)
        self.extended_attrs = data[offset:offset + self.len_extended_attrs]

        offset += self.len_extended_attrs
        num_alloc_descs = len_alloc_descs // 8  # a short_ad is 8 bytes
        for i_unused in range(0, num_alloc_descs):
            (length, pos) = struct.unpack('=LL', data[offset:offset + 8])
            self.alloc_descs.append([length, pos])
            offset += 8

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self.parent = parent

        self._initialized = True

    def record(self):
        '''
        A method to generate the string representing this UDF File Entry.

        Parameters:
         None.
        Returns:
         A string representing this UDF File Entry.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        rec = struct.pack(self.FMT, b'\x00' * 16,
                          self.icb_tag.record(), self.uid, self.gid,
                          self.perms, self.file_link_count, 0, 0, 0,
                          self.info_len, self.log_block_recorded,
                          self.access_time.record(), self.mod_time.record(),
                          self.attr_time.record(), 1,
                          self.extended_attr_icb.record(),
                          self.impl_ident.record(), self.unique_id,
                          self.len_extended_attrs, len(self.alloc_descs) * 8)[16:]
        rec += self.extended_attrs
        for length, pos in self.alloc_descs:
            rec += struct.pack('=LL', length, pos)

        return self.desc_tag.record(rec) + rec

    def extent_location(self):
        '''
        A method to get the extent location of this UDF File Entry.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF File Entry.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self, length, file_type, parent, log_block_size):
        '''
        A method to create a new UDF File Entry.

        Parameters:
         length - The (starting) length of this UDF File Entry; this is ignored
                  if this is a symlink.
         file_type - The type that this UDF File entry represents; one of 'dir', 'file', or 'symlink'.
         parent - The parent UDF File Entry for this UDF File Entry.
         log_block_size - The logical block size for extents.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry already initialized')

        if file_type not in ('dir', 'file', 'symlink'):
            raise pycdlibexception.PyCdlibInternalError("UDF File Entry file type must be one of 'dir', 'file', or 'symlink'")

        self.desc_tag = UDFTag()
        self.desc_tag.new(261)  # FIXME: we should let the user set serial_number

        self.icb_tag = UDFICBTag()
        self.icb_tag.new(file_type)

        self.uid = 4294967295  # Really -1, which means unset
        self.gid = 4294967295  # Really -1, which means unset
        if file_type == 'dir':
            self.perms = 5285
            self.file_link_count = 0
            self.info_len = 0
            self.log_block_recorded = 1
            # The second field (position) is bogus, but will get set
            # properly once reshuffle_extents is called.
            self.alloc_descs.append([length, 0])
        else:
            self.perms = 4228
            self.file_link_count = 1
            self.info_len = length
            self.log_block_recorded = utils.ceiling_div(length, log_block_size)
            len_left = length
            while len_left > 0:
                # According to Ecma-167 14.14.1.1, the least-significant 30 bits
                # of the allocation descriptor length field specify the length
                # (the most significant two bits are properties which we don't
                # currently support).  In theory we should then split files
                # into 2^30 = 0x40000000, but all implementations I've seen
                # split it into smaller.  cdrkit/cdrtools uses 0x3ffff800, and
                # Windows uses 0x3ff00000.  To be more compatible with cdrkit,
                # we'll choose their number of 0x3ffff800.
                alloc_len = min(len_left, 0x3ffff800)
                # The second field (position) is bogus, but will get set
                # properly once reshuffle_extents is called.
                self.alloc_descs.append([alloc_len, 0])
                len_left -= alloc_len

        self.access_time = UDFTimestamp()
        self.access_time.new()

        self.mod_time = UDFTimestamp()
        self.mod_time.new()

        self.attr_time = UDFTimestamp()
        self.attr_time.new()

        self.extended_attr_icb = UDFLongAD()
        self.extended_attr_icb.new(0, 0)

        self.impl_ident = UDFEntityID()
        self.impl_ident.new(0, b'*pycdlib')

        self.unique_id = 0  # this will get set later
        self.len_extended_attrs = 0  # FIXME: let the user set this

        self.extended_attrs = b''

        self.parent = parent

        self.is_sorted = True

        self._initialized = True

    def set_location(self, new_location, tag_location):
        '''
        A method to set the location of this UDF File Entry.

        Parameters:
         new_location - The new extent this UDF File Entry should be located at.
         tag_location - The new relative extent this UDF File Entry should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = tag_location
        self.unique_id = new_location

    def add_file_ident_desc(self, new_fi_desc, logical_block_size):
        '''
        A method to add a new UDF File Identifier Descriptor to this UDF File
        Entry.

        Parameters:
         new_fi_desc - The new UDF File Identifier Descriptor to add.
         logical_block_size - The logical block size to use.
        Returns:
         The number of extents added due to adding this File Identifier Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        if self.icb_tag.file_type != 4:
            raise pycdlibexception.PyCdlibInvalidInput('Can only add a UDF File Identifier to a directory')

        # If flags bit 3 is set, the entries are sorted.
        if self.icb_tag.flags & 0x8 or self.is_sorted:
            bisect.insort_left(self.fi_descs, new_fi_desc)
        else:
            self.fi_descs.append(new_fi_desc)

        num_bytes_to_add = UDFFileIdentifierDescriptor.length(len(new_fi_desc.fi))

        old_num_extents = 0
        # If info_len is 0, then this is a brand-new File Entry, and thus the
        # number of extents it is using is 0.
        if self.info_len > 0:
            old_num_extents = utils.ceiling_div(self.info_len, logical_block_size)

        self.info_len += num_bytes_to_add
        new_num_extents = utils.ceiling_div(self.info_len, logical_block_size)

        self.log_block_recorded = new_num_extents

        self.alloc_descs[0][0] = self.info_len
        if new_fi_desc.is_dir():
            self.file_link_count += 1

        return new_num_extents - old_num_extents

    def remove_file_ident_desc_by_name(self, name, logical_block_size):
        '''
        A method to remove a UDF File Identifier Descriptor from this UDF File
        Entry.

        Parameters:
         name - The name of the UDF File Identifier Descriptor to remove.
         logical_block_size - The logical block size to use.
        Returns:
         The number of extents removed due to removing this File Identifier Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        tmp_fi_desc = UDFFileIdentifierDescriptor()
        tmp_fi_desc.isparent = False
        tmp_fi_desc.fi = name

        # If flags bit 3 is set, the entries are sorted.
        if self.icb_tag.flags & 0x8 or self.is_sorted:
            desc_index = bisect.bisect_left(self.fi_descs, tmp_fi_desc)
        else:
            desc_index = len(self.fi_descs)
            for index, fi_desc in enumerate(self.fi_descs):
                if fi_desc.fi == name:
                    desc_index = index
                    break
        if desc_index == len(self.fi_descs) or self.fi_descs[desc_index].fi != name:
            raise pycdlibexception.PyCdlibInvalidInput('Cannot find file to remove')

        this_desc = self.fi_descs[desc_index]
        if this_desc.is_dir():
            if len(this_desc.file_entry.fi_descs) > 1:
                raise pycdlibexception.PyCdlibInvalidInput('Directory must be empty to use rm_directory')
            self.file_link_count -= 1

        old_num_extents = utils.ceiling_div(self.info_len, logical_block_size)
        self.info_len -= UDFFileIdentifierDescriptor.length(len(this_desc.fi))
        new_num_extents = utils.ceiling_div(self.info_len, logical_block_size)
        self.alloc_descs[0][0] = self.info_len

        del self.fi_descs[desc_index]

        return old_num_extents - new_num_extents

    def set_data_location(self, current_extent, start_extent):  # pylint: disable=unused-argument
        '''
        A method to set the location of the data that this UDF File Entry
        points to.

        Parameters:
         current_extent - Unused
         start_extent - The starting extent for this data location.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        current_assignment = start_extent
        for index, desc_unused in enumerate(self.alloc_descs):
            self.alloc_descs[index][1] = current_assignment
            current_assignment += 1

    def get_data_length(self):
        '''
        A method to get the length of the data that this UDF File Entry
        points to.

        Parameters:
         None.
        Returns:
         The length of the data that this UDF File Entry points to.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')
        return self.info_len

    def set_data_length(self, length):
        '''
        A method to set the length of the data that this UDF File Entry
        points to.

        Parameters:
         length - The new length for the data.
        Returns:
         The length of the data that this Directory Record points to.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Directory Record not yet initialized')

        len_diff = length - self.info_len
        if len_diff > 0:
            # If we are increasing the length, update the last alloc_desc up
            # to the max of 0x3ffff800, and throw an exception if we overflow.
            new_len = self.alloc_descs[-1][0] + len_diff
            if new_len > 0x3ffff800:
                raise pycdlibexception.PyCdlibInvalidInput('Cannot increase the size of a UDF file beyond the current descriptor')
            self.alloc_descs[-1][0] = new_len
        elif len_diff < 0:
            # We are decreasing the length.  It's possible we are removing one
            # or more alloc_descs, so run through the list updating all of the
            # descriptors and remove any we no longer need.
            len_left = length
            alloc_descs_needed = 0
            index = 0
            while len_left > 0:
                this_len = min(len_left, 0x3ffff800)
                alloc_descs_needed += 1
                self.alloc_descs[index][0] = this_len
                index += 1
                len_left -= this_len

            self.alloc_descs = self.alloc_descs[:alloc_descs_needed]

        self.info_len = length

    def is_file(self):
        '''
        A method to determine whether this UDF File Entry points to a file.

        Parameters:
         None.
        Returns:
         True if this UDF File Entry points to a file, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')
        return self.icb_tag.file_type == 5

    def is_symlink(self):
        '''
        A method to determine whether this UDF File Entry points to a symlink.

        Parameters:
         None.
        Returns:
         True if this UDF File Entry points to a symlink, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')
        return self.icb_tag.file_type == 12

    def is_dir(self):
        '''
        A method to determine whether this UDF File Entry points to a directory.

        Parameters:
         None.
        Returns:
         True if this UDF File Entry points to a directory, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')
        return self.icb_tag.file_type == 4

    def file_identifier(self):
        '''
        A method to get the name of this UDF File Entry as a byte string.

        Parameters:
         None.
        Returns:
         The UDF File Entry as a byte string.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        if self.file_ident is None:
            return b'/'

        return self.file_ident.fi

    def find_file_ident_desc_by_name(self, currpath):
        '''
        A method to find a UDF File Identifier descriptor by its name.

        Parameters:
         currpath - The UTF-8 encoded name to look up.
        Returns:
         The UDF File Identifier descriptor corresponding to the passed in name.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        # If this is a directory or it is an empty directory, just skip
        # all work.
        if self.icb_tag.file_type != 4 or not self.fi_descs:
            return None

        tmp = currpath.decode('utf-8')
        try:
            latin1_currpath = tmp.encode('latin-1')
        except (UnicodeDecodeError, UnicodeEncodeError):
            latin1_currpath = None
        ucs2_currpath = tmp.encode('utf-16_be')

        child = None

        # If flags bit 3 is set, the entries are sorted.
        if self.icb_tag.flags & 0x8 or self.is_sorted:
            lo = 1
            hi = len(self.fi_descs)
            while lo < hi:
                mid = (lo + hi) // 2
                fi_desc = self.fi_descs[mid]
                if latin1_currpath is not None and fi_desc.encoding == 'latin-1':
                    lt = fi_desc.fi < latin1_currpath
                else:
                    lt = fi_desc.fi < ucs2_currpath

                if lt:
                    lo = mid + 1
                else:
                    hi = mid
            index = lo
            if index != len(self.fi_descs) and (self.fi_descs[index].fi == latin1_currpath or self.fi_descs[index].fi == ucs2_currpath):
                child = self.fi_descs[index]
        else:
            for fi_desc in self.fi_descs:
                if latin1_currpath is not None and fi_desc.encoding == 'latin-1':
                    eq = fi_desc.fi == latin1_currpath
                else:
                    eq = fi_desc.fi == ucs2_currpath

                if eq:
                    child = fi_desc
                    break

        return child

    def track_file_ident_desc(self, file_ident):
        '''
        A method to start tracking a UDF File Identifier descriptor in this
        UDF File Entry.  Both 'tracking' and 'addition' add the identifier to
        the list of file identifiers, but tracking doees not expand or
        otherwise modify the UDF File Entry.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        # If flags bit 3 is set, the entries are sorted.
        if self.icb_tag.flags & 0x8 or self.is_sorted:
            bisect.insort_left(self.fi_descs, file_ident)
        else:
            self.fi_descs.append(file_ident)

    def finish_directory_parse(self):
        '''
        A method to finish up the parsing of this UDF File Entry directory.
        In particular, this method checks to see if it is in sorted order for
        future use.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Entry not initialized')

        if self.icb_tag.file_type != 4:
            raise pycdlibexception.PyCdlibInternalError('Can only finish_directory for a directory')

        # Here we run through and check to see if all of the entries are sorted;
        # we'll use this information later on when manipulating the children.
        for i in range(1, len(self.fi_descs)):
            if self.fi_descs[i] < self.fi_descs[i - 1]:
                break
        else:
            self.is_sorted = True


class UDFFileIdentifierDescriptor(object):
    '''
    A class representing a UDF File Identifier Descriptor.
    '''
    __slots__ = ('_initialized', 'orig_extent_loc', 'new_extent_loc',
                 'desc_tag', 'file_characteristics', 'len_fi', 'len_impl_use',
                 'fi', 'isdir', 'isparent', 'icb', 'impl_use', 'file_entry',
                 'encoding')

    FMT = '=16sHBB16sH'

    def __init__(self):
        self.file_entry = None
        self._initialized = False
        self.fi = b''
        self.encoding = None
        self.isparent = False
        self.isdir = False

    @classmethod
    def length(cls, namelen):
        '''
        A class method to calculate the size this UDFFileIdentifierDescriptor
        would take up.

        Parameters:
         cls - The class to use (always UDFFileIdentifierDescriptor).
         namelen - The length of the name.
        Returns:
         The length that the UDFFileIdentifierDescriptor would take up.
        '''
        if namelen > 0:
            namelen += 1
        to_add = struct.calcsize(cls.FMT) + namelen
        return to_add + UDFFileIdentifierDescriptor.pad(to_add)

    @staticmethod
    def pad(val):
        '''
        A static method to calculate the amount of padding necessary for this
        UDF File Identifer Descriptor.

        Parameters:
         val - The amount of non-padded space this UDF File Identifier
               Descriptor uses.
        Returns:
         The amount of padding necessary to make this a compliant UDF File
         Identifier Descriptor.
        '''
        return (4 * ((val + 3) // 4)) - val

    def parse(self, data, extent, desc_tag):
        '''
        Parse the passed in data into a UDF File Identifier Descriptor.

        Parameters:
         data - The data to parse.
         extent - The extent that this descriptor currently lives at.
         desc_tag - A UDFTag object that represents the Descriptor Tag.
        Returns:
         The number of bytes this descriptor consumed.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier Descriptor already initialized')

        (tag_unused, file_version_num, self.file_characteristics,
         self.len_fi, icb, self.len_impl_use) = struct.unpack_from(self.FMT, data, 0)

        self.desc_tag = desc_tag

        if file_version_num != 1:
            raise pycdlibexception.PyCdlibInvalidISO('File Identifier Descriptor file version number not 1')

        if self.file_characteristics & 0x2:
            self.isdir = True

        if self.file_characteristics & 0x8:
            self.isparent = True

        self.icb = UDFLongAD()
        self.icb.parse(icb)

        start = struct.calcsize(self.FMT)
        end = start + self.len_impl_use
        self.impl_use = data[start:end]

        start = end
        end = start + self.len_fi
        # The very first byte of the File Identifier describes whether this is
        # an 8-bit or 16-bit encoded string; this corresponds to whether we
        # encode with 'latin-1' or with 'utf-16_be'.  We save that off because we have
        # to write the correct thing out when we record.
        if not self.isparent:
            encoding = bytes(bytearray([data[start]]))
            if encoding == b'\x08':
                self.encoding = 'latin-1'
            elif encoding == b'\x10':
                self.encoding = 'utf-16_be'
            else:
                raise pycdlibexception.PyCdlibInvalidISO('Only UDF File Identifier Descriptor Encodings 8 or 16 are supported')

            start += 1

            self.fi = data[start:end]

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self._initialized = True

        return end + UDFFileIdentifierDescriptor.pad(end)

    def is_dir(self):
        '''
        A method to determine if this File Identifier represents a directory.

        Parameters:
         None.
        Returns:
         True if this File Identifier represents a directory, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier Descriptor not initialized')
        return self.isdir

    def is_parent(self):
        '''
        A method to determine if this File Identifier is a 'parent' (essentially ..).

        Parameters:
         None.
        Returns:
         True if this File Identifier is a parent, False otherwise.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier Descriptor not initialized')
        return self.isparent

    def record(self):
        '''
        A method to generate the string representing this UDF File Identifier Descriptor.

        Parameters:
         None.
        Returns:
         A string representing this UDF File Identifier Descriptor.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier Descriptor not initialized')

        if self.len_fi > 0:
            if self.encoding == 'latin-1':
                prefix = b'\x08'
            elif self.encoding == 'utf-16_be':
                prefix = b'\x10'
            else:
                raise pycdlibexception.PyCdlibInternalError('Invalid UDF encoding; this should not happen')

            fi = prefix + self.fi
        else:
            fi = b''
        rec = struct.pack(self.FMT, b'\x00' * 16, 1,
                          self.file_characteristics, self.len_fi,
                          self.icb.record(),
                          self.len_impl_use) + self.impl_use + fi + b'\x00' * UDFFileIdentifierDescriptor.pad(struct.calcsize(self.FMT) + self.len_impl_use + self.len_fi)
        return self.desc_tag.record(rec[16:]) + rec[16:]

    def extent_location(self):
        '''
        A method to get the extent location of this UDF File Identifier.

        Parameters:
         None.
        Returns:
         Integer extent location of this UDF File Identifier.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier not initialized')

        if self.new_extent_loc is None:
            return self.orig_extent_loc
        return self.new_extent_loc

    def new(self, isdir, isparent, name):
        '''
        A method to create a new UDF File Identifier.

        Parameters:
         isdir - Whether this File Identifier is a directory.
         isparent - Whether this File Identifier is a parent (..).
         name - The name for this File Identifier.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier already initialized')

        self.desc_tag = UDFTag()
        self.desc_tag.new(257)  # FIXME: we should let the user set serial_number

        self.icb = UDFLongAD()
        self.icb.new(2048, 2)

        self.isdir = isdir
        self.isparent = isparent
        self.file_characteristics = 0
        if self.isdir:
            self.file_characteristics |= 0x2
        if self.isparent:
            self.file_characteristics |= 0x8
        self.len_impl_use = 0  # FIXME: need to let the user set this

        self.impl_use = b''

        self.len_fi = 0
        if not isparent:
            bytename = name.decode('utf-8')
            try:
                self.fi = bytename.encode('latin-1')
                self.encoding = 'latin-1'
            except UnicodeEncodeError:
                self.fi = bytename.encode('utf-16_be')
                self.encoding = 'utf-16_be'
            self.len_fi = len(self.fi) + 1

        self._initialized = True

    def set_location(self, new_location, tag_location):
        '''
        A method to set the location of this UDF File Identifier Descriptor.
        Note that many UDF File Identifier Descriptors may have the same
        starting extent.

        Parameters:
         new_location - The new extent this UDF File Identifier Descriptor should be located at.
         tag_location - The new relative extent this UDF File Identifier Descriptor should be located at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier not initialized')

        self.new_extent_loc = new_location
        self.desc_tag.tag_location = tag_location

    def set_icb(self, new_location, tag_location):
        '''
        A method to set the location of the data that this UDF File Identifier
        Descriptor points at.  The data can either be for a directory or for a
        file.

        Parameters:
         new_location - The new extent this UDF File Identifier Descriptor data lives at.
         tag_location - The new relative extent this UDF File Identifier Descriptor data lives at.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('UDF File Identifier not initialized')

        self.icb.set_location(new_location, tag_location)

    def __lt__(self, other):
        if self.isparent:
            if other.isparent:
                return False
            return True
        elif other.isparent:
            return False

        return self.fi < other.fi

    def __eq__(self, other):
        if self.isparent:
            if other.isparent:
                return True
            return False
        elif other.isparent:
            return False

        return self.fi == other.fi


def symlink_to_bytes(symlink_target):
    '''
    A function to generate UDF symlink data from a Unix-like path.

    Parameters:
     symlink_target - The Unix-like path that is the symlink.
    Returns:
     The UDF data corresponding to the symlink.
    '''
    symlink_data = bytearray()
    for comp in symlink_target.split('/'):
        if comp == '':
            # If comp is empty, then we know this is the leading slash
            # and we should make an absolute entry (double slashes and
            # such are weeded out by the earlier utils.normpath).
            symlink_data.extend(b'\x02\x00\x00\x00')
        elif comp == '.':
            symlink_data.extend(b'\x04\x00\x00\x00')
        elif comp == '..':
            symlink_data.extend(b'\x03\x00\x00\x00')
        else:
            symlink_data.extend(b'\x05')
            ostaname = _ostaunicode(comp)
            symlink_data.append(len(ostaname))
            symlink_data.extend(b'\x00\x00')
            symlink_data.extend(ostaname)

    return symlink_data
