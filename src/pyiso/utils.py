# Copyright (C) 2015  Chris Lalancette <clalancette@gmail.com>

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
Various utilities for PyIso.
'''

import socket

import sendfile

from pyisoexception import *

def swab_32bit(input_int):
    '''
    A function to swab a 32-bit integer.

    Parameters:
     input_int - The 32-bit integer to swab.
    Returns:
     The swabbed version of the 32-bit integer.
    '''
    return socket.htonl(input_int)

def swab_16bit(input_int):
    '''
    A function to swab a 16-bit integer.

    Parameters:
     input_int - The 16-bit integer to swab.
    Returns:
     The swabbed version of the 16-bit integer.
    '''
    return socket.htons(input_int)

def ceiling_div(numer, denom):
    '''
    A function to do ceiling division; that is, dividing numerator by denominator
    and taking the ceiling.

    Parameters:
     numer - The numerator for the division.
     denom - The denominator for the division.
    Returns:
     The ceiling after dividing numerator by denominator.
    '''
    # Doing division and then getting the ceiling is tricky; we do upside-down
    # floor division to make this happen.
    # See https://stackoverflow.com/questions/14822184/is-there-a-ceiling-equivalent-of-operator-in-python.
    return -(-numer // denom)

def hexdump(st):
    '''
    A utility function to print a string in hex.

    Parameters:
     st - The string to print.
    Returns:
     A string containing the hexadecimal representation of the input string.
    '''
    return ':'.join(x.encode('hex') for x in st)

def copy_data(data_length, blocksize, infp, outfp):
    '''
    A utility function to copy data from the input file object to the output
    file object.  This function will use the most efficient copy method available,
    which is often sendfile.

    Parameters:
     data_length - The amount of data to copy.
     blocksize - How much data to copy per iteration.
     infp - The file object to copy data from.
     outfp - The file object to copy data to.
    Returns:
     Nothing.
    '''
    if hasattr(infp, 'fileno') and hasattr(outfp, 'fileno'):
        # This is one of those instances where using the file object and the
        # file descriptor causes problems.  The sendfile() call actually updates
        # the underlying file descriptor, but the file object does not know
        # about it.  To get around this, we instead get the offset, allow
        # sendfile() to update the offset, then manually seek the file object
        # to the right location.  This ensures that the file object gets updated
        # properly.
        in_offset = infp.tell()
        out_offset = outfp.tell()
        sendfile.sendfile(outfp.fileno(), infp.fileno(), in_offset, data_length)
        infp.seek(in_offset + data_length)
        outfp.seek(out_offset + data_length)
    else:
        left = data_length
        readsize = blocksize
        while left > 0:
            if left < readsize:
                readsize = left
            outfp.write(infp.read(readsize))
            left -= readsize

def ptr_lt(str1, str2):
    '''
    A function to compare two identifiers according to hte ISO9660 Path Table Record
    sorting order.

    Parameters:
     str1 - The first identifier.
     str2 - The second identifier.
    Returns:
     True if str1 is less than or equal to str2, False otherwise.
    '''
    # This method is used for the bisect.insort_left() when adding a child.
    # It needs to return whether str1 is less than str2.  Here we use the
    # ISO9660 sorting order which is essentially:
    #
    # 1.  The \x00 is always the "dot" record, and is always first.
    # 2.  The \x01 is always the "dotdot" record, and is always second.
    # 3.  Other entries are sorted lexically; this does not exactly match
    #     the sorting method specified in Ecma-119, but does OK for now.
    #
    # FIXME: we need to implement Ecma-119 section 9.3 for the sorting
    # order.
    if str1 == '\x00':
        # If both str1 and str2 are 0, then they are not strictly less.
        if str2 == '\x00':
            return False
        return True
    if str2 == '\x00':
        return False

    if str1 == '\x01':
        if str2 == '\x00':
            return False
        return True

    if str2 == '\x01':
        # If str1 was '\x00', it would have been caught above.
        return False
    return str1 < str2

def utf_encode_space_pad(instr, length):
    output = instr.encode('utf-16_be')
    if len(output) > length:
        raise PyIsoException("Input string too long!")

    left = length - len(output)
    while left > 0:
        output += '\x00 '
        left -= 2

    return output
