CC=gcc
CFLAGS=-Wall -std=c99 -ggdb

suggestomatic: suggestomatic.o
clean:
	rm suggestomatic{,.o}
