import requests
import json

BASE = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443"
AUTH = ("AFarghaly", "Mubadala345")
H = {"Accept": "application/json", "REST-Framework-Version": "2"}

assignment_id = "100000000593293"

print("=" * 80)
print("🔍 Testing Assignment ID: " + assignment_id)
print("=" * 80)

# Test 1: Direct GET by Assignment ID
print("\n📋 TEST 1: Direct GET by Assignment ID")
print("─" * 80)
url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments/{assignment_id}"
print(f"URL: {url}")

r = requests.get(url, auth=AUTH, headers=H, timeout=10)
print(f"Status Code: {r.status_code}")
print(f"Response Headers: {dict(r.headers)}")
print(f"Response Body: {r.text[:500]}")

if r.status_code == 200:
    data = r.json()
    print("\n✅ SUCCESS! Assignment Found:")
    print(json.dumps(data, indent=2))
else:
    print(f"\n❌ Not found or error: {r.text}")

# Test 2: Query by AssignmentId
print("\n" + "=" * 80)
print("📋 TEST 2: Query using AssignmentId filter")
print("─" * 80)
url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments"
params = {
    "q": f"AssignmentId={assignment_id}",
    "limit": 10
}
print(f"URL: {url}")
print(f"Params: {params}")

r = requests.get(url, params=params, auth=AUTH, headers=H, timeout=10)
print(f"Status Code: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    count = data.get('count', 0)
    print(f"✅ Query successful! Found {count} records")
    if count > 0:
        print("\nAssignment Data:")
        print(json.dumps(data['items'][0], indent=2))
    else:
        print("ℹ️  No records found with this AssignmentId")
else:
    print(f"❌ Error: {r.text[:300]}")

# Test 3: Get ANY assignments to see what fields are available
print("\n" + "=" * 80)
print("📋 TEST 3: Getting ANY assignments from system")
print("─" * 80)
url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments"
params = {"limit": 5}

r = requests.get(url, params=params, auth=AUTH, headers=H, timeout=10)
print(f"Status Code: {r.status_code}")

if r.status_code == 200:
    data = r.json()
    total_count = data.get('count', 0)
    print(f"✅ Total assignments in system: {total_count}")
    
    if data.get('items'):
        print(f"\n📋 Sample Assignment (to show available fields):")
        sample = data['items'][0]
        print(json.dumps(sample, indent=2))
    else:
        print("\n⚠️  No assignments exist in the system")
        print("   This means the Project Resource Assignment feature may not be configured")
else:
    print(f"❌ Error: {r.text}")

print("\n" + "=" * 80)
print("✅ Test Complete")
print("=" * 80)
