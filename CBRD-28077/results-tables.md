# CBRD-28077 결과 표 (run-20261112-220750)

Ratios are OOS / Sidecar / Inner Table divided by develop (median of repeats). Below 1 is better.

## io: server instructions incl. drain, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S1 narrow scan | 0.98 / 0.99 / 0.98 | 1.02 / 1.00 / 1.01 | 0.07 / 0.04 / 0.03 | 0.02 / 0.01 / 0.01 |
| S2 wide scan | 1.00 / 1.00 / 1.11 | 1.01 / 1.00 / 1.08 | 1.35 / 1.09 / 2.25 | 1.05 / 1.05 / 3.80 |
| S3n PK lookup, small col | 1.00 / 0.93 / 0.97 | 0.95 / 1.02 / 1.01 | 0.98 / 0.93 / 1.23 | 0.61 / 0.64 / 1.62 |
| S3w PK lookup, big col | 1.00 / 0.93 / 0.95 | 0.95 / 1.02 / 1.03 | 1.20 / 0.99 / 1.12 | 0.94 / 0.99 / 1.65 |
| S5 UPDATE small col (all) | 1.01 / 1.03 / 1.02 | 1.06 / 1.00 / 1.01 | 12.81 / 0.18 / 0.42 | 16.26 / 0.07 / 0.66 |
| S6 UPDATE big col (1/4) | 0.97 / 0.96 / 1.01 | 1.04 / 1.00 / 1.02 | 4.96 / 1.35 / 2.02 | 3.37 / 1.23 / 3.02 |
| S7 UPDATE+INSERT+COMMIT loop | 0.94 / 0.96 / 1.01 | 1.16 / 1.07 / 1.00 | 2.19 / 1.26 / 1.16 | 1.86 / 1.07 / 1.54 |
| S8b UPDATE big+COMMIT loop | 0.91 / 0.94 / 0.93 | 1.07 / 1.03 / 1.01 | 1.75 / 0.92 / 1.15 | 1.32 / 0.91 / 1.41 |
| S8s UPDATE small+COMMIT loop | 0.91 / 0.91 / 0.93 | 1.01 / 1.01 / 0.99 | 1.73 / 0.75 / 0.90 | 2.09 / 0.73 / 1.24 |
| S9 DELETE 1/4 | 1.00 / 1.14 / 1.01 | 1.05 / 1.10 / 1.07 | 0.41 / 0.52 / 0.98 | 0.69 / 0.77 / 3.09 |

## io: data page fetches, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S1 narrow scan | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.01 / 0.01 / 0.01 | 0.00 / 0.00 / 0.00 |
| S2 wide scan | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.00 / 1.00 / 5.00 | 1.17 / 1.33 / 4.33 |
| S3n PK lookup, small col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.45 | 0.61 / 0.61 / 2.05 |
| S3w PK lookup, big col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.27 / 1.09 / 1.45 | 1.00 / 1.06 / 2.05 |
| S5 UPDATE small col (all) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.82 / 0.86 / 1.87 | 2.36 / 0.16 / 0.90 |
| S6 UPDATE big col (1/4) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.56 / 1.77 / 7.70 | 2.32 / 0.96 / 6.64 |
| S7 UPDATE+INSERT+COMMIT loop | 1.00 / 1.00 / 1.00 | 0.98 / 0.99 / 0.98 | 2.07 / 2.06 / 2.66 | 2.07 / 1.17 / 5.25 |
| S8b UPDATE big+COMMIT loop | 1.02 / 1.00 / 1.00 | 1.03 / 1.03 / 1.03 | 2.58 / 1.08 / 3.45 | 1.74 / 0.54 / 5.64 |
| S8s UPDATE small+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 2.74 / 1.00 / 1.92 | 1.86 / 0.40 / 1.85 |
| S9 DELETE 1/4 | 1.00 / 1.00 / 0.98 | 1.00 / 1.00 / 1.00 | 0.80 / 0.89 / 2.17 | 0.29 / 0.35 / 2.45 |

## io: wall seconds, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S1 narrow scan | 0.65 / 1.00 / 0.65 | 1.29 / 0.85 / 1.04 | 0.09 / 0.04 / 0.07 | 0.01 / 0.01 / 0.01 |
| S2 wide scan | 1.12 / 1.24 / 1.00 | 1.28 / 0.93 / 1.02 | 2.26 / 1.37 / 1.45 | 0.86 / 0.82 / 1.27 |
| S3n PK lookup, small col | 1.27 / 0.43 / 0.82 | 0.36 / 1.23 / 1.68 | 1.95 / 0.69 / 6.09 | 0.20 / 0.21 / 0.79 |
| S3w PK lookup, big col | 0.94 / 0.34 / 0.52 | 0.32 / 1.00 / 1.45 | 3.21 / 0.33 / 1.45 | 0.66 / 0.62 / 0.78 |
| S5 UPDATE small col (all) | 0.88 / 0.90 / 1.02 | 2.29 / 1.28 / 1.67 | 2.86 / 0.03 / 0.22 | 1.20 / 0.01 / 0.29 |
| S6 UPDATE big col (1/4) | 0.89 / 1.23 / 0.96 | 1.95 / 1.48 / 1.19 | 1.81 / 1.86 / 1.42 | 1.31 / 0.90 / 3.38 |
| S7 UPDATE+INSERT+COMMIT loop | 0.48 / 0.76 / 1.12 | 5.77 / 3.75 / 1.04 | 0.57 / 0.37 / 0.10 | 1.13 / 0.47 / 1.18 |
| S8b UPDATE big+COMMIT loop | 0.43 / 0.68 / 0.42 | 5.22 / 1.51 / 1.11 | 0.77 / 0.36 / 0.11 | 1.33 / 0.24 / 0.47 |
| S8s UPDATE small+COMMIT loop | 0.32 / 0.33 / 0.37 | 1.14 / 1.17 / 0.94 | 0.69 / 0.07 / 0.36 | 0.36 / 0.16 / 0.56 |
| S9 DELETE 1/4 | 0.91 / 0.70 / 1.20 | 0.95 / 1.35 / 1.13 | 0.07 / 0.73 / 0.80 | 0.02 / 0.23 / 5.69 |

## io: OS read bytes, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S1 narrow scan | 1.00 / 1.00 / 1.01 | 1.00 / 1.00 / 1.00 | 0.02 / 0.02 / 0.02 | 0.00 / 0.00 / 0.00 |
| S2 wide scan | 1.00 / 1.00 / 1.01 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.01 | 1.00 / 1.00 / 1.60 |
| S3n PK lookup, small col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.64 / 0.61 / 2.09 | 0.00 / 0.01 / 1.82 |
| S3w PK lookup, big col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.40 / 1.43 / 1.87 | 0.39 / 1.00 / 1.76 |
| S5 UPDATE small col (all) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.70 / 0.01 / 1.03 | 1.65 / 0.00 / 1.69 |
| S6 UPDATE big col (1/4) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.01 | 1.03 / 1.84 / 1.89 | 1.06 / 1.42 / 7.29 |
| S7 UPDATE+INSERT+COMMIT loop | 1.00 / 1.00 / 1.01 | 1.00 / 1.00 / 1.03 | 10.24 / 5.76 / 4.65 | 1.41 / 1.05 / 4.00 |
| S8b UPDATE big+COMMIT loop | 1.04 / 1.04 / 1.04 | 5.45 / 5.17 / 4.98 | 181.86 / 8.94 / 25.36 | 40.99 / 1.61 / 19.44 |
| S8s UPDATE small+COMMIT loop | 1.00 / 1.02 / 1.00 | 1.00 / 1.00 / 1.01 | 246.35 / 0.05 / 4.82 | 43.73 / 0.03 / 1.95 |
| S9 DELETE 1/4 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.02 / 0.29 / 0.39 | 0.01 / 0.08 / 1.43 |

## io: OS write bytes incl. drain, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S1 narrow scan | - / - / - | - / - / - | 0.00 / 0.00 / 0.00 | - / - / - |
| S2 wide scan | - / - / - | - / - / - | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 1.00 |
| S3n PK lookup, small col | - / - / - | - / - / - | 0.00 / 2.00 / 2.00 | 0.00 / 0.00 / 0.00 |
| S3w PK lookup, big col | 0.50 / 0.00 / 1.00 | - / - / - | - / - / - | - / - / - |
| S5 UPDATE small col (all) | 1.01 / 1.00 / 0.98 | 1.02 / 1.02 / 1.00 | 1.06 / 0.01 / 0.01 | 1.78 / 0.00 / 0.00 |
| S6 UPDATE big col (1/4) | 1.00 / 1.00 / 1.00 | 1.03 / 1.00 / 1.00 | 1.30 / 2.60 / 2.85 | 2.64 / 3.07 / 10.28 |
| S7 UPDATE+INSERT+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 2.35 / 5.63 / 4.00 | 1.25 / 1.44 / 3.47 |
| S8b UPDATE big+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.08 / 1.00 / 1.27 | 2.29 / 0.85 / 4.22 |
| S8s UPDATE small+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.07 / 1.00 / 1.00 | 2.62 / 0.83 / 0.83 |
| S9 DELETE 1/4 | 1.02 / 1.01 / 0.98 | 1.00 / 1.02 / 1.02 | 0.22 / 0.44 / 0.63 | 0.85 / 0.86 / 4.43 |

## warm: server instructions incl. drain, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S4 load INSERT | 1.01 / 1.16 / 1.01 | 1.01 / 1.08 / 0.99 | 0.94 / 1.02 / 1.16 | 1.02 / 1.02 / 1.35 |
| S1 narrow scan | 1.01 / 0.99 / 1.00 | 0.99 / 0.99 / 0.99 | 0.30 / 0.12 / 0.08 | 0.17 / 0.08 / 0.07 |
| S2 wide scan | 1.00 / 1.00 / 1.12 | 1.00 / 1.00 / 1.21 | 1.77 / 1.10 / 9.53 | 0.68 / 0.76 / 11.25 |
| S3n PK lookup, small col | 1.00 / 1.02 / 1.00 | 0.98 / 0.99 / 0.99 | 0.98 / 0.98 / 1.06 | 0.94 / 0.93 / 1.68 |
| S3w PK lookup, big col | 0.98 / 1.02 / 0.98 | 0.99 / 1.01 / 1.02 | 1.01 / 0.99 / 1.08 | 1.12 / 0.97 / 1.64 |
| S5 UPDATE small col (all) | 1.02 / 1.01 / 1.01 | 1.03 / 0.98 / 1.06 | 1.82 / 0.41 / 0.76 | 2.05 / 0.13 / 0.86 |
| S6 UPDATE big col (1/4) | 1.05 / 1.06 / 1.03 | 1.00 / 0.97 / 1.00 | 5.59 / 1.32 / 1.98 | 3.28 / 1.20 / 2.05 |
| S7 UPDATE+INSERT+COMMIT loop | 1.12 / 1.06 / 1.11 | 0.95 / 0.98 / 0.96 | 1.82 / 1.31 / 1.23 | 1.59 / 0.98 / 1.24 |
| S8b UPDATE big+COMMIT loop | 0.91 / 0.90 / 0.89 | 1.00 / 1.00 / 1.00 | 1.63 / 1.00 / 1.25 | 1.17 / 0.96 / 1.41 |
| S8s UPDATE small+COMMIT loop | 0.96 / 0.94 / 0.93 | 0.99 / 1.01 / 0.99 | 1.59 / 0.85 / 0.92 | 1.62 / 0.74 / 1.11 |
| S9 DELETE 1/4 | 1.01 / 1.16 / 1.03 | 1.01 / 1.14 / 1.02 | 0.52 / 0.68 / 1.59 | 0.23 / 0.44 / 2.13 |

## warm: data page fetches, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S4 load INSERT | 0.94 / 0.95 / 0.92 | 0.95 / 1.02 / 0.99 | 1.12 / 0.97 / 1.89 | 1.38 / 1.07 / 3.50 |
| S1 narrow scan | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.01 / 0.01 / 0.01 | 0.00 / 0.00 / 0.00 |
| S2 wide scan | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.00 / 1.00 / 5.00 | 1.17 / 1.33 / 4.33 |
| S3n PK lookup, small col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.45 | 0.61 / 0.61 / 2.05 |
| S3w PK lookup, big col | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.27 / 1.09 / 1.45 | 1.00 / 1.06 / 2.05 |
| S5 UPDATE small col (all) | 1.00 / 1.00 / 1.00 | 0.99 / 0.99 / 1.00 | 2.18 / 0.79 / 1.71 | 1.31 / 0.15 / 0.87 |
| S6 UPDATE big col (1/4) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.58 / 2.19 / 7.79 | 2.48 / 1.12 / 6.04 |
| S7 UPDATE+INSERT+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.65 / 2.46 / 2.64 | 1.77 / 1.19 / 5.19 |
| S8b UPDATE big+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 0.99 / 0.99 | 1.75 / 1.07 / 3.76 | 1.34 / 0.52 / 5.99 |
| S8s UPDATE small+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.87 / 1.00 / 2.05 | 1.48 / 0.36 / 1.92 |
| S9 DELETE 1/4 | 1.02 / 1.03 / 1.01 | 1.02 / 1.00 / 1.02 | 1.05 / 0.95 / 2.30 | 0.49 / 0.39 / 2.13 |

## warm: wall seconds, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S4 load INSERT | 1.30 / 1.02 / 1.19 | 0.80 / 0.39 / 0.41 | 3.51 / 1.77 / 1.82 | 0.49 / 0.85 / 0.79 |
| S1 narrow scan | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.18 / 0.18 / 0.18 | 0.15 / 0.15 / 0.15 |
| S2 wide scan | 0.70 / 0.70 / 0.69 | 1.78 / 1.78 / 1.78 | 2.15 / 1.75 / 7.04 | 0.86 / 1.00 / 4.29 |
| S3n PK lookup, small col | 0.96 / 0.96 / 0.93 | 0.87 / 0.91 / 0.91 | 1.00 / 0.95 / 1.05 | 0.98 / 0.87 / 1.30 |
| S3w PK lookup, big col | 0.96 / 0.94 / 0.98 | 1.05 / 1.02 / 1.02 | 0.93 / 0.93 / 1.00 | 1.08 / 1.00 / 1.24 |
| S5 UPDATE small col (all) | 1.17 / 0.99 / 0.95 | 1.01 / 0.98 / 1.09 | 18.15 / 0.28 / 0.63 | 8.39 / 0.13 / 1.00 |
| S6 UPDATE big col (1/4) | 0.89 / 0.75 / 0.71 | 0.94 / 0.92 / 0.96 | 5.91 / 7.40 / 9.54 | 3.21 / 2.45 / 4.20 |
| S7 UPDATE+INSERT+COMMIT loop | 7.00 / 2.36 / 5.40 | 0.35 / 0.44 / 0.45 | 11.68 / 5.67 / 5.75 | 1.13 / 1.53 / 1.13 |
| S8b UPDATE big+COMMIT loop | 0.46 / 0.45 / 0.37 | 0.72 / 0.62 / 0.77 | 24.28 / 5.02 / 1.16 | 1.06 / 1.00 / 1.60 |
| S8s UPDATE small+COMMIT loop | 0.64 / 0.61 / 0.47 | 0.82 / 0.52 / 0.93 | 2.96 / 0.54 / 0.10 | 2.07 / 1.07 / 1.22 |
| S9 DELETE 1/4 | 0.96 / 0.97 / 0.97 | 1.03 / 0.97 / 1.06 | 0.53 / 0.99 / 2.12 | 0.10 / 0.14 / 0.83 |

## warm: OS write bytes incl. drain, ratio to develop

| scenario | 100 B | 2048 B | 8192 B | 65536 B |
|---|---|---|---|---|
| S4 load INSERT | 1.01 / 1.01 / 1.01 | 0.99 / 0.99 / 0.99 | 0.96 / 1.01 / 1.02 | 1.01 / 1.00 / 1.70 |
| S1 narrow scan | - / - / - | - / - / - | - / - / - | - / - / - |
| S2 wide scan | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 0.00 | - / - / - |
| S3n PK lookup, small col | - / - / - | - / - / - | 0.00 / 0.00 / 0.00 | - / - / - |
| S3w PK lookup, big col | - / - / - | 0.00 / 0.00 / 1.00 | - / - / - | 0.00 / 1.00 / 0.00 |
| S5 UPDATE small col (all) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 61.15 / 0.78 / 0.83 | 43.61 / 0.13 / 0.13 |
| S6 UPDATE big col (1/4) | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 3.90 / 37.12 / 39.95 | 3.85 / 34.43 / 73.65 |
| S7 UPDATE+INSERT+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.28 / 1.07 / 1.27 | 0.19 / 0.17 / 0.38 |
| S8b UPDATE big+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.07 / 1.00 / 1.25 | 1.05 / 0.85 / 3.06 |
| S8s UPDATE small+COMMIT loop | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 1.04 / 1.00 / 1.00 | 1.04 / 0.83 / 0.84 |
| S9 DELETE 1/4 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 | 0.20 / 0.25 / 0.94 | 0.14 / 1.04 / 7.00 |

### 100 B, io: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 691.4 M | 680.0 M | 684.6 M | 680.6 M |
| S2 wide scan | 1.92 G | 1.92 G | 1.93 G | 2.13 G |
| S3n PK lookup, small col | 3.01 G | 3.00 G | 2.81 G | 2.92 G |
| S3w PK lookup, big col | 3.06 G | 3.07 G | 2.86 G | 2.91 G |
| S5 UPDATE small col (all) | 29.91 G | 30.34 G | 30.95 G | 30.61 G |
| S6 UPDATE big col (1/4) | 7.95 G | 7.75 G | 7.60 G | 8.01 G |
| S7 UPDATE+INSERT+COMMIT loop | 4.01 G | 3.77 G | 3.86 G | 4.06 G |
| S8b UPDATE big+COMMIT loop | 2.38 G | 2.18 G | 2.25 G | 2.21 G |
| S8s UPDATE small+COMMIT loop | 2.31 G | 2.11 G | 2.11 G | 2.15 G |
| S9 DELETE 1/4 | 18.33 G | 18.30 G | 20.97 G | 18.60 G |

### 100 B, io: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 11.1 k | 11.1 k | 11.1 k | 11.1 k |
| S2 wide scan | 11.1 k | 11.1 k | 11.1 k | 11.1 k |
| S3n PK lookup, small col | 60.1 k | 60.1 k | 60.1 k | 60.1 k |
| S3w PK lookup, big col | 60.1 k | 60.1 k | 60.1 k | 60.1 k |
| S5 UPDATE small col (all) | 4.5 M | 4.5 M | 4.5 M | 4.5 M |
| S6 UPDATE big col (1/4) | 1.1 M | 1.1 M | 1.1 M | 1.1 M |
| S7 UPDATE+INSERT+COMMIT loop | 100.0 k | 99.9 k | 100.0 k | 100.0 k |
| S8b UPDATE big+COMMIT loop | 56.2 k | 57.2 k | 56.3 k | 56.2 k |
| S8s UPDATE small+COMMIT loop | 54.0 k | 54.0 k | 54.0 k | 54.0 k |
| S9 DELETE 1/4 | 2.9 M | 2.9 M | 2.9 M | 2.8 M |

### 100 B, io: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 202 MiB | 202 MiB | 202 MiB | 204 MiB |
| S2 wide scan | 201 MiB | 202 MiB | 202 MiB | 204 MiB |
| S3n PK lookup, small col | 173 MiB | 173 MiB | 173 MiB | 174 MiB |
| S3w PK lookup, big col | 175 MiB | 175 MiB | 175 MiB | 176 MiB |
| S5 UPDATE small col (all) | 204 MiB | 204 MiB | 204 MiB | 204 MiB |
| S6 UPDATE big col (1/4) | 58 MiB | 58 MiB | 58 MiB | 58 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 125 MiB | 125 MiB | 125 MiB | 127 MiB |
| S8b UPDATE big+COMMIT loop | 10 MiB | 11 MiB | 11 MiB | 11 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 205 MiB | 205 MiB | 205 MiB | 205 MiB |

### 100 B, io: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 924 MiB | 932 MiB | 928 MiB | 903 MiB |
| S6 UPDATE big col (1/4) | 144 MiB | 144 MiB | 144 MiB | 144 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 53 MiB | 53 MiB | 53 MiB | 53 MiB |
| S8b UPDATE big+COMMIT loop | 36 MiB | 36 MiB | 36 MiB | 36 MiB |
| S8s UPDATE small+COMMIT loop | 36 MiB | 36 MiB | 36 MiB | 36 MiB |
| S9 DELETE 1/4 | 576 MiB | 585 MiB | 580 MiB | 563 MiB |

### 100 B, io: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 0.57 | 0.37 | 0.57 | 0.36 |
| S2 wide scan | 0.42 | 0.47 | 0.52 | 0.41 |
| S3n PK lookup, small col | 9.88 | 12.54 | 4.27 | 8.13 |
| S3w PK lookup, big col | 13.89 | 12.99 | 4.72 | 7.23 |
| S5 UPDATE small col (all) | 9.58 | 8.48 | 8.58 | 9.73 |
| S6 UPDATE big col (1/4) | 2.37 | 2.12 | 2.92 | 2.27 |
| S7 UPDATE+INSERT+COMMIT loop | 25.66 | 12.44 | 19.50 | 28.87 |
| S8b UPDATE big+COMMIT loop | 17.45 | 7.53 | 11.89 | 7.28 |
| S8s UPDATE small+COMMIT loop | 18.40 | 5.97 | 6.13 | 6.88 |
| S9 DELETE 1/4 | 4.87 | 4.42 | 3.42 | 5.82 |

### 100 B, warm: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 67.92 G | 68.51 G | 78.51 G | 68.61 G |
| S1 narrow scan | 351.6 M | 355.2 M | 348.8 M | 350.6 M |
| S2 wide scan | 1.60 G | 1.59 G | 1.60 G | 1.79 G |
| S3n PK lookup, small col | 2.48 G | 2.49 G | 2.52 G | 2.49 G |
| S3w PK lookup, big col | 2.51 G | 2.47 G | 2.55 G | 2.46 G |
| S5 UPDATE small col (all) | 39.88 G | 40.53 G | 40.46 G | 40.47 G |
| S6 UPDATE big col (1/4) | 10.00 G | 10.48 G | 10.57 G | 10.31 G |
| S7 UPDATE+INSERT+COMMIT loop | 3.42 G | 3.84 G | 3.61 G | 3.78 G |
| S8b UPDATE big+COMMIT loop | 2.66 G | 2.42 G | 2.40 G | 2.36 G |
| S8s UPDATE small+COMMIT loop | 2.55 G | 2.46 G | 2.40 G | 2.37 G |
| S9 DELETE 1/4 | 15.83 G | 16.00 G | 18.33 G | 16.33 G |

### 100 B, warm: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 4.9 M | 4.7 M | 4.7 M | 4.5 M |
| S1 narrow scan | 11.0 k | 11.0 k | 11.0 k | 11.0 k |
| S2 wide scan | 11.0 k | 11.0 k | 11.0 k | 11.0 k |
| S3n PK lookup, small col | 60.1 k | 60.1 k | 60.1 k | 60.1 k |
| S3w PK lookup, big col | 60.1 k | 60.1 k | 60.1 k | 60.1 k |
| S5 UPDATE small col (all) | 6.0 M | 6.0 M | 6.0 M | 6.0 M |
| S6 UPDATE big col (1/4) | 1.5 M | 1.5 M | 1.5 M | 1.5 M |
| S7 UPDATE+INSERT+COMMIT loop | 108.1 k | 107.8 k | 108.0 k | 108.0 k |
| S8b UPDATE big+COMMIT loop | 60.8 k | 60.9 k | 60.9 k | 60.9 k |
| S8s UPDATE small+COMMIT loop | 60.1 k | 60.1 k | 60.1 k | 60.1 k |
| S9 DELETE 1/4 | 3.3 M | 3.4 M | 3.5 M | 3.4 M |

### 100 B, warm: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S6 UPDATE big col (1/4) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8b UPDATE big+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 0 MiB | 0 MiB | 0 MiB | 0 MiB |

### 100 B, warm: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 1,263 MiB | 1,276 MiB | 1,276 MiB | 1,274 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 766 MiB | 766 MiB | 766 MiB | 766 MiB |
| S6 UPDATE big col (1/4) | 196 MiB | 196 MiB | 196 MiB | 197 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 54 MiB | 54 MiB | 54 MiB | 54 MiB |
| S8b UPDATE big+COMMIT loop | 49 MiB | 49 MiB | 49 MiB | 49 MiB |
| S8s UPDATE small+COMMIT loop | 48 MiB | 48 MiB | 48 MiB | 48 MiB |
| S9 DELETE 1/4 | 113 MiB | 113 MiB | 113 MiB | 113 MiB |

### 100 B, warm: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 15.64 | 20.35 | 15.94 | 18.55 |
| S1 narrow scan | 0.06 | 0.06 | 0.06 | 0.06 |
| S2 wide scan | 0.16 | 0.11 | 0.11 | 0.11 |
| S3n PK lookup, small col | 2.27 | 2.17 | 2.17 | 2.12 |
| S3w PK lookup, big col | 2.32 | 2.22 | 2.17 | 2.27 |
| S5 UPDATE small col (all) | 9.58 | 11.18 | 9.53 | 9.13 |
| S6 UPDATE big col (1/4) | 3.57 | 3.18 | 2.67 | 2.52 |
| S7 UPDATE+INSERT+COMMIT loop | 3.02 | 21.15 | 7.13 | 16.29 |
| S8b UPDATE big+COMMIT loop | 33.89 | 15.54 | 15.39 | 12.44 |
| S8s UPDATE small+COMMIT loop | 24.16 | 15.49 | 14.85 | 11.38 |
| S9 DELETE 1/4 | 2.87 | 2.77 | 2.77 | 2.77 |

### 2048 B, io: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1.79 G | 1.83 G | 1.78 G | 1.80 G |
| S2 wide scan | 2.18 G | 2.21 G | 2.17 G | 2.36 G |
| S3n PK lookup, small col | 2.89 G | 2.74 G | 2.93 G | 2.91 G |
| S3w PK lookup, big col | 2.90 G | 2.76 G | 2.94 G | 2.98 G |
| S5 UPDATE small col (all) | 27.61 G | 29.30 G | 27.71 G | 27.80 G |
| S6 UPDATE big col (1/4) | 11.95 G | 12.47 G | 11.97 G | 12.22 G |
| S7 UPDATE+INSERT+COMMIT loop | 4.35 G | 5.04 G | 4.66 G | 4.37 G |
| S8b UPDATE big+COMMIT loop | 2.40 G | 2.58 G | 2.49 G | 2.43 G |
| S8s UPDATE small+COMMIT loop | 2.11 G | 2.12 G | 2.14 G | 2.08 G |
| S9 DELETE 1/4 | 16.23 G | 17.00 G | 17.80 G | 17.30 G |

### 2048 B, io: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 66.8 k | 66.8 k | 66.8 k | 66.8 k |
| S2 wide scan | 66.8 k | 66.8 k | 66.8 k | 66.8 k |
| S3n PK lookup, small col | 55.1 k | 55.1 k | 55.1 k | 55.1 k |
| S3w PK lookup, big col | 55.1 k | 55.1 k | 55.1 k | 55.1 k |
| S5 UPDATE small col (all) | 1.9 M | 1.9 M | 1.9 M | 1.9 M |
| S6 UPDATE big col (1/4) | 451.8 k | 451.5 k | 451.6 k | 451.6 k |
| S7 UPDATE+INSERT+COMMIT loop | 93.6 k | 92.0 k | 92.2 k | 92.2 k |
| S8b UPDATE big+COMMIT loop | 51.2 k | 53.0 k | 52.6 k | 52.7 k |
| S8s UPDATE small+COMMIT loop | 51.1 k | 51.1 k | 51.1 k | 51.1 k |
| S9 DELETE 1/4 | 1.1 M | 1.1 M | 1.1 M | 1.1 M |

### 2048 B, io: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1,057 MiB | 1,057 MiB | 1,057 MiB | 1,057 MiB |
| S2 wide scan | 1,057 MiB | 1,057 MiB | 1,057 MiB | 1,057 MiB |
| S3n PK lookup, small col | 152 MiB | 152 MiB | 152 MiB | 152 MiB |
| S3w PK lookup, big col | 147 MiB | 147 MiB | 147 MiB | 147 MiB |
| S5 UPDATE small col (all) | 1,065 MiB | 1,065 MiB | 1,065 MiB | 1,065 MiB |
| S6 UPDATE big col (1/4) | 269 MiB | 269 MiB | 269 MiB | 271 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 129 MiB | 129 MiB | 129 MiB | 133 MiB |
| S8b UPDATE big+COMMIT loop | 4 MiB | 20 MiB | 19 MiB | 18 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 1,066 MiB | 1,066 MiB | 1,066 MiB | 1,066 MiB |

### 2048 B, io: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 4,060 MiB | 4,139 MiB | 4,134 MiB | 4,075 MiB |
| S6 UPDATE big col (1/4) | 741 MiB | 765 MiB | 739 MiB | 741 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 52 MiB | 52 MiB | 52 MiB | 52 MiB |
| S8b UPDATE big+COMMIT loop | 36 MiB | 36 MiB | 36 MiB | 36 MiB |
| S8s UPDATE small+COMMIT loop | 36 MiB | 36 MiB | 36 MiB | 36 MiB |
| S9 DELETE 1/4 | 3,979 MiB | 3,988 MiB | 4,068 MiB | 4,076 MiB |

### 2048 B, io: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1.37 | 1.77 | 1.17 | 1.42 |
| S2 wide scan | 1.42 | 1.82 | 1.32 | 1.45 |
| S3n PK lookup, small col | 8.53 | 3.07 | 10.48 | 14.29 |
| S3w PK lookup, big col | 10.88 | 3.47 | 10.83 | 15.80 |
| S5 UPDATE small col (all) | 10.68 | 24.51 | 13.69 | 17.85 |
| S6 UPDATE big col (1/4) | 2.32 | 4.52 | 3.42 | 2.77 |
| S7 UPDATE+INSERT+COMMIT loop | 3.97 | 22.91 | 14.89 | 4.12 |
| S8b UPDATE big+COMMIT loop | 1.77 | 9.23 | 2.67 | 1.97 |
| S8s UPDATE small+COMMIT loop | 1.82 | 2.07 | 2.12 | 1.72 |
| S9 DELETE 1/4 | 9.98 | 9.53 | 13.49 | 11.29 |

### 2048 B, warm: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 65.98 G | 66.31 G | 71.08 G | 65.53 G |
| S1 narrow scan | 391.8 M | 388.4 M | 388.6 M | 389.0 M |
| S2 wide scan | 778.5 M | 778.6 M | 780.4 M | 940.7 M |
| S3n PK lookup, small col | 2.51 G | 2.46 G | 2.49 G | 2.48 G |
| S3w PK lookup, big col | 2.46 G | 2.44 G | 2.48 G | 2.51 G |
| S5 UPDATE small col (all) | 23.94 G | 24.75 G | 23.58 G | 25.47 G |
| S6 UPDATE big col (1/4) | 13.72 G | 13.74 G | 13.32 G | 13.72 G |
| S7 UPDATE+INSERT+COMMIT loop | 4.72 G | 4.49 G | 4.65 G | 4.53 G |
| S8b UPDATE big+COMMIT loop | 2.83 G | 2.82 G | 2.82 G | 2.81 G |
| S8s UPDATE small+COMMIT loop | 2.35 G | 2.32 G | 2.36 G | 2.32 G |
| S9 DELETE 1/4 | 6.60 G | 6.66 G | 7.53 G | 6.74 G |

### 2048 B, warm: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 2.1 M | 2.0 M | 2.2 M | 2.1 M |
| S1 narrow scan | 66.7 k | 66.7 k | 66.7 k | 66.7 k |
| S2 wide scan | 66.7 k | 66.7 k | 66.7 k | 66.7 k |
| S3n PK lookup, small col | 55.1 k | 55.1 k | 55.1 k | 55.1 k |
| S3w PK lookup, big col | 55.1 k | 55.1 k | 55.1 k | 55.1 k |
| S5 UPDATE small col (all) | 2.5 M | 2.5 M | 2.5 M | 2.5 M |
| S6 UPDATE big col (1/4) | 618.2 k | 618.2 k | 615.4 k | 618.2 k |
| S7 UPDATE+INSERT+COMMIT loop | 98.5 k | 98.6 k | 98.8 k | 98.8 k |
| S8b UPDATE big+COMMIT loop | 58.3 k | 58.2 k | 57.9 k | 58.0 k |
| S8s UPDATE small+COMMIT loop | 57.1 k | 57.1 k | 57.1 k | 57.1 k |
| S9 DELETE 1/4 | 1.3 M | 1.3 M | 1.3 M | 1.3 M |

### 2048 B, warm: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S6 UPDATE big col (1/4) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8b UPDATE big+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 0 MiB | 0 MiB | 0 MiB | 0 MiB |

### 2048 B, warm: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 2,430 MiB | 2,415 MiB | 2,415 MiB | 2,414 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 193 MiB | 193 MiB | 193 MiB | 193 MiB |
| S6 UPDATE big col (1/4) | 54 MiB | 54 MiB | 54 MiB | 54 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 55 MiB | 55 MiB | 55 MiB | 55 MiB |
| S8b UPDATE big+COMMIT loop | 48 MiB | 48 MiB | 48 MiB | 48 MiB |
| S8s UPDATE small+COMMIT loop | 48 MiB | 48 MiB | 48 MiB | 48 MiB |
| S9 DELETE 1/4 | 54 MiB | 54 MiB | 54 MiB | 54 MiB |

### 2048 B, warm: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 50.16 | 40.29 | 19.60 | 20.55 |
| S1 narrow scan | 0.11 | 0.11 | 0.11 | 0.11 |
| S2 wide scan | 0.06 | 0.11 | 0.11 | 0.11 |
| S3n PK lookup, small col | 2.27 | 1.97 | 2.07 | 2.07 |
| S3w PK lookup, big col | 2.17 | 2.27 | 2.22 | 2.22 |
| S5 UPDATE small col (all) | 4.88 | 4.92 | 4.77 | 5.32 |
| S6 UPDATE big col (1/4) | 2.37 | 2.22 | 2.17 | 2.28 |
| S7 UPDATE+INSERT+COMMIT loop | 26.76 | 9.38 | 11.79 | 11.94 |
| S8b UPDATE big+COMMIT loop | 10.69 | 7.68 | 6.58 | 8.18 |
| S8s UPDATE small+COMMIT loop | 8.43 | 6.93 | 4.37 | 7.83 |
| S9 DELETE 1/4 | 1.72 | 1.77 | 1.67 | 1.82 |

### 8192 B, io: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 3.03 G | 216.0 M | 108.5 M | 96.4 M |
| S2 wide scan | 2.96 G | 4.00 G | 3.23 G | 6.67 G |
| S3n PK lookup, small col | 2.67 G | 2.63 G | 2.49 G | 3.28 G |
| S3w PK lookup, big col | 2.83 G | 3.40 G | 2.79 G | 3.18 G |
| S5 UPDATE small col (all) | 25.37 G | 325.06 G | 4.64 G | 10.74 G |
| S6 UPDATE big col (1/4) | 11.36 G | 56.36 G | 15.30 G | 22.98 G |
| S7 UPDATE+INSERT+COMMIT loop | 7.36 G | 16.11 G | 9.31 G | 8.52 G |
| S8b UPDATE big+COMMIT loop | 3.79 G | 6.62 G | 3.47 G | 4.35 G |
| S8s UPDATE small+COMMIT loop | 2.73 G | 4.71 G | 2.05 G | 2.46 G |
| S9 DELETE 1/4 | 15.63 G | 6.45 G | 8.09 G | 15.26 G |

### 8192 B, io: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 120.1 k | 676 | 708 | 748 |
| S2 wide scan | 120.1 k | 360.7 k | 120.7 k | 600.8 k |
| S3n PK lookup, small col | 55.1 k | 55.1 k | 55.1 k | 80.1 k |
| S3w PK lookup, big col | 55.1 k | 70.1 k | 60.1 k | 80.1 k |
| S5 UPDATE small col (all) | 647.1 k | 2.5 M | 555.3 k | 1.2 M |
| S6 UPDATE big col (1/4) | 141.7 k | 503.8 k | 250.6 k | 1.1 M |
| S7 UPDATE+INSERT+COMMIT loop | 104.3 k | 215.9 k | 214.7 k | 277.2 k |
| S8b UPDATE big+COMMIT loop | 51.4 k | 132.5 k | 55.6 k | 177.4 k |
| S8s UPDATE small+COMMIT loop | 51.1 k | 140.3 k | 51.0 k | 97.9 k |
| S9 DELETE 1/4 | 477.9 k | 380.8 k | 427.0 k | 1.0 M |

### 8192 B, io: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1,883 MiB | 29 MiB | 28 MiB | 38 MiB |
| S2 wide scan | 1,883 MiB | 1,892 MiB | 1,890 MiB | 1,898 MiB |
| S3n PK lookup, small col | 93 MiB | 60 MiB | 57 MiB | 195 MiB |
| S3w PK lookup, big col | 97 MiB | 136 MiB | 138 MiB | 181 MiB |
| S5 UPDATE small col (all) | 1,928 MiB | 3,287 MiB | 26 MiB | 1,979 MiB |
| S6 UPDATE big col (1/4) | 476 MiB | 490 MiB | 876 MiB | 902 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 78 MiB | 799 MiB | 449 MiB | 362 MiB |
| S8b UPDATE big+COMMIT loop | 4 MiB | 773 MiB | 38 MiB | 108 MiB |
| S8s UPDATE small+COMMIT loop | 3 MiB | 774 MiB | 0 MiB | 15 MiB |
| S9 DELETE 1/4 | 1,930 MiB | 39 MiB | 551 MiB | 749 MiB |

### 8192 B, io: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 5,605 MiB | 5,923 MiB | 40 MiB | 45 MiB |
| S6 UPDATE big col (1/4) | 969 MiB | 1,255 MiB | 2,521 MiB | 2,759 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 57 MiB | 133 MiB | 320 MiB | 227 MiB |
| S8b UPDATE big+COMMIT loop | 36 MiB | 39 MiB | 36 MiB | 46 MiB |
| S8s UPDATE small+COMMIT loop | 36 MiB | 39 MiB | 36 MiB | 36 MiB |
| S9 DELETE 1/4 | 3,843 MiB | 833 MiB | 1,694 MiB | 2,409 MiB |

### 8192 B, io: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 2.87 | 0.26 | 0.11 | 0.21 |
| S2 wide scan | 2.87 | 6.48 | 3.92 | 4.17 |
| S3n PK lookup, small col | 3.07 | 5.98 | 2.12 | 18.70 |
| S3w PK lookup, big col | 10.48 | 33.68 | 3.47 | 15.19 |
| S5 UPDATE small col (all) | 34.68 | 99.19 | 0.97 | 7.58 |
| S6 UPDATE big col (1/4) | 6.39 | 11.59 | 11.89 | 9.08 |
| S7 UPDATE+INSERT+COMMIT loop | 57.78 | 32.97 | 21.15 | 5.82 |
| S8b UPDATE big+COMMIT loop | 25.81 | 19.85 | 9.38 | 2.72 |
| S8s UPDATE small+COMMIT loop | 24.11 | 16.69 | 1.72 | 8.73 |
| S9 DELETE 1/4 | 14.09 | 0.97 | 10.33 | 11.28 |

### 8192 B, warm: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 63.24 G | 59.55 G | 64.27 G | 73.61 G |
| S1 narrow scan | 569.8 M | 168.9 M | 70.1 M | 45.5 M |
| S2 wide scan | 529.2 M | 938.1 M | 580.4 M | 5.04 G |
| S3n PK lookup, small col | 2.49 G | 2.45 G | 2.43 G | 2.65 G |
| S3w PK lookup, big col | 2.52 G | 2.53 G | 2.49 G | 2.71 G |
| S5 UPDATE small col (all) | 15.38 G | 27.98 G | 6.29 G | 11.66 G |
| S6 UPDATE big col (1/4) | 11.88 G | 66.35 G | 15.65 G | 23.56 G |
| S7 UPDATE+INSERT+COMMIT loop | 6.95 G | 12.67 G | 9.13 G | 8.54 G |
| S8b UPDATE big+COMMIT loop | 3.93 G | 6.40 G | 3.93 G | 4.92 G |
| S8s UPDATE small+COMMIT loop | 2.76 G | 4.39 G | 2.33 G | 2.53 G |
| S9 DELETE 1/4 | 4.49 G | 2.36 G | 3.06 G | 7.13 G |

### 8192 B, warm: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 1.1 M | 1.3 M | 1.1 M | 2.2 M |
| S1 narrow scan | 120.1 k | 644 | 676 | 712 |
| S2 wide scan | 120.1 k | 360.6 k | 120.7 k | 600.7 k |
| S3n PK lookup, small col | 55.1 k | 55.1 k | 55.1 k | 80.1 k |
| S3w PK lookup, big col | 55.1 k | 70.1 k | 60.1 k | 80.1 k |
| S5 UPDATE small col (all) | 913.5 k | 2.0 M | 722.0 k | 1.6 M |
| S6 UPDATE big col (1/4) | 210.2 k | 752.1 k | 460.2 k | 1.6 M |
| S7 UPDATE+INSERT+COMMIT loop | 111.7 k | 183.9 k | 275.0 k | 294.9 k |
| S8b UPDATE big+COMMIT loop | 58.4 k | 102.0 k | 62.7 k | 219.7 k |
| S8s UPDATE small+COMMIT loop | 57.3 k | 106.9 k | 57.1 k | 117.7 k |
| S9 DELETE 1/4 | 517.8 k | 546.1 k | 490.5 k | 1.2 M |

### 8192 B, warm: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S6 UPDATE big col (1/4) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8b UPDATE big+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 0 MiB | 0 MiB | 0 MiB | 0 MiB |

### 8192 B, warm: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 3,968 MiB | 3,815 MiB | 3,999 MiB | 4,041 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 67 MiB | 4,088 MiB | 52 MiB | 55 MiB |
| S6 UPDATE big col (1/4) | 29 MiB | 115 MiB | 1,091 MiB | 1,174 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 60 MiB | 76 MiB | 64 MiB | 76 MiB |
| S8b UPDATE big+COMMIT loop | 49 MiB | 52 MiB | 49 MiB | 61 MiB |
| S8s UPDATE small+COMMIT loop | 49 MiB | 51 MiB | 48 MiB | 49 MiB |
| S9 DELETE 1/4 | 67 MiB | 13 MiB | 17 MiB | 64 MiB |

### 8192 B, warm: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 30.47 | 107.05 | 54.01 | 55.51 |
| S1 narrow scan | 0.18 | 0.03 | 0.03 | 0.03 |
| S2 wide scan | 0.12 | 0.26 | 0.21 | 0.87 |
| S3n PK lookup, small col | 2.07 | 2.07 | 1.97 | 2.17 |
| S3w PK lookup, big col | 2.33 | 2.17 | 2.17 | 2.32 |
| S5 UPDATE small col (all) | 4.92 | 89.38 | 1.37 | 3.12 |
| S6 UPDATE big col (1/4) | 1.92 | 11.34 | 14.19 | 18.30 |
| S7 UPDATE+INSERT+COMMIT loop | 3.82 | 44.65 | 21.65 | 21.95 |
| S8b UPDATE big+COMMIT loop | 2.22 | 53.87 | 11.13 | 2.57 |
| S8s UPDATE small+COMMIT loop | 19.56 | 57.89 | 10.58 | 2.02 |
| S9 DELETE 1/4 | 0.97 | 0.52 | 0.97 | 2.07 |

### 65536 B, io: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1.72 G | 38.1 M | 23.8 M | 21.1 M |
| S2 wide scan | 1.74 G | 1.83 G | 1.83 G | 6.61 G |
| S3n PK lookup, small col | 3.93 G | 2.41 G | 2.51 G | 6.38 G |
| S3w PK lookup, big col | 3.90 G | 3.66 G | 3.86 G | 6.44 G |
| S5 UPDATE small col (all) | 11.65 G | 189.49 G | 769.9 M | 7.71 G |
| S6 UPDATE big col (1/4) | 8.74 G | 29.47 G | 10.76 G | 26.39 G |
| S7 UPDATE+INSERT+COMMIT loop | 27.79 G | 51.81 G | 29.74 G | 42.76 G |
| S8b UPDATE big+COMMIT loop | 12.69 G | 16.70 G | 11.51 G | 17.83 G |
| S8s UPDATE small+COMMIT loop | 2.95 G | 6.17 G | 2.14 G | 3.65 G |
| S9 DELETE 1/4 | 5.91 G | 4.07 G | 4.56 G | 18.24 G |

### 65536 B, io: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 96.2 k | 275 | 206 | 214 |
| S2 wide scan | 96.1 k | 112.2 k | 128.2 k | 416.2 k |
| S3n PK lookup, small col | 90.1 k | 55.1 k | 55.1 k | 185.1 k |
| S3w PK lookup, big col | 90.1 k | 90.1 k | 95.1 k | 185.1 k |
| S5 UPDATE small col (all) | 542.1 k | 1.3 M | 85.9 k | 489.3 k |
| S6 UPDATE big col (1/4) | 115.8 k | 268.3 k | 111.5 k | 769.4 k |
| S7 UPDATE+INSERT+COMMIT loop | 220.6 k | 457.4 k | 258.1 k | 1.2 M |
| S8b UPDATE big+COMMIT loop | 127.6 k | 222.7 k | 69.4 k | 720.0 k |
| S8s UPDATE small+COMMIT loop | 128.0 k | 237.8 k | 51.0 k | 237.3 k |
| S9 DELETE 1/4 | 245.5 k | 71.5 k | 86.9 k | 601.2 k |

### 65536 B, io: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 1,260 MiB | 5 MiB | 6 MiB | 5 MiB |
| S2 wide scan | 1,260 MiB | 1,261 MiB | 1,261 MiB | 2,013 MiB |
| S3n PK lookup, small col | 1,004 MiB | 4 MiB | 11 MiB | 1,828 MiB |
| S3w PK lookup, big col | 1,030 MiB | 400 MiB | 1,033 MiB | 1,817 MiB |
| S5 UPDATE small col (all) | 1,488 MiB | 2,450 MiB | 6 MiB | 2,520 MiB |
| S6 UPDATE big col (1/4) | 319 MiB | 337 MiB | 453 MiB | 2,324 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 550 MiB | 775 MiB | 579 MiB | 2,200 MiB |
| S8b UPDATE big+COMMIT loop | 17 MiB | 703 MiB | 28 MiB | 334 MiB |
| S8s UPDATE small+COMMIT loop | 16 MiB | 706 MiB | 0 MiB | 31 MiB |
| S9 DELETE 1/4 | 1,497 MiB | 15 MiB | 119 MiB | 2,135 MiB |

### 65536 B, io: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 2,476 MiB | 4,413 MiB | 7 MiB | 7 MiB |
| S6 UPDATE big col (1/4) | 303 MiB | 798 MiB | 931 MiB | 3,113 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 649 MiB | 809 MiB | 934 MiB | 2,251 MiB |
| S8b UPDATE big+COMMIT loop | 43 MiB | 99 MiB | 37 MiB | 183 MiB |
| S8s UPDATE small+COMMIT loop | 44 MiB | 114 MiB | 36 MiB | 36 MiB |
| S9 DELETE 1/4 | 757 MiB | 642 MiB | 650 MiB | 3,352 MiB |

### 65536 B, io: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S1 narrow scan | 2.92 | 0.03 | 0.03 | 0.03 |
| S2 wide scan | 3.32 | 2.87 | 2.72 | 4.22 |
| S3n PK lookup, small col | 10.29 | 2.02 | 2.17 | 8.13 |
| S3w PK lookup, big col | 10.18 | 6.68 | 6.28 | 7.93 |
| S5 UPDATE small col (all) | 27.57 | 33.08 | 0.32 | 7.98 |
| S6 UPDATE big col (1/4) | 3.57 | 4.67 | 3.22 | 12.09 |
| S7 UPDATE+INSERT+COMMIT loop | 23.06 | 26.06 | 10.74 | 27.21 |
| S8b UPDATE big+COMMIT loop | 14.34 | 19.05 | 3.42 | 6.73 |
| S8s UPDATE small+COMMIT loop | 11.34 | 4.12 | 1.87 | 6.33 |
| S9 DELETE 1/4 | 5.17 | 0.11 | 1.17 | 29.42 |

### 65536 B, warm: server instructions incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 50.45 G | 51.53 G | 51.41 G | 68.08 G |
| S1 narrow scan | 183.1 M | 31.2 M | 15.0 M | 12.3 M |
| S2 wide scan | 365.7 M | 249.5 M | 278.2 M | 4.11 G |
| S3n PK lookup, small col | 2.62 G | 2.46 G | 2.42 G | 4.41 G |
| S3w PK lookup, big col | 2.66 G | 2.99 G | 2.60 G | 4.37 G |
| S5 UPDATE small col (all) | 6.75 G | 13.82 G | 879.0 M | 5.78 G |
| S6 UPDATE big col (1/4) | 10.36 G | 33.95 G | 12.43 G | 21.28 G |
| S7 UPDATE+INSERT+COMMIT loop | 30.45 G | 48.42 G | 29.99 G | 37.82 G |
| S8b UPDATE big+COMMIT loop | 15.48 G | 18.05 G | 14.82 G | 21.86 G |
| S8s UPDATE small+COMMIT loop | 3.10 G | 5.03 G | 2.28 G | 3.44 G |
| S9 DELETE 1/4 | 3.10 G | 703.6 M | 1.35 G | 6.60 G |

### 65536 B, warm: data page fetches

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 372.2 k | 515.1 k | 398.1 k | 1.3 M |
| S1 narrow scan | 96.1 k | 232 | 163 | 167 |
| S2 wide scan | 96.1 k | 112.2 k | 128.2 k | 416.2 k |
| S3n PK lookup, small col | 90.1 k | 55.1 k | 55.1 k | 185.1 k |
| S3w PK lookup, big col | 90.1 k | 90.1 k | 95.1 k | 185.1 k |
| S5 UPDATE small col (all) | 624.4 k | 818.3 k | 96.4 k | 544.4 k |
| S6 UPDATE big col (1/4) | 156.4 k | 388.3 k | 174.6 k | 944.7 k |
| S7 UPDATE+INSERT+COMMIT loop | 253.5 k | 448.9 k | 300.4 k | 1.3 M |
| S8b UPDATE big+COMMIT loop | 160.4 k | 214.7 k | 83.2 k | 961.2 k |
| S8s UPDATE small+COMMIT loop | 160.2 k | 236.3 k | 57.1 k | 307.0 k |
| S9 DELETE 1/4 | 256.1 k | 126.3 k | 99.8 k | 544.4 k |

### 65536 B, warm: OS read bytes

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S6 UPDATE big col (1/4) | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8b UPDATE big+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S8s UPDATE small+COMMIT loop | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S9 DELETE 1/4 | 0 MiB | 0 MiB | 0 MiB | 0 MiB |

### 65536 B, warm: OS write bytes incl. drain

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 2,522 MiB | 2,546 MiB | 2,535 MiB | 4,287 MiB |
| S1 narrow scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S2 wide scan | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3n PK lookup, small col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S3w PK lookup, big col | 0 MiB | 0 MiB | 0 MiB | 0 MiB |
| S5 UPDATE small col (all) | 59 MiB | 2,566 MiB | 7 MiB | 7 MiB |
| S6 UPDATE big col (1/4) | 16 MiB | 62 MiB | 556 MiB | 1,189 MiB |
| S7 UPDATE+INSERT+COMMIT loop | 592 MiB | 113 MiB | 99 MiB | 224 MiB |
| S8b UPDATE big+COMMIT loop | 58 MiB | 61 MiB | 50 MiB | 178 MiB |
| S8s UPDATE small+COMMIT loop | 58 MiB | 60 MiB | 49 MiB | 49 MiB |
| S9 DELETE 1/4 | 19 MiB | 3 MiB | 20 MiB | 134 MiB |

### 65536 B, warm: wall seconds

| scenario | develop | oos | sidecar | inner |
|---|---|---|---|---|
| S4 load INSERT | 40.74 | 19.80 | 34.72 | 32.07 |
| S1 narrow scan | 0.21 | 0.03 | 0.03 | 0.03 |
| S2 wide scan | 0.36 | 0.31 | 0.37 | 1.57 |
| S3n PK lookup, small col | 2.32 | 2.27 | 2.02 | 3.02 |
| S3w PK lookup, big col | 2.52 | 2.72 | 2.52 | 3.12 |
| S5 UPDATE small col (all) | 2.07 | 17.36 | 0.26 | 2.07 |
| S6 UPDATE big col (1/4) | 1.77 | 5.67 | 4.32 | 7.43 |
| S7 UPDATE+INSERT+COMMIT loop | 9.63 | 10.84 | 14.74 | 10.88 |
| S8b UPDATE big+COMMIT loop | 4.37 | 4.62 | 4.37 | 6.98 |
| S8s UPDATE small+COMMIT loop | 2.07 | 4.27 | 2.22 | 2.52 |
| S9 DELETE 1/4 | 1.17 | 0.11 | 0.16 | 0.97 |

## Storage

| size | variant | tag | DB bytes |
|---|---|---|---|
| 100 | develop | after-load | 1,441 MiB |
| 100 | develop | end | 2,304 MiB |
| 100 | oos | after-load | 1,441 MiB |
| 100 | oos | end | 2,304 MiB |
| 100 | sidecar | after-load | 1,441 MiB |
| 100 | sidecar | end | 2,304 MiB |
| 100 | inner | after-load | 1,441 MiB |
| 100 | inner | end | 2,304 MiB |
| 2048 | oos | after-load | 1,697 MiB |
| 2048 | oos | end | 1,985 MiB |
| 2048 | sidecar | after-load | 1,697 MiB |
| 2048 | sidecar | end | 1,985 MiB |
| 2048 | inner | after-load | 1,697 MiB |
| 2048 | inner | end | 1,985 MiB |
| 2048 | develop | after-load | 1,697 MiB |
| 2048 | develop | end | 1,985 MiB |
| 8192 | sidecar | after-load | 2,401 MiB |
| 8192 | sidecar | end | 3,041 MiB |
| 8192 | inner | after-load | 2,433 MiB |
| 8192 | inner | end | 3,233 MiB |
| 8192 | develop | after-load | 2,401 MiB |
| 8192 | develop | end | 2,593 MiB |
| 8192 | oos | after-load | 2,305 MiB |
| 8192 | oos | end | 4,705 MiB |
| 65536 | inner | after-load | 2,529 MiB |
| 65536 | inner | end | 3,649 MiB |
| 65536 | develop | after-load | 1,633 MiB |
| 65536 | develop | end | 2,049 MiB |
| 65536 | oos | after-load | 1,633 MiB |
| 65536 | oos | end | 3,201 MiB |
| 65536 | sidecar | after-load | 1,633 MiB |
| 65536 | sidecar | end | 2,017 MiB |

## Failed statements

- none

## Largest repeat spread ((max-min)/median)

- wall (8192, 'io', 'S3n', 'develop'): 4.62
- wall (2048, 'io', 'S3n', 'oos'): 3.70
- wall (2048, 'io', 'S3w', 'oos'): 2.37
- wall (2048, 'io', 'S3n', 'inner'): 1.26
- wall (2048, 'io', 'S3w', 'sidecar'): 1.06
- wall (2048, 'io', 'S3n', 'sidecar'): 1.03
- wall (65536, 'io', 'S1', 'inner'): 1.02
- wall (100, 'io', 'S3n', 'inner'): 1.01
- wall (65536, 'io', 'S1', 'sidecar'): 1.00
- wall (8192, 'io', 'S3w', 'develop'): 0.99
- wall (8192, 'io', 'S3n', 'inner'): 0.93
- wall (2048, 'io', 'S3w', 'inner'): 0.86
- wall (2048, 'warm', 'S2', 'develop'): 0.84
- wall (65536, 'io', 'S3n', 'develop'): 0.81
- wall (8192, 'io', 'S3w', 'inner'): 0.80
