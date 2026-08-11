INSERT INTO unique_demo VALUES (7, 'holder-will-rollback');
SELECT SLEEP (5.0);
ROLLBACK;
