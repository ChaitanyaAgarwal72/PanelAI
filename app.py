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
    page_icon="⚖️",
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

    def on_agent_status_change(self, agent_id, status_msg, icon):
        self._inject_ctx()
        if agent_id in self.placeholders:
            self.placeholders[agent_id].info(f"{icon} {status_msg}")

    def on_rag_query(self, agent_id, query, results):
        self._inject_ctx()
        with self.log_container:
            with st.expander(f"🔍 {agent_id.title()} Agent searched: '{query}'"):
                st.markdown(f"**Results retrieved:**\n\n{results}")

    def on_conflict_detected(self, conflicts):
        self._inject_ctx()
        self.chair_placeholder.warning(f"⚠️ Detected {len(conflicts)} conflict(s). Initiating resolution debate...")
        for c in conflicts:
            st.toast(f"Conflict: {c['responder']} vs {c['target']}", icon="⚠️")

    def on_resolution_start(self, responder, target):
        self._inject_ctx()
        self.chair_placeholder.info(f"👨‍⚖️ Chair Agent instructing {responder} to debate {target}...")

    def on_synthesis_start(self, msg):
        self._inject_ctx()
        self.chair_placeholder.success(f"👨‍⚖️ {msg}")


def main():
    st.title("⚖️ PanelAI: Multi-Agent IRB Review System")
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

    proposal_text = st.text_area("Research Proposal Details", height=300, placeholder="Enter the methodology, participant details, data handling, etc...")

    if st.button("Submit for Review", type="primary"):
        if not proposal_text.strip():
            st.warning("Please enter a research proposal to review.")
            return
            
        st.markdown("---")
        st.markdown("### 📡 Live Agent Command Center")
        
        log_container = st.container()
        
        st.markdown("#### Specialist Agents")
        col1, col2, col3 = st.columns(3)
        placeholders = {
            "ethics": col1.empty(),
            "privacy": col2.empty(),
            "methodology": col3.empty()
        }
        
        placeholders["ethics"].info("💤 Ethics Agent waiting...")
        placeholders["privacy"].info("💤 Privacy Agent waiting...")
        placeholders["methodology"].info("💤 Methodology Agent waiting...")
        
        st.markdown("#### Orchestration")
        chair_placeholder = st.empty()
        chair_placeholder.info("👨‍⚖️ Chair Agent standing by...")
        
        tracker = EventTracker(placeholders, log_container, chair_placeholder)
        
        try:
            final_report = asyncio.run(run_review_workflow(proposal_text, llm, tracker))
            st.session_state.final_report = final_report
            st.success("Review Complete!")
        except Exception as e:
            st.error(f"An error occurred during the review process: {str(e)}")

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

if __name__ == "__main__":
    main()
