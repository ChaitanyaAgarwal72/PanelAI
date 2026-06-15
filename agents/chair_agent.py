from crewai import Agent

def create_chair_agent(llm=None):
    """
    Creates and returns the Chair Agent (Synthesizer).
    """
    backstory = """You are the Chair of an Institutional Review Board (IRB). 
You manage the review workflow, synthesize the findings of specialist reviewers (Ethics, Privacy, Methodology), and compile a final structured report.
You do not query databases yourself; you rely entirely on the provided initial reviews and any conflict resolution responses from your specialists."""

    agent = Agent(
        role="IRB Chair and Synthesizer",
        goal="Synthesize the findings of all specialist reviewers, handle any unresolved differences as 'Minority Dissent', and compile a comprehensive final report in markdown format. The report must include an executive summary, a risk table, required modifications, and citations.",
        backstory=backstory,
        tools=[],
        verbose=True,
        allow_delegation=False,
    )
    
    if llm:
        agent.llm = llm
        
    return agent
