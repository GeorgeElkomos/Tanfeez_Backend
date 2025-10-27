import requests
import json

BASE = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443"
AUTH = ("AFarghaly", "Mubadala345")
H = {"Accept": "application/json", "REST-Framework-Version": "2"}

# Person IDs to test
person_ids = [
    "100000000334881",
    "100000000334882",
    "100000000334886",
    "100000000334895",
    "100000000334898"
]

print("=" * 80)
print("🔍 Testing Person IDs with projectResourceAssignments")
print("=" * 80)

for person_id in person_ids:
    print(f"\n{'─' * 80}")
    print(f"👤 Testing Person ID: {person_id}")
    print(f"{'─' * 80}")
    
    # Test with projectResourceAssignments
    url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments"
    params = {
        "q": f"ResourceId={person_id}",
        "limit": 10
    }
    
    try:
        r = requests.get(url, params=params, auth=AUTH, headers=H, timeout=10)
        print(f"📊 Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            count = data.get('count', 0)
            print(f"✅ SUCCESS - Found {count} assignments")
            
            if count > 0:
                print(f"\n📋 Sample Assignment Data:")
                sample = data['items'][0]
                for key, value in sample.items():
                    if key != 'links':
                        print(f"   • {key}: {value}")
            else:
                print("   ℹ️  No assignments found for this person")
        else:
            print(f"❌ ERROR: {r.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 80)
print("✅ Test Complete")
print("=" * 80)
