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
#
# An iso with eltorito:
# $ mkdir eltorito
# $ echo foo > foo
# $ echo boot > boot
# $ genisoimage -v -v -iso-level 1 -no-pad -c boot.cat -b boot -no-emul-boot -o eltorito.iso eltorito

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
iso.close()

iso.open(open('eltorito.iso', 'rb'))
iso.close()

'''
iso = pyiso.PyIso()
iso.open('dirtest.iso')
iso.print_tree()
#print iso.pvd
for f in iso.list_files('/DIR1'):
    print f
print iso.get_file('/DIR1/FOO')
iso.get_and_write_file('/DIR1/FOO', 'bar', overwrite=True)
iso.write("mydirtest.iso", overwrite=True)
iso.close()

iso = pyiso.PyIso()
iso.new()
iso.add_directory("/DIR1")
iso.add_data("foo\n", "/DIR1/FOO")
iso.write("new.iso", overwrite=True)
iso.close()

iso = pyiso.PyIso()
iso.new()
iso.add_data("abcdefghijklmnopqrstuvwxyz" * 1000, "/FOO")
iso.write("newbig.iso", overwrite=True)
iso.close()

iso.open('one-file-test.iso')
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
