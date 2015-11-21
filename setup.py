import distutils.core

VERSION='0.1.0'

distutils.core.setup(name='pyiso',
                     version=VERSION,
                     description='Pure python ISO manipulation library',
                     url='http://github.com/clalancette/pyiso',
                     author='Chris Lalancette',
                     author_email='clalancette@gmail.com',
                     license='LGPLv2',
                     classifiers=['Development Status :: 4 - Beta',
                                  'Intended Audience :: Developers',
                                  'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
                                  'Natural Language :: English',
                                  'Programming Language :: Python :: 2',
                     ],
                     keywords='iso9660 iso ecma119 rockridge joliet eltorito',
                     py_modules=['pyiso'],
                     install_requires=['pysendfile'],
                     package_data={},
                     data_files=[],
)
