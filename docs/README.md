# PyCdlib
PyCdlib is a pure python library to parse, write (master), create, and manipulate ISO9660 files.  These files are suitable for writing to a CD or USB.

## Standards
The original ISO9660 standard is fairly old, having first been ratified in 1988.  This standard has many limitations (such as a maximum of 8 directory levels, a maximum of 31 characters for filenames, etc.), and thus a number of extensions have made the original standard a lot more palatable on modern systems.  The most relevant standards that are used today include:

- [ISO 9660:1988](https://en.wikipedia.org/wiki/ISO_9660). Information processing - Volume and file structure of CD-ROM for information interchange.  Also known as [Ecma-119](https://www.ecma-international.org/publications/standards/Ecma-119.htm).
- [ISO/EIC 9660:1999](http://pismotec.com/cfs/iso9660-1999.html).  Information technology -- Volume and file structure of CD-ROM for information interchange.
- [El Torito](http://wiki.osdev.org/El-Torito) Bootable CD-ROM Format Specification Version 1.0.
- [Joliet](https://en.wikipedia.org/wiki/Joliet_(file_system)) Specification.
- [System Use Sharing Protocol (SUSP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09 and Version 1.12.
- [Rock Ridge Interchange Protocol (RRIP)](https://en.wikipedia.org/wiki/Rock_Ridge), Version 1.09 and Version 1.12.

Unfortunately, accessing most of these standards requires a license, so the links above are not primary sources.  Nevertheless, they give a good overview of the state of the ISO ecosystem as it exists today.

While PyCdlib aims to be compliant with these standards, there are a number of complicating factors.  One such factor is that there are places in the standards that are ambiguous, and different implementations have taken different approaches to solving the same problem.  Another complicating factor is the fact that there are several "standard" parts of ISOs that have no relevant standard backing them up; they are just generally agreed to by the various implementations.  PyCdlib takes a middle road here, and tries to be pretty forgiving with the type of ISOs that it can open, but fairly strict with what it can produce.  When there are ambiguities in the standards, PyCdlib generally takes the approach of being compliant with whatever [cdrkit](https://launchpad.net/cdrkit) does.  However, there are several bugs in the cdrkit implementation, so in those cases, PyCdlib falls back to being ISO standard compliant.

### Interchange levels
The original ISO9660 standard defines "interchange" levels 1, 2, and 3.  The differences between the three interchange levels is mostly irrelevant now, as most modern ISOs use interchange level 3 (and supplement it with one of the extensions).  A newer version of the ISO9660 standard was put out in 1999 that lifts some of the restrictions of the original ISO9660 standard.  PyCdlib follows the lead of genisoimage here and defines this as interchange level 4, although that is not an "official" designation.  For almost all use cases, interchange level 3 should be used with the [Rock Ridge](#rock-ridge) and [Joliet](#joliet) extensions.

### Rock Ridge and Joliet
The two most common extensions to the original ISO9660 standard are Rock Ridge and Joliet, both of which allow ISOs to contain deeper directory structures, longer filenames, and other features usually used by modern filesystems.  While both standards aim to accomplish the same goal, they do it in entirely different ways, and some of those details leak through into the PyCdlib API.  Thus, a brief discussion of each of them is in order.

#### Rock Ridge
The standard commonly referred to as "Rock Ridge" is actually two standards, SUSP and Rock Ridge proper.  SUSP stands for "System Use and Sharing Protocol", and defines a few generic, operating system-independent fields to be placed at the end of file and directory metadata on the ISO.  Rock Ridge proper then defines a number of Unix-specific fields to be placed after the SUSP fields.  The combination of the two allows ISOs to contain Unix-like semantics for each file and directory, including permission bits, longer filenames, timestamps, symlinks, character and block devices, and a few other minor features.  One important thing to realize about Rock Ridge is that it is an extension to the original ISO9660, and thus shares the file/directory structure with the original ISO.  This structure can actually be virtually extended for deeper directory structures, but that is an implementation detail and will be glossed over here.  For more information, read the Rock Ridge specification.

#### Joliet
The Joliet standard came out of Microsoft, and is primarily intended to provide extensions to ISO for Windows compatibility.  However, the data stored in Joliet is mostly generic, so can easily be used by all operating systems.  In large contrast to Rock Ridge, Joliet uses an entirely different namespace to store the file and directory structure of the extended names.  The file *data* is shared between ISO9660 and Joliet, but the essential metadata is not.  The consequence of this is that there can be files on the ISO that are only visible to ISO9660/Rock Ridge, files that are only visible to Joliet, or files that are visible to both.  That being said, the most common arrangement is for the file and directory structure to be replicated between ISO9660/Rock Ridge and Joliet.

### El Torito
El Torito is the name of the standard used to make an ISO bootable.  Without going into the details too much, El Torito works by defining a "boot catalog" that has a list of one or more entries for booting.  Each entry consists of a pointer to a file on the ISO, and a booting method.  The available booting methods are:

1.  Floppy emulation booting - Emulate the boot that would have been done by a floppy disk.  The file to be used must be one of the sizes of a floppy, and must have a particular structure.  This method was developed to support very old BIOS's that didn't know how to boot from a CD, but is rarely used anymore.
1.  HD emulation - Emulate the boot that would have happened from a hard drive.  The file to be used must be 512 bytes long, and be a valid MBR.  Again, this method was developed to support old BIOS's, but is rarely used in modern ISOs.
1.  No emulation - Don't do any emulation for booting.  This is the method that is used for BIOS's that know how to boot from ISO, and is the one most commonly used today.  There are few restrictions on what the contents of the file must be, other than it should be valid code for the machine it will be used to boot.

## Python Compatibility
PyCdlib works equally well with Python 2.7 and Python 3.6+.  The [test suite](#testing) ensures that the core PyCdlib code works with both flavors of Python.  Note that most of the command-line tools use Python 2 by default.

## PyCdlib theory of operation
PyCdlib aims to allow users to manipulate ISOs in arbitrary ways, from creating new ISOs to modifying and writing out existing ISOs.  Along the way, the PyCdlib API is meant to hide many of the details of the above standards, letting users concentrate on the modifications they wish to make.

To start using the PyCdlib API, the user must create a new PyCdlib object.  A PyCdlib object cannot do very much until it is initialized, either by creating a new ISO (using the [new](pycdlib-api.html#PyCdlib-new) method), or by opening an existing ISO (using the [open](pycdlib-api.html#PyCdlib-open) method).  Once a PyCdlib object is initialized, files can be added or removed, directories can be added or removed, the ISO can be made bootable, and various other manipulations of the ISO can happen.  Once the user is happy with the current layout of the ISO, the [write](pycdlib-api.html#PyCdlib-write) method can be called, which will write out the current state of the ISO to a file (or file-like object).

Due to some historical aspects of the ISO standards, making modifications to an existing ISO can involve shuffling around a lot of metadata.  In order to maintain decent performance, PyCdlib takes a "lazy" approach to updating that metadata, and only does the update when it needs the results.  This allows the user to make several modifications and effectively "batch" operations without significantly impacting speed.  The minor downside to this is that the metadata stored in the PyCdlib object is not always consistent, so if the user wants to reach into the object to look at a particular field, it may not always be up-to-date.  PyCdlib offers a [force\_consistency](pycdlib-api.html#PyCdlib-force_consistency) API that immediately updates all metadata for just this reason.

## Testing
PyCdlib has an extensive test suite of hundreds of [black box](https://en.wikipedia.org/wiki/Black-box\_testing) tests that get run on each release.  There are three types of tests that PyCdlib currently runs:
- In _parsing_ tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib [open](pycdlib-api.html#PyCdlib-open) method is used to open up the resulting file and check various aspects of the file.  This ensures that PyCdlib can successfully open up existing ISOs.
- In _new_ tests, a new ISO is created using the PyCdlib [new](pycdlib-api.html#PyCdlib-new) method, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.
- In _hybrid_ tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib [open](pycdlib-api.html#PyCdlib-open) method is used to open up the resulting file, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.

PyCdlib currently has 88% code coverage from the tests, and anytime a new bug is found, a test is written to ensure that the bug can't happen again.

## Examples
The easiest way to learn PyCdlib is to see some examples.  We'll start out each example with the entire source code needed to run the example, and then break down the code to show what the individual pieces do.  Note that in most cases, error handling is elided for brevity, though it probably shouldn't be in real code.

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

Create a new ISO using the [new](pycdlib-api.html#PyCdlib-new) method.  The [new](pycdlib-api.html#PyCdlib-new) method has quite a few available arguments, but by passing no arguments, we ask for a basic interchange level 1 ISO with no extensions.  At this point, we could write out a valid ISO image, but it won't have any files or directories in it, so it wouldn't be very interesting.

```
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
```

Now we add a new file to the ISO.  There are a few details to notice in this code.  The first detail is that there are two related APIs called [add_file](pycdlib-api.html#PyCdlib-add_file) and [add_fp](pycdlib-api.html#PyCdlib-add_fp).  The [add_file](pycdlib-api.html#PyCdlib-add_file) API takes the pathname to a file on the local disk to get the contents from.  The [add_fp](pycdlib-api.html#PyCdlib-add_fp) API takes a file-like object to get the contents from; this can be a normal file-object (such as that returned by standard python [open](https://docs.python.org/3.6/library/functions.html#open)), or this can be any other object that acts like a file.  In this case, we use a python [StringIO](https://docs.python.org/2/library/stringio.html) object, which behaves like a file-object but is backed by a string.  The second detail to notice is that the second argument to [add_fp](pycdlib-api.html#PyCdlib-add_fp) is the length of the content to add to the ISO.  Since file-like objects don't have a standard way to get the length, this must be provided by the user.  The [add_file](pycdlib-api.html#PyCdlib-add_file) API can use the length of the file itself for this purpose, so the second argument isn't required there.  The third detail to notice is that the final argument to [add_fp](pycdlib-api.html#PyCdlib-add_fp) is the location of the file on the resulting ISO (also known as the `iso_path`).  The `iso_path` is specified using something similar to a Unix file path.  These paths differ from Unix file paths in that they *must* be absolute paths, since PyCdlib has no concept of a current working directory.  All intermediate directories along the path must exist, otherwise the [add_fp](pycdlib-api.html#PyCdlib-add_fp) call will fail (the `/` root directory always exists and doesn't have to be explicitly created).  Also note that ISO9660-compliant filenames have a slightly odd format owing to their history.  In standard ISO interchange level 1, filenames have a maximum of 8 characters, followed by a required dot, followed by a maximum 3 character extension, followed by a semicolon and a version.  The filename and the extension are both optional, but one or the other must exist.  Only uppercase letters, numbers, and underscore are allowed for either the name or extension.  If any of these rules are violated, PyCdlib will throw an exception.

```
iso.add_directory("/DIR1")
```

Here we add a new directory to the ISO called `DIR1`.  Like [add_fp](pycdlib-api.html#PyCdlib-add_fp), the `iso_path` argument to [add_directory](pycdlib-api.html#PyCdlib-add_directory) is an absolute, Unix like pathname.  The rules for ISO directory names are similar to that of filenames, except that directory names do not have extensions and do not have versions.

```
iso.write('new.iso')
```

Now we finally get to write out the ISO we just created.  The process of writing out an ISO is sometimes called "mastering".  In any case, this is the process of writing the contents of the ISO out to a file on disk.  Similar to the [add_file](pycdlib-api.html#PyCdlib-add_file) and [add_fp](pycdlib-api.html#PyCdlib-add_fp) methods, there are the related [write](pycdlib-api.html#PyCdlib-write) and [write_fp](pycdlib-api.html#PyCdlib-write_fp) methods, the former of which takes a filename to write to, and the latter of which takes a file-like object.

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

for child in iso.list_children('/'):
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

As we saw in the last example, create a new PyCdlib object.  Once we have the object, we can then open up the file passed on the command-line.  During the open, PyCdlib will parse all of the metadata on the ISO, so if the file is coming over a network, this may take a bit of time.  Note that besides the [open](pycdlib-api.html#PyCdlib-open) method, there is also an [open_fp](pycdlib-api.html#PyCdlib-open_fp) method that takes an arbitrary file-like object.

```
for child in iso.list_children('/'):
    print(child.file_identifier())
```

Use the [list_children](pycdlib-api.html#PyCdlib-list_children) API from PyCdlib to iterate over all of the files and directories at the root of the ISO.  As discussed in the [Creating a new, basic ISO](#creating-a-new-basic-iso) example, the paths are Unix-like absolute paths.

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
iso.get_file_from_iso_fp(extracted, iso_path="/FOO.;1")
iso.close()

print(extracted)
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As we've seen before, import pycdlib.  We also import the [StringIO](https://docs.python.org/2/library/stringio.html) module so we can use a python string as a file-like object.

```
iso = pycdlib.PyCdlib()
iso.new()
foostr = "foo\n"
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
out = StringIO.StringIO()
iso.write_fp(out)
iso.close()
```

This code creates a new ISO, adds a single file to it, and writes it out.  This is very similar to the code in [Creating a new, basic ISO](#creating-a-new-basic-iso), so see that example for more information.  One important difference in this code is that it uses a `StringIO` object to master the ISO into so we don't have to write any temporary data out to the filesystem; it all happens in memory.

```
iso.open_fp(out)
```

Here we open up the ISO we created above.  We can safely re-use the PyCdlib object because we called the [close](pycdlib-apihtml#PyCdlib-close) method earlier.  Also note that we use [open_fp](pycdlib-api.html#PyCdlib-open_fp) to open the file-like object we wrote into using [write_fp](pycdlib-api.html#PyCdlib-write_fp) above.

```
extracted = StringIO.StringIO()
iso.get_file_from_iso_fp(extracted, iso_path="/FOO.;1")
```

Now we use the [get_file_from_iso_fp](pycdlib-api.html#PyCdlib-get_file_from_iso_fp) API to extract the data from a file on the ISO.  In this case, we access the "/FOO.;1" file that we created above, and write out the data to the StringIO object `extracted`.

```
iso.close()

print(extracted)
```

As is the case in other examples, we close out the PyCdlib object, and print out the data we extracted.

### Create a bootable ISO (El Torito)
This example will show how to create a bootable [El Torito](#el-torito) ISO.  Here's the complete code for the example:

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

As usual, import the necessary libraries, including pycdlib.

```
iso = pycdlib.PyCdlib()

iso.new()
```

Create a new PyCdlib object, and then create a new, basic ISO.

```
bootstr = "boot\n"
iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), '/BOOT.;1')
```

Add a file called /BOOT.;1 to the ISO.  This is the file that contains the data to be used to boot the ISO when placed into a computer.  The name of the file can be anything (and can even be nested in directories), but the contents have to be very specific.  Getting the appropriate data into the boot file is beyond the scope of this tutorial; see [isolinux](http://www.syslinux.org/wiki/index.php?title=ISOLINUX) for one way of getting the appropriate data.  Suffice it to say that the example code that we are using above will not actually boot, but is good enough to show the PyCdlib API usage.

```
iso.add_eltorito('/BOOT.;1')
```

Add El Torito to the ISO, making the boot file "/BOOT.;1".  After this call, the ISO is actually bootable.  By default, the [add_eltorito](pycdlib-api.html#PyCdlib-add_eltorito) method will use so-called "no emulation" booting, which allows arbitrary data in the boot file.  "Hard drive" and "floppy" emulation is also supported, though these options are more esoteric and need specifically configured boot data to work properly.

```
iso.write('eltorito.iso')

iso.close()
```

Write the ISO out to a file, and close out the PyCdlib object.

### Create an ISO with Rock Ridge extensions
This example will show how to create an ISO with the [Rock Ridge](#rock-ridge) extensions.  Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new(rock_ridge="1.09")
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', rr_name="foo")
iso.add_directory('/DIR1', rr_name="dir1")
iso.write('new.iso')
iso.close()
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As in earlier examples, import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
iso.new(rock_ridge="1.09")
```

Create a new PyCdlib object, and then create a new ISO with that object.  In order to make it have Rock Ridge extensions, we pass the argument `rock_ridge="1.09"` to the [new](pycdlib-api.html#PyCdlib-new) method.  PyCdlib supports both Rock Ridge version 1.09 and 1.12, though 1.09 is more common.

```
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', rr_name="foo")
```

As in earlier examples, create a new file on the ISO from a string.  Because this is a Rock Ridge ISO, we have to also supply the `rr_name` argument to the [add_fp](pycdlib-api.html#PyCdlib-add_fp) method.  Forgetting the `rr_name` argument on a Rock Ridge ISO is an error and PyCdlib will throw an exception.  Note that it is called `rr_name`, and that the argument given is truly a name, not an absolute path.  This is because Rock Ridge is an extension to the original ISO9660, and this alternate name will be stored alongside the original ISO data.

```
iso.add_directory('/DIR1', rr_name="dir1")
```

Create a new directory on the ISO.  Again we must pass the `rr_name` argument to [add_directory](pycdlib-api.html#PyCdlib-add_directory), for all of the same reasons and with the same restrictions as we saw above for [add_fp](pycdlib-api.html#PyCdlib-add_fp).

```
iso.write('new.iso')
iso.close()
```

Write the new ISO out to a file, then close out the ISO.

### Create an ISO with Joliet extensions
This example will show how to create an ISO with the [Joliet](#joliet) extensions.  Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new(joliet=3)
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', joliet_path="/foo")
iso.add_directory('/DIR1', joliet_path="/dir1")
iso.write('new.iso')
iso.close()
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As in earlier examples, import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
iso.new(joliet=3)
```

Create a new PyCdlib object, and then create a new ISO with that object.  In order to make it have Joliet extensions, we pass the argument `joliet=3` to the [new](pycdlib-api.html#PyCdlib-new) method.  PyCdlib supports Joliet levels 1, 2, and 3, but level 3 is by far the most common, so is recommended.

```
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', joliet_path="/foo")
```

As in earlier examples, create a new file on the ISO from a string.  Because this is a Joliet ISO, we have to provide the `joliet_path` argument to [add_fp](pycdlib-api.html#PyCdlib-add_fp) as well.  In contrast to Rock Ridge, Joliet is a completely different namespace from the original ISO9660 structure, and so the argument to be passed here must be an absolute path, not a name.  Because of this, the Joliet file can be on a completely different part of the directory structure, or be omitted completely (in which case the file will only show up on the ISO9660 portion of the ISO).  In practice the Joliet portion of the ISO almost always mirrors the ISO9660 portion of the ISO, so it is recommended to do that when creating new Joliet ISOs.

```
iso.add_directory('/DIR1', joliet_path="/dir1")
```

Create a new directory on the ISO.  Again we must pass the `joliet_path` argument to [add_directory](pycdlib-api.html#PyCdlib-add_directory), for all of the same reasons and with the same restrictions as we saw above for [add_fp](pycdlib-api.html#PyCdlib-add_fp).

```
iso.write('new.iso')
iso.close()
```

Write the new ISO out to a file, then close out the ISO.

### Modifying a file in place
This example will show how to use one of the unique features of PyCdlib, the ability to modify a file in place.  While this doesn't seem like a big deal, it is actually somewhat difficult to achieve in an ISO.  The reason is that modifying a file usually involves moving around a lot of metadata, and additionally may require moving around data as well.  For these reasons, PyCdlib has limitations when modifying a file in place.  In particular:

1.  Only files can be modified in place; directories cannot be changed.
1.  Only existing files can be modified; no files can be added or removed.
1.  The file cannot be extended beyond the extent that the current file lives in.  In ISO9660 terms, an extent is (almost) always 2048 bytes.  Thus, if the current file is 48 bytes, the modification can only increase the size of the file by an additional 2000 bytes.  Shrinking a file is almost never a problem, but note that if the file contents are modified to be smaller than the original, no size will be saved on the resulting ISO.

Despite these limitations, modifying a file in place is extremely fast, much faster than traditional modification and mastering.  Therefore, if the use case calls for just changing a few bytes in a file, it is well worth it to consider modifying the file in place.

Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new()
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
outiso = StringIO.StringIO()
iso.write_fp(outiso)
iso.close()

iso.open_fp(outiso)

bazstr = 'bazzzzzz\n'
iso.modify_file_in_place(StringIO.StringIO(bazstr), len(bazstr), '/FOO.;1')

modifiediso = StringIO.StringIO()
iso.write_fp(modifiediso)
iso.close()
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As in earlier examples, import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
iso.new()
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
outiso = StringIO.StringIO()
iso.write_fp(outiso)
iso.close()
```

Create an ISO with a single file called "/FOO.;1" on it.  This is similar to previous examples, with the one exception that we are using the [write_fp](pycdlib-api.html#PyCdlib-write_fp) API to write the ISO out to a string in memory (rather than on-disk).  Note that at this point, the "/FOO.;1" file has the contents 'foo\n' on the ISO.

```
iso.open_fp(outiso)
```

Open up the ISO that is in the `outiso` StringIO object.

```
bazstr = 'bazzzzzz\n'
iso.modify_file_in_place(StringIO.StringIO(bazstr), len(bazstr), '/FOO.;1')
```

Here we get to the heart of the example.  We use [modify_file_in_place](pycdlib-api.html#PyCdlib-modify_file_in_place) to modify the "/FOO.;1" file to have the contents 'bazzzzzz\n'.  We are allowed to expand the size of the file because we are still smaller than the size of the extent (the [modify_file_in_place](pycdlib-api.html#PyCdlib-modify_file_in_place) API enforces this).

```
modifiediso = StringIO.StringIO()
iso.write_fp(modifiediso)
iso.close()
```

Write the modified ISO out to the StringIO object called "modifiediso".  At this point, the "/FOO.;1" file on "modifiediso" has the contents 'bazzzzzz\n'.  Once we are done with this, close out the object.

### Managing hard-links on an ISO
PyCdlib supports an advanced concept called hard-links, which is multiple names for the same piece of data (this is somewhat similar to Unix hard-links).  Most users will not need to use this functionality and should stick with the standard [add_file](pycdlib-api.html#PyCdlib-add_file) and [rm_file](pycdlib-api.html#PyCdlib-rm_file) APIs.  However, for those that want to do more advanced things like hiding a file from Joliet while having it remain visible in ISO9660, this functionality can be useful.

On an ISO, a piece of data can be referred to (possibly several times) from three different contexts:

1.  From the original ISO9660 context, including the Rock Ridge extensions.
1.  From the Joliet context, since this is a separate namespace.
1.  From the El Torito boot record, since this is effectively a separate namespace.

The data can be referred to zero, one, or many times from each of these contexts.  The most classic example of hard-links happens when an ISO has the Joliet extensions.  In that case, there is implicitly a hard-link from the ISO9660 (and Rock Ridge) context to the file contents, and a hard-link from the Joliet context to the file contents.  When a piece of data has zero entries in a context, it is effectively hidden from that context.  For example, a file could be visible from ISO9660/Rock Ridge, but hidden from Joliet, or vice-versa.  A file could be used for booting, but be hidden from both ISO9660/Rock Ridge and Joliet, etc.  Management of these hard-links is done via the PyCdlib APIs [add_hard_link](pycdlib-api.html#PyCdlib-add_hard_link) and [rm_hard_link](pycdlib-api.html#PyCdlib-rm_hard_link).  Adding or removing a file through the [add_file](pycdlib-api.html#PyCdlib-add_file) and [rm_file](pycdlib-api.html#PyCdlib-rm_file) APIs implicitly manipulates hard-links behind the scenes.  Note that hard-links only make sense for files, since directories have no direct data (only metadata).

An example should help to illustrate the concept.  Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new(joliet=3)

foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')

iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')

iso.rm_hard_link(joliet_path='/foo')

outiso = StringIO.StringIO()
iso.write_fp(outiso)

iso.close()
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As in earlier examples, import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
iso.new(joliet=3)
```

As in earlier examples, create a PyCdlib object, and then create a new, empty ISO with the Joliet extensions.

```
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1', joliet_path='/foo')
```

As in earlier examples, add a new file to the ISO.  Here we have provided both the ISO path '/FOO.;1' and the Joliet path '/foo', so the file implicitly has two links; one from the ISO context, and one from the Joliet context.

```
iso.add_hard_link(iso_old_path='/FOO.;1', iso_new_path='/BAR.;1')
```

Add a hard-link from the original '/FOO.;1' location in the ISO context to a second location in the ISO context '/BAR.;1'.  This takes up no additional space on the ISO for the data, only for the metadata.

```
iso.rm_hard_link(joliet_path='/foo')
```

Remove the link from the Joliet context for the file.  Now this file is effectively hidden from the Joliet context, while still being visible in the ISO context.

```
outiso = StringIO.StringIO()
iso.write_fp(outiso)
```

As in earlier examples, write the ISO out to the StringIO object.

```
iso.close()
```

Since we are done with the ISO object, close it out.

### Forcing consistency
As discussed [earlier](#pycdlib-theory-of-operation), PyCdlib takes a lazy approach to updating metadata.  For performance reasons it is recommended to let PyCdlib handle when and how to update the metadata, but sometimes users need the metadata to be consistent immediately.  PyCdlib offers two solutions for this:

1.  There is an API called [force_consistency](pycdlib-api.html#PyCdlib-force_consistency) that immediately updates all metadata to the latest.
1.  When initially creating the PyCdlib object, the user can set the `always_consistent` parameter to True.  When this is True, PyCdlib will update the metadata after every operation, ensuring that it is always up-to-date.

Of the two, using lazy metadata updating and only calling [force_consistency](pycdlib-api.html#PyCdlib-force_consistency) when absolutely needed is highly preferred.  Using `always_consistent` is only needed in specialized cases (such as first modifying, then introspecting the extent number that a file exists on the ISO).  The following example will use [force_consistency](pycdlib-api.html#PyCdlib-force_consistency) at a particular point to cause the metadata to be updated.  To learn how to use `always_consistent`, please see the documentation for the `__init__` method for PyCdlib.

Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()
iso.new()

foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')

iso.force_consistency()

iso.add_directory('/DIR1')

iso.write('new.iso')
iso.close()
```

Let's take a closer look at the code.

```
import StringIO
import pycdlib
```

As in earlier examples, import the relevant libraries, including pycdlib itself.

```
iso = pycdlib.PyCdlib()
iso.new()
```

As in earlier examples, create a new PyCdlib object and then create a new ISO with no extensions.

```
foostr = 'foo\n'
iso.add_fp(StringIO.StringIO(foostr), len(foostr), '/FOO.;1')
```

As in earlier examples, add a new file to the ISO.

```
iso.force_consistency()
```

Now force consistency on the ISO.  This will cause PyCdlib to update all of the metadata on the ISO, and after this call all of the metadata for all entries on the ISO will be accurate.

```
iso.add_directory('/DIR1')
```

As in earlier examples, add a new directory to the ISO.  Note that the metadata on the ISO is now out-of-date again, so to accurately look at the metadata, [force_consistency](pycdlib-api.html#PyCdlib-force_consistency) would have to be called again after this modification.

```
iso.write('new.iso')
```

As in earlier examples, write the ISO out to a file.  The [write](pycdlib-api.html#PyCdlib-write) method implicitly does a metadata update since it needs all of the metadata to be accurate to successfully write out the ISO.

```
iso.close()
```

As in earlier examples, close the PyCdlib object when we are done with it.

### Creating a "hybrid" bootable ISO
The first 32768 bytes of any ISO are designated as "system use".  In a normal ISO (even a bootable one), these bytes are all zero, but this space can also be used to add in alternative booting mechanisms.  In particular, this space can be used to embed boot code so that the file can be written to a USB stick and booted.  These so called "hybrid" ISO files thus have two booting mechanisms: if the file is actually burned to a CD, then "El Torito" is used to boot, but if it is written to a USB stick, then the system use boot code is used to boot.  PyCdlib supports creating hybrid bootable ISOs through the main API, and the following example will show how.

Here's the complete code for the example:

```
import StringIO
import pycdlib

iso = pycdlib.PyCdlib()

iso.new()

bootstr = "boot\n"
iso.add_fp(StringIO.StringIO(bootstr), len(bootstr), '/BOOT.;1')

iso.add_eltorito('/BOOT.;1')

iso.add_isohybrid()

iso.write('eltorito.iso')

iso.close()
```

Let's take a closer look at the code.

```
import StringIO

import pycdlib
```

As usual, import the necessary libraries, including pycdlib.

```
iso = pycdlib.PyCdlib()

iso.new()
```

Create a new PyCdlib object, and then create a new, basic ISO.

```
isolinuxstr = b'\x00'*0x40 + b'\xfb\xc0\x78\x70'
iso.add_fp(StringIO.StringIO(isolinuxstr), len(isolinuxstr), '/BOOT.;1')
```

Add a file called /BOOT.;1 to the ISO.  The contents of this conform to the expected boot start sequence as specified by isolinux.  A complete discussion of the correct form of the file is out of scope for this tutorial; see [isolinux](http://www.syslinux.org/wiki/index.php?title=ISOLINUX) for more details.  The above is the minimum code that conforms to the sequence, though it is not technically bootable.

```
iso.add_eltorito('/BOOT.;1', boot_load_size=4)
```

Add El Torito to the ISO, making the boot file "/BOOT.;1", and setting the `boot_load_size` to 4.  The `boot_load_size` is the number of 512-bytes sectors to read during initial boot.  While other values may be allowed for this, all current examples (from cdrkit or isolinux) use this value.  After this call, the ISO is El Torito bootable, but not yet a hybrid ISO.

```
iso.add_isohybrid()
```

Add the boot file to the system use area, making this a hybrid ISO.  There are various parameters that can be passed to control how the hybrid file is added, but the defaults are typically good enough for creating a hybrid ISO similar to those made for most Linux distributions.

```
iso.write('eltorito.iso')

iso.close()
```

Write the ISO out to a file, and close out the PyCdlib object.


## Exceptions
When things go wrong, PyCdlib generally throws an exception.  There is a base exception called `PyCdlibException`, which is never itself thrown.  Instead, PyCdlib will throw one of the following exceptions, all of which are subclasses of `PyCdlibException`:

* PyCdlibInvalidISO - Thrown when PyCdlib can't successfully parse an ISO with one of the [open](pycdlib-api.html#PyCdlib-open) methods.  Usually this indicates that the ISO does not follow relevant standards, though it can also sometimes be a bug in PyCdlib itself.
* PyCdlibInvalidInput - Thrown when the user provides invalid input to a PyCdlib API.
* PyCdlibInternalError - Thrown when an unexpected situation happens within PyCdlib itself.  This can happen when there is a bug within PyCdlib itself, or sometimes when an ISO that doesn't conform to standards is parsed.

The arrangement of a base exception of `PyCdlibException` along with subclassed specified errors allows maximum error handling flexibility for client programs.  If a client program wants to handle all PyCdlib errors, it can catch `PyCdlibException`, but if it wants to do something different based on the exception type, it can catch the various exception types.

## Tools

### pycdlib-genisoimage
The `pycdlib-genisoimage` tool aims to be a flag-compatible drop-in replacement for the venerable [genisoimage](https://linux.die.net/man/1/genisoimage) tool, with the big exception that it uses PyCdlib under the hood.  Please see the man page [pycdlib-genisoimage](pycdlib-genisoimage.html) for more information.

### pycdlib-explorer
The `pycdlib-explorer` tool gives a convenient, shell-like interface for opening, exploring, and manipulating existing ISO files.  Please see the man page [pycdlib-explorer](pycdlib-explorer.html) for more information.

## What to do when things go wrong
The PyCdlib library can fail for a number of reasons.  The most common reason for an unexpected failure is when an ISO file doesn't follow the relevant standards. In these cases, PyCdlib will usually throw a `PyCdlibInvalidISO` exception (though it can also throw a `PyCdlibInternalError` in some circumstances).  If this happens, the absolute best thing to do is to open up a new [issue](https://github.com/clalancette/pycdlib/issues), putting a pointer to the problematic ISO in the issue.  If the ISO file cannot be shared, then a new issue should be created anyway, with the relevant backtrace from PyCdlib in it.  From there, additional information can sometimes help to identify the root cause of the issue.
