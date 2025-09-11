from crewai import Agent
from Chatbot.agents.llm_config import basic_llm

manager_agent = Agent(
    role="Manager",
    goal="Coordinate worker agents, evaluate their responses, and decide the optimal next step until the user's request is satisfied.",
    backstory=(
        "You are the senior orchestrator. You analyse the original user request, the latest agent output, and overall history. "
        "You then decide which registered agent should act next and what their task description should be. "
        "When you believe the user has what they need, return a decision with stop=true or next_agent=END."
    ),
    llm=basic_llm,
    verbose=True,
)
