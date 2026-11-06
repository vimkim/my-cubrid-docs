-- probe_ss1_bulk_update.sql - NOT RUN. Measurement recipe for candidate SS-1 (systems-storage report).
--
-- Question: does a bulk MVCC UPDATE that drops OOS chains pay a commit-time cost that grows with the transaction's
-- log volume (postpone cache overflow -> log_do_postpone forward scan) plus one run-postpone system operation per
-- row, compared with the base snapshot d52b188?
--
-- Environment to record: build (debug or release), db_page_size, log_buffer_size, postpone_cache_size (default 512,
-- hidden), storage device, number of vacuum workers, whether HA is on.
--
-- Run the same script on a head build and on a base build. csql session settings: autocommit OFF.
--
--   csql -u dba -c 'set system parameters "autocommit=off"' ...   (or use `;autocommit off` inside csql)
--
-- Measure per run N in {200, 600, 5000, 50000}:
--   a) wall time of the UPDATE statement and of the COMMIT separately (csql `;time on`, or SET TRACE ON)
--   b) log bytes written by the transaction: difference of the append LSA before the UPDATE and after the COMMIT
--      (cubrid diagdb -d 1 <db> | grep -i "append lsa", or `cubrid statdump` Num_log_pages / log page counters)
--   c) cubrid statdump counters Num_tran_ppcache_hits and Num_tran_ppcache_miss (PSTAT_TRAN_NUM_PPCACHE_HITS/MISS)
--      and Num_tran_topop_ppcache_hits/miss around the COMMIT. Expectation from code: miss = 1 for N > 512 on head;
--      hits only for N <= 512; both zero on base.
--   d) number of RVOOS_UPDATE_DROP_POSTPONE and RVOOS_NOTIFY_VACUUM records: cubrid diagdb -d 4 -l (log dump), count.
--
-- Expected result if SS-1 is real: on head, COMMIT time and log bytes read grow with N once N > 512 and with the
-- size of the OOS payloads logged in the same transaction (the scan walks every log record after the first
-- postpone); on base COMMIT time is flat in N.

DROP TABLE IF EXISTS ss1_t;
CREATE TABLE ss1_t (id INT PRIMARY KEY, a VARCHAR(8000), b VARCHAR(8000));  -- values > the OOS threshold go out of row

-- load committed rows, each with two OOS-backed values (about 6000 bytes each)
INSERT INTO ss1_t
  SELECT t.id, REPEAT('a', 6000), REPEAT('b', 6000)
  FROM (SELECT ROWNUM AS id FROM db_class a1, db_class a2, db_class a3 LIMIT 50000) t;
COMMIT;

-- the transaction under test: every row drops both of its chains
;time on
UPDATE ss1_t SET a = REPEAT('c', 6000), b = REPEAT('d', 6000) WHERE id <= 600;
COMMIT;      -- measure this separately from the UPDATE

UPDATE ss1_t SET a = REPEAT('e', 6000), b = REPEAT('f', 6000);   -- N = 50000
COMMIT;      -- measure this separately from the UPDATE
