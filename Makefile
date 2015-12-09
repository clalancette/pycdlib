tests:
	py.test --verbose tests

test-coverage:
	python-coverage run /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

dist:
	python setup.py sdist

rpm: dist
	rpmbuild -ba pyiso.spec --define "_sourcedir `pwd`/dist"

clean:
	rm -rf htmlcov pyiso.spec dist
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: dist tests
