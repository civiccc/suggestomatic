import argparse
import array
import bisect
import mmap
import multiprocessing
import os
import pickle
import struct
import sys
import time

def print_first_ten(filename, out_array):
  print "First 10 elements in '%s' array:" % filename,
  print ', '.join(str(element) for element in out_array[:10])

def parseargs():
  parser = argparse.ArgumentParser(
    description="Suggestomatic calculation engine")

  addarg = parser.add_argument
  addarg('--set-index-filename', type=str,
    help='Pickled dictionary of key => (start_offset, end_offset)')
  addarg('--set-members-filename', type=str,
    help='Binary array or arrays of member_id unsigned int_32s')
  addarg('--suggestions-filename', type=str,
    help='Output filename prefix')
  addarg('--timing-filename', type=str,
    default='timing.csv',
    help='Output timing info filename')
  addarg('--begin-at', type=int, default=0)
  return parser.parse_args()

def load_binary_array(filename):
  out_array = array.array('I')
  with open(filename) as fh:
    size = os.path.getsize(filename)
    item_count = size / out_array.itemsize
    out_array.fromfile(fh, item_count)
    print_first_ten(filename, out_array)
  return out_array

# http://docs.python.org/library/bisect.html#searching-sorted-lists
def bisect_index(haystack, needle):
  '''Locate the leftmost value exactly equal to needle'''
  i = bisect.bisect_left(haystack, needle)
  return i != len(haystack) and haystack[i] == needle

def bisect_intersection(list_a, list_b):
  big_set = list_a if len(list_a) > len(list_b) else list_b
  small_set = list_a if len(list_a) <= len(list_b) else list_b
  return sum(1 for number in small_set if bisect_index(big_set, number))

def advancing_intersection(list_a, list_b):
  a_index, b_index = 0, 0
  a_len, b_len = len(list_a), len(list_b)
  intersections = 0
  while a_index < a_len and b_index < b_len:
    a, b = list_a[a_index], list_b[b_index]
    if a > b: b_index += 1
    elif a == b:
      a_index += 1; b_index += 1
      intersections += 1
    else: a_index += 1
  return intersections

def load_set_array(set_members_mmap, start, end):
  set_members_mmap.seek(start)
  s = array.array('I')
  s.fromstring(set_members_mmap.read(end - start))
  return s

def set_score(set_a, set_b):
  start = time.time()
  intersections = bisect_intersection(set_a, set_b)
  bisect_timing = time.time() - start; start = time.time()
  #advancing_intersections = advancing_intersection(set_a, set_b)
  #advanced_timing = time.time() - start
  if False and len(set_b) > 100000:
    print (
      "multiple", bisect_timing / advanced_timing,
      "set size", len(set_b),
    )
  return intersections / float(len(set_a))

def worker_func(set_a_id):
  set_a = load_set_array(set_members_mmap, *set_index[set_a_id])
  set_a_length = len(set_a)
  set_a_scores = []
  start_time = time.time()
  for i, set_b_id in enumerate(set_ids):
    start = time.time()
    timing = {}
    set_b = load_set_array(set_members_mmap, *set_index[set_b_id])
    timing['loading'] = time.time() - start ; start = time.time()
    score = set_score(set_a, set_b)
    timing['scoring'] = time.time() - start ; start = time.time()

    if sum(timing.values()) > 1.0:
      print 'Set b: %s, loading %.3f / scoring: %.3f' % (
        len(set_b), timing['loading'], timing['scoring'])

    if score > 0:
      set_a_scores.append((set_b_id, score))
    if i % 5000 == 0: print 'progress, set id:', set_a_id, i, time.time() - start_time
  sorted_scores = sorted(set_a_scores, key=lambda x: x[1], reverse=True)[:25]
  return [(set_a_id, set_b_id, score) for set_b_id, score in sorted_scores]

options = parseargs()
# load the large members array of arrays
with open(options.set_members_filename, 'rb') as fh:
  set_members_mmap = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
with open(options.set_index_filename, 'rb') as fh:
  set_index = pickle.load(fh)
  set_ids = sorted(set_index.keys())

class Suggestomatic:
  def run(self):
    options = parseargs()
    print options

    with open(options.set_index_filename, 'rb') as fh:
      set_index = pickle.load(fh)
      set_ids = sorted(set_index.keys())
      print_first_ten("set ids", set_ids)

    set_members_array = array.array('I')
    first_ten = set_members_mmap.read(10 * set_members_array.itemsize)
    set_members_array.fromstring(first_ten)
    print_first_ten(options.set_members_filename, set_members_array)

    for scores in multiprocessing.Pool().imap_unordered(
        worker_func, set_ids[options.begin_at:]):
      print "Finished set %d" % (scores[0][0])
      with open('suggestions.csv', 'a+') as fh:
        for score in scores:
          fh.write('%s,%s,%s\n' % score)


if __name__ == '__main__':
  Suggestomatic().run()
