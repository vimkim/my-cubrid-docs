db=$1
for t in t1 force_inline m pt rp sup sub lk ct1 ct2 ct3 ct4 rp2; do echo "show create table $t;"; done > show_all.sql
csql -S -u dba $db -i show_all.sql 2>&1 | grep "^  'dba\." 
printf ';sc pt__p__p0\n;sc sub\n;sc rp2__p__p1a\n;sc m\n' | csql -S -u dba $db 2>&1 | grep -E "^ +[a-z0-9_]+ +[A-Z]"
