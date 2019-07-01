#!/usr/bin/env python3

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

import pydoc
import lxml.etree

html = pydoc.HTMLDoc()

# Generate the documentation from the pydoc strings
obj, name = pydoc.resolve('pycdlib.pycdlib', 0)
page = html.page(pydoc.describe(obj), html.document(obj, name))

# Now parse that documentation
parser = lxml.etree.HTMLParser()
tree = lxml.etree.parse(BytesIO(page.encode('ascii')), parser)

# Now we remove the "Modules" section, since it contains only links to parts
# of the API that we are not documenting
doc = tree.getroot()

# Remove the 'file:/absolute/path' link
path_a = doc.xpath('/html/body/table[1]/tr/td[2]/font/a[2]')
path_a[0].getparent().remove(path_a[0])

tables = doc.xpath('/html/body/table')
remove_table = None
for table in tables:
    for tr in table.xpath('tr'):
        bgcolor = tr.get('bgcolor')
        if bgcolor == '#aa55cc':
            # We found the 'Modules' section; go back up to the table to remove it
            remove_table = table
            break

if remove_table is not None:
    remove_table.getparent().remove(remove_table)

# Print out the results
print(lxml.etree.tostring(doc).decode('ascii'))
