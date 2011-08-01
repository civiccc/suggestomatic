CC=gcc
CFLAGS=-Wall -Wextra -std=c99 -ggdb -O3

suggestomatic: suggestomatic.o #bloom.o
clean:
	rm suggestomatic{,.o}
