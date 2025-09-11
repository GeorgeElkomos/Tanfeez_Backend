"""
Test script for the new balance report segment APIs
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/accounts-entities"

def test_segments_api():
    """Test getting all unique segments"""
    url = f"{BASE_URL}/balance-report/segments/"
    
    try:
        response = requests.get(url)
        print(f"🔍 Segments API Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error testing segments API: {e}")
        return False

def test_financial_data_api():
    """Test getting financial data for specific segments"""
    url = f"{BASE_URL}/balance-report/financial-data/"
    
    # Test with sample segments from your data
    params = {
        'segment1': '10001',
        'segment2': '2205403', 
        'segment3': 'CTRLCE1'
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"\n💰 Financial Data API Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error testing financial data API: {e}")
        return False

def test_multiple_segments_api():
    """Test getting financial data for multiple segment combinations"""
    url = f"{BASE_URL}/balance-report/financial-data/"
    
    payload = {
        "segments": [
            {
                "segment1": "10001",
                "segment2": "2205403", 
                "segment3": "CTRLCE1"
            },
            {
                "segment1": "10001",
                "segment2": "5041026",
                "segment3": "0000000"
            },
            {
                "segment1": "10191",
                "segment2": "5041025",
                "segment3": "HRCE001"
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n📊 Multiple Segments API Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error testing multiple segments API: {e}")
        return False

def test_filtered_segments_api():
    """Test getting segments with filters"""
    url = f"{BASE_URL}/balance-report/segments/"
    
    # Test filtering by segment1
    params = {'segment1': '10001'}
    
    try:
        response = requests.get(url, params=params)
        print(f"\n🎯 Filtered Segments API Response ({response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error testing filtered segments API: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Balance Report Segment APIs")
    print("="*60)
    
    # Test all unique segments
    segments_ok = test_segments_api()
    
    # Test financial data for specific segments
    financial_ok = test_financial_data_api()
    
    # Test multiple segments
    multiple_ok = test_multiple_segments_api()
    
    # Test filtered segments
    filtered_ok = test_filtered_segments_api()
    
    print("\n" + "="*60)
    print("🎯 Test Results Summary:")
    print(f"✅ Segments API: {'PASS' if segments_ok else 'FAIL'}")
    print(f"✅ Financial Data API: {'PASS' if financial_ok else 'FAIL'}")
    print(f"✅ Multiple Segments API: {'PASS' if multiple_ok else 'FAIL'}")
    print(f"✅ Filtered Segments API: {'PASS' if filtered_ok else 'FAIL'}")
    
    print("\n📝 API Usage Examples:")
    print("1. Get all unique segments:")
    print("   GET /api/accounts-entities/balance-report/segments/")
    
    print("\n2. Get segments filtered by segment1:")
    print("   GET /api/accounts-entities/balance-report/segments/?segment1=10001")
    
    print("\n3. Get financial data for specific segments:")
    print("   GET /api/accounts-entities/balance-report/financial-data/?segment1=10001&segment2=2205403&segment3=CTRLCE1")
    
    print("\n4. Get financial data for multiple segments:")
    print("   POST /api/accounts-entities/balance-report/financial-data/")
    print("   Body: {\"segments\": [{\"segment1\": \"10001\", \"segment2\": \"2205403\", \"segment3\": \"CTRLCE1\"}]}")
