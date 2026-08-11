UPDATE dba.q2_account SET balance = balance + 1 WHERE id = 1;
COMMIT;
SELECT id, balance FROM dba.q2_account WHERE id = 1;
