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
   <command line invocation from #2>
   
