import setuptools
from distutils.command.sdist import sdist as _sdist
import subprocess
import time

VERSION='1.6.0'
RELEASE='1'

class sdist(_sdist):
    ''' custom sdist command, to prep pycdlib.spec file for inclusion '''

    def run(self):
        global VERSION
        global RELEASE

        # Create a development release string for later use
        git_head = subprocess.Popen("git log -1 --pretty=format:%h",
                                    shell=True,
                                    stdout=subprocess.PIPE).communicate()[0].strip()
        date = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        git_release = "%sgit%s" % (date, git_head)

        # Expand macros in pycdlib.spec.in and create pycdlib.spec
        with open('python-pycdlib.spec.in', 'r') as spec_in:
            with open('python-pycdlib.spec', 'w') as spec_out:
                for line in spec_in:
                    if "@VERSION@" in line:
                        line = line.replace("@VERSION@", VERSION)
                    elif "@RELEASE@" in line:
                        # If development release, include date+githash in %{release}
                        if RELEASE.startswith('0'):
                            RELEASE += '.' + git_release
                        line = line.replace("@RELEASE@", RELEASE)
                    spec_out.write(line)

        # Run parent constructor
        _sdist.run(self)

setuptools.setup(name='pycdlib',
                 version=VERSION,
                 description='Pure python ISO manipulation library',
                 url='http://github.com/clalancette/pycdlib',
                 author='Chris Lalancette',
                 author_email='clalancette@gmail.com',
                 license='LGPLv2',
                 classifiers=['Development Status :: 4 - Beta',
                              'Intended Audience :: Developers',
                              'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
                              'Natural Language :: English',
                              'Programming Language :: Python :: 2.7',
                              'Programming Language :: Python :: 3.4',
                 ],
                 keywords='iso9660 iso ecma119 rockridge joliet eltorito udf',
                 packages=['pycdlib'],
                 requires=['pysendfile'],
                 package_data={'': ['examples/*.py']},
                 cmdclass={'sdist': sdist},
                 data_files=[('share/man/man1', ['man/pycdlib-compare.1', 'man/pycdlib-explorer.1', 'man/pycdlib-genisoimage.1'])],
                 scripts=['tools/pycdlib-compare', 'tools/pycdlib-explorer', 'tools/pycdlib-genisoimage'],
)
