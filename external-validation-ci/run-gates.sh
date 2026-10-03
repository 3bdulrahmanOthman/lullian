#!/bin/bash
# Runs every available external gate against /workspace/lullian, writing raw
# evidence (command output, exit codes, reports) to /out. Repository-only file;
# not part of the shipped artifact.
set -uo pipefail
S=/workspace/lullian
O=/out
mkdir -p "$O/se-t1"

{
  echo "== versions =="
  skillspector --version
  semgrep --version
  gitleaks version
  osv-scanner --version
  skillevaluator --version
  skills-ref --version
  pip-audit --version
  bandit --version
} > "$O/tools.txt" 2>&1

echo "[gate] skills-ref"
skills-ref validate "$S" > "$O/skills-ref.out" 2>&1
echo $? > "$O/skills-ref.exit"

echo "[gate] semgrep p/default"
semgrep scan --config p/default --json --quiet "$S" > "$O/semgrep-p-default.json" 2> "$O/semgrep.stderr"
echo $? > "$O/semgrep.exit"

echo "[gate] gitleaks"
gitleaks dir "$S" --report-format json --report-path "$O/gitleaks.json" --no-banner --redact > "$O/gitleaks.stdout" 2> "$O/gitleaks.stderr"
echo $? > "$O/gitleaks.exit"

echo "[gate] osv-scanner"
osv-scanner scan source -r "$S" --format json > "$O/osv.json" 2> "$O/osv.stderr"
echo $? > "$O/osv.exit"

echo "[gate] skillspector static"
skillspector scan "$S" --no-llm --format json --output "$O/skillspector.json" > "$O/skillspector.stdout" 2> "$O/skillspector.stderr"
echo $? > "$O/skillspector.exit"

echo "[gate] skillevaluator tier1"
skillevaluator validate "$S" --type skill --tiers 1 -r json,cli -o "$O/se-t1" > "$O/skillevaluator-t1.stdout" 2> "$O/skillevaluator-t1.stderr"
echo $? > "$O/skillevaluator-t1.exit"

echo "[gate] skillevaluator tier2 (record actual result)"
skillevaluator tier2 "$S" > "$O/skillevaluator-t2.stdout" 2> "$O/skillevaluator-t2.stderr"
echo $? > "$O/skillevaluator-t2.exit"

echo "[gate] skillevaluator tier3 readiness (no simulation)"
skillevaluator doctor > "$O/skillevaluator-t3-doctor.stdout" 2> "$O/skillevaluator-t3-doctor.stderr"
echo $? > "$O/skillevaluator-t3.exit"

echo DONE
