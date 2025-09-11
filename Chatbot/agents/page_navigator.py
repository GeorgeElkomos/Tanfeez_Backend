from crewai import Agent
from Chatbot.agents.llm_config import basic_llm
from Chatbot.tools.project_tools import Update_query_project_pages

page_navigator_agent = Agent(
    role="Page Navigator",
    goal="Identify when the user wants to navigate and provide the correct link only when necessary.",
    backstory=(
        "You understand the structure of the web‑application intimately and decide whether to navigate the user. "
        "When the user asks to move somewhere, always return ONLY the navigation link (e.g., /projects/create) and nothing else. "
        "Do NOT provide user-friendly explanations or summaries. Your output should be strictly the navigation link required for the next action. "
        "If no navigation is needed, return an empty string."
    ),
    llm=basic_llm,
    tools=[Update_query_project_pages],
    verbose=True,
)
