#!/usr/bin/python

# This is a simple example program to show how to use PyIso to open up an
# existing ISO passed on the command-line, and print out all of the file names
# at the root of the ISO.

# Import standard python modules.
import sys

# Import pyiso itself.
import pyiso

# Check that there are enough command-line arguments.
if len(sys.argv) != 2:
    print("Usage: %s <iso>" % (sys.argv[0]))
    sys.exit(1)

# Create a new PyIso object.
iso = pyiso.PyIso()

# Open up a file object.  This causes PyIso to parse all of the metadata on the
# ISO, which is used for later manipulation.
iso.open(sys.argv[1])

# Now iterate through each of the files on the root of the ISO, printing out
# their names.
for child in iso.list_dir('/'):
    print(child.file_identifier())

# Close the ISO object.  After this call, the PyIso object has forgotten
# everything about the previous ISO, and can be re-used.
iso.close()
