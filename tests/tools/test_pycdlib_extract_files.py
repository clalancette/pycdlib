import os
import subprocess
import sys

import pycdlib
import pytest


pycdlib_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pycdlib_exe = os.path.join(pycdlib_root, 'tools', 'pycdlib-extract-files')


def run_process(cmdline):
    env = os.environ.copy()
    env['PYTHONPATH'] = pycdlib_root
    return subprocess.run(cmdline, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def make_rock_ridge_iso(tmpdir, iso_name, rr_name, contents):
    source = tmpdir.join(iso_name + '-source')
    source.write_binary(contents)
    iso_path = tmpdir.join(iso_name + '.iso')
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_file(str(source), '/FILE.;1', rr_name=rr_name)
    iso.write(str(iso_path))
    iso.close()
    return iso_path


def test_pycdlib_extract_files_extracts_normal_file(tmpdir):
    iso_path = make_rock_ridge_iso(tmpdir, 'normal', 'normal-file',
                                   b'normal content\n')
    extract_to = tmpdir.mkdir('extract')

    result = run_process([sys.executable, pycdlib_exe, '-extract-to',
                          str(extract_to), str(iso_path)])

    assert result.returncode == 0
    assert extract_to.join('normal-file').read_binary() == b'normal content\n'


@pytest.mark.parametrize(('malicious_name', 'outside_name'), [
    ('../victim', 'victim'),
    ('../extract-sibling', 'extract-sibling'),
])
def test_pycdlib_extract_files_rejects_rock_ridge_path_traversal(
        tmpdir, malicious_name, outside_name):
    evil_source = tmpdir.join('evil-source')
    evil_source.write_binary(b'unused evil record\n')
    victim_source = tmpdir.join('victim-source')
    victim_source.write_binary(b'attacker controlled\n')

    placeholder = 'a' * len(malicious_name)
    clean_iso = tmpdir.join('clean.iso')
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_file(str(evil_source), '/EVIL.;1', rr_name=placeholder)
    iso.add_file(str(victim_source), '/VICTIM.;1', rr_name=outside_name)
    iso.write(str(clean_iso))
    iso.close()

    image = clean_iso.read_binary()
    placeholder_bytes = placeholder.encode('utf-8')
    assert image.count(placeholder_bytes) == 1
    malicious_iso = tmpdir.join('malicious.iso')
    malicious_iso.write_binary(
        image.replace(placeholder_bytes, malicious_name.encode('utf-8')))

    extract_to = tmpdir.mkdir('extract')
    outside_victim = tmpdir.join(outside_name)
    outside_victim.write_binary(b'original content\n')

    result = run_process([sys.executable, pycdlib_exe, '-extract-to',
                          str(extract_to), str(malicious_iso)])

    assert result.returncode != 0
    assert (b'ISO entry would be extracted outside the target directory'
            in result.stderr)
    assert outside_victim.read_binary() == b'original content\n'


def test_pycdlib_extract_files_rejects_existing_symlink_parent(tmpdir):
    source = tmpdir.join('source')
    source.write_binary(b'attacker controlled\n')
    iso_path = tmpdir.join('symlink-parent.iso')
    iso = pycdlib.PyCdlib()
    iso.new(rock_ridge='1.09')
    iso.add_directory('/LINK', rr_name='link')
    iso.add_file(str(source), '/LINK/VICTIM.;1', rr_name='victim')
    iso.write(str(iso_path))
    iso.close()

    extract_to = tmpdir.mkdir('extract')
    outside = tmpdir.mkdir('outside')
    outside_victim = outside.join('victim')
    outside_victim.write_binary(b'original content\n')
    try:
        os.symlink(str(outside), str(extract_to.join('link')))
    except (NotImplementedError, OSError) as exc:
        pytest.skip('symlinks are unavailable: %s' % (exc))

    result = run_process([sys.executable, pycdlib_exe, '-extract-to',
                          str(extract_to), str(iso_path)])

    assert result.returncode != 0
    assert (b'ISO entry would be extracted outside the target directory'
            in result.stderr)
    assert outside_victim.read_binary() == b'original content\n'
