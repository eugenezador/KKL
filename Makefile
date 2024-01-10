
all: clean build

install:
	src/install.sh

build:
	src/build.sh

rebuild:
	rm -rf build/
	rm -rf QCY/
	rm -f QCL.spec
	rm -f src/QCL.spec

clean:
	rm -rf build/
	rm -rf QCY/
	rm -f QCL.spec
	rm -f src/QCL.spec