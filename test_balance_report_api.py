"""
Test script for balance report API endpoints
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/accounts-entities"

def test_balance_report_status():
    """Test getting balance report status"""
    url = f"{BASE_URL}/balance-report/refresh/"
    
    try:
        response = requests.get(url)
        print(f"Status GET Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing status: {e}")
        return False

def test_balance_report_list():
    """Test listing balance report data"""
    url = f"{BASE_URL}/balance-report/list/"
    
    try:
        response = requests.get(url)
        print(f"\nList GET Response ({response.status_code}):")
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Count: {data.get('count', 'N/A')}")
        if 'data' in data and len(data['data']) > 0:
            print("Sample record:")
            print(json.dumps(data['data'][0], indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing list: {e}")
        return False

def test_balance_report_refresh():
    """Test refreshing balance report data"""
    url = f"{BASE_URL}/balance-report/refresh/"
    
    payload = {
        "control_budget_name": "MIC_HQ_MONTHLY"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"\nRefresh POST Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing refresh: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Balance Report API Endpoints")
    print("="*50)
    
    # Test status endpoint
    status_ok = test_balance_report_status()
    
    # Test list endpoint  
    list_ok = test_balance_report_list()
    
    # Test refresh endpoint (commented out to avoid unnecessary Oracle calls)
    # refresh_ok = test_balance_report_refresh()
    
    print("\n" + "="*50)
    print("Test Results:")
    print(f"✅ Status endpoint: {'PASS' if status_ok else 'FAIL'}")
    print(f"✅ List endpoint: {'PASS' if list_ok else 'FAIL'}")
    # print(f"✅ Refresh endpoint: {'PASS' if refresh_ok else 'FAIL'}")
