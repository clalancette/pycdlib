#!/usr/bin/python3

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
The main code for the pycdlib-extract-files tool, which can extract all or a
subset of files from an ISO.
'''

from __future__ import print_function

import argparse
import collections
import os
import sys

import pycdlib


def parse_arguments():
    '''
    A function to parse all of the arguments passed to the executable.

    Parameters:
     None.
    Returns:
     An ArgumentParser object with the parsed command-line arguments.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-path-type', help='Which path type to use for extraction', action='store', choices=['iso', 'joliet', 'rockridge', 'udf'], default='iso')
    parser.add_argument('iso', help='ISO to open', action='store')
    return parser.parse_args()


def main():
    '''
    The main function for this executable that does the work of extracting
    files from an ISO given the parameters specified by the user.
    '''
    args = parse_arguments()

    iso = pycdlib.PyCdlib()
    print("Opening %s" % (args.iso))
    iso.open(args.iso)

    if args.path_type == 'rockridge':
        if not iso.rock_ridge:
            print('Can only extract Rock Ridge paths from a Rock Ridge ISO')
            return 1
        entry = iso.get_record(rr_path='/')
    elif args.path_type == 'joliet':
        if iso.joliet_vd is None:
            print('Can only extract Joliet paths from a Joliet ISO')
            return 2
        entry = iso.get_record(joliet_path='/')
    elif args.path_type == 'udf':
        if iso.udf_main_descs.pvd is None:
            print('Can only extract UDF paths from a UDF ISO')
            return 3
        entry = iso.get_record(udf_path='/')
    else:
        entry = iso.get_record(iso_path='/')

    dirs = collections.deque([(entry, '/')])
    while dirs:
        dir_record, ident = dirs.popleft()
        ident_to_here = iso.full_path_from_dirrecord(dir_record,
                                                     rockridge=args.path_type == 'rockridge')
        print(ident_to_here)
        if dir_record.is_dir():
            if ident_to_here != '/':
                os.makedirs(ident_to_here[1:])
            if args.path_type == 'rockridge':
                child_lister = iso.list_children(rr_path=ident_to_here)
            elif args.path_type == 'joliet':
                child_lister = iso.list_children(joliet_path=ident_to_here)
            elif args.path_type == 'udf':
                child_lister = iso.list_children(udf_path=ident_to_here)
            else:
                child_lister = iso.list_children(iso_path=ident_to_here)

            for child in child_lister:
                if child is None or child.is_dot() or child.is_dotdot():
                    continue
                dirs.append((child, ident_to_here))
        else:
            if args.path_type == 'rockridge':
                iso.get_file_from_iso(ident_to_here[1:], rr_path=ident_to_here)
            elif args.path_type == 'joliet':
                iso.get_file_from_iso(ident_to_here[1:], joliet_path=ident_to_here)
            elif args.path_type == 'udf':
                iso.get_file_from_iso(ident_to_here[1:], udf_path=ident_to_here)
            else:
                iso.get_file_from_iso(ident_to_here[1:], iso_path=ident_to_here)

    iso.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
