UPDATE bu_control SET payload = payload + 1 WHERE id = 1;
COMMIT;
ALTER TABLE bu_target ADD ATTRIBUTE after_bu INTEGER;
COMMIT;
SELECT attr_name FROM db_attribute
WHERE class_name = 'bu_target' AND attr_name = 'after_bu';
