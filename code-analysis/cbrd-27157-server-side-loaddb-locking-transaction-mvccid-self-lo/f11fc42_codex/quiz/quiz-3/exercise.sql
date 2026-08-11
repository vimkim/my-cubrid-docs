SELECT 'small' AS case_name,
       value_bits = CAST (REPEAT ('AA', 100) AS BIT VARYING) AS value_matches
FROM small_inline;
SELECT 'large' AS case_name,
       value_bits = CAST (REPEAT ('BB', 5000) AS BIT VARYING) AS value_matches
FROM large_oos;
;oos_stats dba.small_inline
;oos_stats dba.large_oos
