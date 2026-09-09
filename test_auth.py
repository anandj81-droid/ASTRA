#!/usr/bin/env python3
"""
Test script for Astra JWT authentication
Run: python test_auth.py
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_response(response, label=""):
    print(f"\n📤 {label} Response:")
    print(f"  Status: {response.status_code}")
    try:
        print(f"  Data: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"  Data: {response.text}")
    return response

def test_login():
    print_section("TEST 1: LOGIN")
    
    login_data = {
        "email": "test@astra.com",
        "password": "Test@123"
    }
    
    print(f"📝 Login with: {login_data['email']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print_response(response, "Login")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Login successful!")
            print(f"  Token: {data['access_token'][:50]}...")
            print(f"  Refresh: {data['refresh_token'][:50]}...")
            print(f"  User: {data['user']['email']} (ID: {data['user']['id']})")
            return data
        else:
            print(f"\n❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def test_protected_endpoint(token):
    print_section("TEST 2: ACCESS PROTECTED ENDPOINT")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("📝 Accessing /auth/me")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=headers
        )
        
        print_response(response, "Protected Endpoint")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Protected endpoint accessible!")
            print(f"  User: {data['name']} ({data['email']})")
            print(f"  Verified: {data['is_verified']}")
            return True
        else:
            print(f"\n❌ Protected endpoint failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_create_rule(token):
    print_section("TEST 3: CREATE AGENT RULE")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    rule_data = {
        "rule_type": "target_rate",
        "target_rate": 84.5,
        "amount": 50000,
        "source": "USD",
        "target": "INR"
    }
    
    print(f"📝 Creating rule: {json.dumps(rule_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/agents/create",
            json=rule_data,
            headers=headers
        )
        
        print_response(response, "Create Rule")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Rule created!")
            print(f"  Rule ID: {data['rule_id']}")
            return True
        else:
            print(f"\n❌ Rule creation failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_invalid_token():
    print_section("TEST 4: INVALID TOKEN")
    
    headers = {
        "Authorization": "Bearer invalid_token_12345",
        "Content-Type": "application/json"
    }
    
    print("📝 Attempting with invalid token")
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=headers
        )
        
        print_response(response, "Invalid Token")
        
        if response.status_code == 401:
            print(f"\n✅ Correctly rejected invalid token!")
            return True
        else:
            print(f"\n❌ Should have returned 401, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_fx_endpoint():
    print_section("TEST 5: PUBLIC ENDPOINT (No Auth Required)")
    
    print("📝 Accessing FX rate endpoint")
    
    try:
        response = requests.get(
            f"{BASE_URL}/fx/rate?source=USD&target=INR"
        )
        
        print_response(response, "FX Rate")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Public endpoint accessible!")
            print(f"  Rate: {data['rate']} {data['source']}/{data['target']}")
            return True
        else:
            print(f"\n❌ Public endpoint failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("🚀 ASTRA JWT AUTHENTICATION TEST")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Test 1: Public endpoints
    print_section("PRE-CHECK: Server Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print("❌ Server is not responding correctly!")
            print("   Make sure the server is running: python main.py")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Make sure the server is running: python main.py")
        sys.exit(1)
    
    # Run tests
    results = []
    
    # Test 1: Login
    login_result = test_login()
    if login_result:
        results.append(("Login", True))
        token = login_result['access_token']
        
        # Test 2: Protected endpoint
        protected_result = test_protected_endpoint(token)
        results.append(("Protected Endpoint", protected_result))
        
        # Test 3: Create rule
        rule_result = test_create_rule(token)
        results.append(("Create Rule", rule_result))
    else:
        results.append(("Login", False))
        token = None
    
    # Test 4: Invalid token
    invalid_result = test_invalid_token()
    results.append(("Invalid Token", invalid_result))
    
    # Test 5: Public endpoint
    public_result = test_fx_endpoint()
    results.append(("Public Endpoint", public_result))
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! JWT authentication is working correctly!")
    else:
        print("\n⚠️ Some tests failed. Please check the logs above.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()