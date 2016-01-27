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
Classes to support El Torito.
'''

import struct

import pyisoexception
import utils

class EltoritoValidationEntry(object):
    '''
    A class that represents an El Torito Validation Entry.  El Torito requires
    that the first entry in the El Torito Boot Catalog be a validation entry.
    '''
    def __init__(self):
        self.initialized = False
        # An El Torito validation entry consists of:
        # Offset 0x0:       Header ID (0x1)
        # Offset 0x1:       Platform ID (0 for x86, 1 for PPC, 2 for Mac)
        # Offset 0x2-0x3:   Reserved, must be 0
        # Offset 0x4-0x1b:  ID String for manufacturer of CD
        # Offset 0x1c-0x1d: Checksum of all bytes.
        # Offset 0x1e:      Key byte 0x55
        # Offset 0x1f:      Key byte 0xaa
        self.fmt = "=BBH24sHBB"

    @staticmethod
    def _checksum(data):
        '''
        A static method to compute the checksum on the ISO.  Note that this is
        *not* a 1's complement checksum; when an addition overflows, the carry
        bit is discarded, not added to the end.
        '''
        s = 0
        for i in range(0, len(data), 2):
            w = ord(data[i]) + (ord(data[i+1]) << 8)
            s = (s + w) & 0xffff
        return s

    def parse(self, valstr):
        '''
        A method to parse an El Torito Validation Entry out of a string.

        Parameters:
         valstr - The string to parse the El Torito Validation Entry out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Validation Entry already initialized")

        (self.header_id, self.platform_id, reserved, self.id_string,
         self.checksum, self.keybyte1,
         self.keybyte2) = struct.unpack(self.fmt, valstr)

        if self.header_id != 1:
            raise pyisoexception.PyIsoException("El Torito Validation entry header ID not 1")

        if self.platform_id not in [0, 1, 2]:
            raise pyisoexception.PyIsoException("El Torito Validation entry platform ID not valid")

        if self.keybyte1 != 0x55:
            raise pyisoexception.PyIsoException("El Torito Validation entry first keybyte not 0x55")
        if self.keybyte2 != 0xaa:
            raise pyisoexception.PyIsoException("El Torito Validation entry second keybyte not 0xaa")

        # Now that we've done basic checking, calculate the checksum of the
        # validation entry and make sure it is right.
        if self._checksum(valstr) != 0:
            raise pyisoexception.PyIsoException("El Torito Validation entry checksum not correct")

        self.initialized = True

    def new(self, platform_id):
        '''
        A method to create a new El Torito Validation Entry.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Validation Entry already initialized")

        self.header_id = 1
        self.platform_id = platform_id
        self.id_string = "\x00"*24 # FIXME: let the user set this
        self.keybyte1 = 0x55
        self.keybyte2 = 0xaa
        self.checksum = 0
        self.checksum = utils.swab_16bit(self._checksum(self._record()) - 1)
        self.initialized = True

    def _record(self):
        '''
        An internal method to generate a string representing this El Torito
        Validation Entry.

        Parameters:
         None.
        Returns:
         String representing this El Torito Validation Entry.
        '''
        return struct.pack(self.fmt, self.header_id, self.platform_id, 0, self.id_string, self.checksum, self.keybyte1, self.keybyte2)

    def record(self):
        '''
        A method to generate a string representing this El Torito Validation
        Entry.

        Parameters:
         None.
        Returns:
         String representing this El Torito Validation Entry.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Validation Entry not yet initialized")

        return self._record()

class EltoritoInitialEntry(object):
    '''
    A class that represents an El Torito Initial Entry.  El Torito requires that
    there is one initial entry in an El Torito Boot Catalog.
    '''
    def __init__(self):
        self.initialized = False
        # An El Torito initial entry consists of:
        # Offset 0x0:      Boot indicator (0x88 for bootable, 0x00 for
        #                  non-bootable)
        # Offset 0x1:      Boot media type.  One of 0x0 for no emulation,
        #                  0x1 for 1.2M diskette emulation, 0x2 for 1.44M
        #                  diskette emulation, 0x3 for 2.88M diskette
        #                  emulation, or 0x4 for Hard Disk emulation.
        # Offset 0x2-0x3:  Load Segment - if 0, use traditional 0x7C0.
        # Offset 0x4:      System Type - copy of Partition Table byte 5
        # Offset 0x5:      Unused, must be 0
        # Offset 0x6-0x7:  Sector Count - Number of virtual sectors to store
        #                  during initial boot.
        # Offset 0x8-0xb:  Load RBA - Start address of virtual disk.
        # Offset 0xc-0x1f: Unused, must be 0.
        self.fmt = "=BBHBBHL20s"

    def parse(self, valstr):
        '''
        A method to parse an El Torito Initial Entry out of a string.

        Parameters:
         valstr - The string to parse the El Torito Initial Entry out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Initial Entry already initialized")

        (self.boot_indicator, self.boot_media_type, self.load_segment,
         self.system_type, unused1, self.sector_count, self.load_rba,
         unused2) = struct.unpack(self.fmt, valstr)

        if self.boot_indicator not in [0x88, 0x00]:
            raise pyisoexception.PyIsoException("Invalid eltorito initial entry boot indicator")
        if self.boot_media_type > 4:
            raise pyisoexception.PyIsoException("Invalid eltorito boot media type")

        # FIXME: check that the system type matches the partition table

        if unused1 != 0:
            raise pyisoexception.PyIsoException("El Torito unused field must be 0")

        # According to the specification, the El Torito unused end field (bytes
        # 0xc - 0x1f, unused2 field) should be all zero.  However, we have found
        # ISOs in the wild where that is not the case, so skip that particular
        # check here.

        self.initialized = True

    def new(self, sector_count):
        '''
        A method to create a new El Torito Initial Entry.

        Parameters:
         sector_count - The number of sectors to assign to this El Torito
                        Initial Entry.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Initial Entry already initialized")

        self.boot_indicator = 0x88 # FIXME: let the user set this
        self.boot_media_type = 0 # FIXME: let the user set this
        self.load_segment = 0x0 # FIXME: let the user set this
        self.system_type = 0
        self.sector_count = sector_count
        self.load_rba = 0 # This will get set later

        self.initialized = True

    def set_rba(self, new_rba):
        '''
        A method to set the load_rba for this El Torito Initial Entry.

        Parameters:
         new_rba - The new address to set for the El Torito Initial Entry.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Initial Entry not yet initialized")

        self.load_rba = new_rba

    def record(self):
        '''
        A method to generate a string representing this El Torito Initial
        Entry.

        Parameters:
         None.
        Returns:
         String representing this El Torito Initial Entry.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Initial Entry not yet initialized")

        return struct.pack(self.fmt, self.boot_indicator, self.boot_media_type,
                           self.load_segment, self.system_type, 0,
                           self.sector_count, self.load_rba, '\x00'*20)

class EltoritoSectionHeader(object):
    '''
    A class that represents an El Torito Section Header.
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=BBH28s"

    def parse(self, valstr):
        '''
        Parse an El Torito section header from a string.

        Parameters:
         valstr - The string to parse.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Section Header already initialized")

        (self.header_indicator, self.platform_id, self.num_section_entries,
         self.id_string) = struct.unpack(self.fmt, valstr)

        self.initialized = True

    def new(self, id_string):
        '''
        Create a new El Torito section header.

        Parameters:
         id_string - The ID to use for this section header.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Section Header already initialized")

        self.header_indicator = 0x90 # FIXME: how should we deal with this?
        self.platform_id = 0 # FIXME: we should allow the user to set this
        self.num_section_entries = 0
        self.id_string = id_string
        self.initialized = True

    def record(self):
        '''
        Get a string representing this El Torito section header.

        Parameters:
         None.
        Returns:
         A string representing this El Torito section header.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Section Header not yet initialized")

        return struct.pack(self.fmt, self.header_indicator, self.platform_id,
                           self.num_section_entries, self.id_string)

class EltoritoSectionEntry(object):
    '''
    A class that represents an El Torito Section Entry.
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=BBHBBHLB19s"

    def parse(self, valstr):
        '''
        Parse an El Torito section entry from a string.

        Parameters:
         valstr - The string to parse.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Section Header already initialized")

        (self.boot_indicator, self.boot_media_type, self.load_segment,
         self.system_type, unused1, self.sector_count, self.load_rba,
         self.selection_criteria_type,
         self.selection_criteria) = struct.unpack(self.fmt, valstr)

        # FIXME: check that the system type matches the partition table

        if unused1 != 0:
            raise pyisoexception.PyIsoException("El Torito unused field must be 0")

        self.initialized = True

    def new(self):
        '''
        Create a new El Torito section header.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Section Header already initialized")

        self.boot_indicator = 0x88 # FIXME: allow the user to set this
        self.boot_media_type = 0x0 # FIXME: allow the user to set this
        self.load_segment = 0 # FIXME: allow the user to set this
        self.system_type = 0 # FIXME: we should copy this from the partition table
        self.sector_count = 0 # FIXME: allow the user to set this
        self.load_rba = 0 # This will get set later
        self.selection_criteria_type = 0 # FIXME: allow the user to set this
        self.selection_criteria = "{:\x00<19}".format('') # FIXME: allow user to set this
        self.initialized = True

    def record(self):
        '''
        Get a string representing this El Torito section header.

        Parameters:
         None.
        Returns:
         A string representing this El Torito section header.
        '''
        return struct.pack(self.fmt, self.boot_indicator, self.boot_media_type,
                           self.load_segment, self.system_type, 0,
                           self.sector_count, self.load_rba,
                           self.selection_criteria_type,
                           self.selection_criteria)

class EltoritoBootCatalog(object):
    '''
    A class that represents an El Torito Boot Catalog.  The boot catalog is the
    basic unit of El Torito, and is expected to contain a validation entry,
    an initial entry, and zero or more section entries.
    '''
    EXPECTING_VALIDATION_ENTRY = 1
    EXPECTING_INITIAL_ENTRY = 2
    EXPECTING_SECTION_HEADER_OR_DONE = 3
    EXPECTING_SECTION_ENTRY = 4

    def __init__(self, br):
        self.dirrecord = None
        self.initialized = False
        self.br = br
        self.initial_entry = None
        self.validation_entry = None
        self.section_header = None
        self.section_entries = []
        self.state = self.EXPECTING_VALIDATION_ENTRY

    def parse(self, valstr):
        '''
        A method to parse an El Torito Boot Catalog out of a string.

        Parameters:
         valstr - The string to parse the El Torito Boot Catalog out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog already initialized")

        if self.state == self.EXPECTING_VALIDATION_ENTRY:
            # The first entry in an El Torito boot catalog is the Validation
            # Entry.  A Validation entry consists of 32 bytes (described in
            # detail in the parse_eltorito_validation_entry() method).
            self.validation_entry = EltoritoValidationEntry()
            self.validation_entry.parse(valstr)
            self.state = self.EXPECTING_INITIAL_ENTRY
        elif self.state == self.EXPECTING_INITIAL_ENTRY:
            # The next entry is the Initial/Default entry.  An Initial/Default
            # entry consists of 32 bytes (described in detail in the
            # parse_eltorito_initial_entry() method).
            self.initial_entry = EltoritoInitialEntry()
            self.initial_entry.parse(valstr)
            self.state = self.EXPECTING_SECTION_HEADER_OR_DONE
        else:
            if valstr[0] == '\x00':
                # An empty entry tells us we are done parsing El Torito, so make
                # sure we got what we expected and then set ourselves as
                # initialized.
                self.initialized = True
            elif valstr[0] == '\x90' or valstr[0] == '\x91':
                # A Section Header Entry
                self.section_header = EltoritoSectionHeader()
                self.section_header.parse(valstr)
                if valstr[0] == '\x91':
                    self.state = self.EXPECTING_SECTION_ENTRY
            elif valstr[0] == '\x88' or valstr[0] == '\x00':
                # A Section Entry
                secentry = EltoritoSectionEntry()
                secentry.parse(valstr)
                self.section_entries.append(secentry)
            elif valstr[0] == '\x44':
                # A Section Entry Extension
                self.section_entries[-1].selection_criteria += valstr[2:]
            else:
                raise pyisoexception.PyIsoException("Invalid El Torito Boot Catalog entry")

        return self.initialized

    def new(self, br, sector_count, platform_id):
        '''
        A method to create a new El Torito Boot Catalog.

        Parameters:
         br - The boot record that this El Torito Boot Catalog is associated
              with.
         sector_count - The number of sectors for the initial entry.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise Exception("El Torito Boot Catalog already initialized")

        # Create the El Torito validation entry
        self.validation_entry = EltoritoValidationEntry()
        self.validation_entry.new(platform_id)

        self.initial_entry = EltoritoInitialEntry()
        self.initial_entry.new(sector_count)

        self.br = br

        self.initialized = True

    def record(self):
        '''
        A method to generate a string representing this El Torito Boot Catalog.

        Parameters:
         None.
        Returns:
         A string representing this El Torito Boot Catalog.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog not yet initialized")

        ret = self.validation_entry.record() + self.initial_entry.record()

        if self.section_header is not None:
            ret += self.section_header.record()

            for entry in self.section_entries:
                ret += entry.record()

        return ret

    def update_initial_entry_location(self, new_rba):
        '''
        A method to update the initial entry location.

        Parameters:
         new_rba - The new extent location to associate with the initial entry.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog not yet initialized")

        self.initial_entry.set_rba(new_rba)

    def set_dirrecord(self, rec):
        '''
        A method to update the directory record associated with this El Torito
        Boot Catalog.  While not explicitly mentioned in the standard, all
        known implemenations of El Torito associate a "fake" file with the
        El Torito Boot Catalog; this call connects the fake directory record
        with this boot catalog.

        Parameters:
         rec - The DirectoryRecord object assocatied with this Boot Catalog
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog not yet initialized")

        self.dirrecord = rec

    def set_initial_entry_dirrecord(self, rec):
        '''
        A method to update the directory record associated with the initial
        entry of this boot catalog.

        Parameters:
         rec - The DirectoryRecord object associated with the initial entry.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog not yet initialized")

        self.initial_entry_dirrecord = rec

    def extent_location(self):
        '''
        A method to get the extent location of this El Torito Boot Catalog.

        Parameters:
         None.
        Returns:
         Integer extent location of this El Torito Boot Catalog.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("El Torito Boot Catalog not yet initialized")

        return struct.unpack("=L", self.br.boot_system_use[:4])[0]
