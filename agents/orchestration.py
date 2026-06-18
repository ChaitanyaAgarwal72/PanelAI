import asyncio
import json
import re
from crewai import Task, Crew, Process

from agents.ethics_agent import create_ethics_agent
from agents.privacy_agent import create_privacy_agent
from agents.methodology_agent import create_methodology_agent
from agents.chair_agent import create_chair_agent

RISK_MAP = {"Low": 1, "Medium": 2, "High": 3}
REVERSE_RISK_MAP = {1: "Low", 2: "Medium", 3: "High"}

def extract_json(output_str):
    """Attempt to extract a JSON block from the agent output."""
    try:
        match = re.search(r'```json\s*(.*?)\s*```', output_str, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(output_str)
    except json.JSONDecodeError:
        return {"risk_level": "Low", "concerns": [], "required_modifications": []}

async def run_agent_task(agent, description, expected_output="JSON object"):
    """Runs a single agent task in a separate thread to allow asyncio.gather."""
    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )
    result = await asyncio.to_thread(crew.kickoff)
    return str(result)

def detect_conflicts(results):
    """
    Detects conflicts between specialist outputs.
    A conflict is defined as a difference >= 2 in risk levels.
    """
    conflicts = []
    agent_names = list(results.keys())
    
    for i in range(len(agent_names)):
        for j in range(i + 1, len(agent_names)):
            name_a = agent_names[i]
            name_b = agent_names[j]
            
            risk_a = RISK_MAP.get(results[name_a].get("risk_level", "Low"), 1)
            risk_b = RISK_MAP.get(results[name_b].get("risk_level", "Low"), 1)
            
            if abs(risk_a - risk_b) >= 2:
                if risk_a > risk_b:
                    responder = name_a
                    target = name_b
                else:
                    responder = name_b
                    target = name_a
                    
                conflicts.append({
                    "responder": responder,
                    "target": target,
                    "responder_concerns": results[responder].get("concerns", []),
                    "target_concerns": results[target].get("concerns", []),
                    "responder_initial_risk": results[responder].get("risk_level", "High"),
                    "target_initial_risk": results[target].get("risk_level", "Low"),
                })
    return conflicts

async def run_review_workflow(proposal_text, llm=None, tracker=None):
    """
    Main orchestration workflow.
    """
    if tracker:
        tracker.on_synthesis_start("Initializing Agents...")

    ethics_agent = create_ethics_agent(llm, tracker)
    privacy_agent = create_privacy_agent(llm, tracker)
    methodology_agent = create_methodology_agent(llm, tracker)
    chair_agent = create_chair_agent(llm)
    
    agents_map = {
        "Ethics Reviewer": ethics_agent,
        "Data Privacy Reviewer": privacy_agent,
        "Methodology Reviewer": methodology_agent
    }
    
    initial_prompt = f"Review the following research proposal:\n\n{proposal_text}"
    
    if tracker:
        tracker.on_agent_status_change("ethics", "Reviewing proposal...")
        tracker.on_agent_status_change("privacy", "Reviewing proposal...")
        tracker.on_agent_status_change("methodology", "Reviewing proposal...")
        
    tasks = [
        run_agent_task(ethics_agent, initial_prompt),
        run_agent_task(privacy_agent, initial_prompt),
        run_agent_task(methodology_agent, initial_prompt)
    ]
    raw_outputs = await asyncio.gather(*tasks)
    
    if tracker:
        tracker.on_agent_status_change("ethics", "Review Complete")
        tracker.on_agent_status_change("privacy", "Review Complete")
        tracker.on_agent_status_change("methodology", "Review Complete")
    
    results = {
        "Ethics Reviewer": extract_json(raw_outputs[0]),
        "Data Privacy Reviewer": extract_json(raw_outputs[1]),
        "Methodology Reviewer": extract_json(raw_outputs[2])
    }
    
    if tracker:
        tracker.on_synthesis_start("Detecting conflicts...")
    conflicts = detect_conflicts(results)
    conflict_responses = []
    
    if conflicts:
        if tracker:
            tracker.on_conflict_detected(conflicts)
            
        resolution_tasks = []
        for conflict in conflicts:
            responder_name = conflict["responder"]
            target_name = conflict["target"]
            responder_agent = agents_map[responder_name]
            
            if tracker:
                tracker.on_resolution_start(responder_name, target_name)
                
            resolution_prompt = f"""You are the {responder_name}. You rated the risk higher than the {target_name}.
Your original concerns: {json.dumps(conflict['responder_concerns'])}
The {target_name} gave a lower risk ({conflict['target_initial_risk']}) and raised these points: {json.dumps(conflict['target_concerns'])}.
Please directly address the {target_name}'s reasoning. Do you still maintain your higher risk assessment? Cite your guidelines if relevant.
Output a brief paragraph directly responding, and state whether you maintain or lower your risk level."""
            
            resolution_tasks.append(
                run_agent_task(responder_agent, resolution_prompt, expected_output="A brief paragraph responding to the conflict and stating the final risk level.")
            )
            
        resolution_raw_outputs = await asyncio.gather(*resolution_tasks)
        for i, conflict in enumerate(conflicts):
            conflict_responses.append({
                "conflict": conflict,
                "response": resolution_raw_outputs[i]
            })
    
    if tracker:
        tracker.on_synthesis_start("Compiling Final Report...")
        
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")

    synthesis_prompt = f"""You are the Chair Agent. Here are the initial reviews from the specialists:

Ethics Reviewer: {json.dumps(results['Ethics Reviewer'])}
Data Privacy Reviewer: {json.dumps(results['Data Privacy Reviewer'])}
Methodology Reviewer: {json.dumps(results['Methodology Reviewer'])}

"""
    if conflict_responses:
        synthesis_prompt += "We had conflicts during the review. Here are the resolution responses:\n"
        for cr in conflict_responses:
            synthesis_prompt += f"\n- {cr['conflict']['responder']} responded to {cr['conflict']['target']}: {cr['response']}"
            
    synthesis_prompt += """\n
Please compile the final report.
Today's date is {CURRENT_DATE_PLACEHOLDER}. Include a report header with this exact placeholder so I can inject the real date later.
Calculate the final verdict by taking a majority vote on the risk level (using any updated levels from the conflict resolution if they lowered their risk).
Preserve any unresolved differences as a "Minority Dissent" section. If you must overrule a specialist, use institutional language such as: "The Chair, after reviewing the conflict, determines that the [Risk Level] risk classification must stand due to the severity of regulatory non-compliance."
The final report must be in Markdown format with an Executive Summary, a Risk Table, Required Modifications, and Citations.

IMPORTANT: At the very end of your response, after the markdown report, you MUST output a JSON code block containing an array of strings representing the final list of citations you used in the report. 
CRITICAL: Do NOT combine or group citations in the JSON list. List each specific article, guideline, or section as a separate, distinct, and highly specific string. 
For example:
```json
{"final_citations": ["GDPR Art. 9(1)", "GDPR Art. 35", "Belmont Report - Informed Consent"]}
```
Do NOT write grouped strings like "GDPR Articles 4, 9, and 35"."""

    raw_final_report = await run_agent_task(chair_agent, synthesis_prompt, expected_output="A comprehensive Markdown report ending with a JSON citations block.")
    
    final_citations = []
    final_report = raw_final_report
    match = re.search(r'```json\s*(.*?)\s*```', raw_final_report, re.DOTALL)
    if match:
        try:
            cit_data = json.loads(match.group(1))
            final_citations = cit_data.get("final_citations", [])
            final_report = raw_final_report[:match.start()].strip()
        except Exception:
            pass
            
    final_report = final_report.replace("{CURRENT_DATE_PLACEHOLDER}", current_date)
    
    if tracker:
        tracker.on_synthesis_start("Report Complete.")
        
    return final_report, results, final_citations
