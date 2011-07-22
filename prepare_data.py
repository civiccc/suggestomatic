#!/usr/bin/python

import array
import argparse
import datetime
from compat import itertools
import logging
import os.path
import sys
import struct


logging.basicConfig()
log = logging.getLogger('prepare_data')
log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)

def log_and_exit(msg, error_code=(-1)):
  log.error(msg)
  sys.exit(error_code)

# infile, outfile, offset, set_id_filename (.txt)
parser = argparse.ArgumentParser(
  description="Prepare Suggestomatic data files from set membership CSV dump")
parser.add_argument('--membership-filename', type=str,
  help='set membership CSV filename')
parser.add_argument('--set-membership-arrays-filename', type=str,
  help='Filename for array of user_id arrays')
parser.add_argument('--member-index-filename', type=str,
  help='Filename for index array into members_array')
parser.add_argument('--set-id-filename', type=str,
  help='Filename for array of set_ids (optional)')

options = parser.parse_args()
log.debug(options)

def load_membership_file(filename):
  try:
    fh = open(filename, 'r')
    filesize = os.path.getsize(filename)
    log.info('CSV membership input file size: %s bytes' % filesize)
    return fh, filesize
  except (IOError, TypeError):
    log_and_exit(
      'membership_filename `%s` does not exist.' % filename)

#TODO move into __main__
membership_fh, membership_filesize = load_membership_file(options.membership_filename)

if not options.set_membership_arrays_filename:
  log_and_exit('--set_memberhsip_arrays_filename must be specified')
elif os.path.exists(options.set_membership_arrays_filename):
  log_and_exit('set_membership_arrays_filename `%s` already exists.' %
    options.set_membership_arrays_filename)
#END#TODO

# helper function to turn an iterable into a list of tuples
in_pairs = lambda xs: [tuple(xs[i:i+2]) for i in range(0, len(xs), 2)]

BUFFERSIZE = 1024 * 64
SIZEOFINT = 4
INTCOUNT = BUFFERSIZE / SIZEOFINT
log.info("Reading in %d integers at a time" % INTCOUNT)

def fill_buffer(fin, BUFFERSIZE):
  """Read `INTCOUNT` integers from file handle `fin` and return array of ints""" 
  set_id_array = array.array('I')
  try:
    set_id_array.fromfile(fin, (INTCOUNT))
  except EOFError: pass
  return map(int, set_id_array)

def enumerate_set_ids(fh, progress_func=lambda x: 0):
  """Return list of integers for set_ids from a file handle. This funtion
  resets the file position. Assumes the input is (user_id, set_id) * N in
  binary.
  """
  fh.seek(0)
  set_ids = set()
  for readbytes in itertools.count(start=0, step=BUFFERSIZE):
    ints = fill_buffer(fh, BUFFERSIZE)
    # grab every other integer, skipping the first one
    new_set_ids = (ints[i+1] for i in xrange(0, len(ints), 2))
    set_ids.update(set(new_set_ids))
    progress_func(readbytes, mb=100)
    if len(ints) != (BUFFERSIZE / SIZEOFINT):
      return list(set_ids)

def progress_func(readbytes, mb=100):
  if readbytes % (BUFFERSIZE * 16 * mb) == 0:
    print "%d / %d bytes read, %.2f%% complete" % (
      readbytes, membership_filesize, 100 * readbytes / float(membership_filesize)
    )

def load_or_enumerate_set_ids():
  # binary array of unsigned integers
  set_ids_array = array.array('I')

  if not options.set_id_filename:
    log_and_exit('Must specify --set-id-filename')
  if not os.path.exists(options.set_id_filename):
    log.info('Enumerating set_ids from file -- this may take a while')
    set_ids = enumerate_set_ids(membership_fh, progress_func)
    with open(options.set_id_filename, 'wb+') as fh:
      set_ids_array.fromlist(set_ids)
      set_ids_array.tofile(fh)
  else:
    log.info('Loading set_ids from `%s`' % options.set_id_filename)
    with open(options.set_id_filename, 'rb') as fh:
      size = os.path.getsize(options.set_id_filename)
      set_ids_array.fromfile(fh, size / SIZEOFINT)
      set_ids = set_ids_array.tolist()
  log.info('%d unique set_ids in file' % len(set_ids))
  return set_ids

set_ids = load_or_enumerate_set_ids()
set_array_offsets = dict()

SEGSIZE = 10000
for set_id_segment in (set_ids[i:i+SEGSIZE] for i in xrange(0, len(set_ids), SEGSIZE)):
  log.info("Starting segment %d" % (int(set_ids.index(set_id_segment[0])) / SEGSIZE))

  # reset data structures
  set_membership = dict((set_id, []) for set_id in set_id_segment)
  set_id_segment_set = set(set_id_segment)
  membership_fh.seek(0) # reset file

  # read entire data file until we're out
  try:
    for readbytes in itertools.count(0, BUFFERSIZE):
      pairs = in_pairs(fill_buffer(membership_fh, BUFFERSIZE))
      for user_id, set_id in pairs:
        if set_id in set_id_segment_set:
          set_membership[set_id].append(user_id)
      progress_func(readbytes, mb=100)
      if len(pairs) != (BUFFERSIZE / SIZEOFINT / 2):
        raise EOFError
  except EOFError: pass

  lens = map(len, set_membership.values())
  log.info('Processed `%d` total set_ids and the biggest has `%d` members' % (
      sum(lens), max(lens)
  ))


  small_sets = 0
  with open(options.set_membership_arrays_filename, 'ab+') as fout:
    for set_id, user_ids in set_membership.iteritems():
      # drop one member sets
      if len(user_ids) <= 1:
        small_sets += 1
        continue

      # add stop integer
      user_ids += [0]

      set_array_offsets[set_id] = file_offset = fout.tell()
      print "Offset %d, set_id %s, about to write %d bytes" % (
        file_offset, set_id, len(user_ids * 4)
      )
      user_id_array = array.array('I')
      user_id_array.fromlist(user_ids)
      user_id_array.tofile(fout)
      print "Offset %d, set_id %s, %d actual bytes written" % (
        fout.tell(), set_id, fout.tell() - file_offset
      )
    print "%d bytes written to %s" % (fout.tell(), options.set_membership_arrays_filename)
  print "Skipped %d sets with 1 member" % small_sets

#sys.exit(0) # SLIDING DEBUG START POINT
# sanity check: does the visual output seem right?
# integrity checks:
#   * the byte before each offset should be 0 to indicate the end of the
#     previous user_id array
#TODO more integrity checks
with open(options.set_membership_arrays_filename, 'rb') as set_array_bin:
  for set_id, offset in set_array_offsets.iteritems():
    print '%d: %d' % (set_id, offset)

    if offset - SIZEOFINT < 0: continue
    set_array_bin.seek(offset - SIZEOFINT)
    zero_array = array.array('I')
    zero_array.fromfile(set_array_bin, 1)
    assert zero_array[0] == 0

max_set_id = max(map(int, set_array_offsets.keys()))
print "max set_id: %d" % max_set_id


with open(options.member_index_filename, 'wb') as indexfile:
  log.info('Generating index file `%s`.' % options.member_index_filename)
  index_list = (
    set_array_offsets.get(set_id, 0)
    for set_id
    in xrange(max(set_array_offsets.keys()))
  )
  index_array = array.array('I')
  index_array.fromlist(index_list)
  index_array.tofile(indexfile)
  log.info('Finished generating index file.')

