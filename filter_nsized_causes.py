#!/usr/bin/python
import struct
import sys

options = dict()
for arg in sys.argv[1:]:
  try:
    key, value = arg.strip().split('=')
    key = key[2:].replace('-', '_')
    options[key] = value
  except ValueError: pass

fout = open(options['outfile'], options.get('write_mode', 'wb+'))
try:
  fin = open(options['infile'], 'r')
except KeyError:
  fin = sys.stdin


CAUSE_IDX = 1
USER_IDX = 0
n_cause_size = int(options.get('n', 1))
print "Using n of %d" % (n_cause_size)

cause_memberships_count = dict()
for i, line in enumerate(fin):
  try: cause_id = int(line[:-1].split(',')[CAUSE_IDX])
  except IndexError: continue

  try: cause_memberships_count[cause_id] += 1
  except KeyError: cause_memberships_count[cause_id] = 1
  if i % 1000000 == 0: print "Progress: %d" % i

print "Finished iterating over file"
big_cause_ids = [
  cause_id
  for cause_id, count
  in cause_memberships_count.iteritems()
  if count > n_cause_size
]

small_cause_ids = [
  cause_id
  for cause_id, count
  in cause_memberships_count.iteritems()
  if count <= n_cause_size
]
cause_id_blacklist = set(small_cause_ids)
print "%d big causes, %d small causes" % (len(big_cause_ids), len(small_cause_ids))

histogram_table = dict()
for cause_id, count in cause_memberships_count.iteritems():
  try: histogram_table[count] += 1
  except KeyError: histogram_table[count] = 1

histogram = sorted(histogram_table.iteritems(), key=lambda x: x[1])
max_count = max(histogram_table.values())
nper_square = max_count / 120 or 1

for cause_size, count in histogram:
  print '%d\t%d\t' % (cause_size, count) + '#' * (count / nper_square)


fin.seek(0)
for i, line in enumerate(fin):
  try: user_id, cause_id = map(int, line[:-1].split(','))
  except ValueError: continue
  if cause_id not in cause_id_blacklist:
    fout.write(struct.pack('II', user_id, cause_id))
  if i % 1000000 == 0: print "Write progress: %d" % i
