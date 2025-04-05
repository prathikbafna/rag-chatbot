import os
import streamlit as st
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.llms import Ollama
from langchain_community.document_loaders import (
    TextLoader, UnstructuredPDFLoader, UnstructuredWordDocumentLoader
)

# ---- Step 1: Build QA Chain from folder ----
@st.cache_resource
def build_qa_chain(folder_path):
    docs = []
    supported_exts = ['.txt', '.pdf', '.docx']
    splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=20)

    for filename in os.listdir(folder_path):
        path = os.path.join(folder_path, filename)
        ext = os.path.splitext(filename)[1].lower()

        try:
            if ext == '.txt':
                loader = TextLoader(path)
            elif ext == '.pdf':
                loader = UnstructuredPDFLoader(path)
            elif ext == '.docx':
                loader = UnstructuredWordDocumentLoader(path)
            else:
                continue

            raw_docs = loader.load()
            split_docs = splitter.split_documents(raw_docs)
            docs.extend(split_docs)
            st.write(f"✅ Loaded {filename}")
        except Exception as e:
            st.warning(f"❌ Failed to load {filename}: {e}")

    if not docs:
        st.error("⚠️ No valid documents were loaded! Please check the folder.")
        return None

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(docs, embeddings)
    llm = Ollama(model="codellama-7b")  # Change model name if needed
    return RetrievalQA.from_chain_type(llm=llm, retriever=db.as_retriever())

# ---- Step 2: Streamlit UI ----
st.set_page_config(page_title="📚 RAG Chatbot", layout="wide")
st.title("📚 RAG Chatbot using Ollama + LangChain")

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None

# Folder path input
folder_path = st.text_input("📁 Enter your document folder path:", value="my_docs")

# Build assistant
if st.button("🚀 Build Assistant"):
    with st.spinner("Processing documents..."):
        qa_chain = build_qa_chain(folder_path)
        if qa_chain:
            st.session_state.qa_chain = qa_chain
            st.success("✅ Assistant is ready!")

# Info message if not ready
if not st.session_state.qa_chain:
    st.info("⬆️ Please enter a folder and click 'Build Assistant' to start chatting.")

# ---- Step 3: Chat Interface ----
if st.session_state.qa_chain:
    with st.form(key="chat_form"):
        question = st.text_input("❓ Ask your question:")
        submit = st.form_submit_button("Send")

    if submit and question:
        with st.spinner("Thinking..."):
            # Include last few Q&A for recursive context
            if st.session_state.chat_history:
                context = "\n".join(
                    [f"Q: {q}\nA: {a}" for q, a in st.session_state.chat_history[-3:]]
                )
                full_prompt = context + f"\nQ: {question}"
            else:
                full_prompt = question

            answer = st.session_state.qa_chain.run(full_prompt)
            st.session_state.chat_history.append((question, answer))

# Display chat history directly
if st.session_state.chat_history:
    st.markdown("### 💬 Chat History")
    for q, a in st.session_state.chat_history:
        st.markdown(f"**🧑‍💻 Q:** {q}")
        st.markdown(f"**🤖 A:** {a}")
        st.markdown("---")  # Separator


# Clear chat button
if st.button("🧹 Clear Chat"):
    st.session_state.chat_history = []
    st.experimental_rerun()
