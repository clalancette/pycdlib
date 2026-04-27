import re

import pytest


def uses_deprecated(*api_names):
    """Mark a test as a caller of one or more deprecated APIs.

    Silences the DeprecationWarning that those APIs emit, and leaves
    the API name(s) as a literal grep target in the test source.  When
    a deprecated API is finally removed, grep tests/ for its name to
    find every test still on the old code path.
    """
    pattern = '|'.join(re.escape(name) for name in api_names)
    return pytest.mark.filterwarnings(
        rf'ignore:.*({pattern}) is deprecated:DeprecationWarning'
    )


def pytest_addoption(parser):
    parser.addoption('--runslow', action='store_true',
                     default=False, help='run slow tests')

def pytest_collection_modifyitems(config, items):
    if config.getoption('--runslow'):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason='need --runslow option to run')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip_slow)

def pytest_runtest_teardown(item):
    if 'tmpdir' in item.funcargs:
        tmpdir = item.funcargs['tmpdir']
        if tmpdir.check():
            tmpdir.remove()
