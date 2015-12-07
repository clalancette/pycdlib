#!/usr/bin/python

# This is a simple program to show how to use PyIso to create a new
# ISO, with one file and one directory on it.

# Import standard python modules.
import sys
import StringIO

# Import pyiso itself.
import pyiso

# Check that there are enough command-line arguments.
if len(sys.argv) != 1:
    print("Usage: %s" % (sys.argv[0]))
    sys.exit(1)

# Create a new PyIso object.
iso = pyiso.PyIso()

# Create a new ISO, accepting all of the defaults.
iso.new()

# Add a new file to the ISO, with the contents coming from
# the file object.  Note that the file object must remain open
# for the lifetime of the PyIso object, as the PyIso object
# uses it for internal operations.  Also note that the
# filename passed here is the filename the data will get
# assigned on the final ISO; it must begin with a forward
# slash, and according to ISO9660 must have a '.', and a
# semicolon followed by a number.  PyIso will raise a
# PyIsoException if any of the rules for an ISO9660 filename
# are violated.
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')

# Add a new directory to the ISO.  Like the filename above,
# ISO9660 directory names must conform to certain standards,
# and PyIso will raise a PyIsoException if those standards
# are not met.
iso.add_directory("/DIR1")

# Write out the ISO to the file object outfp.  This will fully
# master the ISO, creating a file that can be burned onto
# a CD.
with open('new.iso', 'w') as outfp:
    iso.write(outfp)

# Close the ISO object.  After this call, the PyIso object has forgotten
# everything about the previous ISO, and can be re-used.
iso.close()
