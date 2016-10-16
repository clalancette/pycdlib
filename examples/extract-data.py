#!/usr/bin/python

# This is a simple program to show how to use PyCdlib to extract data from the
# ISO.

# Import standard python modules.
import sys
import StringIO

# Import pycdlib itself.
import pycdlib

# Check that there are enough command-line arguments.
if len(sys.argv) != 1:
    print("Usage: %s" % (sys.argv[0]))
    sys.exit(1)


# First we'll create a new ISO and write it out (see create-new.py for more
# information about these steps).
iso = pycdlib.PyCdlib()
iso.new()
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
out = StringIO.StringIO()
iso.write_fp(out)
iso.close()

# Now, let's open up the ISO and extract the contents of the FOO.;1 file.
iso.open_fp(out)
extracted = StringIO.StringIO()
# Use the get_and_write_fp() API to extract the named filename into the file
# descriptor.
iso.get_and_write_fp("/FOO.;1", extracted)
iso.close()

print(extracted)
