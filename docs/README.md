# PyCdlib
PyCdlib is a pure python library to parse, write (master), and create ISO9660 files.  These files are suitable for writing to a CD or USB.

## Standards
The original ISO9660 standard is fairly old, having first been ratified in 1988.  This standard has many limitations (such as a maximum of 8 directory levels, a maximum of 31 characters for filenames, etc.), and thus many extensions have made the original standard a lot more palatable on modern systems.  The most relevant standards that are used today include:

- [ISO 9660:1988](https://en.wikipedia.org/wiki/ISO_9660). Information processing - Volume and file structure of CD-ROM for information interchange.  Also known as [Ecma-119](https://www.ecma-international.org/publications/standards/Ecma-119.htm).
- [ISO/EIC 9660:1999](http://pismotec.com/cfs/iso9660-1999.html).  Information technology -- Volume and file structure of CD-ROM for information interchange.
- [El Torito](http://wiki.osdev.org/El-Torito) Bootable CD-ROM Format Specification Version 1.0.
- [Joliet](https://en.wikipedia.org/wiki/Joliet_(file_system)) Specification.
- [System Use Sharing Protocol (SUSP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09 and Version 1.12.
- [Rock Ridge Interchange Protocol (RRIP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09 and Version 1.12.

Unfortunately, many of these standards require a license to get access to, so most of the links above are not primary sources.  Nevertheless, they give a good overview of the state of the ISO ecosystem as it exists today.

While PyCdlib aims to be compliant with these standards, there are a number of complicating factors.  One such factor is that there are places in the standards that are ambiguous, and different implementations have taken different approaches to solving the same problem.  Another complicating factor is the fact that there are several "standard" parts of ISOs that have no relevant standard backing them up; they are just generally agreed to by the various implementations.  PyCdlib takes a middle road here, and tries to be pretty forgiving with the type of ISOs that it can open, but fairly strict with what it can produce.  When there are ambiguities in the standards, PyCdlib generally takes the approach of being compliant with whatever [cdrkit](https://launchpad.net/cdrkit) does.  However, there are several bugs in the cdrkit implementation, so in those cases, PyCdlib falls back to being ISO standard compliant.

## Rock Ridge and Joliet
The two most common extensions to the original ISO9660 are Rock Ridge and Joliet, both of which allow ISOs to contain much deeper directory structures, longer filenames, and other featuers usually used by modern filesystems.  While both standards aim to accomplish the same goal, they do it in entirely different ways, and some of those details leak through into the PyCdlib API.  Thus, a brief discussion of each of them is in order.

### Rock Ridge
The standard commonly referred to as "Rock Ridge" is actually two standards, SUSP and Rock Ridge proper.  SUSP stands for "System Use and Sharing Protocol", and defines a few generic, operating system-independent fields to be placed at the end of file and directory metadata on the ISO.  Rock Ridge proper then defines a number of Unix-specific fields to be placed at the end of file and directory metadata on the ISO.  The combination of the two allows ISOs to contain Unix-like semantics for each file and directory, including permission bits, longer filenames, timestamps, symlinks, character and block devices, and a few other minor features.  One important thing to realize about Rock Ridge is that it is an extension to the original ISO9660, and thus shares the file/directory structure with the original ISO.  This structure can actually be virtually extended for deeper directory structures, but that is an implementation detail and will be glossed over here.  For more information, read the Rock Ridge specification.

### Joliet
The Joliet standard came out of Microsoft, and was primarily intended to provide extensions to ISO for Windows compatibility.  However, the data stored in Joliet is mostly generic, so can easily be used by all operating systesm.  In large contrast to Rock Ridge, Joliet uses an entirely different namespace to store the file and directory structure of the extended names.  The file *data* is shared between ISO9660 and Joliet, but the essential metadata is not.  The consequence of this is that there can be files on the ISO that are only visible to ISO9660/Rock Ridge, files that are only visible to Joliet, or files that are visible to both.  That being said, the most common arrangement by far is for the file and directory structure to be replicated between ISO9660/Rock Ridge and Joliet.

## Python Compatibility
PyCdlib works equally well with Python 2.7 and Python 3.6+.  The test suite (discussed later) ensures that the core PyCdlib code works with both flavors of Python.  Note that most of the command-line tools use Python 2 by default.

## PyCdlib theory of operation
PyCdlib aims to allow users to manipulate ISOs in arbitrary ways, from creating new ISOs to modifying and writing out existing ISOs.  Along the way, the PyCdlib API is meant to hide many of the details of the above standards, letting users concentrate on the modifications they wish to make.

To start using the PyCdlib API, the user must create a new PyCdlib object.  A PyCdlib object cannot do very much until it is initialized, either by creating a new ISO (using the `new` method), or by opening an existing ISO (using the `open` method).  Once a PyCdlib object is initialized, files can be added or removed, directories can be added or removed, the ISO can be made bootable, and various other manipulations of the ISO can happen.  Once the user is happy with the current layout of the ISO, the `write` method can be called, which will write out the current state of the ISO to a file (or file-like object).

Due to some historical aspects of the ISO standards, making modifications to an existing ISO can involve shuffling around a lot of metadata.  In order to maintain decent performance, PyCdlib takes a "lazy" approach to updating that metadata, and only does the update when it needs the results.  This allows the user to make several modifications and effectively "batch" operations without significantly impacting speed.  The minor downside to this is that the metadata stored in the PyCdlib object is not always consistent, so if the user wants to reach into the object to look at a particular field, it may not always be up-to-date.  PyCdlib offers a `force_consistency` API that immediately updates all metadata for just this reason.

## Testing
PyCdlib has an extensive test suite of hundreds of [black box](https://en.wikipedia.org/wiki/Black-box\_testing) tests that get run on each release.  There are three types of tests that PyCdlib currently runs:
- In parsing tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib `open` method is used to open up the resulting file and check various aspects of the file.  This ensures that PyCdlib can successfully open up existing ISOs.
- In new tests, a new ISO is created using the PyCdlib `new` method, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.
- In hybrid tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib `open` method is used to up the resulting file, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.

PyCdlib currently has 88% code coverage from the tests, and anytime a new bug is found, a test is written to ensure that the bug can't happen again.

## Examples
The easiest way to learn PyCdlib is to see some examples.  We'll start out each example with the entire source code needed to run the example, and then break down each example to show what the individual pieces do.  Note that in most cases, error handling is elided for brevity, though it probably shouldn't be in real code.

### Creating a new, basic ISO
This example will show how to create a new, basic ISO with no extensions.  Here's the complete code for this example:

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

Let's take a closer look at the code.

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

### Opening an existing ISO
This example will show how to examine an existing ISO.  Here's the complete code for this example:

```
import sys

import pycdlib

iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])
for child in iso.list_dir('/'):
    print(child.file_identifier())

iso.close()
```

Let's take a closer look at the code.

```
import sys

import pycdlib
```

As we've seen before, import pycdlib.  We also import the sys module so we get access to the command-line arguments.

```
iso = pycdlib.PyCdlib()
iso.open(sys.argv[1])
```

As we saw in the last example, create a new PyCdlib object.  Once we have the object, we can then open up the file passed on the command-line.  During the open, PyCdlib will parse all of the metadata on the ISO, so if the file is coming over a network, this may take a bit of time.  Note that besides the `open` method, there is also an `open_fp` method that takes an arbitrary file-like object.

```
for child in iso.list_dir('/'):
    print(child.file_identifier())
```
Use the `list_dir` API from PyCdlib to iterate over all of the files and directories at the root of the ISO.  As discussed in the "Creating a new,basic ISO" example, the paths are Unix-like absolute paths.

```
iso.close()
```

Close out the PyCdlib object, releasing all resources and invalidating the contents.  After this call, the object can be reused to create a new ISO or open up an existing ISO.

### Extract data from an existing ISO
This example will show how to extract data from an existing ISO.  Here's the complete code for this example:

```
import StringIO

import pycdlib

iso = pycdlib.PyCdlib()
iso.new()
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
out = StringIO.StringIO()
iso.write_fp(out)
iso.close()

iso.open_fp(out)
extracted = StringIO.StringIO()
iso.get_and_write_fp("/FOO.;1", extracted)
iso.close()

print(extracted)
```

Let's take a closer look at the code.

```
import StringIO

import pycdlib
```

As we've seen before, import pycdlib.  We also import the StringIO module so we can use a python string as a file-like object.

```
iso = pycdlib.PyCdlib()
iso.new()
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
out = StringIO.StringIO()
iso.write_fp(out)
iso.close()
```

This code creates a new ISO, adds a single file to it, and writes it out.  This is very similar to the code in "Creating a new, basic ISO", so see that example for more information.  One important difference with this code is that it uses StringIO as a file-like object so we don't have to write any temporary data out to the filesystem; it happens all in memory.

```
iso.open_fp(out)
```

Here we open up the ISO we created above.  We can safely re-use the PyCdlib object because we did an `iso.close` above.  Also note that we use `open_fp` to open the file-like object we wrote into using `write_fp` above.

```
extracted = StringIO.StringIO()
iso.get_and_write_fp("/FOO.;1", extracted)
```

Now we use the `get_and_write_fp` API to extract the data from a file on the ISO.  In this case, we access the /FOO.;1 file that we created above, and write out the data to the StringIO object `extracted`.

```
iso.close()

print(extracted)
```

As is the case in other examples, we close out the PyCdlib object, and print out the data we extracted.

### Create a bootable ISO (El Torito)
This example will show how to create a bootable ISO, also known as an "El Torito" ISO.  Here's the complete code for the example:

```
import StringIO

import pycdlib

iso = pycdlib.PyCdlib()

iso.new()

bootstr = "boot\n"
iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), '/BOOT.;1')

iso.add_eltorito('/BOOT.;1')

iso.write('eltorito.iso')

iso.close()
```

Let's take a closer look at the code.

```
import StringIO

import pycdlib
```

As usual, import the necessary libraries, include pycdlib

```
iso = pycdlib.PyCdlib()

iso.new()
```

Create a new PyCdlib object, and then create a new, basic ISO.

```
bootstr = "boot\n"
iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), '/BOOT.;1')
```

Add a file called /BOOT.;1 to the ISO.  This is the file that contains the data to be used to boot the ISO when placed into a computer.  The name of the file can be anything (and can even be nested in directories), but the contents have to be very specific.  Getting the appropriate data into the boot file is beyond the scope of this tutorial; see [isolinux](http://www.syslinux.org/wiki/index.php?title=ISOLINUX) for one way of getting the appropirate data.  Suffice it to say that the example code that we are using above will not actually boot, but is good enough to show the PyCdlib API usage.

```
iso.add_eltorito('/BOOT.;1')
```

Add El Torito to the ISO, making the boot file /BOOT.;1.  After this call, the ISO is actually bootable.  By default, the `add_eltorito` method will use so-called "no emulation" booting, which allows arbitrary data in the boot file.  "Hard drive" and "floppy" emulation is also supported, though these options are more esoteric and need specifically configured boot data to work properly.

```
iso.write('eltorito.iso')

iso.close()
```

Write the ISO out to a file, and close out the PyCdlib object.


### Create an ISO with Rock Ridge extensions

### Create an ISO with Joliet extensions

### Managing hard-links on an ISO

### Modifying a file in place

### Forcing consistency

### Creating a "hybrid" ISO

## Exceptions

## Tools

### pycdlib-genisoimage

### pycdlib-explorer

## What to do when things go wrong
* Send me an ISO