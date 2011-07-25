#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <time.h>

inline unsigned int
set_intersection(
    const unsigned int* set_a,
    unsigned int set_a_size,
    const unsigned int* set_b,
    unsigned int set_b_size) {
  unsigned int a, b;
  const unsigned int *set_a_stop = set_a + set_a_size,
                     *set_b_stop = set_b + set_b_size;
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
    } else {
      ++set_a;
    }
  }
  return intersections;
}

int
test_set_intersection() {
  unsigned int set_a[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0};
  unsigned int set_a_size = sizeof(set_a) / sizeof(set_a[0]);
  unsigned int set_b[] = {5, 6, 7, 8, 9, 10, 11, 12, 0};
  unsigned int set_b_size = sizeof(set_b) / sizeof(set_b[0]);
  unsigned int members_in_common = set_intersection(set_a, set_a_size, set_b, set_b_size);
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
  test_set_intersection();
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
  const unsigned int *indexptr = (unsigned int*) indexarray.head;

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
  unsigned int set_id_a, set_id_b, set_a_length, set_b_length;

  printf("%9s %9s %20s %20s %20s \n", "id a", "id b", "comparisons", "good matches", "time elapsed (s)");
  for (int a = begin_at; a < set_id_count; a++) {
    set_id_a = set_ids[a];
    set_a_length = indexptr[set_ids[a+1]] - indexptr[set_id_a];
   
    if (set_a_length == 0) { continue; }

    // goodmatches is a basic heuristic for preventing any set_a's iteration
    // from taking too long. Once sampling is effective, this can be removed
    unsigned short int goodmatches = 0;
    // starting randomly in tihe set id list will make sure we don't always
    // compare the first elements of the array and possibly never even get to
    // the last elements
    unsigned int random_id_offset = rand() % set_id_count;
    unsigned int set_b_index;
    printf("Set `%d` \t length: %d \t random offset: %d \n", set_id_a, (int)(set_a_length), random_id_offset);
    for (int b = a + 1; b < set_id_count; b++) {
      // wrap around back to the start if the offset is too large
      set_b_index = b;
      set_id_b = set_ids[set_b_index];
      set_b_length = indexptr[set_ids[set_b_index+1]] - indexptr[set_id_b];

      // offsets are in bytes but pointer arithmetic calls for words
      intersection_count = set_intersection(
        arraysptr + indexptr[set_id_a] / sizeof(unsigned int),
        set_a_length,
        arraysptr + indexptr[set_id_b] / sizeof(unsigned int),
        set_b_length
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
    printf("`%d` hit %d matches -- ", set_id_a, goodmatches);
  }
  printf("\nSuggestomatic success!\n");
  return EXIT_SUCCESS;
}

