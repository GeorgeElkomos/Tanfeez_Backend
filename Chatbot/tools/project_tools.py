import json
from crewai.tools import tool
from Chatbot.utils.helpers import _load_project_pages, _load_project_database

@tool
def Update_query_project_pages(query: str) -> str:
    """Append project-page info so agents can make better navigation decisions."""
    query += "\n\nAll the information you need about the pages of the project is this:\n"
    query += _load_project_pages()
    return query

@tool
def Update_query_project_database(query: str) -> str:
    """Append project-database info so agents can make better navigation decisions."""
    query += "\n\nAll the information you need about the database of the project is this:\n"
    query += _load_project_database()
    return query

@tool
def run_query(query: str) -> str:
    """Run a SQL query against the project database and return results as a string."""
    from tools.sql_tool import SQLTool
    sql_tool = SQLTool()
    return sql_tool.execute(query)

@tool
def analyze_and_execute_sql_request(user_request: str) -> str:
    """Analyze user request, understand database schema, build SQL query, and execute it automatically."""
    try:
        schema_info = _load_project_database()
        from tools.sql_tool import SQLTool
        sql_tool = SQLTool()
        guidance = """
        COMMON QUERY PATTERNS FOR THIS DATABASE:
        1. ORDER TOTALS (like calculating total for a specific order):
           - Join Orders, OrderItems, and Products tables
           - Use SUM(p.price * oi.quantity)
           - Example: SELECT SUM(p.price * oi.quantity) AS total \
                     FROM Orders o \
                     JOIN OrderItems oi ON o.order_id = oi.order_id \
                     JOIN Products p ON oi.product_id = p.product_id \
                     WHERE o.order_date = 'YYYY-MM-DD HH:MM:SS'
        2. TABLE RELATIONSHIPS:
           - Orders.order_id → OrderItems.order_id
           - OrderItems.product_id → Products.product_id
           - Orders.user_id → Users.user_id
        3. IMPORTANT COLUMN NAMES:
           - Products: price, product_name
           - OrderItems: quantity, order_id, product_id
           - Orders: order_date, order_id, user_id, status
        """
        context = f"""
        User Request: {user_request}
        Database Schema Information: {schema_info}
        {guidance}
        Based on the user request and the database schema above, construct and execute the appropriate SQL query.
        For order total calculations, remember to JOIN the three tables: Orders, OrderItems, and Products.
        Return both the query executed and the results.
        """
        return f"Database schema loaded with query guidance. User request: {user_request}. Now construct the appropriate SQL query considering the table relationships and execute it using the run_query tool."
    except Exception as e:
        return f"Error analyzing request: {str(e)}"

@tool
def get_sql_query_examples(request_type: str) -> str:
    """Get specific SQL query examples based on the type of request."""
    examples = {
        "order_total": """
        Example for calculating order total by order date:
        SELECT SUM(p.price * oi.quantity) AS total_amount
        FROM Orders o
        JOIN OrderItems oi ON o.order_id = oi.order_id
        JOIN Products p ON oi.product_id = p.product_id
        WHERE o.order_date = '2023-11-01 11:30:00'
        """,
        "order_details": """
        Example for getting order details:
        SELECT o.order_id, o.order_date, p.product_name, p.price, oi.quantity, (p.price * oi.quantity) AS item_total
        FROM Orders o
        JOIN OrderItems oi ON o.order_id = oi.order_id
        JOIN Products p ON oi.product_id = p.product_id
        WHERE o.order_date = '2023-11-01 11:30:00'
        """,
        "user_orders": """
        Example for getting user orders:
        SELECT u.username, o.order_id, o.order_date, o.status
        FROM Users u
        JOIN Orders o ON u.user_id = o.user_id
        WHERE u.username = 'example_user'
        """,
        "product_sales": """
        Example for product sales summary:
        SELECT p.product_name, SUM(oi.quantity) AS total_sold, SUM(p.price * oi.quantity) AS total_revenue
        FROM Products p
        JOIN OrderItems oi ON p.product_id = oi.product_id
        GROUP BY p.product_id, p.product_name
        """
    }
    request_lower = request_type.lower()
    if "total" in request_lower and "order" in request_lower:
        return examples["order_total"]
    elif "order" in request_lower and "detail" in request_lower:
        return examples["order_details"]
    elif "user" in request_lower and "order" in request_lower:
        return examples["user_orders"]
    elif "product" in request_lower and "sales" in request_lower:
        return examples["product_sales"]
    else:
        return examples["order_total"]
