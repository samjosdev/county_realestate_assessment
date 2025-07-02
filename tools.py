import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional
# Removed unused import: tool

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

# Removed STATE_FIPS_MAP - unused (FIPS mapping is in prompts.py)

def get_census_data(state_fips: str, variables: str) -> Dict[str, Any]:
    """Simple function to get census data for a state"""
    api_url = "https://api.census.gov/data/2022/acs/acs5"
    params = {
        "get": f"NAME,{variables}",
        "for": "county:*",
        "in": f"state:{state_fips}",
        "key": CENSUS_API_KEY
    }
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()
        return {"data": data, "error": None}
    except Exception as e:
        return {"data": None, "error": str(e)}

def tag_county(county):
    """
    Assigns path-based tags to a county using U.S. Census data.
    Supports:
        1. Budget-Friendliness (affordability)
        2. Family-Friendliness
        3. Urban/Suburban/Rural type
        4. Growth Potential

    Input:
        county (dict): Dictionary of county-level census variables
    Output:
        tags (dict): Dictionary of tag flags, classification, and scores
    """
    tags = {}

    # Extract variables
    home_value = county.get("B25077_001E", 0)
    income = county.get("B19013_001E", 0)
    population = county.get("B01003_001E", 0)
    households_with_kids = county.get("B11005_002E", 0)

    # -------------------------
    # 1. Budget-Friendliness
    # -------------------------
    try:
        affordability_score = round(home_value / income, 2) if income else float("inf")
    except ZeroDivisionError:
        affordability_score = float("inf")

    tags["affordability_score"] = affordability_score
    tags["budget_friendly"] = affordability_score < 3.5

    # -------------------------
    # 2. Family-Friendliness
    # -------------------------
    is_family = (
        income >= 70000 and
        population >= 30000 and
        households_with_kids >= 3000  # Optional cutoff
    )
    tags["family_friendly"] = is_family
    tags["family_score_factors"] = {
        "income": income,
        "population": population,
        "households_with_kids": households_with_kids
    }

    # -------------------------
    # 3. Urban / Suburban / Rural
    # -------------------------
    if population < 25000:
        tags["community_type"] = "rural"
    elif 25000 <= population <= 150000:
        tags["community_type"] = "suburban"
    else:
        tags["community_type"] = "urban"

    # -------------------------
    # 4. Growth Potential
    # -------------------------
    growth_potential = (
        income > 85000 and
        home_value > 300000
    )
    tags["growth_potential"] = growth_potential

    # -------------------------
    # 5. Homeownership Rate
    # -------------------------
    homeownership_rate = compute_homeownership_rate(county)
    tags["homeownership_rate"] = homeownership_rate

    return tags

def calculate_college_degree_rate(county):
    """
    Calculate the percentage of adults (25+) with a bachelor's degree or higher.
    
    Args:
        county (dict): County data with education census variables
        
    Returns:
        float: College degree rate as percentage, or 0 if no data
    """
    # Education levels: Bachelor's, Master's, Professional, Doctorate
    bachelor = county.get("B15003_022E", 0)
    master = county.get("B15003_023E", 0) 
    professional = county.get("B15003_024E", 0)
    doctorate = county.get("B15003_025E", 0)
    total_adults = county.get("B15003_001E", 0)
    
    if total_adults > 0:
        college_graduates = bachelor + master + professional + doctorate
        return round((college_graduates / total_adults) * 100, 1)
    return 0.0

def calculate_state_medians(counties_data):
    """
    Calculate state medians for dynamic filtering and tier-based scoring.
    
    Args:
        counties_data (list): List of county dictionaries
        
    Returns:
        dict: State medians for population, income, home value, and college degree rate
    """
    if not counties_data:
        return {"population": 0, "income": 0, "home_value": 0, "degree_rate": 0}
    
    populations = [c.get('B01003_001E', 0) for c in counties_data]
    incomes = [c.get('B19013_001E', 0) for c in counties_data if c.get('B19013_001E', 0) > 0]
    home_values = [c.get('B25077_001E', 0) for c in counties_data if c.get('B25077_001E', 0) > 0]
    degree_rates = [c.get('college_degree_rate', 0) for c in counties_data if c.get('college_degree_rate', 0) > 0]
    
    # Simple median calculation (avoiding numpy dependency)
    def median(values):
        if not values:
            return 0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
        else:
            return sorted_vals[n//2]
    
    return {
        "population": median(populations),
        "income": median(incomes),
        "home_value": median(home_values),
        "degree_rate": median(degree_rates)
    }

def apply_dynamic_filters(counties_data, user_priority=None):
    """
    Apply dynamic filtering based on state medians and user preferences.
    
    Args:
        counties_data (list): List of county dictionaries
        user_priority (dict): User preferences, including rural preference
        
    Returns:
        list: Filtered counties
    """
    if not counties_data:
        return []
    
    # Calculate state medians for dynamic thresholds
    state_medians = calculate_state_medians(counties_data)
    
    # Check if user wants rural/remote areas
    wants_rural = user_priority and user_priority.get("community_type") == "rural"
    
    # Adjust thresholds based on user preference
    if wants_rural:
        min_population = 20000  # Lower threshold for rural preference
        min_income_ratio = 0.6  # More lenient income requirement
        degree_rate_required = False  # Don't require degree rate for rural
    else:
        min_population = 80000  # Standard threshold
        min_income_ratio = 0.8  # 20% below state median
        degree_rate_required = True
    
    filtered = []
    for county in counties_data:
        # Population filter
        if county.get('B01003_001E', 0) < min_population:
            continue
            
        # Income filter - must be within reasonable range of state median
        county_income = county.get('B19013_001E', 0)
        if county_income < state_medians["income"] * min_income_ratio:
            continue
            
        # Education/school quality filter (skip for rural preference)
        if degree_rate_required:
            county_degree_rate = county.get('college_degree_rate', 0)
            if county_degree_rate < state_medians["degree_rate"]:
                continue
        
        filtered.append(county)
    
    return filtered

def detect_tier(user_budget):
    """
    Returns budget/income tier string.
    """
    if user_budget >= 5_000_000:
        return "ultra_luxury"
    elif user_budget >= 1_000_000:
        return "luxury"
    elif user_budget >= 500_000:
        return "move_up"
    else:
        return "affordable"

def get_notable_family_feature(county):
    """
    Generate a notable family feature description for a county based on its characteristics.
    
    Args:
        county (dict): County data with tags and census variables
        
    Returns:
        str: Notable family feature description
    """
    tags = county.get("tags", {})
    population = county.get("B01003_001E", 0)
    affordability = tags.get("affordability_score", float("inf"))
    homeownership = tags.get("homeownership_rate", 0)  # Fixed: look in tags, not county

    if tags.get("family_friendly") and homeownership > 65:
        return "High income & stable homeownership"

    if tags.get("budget_friendly") and affordability < 3.0 and population < 100000:
        return "Affordable starter homes"

    if tags.get("community_type") == "suburban" and 50000 <= population <= 150000 and tags.get("family_friendly"):
        return "Family-friendly suburbs"

    if tags.get("growth_potential") and tags.get("community_type") == "urban":
        return "Metro growth opportunity"

    return "Solid housing options"

def compute_homeownership_rate(county):
    """
    Calculate homeownership rate as a percentage.
    
    Args:
        county (dict): County data with census variables
        
    Returns:
        float: Homeownership rate as percentage, or None if no data
    """
    owner = county.get("B25003_002E", 0)
    total = county.get("B25003_001E", 0)
    if total > 0:
        return round((owner / total) * 100, 1)  # as percentage
    return None

def score_county(county, user_priority, state_medians=None, user_budget=0):
    """
    Assign a composite score to a county based on tags, user priorities, and budget tier.
    
    Args:
        county (dict): County data with tags
        user_priority (dict): User preferences for scoring
        state_medians (dict): State median values for comparison
        user_budget (int): User's budget/income for tier-based scoring
        
    Returns:
        float: Composite score for sorting
    """
    tags = county.get("tags", {})
    score = 0
    tier = detect_tier(user_budget)
    home_value = county.get("B25077_001E", 0)
    income = county.get("B19013_001E", 0)
    degree_rate = county.get('college_degree_rate', 0)
    
    # Set default medians if not provided
    if state_medians is None:
        state_medians = {"home_value": 0, "income": 0, "degree_rate": 0}
    
    median_home = state_medians.get("home_value", 0)
    median_income = state_medians.get("income", 0)
    median_degree = state_medians.get("degree_rate", 0)

    # --- Tiered scoring logic ---
    if tier == "affordable":
        if home_value <= user_budget:
            score += 5
        score -= max((home_value - user_budget) / 100_000, 0)
    elif tier == "move_up":
        if home_value <= user_budget * 1.2:
            score += 3
        if home_value > user_budget * 1.2:
            score -= 2
        if income > median_income:
            score += 1
    elif tier == "luxury":
        if home_value >= 1.5 * median_home:
            score += 5  # Reward prestige
        if degree_rate > median_degree:
            score += 2
        if income > 1.5 * median_income:
            score += 2
        if home_value < user_budget * 0.5:
            score -= 2  # Too cheap
    elif tier == "ultra_luxury":
        if home_value >= 2.5 * median_home:
            score += 8
        if income > 2 * median_income:
            score += 2
        if degree_rate > median_degree:
            score += 2
        if home_value < user_budget * 0.5:
            score -= 3  # Too cheap for this tier

    # Family, growth, and amenities scoring
    if user_priority.get("family") and tags.get("family_friendly"):
        score += 3
    if user_priority.get("family") and not tags.get("family_friendly"):
        score -= 3

    if user_priority.get("growth") and tags.get("growth_potential"):
        score += 2

    # Community type preference
    if user_priority.get("community_type"):
        if tags.get("community_type") == user_priority["community_type"]:
            score += 2

    # Bonus for large population (amenities)
    population = county.get("B01003_001E", 0)
    if population > 150_000:
        score += 1

    return score

def sort_counties_by_tags(counties, user_priority, state_medians=None, user_budget=0):
    """
    Sort counties by composite score based on user priorities and budget tier.
    
    Args:
        counties (list): List of county dictionaries with tags
        user_priority (dict): User preferences for scoring
        state_medians (dict): State median values for comparison
        user_budget (int): User's budget/income for tier-based scoring
        
    Returns:
        list: Sorted counties by descending score
    """
    for county in counties:
        county["sort_score"] = score_county(county, user_priority, state_medians, user_budget)
    return sorted(counties, key=lambda c: -c["sort_score"])

def real_estate_investment_tool(state_fips: str, state_name: str, comparison_states: str = "", filter_bucket: str = "default") -> Dict[str, Any]:
    """Get residential real estate data for a specific state."""
    if not state_fips or not state_name:
        return {"error": "FIPS code and state name are required."}
    
    # Get data for the main state - added education variables
    variables = "B25077_001E,B19013_001E,B25064_001E,B01003_001E,B11005_002E,B25003_001E,B25003_002E,B15003_022E,B15003_023E,B15003_024E,B15003_025E,B15003_001E"
    result = get_census_data(state_fips, variables)
    
    if result["error"]:
        return {"error": result["error"]}
    
    # Process the data
    header, rows = result["data"][0], result["data"][1:]
    counties_data = []
    
    # All census variables we're collecting
    all_vars = ["B25077_001E", "B19013_001E", "B25064_001E", "B01003_001E", "B11005_002E", 
                "B25003_001E", "B25003_002E", "B15003_022E", "B15003_023E", "B15003_024E", 
                "B15003_025E", "B15003_001E"]
    
    for row in rows:
        county_data = dict(zip(header, row))
        try:
            # Convert to integers, handle missing data
            processed_data = {"name": county_data.get('NAME')}
            for var in all_vars:
                value = county_data.get(var, 0)
                processed_data[var] = int(value) if value and value != '' else 0
            
            # Calculate college degree rate
            processed_data['college_degree_rate'] = calculate_college_degree_rate(processed_data)
            
            # Basic data quality filter - only exclude counties with completely missing data
            if (processed_data['B25077_001E'] > 0 and  # Valid home value
                processed_data['B01003_001E'] >= 10000 and  # At least 10,000 people
                processed_data['B19013_001E'] > 0):  # Valid income data
                counties_data.append(processed_data)
        except (ValueError, TypeError):
            continue
    
    # Calculate affordability scores for all counties first
    for county in counties_data:
        if county['B19013_001E'] > 0:
            county['affordability_score'] = county['B25077_001E'] / county['B19013_001E']
        else:
            county['affordability_score'] = float('inf')
    
    # Apply dynamic filtering based on state medians (will be applied later in workflow)
    # For now, just sort by affordability and return all qualifying counties
    counties_data.sort(key=lambda x: x.get('affordability_score', float('inf')))
    
    # Return more counties to allow for dynamic filtering later
    counties_data = counties_data[:50]  # Increased from 25 to allow filtering
    
    return {
        "data": {state_name: {"data": counties_data}},
        "source": "2022 ACS 5-Year Estimates",
        "state_analyzed": state_name,
        "filter_bucket": filter_bucket
    }

# Removed apply_filter_bucket function - never called anywhere
# Removed available_tools - not used (build_Graph.py creates its own)
