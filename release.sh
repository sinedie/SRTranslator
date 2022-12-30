rm -rf ./dist
rm -rf ./build
python setup.py sdist bdist_wheel
python -m twine upload dist/*