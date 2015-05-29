# The iso in use here was created by doing this:
#
# $ mkdir onefile
# $ echo foo > onefile/foo
# $ genisoimage -v -v -iso-level 1 -no-pad -o one-file-test.iso onefile
#
# It seems to be about the smallest ISO that you can make
#
# Another iso with duplicate names:
# $ mkdir dupname
# $ echo foo > dupname/abcdefghi
# $ echo bar > dupname/abcdefghj
# $ genisoimage -v -v -iso-level 1 -no-pad -o dup-name-test.iso dupname

import pyiso
import StringIO

iso = pyiso.PyIso()
iso.new()
data = "foo\n"
iso.add_fp(StringIO.StringIO(data), len(data), "/FOO")
iso.add_directory("/DIR1")
iso.rm_directory("/DIR1")
iso.write(open("new.iso", "wb"))
iso.close()

'''
iso = pyiso.PyIso()
iso.open(open('one-file-test.iso', 'rb'))
print iso.pvd
iso.print_tree()
f = StringIO.StringIO()
iso.get_and_write('/foo', f)
print("'%s'" % f.getvalue())
iso.get_and_write('/foo', open('bar', 'wb'))
print(iso.list_files("/")[0])
data = "bar\n"
iso.add_fp(StringIO.StringIO(data), len(data), "/bar")
iso.write(open("test.iso", "wb"))
iso.rm_file("/bar")
iso.write(open("test2.iso", "wb"))
iso.close()

iso = pyiso.PyIso()
iso.new()
data = "foo\n"
iso.add_fp(StringIO.StringIO(data), len(data), "/foo")
iso.write(open("new.iso", "wb"))
iso.close()
'''
