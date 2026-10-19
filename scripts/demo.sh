#!/usr/bin/env bash
# Astra Platform — Investor Demo Walkthrough
# Usage:  bash scripts/demo.sh
# Requires: uvicorn running on localhost:8000
# Auto-resets to clean demo state before running.

set -euo pipefail

BASE="http://localhost:8000"
C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_CYAN=$'\033[36m'
C_GREEN=$'\033[32m'

section() {
  echo ""
  echo "${C_BOLD}${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
  echo "${C_BOLD}${C_CYAN}  $1${C_RESET}"
  echo "${C_BOLD}${C_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}"
}

# Temp directory for intermediate JSON files
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# ── Pre-demo reset (ensures clean state for every run) ──
echo "${C_BOLD}🔄 Resetting to known-good demo state...${C_RESET}"
python3 scripts/seed_demo.py --hard > /dev/null 2>&1 || {
  echo "⚠️  Reset failed — continuing anyway"
}
echo "   ✅ Ready"

# ── 0. Health ────────────────────────────────────────────
section "0. Platform health"
curl -s "$BASE/health" | python3 -m json.tool

# ── 1. Login ─────────────────────────────────────────────
section "1. Login"
LOGIN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@astra.com","password":"Test@123"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "User: $(echo "$LOGIN" | python3 -c "import sys,json;d=json.load(sys.stdin)['user'];print(d['email'])")"
echo "Token: ${TOKEN:0:24}..."
AUTH="Authorization: Bearer $TOKEN"

# ── 2. FX rate ───────────────────────────────────────────
section "2. FX — mid-market USD/INR rate"
curl -s "$BASE/api/v1/fx/rate/USD/INR" -H "$AUTH" | python3 -m json.tool

# ── 3. Cost Optimizer — compare $1000 USD→INR ────────────
section "3. Cost Optimizer — \$1000 USD → INR, 5 providers"
curl -s "$BASE/api/v1/cost/compare?base=USD&quote=INR&amount=1000" -H "$AUTH" > "$TMP/cost.json"
python3 - "$TMP/cost.json" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    d = json.load(f)

providers = d.get('providers') or d.get('results') or d.get('comparisons') or []
if not providers:
    print(json.dumps(d, indent=2))
    sys.exit(0)

def get_cost(p):
    return p.get('total_cost', p.get('cost', p.get('total', 999)))
def get_recipient(p):
    return p.get('recipient_gets', p.get('recipient_amount', p.get('converted', 0)))
def get_name(p):
    return p.get('provider', p.get('provider_name', p.get('name', '?')))

providers.sort(key=get_cost)
print(f"{'Rank':<5}{'Provider':<16}{'Cost':>10}{'Recipient gets':>18}")
print('-' * 52)
for i, p in enumerate(providers, 1):
    print(f"{i:<5}{get_name(p):<16}{get_cost(p):>10.2f} {get_recipient(p):>16,.2f}")

if len(providers) > 1:
    savings = get_cost(providers[-1]) - get_cost(providers[0])
    amount = d.get('amount') or d.get('base_amount') or 1000
    pct = savings / amount * 100 if amount else 0
    print('-' * 52)
    print(f"Max savings: ${savings:.2f} ({pct:.1f}% of transfer)")
PYEOF

# ── 4. Last Mile — route $5000 USD→INR ──────────────────
section "4. Last Mile — route \$5000 USD → INR (balanced)"
curl -s -X POST "$BASE/api/v1/lastmile/route" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"source_currency":"USD","target_currency":"INR","amount":5000,"strategy":"balanced"}' \
  | python3 -m json.tool

# ── 5. Status lifecycle ─────────────────────────────────
section "5. Last Mile — payment status lifecycle"
REF="DEMO-$(date +%s)"
echo "Creating status events for $REF"
for STATUS in initiated processing settled; do
  curl -s -X POST "$BASE/api/v1/lastmile/status/$REF/event" -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"$STATUS\",\"note\":\"demo step: $STATUS\"}" > /dev/null
done
curl -s "$BASE/api/v1/lastmile/status/$REF" -H "$AUTH" | python3 -m json.tool

# ── 6. Reconciliation ───────────────────────────────────
section "6. Reconciliation — import ledger + statement, run, summary"
echo "Importing sample ledger..."
curl -s -X POST "$BASE/api/v1/reconciliation/ledger/import" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d @modules/reconciliation/data/sample_ledger.json > /dev/null
echo "Uploading sample statement..."
curl -s -X POST "$BASE/api/v1/reconciliation/statements/import" -H "$AUTH" \
  -F "file=@modules/reconciliation/data/sample_statement.csv" > /dev/null
echo "Running reconciliation for period 2026-03..."
curl -s -X POST "$BASE/api/v1/reconciliation/runs" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"period_start":"2026-03-01T00:00:00","period_end":"2026-03-31T23:59:59"}' \
  > "$TMP/run.json"
python3 -m json.tool < "$TMP/run.json"

RUN_ID=$(python3 -c "import json,sys;print(json.load(open('$TMP/run.json'))['run_id'])")
echo ""
echo "Discrepancies (run $RUN_ID):"
curl -s "$BASE/api/v1/reconciliation/runs/$RUN_ID/discrepancies" -H "$AUTH" > "$TMP/disc.json"
python3 - "$TMP/disc.json" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    d = json.load(f)
items = d.get('items', [])
print(f"  Total: {len(items)}")
for i in items:
    print(f"  • {i['type']:<22} {i['detail']}")
PYEOF

# ── 7. Summary ──────────────────────────────────────────
section "7. Modules loaded"
curl -s "$BASE/modules" > "$TMP/modules.json"
python3 - "$TMP/modules.json" <<'PYEOF'
import sys, json
with open(sys.argv[1]) as f:
    d = json.load(f)
print(f"  Total: {d['count']}   Enabled: {d['enabled_count']}")
for m in d['modules']:
    print(f"  ✓ {m['name']:<16} v{m.get('version','?')}   {m.get('api_prefix','')}")
PYEOF

echo ""
echo "${C_GREEN}${C_BOLD}✅ Demo complete.${C_RESET}"
echo ""