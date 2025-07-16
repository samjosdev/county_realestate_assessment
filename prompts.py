# Updated prompts for HTML report generation
from langchain_core.prompts import PromptTemplate

# Only keep the following prompts, which are used in the active workflow:
# - SINGLE_STATE_INSIGHTS_PROMPT
# - COMPARISON_INSIGHTS_PROMPT
# - SINGLE_STATE_TOOL_CALL_PROMPT
# - COMPARISON_TOOL_CALL_PROMPT

SINGLE_STATE_INSIGHTS_PROMPT = PromptTemplate(
    template="""
You are a professional real estate analyst creating insights for a family's home buying decision.

**ANALYSIS REQUEST:**
State: {state_name}
Family Income: ${income}
User Preferences: {user_preferences}
Top Counties Summary: {summary}

**YOUR TASK:**
Generate professional insights and recommendations for this family's real estate decision in {state_name}.

**REQUIRED OUTPUT FORMAT:**
Split your response into exactly TWO sections using these headers:

INSIGHTS:
[Write 2-3 paragraphs analyzing the real estate market in {state_name} for this family's specific situation. Focus on market trends, affordability, and family-friendly factors. Be specific about their ${income} budget and how it positions them in the market.]

RECOMMENDATION:
[Write 1-2 paragraphs with specific, actionable recommendations for this family. Mention specific counties from the analysis and explain why they're good choices for this family's needs and budget.]

**EXAMPLE OUTPUT:**
INSIGHTS:
With your ${income} income, you're positioned in the move-up buyer segment in {state_name}, giving you access to quality family neighborhoods with excellent schools. The housing market in {state_name} shows strong fundamentals with steady appreciation and good inventory levels. Your budget puts you in competition with other families for the best school districts, but you have sufficient purchasing power to secure homes in top-rated communities.

RECOMMENDATION:
Focus your search on the top 3 counties identified in this analysis, particularly [County Name] which offers the best combination of family amenities and value for your budget. Schedule visits to these areas during school hours to observe the community dynamics and school pickup routines. Consider making offers quickly in this market, as quality family homes in good school districts tend to move fast.

**IMPORTANT:** 
- Be specific to their ${income} budget and {state_name}
- Reference the actual county data provided
- Keep insights practical and actionable
- Maintain a professional, confident tone
""",
    input_variables=["state_name", "summary", "tool_output", "income", "user_preferences"]
)

# Updated Comparison Insights Prompt for HTML reports  
COMPARISON_INSIGHTS_PROMPT = PromptTemplate(
    template="""
You are a professional real estate analyst creating a comparison analysis for a family's home buying decision.

**ANALYSIS REQUEST:**
States: {state1} vs {state2}
Family Income: ${income}
User Preferences: {user_preferences}
Counties Summary: {summary}

**YOUR TASK:**
Generate professional insights and recommendations comparing {state1} and {state2} for this family's real estate decision.

**REQUIRED OUTPUT FORMAT:**
Split your response into exactly TWO sections using these headers:

INSIGHTS:
[Write 2-3 paragraphs comparing the real estate markets in {state1} vs {state2} for this family's specific situation. Compare market trends, affordability, family-friendly factors, and how their ${income} budget positions them in each market. Be specific about the differences and advantages of each state.]

RECOMMENDATION:
[Write 1-2 paragraphs with specific, actionable recommendations for choosing between {state1} and {state2}. Mention specific counties from the analysis and explain which state/counties are better choices for this family's needs and budget. Give a clear recommendation with reasoning.]

**EXAMPLE OUTPUT:**
INSIGHTS:
Comparing {state1} and {state2} for your ${income} budget reveals distinct advantages in each market. {state1} offers [specific advantage] while {state2} provides [different advantage]. Your income level positions you as a competitive buyer in both markets, but with different purchasing power - in {state1} you can access [specific tier], while in {state2} your budget allows for [different tier]. The family-friendly amenities and school quality vary significantly between these markets.

RECOMMENDATION:
Based on your preferences and budget, I recommend focusing on {state1} if you prioritize [specific factor], particularly [County Name] which offers excellent value. However, if [different factor] is more important, {state2}'s [County Name] would be your best choice. Consider visiting both areas during different seasons to experience the climate and community feel before making your final decision.

**IMPORTANT:** 
- Be specific to their ${income} budget and both states
- Reference the actual county data provided
- Provide a clear recommendation with reasoning
- Maintain a professional, confident tone
""",
    input_variables=["state1", "state2", "summary", "tool_output", "income", "user_preferences"]
)

# Tool call generation prompts
SINGLE_STATE_TOOL_CALL_PROMPT = PromptTemplate(
    template="""You are helping a family find the best counties for real estate investment in a specific state.

Based on the extracted state information, you need to call the real_estate_investment_tool to get county data.

State Information: {state_info}
State Name: {state_name}
State FIPS: {state_fips}

Call the real_estate_investment_tool with the following parameters:
- state_fips: {state_fips}
- state_name: {state_name}
- filter_bucket: default

Use the tool to get the county data for this state."""
)

COMPARISON_TOOL_CALL_PROMPT = PromptTemplate(
    template="""You are helping a family compare real estate investment opportunities between two states.

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
)