live=4096 records (one per page), steps=200000, seed=7
| workload | design | grows | grows with reclaim | reclaims saved vs cand | mean pages examined per grow | max | peak pages | peak sectors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vacuum only, fast path 0.9 | current | 180064 | 0 (0.0%) |  | 4096.00 | 4096 | 4096 | 64 |
| vacuum only, fast path 0.9 | cand (set K=0) | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| vacuum only, fast path 0.9 | set K=8 | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| vacuum only, fast path 0.9 | set K=64 | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| vacuum only, fast path 0.9 | count K=0 | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| vacuum only, fast path 0.9 | count K=64 | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| vacuum only, fast path 0.9 | count e=0.1 | 180064 | 0 (0.0%) | 0 | 0.00 | 0 | 4096 | 64 |
| rollback 5%, fast path 0.9 | current | 189848 | 9784 (5.2%) |  | 3989.69 | 4096 | 4096 | 64 |
| rollback 5%, fast path 0.9 | cand (set K=0) | 189848 | 9784 (5.2%) | 0 | 0.05 | 1 | 4096 | 64 |
| rollback 5%, fast path 0.9 | set K=8 | 189848 | 9776 (5.1%) | 8 | 0.05 | 1 | 4104 | 65 |
| rollback 5%, fast path 0.9 | set K=64 | 189848 | 9720 (5.1%) | 64 | 0.05 | 1 | 4160 | 65 |
| rollback 5%, fast path 0.9 | count K=0 | 189848 | 9784 (5.2%) | 0 | 104.78 | 4096 | 4096 | 64 |
| rollback 5%, fast path 0.9 | count K=64 | 189848 | 9720 (5.1%) | 64 | 1.66 | 359 | 4160 | 65 |
| rollback 5%, fast path 0.9 | count e=0.1 | 189848 | 9329 (4.9%) | 455 | 0.25 | 41 | 4551 | 72 |
| fast path 0.5, half the misses hidden | current | 150110 | 49984 (33.3%) |  | 3413.47 | 4096 | 4096 | 64 |
| fast path 0.5, half the misses hidden | cand (set K=0) | 150110 | 49984 (33.3%) | 0 | 0.33 | 1 | 4096 | 64 |
| fast path 0.5, half the misses hidden | set K=8 | 150110 | 49976 (33.3%) | 8 | 0.33 | 1 | 4104 | 65 |
| fast path 0.5, half the misses hidden | set K=64 | 150110 | 49920 (33.3%) | 64 | 0.33 | 1 | 4160 | 65 |
| fast path 0.5, half the misses hidden | count K=0 | 150110 | 49984 (33.3%) | 0 | 681.37 | 4096 | 4096 | 64 |
| fast path 0.5, half the misses hidden | count K=64 | 150110 | 49920 (33.3%) | 64 | 10.70 | 374 | 4160 | 65 |
| fast path 0.5, half the misses hidden | count e=0.1 | 150110 | 49529 (33.0%) | 455 | 1.71 | 91 | 4551 | 72 |
| no fast path, all hidden | current | 200000 | 200000 (100.0%) |  | 2047.46 | 4096 | 4096 | 64 |
| no fast path, all hidden | cand (set K=0) | 200000 | 200000 (100.0%) | 0 | 1.00 | 1 | 4096 | 64 |
| no fast path, all hidden | set K=8 | 200000 | 199992 (100.0%) | 8 | 1.00 | 1 | 4104 | 65 |
| no fast path, all hidden | set K=64 | 200000 | 199936 (100.0%) | 64 | 1.00 | 1 | 4160 | 65 |
| no fast path, all hidden | count K=0 | 200000 | 200000 (100.0%) | 0 | 2047.46 | 4096 | 4096 | 64 |
| no fast path, all hidden | count K=64 | 200000 | 199936 (100.0%) | 64 | 32.16 | 375 | 4160 | 65 |
| no fast path, all hidden | count e=0.1 | 200000 | 199545 (99.8%) | 455 | 5.16 | 55 | 4551 | 72 |
