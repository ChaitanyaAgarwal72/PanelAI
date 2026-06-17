import streamlit as st
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from crewai import LLM
from agents.orchestration import run_review_workflow

st.set_page_config(
    page_title="PanelAI - IRB Reviewer",
    page_icon="⚖️",
    layout="wide"
)

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
            
        with st.spinner("Agents are analyzing the proposal. This may take a minute or two..."):
            try:
                final_report = asyncio.run(run_review_workflow(proposal_text, llm))
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
