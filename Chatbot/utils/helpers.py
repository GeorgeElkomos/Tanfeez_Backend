import json

def _load_project_pages() -> str:
    with open("./Chatbot/System-Info/Project Pages.json", "r", encoding="utf-8") as f:
        return json.dumps(json.load(f))

def _load_project_database() -> str:
    with open("./Chatbot/System-Info/Database Tables.json", "r", encoding="utf-8") as f:
        return json.dumps(json.load(f))
