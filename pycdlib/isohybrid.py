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
Implementation of ISO hybrid support.
'''

from __future__ import absolute_import

import random
import struct

import pycdlib.pycdlibexception as pycdlibexception


class IsoHybrid(object):
    '''
    A class that represents an ISO hybrid; that is, an ISO that can be booted
    via CD or via an alternate boot mechanism (such as USB).
    '''
    __slots__ = ('_initialized', 'header', 'mbr', 'rba', 'mbr_id', 'part_entry',
                 'bhead', 'bsect', 'bcyle', 'ptype', 'ehead', 'esect', 'ecyle',
                 'part_offset', 'psize', 'geometry_heads', 'geometry_sectors')

    FMT = '=400sLLLH'
    ORIG_HEADER = b'\x33\xed' + b'\x90' * 30
    MAC_AFP = b'\x45\x52\x08\x00\x00\x00\x90\x90' + b'\x00' * 24

    def __init__(self):
        self._initialized = False

    def parse(self, instr):
        '''
        A method to parse ISO hybridization info out of an existing ISO.

        Parameters:
         instr - The data for the ISO hybridization.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('This IsoHybrid object is already initialized')

        if len(instr) != 512:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid size of the instr')

        if instr[0:32] == self.ORIG_HEADER:
            self.header = self.ORIG_HEADER
        elif instr[0:32] == self.MAC_AFP:
            self.header = self.MAC_AFP
        else:
            # If we didn't see anything that we expected, then this is not an
            # IsoHybrid ISO, so just quietly return False
            return False

        (self.mbr, self.rba, unused1, self.mbr_id,
         unused2) = struct.unpack_from(self.FMT, instr[:32 + struct.calcsize(self.FMT)], 32)

        if unused1 != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid IsoHybrid section')

        if unused2 != 0:
            raise pycdlibexception.PyCdlibInvalidISO('Invalid IsoHybrid section')

        offset = 32 + struct.calcsize(self.FMT)
        for i in range(1, 5):
            if bytes(bytearray([instr[offset]])) == b'\x80':
                self.part_entry = i
                (const_unused, self.bhead, self.bsect, self.bcyle, self.ptype,
                 self.ehead, self.esect, self.ecyle, self.part_offset,
                 self.psize) = struct.unpack_from('=BBBBBBBBLL', instr[:offset + 16], offset)
                break
            offset += 16
        else:
            raise pycdlibexception.PyCdlibInvalidISO('No valid partition found in IsoHybrid!')

        if bytes(bytearray([instr[-2]])) != b'\x55' or bytes(bytearray([instr[-1]])) != b'\xaa':
            raise pycdlibexception.PyCdlibInvalidISO('Invalid tail on isohybrid section')

        self.geometry_heads = self.ehead + 1
        # FIXME: I can't see any way to compute the number of sectors from the
        # available information.  For now, we just hard-code this at 32 and
        # hope for the best.
        self.geometry_sectors = 32

        self._initialized = True

        return True

    def new(self, mac, part_entry, mbr_id, part_offset,
            geometry_sectors, geometry_heads, part_type):
        '''
        A method to add ISO hybridization to an ISO.

        Parameters:
         mac - Whether this ISO should be made bootable for the Macintosh.
         part_entry - The partition entry for the hybridization.
         mbr_id - The mbr_id to use for the hybridization.
         part_offset - The partition offset to use for the hybridization.
         geometry_sectors - The number of sectors to use for the hybridization.
         geometry_heads - The number of heads to use for the hybridization.
         part_type - The partition type for the hybridization.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('This IsoHybrid object is already initialized')

        if mac:
            self.header = self.MAC_AFP
        else:
            self.header = self.ORIG_HEADER

        isohybrid_data_hd0 = b'\x33\xed\xfa\x8e\xd5\xbc\x00\x7c\xfb\xfc\x66\x31\xdb\x66\x31\xc9\x66\x53\x66\x51\x06\x57\x8e\xdd\x8e\xc5\x52\xbe\x00\x7c\xbf\x00\x06\xb9\x00\x01\xf3\xa5\xea\x4b\x06\x00\x00\x52\xb4\x41\xbb\xaa\x55\x31\xc9\x30\xf6\xf9\xcd\x13\x72\x16\x81\xfb\x55\xaa\x75\x10\x83\xe1\x01\x74\x0b\x66\xc7\x06\xf1\x06\xb4\x42\xeb\x15\xeb\x00\x5a\x51\xb4\x08\xcd\x13\x83\xe1\x3f\x5b\x51\x0f\xb6\xc6\x40\x50\xf7\xe1\x53\x52\x50\xbb\x00\x7c\xb9\x04\x00\x66\xa1\xb0\x07\xe8\x44\x00\x0f\x82\x80\x00\x66\x40\x80\xc7\x02\xe2\xf2\x66\x81\x3e\x40\x7c\xfb\xc0\x78\x70\x75\x09\xfa\xbc\xec\x7b\xea\x44\x7c\x00\x00\xe8\x83\x00\x69\x73\x6f\x6c\x69\x6e\x75\x78\x2e\x62\x69\x6e\x20\x6d\x69\x73\x73\x69\x6e\x67\x20\x6f\x72\x20\x63\x6f\x72\x72\x75\x70\x74\x2e\x0d\x0a\x66\x60\x66\x31\xd2\x66\x03\x06\xf8\x7b\x66\x13\x16\xfc\x7b\x66\x52\x66\x50\x06\x53\x6a\x01\x6a\x10\x89\xe6\x66\xf7\x36\xe8\x7b\xc0\xe4\x06\x88\xe1\x88\xc5\x92\xf6\x36\xee\x7b\x88\xc6\x08\xe1\x41\xb8\x01\x02\x8a\x16\xf2\x7b\xcd\x13\x8d\x64\x10\x66\x61\xc3\xe8\x1e\x00\x4f\x70\x65\x72\x61\x74\x69\x6e\x67\x20\x73\x79\x73\x74\x65\x6d\x20\x6c\x6f\x61\x64\x20\x65\x72\x72\x6f\x72\x2e\x0d\x0a\x5e\xac\xb4\x0e\x8a\x3e\x62\x04\xb3\x07\xcd\x10\x3c\x0a\x75\xf1\xcd\x18\xf4\xeb\xfd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        self.mbr = isohybrid_data_hd0
        self.rba = 0  # This will be set later
        self.mbr_id = mbr_id
        if self.mbr_id is None:
            self.mbr_id = random.getrandbits(32)

        self.part_entry = part_entry
        self.bhead = (part_offset // geometry_sectors) % geometry_heads
        self.bsect = (part_offset % geometry_sectors) + 1
        self.bcyle = part_offset // (geometry_heads * geometry_sectors)
        self.bsect += (self.bcyle & 0x300) >> 2
        self.bcyle &= 0xff
        self.ptype = part_type
        self.ehead = geometry_heads - 1
        self.part_offset = part_offset
        self.geometry_heads = geometry_heads
        self.geometry_sectors = geometry_sectors

        self._initialized = True

    def _calc_cc(self, iso_size):
        '''
        A method to calculate the 'cc' and the 'padding' values for this
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
        cc = (iso_size + padding) // cylsize
        if cc > 1024:
            cc = 1024

        return (cc, padding)

    def record(self, iso_size):
        '''
        A method to generate a string containing the ISO hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A string containing the ISO hybridization.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('This IsoHybrid object is not yet initialized')

        outlist = [struct.pack('=32s400sLLLH', self.header, self.mbr, self.rba,
                               0, self.mbr_id, 0)]

        for i in range(1, 5):
            if i == self.part_entry:
                cc, padding_unused = self._calc_cc(iso_size)
                esect = self.geometry_sectors + (((cc - 1) & 0x300) >> 2)
                ecyle = (cc - 1) & 0xff
                psize = cc * self.geometry_heads * self.geometry_sectors - self.part_offset
                outlist.append(struct.pack('=BBBBBBBBLL', 0x80, self.bhead,
                                           self.bsect, self.bcyle, self.ptype,
                                           self.ehead, esect, ecyle,
                                           self.part_offset, psize))
            else:
                outlist.append(b'\x00' * 16)
        outlist.append(b'\x55\xaa')

        return b''.join(outlist)

    def record_padding(self, iso_size):
        '''
        A method to record padding for the ISO hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A string of zeros the right size to pad the ISO.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('This IsoHybrid object is not yet initialized')

        return b'\x00' * self._calc_cc(iso_size)[1]

    def update_rba(self, current_extent):
        '''
        A method to update the current rba for the ISO hybridization.

        Parameters:
         current_extent - The new extent to set the RBA to.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('This IsoHybrid object is not yet initialized')

        self.rba = current_extent
