import argparse
import array
import mmap
import os
import struct
import sys
import time

class Suggestomatic:
  def parseargs(self):
    parser = argparse.ArgumentParser(
      description="Suggestomatic calculation engine")

    addarg = parser.add_argument
    addarg('--set-ids-filename', type=str,
      help='Binary file containing unsigned int_32s of set IDs')
    addarg('--set-index-filename', type=str,
      help='Binary array of unsigned int_32s that indexes set_membership_filename')
    addarg('--set-members-filename', type=str,
      help='Binary array or arrays of member_id unsigned int_32s')
    addarg('--suggestions-filename', type=str,
      help='Output filename prefix')
    addarg('--good-threshold', type=float, default=.05)
    addarg('--begin-at', type=int, default=0)

    options = parser.parse_args()
    #TODO check the options
    return options

  def run(self):
    options = self.parseargs()
    print options

    def print_first_ten(filename, out_array):
      print "First 10 elements in '%s' array:" % filename,
      print ', '.join(str(element) for element in out_array[:10])

    def load_binary_array(filename):
      out_array = array.array('I')
      with open(filename) as fh:
        size = os.path.getsize(filename)
        item_count = size / out_array.itemsize
        out_array.fromfile(fh, item_count)
        print_first_ten(filename, out_array)
      return out_array

    set_ids_array = load_binary_array(options.set_ids_filename)
    set_index_array = load_binary_array(options.set_index_filename)


    # load the large members array of arrays
    with open(options.set_members_filename, 'rb') as fh:
      set_members_mmap = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)

    set_members_array = array.array('I')
    first_ten = set_members_mmap.read(10 * set_members_array.itemsize)
    set_members_array.fromstring(first_ten)
    print_first_ten(options.set_members_filename, set_members_array)

    def load_set_array(set_id):
      start, end = [set_index_array[offset] for offset in (set_id, set_id+1)]
      if end == 0: end = start
      set_members_mmap.seek(start)
      s = array.array('I')
      s.fromstring(set_members_mmap.read(end - start))
      return s

    for set_a_id in set_ids_array:
      set_a = load_set_array(set_a_id)
      set_a_length = float(len(set_a))
      set_a_scores = []
      start_time = time.time()
      for i, set_b_id in enumerate(set_ids_array):
        set_b = load_set_array(set_b_id)
        intersections = bisect_intersection(set_a, set_b)
        score = intersections / set_a_length
        if score > 1: import pdb; pdb.set_trace()
        if score > 0:
          set_a_scores.append((set_b_id, score))
        if i % 1000 == 0: print i, time.time() - start_time
      set_a_scores.sort(key=lambda x: x[1], reverse=True)

# http://docs.python.org/library/bisect.html#searching-sorted-lists
import bisect
def bisect_index(haystack, needle):
    '''Locate the leftmost value exactly equal to needle'''
    i = bisect.bisect_left(haystack, needle)
    return i != len(haystack) and haystack[i] == needle

def bisect_intersection(list_a, list_b):
    big_set = list_a if len(list_a) > len(list_b) else list_b
    small_set = list_a if len(list_a) <= len(list_b) else list_b
    return sum(1 for number in small_set if bisect_index(big_set, number))

if __name__ == '__main__':
  Suggestomatic().run()
