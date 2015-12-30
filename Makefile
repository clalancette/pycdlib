tests:
	py.test --verbose tests

test-coverage:
	python-coverage run /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

pylint:
	-pylint --rcfile=pylint.conf src/pyiso

sdist:
	python setup.py sdist

srpm: sdist
	rpmbuild -bs pyiso.spec --define "_sourcedir `pwd`/dist"

rpm: sdist
	rpmbuild -ba pyiso.spec --define "_sourcedir `pwd`/dist"

deb:
	debuild -i -uc -us -b

clean:
	rm -rf htmlcov pyiso.spec dist MANIFEST .coverage
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: dist tests
