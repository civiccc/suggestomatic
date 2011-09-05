"""Generates test input data for Causomatic that tries to mimic the scale of
Causes' datasets for scoring algorithm performance benchmarking. In particular,
this will generate a few *very large* sets, more sets with 10x less users, ad
nauseum"""

import random

if __name__ == '__main__':
  # generate a nice, decreasing distribution
  set_sizes = [((10 ** i),) * (10 - i) for i in range(7, 0, -1)]
  # flatten the list
  set_sizes = [item for sublist in set_sizes for item in sublist]
  print "set sizes: %s" % str(set_sizes)

  id_upper_bound = 2 * 10 ** 7
  print "building user_ids from 0 to %d" % id_upper_bound
  user_ids = range(id_upper_bound)
  print "finished building user_id set, generating memberships"

  with open('sample.data', 'wb+') as fh:
    for set_id, set_size in enumerate(set_sizes, start=1):
      print "Building user ids for set size %d" % set_size
      random.shuffle(user_ids)
      print "Writing results to sample.data..."
      fh.write(
        ''.join('%d,%d\n' % (user_id, set_id)
                           for user_id in user_ids[:set_size]))


