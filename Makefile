clean:
	rm -rf htmlcov python-pycdlib.spec dist MANIFEST .coverage profile build *.lprof .mypy_cache
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

deb:
	debuild -i -uc -us -b

docs:
	groff -mandoc -Thtml man/pycdlib-explorer.1 > docs/pycdlib-explorer.html
	groff -mandoc -Thtml man/pycdlib-extract-files.1 > docs/pycdlib-extract-files.html
	groff -mandoc -Thtml man/pycdlib-genisoimage.1 > docs/pycdlib-genisoimage.html
	python3 custom-pydoc.py > docs/pycdlib-api.html

flake8:
	-python3 -m flake8 --ignore=E501,E266 --max-complexity 80 pycdlib tools/*

mypy:
	python3 -m mypy --ignore-missing-imports -p pycdlib

profile:
	python3 -m cProfile -o profile -m pytest --verbose tests
	python3 -c "import pstats; p=pstats.Stats('profile');p.strip_dirs();p.sort_stats('time').print_stats(30)"

pylint:
	-python3 -m pylint --rcfile=pylint.conf pycdlib tools/*

rpm: sdist
	rpmbuild -ba python-pycdlib.spec --define "_sourcedir `pwd`/dist"

sdist:
	python3 setup.py sdist

slowtests:
	PYCDLIB_TRACK_WRITES=1 python3 -m pytest --basetemp=/var/tmp/pycdlib-tests --runslow --verbose tests

srpm: sdist
	rpmbuild -bs python-pycdlib.spec --define "_sourcedir `pwd`/dist"

test-coverage:
	PYCDLIB_TRACK_WRITES=1 python3 -m coverage run --source pycdlib -m pytest --basetemp=/var/tmp/pycdlib-tests --runslow --verbose tests
	python3 -m coverage html
	xdg-open htmlcov/index.html

tests:
	python3 -m pytest --verbose tests

.PHONY: clean deb docs flake8 lineprof mypy profile pylint rpm sdist slowtests srpm test-coverage tests
