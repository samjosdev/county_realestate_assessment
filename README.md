# 🏡 FamilyHomeFinder

**Your Data-Driven Guide to the Best Places to Live**

FamilyHomeFinder is an intelligent real estate analysis platform that helps families find the perfect counties to call home. Using U.S. Census data, advanced scoring algorithms, and AI-powered insights, it generates comprehensive reports comparing states and ranking counties based on your specific family needs and budget.

## ✨ Features

- **🎯 Intelligent County Ranking**: Multi-dimensional scoring system evaluating affordability, family-friendliness, economic vitality, housing stability, and budget compatibility
- **📊 State Comparisons**: Side-by-side analysis of multiple states with top county recommendations
- **👨‍👩‍👧‍👦 Family-Focused**: Considers family size, lifestyle preferences, and priorities in recommendations
- **💰 Budget-Aware**: Adapts analysis based on income levels from affordable to ultra-luxury segments
- **🖼️ Visual Reports**: Rich HTML reports with county images, statistics, and actionable insights
- **🤖 AI-Powered**: Uses Google's Gemini LLM for natural language processing and insight generation
- **📱 User-Friendly Interface**: Clean Gradio web interface with progress tracking

## 🏗️ Architecture

FamilyHomeFinder uses a modern, modular architecture built on LangGraph for workflow orchestration:

```
📁 Project Structure
├── app.py                     # Gradio web interface
├── build_graph.py            # LangGraph workflow orchestration
├── models.py                 # LLM configuration (Gemini)
├── prompts.py                # AI prompt templates
├── tools.py                  # Real estate analysis tools
├── html_formatting.py        # Report generation
├── best_counties_by_state.py # Curated county lists
├── 📁 data_sources/
│   ├── census_api.py         # U.S. Census API integration
│   └── image_apis.py         # Image fetching (Unsplash, Pexels, Wikipedia)
├── 📁 scoring/
│   ├── county_scoring.py     # Multi-dimensional scoring algorithms
│   └── filtering.py          # County filtering and ranking
└── 📁 utils/
    ├── data_processing.py    # Data transformation utilities
    └── user_preferences.py   # User preference parsing
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API keys for:
  - Google Generative AI (Gemini)
  - U.S. Census API
  - Unsplash (optional, for images)
  - Pexels (optional, for images)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/familyhomefinder.git
   cd familyhomefinder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key
   CENSUS_API_KEY=your_census_api_key
   UNSPLASH_ACCESS_KEY=your_unsplash_key  # Optional
   PEXELS_API_KEY=your_pexels_key        # Optional
   SERPER_API_KEY=your_serper_key        # Optional for Google Images
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

   The web interface will be available at `http://localhost:7860`

### Getting API Keys

- **Google Generative AI**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- **U.S. Census API**: Register at [Census.gov](https://api.census.gov/data/key_signup.html)
- **Unsplash**: Create account at [Unsplash Developers](https://unsplash.com/developers)
- **Pexels**: Sign up at [Pexels API](https://www.pexels.com/api/)

## 🎯 How It Works

### 1. User Input Processing
- Family details (income, size, preferences)
- State selection (single or comparison)
- Lifestyle priorities (urban/suburban/rural)
- Main priorities (affordability/investment/safety/balanced)

### 2. Workflow Routing
The system uses LangGraph to route queries through different workflows:

- **Single State Analysis**: Deep dive into one state's counties
- **State Comparison**: Side-by-side analysis of two states
- **Simple Routing**: Form-based input processing (no NLP needed)

### 3. Data Collection
- **Census Data**: Population, income, housing, education statistics
- **Image Data**: County and city images from multiple sources
- **Best Counties**: Curated lists of top-performing counties per state

### 4. Intelligent Scoring
Counties are evaluated across multiple dimensions:

- **Affordability** (0-100): Price-to-income ratios, cost of living
- **Family Friendliness** (0-100): Households with children, income stability, population size
- **Economic Vitality** (0-100): Income levels, education rates, growth potential
- **Housing Stability** (0-100): Homeownership rates, market stability
- **Budget Compatibility** (0-100): Alignment with user's budget tier

### 5. Report Generation
Rich HTML reports featuring:
- Top 5 counties with detailed statistics
- Professional images and visualizations
- AI-generated insights and recommendations
- Budget-specific advice

## 🔧 Configuration

### Budget Tiers
The system automatically detects user budget tiers:

- **Affordable**: < $200,000
- **Move-up**: $200,000 - $500,000
- **Luxury**: $500,000 - $1,000,000
- **Ultra-luxury**: > $1,000,000

### Scoring Weights
Default scoring weights (automatically adjusted based on user priorities):

```python
weights = {
    'affordability': 0.22,
    'family_friendly': 0.23,
    'economic_vitality': 0.20,
    'housing_stability': 0.16,
    'budget_compatibility': 0.19
}
```

## 📊 Data Sources

- **U.S. Census Bureau**: 2022 American Community Survey (ACS) 5-Year Estimates
- **Images**: Unsplash, Pexels, Wikipedia, Google Images (via Serper)
- **Best Counties**: Curated lists based on various quality-of-life metrics

## 🛠️ Development

### Key Components

**LangGraph Workflow** (`build_graph.py`)
- Orchestrates the entire analysis pipeline
- Handles routing between single-state and comparison workflows
- Manages LLM interactions and tool calls

**Scoring Engine** (`scoring/county_scoring.py`)
- Multi-dimensional county evaluation
- Budget tier detection
- Weighted score calculation

**Data Processing** (`utils/data_processing.py`)
- Census data normalization
- Tool result extraction
- Currency and percentage formatting

**Report Generation** (`html_formatting.py`)
- Professional HTML report templates
- Image integration
- Responsive design

### Adding New Features

1. **New Data Sources**: Extend `data_sources/` modules
2. **Scoring Metrics**: Modify `scoring/county_scoring.py`
3. **Report Formats**: Update `html_formatting.py`
4. **Workflow Changes**: Modify `build_graph.py`

### Testing

```bash
# Run basic functionality test
python -c "from tools import real_estate_investment_tool; print(real_estate_investment_tool('06', 'California'))"
```

## 🌐 Deployment

### Local Deployment
```bash
python app.py
```

### Production Deployment

The app is configured for deployment on platforms like:
- **Hugging Face Spaces**
- **Railway**
- **Render**
- **Google Cloud Run**

Environment variables:
```bash
PORT=7860
HOST=0.0.0.0
```

## 📝 Example Usage

### Programmatic Usage

```python
import asyncio
from build_graph import USCensusAgent
from langchain_core.messages import HumanMessage

async def analyze_states():
    # Setup agent
    agent = USCensusAgent()
    graph = await agent.setup_graph()
    
    # Define analysis parameters
    state = {
        "messages": [HumanMessage(content="Find me a good place to buy a house in Oregon")],
        "states": [{"state_name": "Oregon", "fips_code": "41"}],
        "income": "150000",
        "user_preferences": "Family of 4, suburban lifestyle, good schools",
        "needs_followup": False
    }
    
    # Run analysis
    result = await graph.ainvoke(state, config={"configurable": {"thread_id": "test_123"}})
    print(result["final_result"])

# Run the analysis
asyncio.run(analyze_states())
```

### Web Interface Usage

1. **Configure Preferences**: Set family size, income, lifestyle
2. **Select States**: Choose single state or comparison
3. **Generate Report**: Click "Top Counties" and wait 2-7 minutes
4. **Review Results**: Explore ranked counties with insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **U.S. Census Bureau** for comprehensive demographic data
- **Google** for Gemini LLM capabilities
- **Unsplash & Pexels** for beautiful county imagery
- **LangChain & LangGraph** for workflow orchestration
- **Gradio** for the intuitive web interface

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/familyhomefinder/issues)
- **Documentation**: [Project Wiki](https://github.com/yourusername/familyhomefinder/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/familyhomefinder/discussions)

---

**Made with ❤️ for families finding their perfect home**