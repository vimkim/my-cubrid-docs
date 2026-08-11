INSERT INTO unique_demo VALUES (7, 'observer-after-wait');
COMMIT;
SELECT id, note FROM unique_demo WHERE id = 7;
