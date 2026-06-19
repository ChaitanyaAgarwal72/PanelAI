import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

load_dotenv()

from crewai import LLM
from agents.orchestration import run_review_workflow

st.set_page_config(
    page_title="PanelAI - IRB Reviewer",
    layout="wide"
)

class EventTracker:
    def __init__(self, placeholders, log_container, chair_placeholder):
        self.placeholders = placeholders
        self.log_container = log_container
        self.chair_placeholder = chair_placeholder
        self.ctx = get_script_run_ctx()

    def _inject_ctx(self):
        if self.ctx:
            add_script_run_ctx(ctx=self.ctx)

    def on_agent_status_change(self, agent_id, status_msg, icon=None):
        self._inject_ctx()
        if agent_id in self.placeholders:
            self.placeholders[agent_id].info(status_msg)

    def on_rag_query(self, agent_id, query, results):
        self._inject_ctx()
        with self.log_container:
            with st.expander(f"Search Context: {agent_id.title()} Agent queried '{query}'"):
                st.markdown(f"**Results retrieved:**\n\n{results}")

    def on_conflict_detected(self, conflicts):
        self._inject_ctx()
        self.chair_placeholder.warning(f"Detected {len(conflicts)} conflict(s). Initiating resolution debate...")
        for c in conflicts:
            st.toast(f"Conflict: {c['responder']} vs {c['target']}")

    def on_resolution_start(self, responder, target):
        self._inject_ctx()
        self.chair_placeholder.info(f"Chair Agent instructing {responder} to debate {target}...")

    def on_synthesis_start(self, msg):
        self._inject_ctx()
        self.chair_placeholder.success(f"{msg}")


def main():
    st.title("PanelAI: Multi-Agent IRB Review System")
    st.markdown("Submit your research proposal below. Our specialized AI agents (Ethics, Privacy, and Methodology) will review it against official guidelines and the Chair Agent will synthesize a final report.")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
        st.stop()
        
    llm = LLM(
        model="gemini/gemini-3.1-flash-lite",
        api_key=api_key
    )

    if "final_report" not in st.session_state:
        st.session_state.final_report = None
    if "review_results" not in st.session_state:
        st.session_state.review_results = None

    import fitz
    
    uploaded_file = st.file_uploader("Upload Research Proposal (PDF)", type=["pdf"], accept_multiple_files=False)
    extracted_text = ""
    
    if uploaded_file is not None:
        try:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")

    proposal_text = st.text_area("Research Proposal Details", value=extracted_text, height=300, placeholder="Enter the methodology, participant details, data handling, or upload a PDF above...")

    if st.button("Submit for Review", type="primary"):
        if not proposal_text.strip():
            st.warning("Please enter a research proposal to review.")
            return
            
        st.markdown("---")
        st.markdown("### Live Agent Command Center")
        
        log_container = st.container()
        
        st.markdown("#### Specialist Agents")
        col1, col2, col3 = st.columns(3)
        placeholders = {
            "ethics": col1.empty(),
            "privacy": col2.empty(),
            "methodology": col3.empty()
        }
        
        placeholders["ethics"].info("Ethics Agent: Waiting...")
        placeholders["privacy"].info("Privacy Agent: Waiting...")
        placeholders["methodology"].info("Methodology Agent: Waiting...")
        
        st.markdown("#### Orchestration")
        chair_placeholder = st.empty()
        chair_placeholder.info("Chair Agent: Standing by...")
        
        tracker = EventTracker(placeholders, log_container, chair_placeholder)
        
        try:
            final_report, results, final_citations, conflict_responses = asyncio.run(run_review_workflow(proposal_text, llm, tracker))
            st.session_state.final_report = final_report
            st.session_state.review_results = results
            st.session_state.final_citations = final_citations
            st.session_state.conflict_responses = conflict_responses
            st.success("Review Complete.")
        except Exception as e:
            st.error(f"An error occurred during the review process: {str(e)}")

    if getattr(st.session_state, "conflict_responses", None):
        st.subheader("Live Debate Log")
        for cr in st.session_state.conflict_responses:
            conflict = cr['conflict']
            responder = conflict['responder']
            target = conflict['target']
            response = cr['response']
            
            st.markdown(f"**Conflict Detected:** {responder} ({conflict['responder_initial_risk']}) vs {target} ({conflict['target_initial_risk']})")
            with st.chat_message("user", avatar="👨‍⚖️"):
                st.markdown(f"**Chair Agent asks {responder}:** '{target} rated this risk lower. Do you still maintain your high-risk assessment?'")
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f"**{responder} responds:** '{response}'")
            st.markdown("---")

    if st.session_state.final_report:
        st.subheader("Final IRB Report")
        st.markdown(st.session_state.final_report)
        
        from utils.pdf_generator import markdown_to_pdf_bytes
        pdf_data = markdown_to_pdf_bytes(st.session_state.final_report)
        
        st.download_button(
            label="Download Report as PDF",
            data=pdf_data,
            file_name="IRB_Final_Report.pdf",
            mime="application/pdf"
        )
        
        from utils.tools import fetch_source_text
        
        @st.dialog("Source Document Viewer")
        def open_citation_modal(citation_text):
            st.markdown(f"**Referenced Source:** {citation_text}")
            st.markdown("---")
            with st.spinner("Fetching original text from knowledge base..."):
                source_chunk = fetch_source_text(citation_text)
            st.info(source_chunk)
            
        with st.sidebar:
            st.header("Source Citations Explorer")
            st.markdown("Click any citation below to read the original guideline text.")
            
            citations_to_show = getattr(st.session_state, "final_citations", [])
            
            if citations_to_show:
                for cit in citations_to_show:
                    if st.button(f"View: {cit[:40]}...", key=f"cit_{cit}"):
                        open_citation_modal(cit)
            else:
                st.write("No specific citations were returned for this review.")

if __name__ == "__main__":
    main()
