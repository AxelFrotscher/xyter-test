#!/bin/bash
for i in $(seq 0 1 127)
do
   echo "Get Scurve for channel: $i"
   ./test_sts_scurve_4.py $i
done
