import struct
import binascii

class PyIso(object):
    VOLUME_DESCRIPTOR_TYPE_PRIMARY = 1
    def _get_primary_volume_descriptor(self, cdfd):
        """
        Method to extract the primary volume descriptor from a CD.
        """
        # check out the primary volume descriptor to make sure it is sane
        cdfd.seek(16*2048)
        fmt = "=B5sBB32s32sQLLQQQQHHHHHHLL"
        (desc_type, identifier, version, unused1, system_identifier, volume_identifier, unused2, space_size_le, space_size_be, unused3dot1, unused3dot2, unused3dot3, unused3dot4, set_size_le, set_size_be, seqnum_le, seqnum_be, lb_size_le, lb_size_be, path_table_size_le, path_table_size_be) = struct.unpack(fmt, cdfd.read(struct.calcsize(fmt)))

        # According to Ecma-119, 8.4.1, the primary volume descriptor type should be 1
        if desc_type != self.VOLUME_DESCRIPTOR_TYPE_PRIMARY:
            raise Exception("Invalid primary volume descriptor")
        # According to Ecma-119, 8.4.2, the identifier should be "CD001"
        if identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        # According to Ecma-119, 8.4.3, the version should be 1
        if version != 1:
            raise Exception("Invalid primary volume descriptor version")
        # According to Ecma-119, 8.4.4, the first unused field should be 0
        if unused1 != 0:
            raise Exception("data in unused field not zero")
        # According to Ecma-119, 8.4.5, the second unused field (after the
        # system identifier and volume identifier) should be 0
        if unused2 != 0:
            raise Exception("data in 2nd unused field not zero")
        # According to Ecma-119, 8.4.9, the third unused field should be all 0
        if unused3dot1 != 0 or unused3dot2 != 0 or unused3dot3 != 0 or unused3dot4 != 0:
            raise Exception("data in 3rd unused field not zero")
        print("'%s'" % desc_type)
        print("'%s'" % identifier)
        print("'%s'" % version)
        print("'%s'" % system_identifier)
        print("'%s'" % volume_identifier)
        print("'%s'" % space_size_le)
        print("'%s'" % space_size_be)
        print("'%s'" % set_size_le)
        print("'%s'" % set_size_be)
        print("'%s'" % seqnum_le)
        print("'%s'" % seqnum_be)
        print("'%s'" % lb_size_le)
        print("'%s'" % lb_size_be)
        print("'%s'" % path_table_size_le)
        print("'%s'" % path_table_size_be)

        #return self._PrimaryVolumeDescriptor(version, system_identifier,
        #                                     volume_identifier, space_size_le,
        #                                     set_size_le, seqnum_le)

        return "PVD"

    def open(self, filename):
        fd = open(filename, "r")
        pvd = self._get_primary_volume_descriptor(fd)
        fd.close()
