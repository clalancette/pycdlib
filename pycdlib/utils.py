# Copyright (C) 2015-2020  Chris Lalancette <clalancette@gmail.com>

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
import re
import sys
import time

from pycdlib import pycdlibexception

# For mypy annotations
if False:  # pylint: disable=using-constant-test
    from typing import BinaryIO, List, Tuple  # NOQA pylint: disable=unused-import


def swab_32bit(x):
    # type: (int) -> int
    '''
    A function to swab a 32-bit integer.

    Parameters:
     x - The 32-bit integer to swab.
    Returns:
     The swabbed version of the 32-bit integer.
    '''
    if x > (((1 << 32) - 1) & 0xFFFFFFFF) or x < 0:
        raise pycdlibexception.PyCdlibInternalError('Invalid integer passed to swab; must be unsigned 32-bits!')

    return ((x << 24) & 0xFF000000) | ((x << 8) & 0x00FF0000) | ((x >> 8) & 0x0000FF00) | ((x >> 24) & 0x000000FF)


def swab_16bit(x):
    # type: (int) -> int
    '''
    A function to swab a 16-bit integer.

    Parameters:
     x - The 16-bit integer to swab.
    Returns:
     The swabbed version of the 16-bit integer.
    '''
    if x > (((1 << 16) - 1) & 0xFFFFFFFF) or x < 0:
        raise pycdlibexception.PyCdlibInternalError('Invalid integer passed to swab; must be unsigned 16-bits!')

    return ((x << 8) & 0xFF00) | ((x >> 8) & 0x00FF)


def ceiling_div(numer, denom):
    # type: (int, int) -> int
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
    # type: (int, int, BinaryIO, BinaryIO) -> None
    '''
    A utility function to copy data from the input file object to the output
    file object.

    Parameters:
     data_length - The amount of data to copy.
     blocksize - How much data to copy per iteration.
     infp - The file object to copy data from.
     outfp - The file object to copy data to.
    Returns:
     Nothing.
    '''
    left = data_length
    readsize = blocksize
    while left > 0:
        if left < readsize:
            readsize = left
        data = infp.read(readsize)
        # We have seen ISOs in the wild (Tribes Vengeance 1of4.iso) that
        # lie about the size of their files, causing reads to fail (since
        # we hit EOF before the supposed end of the file).  If we got less data
        # than we asked for, abort the loop silently.
        data_len = len(data)
        if data_len != readsize:
            data_len = left
        outfp.write(data)
        left -= data_len


def encode_space_pad(instr, length, encoding):
    # type: (bytes, int, str) -> bytes
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
    # type: (str) -> bytes
    '''
    Normalize the given path, eliminating double slashes, etc.  This function is
    a copy of the built-in python normpath, except we do *not* allow double
    slashes at the start.

    Parameters:
     path - The path to normalize.
    Returns:
     The normalized path.
    '''
    sep = '/'
    empty = ''
    dot = '.'
    dotdot = '..'

    if path == empty:
        return dot.encode('utf-8')

    initial_slashes = path.startswith(sep)
    comps = path.split(sep)
    new_comps = []  # type: List[str]
    for comp in comps:
        if comp in (empty, dot):
            continue
        if comp != dotdot or (not initial_slashes and not new_comps) or (new_comps and new_comps[-1] == dotdot):
            new_comps.append(comp)
        elif new_comps:
            new_comps.pop()
    newpath = sep * initial_slashes + sep.join(new_comps)
    if sys.version_info >= (3, 0):
        newpath_bytes = newpath.encode('utf-8')
    else:
        newpath_bytes = newpath.decode('utf-8').encode('utf-8')
    if not starts_with_slash(newpath_bytes):
        raise pycdlibexception.PyCdlibInvalidInput('Must be a path starting with /')

    return newpath_bytes


def gmtoffset_from_tm(tm, local):
    # type: (float, time.struct_time) -> int
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
    # type: (BinaryIO, int, int) -> None
    '''
    A function to write padding out from data_size up to pad_size
    efficiently.

    Parameters:
     fp - The file object to use to write padding out to.
     data_size - The current size of the data.
     pad_size - The boundary size of data to pad out to.
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
    # type: (bytes) -> bool
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
    # type: (bytes) -> List[bytes]
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
    # type: (BinaryIO) -> bool
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


def truncate_basename(basename, iso_level, is_dir):
    # type: (str, int, bool) -> str
    '''
    A function to truncate a basename and make it conformant to the passed-in
    ISO interchange level.

    Parameters:
     basename - The initial basename to truncate and translate
     iso_level - The ISO interchange level to follow when truncating/translating
     is_dir - Whether this is a directory or a file
    Returns:
     The truncated and translated name suitable for the ISO interchange level
     specified.
    '''
    if iso_level == 4:
        # ISO level 4 allows "anything", so just return the original.
        return basename

    if iso_level == 1:
        maxlen = 8
    else:
        maxlen = 31 if is_dir else 30

    # For performance reasons, we first truncate the string to the length
    # allowed.  Second, ISO9660 Levels 1, 2, and 3 require all uppercase names,
    # so we uppercase it.
    valid_base = basename[:maxlen].upper()

    # Finally, ISO9660 requires only uppercase letters, 0-9, and underscore.
    # Translate any non-compliant characters to underscore and return that.
    return re.sub('[^A-Z0-9_]{1}', r'_', valid_base)


def mangle_file_for_iso9660(orig, iso_level):
    # type: (str, int) -> Tuple[str, str]
    '''
    A function to take a regular Unix-style filename (including extension) and
    produce a tuple consisting of an ISO9660-valid basename and an ISO9660-valid
    extension.

    Parameters:
     orig - The original filename
     iso_level - The ISO interchange level to conform to
    Returns:
     A tuple where the first entry is the ISO9660-compliant basename and where
     the second entry is the ISO9660-compliant extension.
    '''
    # ISO9660 has a lot of restrictions on what valid names are.  Here, we mangle
    # the names to conform to those rules.  In particular, the rules for
    # filenames are:
    # 1.  Filenames can only consist of d-characters or d1-characters; these are
    #     defined in the Appendix as: 0-9A-Z_
    # 2.  Filenames look like:
    #     - zero or more d-characters (filename)
    #     - separator 1 (.)
    #     - zero or more d-characters (extension)
    #     - separate 2 (;)
    #     - version, between 0 and 32767
    # If the filename contains zero characters, then the extension must contain
    # at least one character, and vice versa.
    # 3.  If this is iso level one, then the length of the filename cannot
    #     exceed 8 and the length of the extension cannot exceed 3.  In levels 2
    #     and 3, the length of the filename+extension cannot exceed 30.
    #
    # This function takes any valid Unix filename and converts it into one that
    # is allowed by the above rules.  It does this by substituting _ for any
    # invalid characters in the filename, and by shortening the name to a form
    # of aaa_xxxx.eee;1 (if necessary).  The aaa is always the first three
    # characters of the original filename; the xxxx is the next number in a
    # sequence starting from 0.

    valid_ext = ''
    splitter = orig.split('.')
    if iso_level == 4:
        # A level 4 ISO allows 'anything', so just return the original.
        if len(splitter) == 1:
            return orig, valid_ext

        ext = splitter[-1]
        return orig[:len(orig) - len(ext) - 1], ext

    if len(splitter) == 1:
        # No extension specified, leave ext empty
        basename = orig
    else:
        ext = splitter[-1]
        basename = orig[:len(orig) - len(ext) - 1]

        # If the extension is empty, too long (> 3), or contains any illegal
        # characters, we treat it as part of the basename instead
        extlen = len(ext)
        if extlen == 0 or extlen > 3:
            valid_ext = ''
            basename = orig
        else:
            tmpext = ext.upper()
            valid_ext, numsub = re.subn('[^A-Z0-9_]{1}', r'_', tmpext)
            if numsub > 0:
                valid_ext = ''
                basename = orig

    # All right, now we have the basename of the file, and (optionally) an
    # extension.
    return truncate_basename(basename, iso_level, False), valid_ext + ';1'


def mangle_dir_for_iso9660(orig, iso_level):
    # type: (str, int) -> str
    '''
    A function to take a regular Unix-style directory name and produce an
    ISO9660-valid directory name.

    Parameters:
     orig - The original filename
     iso_level - The ISO interchange level to conform to
    Returns:
     An ISO9660-compliant directory name.
    '''
    # ISO9660 has a lot of restrictions on what valid directory names are.
    # Here, we mangle the names to conform to those rules.  In particular, the
    # rules for dirnames are:
    # 1.  Filenames can only consist of d-characters or d1-characters; these are
    #     defined in the Appendix as: 0-9A-Z_
    # 2.  If this is ISO level one, then directory names consist of no more than
    #     8 characters
    # This function takes any valid Unix directory name and converts it into one
    # that is allowed by the above rules.  It does this by substituting _ for
    # any invalid character in the directory name, and by shortening the name to
    # a form of aaaaxxx (if necessary).  The aaa is always the first three
    # characters of the original filename; the xxxx is the next number in a
    # sequence starting from 0.

    return truncate_basename(orig, iso_level, True)
