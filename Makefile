
all: rebuild build

install:
	src/install.sh

build:
	src/build.sh

rebuild:
	rm -rf build/
	rm -f QCL.spec
	rm -f src/QCL.spec

clean:
	rm -rf src/build/
	rm -f QCL.spec
	rm -f src/QCL.spec