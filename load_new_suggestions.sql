LOAD DATA LOCAL INFILE
'suggestions.csv'
INTO TABLE cause_suggestions
FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
(set_id_a, set_id_b, score)
SET id=NULL; -- get the autoincrement right
