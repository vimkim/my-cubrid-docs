UPDATE dba.q2_account SET balance = 900 WHERE id = 1;
SELECT SLEEP (20.0);
ROLLBACK;
