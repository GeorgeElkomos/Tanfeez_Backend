import json
import sqlite3
from openai import OpenAI

# ---------- 1. SQL Generation ----------
def generate_sql_query(user_input: str) -> str:
    """
    Generate an SQL query based on user input and table schema using DeepSeek API.
    """
    schema_path = r"AI\System_Infoframtion\tables.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    table_schema = json.dumps(schema_data, indent=2).replace("\n", " ").strip()

    full_prompt = f"""
You are an AI SQL generator. 
Generate a valid SQL query **only** based on the following user input and table schema.

- Do not include explanations, comments, markdown formatting, or any text other than the SQL query itself.
- The output must start directly with the SQL statement (e.g., SELECT, INSERT, UPDATE, DELETE).
- Ensure the SQL syntax is correct and executable.
- Ensure the SQL query is relevant to the provided table schema.
- Ensure the Generated SQL query is complete and includes all necessary fields and is only one SQL statement.
- Ensure the SQL query adds any necessary conditions or filters.

User Input: {user_input}
Table Schema: {table_schema}
    """

    api_key = "sk-10a67facfda84d9d9f2829e5cf9ed10f"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": full_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error generating SQL: {e}")
        return None


# ---------- 2. SQL Execution ----------
def Execute_Sql_Query(sql_query: str) -> str:
    """
    Execute the provided SQL query and return the results in JSON format.
    """
    DB_PATH = "db.sqlite3"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if not sql_query.strip().upper().startswith("SELECT"):
        conn.close()
        return json.dumps({
            "error": "Only SELECT queries are allowed for safety",
            "status": "rejected"
        })

    try:
        cursor.execute(sql_query)
        results = cursor.fetchall()
        results_list = [dict(row) for row in results]
        response = json.dumps({
            "data": results_list,
            "status": "success"
        })
    except Exception as e:
        response = json.dumps({
            "error": str(e),
            "status": "failed"
        })
    finally:
        conn.close()

    return response


# ---------- 3. Result Analysis (Main Pipeline) ----------
def analyze_sql_result(user_request: str) -> str:
    """
    Full pipeline:
    1. Generate SQL query from user request
    2. Execute SQL
    3. Pass results back to DeepSeek for analysis
    """
    print(f"🧠 User Request: {user_request}")

    # Step 1: Generate SQL
    sql_query = generate_sql_query(user_request)
    if not sql_query:
        return "❌ Failed to generate SQL query."

    print(f"📄 Generated SQL: {sql_query}")

    # Step 2: Execute SQL
    sql_result_json = Execute_Sql_Query(sql_query)
    sql_result = json.loads(sql_result_json)

    if sql_result.get("status") != "success":
        return f"❌ Query execution failed: {sql_result.get('error')}"

    # Step 3: Ask model to interpret the result
    analysis_prompt = f"""
You are a data analyst AI. The user asked: "{user_request}"

Here is the SQL query result (in JSON):
{json.dumps(sql_result['data'], indent=2)}

Provide a clear and concise natural language answer based on this data.
"""

    api_key = "sk-10a67facfda84d9d9f2829e5cf9ed10f"
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        analysis_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a data analyst AI."},
                {"role": "user", "content": analysis_prompt},
            ],
        )
        final_answer = analysis_response.choices[0].message.content.strip()
        return final_answer,sql_result
    except Exception as e:
        return f"❌ Error during analysis: {e}"
