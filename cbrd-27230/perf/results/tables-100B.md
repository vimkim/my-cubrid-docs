## 1. Server instructions (drain included), median of the repeats

reuse/base and reuse/dev divide the reuse build by reuse-base and by develop. The three builds ran at the same time.

### 100 B

| scenario | mode | develop | reuse-base | reuse | reuse/base | reuse/dev | base/dev | spread dev / base / reuse |
|---|---|---:|---:|---:|---:|---:|---:|---|
| S4 적재 INSERT | warm | 11.12G | 11.08G | 11.18G | x1.01 | x1.01 | x1.00 | 0.00 / 0.00 / 0.00 |
| S1 작은 컬럼 scan | io | 157.7M | 158.0M | 156.2M | x0.99 | x0.99 | x1.00 | 0.09 / 0.06 / 0.00 |
| S1 작은 컬럼 scan | warm | 76.2M | 76.3M | 76.0M | x1.00 | x1.00 | x1.00 | 0.02 / 0.01 / 0.01 |
| S2 큰 값 비교 scan | io | 403.8M | 401.9M | 402.7M | x1.00 | x1.00 | x1.00 | 0.01 / 0.01 / 0.01 |
| S2 큰 값 비교 scan | warm | 325.1M | 322.8M | 323.1M | x1.00 | x0.99 | x0.99 | 0.00 / 0.00 / 0.00 |
| S3n PK 조회 5천 회, 작은 컬럼 | io | 2.52G | 2.52G | 2.55G | x1.01 | x1.01 | x1.00 | 0.01 / 0.00 / 0.02 |
| S3n PK 조회 5천 회, 작은 컬럼 | warm | 2.43G | 2.42G | 2.44G | x1.01 | x1.00 | x0.99 | 0.01 / 0.01 / 0.01 |
| S3w PK 조회 5천 회, 큰 컬럼 | io | 2.58G | 2.55G | 2.57G | x1.01 | x1.00 | x0.99 | 0.03 / 0.02 / 0.02 |
| S3w PK 조회 5천 회, 큰 컬럼 | warm | 2.44G | 2.46G | 2.48G | x1.01 | x1.02 | x1.01 | 0.03 / 0.03 / 0.03 |
| S5 작은 컬럼 UPDATE 전체 | io | 8.38G | 8.34G | 8.45G | x1.01 | x1.01 | x1.00 | 0.05 / 0.05 / 0.03 |
| S5 작은 컬럼 UPDATE 전체 | warm | 8.02G | 7.99G | 8.13G | x1.02 | x1.01 | x1.00 | 0.03 / 0.03 / 0.03 |
| S6 큰 컬럼 UPDATE 1/8 | io | 1.20G | 1.21G | 1.22G | x1.01 | x1.01 | x1.01 | 0.00 / 0.00 / 0.01 |
| S6 큰 컬럼 UPDATE 1/8 | warm | 1.14G | 1.14G | 1.14G | x1.00 | x1.00 | x1.01 | 0.02 / 0.04 / 0.01 |
| S7 UPDATE+INSERT+COMMIT 600회 | io | 791.8M | 805.0M | 777.0M | x0.97 | x0.98 | x1.02 | 0.06 / 0.03 / 0.03 |
| S7 UPDATE+INSERT+COMMIT 600회 | warm | 741.6M | 713.5M | 742.0M | x1.04 | x1.00 | x0.96 | 0.05 / 0.06 / 0.07 |
| S8b 큰 컬럼 UPDATE+COMMIT 600회 | io | 486.7M | 485.0M | 487.9M | x1.01 | x1.00 | x1.00 | 0.10 / 0.15 / 0.11 |
| S8b 큰 컬럼 UPDATE+COMMIT 600회 | warm | 466.6M | 470.0M | 468.4M | x1.00 | x1.00 | x1.01 | 0.03 / 0.04 / 0.03 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | io | 495.7M | 494.1M | 479.3M | x0.97 | x0.97 | x1.00 | 0.05 / 0.02 / 0.08 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | warm | 458.4M | 465.6M | 458.0M | x0.98 | x1.00 | x1.02 | 0.03 / 0.03 / 0.05 |
| S9 DELETE 1/8 | io | 1.93G | 1.55G | 1.85G | x1.19 | x0.96 | x0.80 | 0.23 / 0.22 / 0.17 |
| S9 DELETE 1/8 | warm | 1.87G | 2.02G | 2.00G | x0.99 | x1.07 | x1.08 | 0.16 / 0.12 / 0.07 |
| S11 8 client 큰 컬럼 UPDATE | warm | 1.41G | 1.42G | 1.43G | x1.00 | x1.01 | x1.01 | 0.13 / 0.04 / 0.03 |
| S12 8 client 큰 값 INSERT | warm | 1.51G | 1.53G | 1.50G | x0.98 | x1.00 | x1.02 | 0.04 / 0.06 / 0.03 |

## 2. Per-repeat values of S5 and S8s (instructions incl. drain, G)

S5 repeats run on the table in the state the previous repeat left it; rep 0 of warm is the first UPDATE after load.

| size | mode | scenario | build | rep 0 | rep 1 | rep 2 |
|---|---|---|---|---:|---:|---:|
| 100 | warm | S5 | develop | 8.04 | 7.80 | 8.02 |
| 100 | warm | S5 | reuse-base | 7.99 | 7.92 | 8.16 |
| 100 | warm | S5 | reuse | 8.19 | 8.13 | 7.93 |
| 100 | io | S5 | develop | 8.38 | 8.12 | 8.56 |
| 100 | io | S5 | reuse-base | 8.34 | 8.21 | 8.65 |
| 100 | io | S5 | reuse | 8.45 | 8.52 | 8.30 |
| 100 | warm | S8s | develop | 0.46 | 0.46 | 0.47 |
| 100 | warm | S8s | reuse-base | 0.47 | 0.47 | 0.46 |
| 100 | warm | S8s | reuse | 0.46 | 0.47 | 0.45 |
| 100 | io | S8s | develop | 0.48 | 0.50 | 0.51 |
| 100 | io | S8s | reuse-base | 0.50 | 0.49 | 0.49 |
| 100 | io | S8s | reuse | 0.51 | 0.48 | 0.47 |

## 3. S5 detail: other metrics, median

| size | mode | build | instructions | cycles | data page fetches | OS write MiB | OS read MiB | wall s | drain s |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | warm S5 | develop | 8.02G | 5.23G | 1.2M | 154 | 0 | 1.57 | 0.0 |
| 100 | warm S5 | reuse-base | 7.99G | 5.55G | 1.2M | 154 | 0 | 1.67 | 0.0 |
| 100 | warm S5 | reuse | 8.13G | 5.57G | 1.2M | 154 | 0 | 1.62 | 0.0 |
| 100 | io S5 | develop | 8.38G | 6.29G | 1.2M | 155 | 44 | 1.87 | 0.0 |
| 100 | io S5 | reuse-base | 8.34G | 6.00G | 1.2M | 155 | 44 | 1.72 | 0.0 |
| 100 | io S5 | reuse | 8.45G | 6.19G | 1.2M | 155 | 44 | 1.92 | 0.0 |
| 100 | warm S8s | develop | 458.4M | 673.2M | 11.5k | 10 | 0 | 0.37 | 0.0 |
| 100 | warm S8s | reuse-base | 465.6M | 668.5M | 11.5k | 10 | 0 | 0.36 | 0.0 |
| 100 | warm S8s | reuse | 458.0M | 653.1M | 11.5k | 10 | 0 | 0.37 | 0.0 |
| 100 | io S8s | develop | 495.7M | 709.2M | 11.8k | 10 | 2 | 0.47 | 0.0 |
| 100 | io S8s | reuse-base | 494.1M | 735.6M | 12.0k | 10 | 2 | 0.47 | 0.0 |
| 100 | io S8s | reuse | 479.3M | 713.4M | 12.0k | 10 | 2 | 0.47 | 0.0 |

## 4. Heap and OOS file pages after each measured step

Each cell is "OOS user pages / OOS records"; heap pages in brackets. The record before a step is the "before" of that step. develop has no OOS file (heap pages only).

### 100 B

| after | develop heap pages | reuse-base OOS pages / recs [heap] | reuse OOS pages / recs [heap] |
|---|---:|---:|---:|
| after-load | 2,177 | 0 / 0 [2,177] | 0 / 0 [2,177] |
| warm-S5-0 | 2,177 | 0 / 0 [2,177] | 0 / 0 [2,177] |
| warm-S6-0 | 2,177 | 0 / 0 [2,177] | 0 / 0 [2,177] |
| warm-S7-0 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8b-0 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8s-0 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S5-1 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S6-1 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S7-1 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8b-1 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8s-1 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S5-2 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S6-2 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S7-2 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8b-2 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| warm-S8s-2 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| io-S5-0 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| io-S6-0 | 2,181 | 0 / 0 [2,181] | 0 / 0 [2,181] |
| io-S7-0 | 2,189 | 0 / 0 [2,189] | 0 / 0 [2,189] |
| io-S8b-0 | 2,189 | 0 / 0 [2,189] | 0 / 0 [2,189] |
| io-S8s-0 | 2,189 | 0 / 0 [2,189] | 0 / 0 [2,189] |
| io-S5-1 | 2,189 | 0 / 0 [2,189] | 0 / 0 [2,189] |
| io-S6-1 | 2,189 | 0 / 0 [2,189] | 0 / 0 [2,189] |
| io-S7-1 | 2,193 | 0 / 0 [2,193] | 0 / 0 [2,193] |
| io-S8b-1 | 2,193 | 0 / 0 [2,193] | 0 / 0 [2,193] |
| io-S8s-1 | 2,193 | 0 / 0 [2,193] | 0 / 0 [2,193] |
| io-S5-2 | 2,193 | 0 / 0 [2,193] | 0 / 0 [2,193] |
| io-S6-2 | 2,193 | 0 / 0 [2,193] | 0 / 0 [2,193] |
| io-S7-2 | 2,201 | 0 / 0 [2,201] | 0 / 0 [2,201] |
| io-S8b-2 | 2,201 | 0 / 0 [2,201] | 0 / 0 [2,201] |
| io-S8s-2 | 2,201 | 0 / 0 [2,201] | 0 / 0 [2,201] |
| warm-S11-0 | 2,201 | 0 / 0 [2,201] | 0 / 0 [2,201] |
| warm-S12-0 | 2,223 | 0 / 0 [2,222] | 0 / 0 [2,221] |
| warm-S11-1 | 2,223 | 0 / 0 [2,222] | 0 / 0 [2,221] |
| warm-S12-1 | 2,245 | 0 / 0 [2,242] | 0 / 0 [2,241] |
| warm-S11-2 | 2,245 | 0 / 0 [2,242] | 0 / 0 [2,241] |
| warm-S12-2 | 2,266 | 0 / 0 [2,266] | 0 / 0 [2,264] |
| warm-S9-0 | 2,266 | 0 / 0 [2,266] | 0 / 0 [2,264] |
| warm-S9-1 | 2,266 | 0 / 0 [2,266] | 0 / 0 [2,264] |
| warm-S9-2 | 2,266 | 0 / 0 [2,265] | 0 / 0 [2,264] |
| io-S9-0 | 2,266 | 0 / 0 [2,265] | 0 / 0 [2,264] |
| io-S9-1 | 2,266 | 0 / 0 [2,264] | 0 / 0 [2,264] |
| io-S9-2 | 2,266 | 0 / 0 [2,264] | 0 / 0 [2,264] |
| end | 2,266 | 0 / 0 [2,264] | 0 / 0 [2,264] |

## 5. Result checks across builds

- Measured statements with a digest and affected-row count: 60; builds that disagree: 0
- Table checksums (count, sum(k), sum(id), sum(bit_length(big))) and wrong-length counts: 10; builds that disagree: 0
- Content checks (rows holding each written byte pattern): 5 points; builds that disagree or returned nothing: 0
- Rows with a wrong big length: 0
- Builds present per check point: develop, reuse, reuse-base

## 6. Failures

- none

## 7. Load average at each record (1 min)

- develop: min 7.2, median 12.6, max 20.2 (188 records)
- reuse-base: min 7.2, median 12.4, max 20.2 (188 records)
- reuse: min 7.1, median 12.3, max 21.1 (188 records)
