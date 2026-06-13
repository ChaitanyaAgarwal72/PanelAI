import os
import re
import chromadb
import fitz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DOCS_DIR = os.path.join(BASE_DIR, "source_docs")
CHROMA_DB_DIR = os.path.join(BASE_DIR, "chroma_db")

os.makedirs(CHROMA_DB_DIR, exist_ok=True)

client_ethics = chromadb.PersistentClient(path=os.path.join(CHROMA_DB_DIR, "ethics"))
client_privacy = chromadb.PersistentClient(path=os.path.join(CHROMA_DB_DIR, "privacy"))
client_methodology = chromadb.PersistentClient(path=os.path.join(CHROMA_DB_DIR, "methodology"))

col_ethics = client_ethics.get_or_create_collection(name="ethics_kb")
col_privacy = client_privacy.get_or_create_collection(name="privacy_kb")
col_methodology = client_methodology.get_or_create_collection(name="methodology_kb")

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def add_overlap(chunks, overlap_chars=200):
    """Adds a small overlap from the next chunk to the current chunk."""
    overlapped = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        if i < len(chunks) - 1:
            next_chunk = chunks[i+1].strip()
            dynamic_overlap = min(overlap_chars, len(next_chunk) // 5)
            if dynamic_overlap > 0:
                overlap_text = next_chunk[:dynamic_overlap]
                chunk = chunk + "\n\n--- Overlap with next section ---\n" + overlap_text + "..."
        overlapped.append(chunk)
    return overlapped

def chunk_ethics():
    print("Processing Ethics DB...")
    # 1. Belmont Report (7 chunks)
    belmont_path = os.path.join(SOURCE_DOCS_DIR, "ethics", "the-belmont-report-508c_FINAL.pdf")
    belmont_text = extract_text_from_pdf(belmont_path)
    
    headers = [
        r"A\. Boundaries Between Practice and Research",
        r"1\. Respect for Persons\.",
        r"2\. Beneficence\.",
        r"3\. Justice\.",
        r"1\. Informed Consent\.",
        r"2\. Assessment of Risks and Benefits\.",
        r"3\. Selection of Subjects\."
    ]
    positions = []
    for h in headers:
        match = re.search(h, belmont_text)
        if match:
            positions.append(match.start())
    
    positions.sort()
    positions.append(len(belmont_text))
    
    belmont_chunks = []
    for i in range(len(positions)-1):
        belmont_chunks.append("BELMONT REPORT:\n" + belmont_text[positions[i]:positions[i+1]].strip())
        
    belmont_chunks = add_overlap(belmont_chunks, 150)

    # 2. WMA Helsinki (37 chunks)
    helsinki_path = os.path.join(SOURCE_DOCS_DIR, "ethics", "wma-declaration-of-helsinki.pdf")
    helsinki_text = extract_text_from_pdf(helsinki_path)
    
    raw_helsinki_chunks = re.split(r'\n(?=\d{1,2}\.\s+[A-Z])', helsinki_text)
    helsinki_chunks = []
    for c in raw_helsinki_chunks:
        c = c.strip()
        if re.match(r'^\d{1,2}\.\s+', c):
            helsinki_chunks.append("WMA HELSINKI DECLARATION:\n" + c)

    helsinki_chunks = add_overlap(helsinki_chunks, 100)

    all_ethics_chunks = belmont_chunks + helsinki_chunks
    
    col_ethics.add(
        documents=all_ethics_chunks,
        metadatas=[{"source": "ethics"} for _ in all_ethics_chunks],
        ids=[f"ethics_{i}" for i in range(len(all_ethics_chunks))]
    )
    print(f"Added {len(all_ethics_chunks)} chunks to Ethics DB.")

def chunk_privacy():
    print("Processing Privacy DB...")
    # data_privacy.txt (6 chunks)
    privacy_path = os.path.join(SOURCE_DOCS_DIR, "data_privacy.txt")
    with open(privacy_path, "r", encoding="utf-8") as f:
        privacy_text = f.read()
        
    chunks = re.split(r'-{10,}', privacy_text)
    privacy_chunks = [c.strip() for c in chunks if c.strip()]
    privacy_chunks = add_overlap(privacy_chunks, 150)
    
    col_privacy.add(
        documents=privacy_chunks,
        metadatas=[{"source": "data_privacy.txt"} for _ in privacy_chunks],
        ids=[f"privacy_{i}" for i in range(len(privacy_chunks))]
    )
    print(f"Added {len(privacy_chunks)} chunks to Privacy DB.")

def chunk_methodology():
    print("Processing Methodology DB...")
    
    # 1. biases.txt (7 chunks)
    biases_path = os.path.join(SOURCE_DOCS_DIR, "methodology", "biases.txt")
    with open(biases_path, "r", encoding="utf-8") as f:
        biases_text = f.read()
    
    raw_biases = re.split(r'\n##\s+', biases_text)
    biases_chunks = ["BIASES:\n" + c.strip() for c in raw_biases if c.strip() and not c.strip().startswith('# Research')]
    biases_chunks = add_overlap(biases_chunks, 100)
    
    # 2. STROBE_checklist (Chunk by item number)
    strobe_path = os.path.join(SOURCE_DOCS_DIR, "methodology", "STROBE_checklist_v4_combined.pdf")
    strobe_text = extract_text_from_pdf(strobe_path)
    
    sections = [
        r"Title and abstract\s+1\s+", r"Background/rationale\s+2\s+", r"Objectives\s+3\s+",
        r"Study design\s+4\s+", r"Setting\s+5\s+", r"Participants\s+6\s+", r"Variables\s+7\s+",
        r"Data sources/\s*measurement\s+8\*\s+", r"Bias\s+9\s+", r"Study size\s+10\s+",
        r"Quantitative variables\s+11\s+", r"Statistical methods\s+12\s+", r"Participants\s+13\*\s+",
        r"Descriptive\s*data\s+14\*\s+", r"Outcome data\s+15\*\s+", r"Main results\s+16\s+",
        r"Other analyses\s+17\s+", r"Key results\s+18\s+", r"Limitations\s+19\s+",
        r"Interpretation\s+20\s+", r"Generalisability\s+21\s+", r"Funding\s+22\s+"
    ]
    
    positions = []
    for s in sections:
        match = re.search(s, strobe_text, re.IGNORECASE | re.DOTALL)
        if match:
            positions.append(match.start())
            
    positions.sort()
    positions.append(len(strobe_text))
    
    strobe_chunks = []
    for i in range(len(positions)-1):
        strobe_chunks.append("STROBE CHECKLIST:\n" + strobe_text[positions[i]:positions[i+1]].strip())
    strobe_chunks = add_overlap(strobe_chunks, 150)

    # 3. Power and Sample Size
    power_path = os.path.join(SOURCE_DOCS_DIR, "methodology", "7.7.01__Power_and_Sample_Size.pdf")
    power_text = extract_text_from_pdf(power_path)
    
    headers = [
        r"Large N and Small Effects",
        r"Small N and Large Effects",
        r"Type I errors: Convincing with Small Samples\?"
    ]
    positions = []
    for h in headers:
        match = re.search(h, power_text)
        if match:
            positions.append(match.start())
            
    positions.sort()
    positions.append(len(power_text))
    
    power_chunks = []
    for i in range(len(positions)-1):
        power_chunks.append("POWER AND SAMPLE SIZE:\n" + power_text[positions[i]:positions[i+1]].strip())
    power_chunks = add_overlap(power_chunks, 150)

    all_methodology_chunks = biases_chunks + strobe_chunks + power_chunks
    
    col_methodology.add(
        documents=all_methodology_chunks,
        metadatas=[{"source": "methodology"} for _ in all_methodology_chunks],
        ids=[f"methodology_{i}" for i in range(len(all_methodology_chunks))]
    )
    print(f"Added {len(all_methodology_chunks)} chunks to Methodology DB.")

if __name__ == "__main__":
    chunk_ethics()
    chunk_privacy()
    chunk_methodology()
    print("Vector databases created successfully in chroma_db/ !")
