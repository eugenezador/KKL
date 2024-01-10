
all: clean build

install:
	src/install.sh

build:
	src/build.sh

clean:
	rm -rf build/
	rm -rf app/
	rm -f QCL.spec
	rm -f src/QCL.spec