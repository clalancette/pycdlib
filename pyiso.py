import struct

# There are a number of specific ways that numerical data is stored in the
# ISO9660/Ecma-119 standard.  In the text these are reference by the section
# number they are stored in.  A brief synopsis:
#
# 7.1.1 - 8-bit number
# 7.2.3 - 16-bit number, stored first as little-endian then as big-endian (4 bytes total)
# 7.3.1 - 32-bit number, stored as little-endian
# 7.3.2 - 32-bit number ,stored as big-endian
# 7.3.3 - 32-bit number, stored first as little-endian then as big-endian (8 bytes total)

class PyIso(object):
    VOLUME_DESCRIPTOR_TYPE_PRIMARY = 1
    def _get_primary_volume_descriptor(self, cdfd):
        """
        Method to extract the primary volume descriptor from a CD.
        """
        # check out the primary volume descriptor to make sure it is sane
        cdfd.seek(16*2048)
        fmt = "=B5sBB32s32sQLLQQQQHHHHHHLLLLLL34s128s128s128s128s37s37s37s17s17s17s17sBB512s653s"
        (desc_type, identifier, version, unused1, system_identifier,
         volume_identifier, unused2, space_size_le, space_size_be, unused3dot1,
         unused3dot2, unused3dot3, unused3dot4, set_size_le, set_size_be,
         seqnum_le, seqnum_be, lb_size_le, lb_size_be, path_table_size_le,
         path_table_size_be, path_table_loc_le, optional_path_table_loc_le,
         path_table_loc_be, optional_path_table_loc_be,
         root_dir_record, vol_set_identifier, pub_identifier,
         preparer_identifier, app_identifier,
         copyright_file_identifier, abstract_file_identifier,
         bibliographic_file_identifier, vol_creation_date, vol_mod_date,
         vol_expiration_date, vol_effective_data, file_structure_version,
         unused4, app_use, unused5) = struct.unpack(fmt, cdfd.read(struct.calcsize(fmt)))

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
        if file_structure_version != 1:
            raise Exception("File structure version expected to be 1")
        if unused4 != 0:
            raise Exception("data in 4th unused field not zero")
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
        print("'%s'" % path_table_loc_le)
        print("'%s'" % optional_path_table_loc_le)
        print("'%s'" % path_table_loc_be)
        print("'%s'" % optional_path_table_loc_be)
        # FIXME: the root directory record needs to be implemented correctly;
        # right now we just have it as a 34-byte string placeholder.
        print("'%s'" % vol_set_identifier)
        print("'%s'" % pub_identifier)
        print("'%s'" % preparer_identifier)
        print("'%s'" % app_identifier)
        print("'%s'" % copyright_file_identifier)
        print("'%s'" % abstract_file_identifier)
        print("'%s'" % bibliographic_file_identifier)
        # FIXME: the vol_creation_date, vol_mod_date, vol_expiration_date,
        # and vol_effective_date need to be implemented; right now we just have
        # them as 17-byte string placeholders.
        print("'%s'" % file_structure_version)
        print("'%s'" % app_use)
        #return self._PrimaryVolumeDescriptor(version, system_identifier,
        #                                     volume_identifier, space_size_le,
        #                                     set_size_le, seqnum_le)

        return "PVD"

    def open(self, filename):
        fd = open(filename, "r")
        pvd = self._get_primary_volume_descriptor(fd)
        fd.close()
