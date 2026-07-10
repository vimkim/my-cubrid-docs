-- CBRD-27014 OOS SELECT performance workload for SQL review.
-- Execute the finalized file unchanged on develop and the selected OOS branch.
-- The values below are initial targets. Storage-layout validation in the plan is
-- mandatory before any timing result is accepted.

-- ==========================================================================
-- DDL: Layout A -- about 14.5 KiB, ordinary heap record on develop
-- ==========================================================================

DROP TABLE IF EXISTS perf_heap_14500;

CREATE TABLE perf_heap_14500 (
  id          BIGINT NOT NULL,
  lookup_key  INT NOT NULL,
  hot_col     INT NOT NULL,
  inline_1    BIT VARYING,
  inline_2    BIT VARYING,
  inline_3    BIT VARYING,
  cold_1      BIT VARYING,
  cold_2      BIT VARYING
);

CREATE INDEX ix_heap_14500_lookup ON perf_heap_14500 (lookup_key);

-- DML: 3,900 inline-target bytes + 10,500 demotion-target bytes = 14,400 bytes.
-- 48271 is coprime with 100000, producing a deterministic permutation.
INSERT INTO perf_heap_14500
SELECT LEVEL,
       MOD (CAST (LEVEL - 1 AS BIGINT) * 48271, 100000) + 1,
       MOD (LEVEL, 1000),
       REPEAT (X'11', 1300),
       REPEAT (X'22', 1300),
       REPEAT (X'33', 1300),
       REPEAT (X'AA', 5300),
       REPEAT (X'BB', 5200)
  FROM db_root
CONNECT BY LEVEL <= 100000;

COMMIT;

-- ==========================================================================
-- DDL: Layout B -- about 22 KiB, REC_BIGONE overflow record on develop
-- ==========================================================================

DROP TABLE IF EXISTS perf_overflow_22000;

CREATE TABLE perf_overflow_22000 (
  id          BIGINT NOT NULL,
  lookup_key  INT NOT NULL,
  hot_col     INT NOT NULL,
  inline_1    BIT VARYING,
  inline_2    BIT VARYING,
  inline_3    BIT VARYING,
  cold_1      BIT VARYING,
  cold_2      BIT VARYING,
  cold_3      BIT VARYING
);

CREATE INDEX ix_overflow_22000_lookup ON perf_overflow_22000 (lookup_key);

-- DML: 3,900 inline-target bytes + 18,000 demotion-target bytes = 21,900 bytes.
INSERT INTO perf_overflow_22000
SELECT LEVEL,
       MOD (CAST (LEVEL - 1 AS BIGINT) * 48271, 100000) + 1,
       MOD (LEVEL, 1000),
       REPEAT (X'11', 1300),
       REPEAT (X'22', 1300),
       REPEAT (X'33', 1300),
       REPEAT (X'AA', 7000),
       REPEAT (X'BB', 6000),
       REPEAT (X'CC', 5000)
  FROM db_root
CONNECT BY LEVEL <= 100000;

COMMIT;

-- ==========================================================================
-- Validation DML -- run before measurement, outside the timed interval
-- ==========================================================================

SELECT COUNT (*), COUNT (DISTINCT id), COUNT (DISTINCT lookup_key),
       MIN (id), MAX (id), SUM (id),
       MIN (DISK_SIZE (inline_1)), MAX (DISK_SIZE (inline_1)),
       MIN (DISK_SIZE (cold_1)), MAX (DISK_SIZE (cold_1)),
       MIN (DISK_SIZE (cold_2)), MAX (DISK_SIZE (cold_2))
  FROM perf_heap_14500;

SELECT COUNT (*), COUNT (DISTINCT id), COUNT (DISTINCT lookup_key),
       MIN (id), MAX (id), SUM (id),
       MIN (DISK_SIZE (inline_1)), MAX (DISK_SIZE (inline_1)),
       MIN (DISK_SIZE (cold_1)), MAX (DISK_SIZE (cold_1)),
       MIN (DISK_SIZE (cold_2)), MAX (DISK_SIZE (cold_2)),
       MIN (DISK_SIZE (cold_3)), MAX (DISK_SIZE (cold_3))
  FROM perf_overflow_22000;

-- ==========================================================================
-- Measured SELECT DML: Layout A
-- ==========================================================================

-- Q1A: server-side narrow full scan.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ SUM (id)
  FROM perf_heap_14500;

-- Q2A: all IDs; retain server trace and end-to-end output time separately.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ id
  FROM perf_heap_14500;

-- Q3A template: the runner substitutes a checked-in fixed-seed range list.
-- The sample range returns 100 rows scattered across the heap.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ hot_col
  FROM perf_heap_14500
 WHERE lookup_key BETWEEN 41001 AND 41100;

-- ==========================================================================
-- Measured SELECT DML: Layout B
-- ==========================================================================

-- Q1B: server-side narrow full scan.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ SUM (id)
  FROM perf_overflow_22000;

-- Q2B: all IDs; retain server trace and end-to-end output time separately.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ id
  FROM perf_overflow_22000;

-- Q3B template: use the exact same range list as Q3A.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ hot_col
  FROM perf_overflow_22000
 WHERE lookup_key BETWEEN 41001 AND 41100;

-- ==========================================================================
-- Payload-read extension: generated and measured separately as Q4/Q5
-- ==========================================================================

-- Q4: resolve one known-demoted column. Use content equality rather than
-- DISK_SIZE(), because the latter may be answerable from OOS OID metadata.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ COUNT (*)
  FROM perf_heap_14500
 WHERE cold_1 = CAST (REPEAT (X'AA', 5300) AS BIT VARYING);

SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ COUNT (*)
  FROM perf_overflow_22000
 WHERE cold_1 = CAST (REPEAT (X'AA', 7000) AS BIT VARYING);

-- Q5: access every logical column while returning one checksum. Every payload
-- comparison is true, so the CASE validates all inline and OOS values without
-- transferring 1.4-2.2 GB of row data per measured pass.
SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       SUM (id + lookup_key + hot_col
            + CASE WHEN inline_1 = CAST (REPEAT (X'11', 1300) AS BIT VARYING)
                         AND inline_2 = CAST (REPEAT (X'22', 1300) AS BIT VARYING)
                         AND inline_3 = CAST (REPEAT (X'33', 1300) AS BIT VARYING)
                         AND cold_1 = CAST (REPEAT (X'AA', 5300) AS BIT VARYING)
                         AND cold_2 = CAST (REPEAT (X'BB', 5200) AS BIT VARYING)
                    THEN 1 ELSE 0 END)
  FROM perf_heap_14500;

SELECT /*+ NO_MERGE RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */
       SUM (id + lookup_key + hot_col
            + CASE WHEN inline_1 = CAST (REPEAT (X'11', 1300) AS BIT VARYING)
                         AND inline_2 = CAST (REPEAT (X'22', 1300) AS BIT VARYING)
                         AND inline_3 = CAST (REPEAT (X'33', 1300) AS BIT VARYING)
                         AND cold_1 = CAST (REPEAT (X'AA', 7000) AS BIT VARYING)
                         AND cold_2 = CAST (REPEAT (X'BB', 6000) AS BIT VARYING)
                         AND cold_3 = CAST (REPEAT (X'CC', 5000) AS BIT VARYING)
                    THEN 1 ELSE 0 END)
  FROM perf_overflow_22000;
