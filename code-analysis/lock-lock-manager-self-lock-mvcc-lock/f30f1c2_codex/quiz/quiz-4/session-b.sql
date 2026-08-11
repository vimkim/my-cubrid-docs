INSERT INTO dba.q4_unique VALUES (101, 'b');
INSERT INTO dba.q4_unique VALUES (100, 'c');
COMMIT;
SELECT id, note_text FROM dba.q4_unique ORDER BY id;
