INSERT INTO unique_demo VALUES (8, 'different-key-control');
COMMIT;
DELETE FROM unique_demo WHERE id = 8;
COMMIT;
SELECT COUNT (*) AS key8_count FROM unique_demo WHERE id = 8;
