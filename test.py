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

iso = pyiso.PyIso()
iso.open('one-file-test.iso')
iso.print_tree()
f = iso.get_file('/foo')
print("'%s'" % f)
#iso.get_file('/')
iso.get_and_write_file('/foo', 'bar', overwrite=True)
print(iso.list_files("/")[0])
iso.add_data("bar\n", "/bar")
iso.write("test.iso", overwrite=True)
iso.close()

#iso.open('dup-name-test.iso')
#iso.print_tree()
#print("'%s'" % iso.get_and_write_file('/abcde000'))
#iso.close()
