pandoc -f markdown -t rst -o README.txt README.md
pandoc -f markdown -t rst -o CHANGES.txt CHANGES.md
python setup.py sdist upload
