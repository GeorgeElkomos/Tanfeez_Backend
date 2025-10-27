import requests
import json

BASE = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443"
AUTH = ("AFarghaly", "Mubadala345")
H = {"Accept": "application/json", "REST-Framework-Version": "2"}

person_ids = [
    "100000000334881",
    "100000000334882", 
    "100000000334886",
    "100000000334895",
    "100000000334898"
]

print("=" * 80)
print("🔍 COMPREHENSIVE TEST - Multiple Endpoints")
print("=" * 80)

# Test 1: Get all resource assignments to see field structure
print("\n" + "=" * 80)
print("📋 TEST 1: Getting sample resource assignments (any person)")
print("=" * 80)
url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments"
r = requests.get(url, params={"limit": 3}, auth=AUTH, headers=H)
if r.status_code == 200:
    data = r.json()
    count = data.get('count', 0)
    print(f"✅ Total assignments in system: {count}")
    if data.get('items'):
        print(f"\n📋 Sample assignment fields:")
        sample = data['items'][0]
        for key in sorted(sample.keys()):
            if key != 'links':
                print(f"   • {key}: {sample[key]}")

# Test 2: Check persons endpoint
print("\n" + "=" * 80)
print("📋 TEST 2: Checking if these are valid Person IDs")
print("=" * 80)
for person_id in person_ids:
    # Try persons endpoint
    url = f"{BASE}/fscmRestApi/resources/11.13.18.05/persons/{person_id}"
    r = requests.get(url, auth=AUTH, headers=H, timeout=5)
    print(f"Person {person_id}: Status {r.status_code}", end="")
    if r.status_code == 200:
        data = r.json()
        print(f" - ✅ {data.get('DisplayName', 'N/A')} ({data.get('PersonNumber', 'N/A')})")
    else:
        print(f" - ❌ Not found")

# Test 3: Check project team members
print("\n" + "=" * 80)
print("📋 TEST 3: Checking project team members")
print("=" * 80)
url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectTeamMembers"
r = requests.get(url, params={"limit": 2}, auth=AUTH, headers=H)
print(f"Team Members endpoint status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Total team members: {data.get('count', 0)}")
    if data.get('items'):
        print(f"\nSample team member fields:")
        sample = data['items'][0]
        for key in sorted(sample.keys()):
            if key != 'links':
                print(f"   • {key}: {sample[key]}")

# Test 4: Try to find them by PersonNumber
print("\n" + "=" * 80)
print("📋 TEST 4: Testing resource assignments with different ID formats")
print("=" * 80)

# First get a person number mapping
print("\nTrying to map Person IDs to Person Numbers...")
person_mappings = {}
for person_id in person_ids[:2]:  # Just test first 2
    url = f"{BASE}/fscmRestApi/resources/11.13.18.05/persons/{person_id}"
    r = requests.get(url, auth=AUTH, headers=H, timeout=5)
    if r.status_code == 200:
        data = r.json()
        person_number = data.get('PersonNumber')
        if person_number:
            person_mappings[person_id] = person_number
            print(f"   {person_id} → PersonNumber: {person_number}")

print("\n" + "=" * 80)
print("✅ Test Complete")
print("=" * 80)
