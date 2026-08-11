SELECT 'first' AS phase, balance FROM dba.q3_account WHERE id = 1;
SELECT 'second' AS phase, balance FROM dba.q3_account WHERE id = 1 FOR UPDATE;
UPDATE dba.q3_account SET balance = balance + 1 WHERE id = 1;
COMMIT;
SELECT 'third' AS phase, balance FROM dba.q3_account WHERE id = 1;
