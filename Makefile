CC=gcc
CFLAGS=-Wall -std=c99 -ggdb -O3

SHELL := /bin/bash

suggestomatic: suggestomatic.o
clean:
	rm suggestomatic{,.o}
