# ⚖️ PanelAI: Autonomous IRB Review System

PanelAI is a state-of-the-art Multi-Agent system built with [CrewAI](https://github.com/joaomdmoura/crewAI) and [Streamlit](https://streamlit.io/) designed to simulate an Institutional Review Board (IRB). It autonomously reviews research proposals to ensure they meet strict ethical, privacy, and methodological standards before human trials begin.

## ✨ Key Features

### 🤖 Multi-Agent Architecture
The system employs a hierarchical "panel" of specialized AI agents:
*   **Ethics Agent**: Evaluates participant risk, consent processes, and adherence to the Belmont Report principles.
*   **Privacy Agent**: Scrutinizes data handling, storage, and anonymization against strict frameworks like the GDPR.
*   **Methodology Agent**: Assesses the scientific validity, sample size justification, and checks for cognitive or selection biases.
*   **Chair Agent (Orchestrator)**: Synthesizes the findings of the three specialists. If specialists disagree on the risk level (e.g., Ethics says "Low Risk" but Privacy says "High Risk"), the Chair Agent actively interrogates them, resolves the conflict, and issues a final overarching verdict.

### 📚 Intelligent Citation Explorer (Hybrid RAG)
When the Chair Agent cites a specific rule (e.g., "GDPR Art. 9(1)"), the UI generates clickable buttons for each citation. Clicking a citation triggers a **Hybrid Search** (Vector Embedding + Keyword Filtering) against a local ChromaDB vector database, pulling the *exact* original text of the law or guideline for you to read in a modal popup.

### 💬 "Interrogate the Chair" Chatbot
Disagree with the final verdict? Click the "Chat with Chair" button to open a context-aware chatbot. You can actively debate the Chair Agent, ask for clarifications on required modifications, or request advice on how to improve your proposal's score.

### 📄 Seamless Document Handling
*   **PDF Upload**: Built-in support to upload research proposals as PDFs. Text is automatically extracted using `PyMuPDF`.
*   **PDF Export**: Once the IRB Final Report is generated in Markdown, you can download a beautifully formatted PDF version of the report with a single click using `markdown-pdf`.

## 🛠️ Technology Stack
*   **Backend / LLM Orchestration**: [CrewAI](https://github.com/joaomdmoura/crewAI) & `langchain`
*   **Frontend**: [Streamlit](https://streamlit.io/)
*   **Vector Database (RAG)**: [ChromaDB](https://www.trychroma.com/)
*   **LLM Provider**: Google Gemini (`gemini-3.1-flash-lite`)
*   **PDF Processing**: `PyMuPDF` (fitz), `markdown-pdf`

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_api_key_here
```

### 3. Run the Application
Launch the Streamlit dashboard:
```bash
streamlit run app.py
```

## 🖥️ Using the Dashboard
1. **Upload**: Drag and drop your research proposal PDF into the uploader, or paste plain text.
2. **Review**: Click "Submit for Review". Watch the live command center as the Ethics, Privacy, and Methodology agents process the document simultaneously.
3. **Analyze**: Read the Chair's Final Report. Use the top buttons to toggle the sidebar to either **View Citations** (read the original laws) or **Chat with Chair** (debate the findings).
4. **Export**: Click the "Download Report as PDF" button to save the finalized review.