from crewai import Agent
from Chatbot.agents.llm_config import basic_llm
from Chatbot.tools.project_tools import Update_query_project_database, run_query, analyze_and_execute_sql_request, get_sql_query_examples

sql_builder_agent = Agent(
    role="SQL Builder and Executor",
    goal="Construct and execute complex SQL queries accurately, especially JOINs across multiple tables for order calculations and data analysis.",
    backstory=(
        "You are an expert database analyst specializing in e-commerce database queries. "
        "CRITICAL WORKFLOW - You MUST always follow these steps: "
        "1. FIRST: Use Update_query_project_database tool to load the complete database schema "
        "2. SECOND: Analyze the user request and identify which tables need to be joined "
        "3. THIRD: For ORDER TOTAL calculations specifically: "
        "   - Join Orders, OrderItems, and Products tables "
        "   - Use proper column names: Orders.order_date, OrderItems.quantity, Products.price "
        "   - Calculate SUM(Products.price * OrderItems.quantity) "
        "   - Match Orders.order_id = OrderItems.order_id AND OrderItems.product_id = Products.product_id "
        "4. FOURTH: Execute the query using run_query tool "
        "5. ALWAYS return the actual database results, never just explain what should be done "
        "\n"
        "EXAMPLE ORDER TOTAL QUERY PATTERN: "
        "SELECT SUM(p.price * oi.quantity) AS total_amount "
        "FROM Orders o "
        "JOIN OrderItems oi ON o.order_id = oi.order_id "
        "JOIN Products p ON oi.product_id = p.product_id "
        "WHERE o.order_date = '[specific_date_time]' "
        "\n"
        "Remember: Always JOIN the tables correctly and return actual query results, not explanations."
    ),
    llm=basic_llm,
    tools=[Update_query_project_database, run_query, analyze_and_execute_sql_request, get_sql_query_examples],
    verbose=True,
)
