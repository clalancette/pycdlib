import os
import subprocess

import pytest

pycdlib_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pycdlib_exe = os.path.join(pycdlib_root, 'tools', 'pycdlib-genisoimage')


def find_executable(executable):
    paths = os.environ['PATH'].split(os.pathsep)

    if os.path.isfile(executable):
        return executable
    else:
        for p in paths:
            f = os.path.join(p, executable)
            if os.path.isfile(f):
                return f
    return None


class ProcessException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


def run_process(cmdline):
    if not 'LD_LIBRARY_PATH' in os.environ:
        os.environ['LD_LIBRARY_PATH'] = ''

    process = subprocess.Popen(cmdline,
                               env={
                                   'LD_LIBRARY_PATH': os.environ['LD_LIBRARY_PATH'],
                                   'PATH': os.environ['PATH'],
                                   'PYTHONPATH': pycdlib_root,
                               },
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    out, err = process.communicate()

    ret = process.wait()
    if ret != 0:
        raise ProcessException('Process failed: %s\n%s' % (out, err))

    return out, err


@pytest.mark.skipif(find_executable('isosize') is None or
                    find_executable('isovfy') is None,
                    reason='isosize not installed')
def test_pycdlib_genisoimage_nofiles(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('nofiles')
    outfile = str(indir) + '.iso'

    def _do_test(binary):
        run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-o',
                     str(outfile), str(indir)])
        run_process(['isovfy', str(outfile)])
        out, err = run_process(['isosize', str(outfile)])
        size = int(out.strip())
        assert(size == 49152)

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isosize') is None or
                    find_executable('isovfy') is None or
                    find_executable('iso-read') is None,
                    reason='isosize not installed')
def test_pycdlib_genisoimage_onedir(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('onedir')
    outfile = str(indir) + '.iso'
    dir1 = indir.mkdir('dir1')
    with open(os.path.join(str(dir1), 'foo'), 'wb') as outfp:
        outfp.write(b'foo\n')

    def _do_test(binary):
        run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-o',
                     str(outfile), str(indir)])
        run_process(['isovfy', str(outfile)])
        out, err = run_process(['isosize', str(outfile)])
        genisoimage_size = int(out.strip())
        assert(genisoimage_size == 53248)
        foocheck = os.path.join(str(tmpdir), 'foocheck')
        out, err = run_process(['iso-read', '-i', str(outfile), '-e', 'dir1/foo', '-o', foocheck])
        with open(foocheck, 'rb') as infp:
            assert(infp.read() == b'foo\n')

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isosize') is None or
                    find_executable('isovfy') is None or
                    find_executable('iso-read') is None,
                    reason='isosize not installed')
def test_pycdlib_genisoimage_onefile(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('onedir')
    outfile = str(indir) + '.iso'
    with open(os.path.join(str(indir), 'foo'), 'wb') as outfp:
        outfp.write(b'foo\n')

    def _do_test(binary):
        run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-o',
                     str(outfile), str(indir)])
        run_process(['isovfy', str(outfile)])
        out, err = run_process(['isosize', str(outfile)])
        genisoimage_size = int(out.strip())
        assert(genisoimage_size == 51200)
        foocheck = os.path.join(str(tmpdir), 'foocheck')
        out, err = run_process(['iso-read', '-i', str(outfile), '-e', 'foo', '-o', foocheck])
        with open(foocheck, 'rb') as infp:
            assert(infp.read() == b'foo\n')

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isosize') is None or
                    find_executable('isovfy') is None or
                    find_executable('iso-read') is None,
                    reason='isosize not installed')
def test_pycdlib_genisoimage_file_cmdline(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('onedir')
    outfile = str(indir) + '.iso'
    foofile = os.path.join(str(indir), 'foo')
    with open(foofile, 'wb') as outfp:
        outfp.write(b'foo\n')

    def _do_test(binary):
        run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-o',
                     str(outfile), foofile])
        run_process(['isovfy', str(outfile)])
        out, err = run_process(['isosize', str(outfile)])
        genisoimage_size = int(out.strip())
        assert(genisoimage_size == 51200)
        foocheck = os.path.join(str(tmpdir), 'foocheck')
        out, err = run_process(['iso-read', '-i', str(outfile), '-e', 'foo', '-o', foocheck])
        with open(foocheck, 'rb') as infp:
            assert(infp.read() == b'foo\n')

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isosize') is None or
                    find_executable('isovfy') is None or
                    find_executable('iso-read') is None,
                    reason='isosize not installed')
def test_pycdlib_genisoimage_boot_file_cmdline(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('onedir')
    outfile = str(indir) + '.iso'
    bootfile = os.path.join(str(indir), 'boot')
    with open(bootfile, 'wb') as outfp:
        outfp.write(b'boot\n')

    def _do_test(binary):
        run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-b', 'boot',
                     '-c', 'boot.cat', '-no-emul-boot', '-o', str(outfile),
                     bootfile])
        run_process(['isovfy', str(outfile)])
        out, err = run_process(['isosize', str(outfile)])
        genisoimage_size = int(out.strip())
        assert(genisoimage_size == 55296)
        bootcheck = os.path.join(str(tmpdir), 'bootcheck')
        out, err = run_process(['iso-read', '-i', str(outfile), '-e', 'boot', '-o', bootcheck])
        with open(bootcheck, 'rb') as infp:
            assert(infp.read() == b'boot\n')

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


def test_pycdlib_genisoimage_bootfile_bad(tmpdir):
    # First set things up, and generate the ISO with genisoimage.
    indir = tmpdir.mkdir('onedir')
    outfile = str(indir) + '.iso'

    def _do_test(binary):
        try:
            run_process([binary, '-v', '-iso-level', '1', '-no-pad', '-b', 'boot',
                         '-c', 'boot.cat', '-no-emul-boot', '-o', str(outfile),
                         str(indir)])
        except ProcessException as e:
            err1 = "Uh oh, I cant find the boot image 'boot'" in str(e)
            assert(err1)

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isovfy') is None or
                    find_executable('isoinfo') is None or
                    find_executable('iso-read') is None,
                    reason='ISO verification tools not installed')
@pytest.mark.parametrize('option,bootpath,iso_path,input_name', [
    ('-b', 'boot.img', '/BOOT.IMG;1', 'input'),
    ('-b', 'images/boot.img', '/IMAGES/BOOT.IMG;1', 'input'),
    ('-b', 'images/efi/boot.img', '/IMAGES/EFI/BOOT.IMG;1', 'input'),
    ('-e', 'images/efi/boot.img', '/IMAGES/EFI/BOOT.IMG;1', 'input'),
    ('-b', 'images/boot.img', '/IMAGES/BOOT.IMG;1', 'images'),
])
def test_pycdlib_genisoimage_boot_directory(tmpdir, option, bootpath, iso_path,
                                           input_name):
    indir = tmpdir.mkdir(input_name)
    bootfile = indir.join(bootpath)
    bootfile.dirpath().ensure(dir=True)
    payload = b'boot image' * 512
    bootfile.write_binary(payload)
    decoy = indir.join('unrelated', bootpath)
    decoy.dirpath().ensure(dir=True)
    decoy.write_binary(b'decoy image' * 512)
    outfile = str(tmpdir.join('output.iso'))

    def _do_test(binary):
        run_process([binary, '-iso-level', '1', option, bootpath,
                     '-no-emul-boot', '-o', outfile, str(indir)])
        run_process(['isovfy', outfile])
        bootcheck = str(tmpdir.join('bootcheck'))
        run_process(['iso-read', '-i', outfile, '-e', iso_path[1:],
                     '-o', bootcheck])
        with open(bootcheck, 'rb') as fp:
            assert fp.read() == payload
        out, err = run_process(['isoinfo', '-d', '-i', outfile])
        assert b'Bootid 88 (bootable)' in out
        assert b'Boot media 0 (No Emulation Boot)' in out
        boot_sector = int(next(line for line in out.splitlines()
                               if b'Bootoff ' in line).split()[-1])
        with open(outfile, 'rb') as fp:
            fp.seek(boot_sector * 2048)
            assert fp.read(len(payload)) == payload

    _do_test('genisoimage')
    _do_test(pycdlib_exe)


@pytest.mark.skipif(find_executable('isovfy') is None or
                    find_executable('isoinfo') is None or
                    find_executable('iso-read') is None,
                    reason='ISO verification tools not installed')
@pytest.mark.parametrize('catalogpath,iso_path,input_name', [
    ('boot.cat', '/BOOT.CAT;1', 'input'),
    ('images/boot.cat', '/IMAGES/BOOT.CAT;1', 'input'),
    ('alpha/beta/boot.cat', '/ALPHA/BETA/BOOT.CAT;1', 'input'),
    ('images/boot.cat', '/IMAGES/BOOT.CAT;1', 'images'),
])
def test_pycdlib_genisoimage_catalog_directory(tmpdir, catalogpath, iso_path,
                                              input_name):
    indir = tmpdir.mkdir(input_name)
    indir.join(catalogpath).dirpath().ensure(dir=True)
    if '/' in catalogpath:
        # A preexisting nested catalog must be excluded during traversal.
        indir.join(catalogpath).write_binary(b'stale catalog')
    if catalogpath == 'alpha/beta/boot.cat':
        # This sibling must not consume the nested beta path component.
        indir.mkdir('beta').join('boot.cat').write_binary(b'sibling catalog')
    indir.join('boot.img').write_binary(b'boot image' * 512)
    outfile = str(tmpdir.join('output.iso'))

    def _do_test(binary):
        run_process([binary, '-iso-level', '1', '-b', 'boot.img',
                     '-c', catalogpath, '-no-emul-boot', '-o', outfile,
                     str(indir)])
        run_process(['isovfy', outfile])
        catalogcheck = str(tmpdir.join('catalogcheck'))
        run_process(['iso-read', '-i', outfile, '-e', iso_path[1:],
                     '-o', catalogcheck])
        out, err = run_process(['isoinfo', '-d', '-i', outfile])
        assert b'Key 55 AA' in out
        assert b'Bootid 88 (bootable)' in out
        catalog_sector = int(next(line for line in out.splitlines()
                                  if b'boot catalog is in sector ' in line).split()[-1])
        with open(outfile, 'rb') as fp, open(catalogcheck, 'rb') as catalogfp:
            fp.seek(catalog_sector * 2048)
            assert catalogfp.read() == fp.read(2048)
        if catalogpath == 'alpha/beta/boot.cat':
            siblingcheck = str(tmpdir.join('siblingcheck'))
            run_process(['iso-read', '-i', outfile, '-e', 'BETA/BOOT.CAT;1',
                         '-o', siblingcheck])
            with open(siblingcheck, 'rb') as fp:
                assert fp.read() == b'sibling catalog'

    _do_test('genisoimage')
    _do_test(pycdlib_exe)
