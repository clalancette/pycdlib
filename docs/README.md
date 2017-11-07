# PyCdlib
PyCdlib is a pure python library to parse, write (master), and create ISO9660 files.  These files are suitable for writing to a CD or USB.

## Standards
The original ISO9660 standard is fairly old, having first been ratified in 1988.  This standard has many limitations (such as a maximum of 8 directory levels, a maximum of 31 characters for filenames, etc.), and thus many extensions have made the original standard a lot more palatable on modern systems.  The most relevant standards that are used today include:

- [ISO 9660:1988](https://en.wikipedia.org/wiki/ISO_9660). Information processing - Volume and file structure of CD-ROM for information interchange.  Also known as [Ecma-119](https://www.ecma-international.org/publications/standards/Ecma-119.htm).
- [ISO/EIC 9660:1999](http://pismotec.com/cfs/iso9660-1999.html).  Information technology -- Volume and file structure of CD-ROM for information interchange.
- [El Torito](http://wiki.osdev.org/El-Torito) Bootable CD-ROM Format Specification Version 1.0.
- [Joliet](https://en.wikipedia.org/wiki/Joliet_(file_system)) Specification.
- [System Use Sharing Protocol (SUSP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09 and Version 1.12.
- [Rock Ridge Interchange Protocol (RRIP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09.

Unfortunately, many of these standards require a license to get access to, so most of the links above are not primary sources.  Nevertheless, they give a good overview of the state of the ISO ecosystem as it exists today.

While PyCdlib aims to be compliant with these standards, there are a number of complicating factors.  One such factor is that there are places in the standards that are ambiguous, and different implementations have taken different approaches to solving the same problem.  Another complicating factor is the fact that there are several "standard" parts of ISOs that have no relevant standard backing them up; they are just generally agreed to by the various implementations.  PyCdlib takes a middle road here, and tries to be pretty forgiving with the type of ISOs that it can open, but fairly strict with what it can produce.  When there are ambiguities in the standards, PyCdlib generally takes the approach of being compliant with whatever [cdrkit](https://launchpad.net/cdrkit) does.  However, there are several bugs in the cdrkit implementation, so in those cases, PyCdlib falls back to being ISO standard compliant.

## PyCdlib theory of operation
PyCdlib aims to allow users to manipulate ISOs in arbitrary ways, from creating new ISOs to modifying and writing out existing ISOs.  Along the way, the PyCdlib API is meant to hide many of the details of the above standards, letting users concentrate on the modifications they wish to make.

To start using the PyCdlib API, the user must create a new PyCdlib object.  A PyCdlib object cannot do very much until it is initialized, either by creating a new ISO (using the `new` method), or by opening an existing ISO (using the `open` method).  Once a PyCdlib object is initialized, files can be added or removed, directories can be added or removed, the ISO can be made bootable, and various other manipulations of the ISO can happen.  Once the uesr is happy with the current layout of the ISO, the `write` method can be called, which will write out the current state of the ISO to a file (or file-like object).

## Testing
PyCdlib has an extensive test suite of hundreds of (black box)[https://en.wikipedia.org/wiki/Black-box\_testing] tests that get run on each release.  There are three types of tests that PyCdlib currently runs:
- In parsing tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib `open` method is used to open up the resulting file and check various aspects of the file.  This ensures that PyCdlib can successfully open up existing ISOs.
- In new tests, a new ISO is created using the PyCdlib `new` method, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.
- In hybrid tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib `open` method is used to up the resulting file, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that thiings were created as they should be.

PyCdlib currently has 88% code coverage from the tests, and anytime a new bug is found, a test is written to ensure that the bug can't happen again.

## Examples
The easiest way to learn PyCdlib is to see some examples.  We'll start out each example with the entire source code needed to run the example, and then break down each example to show what the individual pieces do.  Note that in most cases, error handling is elided for brevity, though it probably shouldn't be in real code.

### Creating a new, basic ISO
```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new()
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
iso.add_directory('/DIR1')
iso.write('new.iso')
iso.close()
```

Let's take a closer look at some of this code.

```
import StringIO
import pycdlib
```

First import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
```

Create a new PyCdlib object.  At this point, the object can only do one of two things: open up an existing ISO, or create a new ISO.

```
iso.new()
```

Create a new ISO using the `new` method.  The `new` method has quite a few available arguments, but by passing no arguments, we ask for a basic ISO interchange level 1 iso with no extensions.  At this point, we could write out a valid ISO image, but it won't have any files or directories in it, so it wouldn't be very interesting.

```
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
```

Now we add a new file to the ISO.  There are a few details to notice in this code.  The first detail to notice is that there are two related APIs called `add_file` and `add_fp`.  The `add_file` API takes the pathname to a file on the local disk to get the contents from.  The `add_fp` API takes a file-like object to get the contents from; this can be a normal file-object (such as that returned by standard python (open)[https://docs.python.org/3.6/library/functions.html#open], or this can be any other object that acts like a file.  In this case, we just use a python `StringIO` object, which behaves like a file-object but is backed by a string.  The second detail to notice is that the second argument to `add_fp` is the length of the content to add to the ISO.  Since file-like objects don't have a standard way to get the length, this must be provided by the user.  The `add_file` API can use the length of the file itself for this purpose, so the second argument isn't required there.  The third detail to notice is that the final argument to `add_fp` is the location of the file on the resulting ISO (also known as the `iso_path`).  The `iso_path` is specified using something similar to a Unix file path.  These paths differ from Unix file paths in that they *must* be absolute paths, since PyCdlib has no concept of a current working directory.  All intermediate directories along the path must exist, otherwise the `add_fp` call will fail (the `/` root directory always exists and doesn't have to be explicitly created).  Also note that ISO9660-compliant filenames have a slightly odd format owing to their history.  In standard ISO interchange level 1, filenames have a maximum of 8 characters, followed by a required dot, followed by a maximum 3 character extension, followed by a semicolon and a version.  The filename and the extension are both optional, but one or the other must exist.  Only uppercase letters, numbers, and underscore are allowed for either the name or extension.  If any of these rules are violated, PyCdlib will throw an exception.

```
iso.add_directory("/DIR1")
```

Here we add a new directory to the ISO called `DIR1`.  Like `add_fp`, the `iso_path` argument to `add_directory` is an absolute, Unix like pathname.  The rules for ISO directory names are similar to that of filenames, except that directory names do not have extensions and do not have versions.

```
iso.write('new.iso')
```

Now we finally get to write out the ISO we just created.  The process of writing out an ISO is sometimes called "mastering".  In any case, this is the process of writing the contents of the ISO out to a file on disk.  Similar to the `add_file` and `add_fp` methods, there are the related `write_file` and `write_fp` methods, the former of which takes a filename to write to, and the latter of which takes a file-like object.

```
iso.close()
```

Close out the PyCdlib object, releasing all resources and invalidating the contents.  After this call, the object can be reused to create a new ISO or open up an existing ISO.

### Exceptions


## Tools

