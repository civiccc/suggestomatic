#!/usr/bin/python

import argparse
import array
import datetime
import collections
from compat import itertools
import logging
import os.path
import struct
import sys
import time


logging.basicConfig()
log = logging.getLogger('prepare_data')
log.setLevel(logging.INFO)

def log_and_exit(msg, error_code=(-1)):
  log.error(msg)
  sys.exit(error_code)

def parseargs():
  parser = argparse.ArgumentParser(
    description="Prepare Suggestomatic data files from set membership CSV dump")

  timestamp = time.time()
  addarg = parser.add_argument
  addarg('--membership-csv', type=str,
    help='(i) set membership CSV of form (user_id, set_id')
  addarg('--membership-filename', type=str,
    default='%s-membership.bin' % time.time(),
    help='(i) set membership binary image filename')
  addarg('--set-membership-arrays-filename', type=str,
    default='%s-set-members.bin' % time.time(),
    help='(o) Array of member_id ararys filename')
  addarg('--set-members-index-filename', type=str,
    default='%s-set-members-index.bin' % time.time(),
    help='(o) Index array into set members arrays filename')
  addarg('--set-id-filename', type=str,
    default='%s-set-ids.bin' % time.time(),
    help='(i/o) Array of set_ids filename')
  addarg('--small-group-threshold', type=int, default=1,
    help="Drop groups with less than or equal to this many members")

  options = parser.parse_args()
  if not (options.membership_csv or options.membership_filename):
    log_and_exit(
      '--membership_csv or --membership_filename needs to be specified')

  if not options.set_membership_arrays_filename:
    log_and_exit('--set_membership_arrays_filename must be specified')
  elif os.path.exists(options.set_membership_arrays_filename):
    log_and_exit('set_membership_arrays_filename `%s` already exists.' %
      options.set_membership_arrays_filename)
  return options

def membership_csv_to_bin(csv_filename, binary_filename):
  assert csv_filename and os.path.exists(csv_filename)
  assert binary_filename
  log.info('CSV membership filesize: %s bytes' % os.path.getsize(csv_filename))
  group_members = collections.defaultdict(int)
  with open(csv_filename) as csvfile:
    for i, line in enumerate(csvfile):
      user_id, group_id = map(int, line.strip().split(','))
      group_members[group_id] += 1
      if i % 1000000 == 0: log.info("Progress: %d" % i)

  f = lambda id: group_members[id] <= options.small_group_threshold
  group_id_blacklist = set(id for id in group_members if f(id))

  with open(csv_filename) as csvfile:
    with open(binary_filename, 'wb+') as binaryfile:
      for i, line in enumerate(csvfile):
        user_id, group_id = map(int, line.strip().split(','))
        if group_id not in group_id_blacklist:
          binaryfile.write(struct.pack('II', user_id, group_id))
        if i % 1000000 == 0: log.info("Write progress: %d" % i)

def load_membership_file(filename):
  try:
    fh = open(filename, 'r')
    filesize = os.path.getsize(filename)
    log.info('Binary membership input file size: %s bytes' % filesize)
    return fh, filesize
  except (IOError, TypeError):
    log_and_exit(
      'membership_filename `%s` does not exist.' % filename)

# helper function to turn an iterable into a list of tuples
in_pairs = lambda xs: [tuple(xs[i:i+2]) for i in range(0, len(xs), 2)]

def fill_buffer(fin, BUFFERSIZE):
  """Read `INTCOUNT` integers from file handle `fin` and return array of ints""" 
  set_id_array = array.array('I')
  try:
    set_id_array.fromfile(fin, (INTCOUNT))
  except EOFError: pass
  return map(int, set_id_array)

def enumerate_set_ids(fh, progress_func=lambda x: 0):
  """Return list of integers for set_ids from a file handle. This funtion
  resets the file position. Assumes the input is (member_id, set_id) * N in
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
    log.info("%d / %d bytes read, %.2f%% complete" % (
      readbytes, membership_filesize, 100 * readbytes / float(membership_filesize)
    ))

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

def extract_membership(set_id_segment, membership_fh):
  set_membership = dict((set_id, []) for set_id in set_id_segment)
  set_id_segment_set = set(set_id_segment)
  membership_fh.seek(0) # reset file

  # read entire data file until we've hit EOF
  try:
    for readbytes in itertools.count(0, BUFFERSIZE):
      pairs = in_pairs(fill_buffer(membership_fh, BUFFERSIZE))
      for member_id, set_id in pairs:
        if set_id in set_id_segment_set:
          set_membership[set_id].append(member_id)
      progress_func(readbytes, mb=100)
      if len(pairs) != (BUFFERSIZE / SIZEOFINT / 2):
        raise EOFError
  except EOFError:
    pass
  return set_membership

def verify_results(arrays_filename, set_array_offsets):
  """Integrity check: the byte before each offset should be a 0 to indicate the
  end of the previous array"""
  with open(arrays_filename, 'rb') as set_array_bin:
    for set_id, offset in set_array_offsets.iteritems():
      log.debug('%d: %d' % (set_id, offset))
      if offset - SIZEOFINT < 0: continue
      set_array_bin.seek(offset - SIZEOFINT)
      zero_array = array.array('I')
      zero_array.fromfile(set_array_bin, 1)
      assert zero_array[0] == 0

def generate_index(index_filename, set_array_offsets):
  with open(index_filename, 'wb') as fh:
    log.info('Generating index file `%s`.' % index_filename)
    index_list = [
      set_array_offsets.get(set_id, 0)
      for set_id
      in xrange(max(set_array_offsets.keys()))
    ]
    index_array = array.array('I')
    index_array.fromlist(index_list)
    index_array.tofile(fh)
    log.info('Finished generating index file.')

BUFFERSIZE = 1024 * 64
SIZEOFINT = 4
INTCOUNT = BUFFERSIZE / SIZEOFINT
SEGSIZE = 10000

if __name__ == '__main__':
  options = parseargs()

  exists = lambda path: path is not None and os.path.exists(path)
  if exists(options.membership_csv) and not exists(options.membership_filename):
    log.debug('Need to convert input CSV to binary image')
    membership_csv_to_bin(options.membership_csv, options.membership_filename)

  membership_tuple = load_membership_file(options.membership_filename)
  membership_fh, membership_filesize = membership_tuple

  set_ids = load_or_enumerate_set_ids()
  set_array_offsets = dict()

  log.info("Reading in %d integers at a time" % INTCOUNT)
  for set_id_segment in (set_ids[i:i+SEGSIZE] for i in xrange(0, len(set_ids), SEGSIZE)):
    log.info("Starting segment %d" % (int(set_ids.index(set_id_segment[0])) / SEGSIZE))
    set_membership = extract_membership(set_id_segment, membership_fh)

    lens = map(len, set_membership.values())
    log.info('Processed `%d` total set_ids' % sum(lens))
    log.info('The biggest set has `%d` members' % max(lens))

    small_sets = 0
    with open(options.set_membership_arrays_filename, 'ab+') as fout:
      for set_id, member_ids in set_membership.iteritems():
        if len(member_ids) <= 1: # drop one member sets
          small_sets += 1
          continue

        member_ids += [0] # add stop integer

        set_array_offsets[set_id] = file_offset = fout.tell()
        log.debug("Offset %d, set_id %s, about to write %d bytes" % (
          file_offset, set_id, len(member_ids * 4)
        ))
        member_id_array = array.array('I')
        member_id_array.fromlist(member_ids)
        member_id_array.tofile(fout)
        log.debug("Offset %d, set_id %s, %d actual bytes written" % (
          fout.tell(), set_id, fout.tell() - file_offset
        ))
      log.info("%d bytes written to %s" %
        (fout.tell(), options.set_membership_arrays_filename)
      )
    log.info("Skipped %d sets with 1 member" % small_sets)

  verify_results(options.set_membership_arrays_filename, set_array_offsets)
  generate_index(options.set_members_index_filename, set_array_offsets)
  log.info('Finished preparing data for Suggestomatic. To start, run:')
  log.info(' '.join((
    './suggestomatic',
    options.set_id_filename,
    options.set_members_index_filename,
    options.set_membership_arrays_filename,
    '0',
    'suggestions.csv'
  )))


