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
iso.open(open('eltorito.iso', 'rb'))
iso.print_tree()
f = StringIO.StringIO()
iso.get_and_write('/BOOT.CAT;1', f)
iso.close()

import binascii
print binascii.hexlify(f.getvalue())
