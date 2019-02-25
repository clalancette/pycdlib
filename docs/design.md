# Design

## Overview

The aim of PyCdlib is to be a pure Python library that can be used to easily interact with the filesystems that make up various optical disks (collectively known as "ISOs" throughout the rest of this document).  This includes the original ISO9660 standard (also known as Ecma-119), the El Torito booting standard, the Joliet and Rock Ridge extensions, and the UDF filesystem.

## Context

The original motivation for writing the library was to replace the subprocess calls to genisoimage in [Oz](https://github.com/clalancette/oz) with something pure Python.  During initial research, no suitably complete, Python-only ISO manipulation library was found.  It was also discovered that cdrkit (the upstream project that contains genisoimage) is dormant, embroiled in a somewhat bitter fork, contains several serious bugs, and lacks an externally visible test suite.  PyCdlib was created to address the above problems and provide a pure Python library for ISO introspection and manipulation.

## Goals

* A library to interact with optical disk filesystems.
* Support for reading, writing (mastering), and introspecting optical disk filesystems.
* Relatively simple API.
* Python 2 and Python 3 compatibility.
* Expansive test coverage.
* Limited in-place modification of existing ISOs, something that none of the other libraries support.
* Performance approaching that of genisoimage.

## Non-Goals

## Existing solutions

The cdrkit project mentioned in the Context section is the canonical Linux ISO filesystem manipulation program on many Linux distributions.  The upstream project that it was forked from is called [cdrtools](http://cdrtools.sourceforge.net/private/cdrecord.html).  While cdrtools is *not* dormant, it does not offer a Python library, and thus does not meet the original criteria for the project.

## PyCdlib solution

## Alternative solution

## Testing

## Open Questions

---

<div style="width: 100%; display: table;">
  <div style="display: table-row;">
    <div style="width: 33%; display: table-cell; text-align: left;">
      <a href="example-reading-file-in-chunks.html"><-- Example: Reading a large file in chunks</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: center;">
      <a href="https://clalancette.github.io/pycdlib/">Top</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: right;">
      <a href="tools.html">Tools --></a>
    </div>
</div>
