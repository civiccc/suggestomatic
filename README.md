Suggestomatic
========

How to use
--------

1. Your starting point is a CSV dump of (user_id,group_id) tuples.
   If you're using MySQL, you dump a table in the proper format with:
   `mysql -e 'select concat(user_id, \",\", group_id) as r from memberships)'`

2. Data preparation:
   `python ./prepare.py_data --membership-csv=<file you dumped in #1>`
   When this step is done, it will print the command line arguments needed
   to load that data file into Suggestomatic

3. Run Suggestomatic:
   `make suggestomatic`
   `(command line invocation from #2>)`
   (it will look something like `./suggestomatic 1311574636.32-set-ids.bin 1311574636.32-set-members-index.bin 1311574636.32-set-members.bin 0 suggestions.csv`)

How to generate test data
--------

    derwiki@fordfiesta:~/src/suggestomatic/test$ nice ./test.py --only-csv --recommendation-file=test_data --num-groups=1000
    Invalid option --recommendation-file=test_data. Try ./test --help for help.
    derwiki@fordfiesta:~/src/suggestomatic/test$ ls -lh
    total 1.7M
    -rw-r--r-- 1 derwiki derwiki 1.7M 2011-07-25 22:24 test_data
    -rwxr-xr-x 1 derwiki derwiki 5.0K 2011-07-25 22:17 test.py


