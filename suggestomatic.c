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

#define NUM_PROCESSES 8

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
    double intersection_percent) {
  fprintf(fout, "%d,%d,%f\n", set_id_a, set_id_b, intersection_percent);
  fflush(fout);
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
    "pid", "id a", "length", "good matches", "time elapsed (s)"
  );
}

void similarity_for_set(
    unsigned int set_index,
    FILE* fout,
    float good_threshold,
    unsigned int* set_ids,
    unsigned int set_id_count,
    unsigned int* indexptr,
    unsigned int* arraysptr,
    struct fileinfo arrays) {

  clock_t started_at = clock();
  unsigned int set_id_a = set_ids[set_index],
               set_id_b, set_a_length;
  unsigned int *set_a_start, *set_a_end, *set_b_start, *set_b_end;
  // be super careful to subtract addresses and not sizeof(int) quantities
  set_a_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_a]);
  if (set_index + 1 == set_id_count) {
    set_a_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
  } else {
	  set_a_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[set_index+1]]);
  }
  set_a_length = (unsigned int)((char*)set_a_end - (char*)set_a_start);

  if (set_a_start == set_a_end) { return; }

  // goodmatches is a basic heuristic for preventing any set_a's iteration
  // from taking too long. Once sampling is effective, this can be removed
  unsigned short int goodmatches = 0;
  for (int b = set_index + 1; b < set_id_count; b++) {
    // We don't compare sets to themselves.
    if (set_index == b) { continue; }

    set_id_b = set_ids[b];
    set_b_start = (unsigned int*)((char*)arraysptr + indexptr[set_id_b]);
    if (set_index + 1 == set_id_count) {
      set_b_end = (unsigned int*)((char*)arraysptr + arrays.filesize);
    } else {
      set_b_end = (unsigned int*)((char*)arraysptr + indexptr[set_ids[b+1]]);
    }

    unsigned int intersection_count = set_intersection(
      set_a_start, set_a_end, set_b_start, set_b_end
    );

    // Calculate the percentage of set_a that intersects with set_b.
    double intersection_percent = ((double) intersection_count)/set_a_length;
    // record "good" matches
    if (intersection_percent >= good_threshold) {
      write_result(fout, set_id_a, set_id_b, intersection_percent);
      ++goodmatches;
      // early out when we have "enough" good matches
      if (goodmatches >= 100) { break; }
    }
  }
  printf(
    "%9u %9u %9u %20d %20.4f \n",
    (unsigned int)getpid(),
    set_id_a, set_a_length,
    goodmatches,
    ((float)clock() - started_at) / CLOCKS_PER_SEC
  );
}

int
main(int argc, char *argv[]) {
  if (test_set_intersection() != 0) {
    return EXIT_FAILURE;
  }
  printf("Smoke tests pass, starting engine\n");

  // set up command line params
  unsigned short arg = 1;
  char *set_ids_filename = argv[arg++],
       *set_index_filename = argv[arg++],
       *set_members_filename = argv[arg++],
       *suggestions_filename = argv[arg++];
  double good_threshold = atof(argv[arg++]);

  // optional param with default
  unsigned int begin_at = 0;
  if (argc > 6) {
    begin_at = atoi(argv[arg]);
    printf("Using optional begin_at parameter: %d \n", begin_at);
  }

  printf("%s\n", argv[0]);
  printf("set_ids_filename: %s \n", set_ids_filename);
  printf("set_index_filename: %s \n", set_index_filename);
  printf("set_members_filename: %s \n", set_members_filename);
  printf("suggestions_filename: %s \n", suggestions_filename);
  printf("good_threshold: %.3f \n", good_threshold);
  printf("begin_at: %d \n", begin_at);


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


  pid_t pids[NUM_PROCESSES];
  int active_pids = NUM_PROCESSES;
  printf("Spinning up %d worker processes...\n", NUM_PROCESSES);
  print_progress_headers();
  for (int i = 0; i < active_pids; i++) {
    pids[i] = fork();
    if (pids[i] < 0) {
      perror(NULL);
      return EXIT_FAILURE;
    } else if (pids[i] == 0) {
      unsigned long intersection_count;
      int started_at = (int)time(NULL);
      char *process_filename = malloc(80);
      sprintf(process_filename, "%s.%u", suggestions_filename, i);
      FILE* fout = fopen(process_filename, "w");
    
      for (int a = begin_at + i; a < set_id_count; a+= NUM_PROCESSES) {
        similarity_for_set(
          a,
          fout,
          good_threshold,
          set_ids,
          set_id_count,
          indexptr,
          arraysptr,
          arrays
        );
        if (0 == a % 10) { print_progress_headers(); }
      }
      fclose(fout);
      printf("Segment starting at %d finished\n", begin_at + i);
      return EXIT_SUCCESS;
    }
  }

  pid_t pid;
  int status;
  while (active_pids > 0) {
    pid = wait(&status);
    printf("Child with PID %ld exited with status 0x%x.\n", (long)pid, status);
    active_pids--;
  }
  printf("\nSuggestomatic success!\n");
  return EXIT_SUCCESS;
}

