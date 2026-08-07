-- experiment-1 runner: B-tree insert 워크로드
-- 목적: 단조 증가 key 20,000건 insert로 leaf split과 non-leaf 수정을 유발해
--       page latch 승격(promote) 카운터가 실제로 증가하는지 관측한다.
-- 관측은 실행 전/후의 `cubrid statdump sx_latch_lab` 차이로 한다.

DROP TABLE IF EXISTS sx_promote_t;

CREATE TABLE sx_promote_t (id INT PRIMARY KEY, v VARCHAR(100));

INSERT INTO sx_promote_t
SELECT LEVEL, REPEAT('x', 80) FROM db_root CONNECT BY LEVEL <= 20000;

COMMIT;

SELECT COUNT(*) FROM sx_promote_t;
