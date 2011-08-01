CC=gcc
CFLAGS=-Wall -std=c99 -ggdb -O3

suggestomatic: suggestomatic.o #bloom.o
clean:
	rm suggestomatic{,.o}
