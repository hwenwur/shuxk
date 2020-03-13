# 本文件仅适用于Linux系统

run:
	@python run.py 学号

dep:
	pip freeze > requirements.txt

pack: clean
	tar -cf dist.tar Makefile requirements.txt run.py courses.txt shuxk/ 说明.txt
	# 文件列表
	@tar -tf dist.tar

cloc:
	cloc ./ --exclude-dir=.vscode,venv


clean:
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -delete
	rm -f run.log result.html
	rm -f dist.tar
