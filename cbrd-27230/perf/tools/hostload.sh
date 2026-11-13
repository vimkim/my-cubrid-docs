#!/bin/bash
# Sample the host load every INTERVAL seconds: date, /proc/loadavg and the six busiest processes.
out=${1:?output file}
iv=${2:-30}
while :; do
  { date '+%F %T'; cat /proc/loadavg; ps -eo pcpu,user:12,comm --sort=-pcpu | head -n 7; echo; } >> "$out"
  sleep "$iv"
done
