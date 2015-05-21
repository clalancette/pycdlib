import StringIO

def check_pvd(pvd, size, path_table_size, path_table_location_be):
    # genisoimage always produces ISOs with 2048-byte sized logical blocks.
    assert(pvd.log_block_size == 2048)
    # The little endian version of the path table should always start at
    # extent 19.
    assert(pvd.path_table_location_le == 19)
    # The big endian version of the path table changes depending on how many
    # directories there are on the ISO.
    assert(pvd.path_table_location_be == path_table_location_be)
    # genisoimage only supports setting the sequence number to 1
    assert(pvd.seqnum == 1)
    # The amount of space the ISO takes depends on the files and directories
    # on the ISO.
    assert(pvd.space_size == size)
    # The path table size depends on how many directories there are on the ISO.
    assert(pvd.path_tbl_size == path_table_size)

def check_root_dir_record(root_dir_record, num_children, data_length,
                          extent_location):
    # The root_dir_record directory record length should be exactly 34.
    assert(root_dir_record.dr_len == 34)
    # The root directory should be the, erm, root.
    assert(root_dir_record.is_root == True)
    # The root directory record should also be a directory.
    assert(root_dir_record.isdir == True)
    # The root directory record should have a name of the byte 0.
    assert(root_dir_record.file_ident == "\x00")
    # The length of the root directory record depends on the number of entries
    # there are at the top level.
    assert(root_dir_record.data_length == data_length)
    # The number of children the root directory record has depends on the number
    # of files+directories there are at the top level.
    assert(len(root_dir_record.children) == num_children)
    # Make sure the root directory record starts at the extent we expect.
    assert(root_dir_record.extent_location() == extent_location)

def check_dot_dir_record(dot_record):
    # The file identifier for the "dot" directory entry should be the byte 0.
    assert(dot_record.file_ident == "\x00")
    # The "dot" directory entry should be a directory.
    assert(dot_record.isdir == True)
    # The "dot" directory record length should be exactly 34.
    assert(dot_record.dr_len == 34)
    # The "dot" directory record is not the root.
    assert(dot_record.is_root == False)
    # The "dot" directory record should have no children.
    assert(len(dot_record.children) == 0)

def check_dotdot_dir_record(dotdot_record):
    # The file identifier for the "dotdot" directory entry should be the byte 1.
    assert(dotdot_record.file_ident == "\x01")
    # The "dotdot" directory entry should be a directory.
    assert(dotdot_record.isdir == True)
    # The "dotdot" directory record length should be exactly 34.
    assert(dotdot_record.dr_len == 34)
    # The "dotdot" directory record is not the root.
    assert(dotdot_record.is_root == False)
    # The "dotdot" directory record should have no children.
    assert(len(dotdot_record.children) == 0)

def check_file_contents(iso, path, contents):
    out = StringIO.StringIO()
    iso.get_and_write(path, out)
    assert(out.getvalue() == contents)
