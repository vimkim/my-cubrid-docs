| scenario | mode | build | rep 0 (G) | rep 1 (G) | rep 2 (G) | median (G) | wall s (median) | OS write MiB (median) | x develop |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| S5 | warm | develop | 4.65 | 4.54 | 4.45 | 4.54 | 1.12 | 22 | x1.00 |
| S5 | warm | oos | 6.72 | 47.22 | 74.93 | 47.22 | 6.98 | 135 | x10.41 |
| S5 | io | develop | 10.39 | 10.23 | 10.14 | 10.23 | 9.03 | 2,343 | x1.00 |
| S5 | io | oos | 65.84 | 88.13 | 73.94 | 73.94 | 14.44 | 2,616 | x7.23 |
| S8s | warm | develop | 0.50 | 0.50 | 0.50 | 0.50 | 0.52 | 10 | x1.00 |
| S8s | warm | oos | 0.57 | 0.71 | 0.76 | 0.71 | 0.42 | 10 | x1.42 |
| S8s | io | develop | 0.52 | 0.52 | 0.59 | 0.52 | 0.52 | 10 | x1.00 |
| S8s | io | oos | 0.95 | 0.83 | 0.82 | 0.83 | 0.77 | 10 | x1.60 |

| after | develop heap pages | oos OOS pages / recs |
|---|---:|---:|
| after-load | 40,001 | 40,001 / 40,000 |
| warm-S5-0 | 40,001 | 80,001 / 40,135 |
| warm-S5-1 | 40,602 | 81,439 / 40,600 |
| warm-S5-2 | 41,202 | 82,688 / 41,200 |
| io-S5-0 | 41,802 | 83,770 / 41,800 |
| io-S5-1 | 42,402 | 85,331 / 42,400 |
| io-S5-2 | 43,002 | 86,543 / 43,000 |
| end | 12,412 | 86,362 / 12,388 |

checksum/content points: 10; disagreeing between develop and oos: 0
