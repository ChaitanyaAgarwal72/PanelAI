from crewai import Agent
import os
from utils.tools import get_retrieve_guidelines_tool

def create_methodology_agent(llm=None):
    """
    Creates and returns the Methodology Agent.
    """
    retrieve_tool = get_retrieve_guidelines_tool("methodology")
    
    backstory = """You are a Methodology Reviewer on an IRB. Your knowledge is strictly limited to the documents you retrieve: a bias compendium, the STROBE checklist for observational studies, and a statistical power guide.

                Instructions:
                1. Query your knowledge base for relevant concepts: e.g., "sampling bias", "power analysis", "STROBE sample size", "confounding".
                2. Identify methodological flaws based ONLY on retrieved content. CRITICAL RULE: You MUST ONLY cite and use sources that you have successfully retrieved from your knowledge base. DO NOT bring in outside knowledge. DO NOT hallucinate rules or guidelines that are not present in your retrieved text.
                3. For each concern, cite the source (e.g., "Bias compendium - Selection bias", "STROBE item 7 - sample size", "Power guide - effect size").
                4. If the study design is not covered by the STROBE checklist (e.g., experimental RCT), note that the checklist may not fully apply but still flag general issues like bias and power.
                5. Output JSON with risk_level, concerns, and required_modifications."""

    agent = Agent(
        role="Methodology Reviewer",
        goal="Assess the scientific quality of the study: sample size justification, presence of bias (selection, measurement, etc.), overall study design validity (using STROBE checklist where applicable), and statistical power considerations.",
        backstory=backstory,
        tools=[retrieve_tool],
        verbose=True,
        allow_delegation=False,
    )
    
    if llm:
        agent.llm = llm
        
    return agent
