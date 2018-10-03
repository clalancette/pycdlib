# Testing
PyCdlib has an extensive test suite of hundreds of [black box](https://en.wikipedia.org/wiki/Black-box\_testing) tests that get run on each release.  There are three types of tests that PyCdlib currently runs:
- In _parsing_ tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib [open](pycdlib-api.html#PyCdlib-open) method is used to open up the resulting file and check various aspects of the file.  This ensures that PyCdlib can successfully open up existing ISOs.
- In _new_ tests, a new ISO is created using the PyCdlib [new](pycdlib-api.html#PyCdlib-new) method, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.
- In _hybrid_ tests, specific sequences of files and directories are created, and then an ISO is generated using genisoimage from [cdrkit](https://launchpad.net/cdrkit).  Then the PyCdlib [open](pycdlib-api.html#PyCdlib-open) method is used to open up the resulting file, and the ISO is manipulated in specific ways.  Various aspects of these newly created files are compared against known examples to ensure that things were created as they should be.

PyCdlib currently has 88% code coverage from the tests, and anytime a new bug is found, a test is written to ensure that the bug can't happen again.

---

<div style="width: 100%; display: table;">
  <div style="display: table-row;">
    <div style="width: 33%; display: table-cell; text-align: left;">
      <a href="tools.html"><-- Tools</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: center;">
      <a href="https://clalancette.github.io/pycdlib/">Top</a>
    </div>
    <div style="width: 33%; display: table-cell; text-align: right;">
      <a href="exceptions.html">Exceptions --></a>
    </div>
</div>
