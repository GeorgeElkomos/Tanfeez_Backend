import requests

BASE = "https://hcbg-dev4.fa.ocs.oraclecloud.com:443"
AUTH = ("AFarghaly", "Mubadala345")
H = {"Accept": "application/json", "REST-Framework-Version": "2"}

def get_task_assignments(person_number):
    url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectResourceAssignments"
    
    # Try with the actual Person ID
    test_queries = [
        f"ResourceId={person_number}",
        f"PersonId={person_number}",
    ]
    
    for test_q in test_queries:
        params = {"q": test_q, "limit": 5}
        print(f"\n🔍 Testing query: {test_q}")
        r = requests.get(url, params=params, auth=AUTH, headers=H)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            result = r.json()
            print(f"   ✅ SUCCESS! Count: {result.get('count', 0)}")
            if result.get('items'):
                print(f"   Sample item keys: {list(result['items'][0].keys())}")
                print(f"   Full response: {result}")
            return {"mode": "assignments", "items": result.get("items", [])}
        else:
            print(f"   ❌ Error: {r.text[:200]}")
    
    print("\n⚠️  None of the queries worked, trying without filter...")
    params = {
        "limit": 5  # Just get 5 records to see structure
    }
    print(f"🔍 Request URL: {url}")
    print(f"🔍 Request Params: {params}")
    try:
        r = requests.get(url, params=params, auth=AUTH, headers=H)
        print(f"✅ Status Code: {r.status_code}")
        print(f"📄 Response Headers: {dict(r.headers)}")
        print(f"📝 Response Body: {r.text[:1000]}")  # First 1000 chars
        if r.status_code == 200:
            return {"mode": "assignments", "items": r.json().get("items", [])}
        else:
            print(f"❌ ERROR: Got status {r.status_code}")
            return {"mode": "error", "status_code": r.status_code, "response": r.text}
    except requests.RequestException as e:
        print(f"Error fetching task assignments: {e}")
    # Fallback to team members + tasks
    tm_url = f"{BASE}/fscmRestApi/resources/11.13.18.05/projectTeamMembers"
    tm_params = {
        "q": f"PersonNumber={person_number};TeamMemberStatusCode=ACTIVE",
        "fields": "ProjectId,ProjectNumber,ProjectName,PersonNumber",
        "limit": 500
    }
    print("\n🔄 Fetching team members...")
    tm_response = requests.get(tm_url, params=tm_params, auth=AUTH, headers=H)
    print(f"✅ Team Members Status: {tm_response.status_code}")
    print(f"📝 Team Members Response: {tm_response.text[:1000]}")
    
    if tm_response.status_code != 200:
        print(f"❌ ERROR: Team members API failed with {tm_response.status_code}")
        return {"mode": "error", "status_code": tm_response.status_code, "response": tm_response.text}
    
    tm = tm_response.json().get("items", [])
    rows = []
    for t in tm:
        purl = f"{BASE}/fscmRestApi/resources/11.13.18.05/projects/{t['ProjectId']}/child/tasks"
        p = requests.get(purl, params={"fields":"TaskNumber,Name,TaskId,StatusCode","limit":1000}, auth=AUTH, headers=H)
        if p.status_code == 200:
            for task in p.json().get("items", []):
                rows.append({
                    "ProjectNumber": t["ProjectNumber"],
                    "ProjectName": t["ProjectName"],
                    "TaskNumber": task["TaskNumber"],
                    "TaskName": task["Name"],
                    "StatusCode": task.get("StatusCode")
                })
    return {"mode": "team+tasks", "items": rows}

get_task_assignments("100000000334881")
