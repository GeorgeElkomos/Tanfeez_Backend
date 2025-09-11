from crewai import Task
from Chatbot.agents.manager import manager_agent
from Chatbot.agents.registry import AGENT_REGISTRY
from Chatbot.models.schemas import ManagerDecision

def create_manager_task(context):
    description = (
        "# Manager Decision\n\n"
        "## Original user request\n{user_request}\n\n"
        "## Latest agent response\n{latest_response}\n\n"
        "## Conversation history (JSON)\n{history}\n\n"
        "You have the following agents available: "
        + ", ".join(AGENT_REGISTRY.keys()) + ".\n\n"
        "IMPORTANT TASK ASSIGNMENT RULES:\n"
        "- For SQLBuilderAgent: Always instruct them to 'Load database schema, construct the appropriate SQL query with proper JOINs if needed, execute it, and return the actual results'\n"
        "- For order total calculations: Specifically mention 'Calculate using JOIN across Orders, OrderItems, and Products tables'\n"
        "- Never assign just 'build a query' - always require execution and results\n\n"
        "Decide which agent should be called next. "
        "Return STRICTLY valid JSON conforming to this schema:\n"
        "{{\"next_agent\": \"<AgentName or END>\", \"next_task_description\": \"<description>\", \"stop\": <true|false>}}"
    ).format(**context)
    return Task(
        description=description,
        expected_output="ManagerDecision JSON",
        agent=manager_agent,
        output_json=ManagerDecision,
    )
