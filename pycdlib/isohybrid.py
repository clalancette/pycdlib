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

import struct
import random

import pycdlib.pycdlibexception as pycdlibexception

class IsoHybrid(object):
    '''
    A class that represents an ISO hybrid; that is, an ISO that can be booted
    via CD or via an alternate boot mechanism (such as USB).
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
            raise pycdlibexception.PyCdlibException("This IsoHybrid object is already initialized")

        if len(instr) != 512:
            raise pycdlibexception.PyCdlibException("Invalid size of the instr")

        (self.mbr, self.rba, unused1, self.mbr_id, unused2) = struct.unpack_from(self.fmt, instr[:struct.calcsize(self.fmt)], 0)

        if unused1 != 0:
            raise pycdlibexception.PyCdlibException("Invalid IsoHybrid section")

        if unused2 != 0:
            raise pycdlibexception.PyCdlibException("Invalid IsoHybrid section")

        offset = struct.calcsize(self.fmt)
        self.part_entry = None
        for i in range(1, 5):
            if bytes(bytearray([instr[offset]])) == b'\x80':
                self.part_entry = i
                (const_unused, self.bhead, self.bsect, self.bcyle, self.ptype,
                 self.ehead, self.esect, self.ecyle, self.part_offset,
                 self.psize) = struct.unpack_from("=BBBBBBBBLL", instr[:offset+16], offset)
                break
            offset += 16

        if self.part_entry is None:
            raise pycdlibexception.PyCdlibException("No valid partition found in IsoHybrid!")

        if bytes(bytearray([instr[-2]])) != b'\x55' or bytes(bytearray([instr[-1]])) != b'\xaa':
            raise pycdlibexception.PyCdlibException("Invalid tail on isohybrid section")

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
            raise pycdlibexception.PyCdlibException("This IsoHybrid object is already initialized")

        self.mbr = instr
        self.rba = rba
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
        cc = (iso_size + padding) // cylsize
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
            raise pycdlibexception.PyCdlibException("This IsoHybrid object is not yet initialized")

        outlist = [struct.pack("=432sLLLH", self.mbr, self.rba, 0, self.mbr_id, 0)]

        for i in range(1, 5):
            if i == self.part_entry:
                cc,padding_unused = self._calc_cc(iso_size)
                esect = self.geometry_sectors + (((cc - 1) & 0x300) >> 2)
                ecyle = (cc - 1) & 0xff
                psize = cc * self.geometry_heads * self.geometry_sectors - self.part_offset
                outlist.append(struct.pack("=BBBBBBBBLL", 0x80, self.bhead, self.bsect,
                                           self.bcyle, self.ptype, self.ehead,
                                           esect, ecyle, self.part_offset, psize))
            else:
                outlist.append(b'\x00'*16)
        outlist.append(b'\x55\xaa')

        return b"".join(outlist)

    def record_padding(self, iso_size):
        '''
        A method to record padding for the ISO hybridization.

        Parameters:
         iso_size - The size of the ISO, excluding the hybridization.
        Returns:
         A string of zeros the right size to pad the ISO.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This IsoHybrid object is not yet initialized")

        return b'\x00'*self._calc_cc(iso_size)[1]
