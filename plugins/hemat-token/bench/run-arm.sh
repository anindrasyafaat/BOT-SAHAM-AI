#!/bin/bash
# Benchmark arm: fresh fixture, headless Claude, then correctness check. Costs real API money (~$0.2-0.5 per run).
# usage: run-arm.sh <name> [extra claude flags...]
S=$(cd "$(dirname "$0")" && pwd); name=$1; shift
d=$S/run-$name; node $S/make-fixture.js $d
cd $d && timeout 600 claude -p "Tests in test.js fail. Find and fix the bug in src/, then run node test.js to confirm. Reply in one line." \
  --output-format json --permission-mode acceptEdits --allowedTools "Read Grep Glob Edit Bash(node test.js)" "$@" > $S/$name.out.json 2>$S/$name.err
node test.js >/dev/null 2>&1 && echo "$name PASS" || echo "$name FAIL"
