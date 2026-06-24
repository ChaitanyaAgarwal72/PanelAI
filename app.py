import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

load_dotenv()

from crewai import LLM
from agents.orchestration import run_review_workflow, answer_chair_question

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
    st.title("⚖️ PanelAI - Autonomous IRB Review System")
    st.markdown("Upload a research proposal to have it automatically reviewed by specialized AI agents. Ethics, Privacy, and Methodology agents will review it against official guidelines and the Chair Agent will synthesize a final report.")
    
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
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "active_sidebar_view" not in st.session_state:
        st.session_state.active_sidebar_view = None
    if "widget_key" not in st.session_state:
        st.session_state.widget_key = 0
    if "chatbot_clicked" not in st.session_state:
        st.session_state.chatbot_clicked = False
    if "open_sidebar_trigger" not in st.session_state:
        st.session_state.open_sidebar_trigger = False

    import fitz
    
    uploaded_file = st.file_uploader("Upload Research Proposal (PDF)", type=["pdf"], accept_multiple_files=False, key=f"uploader_{st.session_state.widget_key}")
    
    if f"proposal_{st.session_state.widget_key}" not in st.session_state:
        st.session_state[f"proposal_{st.session_state.widget_key}"] = ""
        
    if uploaded_file is not None and st.session_state.get(f"last_uploaded_{st.session_state.widget_key}") != uploaded_file.name:
        st.session_state[f"last_uploaded_{st.session_state.widget_key}"] = uploaded_file.name
        try:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            st.session_state[f"proposal_{st.session_state.widget_key}"] = text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")

    proposal_text = st.text_area("Research Proposal Details", key=f"proposal_{st.session_state.widget_key}", height=300, placeholder="Enter the methodology, participant details, data handling, or upload a PDF above...")

    col_sub, col_space, col_clear = st.columns([2, 6, 2])
    with col_clear:
        if st.button("Clear Review", type="secondary", use_container_width=True):
            st.session_state.final_report = None
            st.session_state.review_results = None
            st.session_state.chat_history = []
            st.session_state.active_sidebar_view = None
            st.session_state.widget_key += 1
            if "final_citations" in st.session_state:
                del st.session_state.final_citations
            if "conflict_responses" in st.session_state:
                del st.session_state.conflict_responses
            st.rerun()

    with col_sub:
        submit_clicked = st.button("Submit for Review", type="primary", use_container_width=True)
        
    if submit_clicked:
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
        st.markdown("---")
        
        col_chat, col_cit, col_space = st.columns([2, 2, 6])
        with col_chat:
            if st.button("💬 Chat with Chair", use_container_width=True):
                st.session_state.active_sidebar_view = "chat"
                st.session_state.chatbot_clicked = True
                st.session_state.open_sidebar_trigger = True
        with col_cit:
            if st.button("📚 View Citations", use_container_width=True):
                st.session_state.active_sidebar_view = "citations"
                st.session_state.open_sidebar_trigger = True
                
        if not st.session_state.chatbot_clicked:
            st.markdown("""
            <style>
            @keyframes bounce {
                0%, 100% {transform: translateX(0);}
                50% {transform: translateX(-10px);}
            }
            .bouncy-text {
                color: #ff4b4b;
                font-weight: bold;
                animation: bounce 1s infinite;
                display: inline-block;
                margin-top: -30px;
                margin-left: 20px;
            }
            </style>
            <div class='bouncy-text'>☝️ Interrogate the Chair!</div>
            """, unsafe_allow_html=True)
        
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
            if st.session_state.active_sidebar_view == "citations":
                st.header("Source Citations Explorer")
                st.markdown("Click any citation below to read the original guideline text.")
                
                citations_to_show = getattr(st.session_state, "final_citations", [])
                
                if citations_to_show:
                    for cit in citations_to_show:
                        if st.button(f"View: {cit[:40]}...", key=f"cit_{cit}"):
                            open_citation_modal(cit)
                else:
                    st.write("No specific citations were returned for this review.")
            
            elif st.session_state.active_sidebar_view == "chat":
                st.header("💬 Interrogate the Chair")
                st.markdown("Have questions about the final decision? Ask the Chair Agent directly!")
                
                with st.form("chat_form", clear_on_submit=True):
                    prompt = st.text_input("Ask a question about the review...")
                    submitted = st.form_submit_button("Send ⬆️")
                        
                if submitted and prompt:
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    
                    with st.spinner("Chair Agent is thinking..."):
                        response = asyncio.run(answer_chair_question(
                            question=prompt,
                            chat_history=st.session_state.chat_history[:-1], 
                            proposal_text=proposal_text,
                            final_report=st.session_state.final_report,
                            llm=llm
                        ))
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.rerun()
                    
                pairs = []
                for i in range(0, len(st.session_state.chat_history), 2):
                    pairs.append(st.session_state.chat_history[i:i+2])
                
                for pair in reversed(pairs):
                    for msg in pair:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["content"])

    if st.session_state.get("open_sidebar_trigger", False):
        st.session_state.open_sidebar_trigger = False
        st.html("""
            <script>
            const doc = window.parent ? window.parent.document : document;
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            if (sidebar && sidebar.getAttribute('aria-expanded') === 'false') {
                const btn = doc.querySelector('[data-testid="collapsedControl"]');
                if (btn) btn.click();
            }
            </script>
        """)

if __name__ == "__main__":
    main()
