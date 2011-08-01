#include <assert.h>
#include <fcntl.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "vendor/bloom/bloom.h"
#include "vendor/bloom/bloom.c"

unsigned int
set_intersection(
    const unsigned int* set_a,
    const unsigned int* set_a_stop,
    const unsigned int* set_b,
    const unsigned int* set_b_stop) {
  unsigned int a, b;
  unsigned int intersections = 0;
  while (set_a < set_a_stop && set_b < set_b_stop) {
    // caching these derefences makes it much faster
    a = *set_a;
    b = *set_b;
    if (a > b) {
      ++set_b;
    } else if (a == b) {
      ++intersections;
      ++set_a;
      ++set_b;
    } else if (0 == a || 0 == b) {
      return intersections;
    } else {
      ++set_a;
    }
  }
  return intersections;
}

int
test_set_intersection() {
  unsigned int set_a[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
  unsigned int *set_a_end = set_a + sizeof(set_a) / sizeof(set_a[0]);
  unsigned int set_b[] = {5, 6, 7, 8, 9, 10, 11, 12};
  unsigned int *set_b_end = set_b + sizeof(set_b) / sizeof(set_b[0]);
  unsigned int members_in_common = set_intersection(set_a, set_a_end, set_b, set_b_end);
  if (members_in_common != 6) {
    printf("Got %i instead of 6\n", members_in_common);
    return -1;
  }
  return 0;
}

struct null_integer {
  unsigned int id;
  char zero;
};

struct fileinfo {
  int fh;
  size_t filesize;
  void *head;
};

struct fileinfo
load_binary_file(char *filename) {
  struct fileinfo fi;

  if ((fi.fh = open(filename, O_RDONLY)) == -1) {
    fprintf(stderr, "mmap: Error: opening file: %s\n", filename), exit(EXIT_FAILURE);
  }

  fi.filesize = lseek(fi.fh, 0, SEEK_END);
  printf("Loading `%s`, filesize: %zd bytes\n", filename, fi.filesize);
  if ((fi.head = mmap(0, fi.filesize, PROT_READ, MAP_SHARED, fi.fh, 0)) == (void *) -1) {
    fprintf(stderr, "Error mapping input file: %s\n", filename), exit(EXIT_FAILURE);
  }

  return fi;
}

void write_result(
    FILE *fout,
    unsigned int set_id_a,
    unsigned int set_id_b,
    unsigned int score) {
  fprintf(fout, "%d,%d,%d,\n", set_id_a, set_id_b, score);
}

void
first_10_elements(unsigned int *head, char *filename) {
  printf("Printing first 10 elements of %s\n", filename);
  unsigned int *limit = head + 10;
  for (; head < limit; head++) {
    printf("0x%p: %u\n", head, *head);
  }
  printf("\n");
}

void print_progress_headers() {
  printf(
    "%9s %9s %9s %20s %20s \n",
    "id a", "set_id_a", "length", "non-0 matches", "time elapsed (s)"
  );
}

// qsort int comparison function
int int_cmp(const void *a, const void *b)
{
  // input are in (id, score) format, so grab the second word only
  const int *ia = ((const int *)a)+1;
  const int *ib = ((const int *)b)+1;
  return *ib  - *ia;
}

int
main(int argc, char *argv[]) {
  if (test_set_intersection() != 0) {
    return EXIT_FAILURE;
  }
  printf("Smoke tests pass, starting engine\n");

  // set up command line params
  char *set_ids_filename = argv[1],
       *set_index_filename = argv[2],
       *set_members_filename = argv[3],
       *suggestions_filename = argv[4];

  // optional param with default
  unsigned int begin_at = 0;
  if (argc > 5) {
    begin_at = atoi(argv[5]);
  }
  printf("Beginning at set id %d", begin_at);

  struct fileinfo set_ids_file = load_binary_file(set_ids_filename);
  unsigned int *set_ids = (unsigned int*)(set_ids_file.head);
  unsigned int set_id_count = set_ids_file.filesize / sizeof(unsigned int);
  printf("Loaded %d sets\n", set_id_count);

  // visual inspection sanity check
  first_10_elements(set_ids, set_ids_filename);

  // set_index_filename: binary image of set id file offsets in set_members_filename
  //  acts as a set_id -> memory offset lookup table
  //  eg, indexarray[set_id] == arrays + offset_of_set_id_in_image
  struct fileinfo indexarray = load_binary_file(set_index_filename);
  unsigned int *indexptr = (unsigned int*) indexarray.head;

  // visual inspection sanity check
  first_10_elements((unsigned int*)indexarray.head, set_index_filename);
  
  // set_members_filename : binary image of set id membership arrays
  struct fileinfo arrays = load_binary_file(set_members_filename);
  const unsigned int *arraysptr = (unsigned int*) arrays.head;

  // visual inspection sanity check
  first_10_elements((unsigned int*)arrays.head, set_members_filename);

  FILE *fout = fopen(suggestions_filename, "a+");
  unsigned long score;
  int started_at = (int)time(NULL);
  unsigned int set_id_a, set_id_b, set_a_length, set_b_length;
  unsigned int *set_a_start, *set_a_end, *set_b_start, *set_b_end;
  unsigned int *result_set = (unsigned int*)malloc(set_id_count * 2 * sizeof(int));
  if (result_set == NULL) {
    perror(NULL);
    exit(EXIT_FAILURE);
  }

  print_progress_headers();
  struct null_integer bloom_item;
  bloom_item.zero = 0x0;
  for (int a = begin_at; a < set_id_count; a++) {
    // 2 => (set_id_b, score)
    unsigned int* rs_iter = result_set;
    set_id_a = set_ids[a];
    memset(result_set, (char)0x0, set_id_count * 2 * sizeof(int));

    // be super careful to subtract addresses and not sizeof(int) quantities
    set_a_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_a]);
    if (a + 1 == set_id_count) {
      set_a_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
    } else {
	  set_a_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[a+1]]);
    }
    set_a_length = (unsigned int)((char*)set_a_end - (char*)set_a_start) / sizeof(unsigned int);

    // by no means a permanent fix, this means we can at get some
    // recommendations for the smaller sets
    bloom_t *set_a_bloom = NULL;
    if (set_a_length > 40000) {
      printf("Preparing bloom filter... ");
      fflush(0);
      bloom_t *set_a_bloom = bloom_filter_new(2500000);
      unsigned int *set_a_iter = set_a_start;
      unsigned int i = 0;
      while (set_a_iter < set_a_end) {
        bloom_item.id = *set_a_iter++;
        if (bloom_item.id == 0) { continue; }
        bloom_filter_add(set_a_bloom, (char*)&bloom_item);
        i += bloom_filter_contains(set_a_bloom, (char*)&bloom_item);
      }
      printf("Done: %d elements.\n", i);
    }

    if (set_a_start == set_a_end) { continue ; }

    printf("%9u %9u %9u", a, set_id_a, set_a_length);
    fflush(0);
    for (int b = a + 1; b < set_id_count; b++) {
      set_id_b = set_ids[b];
      set_b_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_b]);
      if (a + 1 == set_id_count) {
        set_b_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
      } else {
        set_b_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[b+1]]);
      }
      set_b_length = (unsigned int)((char*)set_b_end - (char*)set_b_start);

      if (set_a_length > 40000) {
        score = 0;
        for (unsigned int *set_b_ele = set_b_start; set_b_ele < set_b_end; set_b_ele++) {
          bloom_item.id = *set_b_ele;
          score += bloom_filter_contains(set_a_bloom, (char*)&bloom_item);
        }
        if (score > 0) { printf("%d\n", score); }
      } else {
        score = set_intersection(
          set_a_start, set_a_end, set_b_start, set_b_end
        );
      }

      if (score > 0) {
        // record the inner id and the score
        memcpy(rs_iter++, (const void*)&set_id_b, sizeof(unsigned int));
        memcpy(rs_iter++, (const void*)&score,    sizeof(unsigned int));
      }
    }
    if (NULL != set_a_bloom) { bloom_filter_free(set_a_bloom); }
    unsigned int bytes_used = (char*)rs_iter - (char*)result_set;
    qsort(result_set, bytes_used , 2 * sizeof(unsigned int), int_cmp);

    // write at least 50 non-zero results, sorted
    for (short int i = 0; i < 100; i += 2) {
      write_result(fout, set_id_a, result_set[i], result_set[i+1]);
      if (i > (bytes_used / sizeof(unsigned int) / 2)) { break; }
    }

    printf(
      " * %20lu %20d \n",
      bytes_used / sizeof(unsigned int),
      (int)time(NULL) - started_at
    );
    if (0 == set_id_a % 10) { print_progress_headers(); }
  }
  free(result_set);
  printf("\nSuggestomatic success!\n");
  return EXIT_SUCCESS;
}

