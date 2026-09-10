# GovAssist AI – Government Scheme Assistant Agent

GovAssist AI is a professional academic project that helps citizens discover government scholarships, financial schemes, government jobs, and skill-based opportunities using AI-assisted matching and a multi-agent workflow.

## Features

- Multi-agent LangGraph workflow
- LangChain prompt + retrieval architecture
- ReAct, CoT, and ToT planning support
- FAISS persistent memory and similarity search
- Government scheme and scholarship discovery
- Government job and vacancy dashboard
- Resume and career matching
- Deadline tracker with SQLite persistence
- Multimodal upload support for PDF, DOCX, TXT, image, and audio
- Demo mode without API key

## Architecture

- Streamlit frontend for dashboard and modules
- LangGraph workflow for planner, researcher, matcher, verifier, memory, and responder
- FAISS persistent vector memory for query retrieval
- SQLite database for application and profile tracking
- JSON knowledge base for scholarships, jobs, skills, and schemes

## Technologies

- Streamlit
- LangChain
- LangGraph
- FAISS
- SQLite
- Python
- Groq (optional via .env)
- pypdf and python-docx

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

## Demo mode

The app works without an API key.

Set `GROQ_API_KEY` in a `.env` file when you want active LLM-backed reasoning.

## Important safety note

Opportunity information shown here is for guidance/demo purposes. Always verify the latest eligibility, deadline, documents and application procedure on the official government notification or portal.

## Project modules

1. AI Assistant + Multimodal Chatbot
2. Scholarships & Financial Schemes
3. Government Jobs & Vacancies
4. Resume & Career Matcher
5. Application & Deadline Tracker
6. Personalized Opportunity Finder

## Academic mapping

- Government Scheme Assistant Agent: AI Assistant + opportunity recommender
- LangChain: prompt/retrieval-based reasoning
- LangGraph: multi-agent workflow
- ReAct: observe -> reason -> act
- CoT: structured eligibility reasoning
- ToT: multiple path planning
- FAISS: persistent memory similarity search
- SQLite: application and profile persistence

## Limitations

- Demo data is educational, not official live government data
- Real LLM integration requires a valid API key
- Final eligibility must still be verified on official portals
