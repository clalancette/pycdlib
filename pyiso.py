import struct

class PyIso(object):
    def _get_primary_volume_descriptor(self, cdfd):
        """
        Method to extract the primary volume descriptor from a CD.
        """
        # check out the primary volume descriptor to make sure it is sane
        cdfd.seek(16*2048)
        fmt = "=B5sBB32s32sQLL32sHHHH"
        (desc_type, identifier, version, unused1, system_identifier, volume_identifier, unused2, space_size_le, space_size_be, unused3, set_size_le, set_size_be, seqnum_le, seqnum_be) = struct.unpack(fmt, cdfd.read(struct.calcsize(fmt)))

        if desc_type != 0x1:
            raise Exception("Invalid primary volume descriptor")
        if identifier != "CD001":
            raise Exception("invalid CD isoIdentification")
        if unused1 != 0x0:
            raise Exception("data in unused field")
        if unused2 != 0x0:
            raise Exception("data in 2nd unused field")

        #return self._PrimaryVolumeDescriptor(version, system_identifier,
        #                                     volume_identifier, space_size_le,
        #                                     set_size_le, seqnum_le)

        return "PVD"

    def open(self, filename):
        fd = open(filename, "r")
        pvd = self._get_primary_volume_descriptor(fd)
        fd.close()
