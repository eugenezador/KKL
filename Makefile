
all: rebuild build

install:
	src/install.sh

build: rebuild
	src/build.sh

run: build
	cd QCL && ./QCL

rebuild:
	rm -f QCL/QCL
	rm -f QCL.spec
	rm -f src/QCL.spec

clean:
	rm -rf build/
	rm -rf QCL/*
	rm -f QCL.spec
	rm -f src/QCL.spec