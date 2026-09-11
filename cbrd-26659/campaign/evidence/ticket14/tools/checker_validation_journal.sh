#!/bin/bash
# CBRD-26659 campaign ticket 14 -- checker validation for the second checking mechanism.
#
# The whole-value oracle has its negative control in the testcase repository
# (negative_control/make_negative_control.sh). This is the controlled failure example for
# the other mechanism the case relies on: the acknowledgement parser that turns csql output
# into the affected-row and error counts assert_txn judges a committed transaction by.
# The two shapes that matter are the last four checks: a SQL error and a connection failure
# must both yield affected=0 with errors>=1, because csql has been seen to exit 0 on a
# connection failure, so a parser that read them as success would let a transaction that
# never ran be journalled as acknowledged.
#
# Exit status 0 only when every check holds.
# Unit check of the two parsing helpers the case relies on, against real csql output
# shapes, including the failure shapes they must not read as success.
fails=0
chk() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1 : expected [$2] got [$3]"; fails=$((fails+1)); fi; }

affected_of() { echo "$1" | sed -n 's/^\([0-9][0-9]*\) rows\{0,1\} affected.*/\1/p' | awk '{s+=$1} END {print s+0}'; }
errors_of()   { echo "$1" | grep -c "ERROR"; }

four="1 row affected. (0.003000 sec) 
1 row affected. (0.001000 sec) 
1 row affected. (0.001000 sec) 
1 row affected. (0.001000 sec) 
Execute OK. (0.000000 sec) "
chk "four single-row inserts sum to 4" 4 "$(affected_of "$four")"
chk "  and carry no error"             0 "$(errors_of "$four")"

plural="4 rows affected. (0.002000 sec) "
chk "a plural affected line parses"    4 "$(affected_of "$plural")"

none="
In line 1, column 8,

ERROR: before '  FROM p;'
Attribute \"nosuchcolumn\" was not found.
"
chk "a SQL error yields zero affected" 0 "$(affected_of "$none")"
chk "  and is counted as an error"     1 "$(errors_of "$none")"

conn="
ERROR: Failed to connect to database server, 'x', on the following host(s): localhost
"
chk "a connection failure counts"      1 "$(errors_of "$conn")"
chk "  and affects no rows"            0 "$(affected_of "$conn")"

partial="1 row affected. (0.001000 sec) 

ERROR: Operation would have caused one or more unique constraint violations.
"
chk "a partly failed txn sums rows"    1 "$(affected_of "$partial")"
chk "  and still reports the error"    1 "$(errors_of "$partial")"

empty=""
chk "empty output affects no rows"     0 "$(affected_of "$empty")"
chk "  and reports no error"           0 "$(errors_of "$empty")"

echo "failures=$fails"
[ $fails -eq 0 ]
