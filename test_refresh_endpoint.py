#!/usr/bin/env python
"""
Simple test to check if the refresh API endpoint is working
"""
import requests
import json

def test_refresh_endpoint():
    """Test the balance report refresh endpoint"""
    url = "http://127.0.0.1:8000/api/accounts-entities/balance-report/refresh/"
    
    # Test data
    payload = {
        "control_budget_name": "MIC_HQ_MONTHLY",
        "Period_name": "sep-25"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing Balance Report Refresh Endpoint")
    print("=" * 50)
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        print("🚀 Sending POST request...")
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response Text: {response.text}")
        elif response.status_code == 400:
            print("❌ BAD REQUEST (400)")
            try:
                data = response.json()
                print(f"Error Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response Text: {response.text}")
        elif response.status_code == 401:
            print("🔒 AUTHENTICATION REQUIRED (401)")
            print("This endpoint requires authentication. You need to:")
            print("1. Login first to get an authentication token")
            print("2. Include the token in the Authorization header")
        elif response.status_code == 500:
            print("💥 INTERNAL SERVER ERROR (500)")
            try:
                data = response.json()
                print(f"Error Response: {json.dumps(data, indent=2)}")
            except:
                print(f"Response Text: {response.text}")
        else:
            print(f"❓ UNEXPECTED RESPONSE ({response.status_code})")
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR")
        print("Make sure the Django server is running on http://127.0.0.1:8000/")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_refresh_endpoint()
