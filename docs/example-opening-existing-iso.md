# Example: Opening an existing ISO
This example will show how to examine an existing ISO.  Here's the complete code for this example:

```python
import sys
import pycdlib

iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])

for child in iso.list_children(iso_path='/'):
    print(child.file_identifier())

iso.close()
```

Let's take a closer look at the code.

```python
import sys
import pycdlib
```

As we've seen before, import pycdlib.  We also import the sys module so we get access to the command-line arguments.

```python
iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])
```

As we saw in the last example, create a new PyCdlib object.  Once we have the object, we can then open up the file passed on the command-line.  During the open, PyCdlib will parse all of the metadata on the ISO, so if the file is coming over a network, this may take a bit of time.  Note that besides the [open](pycdlib-api.html#PyCdlib-open) method, there is also an [open_fp](pycdlib-api.html#PyCdlib-open_fp) method that takes an arbitrary file-like object.

```python
for child in iso.list_children(iso_path='/'):
    print(child.file_identifier())
```

Use the [list_children](pycdlib-api.html#PyCdlib-list_children) API from PyCdlib to iterate over all of the files and directories at the root of the ISO.  As discussed in the [Creating a new, basic ISO](example-creating-new-basic-iso.md) example, the paths are Unix-like absolute paths.

Note that `iso_path` selects the plain ISO9660 view of the filesystem, so the names printed above will be the ISO9660 names.  Those are restricted to upper-case letters, digits, and underscores, are truncated to 8.3 (or 31 characters, depending on the interchange level), and carry a trailing version number, so a file that shows up as `install-tl-windows.bat` on a desktop operating system may be listed here as `INSTALL_.BAT;1`.  The full names live in one of the ISO extensions: Rock Ridge (mostly Linux/Unix ISOs), Joliet (mostly Windows ISOs), or UDF (DVDs and many modern ISOs).  Most real-world ISOs carry at least one of these, and desktop operating systems prefer them over the ISO9660 names.  To see the same names that a desktop would show, check which extensions the ISO has with [has_rock_ridge](pycdlib-api.html#PyCdlib-has_rock_ridge), [has_joliet](pycdlib-api.html#PyCdlib-has_joliet), and [has_udf](pycdlib-api.html#PyCdlib-has_udf), and then pass `rr_path`, `joliet_path`, or `udf_path` instead of `iso_path`:

```python
if iso.has_udf():
    kwargs = {'udf_path': '/'}
elif iso.has_rock_ridge():
    kwargs = {'rr_path': '/'}
elif iso.has_joliet():
    kwargs = {'joliet_path': '/'}
else:
    kwargs = {'iso_path': '/'}

for child in iso.list_children(**kwargs):
    if child.is_dot() or child.is_dotdot():
        continue
    print(iso.full_path_from_dirrecord(child, rockridge='rr_path' in kwargs))
```

The same `iso_path`/`rr_path`/`joliet_path`/`udf_path` choice applies to every API that takes a path, including [get_record](pycdlib-api.html#PyCdlib-get_record), [walk](pycdlib-api.html#PyCdlib-walk), [get_file_from_iso](pycdlib-api.html#PyCdlib-get_file_from_iso), and [open_file_from_iso](pycdlib-api.html#PyCdlib-open_file_from_iso).  Note that the path must be spelled in the namespace you select; a Joliet path uses the Joliet name (`/install-tl-windows.bat`), not the ISO9660 name (`/INSTALL_.BAT;1`).  [full_path_from_dirrecord](pycdlib-api.html#PyCdlib-full_path_from_dirrecord) is used above because it decodes the name in whichever encoding the selected namespace uses (Joliet names, for instance, are UCS-2), while [file_identifier](pycdlib-api.html#DirectoryRecord-file_identifier) returns the raw on-disk bytes.

```python
iso.close()
```

Close out the PyCdlib object, releasing all resources and invalidating the contents.  After this call, the object can be reused to create a new ISO or open up an existing ISO.

---

<div style="width: 100%; display: table;">
  <div style="display: table-row;">
    <div style="width: 33%; display: table-cell; text-align: left;">
      <a href="example-creating-new-basic-iso.html"><-- Example: Creating a new, basic ISO</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: center;">
      <a href="https://clalancette.github.io/pycdlib/">Top</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: right;">
      <a href="example-extracting-data-from-iso.html">Example: Extracting data from an existing ISO --></a>
    </div>
</div>
