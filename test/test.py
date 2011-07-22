#!/usr/bin/python

import random
import sys
import os

NUM_USERS  = 100
NUM_GROUPS = 100
NUM_RECOMMENDATIONS = 5
FILL_FACTOR  = 4 # The closer this is to 0, the more dense the testing data will
                 # be (that is, p(data[x][y] == True) will approach 1).

# TEXT will appear bold when printed to the terminal.
def bold_text(text):
  return "\033[1m%s\033[0;0m" % text

# Creates a NUM_USERS by NUM_GROUPS 2d array of booleans. array[x][y] == True
# indicates that user x is a member of group y.
def generate_testing_data():
  user_likes_group = [[False] * NUM_GROUPS for x in range(NUM_USERS)]

  for x in range(NUM_USERS * NUM_GROUPS / FILL_FACTOR):
    user_likes_group[random.randrange(1, NUM_USERS)][random.randrange(1, NUM_USERS)] = True

  return user_likes_group

# Write DATA as CSV to file FILE_NAME. FILE_NAME is guaranteed to not already
# exist by check_file_validity.
def dump_data(data, file_location):
  output = ""

  for x in range(NUM_USERS):
    for y in range(NUM_GROUPS):
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

# Find the top NUM_RECOMMENDATIONS recommendations for each group.
def dump_recommendations(user_likes_group, recommendations_file_location):
  # a_user_likes_both[a][b] is True iff a user likes both group a and group b.
  a_user_likes_both = [[0] * NUM_GROUPS for x in range(NUM_GROUPS)]

  for user_id in range(NUM_USERS):
    for group_id_1 in range(NUM_GROUPS):
      for group_id_2 in range(NUM_GROUPS): # Don't double count.
        if group_id_1 == group_id_2: continue
        if user_likes_group[user_id][group_id_1] and \
           user_likes_group[user_id][group_id_2]:
          a_user_likes_both[group_id_1][group_id_2] += 1
  
  # We make pairs of group_id,
  recommendations = [sorted(enumerate(a_user_likes_both[x]), key=lambda x:-x[1])
                      for x in range(NUM_GROUPS)]

  output = ""
  for group_id in range(NUM_GROUPS):
    output += "For group %d:" % group_id
    output += "".join(["\n\tGroup %d with %d members in common" % (x[0], x[1]) 
        for x in recommendations[group_id][:NUM_RECOMMENDATIONS]])
    output += "\n"

  with open(recommendations_file_location, 'w') as recommendations_file:
    recommendations_file.write(output)

def main():
  global NUM_USERS
  global NUM_GROUPS
  global NUM_RECOMMENDATIONS

  only_csv = False
  data_file_name = "test_data"
  recommendations_file_name = "output"

  if len(sys.argv) > 1:
    if sys.argv[1] == "--help":
      print "%s : ./test.py [--only-csv] [--num-groups=NUM] [--csv-file=CSV_FILE] [--output-file=OUTPUT_FILE]" % (bold_text("Usage"))
      print ""
      print "Will writes a CSV of user_id, group_id pairs to CSV_FILE. Then, " 
      print "writes the top %d recommendations to OUTPUT_FILE." % (NUM_RECOMMENDATIONS)
      print ""
      print bold_text("Command line options:")
      print ""
      print "\t%s" % bold_text("--csv-file")
      print "\t\tOutput file for CSV data. Defaults to %s if not provided." % data_file_name
      print "\t\tWill remove an old csv file if it exists."
      print "\t%s" % bold_text("--recommendation-file")
      print "\t\tOutput file for correct suggestions. Defaults to %s if not provided." % recommendations_file_name
      print "\t\tWill remove an old output file if it exists."
      print "\t%s" % bold_text("--only-csv")
      print "\t\tDon't generate an answer; only generate the CSV data."
      print "\t%s" % bold_text("--num-groups=NUM")
      print "\t\tOverride the default number of groups and users (%d); use NUM instead for both." % NUM_USERS

      exit(0)
    else:
      for arg in sys.argv[1:]:
        if arg.startswith("--only-csv"):
          only_csv = True
        elif arg.startswith("--csv-file="):
          data_file_name = arg[len("--csv-file="):]
        elif arg.startswith("--recommendations-file="):
          recommendations_file_name = arg[len("--recommendations-file="):]
        elif arg.startswith("--num-groups="):
          num = int(arg[len("--num-groups="):])
          NUM_USERS = num
          NUM_GROUPS = num
        else:
          print "Invalid option %s. Try ./test --help for help." % arg

  data_file_location = os.path.join(os.getcwd(), data_file_name)
  if not only_csv: recommendations_file_location = os.path.join(os.getcwd(), recommendations_file_name)

  check_file_validity(data_file_location)
  if not only_csv: check_file_validity(recommendations_file_location)
  data = generate_testing_data()
  dump_data(data, data_file_location)
  if not only_csv: dump_recommendations(data, recommendations_file_location)

main()

