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
PyCdlib Inode class.
'''

from __future__ import absolute_import

import pycdlib.pycdlibexception as pycdlibexception


class Inode(object):
    '''
    A class that represents an inode, the pointer to a piece of data
    (not metadata) on an ISO.
    '''
    __slots__ = ('_initialized', 'new_extent_loc', 'orig_extent_loc',
                 'linked_records', 'data_length', 'manage_fp', 'data_fp',
                 'original_data_location', 'fp_offset', 'boot_info_table',
                 'num_udf')

    DATA_ON_ORIGINAL_ISO = 1
    DATA_IN_EXTERNAL_FP = 2

    def __init__(self):
        self.linked_records = []
        self._initialized = False
        self.data_length = 0
        self.boot_info_table = None
        self.num_udf = 0

    def new(self, length, fp, manage_fp, offset):
        '''
        Initialize a new Inode.

        Parameters:
         None.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is already initialized')

        # These will be set later.
        self.orig_extent_loc = None
        self.new_extent_loc = None

        self.data_length = length

        self.data_fp = fp
        self.manage_fp = manage_fp
        self.fp_offset = offset
        self.original_data_location = self.DATA_IN_EXTERNAL_FP

        self._initialized = True

    def parse(self, extent, length, fp, log_block_size):
        '''
        Parse an existing Inode.  This just saves off the extent for later use.

        Parameters:
         extent - The original extent that the data lives at.
        Returns:
         Nothing.
        '''
        if self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is already initialized')

        self.orig_extent_loc = extent
        self.new_extent_loc = None

        self.data_length = length

        self.data_fp = fp
        self.manage_fp = False
        self.fp_offset = extent * log_block_size
        self.original_data_location = self.DATA_ON_ORIGINAL_ISO

        self._initialized = True

    def extent_location(self):
        '''
        Get the current location of this Inode on the ISO.

        Parameters:
         None.
        Returns:
         The extent location of this Inode on the ISO.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is not yet initialized')

        if self.new_extent_loc is not None:
            return self.new_extent_loc
        return self.orig_extent_loc

    def set_location(self, extent):
        '''
        Set the current location of this Inode on the ISO.

        Parameters:
         extent - The new extent location for this Inode.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is not yet initialized')

        self.new_extent_loc = extent

    def get_data_length(self):
        '''
        Get the length of the data pointed to by this Inode.

        Parameters:
         None.
        Returns:
         The length of the data pointed to by this Inode.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is not yet initialized')

        return self.data_length

    def add_boot_info_table(self, boot_info_table):
        '''
        A method to add a boot info table to this Inode.

        Parameters:
         boot_info_table - The Boot Info Table object to add to this Inode.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is not yet initialized')

        self.boot_info_table = boot_info_table

    def update_fp(self, fp, length):
        '''
        Update the Inode to use a different file object and length.

        Parameters:
         fp - A file object that contains the data for this Inode.
         length - The length of the data.
        Returns:
         Nothing.
        '''
        if not self._initialized:
            raise pycdlibexception.PyCdlibInternalError('Inode is not yet initialized')

        self.original_data_location = self.DATA_IN_EXTERNAL_FP
        self.data_fp = fp
        self.data_length = length
        self.fp_offset = 0


class InodeOpenData(object):
    '''
    A class to be a contextmanager for opening data on a DirectoryRecord object.
    '''
    __slots__ = ('ino', 'logical_block_size', 'data_fp')

    def __init__(self, ino, logical_block_size):
        self.ino = ino
        self.logical_block_size = logical_block_size

    def __enter__(self):
        if self.ino.manage_fp:
            # In the case that we are managing the FP, the data_fp member
            # actually contains the filename, not the fp.  Use that to
            # our advantage here.
            self.data_fp = open(self.ino.data_fp, 'rb')
        else:
            self.data_fp = self.ino.data_fp

        if self.ino.original_data_location == self.ino.DATA_ON_ORIGINAL_ISO:
            self.data_fp.seek(self.ino.orig_extent_loc * self.logical_block_size)
        else:
            self.data_fp.seek(self.ino.fp_offset)

        return self.data_fp, self.ino.data_length

    def __exit__(self, *args):
        if self.ino.manage_fp:
            self.data_fp.close()
