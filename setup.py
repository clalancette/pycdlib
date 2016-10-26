import setuptools
from distutils.command.sdist import sdist as _sdist
import subprocess
import time

VERSION='1.0.0'
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
        spec_in = open('pycdlib.spec.in', 'r')
        spec = open('pycdlib.spec', 'w')
        for line in spec_in.xreadlines():
            if "@VERSION@" in line:
                line = line.replace("@VERSION@", VERSION)
            elif "@RELEASE@" in line:
                # If development release, include date+githash in %{release}
                if RELEASE.startswith('0'):
                    RELEASE += '.' + git_release
                line = line.replace("@RELEASE@", RELEASE)
            spec.write(line)
        spec_in.close()
        spec.close()

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
                 keywords='iso9660 iso ecma119 rockridge joliet eltorito',
                 packages=['pycdlib'],
                 requires=['pysendfile'],
                 package_data={'': ['examples/*.py']},
                 cmdclass={'sdist': sdist},
                 data_files=[],
                 scripts=['tools/pycdlib-compare', 'tools/pycdlib-explorer'],
)
