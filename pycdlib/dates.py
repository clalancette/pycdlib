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
Classes and utilities for ISO date support.
'''

from __future__ import absolute_import

import struct
import time

import pycdlib.pycdlibexception as pycdlibexception

def gmtoffset_from_tm(tm, local):
    '''
    A function to compute the GMT offset from the time in seconds since the epoch
    and the local time object.

    Parameters:
     tm - The time in seconds since the epoch.
     local - The struct_time object representing the local time.
    Returns:
     The gmtoffset.
    '''
    gmtime = time.gmtime(tm)
    tmpyear = gmtime.tm_year - local.tm_year
    tmpyday = gmtime.tm_yday - local.tm_yday
    tmphour = gmtime.tm_hour - local.tm_hour
    tmpmin = gmtime.tm_min - local.tm_min

    if tmpyday < 0:
        tmpyday = -1
    else:
        if tmpyear > 0:
            tmpyday = 1
    return -(tmpmin + 60 * (tmphour + 24 * tmpyday)) // 15

class InterfaceISODate(object):
    '''
    An interface class for Ecma-119 dates.  This is here to ensure that both
    the VolumeDescriptorDate class and the DirectoryRecordDate class implement
    the same interface.
    '''
    def parse(self, datestr):
        '''
        The unimplemeted parse method for the parent class.  The child class
        is expected to implement this.

        Parameters:
         datestr - The date string to parse.
        Returns:
         Nothing.
        '''
        raise NotImplementedError("Parse not yet implemented")

    def record(self):
        '''
        The unimplemented record method for the parent class.  The child class
        is expected to implement this.

        Parameters:
         None.
        Returns:
         String representing this date.
        '''
        raise NotImplementedError("Record not yet implemented")

    def new(self, tm=None):
        '''
        The unimplemented new method for the parent class.  The child class
        is expected to implement this.

        Parameters:
         tm - struct_time object to base new VolumeDescriptorDate off of,
              or None for an empty VolumeDescriptorDate.
        Returns:
         Nothing.
        '''
        raise NotImplementedError("New not yet implemented")

class DirectoryRecordDate(InterfaceISODate):
    '''
    A class to represent a Directory Record date as described in Ecma-119
    section 9.1.5.  The Directory Record date consists of the number of years
    since 1900, the month, the day of the month, the hour, the minute, the
    second, and the offset from GMT in 15 minute intervals.  There are two main
    ways to use this class: either to instantiate and then parse a string to
    fill in the fields (the parse() method), or to create a new entry with a
    tm structure (the new() method).
    '''
    def __init__(self):
        self.initialized = False
        self.fmt = "=BBBBBBb"

    def parse(self, datestr):
        '''
        Parse a Directory Record date out of a string.

        Parameters:
         datestr - The string to parse the date out of.
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record Date already initialized")

        (self.years_since_1900, self.month, self.day_of_month, self.hour,
         self.minute, self.second,
         self.gmtoffset) = struct.unpack_from(self.fmt, datestr, 0)

        self.initialized = True

    def new(self, tm=None):
        '''
        Create a new Directory Record date based on the current time.

        Parameters:
         tm - An optional argument that must be None
        Returns:
         Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record Date already initialized")

        if tm is not None:
            raise pycdlibexception.PyCdlibException("Directory Record Date does not support passing tm in")

        # This algorithm was ported from cdrkit, genisoimage.c:iso9660_date()
        tm = time.time()
        local = time.localtime(tm)
        self.years_since_1900 = local.tm_year - 1900
        self.month = local.tm_mon
        self.day_of_month = local.tm_mday
        self.hour = local.tm_hour
        self.minute = local.tm_min
        self.second = local.tm_sec
        self.gmtoffset = gmtoffset_from_tm(tm, local)
        self.initialized = True

    def record(self):
        '''
        Return a string representation of the Directory Record date.

        Parameters:
         None.
        Returns:
         A string representing this Directory Record Date.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("Directory Record Date not initialized")

        return struct.pack(self.fmt, self.years_since_1900, self.month,
                           self.day_of_month, self.hour, self.minute,
                           self.second, self.gmtoffset)

    def __ne__(self, other):
        return self.years_since_1900 != other.years_since_1900 or self.month != other.month or self.day_of_month != other.day_of_month or self.hour != other.hour or self.minute != other.minute or self.second != other.second or self.gmtoffset != other.gmtoffset

class VolumeDescriptorDate(InterfaceISODate):
    '''
    A class to represent a Volume Descriptor Date as described in Ecma-119
    section 8.4.26.1.  The Volume Descriptor Date consists of a year (from 1 to
    9999), month (from 1 to 12), day of month (from 1 to 31), hour (from 0
    to 23), minute (from 0 to 59), second (from 0 to 59), hundredths of second,
    and offset from GMT in 15-minute intervals (from -48 to +52) fields.  There
    are two main ways to use this class: either to instantiate and then parse a
    string to fill in the fields (the parse() method), or to create a new entry
    with a tm structure (the new() method).
    '''
    def __init__(self):
        self.initialized = False
        self.time_fmt = "%Y%m%d%H%M%S"
        self.empty_string = b'0'*16 + b'\x00'

    def parse(self, datestr):
        '''
        Parse a Volume Descriptor Date out of a string.  A string of all zeros
        is valid, which means that the date in this field was not specified.

        Parameters:
          datestr - string to be parsed
        Returns:
          Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("This Volume Descriptor Date object is already initialized")

        if len(datestr) != 17:
            raise pycdlibexception.PyCdlibException("Invalid ISO9660 date string")

        if datestr == self.empty_string or datestr == b'\x00'*17 or datestr == b'0'*17:
            # Ecma-119, 8.4.26.1 specifies that if the string was all the
            # digit zero, with the last byte 0, the time wasn't specified.
            # However, in practice I have found that some ISOs specify this
            # field as all the number 0, so we allow both.
            self.year = 0
            self.month = 0
            self.dayofmonth = 0
            self.hour = 0
            self.minute = 0
            self.second = 0
            self.hundredthsofsecond = 0
            self.gmtoffset = 0
            self.present = False
        else:
            timestruct = time.strptime(datestr[:-3].decode('utf-8'), self.time_fmt)
            self.year = timestruct.tm_year
            self.month = timestruct.tm_mon
            self.dayofmonth = timestruct.tm_mday
            self.hour = timestruct.tm_hour
            self.minute = timestruct.tm_min
            self.second = timestruct.tm_sec
            self.hundredthsofsecond = int(datestr[14:15])
            self.gmtoffset, = struct.unpack_from("=b", datestr, 16)
            self.present = True

        self.initialized = True
        self.date_str = datestr

    def record(self):
        '''
        Return the date string for this object.

        Parameters:
          None.
        Returns:
          Date as a string.
        '''
        if not self.initialized:
            raise pycdlibexception.PyCdlibException("This Volume Descriptor Date is not yet initialized")

        return self.date_str

    def new(self, tm=None):
        '''
        Create a new Volume Descriptor Date.  If tm is None, then this Volume
        Descriptor Date will be full of zeros (meaning not specified).  If tm
        is not None, it is expected to be a struct_time object, at which point
        this Volume Descriptor Date object will be filled in with data from that
        struct_time.

        Parameters:
          tm - struct_time object to base new VolumeDescriptorDate off of,
               or None for an empty VolumeDescriptorDate.
        Returns:
          Nothing.
        '''
        if self.initialized:
            raise pycdlibexception.PyCdlibException("This Volume Descriptor Date object is already initialized")

        if tm is not None:
            local = time.localtime(tm)
            self.year = local.tm_year
            self.month = local.tm_mon
            self.day_of_month = local.tm_mday
            self.hour = local.tm_hour
            self.minute = local.tm_min
            self.second = local.tm_sec
            self.hundredthsofsecond = 0
            self.gmtoffset = gmtoffset_from_tm(tm, local)
            self.date_str = b"%s%s%s" % (time.strftime(self.time_fmt, local).encode('utf-8'), "{:0<2}".format(self.hundredthsofsecond).encode('utf-8'), struct.pack("=b", self.gmtoffset))
            self.present = True
        else:
            self.year = 0
            self.month = 0
            self.dayofmonth = 0
            self.hour = 0
            self.minute = 0
            self.second = 0
            self.hundredthsofsecond = 0
            self.gmtoffset = 0
            self.date_str = self.empty_string
            self.present = False

        self.initialized = True

    def __ne__(self, other):
        return self.year != other.year or self.month != other.month or self.dayofmonth != other.dayofmonth or self.hour != other.hour or self.minute != other.minute or self.second != other.second or self.hundredthsofsecond != other.hundredthsofsecond or self.gmtoffset != other.gmtoffset or self.date_str != other.date_str
