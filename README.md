# fintrack-ai

A multi-agent financial tracking and advice system built with CrewAI, LangChain, Chroma, and SQLite.

## Features

- `Bookkeeper` agent for expense logging and summaries
- `Market Analyst` agent for market research and pricing insights
- `Financial Advisor` agent for budgeting recommendations
- RAG integration using Chroma and OpenAI embeddings for personal goals and bank statement queries
- Local SQLite expense database for transaction capture
- Optional Serper web search integration for market data

## Setup

1. Install Python 3.12 using Homebrew:

```bash
brew install python@3.12
```

2. Create and activate the project virtual environment:

```bash
/opt/homebrew/bin/python3.12 -m venv venv312
source venv312/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.

```bash
cp .env.example .env
```

5. Optionally set `SERPER_API_KEY` if you want market search integration.

## Run

```bash
source venv312/bin/activate
python main.py
```

Then enter a financial prompt like:

- `Log a $45 lunch expense and tell me whether my spending is on track.`
- `Compare current mortgage rates with personal goals and suggest a saving plan.`
- `Summarize my recent expenses and check if I can save 20% more this month.`

## Notes

- The SQLite ledger is stored in `db/expenses.db`.
- The Chroma RAG index is stored in `db/chroma`.
- The system uses an interactive `main.py` prompt to demonstrate CrewAI task execution.
