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

import collections
import copy
import io
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

class RecordReader(io.RawIOBase):
    '''
    A class to access inode data using IOBase primitives.
    '''

    def __init__(self, found_record, logical_block_size):
        self._logical_block_size = logical_block_size
        self._all_records = collections.deque()
        self._current_records = None

        self._position = 0
        self._length = 0

        while found_record is not None and found_record.get_data_length() > 0:
            self._all_records.append({
                'inode': found_record.ino,
                'length': found_record.ino.data_length,
                'offset': 0,
            })
            self._length += found_record.ino.data_length

            if found_record.data_continuation is not None:
                found_record = found_record.data_continuation
            else:
                found_record = None

        self._current_records = copy.deepcopy(self._all_records)

    def readinto(self, b):
        """\
        Read up to len(b) bytes into b.

        Returns number of bytes read (0 for EOF), or None if the object
        is set not to block and has no data to read.
        """
        if not self._current_records:
            return 0

        # Take the next file and read the next chunk
        entry = self._current_records.popleft()
        length = min(len(b), entry['length'] - entry['offset'])

        with InodeOpenData(entry['inode'], self.logical_block_size) as (data_fp, _):
            data_fp.seek(entry['offset'])
            chunk = data_fp.read(length)

        # Put back the file to the pool if there is still unread data in it
        n = len(chunk)
        self._position += n
        entry['offset'] += n
        if entry['offset'] < entry['length']:
            self._current_files.appendleft(entry)

        # Return the data read
        try:
            b[:n] = chunk
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array(b'b', chunk)

        return n

    def seek(self, pos, whence=0):
        """\
        Change stream position.

        Change the stream position to byte offset pos. Argument pos is
        interpreted relative to the position indicated by whence.  Values
        for whence are:

        * 0 -- start of stream (the default); offset should be zero or positive
        * 1 -- current stream position; offset may be negative
        * 2 -- end of stream; offset is usually negative

        Return the new absolute position.
        """
        if self.closed:
            raise ValueError("seek on closed file")
        try:
            pos.__index__
        except AttributeError:
            raise TypeError("an integer is required")
        if not (0 <= whence <= 2):
            raise ValueError("invalid whence")

        # Quick case for tell()
        if pos==0 and whence==1:
            return self._position

        self._current_records = collections.deque()
        skip = {
            0: max(0, pos),
            1: min(self._length, max(0, self._position + pos)),
            2: min(self._length, self._length + pos)
        }[whence]
        self._position = 0

        for entry in self._all_records:
            if entry['length'] <= skip:
                self._position += entry['length']
                skip -= entry['length']
                continue

            new_entry = entry.copy()

            if skip:
                new_entry['offset'] = skip
                self._position += skip
                skip = 0

            self._current_records.append(new_entry)

        return self._position

    def readable(self):
        """\
        Return True if the stream can be read from. If False, `read()` will
        raise IOError.
        """
        return True

    def seekable(self):
        """\
        Return True if the stream supports random access. If False, `seek()`,
        `tell()` and `truncate()` will raise IOError.
        """
        return True
