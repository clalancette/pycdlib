# Copyright (C) 2015-2019  Chris Lalancette <clalancette@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""The custom exception class for PyCdlib."""


class PyCdlibException(Exception):
    """The custom Exception class for PyCdlib."""
    def __init__(self, msg):
        # type: (str) -> None
        Exception.__init__(self, msg)


class PyCdlibInternalError(PyCdlibException):
    """The Internal Error Exception class for PyCdlib."""
    def __init__(self, msg):
        # type: (str) -> None
        PyCdlibException.__init__(self, msg)


class PyCdlibInvalidInput(PyCdlibException):
    """The Invalid User Input Exception class for PyCdlib."""
    def __init__(self, msg):
        # type: (str) -> None
        PyCdlibException.__init__(self, msg)


class PyCdlibInvalidISO(PyCdlibException):
    """The Invalid ISO Exception class for PyCdlib."""
    def __init__(self, msg):
        # type: (str) -> None
        PyCdlibException.__init__(self, msg)
