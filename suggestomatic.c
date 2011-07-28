#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <time.h>

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
    unsigned int intersection) {
  fprintf(fout, "%d,%d,%d\n", set_id_a, set_id_b, intersection);
}

void
print_progress_headers() {
  printf(
    "%9s %9s %20s %20s %20s \n",
    "id a", "id b",
    "comparisons",
    "good matches",
    "time elapsed (s)"
  );
}

void
print_progress(
    unsigned int set_id_a,
    unsigned int set_id_b,
    unsigned long counter,
    unsigned short int goodmatches,
    int started_at) {
  printf(
  "%9d %9d %20lu %20d %20d\n", 
    set_id_a,
    set_id_b,
    counter,
    goodmatches,
    (int)time(NULL) - started_at
  );
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
  unsigned int good_threshold = atoi(argv[5]);

  // optional param with default
  unsigned int begin_at = 0;
  if (argc > 6) {
    begin_at = atoi(argv[6]);
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
  unsigned long counter = 0, intersection_count;
  int started_at = (int)time(NULL);
  unsigned int set_id_a, set_id_b, set_a_length;
  unsigned int *set_a_start, *set_a_end, *set_b_start, *set_b_end;

  printf("%9s %9s %20s %20s %20s \n", "id a", "id b", "comparisons", "good matches", "time elapsed (s)");
  for (int a = begin_at; a < set_id_count; a++) {
    set_id_a = set_ids[a];

    // be super careful to subtract addresses and not sizeof(int) quantities
    set_a_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_a]);
    if (a + 1 == set_id_count) {
      set_a_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
    } else {
	  set_a_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[a+1]]);
    }
    set_a_length = (unsigned int)((char*)set_a_end - (char*)set_a_start);
   
    if (set_a_start == set_a_end) { continue ; }

    // goodmatches is a basic heuristic for preventing any set_a's iteration
    // from taking too long. Once sampling is effective, this can be removed
    unsigned short int goodmatches = 0;
    printf("Set a: %d \t length: %u \t", set_id_a, set_a_length);
    for (int b = a + 1; b < set_id_count; b++) {
      set_id_b = set_ids[a];
      set_b_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_b]);
      if (a + 1 == set_id_count) {
        set_b_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
      } else {
        set_b_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[b+1]]);
      }

      intersection_count = set_intersection(
        set_a_start, set_a_end, set_b_start, set_b_end
      );

      // record "good" matches
      if (intersection_count > good_threshold) {
        write_result(fout, set_id_a, set_id_b, intersection_count);
        ++goodmatches;
        // early out when we have "enough" good matches
        if (goodmatches >= 100) { break; }
      }

      // visual output for progress
      if (++counter % 100000 == 0) {
        if (counter % 1000000 == 0) { print_progress_headers(); }
        print_progress(set_id_a, set_id_b, counter, goodmatches, started_at);
      }
    }
    printf("%d good matches \n", goodmatches);
  }
  printf("\nSuggestomatic success!\n");
  return EXIT_SUCCESS;
}

