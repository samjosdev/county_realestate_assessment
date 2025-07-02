import asyncio
from typing import TypedDict, Annotated, List, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from datetime import datetime
from models import get_supervisor_llm, get_formatter_llm
from prompts import (
    FOLLOWUP_QUESTIONS_PROMPT,
    MULTI_STATE_FIPS_EXTRACTION_PROMPT,
    SINGLE_STATE_INSIGHTS_PROMPT,
    COMPARISON_INSIGHTS_PROMPT,
    FIPS_CONTEXT,
    NON_REAL_ESTATE_RESPONSE,
    SINGLE_STATE_TOOL_CALL_PROMPT,
    COMPARISON_TOOL_CALL_PROMPT,
    PARSE_FOUR_FACTORS_PROMPT
)
from langchain_core.output_parsers import JsonOutputParser
from tools import real_estate_investment_tool, tag_county, sort_counties_by_tags, get_notable_family_feature, apply_dynamic_filters, calculate_state_medians, detect_tier, score_county
from langgraph.prebuilt import tools_condition, ToolNode
from langchain.prompts import PromptTemplate
from formatting import format_single_state_report, format_comparison_report

# Create a checkpointer for state persistence
checkpointer = MemorySaver()

# Simplified state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_output: Optional[dict]
    is_comparison: Optional[bool]
    summary: Optional[str]
    insights: Optional[str]
    final_result: Optional[str]
    followup_question: Optional[str]
    needs_followup: Optional[bool]
    states: Optional[list]
    route: Optional[str]  # Used for routing: "non_real_estate", "comparison", "single_state"
    user_preferences: Optional[str]  # Store user's answers to followup questions
    income: Optional[str]  # Store extracted or provided income information
    extracted_preferences: Optional[dict]  # Store structured preferences from LLM analysis

class USCensusAgent(BaseModel):
    graph: Any = Field(default=None, init=False)
    formatter_llm: Any = Field(default=None, init=False)
    formatter_llm_with_tools: Any = Field(default=None, init=False)
    supervisor_llm: Any = Field(default=None, init=False)
    supervisor_llm_with_tools: Any = Field(default=None, init=False)
    tools: Any = Field(default=None, init=False)
    single_state_tool_node: Any = Field(default=None, init=False)
    comparison_tool_node: Any = Field(default=None, init=False)

    class Config:
        arbitrary_types_allowed = True

    async def setup_graph(self):
        """
        Setup function that initializes LLMs, binds them with tools, creates ToolNode,
        and then builds the workflow graph.
        
        Returns:
            Compiled graph ready for execution
        """
        print("🔧 Setting up USCensusAgent...")
        
        # Initialize LLMs
        self.supervisor_llm = get_supervisor_llm()
        self.formatter_llm = get_formatter_llm()
        self.tools = [real_estate_investment_tool]
        
        # Bind tools to LLMs for tool calling
        self.supervisor_llm_with_tools = self.supervisor_llm.bind_tools(self.tools)
        self.formatter_llm_with_tools = self.formatter_llm.bind_tools(self.tools)
        self.graph = self.build_graph()
        print("✅ USCensusAgent setup complete!")
        return self.graph
    
    # --- New Workflow Nodes as staticmethods ---
    def extract_states_and_flag(self, state):
        print("🔄 Executing: extract_states_and_flag node")
        # If states are already populated, skip extraction
        existing_states = state.get("states")
        if existing_states:
            print(f"✅ States already extracted: {existing_states}, skipping re-extraction")
            return state
        # Extract states from the first message (original query)
        messages = state.get("messages", [])
        if not messages:
            raise ValueError("Messages to extract states from not found!")
        user_query = messages[0].content
        
        try:
            multi_state_prompt = PromptTemplate(
                input_variables=["query", "context"],
                template=MULTI_STATE_FIPS_EXTRACTION_PROMPT
            )
            chain = multi_state_prompt | get_supervisor_llm() | JsonOutputParser()
            result = chain.invoke({"query": user_query, "context": FIPS_CONTEXT})
            states = result.get("states", [])
            if not states:
                print(f"⚠️ No states found in query - routing to non-real estate handler")
                return {
                    **state,
                    "route": "non_real_estate",
                    "states": [],
                    "is_comparison": False
                }
            is_comparison = len(states) > 1
        except Exception as e:
            print(f"❌ Error in state extraction: {e} - routing to non-real estate handler")
            return {
                **state,
                "route": "non_real_estate", 
                "states": [],
                "is_comparison": False
            }
        print(f"✅ Completed: extract_states_and_flag -> {states} (is_comparison={is_comparison})")
        return {
            **state,
            "states": states,
            "is_comparison": is_comparison,
            "needs_followup": True  # Reset to True for new queries
        }

    def ask_followup_question(self, state):
        print("🔄 Executing: ask_followup_question")
        messages = state.get("messages", [])
        
        # If we have more than one message, user has answered the followup
        if len(messages) > 1:
            print("[DEBUG] User has answered followup, proceeding to routing.")
            
            # Step 2: LLM parses both queries to populate 4 factors
            user_response = messages[-1].content if len(messages) > 1 else ""
            original_query = messages[0].content if messages else ""
            
            try:
                # Use LLM to parse and populate the 4 factors
                parsing_chain = PARSE_FOUR_FACTORS_PROMPT | get_supervisor_llm() | JsonOutputParser()
                four_factors = parsing_chain.invoke({
                    "original_query": original_query,
                    "user_response": user_response
                })
                print(f"[DEBUG] LLM parsed 4 factors: {four_factors}")
                
                # Extract values with defaults
                income = four_factors.get("budget_income", "150000")
                user_preferences = f"Family: {four_factors.get('family_situation', 'family-friendly')}, Lifestyle: {four_factors.get('lifestyle_preference', 'mixed communities')}, Growth: {four_factors.get('growth_priorities', 'balanced')}"
                
            except Exception as e:
                print(f"[DEBUG] Error parsing factors: {e}, using defaults")
                income = "150000"
                user_preferences = f"Original: {original_query}\nResponse: {user_response}"
            
            # Determine routing based on state
            if state.get("route") == "non_real_estate":
                route = "non_real_estate"
            elif state.get("is_comparison"):
                route = "comparison"
            else:
                route = "single_state"
            
            print(f"[DEBUG] Routing to: {route}")
            print(f"[DEBUG] Final income: {income}")
            
            return {
                **state, 
                "needs_followup": False, 
                "route": route,
                "user_preferences": user_preferences,
                "income": income
            }
            
        # First time - ask the followup question
        if not state.get('needs_followup', True):
            print("[DEBUG] needs_followup is False, skipping followup question.")
            return {**state, "needs_followup": False}
            
        # Use the original query (first message) for generating followup questions
        user_query = messages[0].content if messages else ""
        questions_chain = FOLLOWUP_QUESTIONS_PROMPT | get_supervisor_llm()
        result = questions_chain.invoke({"user_query": user_query})
        question_text = result.content if hasattr(result, 'content') else str(result)
        print("✅ Completed: ask_followup_question -> interrupting")
        return interrupt({**state, "followup_question": question_text, "needs_followup": False})

    def single_state_county_lookup(self, state):
        """County lookup node for single state flow"""
        print("🔄 Executing: single_state_county_lookup (LLM generates tool call)")
        
        state_info = state["states"][0]
        prompt = SINGLE_STATE_TOOL_CALL_PROMPT.format(
            state_info=state_info,
            state_name=state_info["state_name"],
            state_fips=state_info["fips_code"]
        )
        
        print(f"[DEBUG] Single state prompt: {prompt[:200]}...")
        
        # LLM generates tool call
        response = self.supervisor_llm_with_tools.invoke([{"role": "user", "content": prompt}])
        
        # Debug: Check if tool calls were generated
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"[DEBUG] Tool calls generated: {len(response.tool_calls)} calls")
            for i, tool_call in enumerate(response.tool_calls):
                print(f"[DEBUG] Tool call {i}: {tool_call.get('name', 'unknown')} with args: {str(tool_call.get('args', {}))[:100]}...")
        else:
            print("[DEBUG] ⚠️ No tool calls generated by LLM!")
        
        # Add the AI message with tool calls to state
        return {
            **state,
            "messages": state.get("messages", []) + [response]
        }

    def comparison_county_lookup(self, state):
        """County lookup node for comparison flow"""
        print("🔄 Executing: comparison_county_lookup (LLM generates tool calls)")
        
        state1, state2 = state["states"][:2]
        prompt = COMPARISON_TOOL_CALL_PROMPT.format(
            state1_info=state1,
            state1_name=state1["state_name"],
            state1_fips=state1["fips_code"],
            state2_info=state2,
            state2_name=state2["state_name"],
            state2_fips=state2["fips_code"]
        )
        
        # LLM generates tool calls
        response = self.supervisor_llm_with_tools.invoke([{"role": "user", "content": prompt}])
        
        # Add the AI message with tool calls to state
        return {
            **state,
            "messages": state.get("messages", []) + [response]
        }

    def process_single_state_tool_results(self, state):
        """Process single state tool call results and extract tool_output"""
        print("🔄 Executing: process_single_state_tool_results")
        messages = state.get("messages", [])
        
        # Find the last tool result for single state
        tool_output = {}
        tool_results = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'tool']
        if tool_results:
            content = tool_results[-1].content
            # Handle both string and dict content
            if isinstance(content, str):
                try:
                    import json
                    tool_output = json.loads(content)
                except json.JSONDecodeError:
                    print(f"⚠️ Could not parse tool result as JSON: {content}")
                    tool_output = {}
            else:
                tool_output = content if isinstance(content, dict) else {}
        else:
            print("⚠️ No tool results found in messages for single state")
            
        print(f"✅ Processed single state tool result: {type(tool_output)} with keys {list(tool_output.keys()) if isinstance(tool_output, dict) else 'N/A'}")
        return {**state, "tool_output": tool_output}

    def process_comparison_tool_results(self, state):
        """Process comparison tool call results and extract tool_output"""
        print("🔄 Executing: process_comparison_tool_results")
        messages = state.get("messages", [])
        
        # Find tool results for comparison (should have 2 results)
        tool_results = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'tool']
        
        if len(tool_results) >= 2:
            # Extract and parse results from both tool calls
            results = {}
            for i, key in enumerate(['state1', 'state2']):
                content = tool_results[-(2-i)].content if hasattr(tool_results[-(2-i)], 'content') else {}
                # Handle both string and dict content
                if isinstance(content, str):
                    try:
                        import json
                        results[key] = json.loads(content)
                    except json.JSONDecodeError:
                        print(f"⚠️ Could not parse tool result as JSON for {key}: {content}")
                        results[key] = {}
                else:
                    results[key] = content if isinstance(content, dict) else {}
            tool_output = results
        else:
            print(f"⚠️ Expected 2 tool results for comparison, found {len(tool_results)}")
            tool_output = {"state1": {}, "state2": {}}
            
        print(f"✅ Processed comparison tool results: state1 type={type(tool_output.get('state1'))}, state2 type={type(tool_output.get('state2'))}")
        return {**state, "tool_output": tool_output}

    def summarize_single_state(self, state):
        print("🔄 Executing: summarize_single_state with tagging and sorting")
        # Extract tool results directly from messages
        messages = state.get("messages", [])
        tool_results = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'tool']
        
        tool_output = {}
        if tool_results:
            content = tool_results[-1].content
            if isinstance(content, str):
                try:
                    import json
                    tool_output = json.loads(content)
                except json.JSONDecodeError:
                    print(f"⚠️ Could not parse tool result as JSON: {content}")
            else:
                tool_output = content if isinstance(content, dict) else {}
        
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])
        
        # Apply dynamic filtering and tagging system
        if counties:
            print(f"[DEBUG] Starting with {len(counties)} counties...")
            
            # Step 1: Parse user preferences and budget
            user_preferences = state.get("user_preferences", "")
            user_priority = self._parse_user_priority(user_preferences)
            user_budget = int(state.get("income", "150000"))
            tier = detect_tier(user_budget)
            print(f"[DEBUG] User priority: {user_priority}")
            print(f"[DEBUG] User budget: ${user_budget:,} (Tier: {tier})")
            
            # Step 2: Calculate state medians for tier-based scoring
            state_medians = calculate_state_medians(counties)
            print(f"[DEBUG] State medians: Home=${state_medians['home_value']:,.0f}, Income=${state_medians['income']:,.0f}")
            
            # Step 3: Apply dynamic filtering based on state medians
            counties = apply_dynamic_filters(counties, user_priority)
            print(f"[DEBUG] After dynamic filtering: {len(counties)} counties remain")
            
            # Step 4: Tag all remaining counties with 5-factor analysis
            for county in counties:
                county['tags'] = tag_county(county)
                county['tags']['notable_family_feature'] = get_notable_family_feature(county)
            print(f"[DEBUG] Applied tagging to {len(counties)} counties")
            
            # Step 5: Sort counties by tier-based composite score
            counties = sort_counties_by_tags(counties, user_priority, state_medians, user_budget)
            print(f"[DEBUG] Counties sorted by tier-based relevance score")
            
            # Limit to top 25 for final output
            counties = counties[:25]
            
            # Update tool_output with filtered, tagged and sorted counties
            tool_output["data"][state_name]["data"] = counties
        
        summary = f"Top 5 counties in {state_name}: " + ", ".join([c["name"] for c in counties[:5]])
        return {**state, "summary": summary, "tool_output": tool_output}
    
    def _parse_user_priority(self, user_preferences: str) -> dict:
        """Parse user preferences into priority object for scoring."""
        priority = {
            "budget": True,  # Default to True since everyone cares about budget
            "family": False,
            "community_type": None,
            "growth": False
        }
        
        if not user_preferences:
            return priority
            
        pref_lower = user_preferences.lower()
        
        # Check for family priorities
        family_keywords = ["family", "children", "kids", "school", "safety", "child"]
        if any(keyword in pref_lower for keyword in family_keywords):
            priority["family"] = True
            
        # Check for community type preferences
        if any(word in pref_lower for word in ["urban", "city", "downtown", "metropolitan"]):
            priority["community_type"] = "urban"
        elif any(word in pref_lower for word in ["suburban", "suburb", "neighborhood"]):
            priority["community_type"] = "suburban"  
        elif any(word in pref_lower for word in ["rural", "small town", "country", "quiet"]):
            priority["community_type"] = "rural"
            
        # Check for growth/investment priorities
        growth_keywords = ["growth", "investment", "job", "economic", "opportunity", "tech", "development"]
        if any(keyword in pref_lower for keyword in growth_keywords):
            priority["growth"] = True
            
        return priority

    def insights_single_state(self, state):
        print("🔄 Executing: insights_single_state (LLM-based)")
        summary = state.get("summary", "")
        tool_output = state.get("tool_output", {})
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        income = state.get("income", "150000")
        user_preferences = state.get("user_preferences", "No specific preferences provided")
        
        # Add tier information
        user_budget = int(income)
        tier = detect_tier(user_budget)
        tier_descriptions = {
            "affordable": "affordable housing",
            "move_up": "move-up buyer segment", 
            "luxury": "luxury home market",
            "ultra_luxury": "ultra-luxury estate market"
        }
        tier_description = tier_descriptions.get(tier, "housing market")
        
        # Use the prompt from prompts.py
        chain = SINGLE_STATE_INSIGHTS_PROMPT | get_formatter_llm()
        response = chain.invoke({
            "state_name": state_name,
            "summary": summary,
            "tool_output": str(tool_output),
            "income": income,
            "user_preferences": f"{user_preferences} (Budget tier: {tier_description})"
        })
        
        # Parse response (simple split)
        content = response.content if hasattr(response, 'content') else str(response)
        insights, recommendation = "", ""
        if "Recommendation:" in content:
            parts = content.split("Recommendation:")
            insights = parts[0].replace("Insights:", "").strip()
            recommendation = parts[1].strip()
        else:
            insights = content.strip()
        return {**state, "insights": insights, "recommendation": recommendation}

    def assemble_single_state(self, state):
        print("🔄 Executing: assemble_single_state (detailed report)")
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if income_raw.isdigit() else income_raw
        counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])
        
        # Use formatting function from formatting.py
        final_report = format_single_state_report(
            state_name=state_name,
            income=income,
            counties=counties,
            insights=insights,
            recommendation=recommendation
        )
        
        # Reset state flags for next query
        return {
            "messages": state.get("messages", []),
            "final_result": final_report
        }

    def summarize_comparison(self, state):
        print("🔄 Executing: summarize_comparison with tagging and sorting")
        
        # First, extract tool results from messages (similar to process_comparison_tool_results)
        messages = state.get("messages", [])
        tool_results = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'tool']
        
        tool_output = {}
        if len(tool_results) >= 2:
            # Extract and parse results from both tool calls
            results = {}
            for i, key in enumerate(['state1', 'state2']):
                content = tool_results[-(2-i)].content if hasattr(tool_results[-(2-i)], 'content') else {}
                # Handle both string and dict content
                if isinstance(content, str):
                    try:
                        import json
                        results[key] = json.loads(content)
                    except json.JSONDecodeError:
                        print(f"⚠️ Could not parse tool result as JSON for {key}: {content}")
                        results[key] = {}
                else:
                    results[key] = content if isinstance(content, dict) else {}
            tool_output = results
        else:
            print(f"⚠️ Expected 2 tool results for comparison, found {len(tool_results)}")
            tool_output = {"state1": {}, "state2": {}}
        
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        counties1 = tool_output.get("state1", {}).get("data", {}).get(name1, {}).get("data", [])
        counties2 = tool_output.get("state2", {}).get("data", {}).get(name2, {}).get("data", [])

        user_preferences = state.get("user_preferences", "")
        user_priority = self._parse_user_priority(user_preferences)
        user_budget = int(state.get('income', 0) or 0)

        # Apply dynamic filtering and tier-aware scoring for both states
        for i, (counties, name) in enumerate([(counties1, name1), (counties2, name2)]):
            print(f"[DEBUG] Processing state {i+1} ({name}): {len(counties)} counties found")
            if counties:
                state_medians = calculate_state_medians(counties)
                print(f"[DEBUG] State medians for {name}: Home=${state_medians['home_value']:,.0f}, Income=${state_medians['income']:,.0f}")
                
                # Tag and score all
                for county in counties:
                    county['tags'] = tag_county(county)
                    county['tags']['notable_family_feature'] = get_notable_family_feature(county)
                
                # Tier-aware sorting
                counties = sorted(counties, key=lambda c: -score_county(c, user_priority, state_medians, user_budget))
                print(f"[DEBUG] After tier-aware sorting for {name}: {len(counties)} counties")
                
                # Ensure we have at least 3 counties for the table
                if len(counties) < 3:
                    # Fallback: sort by home value and take what we have
                    counties = sorted(counties, key=lambda c: -c.get("B25077_001E", 0))
                    print(f"[DEBUG] Fallback applied for {name}: {len(counties)} counties available")
                
                # Write back
                if i == 0:
                    counties1 = counties[:25]  # Limit to 25 max
                else:
                    counties2 = counties[:25]  # Limit to 25 max
            else:
                print(f"[DEBUG] No counties found for {name}")
                # Set empty but ensure structure exists
                if i == 0:
                    counties1 = []
                else:
                    counties2 = []

        # Update tool_output
        if counties1:
            tool_output["state1"]["data"][name1]["data"] = counties1
        if counties2:
            tool_output["state2"]["data"][name2]["data"] = counties2

        # Generate summary with safety checks
        counties1_names = [c.get("name", "Unknown County") for c in counties1[:3]] if counties1 else ["No data available"]
        counties2_names = [c.get("name", "Unknown County") for c in counties2[:3]] if counties2 else ["No data available"]
        
        summary = f"Top 3 counties in {name1}: " + ", ".join(counties1_names)
        summary += f" | Top 3 counties in {name2}: " + ", ".join(counties2_names)
        
        print(f"[DEBUG] Final summary: {summary}")
        print(f"[DEBUG] Counties1 count: {len(counties1)}, Counties2 count: {len(counties2)}")
        
        return {**state, "summary": summary, "tool_output": tool_output}

    def insights_comparison(self, state):
        print("🔄 Executing: insights_comparison (LLM-based)")
        summary = state.get("summary", "")
        tool_output = state.get("tool_output", {})
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        income = state.get("income", "150000")
        user_preferences = state.get("user_preferences", "No specific preferences provided")
        
        # Add tier information
        user_budget = int(income)
        tier = detect_tier(user_budget)
        tier_descriptions = {
            "affordable": "affordable housing",
            "move_up": "move-up buyer segment", 
            "luxury": "luxury home market",
            "ultra_luxury": "ultra-luxury estate market"
        }
        tier_description = tier_descriptions.get(tier, "housing market")
        
        # Use the prompt from prompts.py
        chain = COMPARISON_INSIGHTS_PROMPT | get_formatter_llm()
        response = chain.invoke({
            "state1": name1,
            "state2": name2,
            "summary": summary,
            "tool_output": str(tool_output),
            "income": income,
            "user_preferences": f"{user_preferences} (Budget tier: {tier_description})"
        })
        
        # Parse response (simple split)
        content = response.content if hasattr(response, 'content') else str(response)
        takeaways, recommendation = "", ""
        if "Recommendation:" in content:
            parts = content.split("Recommendation:")
            takeaways = parts[0].replace("Takeaways:", "").strip()
            recommendation = parts[1].strip()
        else:
            takeaways = content.strip()
        return {**state, "insights": takeaways, "recommendation": recommendation}

    def handle_non_real_estate(self, state):
        print("🔄 Executing: handle_non_real_estate")
        messages = state.get("messages", [])
        user_query = messages[0].content if messages else "your query"
        
        # Use the imported prompt template instead of hardcoded response
        response = NON_REAL_ESTATE_RESPONSE.format(user_query=user_query)
        
        print("✅ Completed: handle_non_real_estate")
        return {
            "messages": state.get("messages", []),
            "final_result": response
        }

    def assemble_comparison(self, state):
        print("🔄 Executing: assemble_comparison (detailed report)")
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if income_raw.isdigit() else income_raw
        counties1 = tool_output.get("state1", {}).get("data", {}).get(name1, {}).get("data", [])
        counties2 = tool_output.get("state2", {}).get("data", {}).get(name2, {}).get("data", [])
        
        # Use formatting function from formatting.py
        final_report = format_comparison_report(
            name1=name1,
            name2=name2,
            income=income,
            counties1=counties1,
            counties2=counties2,
            insights=insights,
            recommendation=recommendation
        )
        
        # Reset state flags for next query
        return {
            "messages": state.get("messages", []),
            "final_result": final_report
        }

    



    def build_graph(self):
        graph = StateGraph(AgentState)
        
        # Create separate ToolNodes for each flow
        print("🔄 Creating ToolNodes for each flow")        
        self.single_state_tool_node = ToolNode(self.tools)
        self.comparison_tool_node = ToolNode(self.tools)

        #Common nodes for all three flows
        graph.add_node("extract_states", self.extract_states_and_flag)
        graph.add_node("followup_question", self.ask_followup_question)
        
        # Separate county lookup nodes for independent flows
        graph.add_node("single_state_county_lookup", self.single_state_county_lookup)
        graph.add_node("comparison_county_lookup", self.comparison_county_lookup)
        
        # Separate tool nodes for each flow
        graph.add_node("single_state_tools", self.single_state_tool_node)
        graph.add_node("comparison_tools", self.comparison_tool_node)
        
        # Downstream processing nodes (no separate processing nodes)
        graph.add_node("summarize_single_state", self.summarize_single_state)
        graph.add_node("insights_single_state", self.insights_single_state)
        graph.add_node("assemble_single_state", self.assemble_single_state)
        graph.add_node("summarize_comparison", self.summarize_comparison)
        graph.add_node("insights_comparison", self.insights_comparison)
        graph.add_node("assemble_comparison", self.assemble_comparison)

        #Exception path (non supported usecases)
        graph.add_node("handle_non_real_estate", self.handle_non_real_estate)
        
        #EXECUTION FLOW
        #Entry point
        graph.set_entry_point("extract_states")
        
        # Handle routing from extract_states
        graph.add_conditional_edges(
            "extract_states",
            lambda state: state.get("route", "continue"),
            {
                "non_real_estate": "handle_non_real_estate",
                "continue": "followup_question"
            }
        )
        
        graph.add_conditional_edges(
            "followup_question",
            lambda state: state.get("route", "continue"),
            {
                "single_state": "single_state_county_lookup",
                "comparison": "comparison_county_lookup", 
                "non_real_estate": "handle_non_real_estate",
                "continue": "followup_question"  # Loop back for interrupt handling
            }
        )
        
        # County lookup to tools connections  
        def debug_tools_condition(state):
            """Debug wrapper for tools_condition"""
            result = tools_condition(state)
            print(f"[DEBUG] tools_condition result: {result}")
            messages = state.get("messages", [])
            if messages:
                last_msg = messages[-1]
                print(f"[DEBUG] Last message type: {type(last_msg)}")
                if hasattr(last_msg, 'tool_calls'):
                    print(f"[DEBUG] Last message has tool_calls: {len(last_msg.tool_calls) if last_msg.tool_calls else 0}")
            return result
            
        graph.add_conditional_edges(
            "single_state_county_lookup",
            debug_tools_condition,
            {
                "tools": "single_state_tools",
                END: END
            }
        )
        
        graph.add_conditional_edges(
            "comparison_county_lookup",
            tools_condition,
            {
                "tools": "comparison_tools",
                END: END
            }
        )

        # Tool nodes check if more tools need to be called
        graph.add_conditional_edges(
            "single_state_tools",
            tools_condition,
            {
                "tools": "single_state_tools",  # Loop back if more tools to call
                "__end__": "summarize_single_state"  # Move to summarize when done
            }
        )
        
        graph.add_conditional_edges(
            "comparison_tools",
            tools_condition,
            {
                "tools": "comparison_tools",  # Loop back if more tools to call
                "__end__": "summarize_comparison"  # Move to summarize when done
            }
        )

        # Single state execution flow
        graph.add_edge("summarize_single_state", "insights_single_state")
        graph.add_edge("insights_single_state", "assemble_single_state")

        # Comparison state execution flow
        graph.add_edge("summarize_comparison", "insights_comparison")
        graph.add_edge("insights_comparison", "assemble_comparison")
        
        return graph.compile(checkpointer=checkpointer)

def setup_and_build_graph():
    """
    Helper function to create a USCensusAgent and set up its graph.
    This handles the async setup properly.
    """
    import asyncio
    
    async def _setup():
        agent = USCensusAgent()
        graph = await agent.setup_graph()
        return agent, graph
    
    # If we're already in an async context, return the coroutine
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, can't use asyncio.run
        return asyncio.create_task(_setup())
    except RuntimeError:
        # No running loop, we can use asyncio.run
        return asyncio.run(_setup())

# For testing, you can instantiate and run this new workflow graph
us_census_agent = USCensusAgent()

# Create a function that returns the setup graph for import
async def get_new_workflow_graph():
    """Get the workflow graph with proper async setup"""
    if not us_census_agent.graph:
        await us_census_agent.setup_graph()
    return us_census_agent.graph

# For backwards compatibility, create a sync version
def get_workflow_graph_sync():
    """Get the workflow graph using sync setup"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, return None and let caller handle async
        return None
    except RuntimeError:
        # No running loop, we can use asyncio.run
        async def _setup():
            if not us_census_agent.graph:
                await us_census_agent.setup_graph()
            return us_census_agent.graph
        return asyncio.run(_setup())

# Try to create the graph for backwards compatibility
try:
    new_workflow_graph = get_workflow_graph_sync()
except Exception as e:
    print(f"Note: Async setup required. Use 'await get_new_workflow_graph()' or 'await us_census_agent.setup_graph()'")
    new_workflow_graph = None

# At the end, expose both for import
__all__ = ["us_census_agent", "checkpointer", "new_workflow_graph", "get_new_workflow_graph", "setup_and_build_graph"]