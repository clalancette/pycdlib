# Copyright (C) 2015-2018  Chris Lalancette <clalancette@gmail.com>

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
Various utilities for PyCdlib.
'''

from __future__ import absolute_import

try:
    import cStringIO  # pylint: disable=import-error
except ImportError:
    pass
import io
import os
import socket
import sys
import time

import pycdlib.pycdlibexception as pycdlibexception

have_sendfile = True
try:
    from sendfile import sendfile
except ImportError:
    try:
        from os import sendfile  # pylint: disable=ungrouped-imports
    except ImportError:
        have_sendfile = False


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
    use_sendfile = False
    if have_sendfile:
        # Python 3 implements the fileno method for all file-like objects, so
        # we can't just use the existence of the method to tell whether it is
        # available.  Instead, we try to assign it, and if we fail, then we
        # assume it is not available.
        try:
            x_unused = infp.fileno()  # NOQA
            y_unused = outfp.fileno()  # NOQA
            use_sendfile = True
        except (AttributeError, io.UnsupportedOperation):
            pass

    if use_sendfile:
        # This is one of those instances where using the file object and the
        # file descriptor causes problems.  The sendfile() call actually updates
        # the underlying file descriptor, but the file object does not know
        # about it.  To get around this, we instead get the offset, allow
        # sendfile() to update the offset, then manually seek the file object
        # to the right location.  This ensures that the file object gets updated
        # properly.
        in_offset = infp.tell()
        out_offset = outfp.tell()
        sendfile(outfp.fileno(), infp.fileno(), in_offset, data_length)
        infp.seek(in_offset + data_length)
        outfp.seek(out_offset + data_length)
    else:
        left = data_length
        readsize = blocksize
        while left > 0:
            if left < readsize:
                readsize = left
            data = infp.read(readsize)
            # We have seen ISOs in the wild (Tribes Vengeance 1of4.iso) that
            # lie about the size of their files, causing reads to fail (since
            # we hit EOF before the supposed end of the file).  If we are using
            # sendfile above, sendfile just silently returns as much data as it
            # can, with no additional checking.  We should do the same here, so
            # if we got less data than we asked for, abort the loop silently.
            data_len = len(data)
            if data_len != readsize:
                data_len = left
            outfp.write(data)
            left -= data_len


def encode_space_pad(instr, length, encoding):
    '''
    A function to pad out an input string with spaces to the length specified.
    The space is first encoded into the specified encoding, then appended to
    the input string until the length is reached.

    Parameters:
     instr - The input string to encode and pad.
     length - The length to pad the input string to.
     encoding - The encoding to use.
    Returns:
     The input string encoded in the encoding and padded with encoded spaces.
    '''
    output = instr.decode('utf-8').encode(encoding)
    if len(output) > length:
        raise pycdlibexception.PyCdlibInvalidInput('Input string too long!')

    encoded_space = ' '.encode(encoding)

    left = length - len(output)
    while left > 0:
        output += encoded_space
        left -= len(encoded_space)

    if left < 0:
        output = output[:left]

    return output


def normpath(path):
    '''
    A method to normalize the path, eliminating double slashes, etc.  This
    method is a copy of the built-in python normpath, except we do *not* allow
    double slashes at the start.

    Parameters:
     path - The path to normalize.
    Returns:
     The normalized path.
    '''
    if not isinstance(path, bytes):
        path = path.encode('utf-8')

    sep = b'/'
    empty = b''
    dot = b'.'
    dotdot = b'..'

    if path == empty:
        if isinstance(dot, bytes):
            return dot
        return dot.encode('utf-8')

    initial_slashes = path.startswith(sep)
    comps = path.split(sep)
    new_comps = []
    for comp in comps:
        if comp in (empty, dot):
            continue
        if comp != dotdot or (not initial_slashes and not new_comps) or (new_comps and new_comps[-1] == dotdot):
            new_comps.append(comp)
        elif new_comps:
            new_comps.pop()
    comps = new_comps
    path = sep.join(comps)
    path = sep * initial_slashes + path
    if not isinstance(path, bytes):
        path = path.encode('utf-8')
    if not isinstance(dot, bytes):
        dot = dot.encode('utf-8')
    return path or dot


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


def zero_pad(fp, data_size, pad_size):
    '''
    A function to write padding out from data_size up to pad_size
    efficiently.

    Parameters:
     fp - The file object to use to write padding out to.
     data_size - The current size of the data.
     pad_size - The size of data to pad out to.
    Returns:
     Nothing.
    '''
    padbytes = pad_size - (data_size % pad_size)
    if padbytes == pad_size:
        # Nothing to pad, get out.
        return

    fp.seek(padbytes - 1, os.SEEK_CUR)
    fp.write(b'\x00')


def starts_with_slash(path):
    '''
    A function to determine if a path starts with a slash.  This is somewhat
    difficult to do portably between Python2 and Python3 and with performance,
    so we have a dedicated function for it.

    Parameters:
     path - The path to determine if it starts with a slash
    Returns:
     Whether the path starts with a slash.
    '''
    return bytearray(path)[0] == 47


def split_path(iso_path):
    '''
    A function to take a fully-qualified iso path and split it into components.

    Parameters:
     iso_path - The path to split.
    Returns:
     The components of the path as a list.
    '''
    if not starts_with_slash(iso_path):
        raise pycdlibexception.PyCdlibInvalidInput('Must be a path starting with /')

    # Split the path along the slashes.  Since our paths are always absolute,
    # the front is blank.
    return iso_path.split(b'/')[1:]


def file_object_supports_binary(fp):
    '''
    A function to check whether a file-like object supports binary mode.

    Parameters:
     fp - The file-like object to check for binary mode support.
    Returns:
     True if the file-like object supports binary mode, False otherwise.
    '''
    if hasattr(fp, 'mode'):
        return 'b' in fp.mode

    # Python 3
    if sys.version_info >= (3, 0):
        return isinstance(fp, (io.RawIOBase, io.BufferedIOBase))

    # Python 2
    return isinstance(fp, (cStringIO.OutputType, cStringIO.InputType, io.RawIOBase, io.BufferedIOBase))
