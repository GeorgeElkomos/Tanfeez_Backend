from crewai import Agent
from typing import Dict
from Chatbot.agents.llm_config import basic_llm

AGENT_REGISTRY: Dict[str, Agent] = {}

def register(agent: Agent, agent_name: str = None) -> Agent:
    name = agent_name or agent.role
    AGENT_REGISTRY[name] = agent
    return agent
