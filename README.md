---
title: FamilyHomeFinder
app_file: app.py
sdk: gradio
sdk_version: 4.0.0
---
Here’s a comprehensive `README.md` for your project based on the provided files and code. This README aims to make it easy for anyone (including yourself, weeks or months from now) to understand the architecture, workflow, and how to run or extend the code.

---

# 🏡 Real Estate Agent Routing Workflow

A **prototype implementation** of Anthropic’s Agent Routing and Workflow framework, focused on real estate recommendation and comparison for U.S. homebuyers using modern LLMs and multi-agent orchestration (LangGraph).

This system intelligently **routes user queries** to the right workflow (single-state report, multi-state comparison, or fallback), asks follow-up questions for missing info, fetches data from the U.S. Census, and assembles detailed, visual-rich reports—leveraging LLM prompt engineering and external tools.

---

## ✨ Key Features

* **LLM Orchestration:** Uses Gemini (Google Generative AI) models to analyze and route queries, generate follow-up questions, and assemble natural language reports.
* **Agent Routing:** Distinguishes between single-state and multi-state/comparison queries, with a fallback for off-topic questions.
* **Tool-Enhanced:** Calls real estate analysis tools to fetch and process county-level Census data (home value, income, education, etc.).
* **Image Integration:** Pulls in county/city images from Unsplash, Pexels, Google Images, and Wikipedia for highly visual outputs.
* **Interactive Follow-up:** Detects missing key factors (budget, family, lifestyle, growth) and prompts the user for additional details before proceeding.
* **Auto-formatting:** Rich markdown reports with tables, emojis, key takeaways, and “Why you’ll love it” summaries.

---

## 📁 Project Structure

```
.
├── models.py          # LLM setup (Gemini) for supervisor/formatter roles
├── prompts.py         # All prompt templates and instructions for LLMs
├── tools.py           # Real estate data tools, scoring, image fetching, county processing
├── html_formatting.py # HTML report generation and formatting utilities
├── build_graph.py     # Core agent workflow/graph orchestration (LangGraph)
├── app.py             # Gradio web interface
├── cli_app.py         # Command-line interface
└── (data, secrets, etc.)
```

---

## 🚀 How It Works

1. **User Input:** User asks a real estate question (e.g., “Best places to buy a home in Texas vs. Florida for my family?”).
2. **State Extraction:** System uses LLM prompt to parse U.S. state names and decide if it’s a comparison or single-state query.
3. **Follow-up (if needed):** If info is missing (budget, family, etc.), asks targeted, conversational follow-up questions.
4. **Workflow Routing:**

   * **Comparison:** If multiple states, triggers dual tool calls and a comparison workflow.
   * **Single State:** If only one state, routes to the single-state tool/report workflow.
   * **Non-Real Estate:** If off-topic, responds with a friendly message about supported queries.
5. **Tool Calls & Data Fetch:** Queries the U.S. Census and other sources for up-to-date county-level data. Images are fetched via Unsplash/Pexels/Google/Wikipedia APIs.
6. **Scoring & Tagging:** Counties are ranked using affordability, family-friendliness, economic vitality, and more. Each is tagged for features like “great schools” or “luxury housing.”
7. **Rich Output:** Final reports are beautifully formatted in markdown (or HTML), including tables, summaries, images, and actionable advice.

---

## 🛠️ Setup & Usage

### 1. Clone & Install

```bash
git clone <this-repo>
cd <this-repo>
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file with your API keys:

```
GOOGLE_API_KEY=your_gemini_key
CENSUS_API_KEY=your_census_api_key
UNSPLASH_ACCESS_KEY=your_unsplash_key
PEXELS_API_KEY=your_pexels_key
SERPER_API_KEY=your_serper_key  # Google Images (Serper) for richer image results
```

### 3. Run the Agent Workflow

All orchestration is in `build_Graph.py` (see the `USCensusAgent` class and the async `setup_graph()` method). Typical usage in an async context:

```python
from build_Graph import USCensusAgent
import asyncio

agent = USCensusAgent()
graph = asyncio.run(agent.setup_graph())
# ...then invoke with user queries/messages as needed!
```

---

## 🧠 File-by-File Summary

* **models.py**
  Loads LLMs (Gemini) for supervisor and formatter agent roles.
* **prompts.py**
  All the complex prompt templates for routing, follow-up, state extraction, and insights.
* **tools.py**
  Handles:

  * Real estate data fetch (U.S. Census API)
  * County/city image search (Unsplash, Pexels, Google Images, Wikipedia)
  * County scoring and tiering
  * Parsing user preferences
  * Utility functions for filtering/tagging counties
* **html_formatting.py**
  Generates all HTML reports and tables for the web app. Includes key takeaways, tables, emoji summaries, and fallback notes.
* **build_graph.py**
  Orchestrates the entire workflow as a LangGraph. Defines workflow nodes, routing conditions, follow-up/question logic, and calls out to the right tools and HTML formatting at each step.

---

## 🧩 Extending or Customizing

* **Add new tools:** Plug in new data sources or analytics in `tools.py`.
* **Edit prompts:** Tweak how the LLM interprets/routes or assembles outputs via `prompts.py`.
* **Change report look:** Modify `formatting.py` for new sections, themes, or front-end integration.
* **Workflow logic:** For new agent types or more sophisticated routing, extend `build_Graph.py`.

---

## 📝 Example Query

> “Find me a good place to buy a house in West Virginia, with good schools and city amenities.”

**Workflow:**

* Extracts “West Virginia” and FIPS code
* Detects missing info (budget/family size), asks follow-up
* Fetches county data, pulls images, tags/ranks top options
* Returns a markdown/HTML report with 3–5 counties, key stats, images, and friendly advice

---

## 📚 References

* [LangGraph Docs](https://langgraph.dev/)
* [LangChain Docs](https://python.langchain.com/)
* [US Census API](https://www.census.gov/data/developers/data-sets.html)
* [Gemini (Google Generative AI)](https://ai.google.dev/)

---

## 👋 Author & License

*Prototype by \[your name or team]*.
This project is for demonstration and prototyping purposes only.

---

Let me know if you want a *QUICK START* or *DEVELOPER NOTES* section added!
