tests:
	py.test --verbose tests

test-coverage:
	python-coverage run --source src/pycdlib /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

pylint:
	-pylint --rcfile=pylint.conf src/pycdlib

sdist:
	python setup.py sdist

srpm: sdist
	rpmbuild -bs pycdlib.spec --define "_sourcedir `pwd`/dist"

rpm: sdist
	rpmbuild -ba pycdlib.spec --define "_sourcedir `pwd`/dist"

deb:
	debuild -i -uc -us -b

profile:
	python -m cProfile -o profile /usr/bin/py.test --verbose tests
	python -c "import pstats; p=pstats.Stats('profile');p.strip_dirs();p.sort_stats('time').print_stats(30)"

clean:
	rm -rf htmlcov pycdlib.spec dist MANIFEST .coverage profile
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: tests test-coverage pylint sdist srpm rpm deb profile clean
