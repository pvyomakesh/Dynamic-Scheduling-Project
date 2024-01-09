.PHONY: clean test

test: project.py test.in
	env python3 project.py test.in > out.txt

clean:
	-rm out.txt
