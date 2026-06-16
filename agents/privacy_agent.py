from crewai import Agent
import os
from utils.tools import get_retrieve_guidelines_tool

def create_privacy_agent(llm=None):
    """
    Creates and returns the Data Privacy Agent.
    """
    retrieve_tool = get_retrieve_guidelines_tool("privacy")
    
    backstory = """You are a Data Privacy Reviewer on an IRB. Your sole authority comes from the 
                    GDPR articles and recitals provided by your 'retrieve_guidelines' tool.

                    Instructions:
                    1. Retrieve relevant guidelines using queries like "biometric data", "consent", "data protection impact assessment", "purpose limitation".
                    2. Identify privacy concerns based STRICTLY on the retrieved text. CRITICAL RULE: You MUST ONLY cite and use sources that you have successfully retrieved from your knowledge base. DO NOT bring in outside knowledge. DO NOT hallucinate rules or guidelines that are not present in your retrieved text.
                    3. Cite the exact article/recital for each concern (e.g., "GDPR Art. 9(1) prohibits processing of biometric data...").
                    4. If the proposal mentions data types not covered by your guidelines (e.g., purely anonymized non-personal data), you may note it's outside scope but do not invent rules.
                    5. Output JSON with risk_level, concerns, and required_modifications."""

    agent = Agent(
        role="Data Privacy Reviewer",
        goal="Check the proposal's data handling against GDPR Articles 4, 5, 9, 35 and Recitals 51, 71. Focus on: lawfulness, purpose limitation, data minimization, special categories (biometric/health data), DPIA requirement, and rights of data subjects.",
        backstory=backstory,
        tools=[retrieve_tool],
        verbose=True,
        allow_delegation=False,
    )
    
    if llm:
        agent.llm = llm
        
    return agent
