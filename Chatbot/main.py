"""
Main entry point for the multi-agent orchestration system (modular version).
"""

import os
import json
import sys
from contextlib import contextmanager
from typing import Dict, List, Any

from crewai import Crew, Process
from Chatbot.agents.manager import manager_agent
from Chatbot.agents.registry import AGENT_REGISTRY, register
from Chatbot.agents.page_navigator import page_navigator_agent
from Chatbot.agents.sql_builder import sql_builder_agent
from Chatbot.agents.general_qa import general_qa_agent
from Chatbot.tasks.manager_task import create_manager_task

# Configuration
OUTPUT_DIR = "./Chatbot/ai-output/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Register agents (if not already registered in their modules)
register(page_navigator_agent, "PageNavigatorAgent")
register(sql_builder_agent, "SQLBuilderAgent")
register(general_qa_agent, "GeneralQAAgent")
register(manager_agent, "ManagerAgent")


def set_global_logging(logs: bool):
    """Globally suppress or enable logging for CrewAI and Python, but not print()."""
    import logging
    if not logs:
        # Only suppress logging, not sys.stdout
        logging.getLogger().setLevel(logging.CRITICAL)
        logging.getLogger("crewai").setLevel(logging.CRITICAL)
    # else:
    #     # Restore logging level if needed (optional, not implemented here)
    #     pass

def check_convergence(history, N=2):
    """Check if the last N non-manager, non-GQA agent responses are identical."""
    if len(history) >= N * 2:
        last_outputs = [
            entry["output"] for entry in reversed(history)
            if entry.get("agent") not in ("ManagerAgent", "GeneralQAAgent")
        ][:N]
        if len(last_outputs) == N and all(r == last_outputs[0] for r in last_outputs):
            return True
    return False

def handle_convergence(history, user_request, final_outputs):
    """Handle the case when convergence is detected and trigger GeneralQAAgent summary."""
    last_agent_result = None
    last_agent_name = None
    for entry in reversed(history):
        agent_name = entry.get("agent")
        if agent_name not in ("GeneralQAAgent", "ManagerAgent"):
            last_agent_result = entry.get("output")
            last_agent_name = agent_name
            break
    if last_agent_result:
        from crewai import Task
        final_task = Task(
            description=(
                f"The following data was calculated by agent '{last_agent_name}':\n{last_agent_result}\n"
                f"Please summarize these results in plain English for the user request: {user_request}.\nDo not repeat the table, but explain what the data means."
            ),
            expected_output="User-friendly summary of the results",
            agent=AGENT_REGISTRY.get("GeneralQAAgent"),
        )
        final_crew = Crew(
            agents=[AGENT_REGISTRY.get("GeneralQAAgent")],
            tasks=[final_task],
            process=Process.sequential,
            verbose=True,
            telemetry=False
        )
        gen_result = final_crew.kickoff()
        final_outputs["GeneralQAAgent"] = str(gen_result)
        history.append({"agent": "GeneralQAAgent", "output": str(gen_result)})
    history.append({"agent": "System", "output": "Convergence detected: repeated identical results. Stopping."})
    return True

def run_manager_agent(user_request, latest_response, history, logs=True):
    """Run the manager agent and return the decision json and updated history."""
    manager_task = create_manager_task({
        "user_request": user_request,
        "latest_response": latest_response,
        "history": json.dumps(history, ensure_ascii=False),
    })
    manager_crew = Crew(
        agents=[manager_agent],
        tasks=[manager_task],
        process=Process.sequential,
        verbose=logs,
        telemetry=False
    )
    manager_result = manager_crew.kickoff()
    decision_json = manager_result.json_dict
    history.append({"agent": "ManagerAgent", "output": decision_json})
    return decision_json, history

def handle_manager_stop(user_request, history, final_outputs, logs=True):
    """Handle the case when the manager agent decides to stop and trigger GeneralQAAgent if needed."""
    if "GeneralQAAgent" not in final_outputs:
        last_agent_result = None
        last_agent_name = None
        for entry in reversed(history):
            agent_name = entry.get("agent")
            if agent_name not in ("GeneralQAAgent", "ManagerAgent"):
                last_agent_result = entry.get("output")
                last_agent_name = agent_name
                break
        from crewai import Task
        if last_agent_result:
            final_task = Task(
                description=(
                    f"The following data was calculated by agent '{last_agent_name}':\n{last_agent_result}\n"
                    f"Please summarize these results in plain English for the user request: {user_request}.\nDo not repeat the table, but explain what the data means."
                ),
                expected_output="User-friendly summary of the results",
                agent=AGENT_REGISTRY.get("GeneralQAAgent"),
            )
        else:
            final_task = Task(
                description=f"Provide a final answer to the user request: {user_request}",
                expected_output="User-friendly summary of the results",
                agent=AGENT_REGISTRY.get("GeneralQAAgent"),
            )
        final_crew = Crew(
            agents=[AGENT_REGISTRY.get("GeneralQAAgent")],
            tasks=[final_task],
            process=Process.sequential,
            verbose=logs,
            telemetry=False
        )
        gen_result = final_crew.kickoff()
        final_outputs["GeneralQAAgent"] = str(gen_result)
    return True

def run_worker_agent(next_agent_name, next_task_description, user_request, final_outputs, history, logs=True):
    """Run the worker agent and update outputs and history."""
    worker_agent = AGENT_REGISTRY.get(next_agent_name)
    if worker_agent is None:
        raise ValueError(f"Unknown agent requested by Manager: {next_agent_name}")
    from crewai import Task
    worker_task = Task(
        description=next_task_description or f"Handle user request: {user_request}",
        expected_output="Complete response to the task",
        agent=worker_agent,
    )
    worker_crew = Crew(
        agents=[worker_agent],
        tasks=[worker_task],
        process=Process.sequential,
        verbose=logs,
        telemetry=False
    )
    worker_result = worker_crew.kickoff()
    agent_response = str(worker_result)
    final_outputs[next_agent_name] = agent_response
    history.append({"agent": next_agent_name, "output": agent_response})
    return agent_response, history

def save_history(history):
    """Save the conversation history to a JSON file."""
    history_file = os.path.join(OUTPUT_DIR, "history.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_responses(final_outputs):
    """Save the agent responses to a JSON file."""
    responses_file = os.path.join(OUTPUT_DIR, "responses.json")
    with open(responses_file, "w", encoding="utf-8") as f:
        json.dump(final_outputs, f, ensure_ascii=False, indent=2)

def end_and_save(history, final_outputs):
    """Save both history and responses at the end of the run."""
    save_history(history)
    save_responses(final_outputs)

@contextmanager
def suppress_stdout():
    """Context manager to suppress stdout (print output) temporarily."""
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    try:
        yield
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout

def orchestrate(user_request: str, logs: bool = True) -> None:
    """Run a full conversation, letting the Manager steer between agents.
    Set logs=False to suppress verbose output from CrewAI agents and crews."""
    final_outputs = {}
    history: List[Dict[str, Any]] = []
    latest_response = ""
    next_agent_name: str = "ManagerAgent"
    stop = False
    next_task_description = ""
    if logs == False:
        set_global_logging(False)  # Set to False to suppress all output
    while not stop:
        if check_convergence(history):
            with suppress_stdout():
                handle_convergence(history, user_request, final_outputs)
            save_history(history)
            break
        if next_agent_name == "ManagerAgent":
            with suppress_stdout():
                decision_json, history = run_manager_agent(user_request, latest_response, history, logs)
            save_history(history)
            stop = decision_json.get("stop", False) or decision_json.get("next_agent") == "END"
            if stop:
                with suppress_stdout():
                    handle_manager_stop(user_request, history, final_outputs, logs)
                end_and_save(history, final_outputs)
                break
            next_agent_name = decision_json["next_agent"]
            next_task_description = decision_json.get("next_task_description", "")
        else:
            with suppress_stdout():
                agent_response, history = run_worker_agent(next_agent_name, next_task_description, user_request, final_outputs, history, logs)
            latest_response = agent_response
            next_agent_name = "ManagerAgent"
    end_and_save(history, final_outputs)
    if logs == False:
        set_global_logging(True)  # Set to False to suppress all output
    return final_outputs


if __name__ == "__main__":
    _user_request = "Navigate me to create a new project"
    print("User Input:",_user_request)
    responce = orchestrate(_user_request, logs=False)
    print("Final outputs:", responce)
