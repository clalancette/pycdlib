tests:
	py.test --verbose tests
	py.test-3 --verbose tests

test-coverage:
	python-coverage run --source pycdlib /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

pylint:
	-pylint --rcfile=pylint.conf pycdlib tools/*

flake8:
	-flake8 --ignore=E501,E266 pycdlib tools/*

sdist:
	python setup.py sdist

srpm: sdist
	rpmbuild -bs python-pycdlib.spec --define "_sourcedir `pwd`/dist"

rpm: sdist
	rpmbuild -ba python-pycdlib.spec --define "_sourcedir `pwd`/dist"

deb:
	debuild -i -uc -us -b

profile:
	python -m cProfile -o profile /usr/bin/py.test --verbose tests
	python -c "import pstats; p=pstats.Stats('profile');p.strip_dirs();p.sort_stats('time').print_stats(30)"

genhtmldocs:
	#man2html man/pycdlib-genisoimage.1 | tail -n +2 | sed -e '/Return to Main Contents/d' > docs/pycdlib-genisoimage.html
	#man2html man/pycdlib-explorer.1 | tail -n +2 > docs/pycdlib-explorer.html
	groff -mandoc -Thtml man/pycdlib-explorer.1 > docs/pycdlib-explorer.html
	groff -mandoc -Thtml man/pycdlib-genisoimage.1 > docs/pycdlib-genisoimage.html

clean:
	rm -rf htmlcov python-pycdlib.spec dist MANIFEST .coverage profile build
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: tests test-coverage pylint flake8 sdist srpm rpm deb profile clean
