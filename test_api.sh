#!/bin/bash
echo "🧪 Testing Astra API..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Test 1: Health
echo -n "1. Health Check: "
response=$(curl -s http://localhost:8000/health)
if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

# Test 2: FX Rate
echo -n "2. FX Rate: "
response=$(curl -s http://localhost:8000/fx/rate?source=USD&target=INR)
if echo "$response" | grep -q "rate"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

# Test 3: Prediction
echo -n "3. AI Prediction: "
response=$(curl -s -X POST http://localhost:8000/fx/predict -H "Content-Type: application/json" -d '{"source":"USD","target":"INR"}')
if echo "$response" | grep -q "predicted_rate"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

# Test 4: Create Agent
echo -n "4. Create Agent: "
response=$(curl -s -X POST http://localhost:8000/agents/create -H "Content-Type: application/json" -d '{"rule_type":"target_rate","target_rate":86.0,"amount":50000}')
if echo "$response" | grep -q "rule_id"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
fi

echo ""
echo "✅ All tests complete!"
