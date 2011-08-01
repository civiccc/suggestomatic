CC=gcc
CFLAGS=-Wall -std=c99 -ggdb -O3

suggestomatic: suggestomatic.o
clean:
	rm suggestomatic
	rm suggestomatic.o
