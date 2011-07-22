#!/usr/bin/python

import random
import sys
import os

MAX_USER_ID = 1000
MAX_CAUSE_ID = 1000
FILL_FACTOR = 4 # The closer this is to 0, the more dense the testing data will
                # be (that is, p(data[x][y] == True) will approach 1).

def generate_testing_data():
  # user_likes_cause[a][b] is true iff user a likes cause b.
  user_likes_cause = [[False] * MAX_CAUSE_ID for x in range(MAX_USER_ID)]

  for x in range(MAX_USER_ID * MAX_CAUSE_ID / FILL_FACTOR):
    user_likes_cause[random.randrange(0, MAX_USER_ID)][random.randrange(0, MAX_USER_ID)] = True

  return user_likes_cause

# Write DATA as CSV to file FILE_NAME. FILE_NAME is guaranteed to not already
# exist by check_file_validity.
def dump_data(data, file_location):
  output = ""

  for x in range(MAX_USER_ID):
    for y in range(MAX_CAUSE_ID):
      if data[x][y]:
        output += "%d,%d\n" % (x, y)

  with open(file_location, 'w') as output_file:
    output_file.write(output)

# Ensure that FILE_NAME does not already exist. If so, remove it.
def check_file_validity(file_location):
  if os.path.exists(file_location):
    answer = raw_input("File %s exists. Overwrite? [y/n]" % file_location)
    if answer.upper() != "Y":
      exit(0)

    os.unlink(file_location)

def main():
  file_name = "test_data"

  if len(sys.argv) > 1:
    if sys.argv[1] == "--help":
      print "Suggestomatic testing script."
      print ""
      print "Usage: ./test.py [file]"
      print ""
      print "Will dump a CSV of user_id, cause_id pairs to FILE. FILE defaults"
      print "to %s if not provided." % file_name

      exit(0)
    else:
      file_name = sys.argv[1]

  file_location = os.path.join(os.getcwd(), file_name)

  check_file_validity(file_location)
  data = generate_testing_data()
  dump_data(data, file_location)

main()

