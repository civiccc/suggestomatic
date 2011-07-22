#!/usr/bin/python
import struct
import sys

# filter_nsized_groups: Given a CSV file of (user, group) pairs, each indicating
# that user USER belongs to group GROUP, do two things:
#
# 1. Remove all groups with a size that fall under a threshold, specified in 
#    arguments passed to the file (defaults to 1).
#
# 2. Writes the resulting pairs to a new binary file, with a name specified in
#    the arguments passed in.

# Parses command line arguments. See --help screen for more information.
def parse_arguments():
  options = {}
  for arg in sys.argv[1:]:
    if arg == "--help":
      print "usage: ./filter_nsized_causes.py --outfile=OUTPUT [--n=N] [--infile=INPUT]"
      print ""
      print "n: threshold of group size to include in output file. (default = 1)"
      print ""
      print "outfile: location of the output of this file."
      print ""
      print "infile: CSV of (user, group) pairs."

      exit(0)
    try:
      key, value = arg.strip().split('=')
      key = key[2:].replace('-', '_')
      options[key] = value
    except ValueError: 
      pass

  return options

class FilterGroups:
  # OPTIONS is a dictionary of settings.
  #
  # options['infile']  : The input file. Required.
  # options['outfile'] : The output file. Required.
  # options['n']       : Group size threshold. Defaults to 1.
  def __init__(self, options):
    self.GROUP_IDX = 1

    self.options = options
    self.threshold = int(self.options.get('n', 1))

    self.fin, self.fout = self.open_files()
    groups_members = self.count_membership(self.fin)

    # Blacklist small groups.
    group_id_blacklist = set([id for id in groups_members if groups_members[id] <= self.threshold])

    self.write_result(group_id_blacklist)

  # Open input and output files.
  def open_files(self):
    fout = open(self.options['outfile'], 'wb+')
    fin = None
    try:
      fin = open(self.options['infile'], 'r')
    except KeyError:
      fin = sys.stdin

    return (fin, fout)

  # Return a dictionary mapping groups to member count.
  def count_membership(self, input_file):
    groups_members = {}
    for i, line in enumerate(input_file):
      try: 
        group_id = int(line[:-1].split(',')[self.GROUP_IDX])
      except IndexError: 
        print "CSV file is improperly formatted on line %d (no comma found)" % i
        continue

      try: 
        groups_members[group_id] += 1
      except KeyError: 
        groups_members[group_id] = 1

      if i % 1000000 == 0: print "Progress: %d" % i

    return groups_members

  # Write out pairs of user_id, group_id to binary file, removing all pairs
  # that have a group_id in BLACKLIST.
  def write_result(self, blacklist):
    self.fin.seek(0)
    for i, line in enumerate(self.fin):
      try: 
        user_id, group_id = map(int, line[:-1].split(','))
      except ValueError: 
        continue

      if group_id not in blacklist:
        self.fout.write(struct.pack('II', user_id, group_id))
      if i % 1000000 == 0: print "Write progress: %d" % i

if __name__ == "__main__":
  f = FilterGroups(parse_arguments())
