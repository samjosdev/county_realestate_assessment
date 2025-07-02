from langchain_core.prompts import PromptTemplate

# FIPS code mapping context
FIPS_CONTEXT = """
Alabama: 01, Alaska: 02, Arizona: 04, Arkansas: 05, California: 06,
Colorado: 08, Connecticut: 09, Delaware: 10, Florida: 12, Georgia: 13,
Hawaii: 15, Idaho: 16, Illinois: 17, Indiana: 18, Iowa: 19,
Kansas: 20, Kentucky: 21, Louisiana: 22, Maine: 23, Maryland: 24,
Massachusetts: 25, Michigan: 26, Minnesota: 27, Mississippi: 28,
Missouri: 29, Montana: 30, Nebraska: 31, Nevada: 32, New Hampshire: 33,
New Jersey: 34, New Mexico: 35, New York: 36, North Carolina: 37,
North Dakota: 38, Ohio: 39, Oklahoma: 40, Oregon: 41, Pennsylvania: 42,
Rhode Island: 44, South Carolina: 45, South Dakota: 46, Tennessee: 47,
Texas: 48, Utah: 49, Vermont: 50, Virginia: 51, Washington: 52,
West Virginia: 54, Wisconsin: 55, Wyoming: 56
"""

# Note: STATE_FIPS_EXTRACTION_PROMPT removed - was unused duplicate of MULTI_STATE_FIPS_EXTRACTION_PROMPT

MULTI_STATE_FIPS_EXTRACTION_PROMPT = '''
Extract all U.S. states mentioned in the following query. For each, return the state name and FIPS code as a list of dictionaries under the key 'states'.

Format:
{{
  "states": [
    {{"state_name": "Texas", "fips_code": "48"}},
    {{"state_name": "Florida", "fips_code": "12"}}
  ]
}}

Query: {query}
Context: {context}
'''
# Follow-up questions prompt
FOLLOWUP_QUESTIONS_PROMPT = PromptTemplate(
    template="""
You are a helpful real estate assistant. Analyze the user's query to determine which of these 4 ESSENTIAL areas are missing or unclear:

USER QUERY: "{user_query}"

**ANALYSIS CHECKLIST:**
1. **Budget/Income** - Is there a clear household income, budget range, or affordability level mentioned?
2. **Family-Friendliness** - Is family size, number of children, school priorities, or safety concerns mentioned?
3. **Urban vs. Rural Lifestyle** - Is there a clear preference for city, suburbs, small towns, or rural areas?
4. **Long-Term Growth Potential** - Are job opportunities, economic growth, or investment timeline mentioned?

**TASK:** Ask targeted follow-up questions ONLY for the missing areas. Always ask at least 2-3 questions to cover gaps.

**QUESTION TEMPLATES:**
- Budget missing → "What's your household income range or budget for housing costs?"
- Family missing → "Tell me about your family - how many children and what are your priorities (schools, safety, amenities)?"
- Lifestyle missing → "Do you prefer urban areas with city amenities, suburban communities, or smaller rural towns?"
- Growth missing → "Are you looking for strong job markets and economic growth, or is affordability your main priority?"

**OUTPUT FORMAT:**
"To provide you with the most tailored recommendations, I need to understand a few more details:

1. [Question about missing area 1]
2. [Question about missing area 2]
3. [Question about missing area 3 if needed]

Please share these preferences so I can find the perfect match for your needs."

Make the questions conversational and specific to their query context.
""",
    input_variables=["user_query"],
)

# Single State Insights and Recommendations Prompt
SINGLE_STATE_INSIGHTS_PROMPT = PromptTemplate(
    template="""
You are a friendly real estate advisor. Create engaging insights and recommendations for a family with ${income} income looking in {state_name}.

Summary: {summary}
Tool Data: {tool_output}
User Preferences: {user_preferences}

Write in a warm, personal style with emojis. Focus on their buying power, lifestyle choices, and family priorities.

Format your response exactly as:
Insights: 
💸 [Point about their income/buying power - make it empowering]

🏘️ [Point about lifestyle choices/variety available]

👨‍👩‍👧‍👦 [Point about family-friendly aspects]

Recommendation:
🔹 [First recommendation with specific guidance]

🔹 [Second recommendation with specific guidance]

🎯 [Closing advice that's encouraging and actionable]

Example style:
💸 Your income gives you serious buying power. With $150k/year, homes that strain others' budgets are well within reach.
🏘️ Pick your pace: From booming metros to relaxed, affordable towns, {state_name} gives families room to choose.
👨‍👩‍👧‍👦 Family is built in. All top counties show strong indicators of family life and safe communities.

🔹 Big-City Life with Upside? Choose [county]. Yes, prices are higher — but so is opportunity.
🔹 Want Space & Savings? [County] offers big cost breaks and great environments for raising kids.
🎯 You've got options. Use this report as your launchpad — then zoom into local details.
""",
    input_variables=["state_name", "summary", "tool_output", "income", "user_preferences"]
)

# State Comparison Insights and Recommendations Prompt  
COMPARISON_INSIGHTS_PROMPT = PromptTemplate(
    template="""
You are a friendly real estate advisor. Create engaging insights and recommendations comparing {state1} vs {state2} for a family with ${income} income.

Summary: {summary}
Tool Data: {tool_output}
User Preferences: {user_preferences}

Write in a warm, personal style with emojis. Focus on their buying power, lifestyle differences, and family priorities.

Format your response exactly as:
Takeaways:
💸 [Point about their income/buying power in both states - make it empowering]

🏘️ [Point about lifestyle differences between the states]

👨‍👩‍👧‍👦 [Point about family-friendly aspects and differences]

Recommendation:
🔹 [First recommendation with specific state/county guidance]

🔹 [Second recommendation with specific state/county guidance]

🎯 [Closing advice that's encouraging and actionable]

Example style:
💸 Your ${income} income gives you flexibility in both states, but your dollar goes further in [state].
🏘️ {state1} offers [lifestyle], while {state2} provides [different lifestyle] — pick your pace.
👨‍👩‍👧‍👦 Both states show family-friendly communities, but [state] edges ahead in [specific area].

🔹 Choose {state1} if you want [specific benefit]. Top picks: [counties].
🔹 Go with {state2} if you prioritize [different benefit]. Focus on: [counties].
🎯 You can't go wrong with either choice. Let your lifestyle priorities guide the final decision.
""",
    input_variables=["state1", "state2", "summary", "tool_output", "income", "user_preferences"]
)

# Removed ROUTE_AND_PARSE_PROMPT - unused

# Non-real estate query response template
NON_REAL_ESTATE_RESPONSE = """I'm a specialized real estate analysis agent focused on helping families find the best places to buy homes in US states. 

Your query: "{user_query}"

I can help you with:
• Real estate market analysis for specific US states
• Comparing states for real estate investment
• Finding family-friendly counties with good home values
• Analyzing median home prices and household incomes by state

Please ask me about real estate markets, property values, or housing data for specific US states. For example:
- "Show me real estate data for Texas"
- "Compare California vs Texas for real estate"
- "Best counties in Florida for a family of four"
"""

# Tool call generation prompts
SINGLE_STATE_TOOL_CALL_PROMPT = """You are helping a family find the best counties for real estate investment in a specific state.

Based on the extracted state information, you need to call the real_estate_investment_tool to get county data.

State Information: {state_info}
State Name: {state_name}
State FIPS: {state_fips}

Call the real_estate_investment_tool with the following parameters:
- state_fips: {state_fips}
- state_name: {state_name}
- filter_bucket: default

Use the tool to get the county data for this state."""

COMPARISON_TOOL_CALL_PROMPT = """You are helping a family compare real estate investment opportunities between two states.

Based on the extracted state information, you need to call the real_estate_investment_tool for both states to get county data for comparison.

State 1 Information: {state1_info}
State 1 Name: {state1_name}
State 1 FIPS: {state1_fips}

State 2 Information: {state2_info}
State 2 Name: {state2_name}
State 2 FIPS: {state2_fips}

Call the real_estate_investment_tool twice:
1. For {state1_name} with state_fips: {state1_fips}, state_name: {state1_name}, filter_bucket: default
2. For {state2_name} with state_fips: {state2_fips}, state_name: {state2_name}, filter_bucket: default

Use the tool to get county data for both states so we can compare them."""

# Four factors parsing prompt (after user responds to follow-up)
PARSE_FOUR_FACTORS_PROMPT = PromptTemplate(
    template="""
You are an expert analyst. Parse the user's complete conversation to populate the 4 key factors for real estate recommendations.

ORIGINAL QUERY: "{original_query}"
USER FOLLOWUP RESPONSE: "{user_response}"

**THE 4 FACTORS TO POPULATE:**
1. **Budget/Income** - Extract or default to $150,000
2. **Family Situation** - Extract family details or default to "family-friendly communities"  
3. **Lifestyle Preference** - Extract urban/suburban/rural preference or default to "mixed communities with good amenities"
4. **Growth Priorities** - Extract economic priorities or default to "balanced affordability and stability"

**INSTRUCTIONS:**
- Extract information when clearly stated
- Make reasonable inferences from context
- Use defaults when information is missing
- For income, convert to annual dollar amount (e.g., "120k" → "120000")

**OUTPUT FORMAT (JSON):**
{{
  "budget_income": "150000",
  "family_situation": "Family of four with 2 school-age children, prioritizes good schools and safety",
  "lifestyle_preference": "Suburban communities with family amenities",
  "growth_priorities": "Balanced focus on affordability and economic stability"
}}

Parse and return the JSON response:
""",
    input_variables=["original_query", "user_response"]
)