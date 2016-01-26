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
Base class for Primary and Supplementary Volume Descriptor.
'''

import bisect

import pyisoexception
import utils
import path_table_record

class HeaderVolumeDescriptor(object):
    '''
    A parent class for Primary and Supplementary Volume Descriptors.  The two
    types of descriptors share much of the same functionality, so this is the
    parent class that both classes derive from.
    '''
    def __init__(self):
        self.initialized = False
        self.path_table_records = []
        self.space_size = None
        self.log_block_size = None
        self.root_dir_record = None
        self.path_tbl_size = None
        self.path_table_num_extents = None
        self.seqnum = None

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
        raise pyisoexception.PyIsoException("Child class must implement parse")

    def new(self, flags, sys_ident, vol_ident, set_size, seqnum, log_block_size,
            vol_set_ident, pub_ident, preparer_ident, app_ident,
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
        raise pyisoexception.PyIsoException("Child class must implement new")

    def path_table_size(self):
        '''
        A method to get the path table size of the Volume Descriptor.

        Parameters:
         None.
        Returns:
         Path table size in bytes.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        return self.path_tbl_size

    def add_path_table_record(self, ptr):
        '''
        A method to add a new path table record to the Volume Descriptor.

        Parameters:
         ptr - The new path table record object to add to the list of path
               table records.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")
        # We keep the list of children in sorted order, based on the __lt__
        # method of the PathTableRecord object.
        bisect.insort_left(self.path_table_records, ptr)

    def set_ptr_dirrecord(self, dirrecord):
        '''
        A method to store a directory record that is associated with a path
        table record.  This will be used during extent reshuffling to update
        all of the path table records with the correct values from the directory
        records.  Note that a path table record is said to be associated with
        a directory record when the file identification of the two match.

        Parameters:
         dirrecord - The directory record object to associate with a path table
                     record with the same file identification.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")
        if dirrecord.is_root:
            ptr_index = 0
        else:
            ptr_index = self.find_ptr_index_matching_ident(dirrecord.file_ident)
        self.path_table_records[ptr_index].set_dirrecord(dirrecord)

    def find_ptr_index_matching_ident(self, child_ident):
        '''
        A method to find a path table record index that matches a particular
        filename.

        Parameters:
         child_ident - The name of the file to find.
        Returns:
         Path table record index corresponding to the filename.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        saved_ptr_index = -1
        for index,ptr in enumerate(self.path_table_records):
            if ptr.directory_identifier == child_ident:
                saved_ptr_index = index
                break

        if saved_ptr_index == -1:
            raise pyisoexception.PyIsoException("Could not find path table record!")

        return saved_ptr_index

    def add_to_space_size(self, addition_bytes):
        '''
        A method to add bytes to the space size tracked by this Volume
        Descriptor.

        Parameters:
         addition_bytes - The number of bytes to add to the space size.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")
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
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")
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
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        return self.root_dir_record

    def logical_block_size(self):
        '''
        A method to get this Volume Descriptor's logical block size.

        Parameters:
         None.
        Returns:
         Size of this Volume Descriptor's logical block size in bytes.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        return self.log_block_size

    def add_to_ptr(self, ptr_size):
        '''
        Add the length of a new file to the volume descriptor.

        Parameters:
         ptr_size - The length to add to the path table record.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        # First add to the path table size.
        self.path_tbl_size += ptr_size
        if (utils.ceiling_div(self.path_tbl_size, 4096) * 2) > self.path_table_num_extents:
            # If we overflowed the path table size, then we need to update the
            # space size.  Since we always add two extents for the little and
            # two for the big, add four total extents.  The locations will be
            # fixed up during reshuffle_extents.
            self.add_to_space_size(4 * self.log_block_size)
            self.path_table_num_extents += 2

    def remove_from_ptr(self, directory_ident):
        '''
        Remove an entry from the volume descriptor.

        Parameters:
         directory_ident - The identifier for the directory to remove.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        ptr_index = self.find_ptr_index_matching_ident(directory_ident)

        # Next remove from the Path Table Record size.
        self.path_tbl_size -= path_table_record.PathTableRecord.record_length(self.path_table_records[ptr_index].len_di)
        new_extents = utils.ceiling_div(self.path_tbl_size, 4096) * 2

        if new_extents > self.path_table_num_extents:
            # This should never happen.
            raise pyisoexception.PyIsoException("This should never happen")
        elif new_extents < self.path_table_num_extents:
            self.remove_from_space_size(4 * self.log_block_size)
            self.path_table_num_extents -= 2
        # implicit else, no work to do

        del self.path_table_records[ptr_index]

    def sequence_number(self):
        '''
        A method to get this Volume Descriptor's sequence number.

        Parameters:
         None.
        Returns:
         This Volume Descriptor's sequence number.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        return self.seqnum

    def update_ptr_records(self):
        '''
        Walk the path table records, updating the extent locations and directory
        numbers for each one.  This is used after reassigning extents on the
        ISO so that the path table records will be up-to-date with the rest of
        the ISO.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        for index,ptr in enumerate(self.path_table_records):
            ptr.update_extent_location_from_dirrecord()
            ptr.set_directory_number(index + 1)
            # Here we update the parent directory number of this path table
            # record based on the actual parent.  At first glance, this seems
            # unsafe because we may not have set the parent's directory number
            # yet.  However, we know that the path_table_records list is in
            # sorted order based on depth, so by the time we reach this record
            # its parent has definitely been updated.
            ptr.update_parent_directory_number()

    def update_ptr_dirnums(self):
        '''
        Walk the path table records, updating the directory numbers for each
        one.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        for index,ptr in enumerate(self.path_table_records):
            ptr.set_directory_number(index + 1)

    def copy_sizes(self, othervd):
        '''
        Copy the path_tbl_size, path_table_num_extents, and space_size from
        another volume descriptor.

        Parameters:
         othervd - The other volume descriptor to copy from.
        Returns:
         Nothing.
        '''
        if not self.initialized:
            raise pyisoexception.PyIsoException("This Volume Descriptor is not yet initialized")

        self.space_size = othervd.space_size
        self.path_tbl_size = othervd.path_tbl_size
        self.path_table_num_extents = othervd.path_table_num_extents
