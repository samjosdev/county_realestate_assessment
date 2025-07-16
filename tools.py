import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import statistics
from best_counties_by_state import BEST_COUNTIES_PER_STATE
import random
from datetime import datetime

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
FBI_API_KEY = os.getenv("FBI_API_KEY")  # Get from https://api.data.gov/signup/
FBI_API_BASE = "https://api.usa.gov/crime/fbi/sapi"

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

# FBI Crime Data Functions
def get_fbi_crime_data_by_state(state_fips: str) -> Dict[str, Any]:
    """
    Fetch FBI crime data for a specific state. Returns None if unavailable.
    
    Args:
        state_fips: State FIPS code (e.g., "41" for Oregon)
    
    Returns:
        Dictionary containing crime statistics or None if unavailable
    """
    if not FBI_API_KEY:
        return None
    
    try:
        # Try multiple endpoint patterns to get state data
        endpoints = [
            f"/api/summarized/state/{state_fips}",
            f"/api/data/nibrs/national/state/{state_fips}/offense",
            f"/api/summarized/state/{state_fips}/offense"
        ]
        
        for endpoint in endpoints:
            url = f"{FBI_API_BASE}{endpoint}"
            
            params = {
                "api_key": FBI_API_KEY,
                "since": "2020",  # Recent years since NIBRS transition
                "until": "2023"
            }
            
            try:
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and 'results' in data and data['results']:
                        return {
                            "data": data,
                            "source": "FBI Uniform Crime Reporting Program",
                            "last_updated": datetime.now().strftime("%Y-%m-%d"),
                            "coverage": "State-level data",
                            "endpoint_used": endpoint
                        }
                elif response.status_code == 403:
                    # API key issue - stop trying
                    return None
                    
            except requests.exceptions.RequestException:
                continue
        
        return None
        
    except Exception:
        return None

def get_state_agencies(state_fips: str) -> Dict[str, Any]:
    """
    Get list of law enforcement agencies in a state for potential county-level mapping.
    """
    if not FBI_API_KEY:
        return {"error": "FBI API key not configured"}
    
    try:
        url = f"{FBI_API_BASE}/api/agencies"
        
        params = {
            "api_key": FBI_API_KEY,
            "state_id": state_fips,
            "per_page": 200
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "agencies": data.get("results", []),
            "total": data.get("pagination", {}).get("count", 0),
            "source": "FBI UCR Program - Agency Directory"
        }
        
    except Exception as e:
        return {"error": f"Error fetching agency data: {str(e)}"}

def calculate_state_crime_metrics(crime_data: Dict, state_population: int) -> Optional[Dict[str, Any]]:
    """
    Calculate state-level crime safety metrics from FBI data.
    Returns None if data is insufficient.
    """
    if not crime_data or state_population <= 0:
        return None
    
    try:
        results = crime_data.get("data", {}).get("results", [])
        if not results:
            return None
        
        # Get most recent year's data
        latest_data = results[-1] if results else {}
        if not latest_data:
            return None
        
        # Process real FBI API data
        violent_crimes = 0
        property_crimes = 0
        
        # Extract crime counts (handle different API response formats)
        if "violent_crime_rate" in latest_data:
            # Rate data
            violent_crime_rate = latest_data.get("violent_crime_rate", 0)
            property_crime_rate = latest_data.get("property_crime_rate", 0)
        else:
            # Count data - convert to rates
            violent_crimes = (
                latest_data.get("homicide", 0) +
                latest_data.get("rape_legacy", 0) +
                latest_data.get("rape_revised", 0) +
                latest_data.get("robbery", 0) +
                latest_data.get("aggravated_assault", 0)
            )
            
            property_crimes = (
                latest_data.get("burglary", 0) +
                latest_data.get("larceny", 0) +
                latest_data.get("motor_vehicle_theft", 0) +
                latest_data.get("arson", 0)
            )
            
            # Calculate rates per 100,000 residents
            violent_crime_rate = (violent_crimes / state_population) * 100000 if state_population > 0 else 0
            property_crime_rate = (property_crimes / state_population) * 100000 if state_population > 0 else 0
        
        # Only proceed if we have meaningful data
        if violent_crime_rate == 0 and property_crime_rate == 0:
            return None
        
        # National averages for comparison
        national_violent_avg = 380
        national_property_avg = 1950
        
        # Calculate safety scores (0-100, higher is safer)
        violent_score = max(0, min(100, 100 - (violent_crime_rate / national_violent_avg) * 50))
        property_score = max(0, min(100, 100 - (property_crime_rate / national_property_avg) * 50))
        
        # Overall safety score (weighted: violent crimes matter more for families)
        overall_safety_score = (violent_score * 0.7) + (property_score * 0.3)
        
        return {
            "overall_safety_score": round(overall_safety_score, 1),
            "violent_crime_rate": round(violent_crime_rate, 1),
            "property_crime_rate": round(property_crime_rate, 1),
            "violent_safety_score": round(violent_score, 1),
            "property_safety_score": round(property_score, 1),
            "safety_tier": get_safety_tier(overall_safety_score),
            "family_friendly_rating": get_family_safety_rating(overall_safety_score),
            "data_year": latest_data.get("year", "Unknown"),
            "data_source": "FBI UCR Program"
        }
        
    except Exception:
        return None

def get_safety_tier(safety_score: float) -> str:
    """Convert safety score to descriptive tier"""
    if safety_score >= 80:
        return "Very Safe"
    elif safety_score >= 65:
        return "Safe"
    elif safety_score >= 50:
        return "Moderate"
    elif safety_score >= 35:
        return "Below Average"
    else:
        return "Needs Attention"

def get_family_safety_rating(safety_score: float) -> str:
    """Convert safety score to family-specific rating"""
    if safety_score >= 75:
        return "Excellent for families"
    elif safety_score >= 60:
        return "Good for families"
    elif safety_score >= 45:
        return "Consider with caution"
    else:
        return "Research thoroughly"

def add_crime_data_to_counties(counties_data: list, state_fips: str, state_name: str) -> list:
    """
    Add FBI crime data to counties only if available. No fallbacks or error messages.
    """
    # Only proceed if we have an API key
    if not FBI_API_KEY:
        return counties_data
    
    # Try to get FBI crime data
    crime_data = get_fbi_crime_data_by_state(state_fips)
    
    # If no data available, return counties unchanged (no crime data fields added)
    if not crime_data:
        return counties_data
    
    # Calculate state population for baseline metrics
    state_population = sum(county.get('B01003_001E', 0) for county in counties_data)
    
    # Calculate state-level crime metrics
    state_metrics = calculate_state_crime_metrics(crime_data, state_population)
    
    # If metrics calculation failed, return counties unchanged
    if not state_metrics:
        return counties_data
    
    # Apply crime data to counties with population-based adjustments
    for county in counties_data:
        population = county.get('B01003_001E', 0)
        
        if population > 0:
            # Adjust safety score based on population size
            base_score = state_metrics['overall_safety_score']
            
            if population >= 500000:  # Large urban areas
                adjusted_score = base_score * 0.85
            elif population >= 100000:  # Medium cities
                adjusted_score = base_score * 0.92
            elif population >= 50000:   # Small cities
                adjusted_score = base_score * 0.97
            else:  # Rural/small towns
                adjusted_score = min(100, base_score * 1.05)
            
            county['crime_data'] = {
                "overall_safety_score": round(adjusted_score, 1),
                "safety_tier": get_safety_tier(adjusted_score),
                "family_friendly_rating": get_family_safety_rating(adjusted_score),
                "violent_crime_rate": state_metrics.get('violent_crime_rate'),
                "property_crime_rate": state_metrics.get('property_crime_rate'),
                "data_year": state_metrics.get('data_year'),
                "data_source": state_metrics.get('data_source')
            }
    
    return counties_data

def setup_fbi_api():
    """
    Simple setup function that returns True/False for API availability.
    No error messages printed.
    """
    if not FBI_API_KEY:
        return False
    
    # Test API connection quietly
    try:
        test_url = f"{FBI_API_BASE}/api/agencies"
        response = requests.get(test_url, params={"api_key": FBI_API_KEY, "per_page": 1}, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def calculate_comprehensive_scores(county, state_medians, user_budget):
    """
    Enhanced scoring that accounts for county-level characteristics.
    """
    scores = {}
    
    # Extract key metrics
    home_value = county.get("B25077_001E", 0)
    income = county.get("B19013_001E", 0)
    population = county.get("B01003_001E", 0)
    households_with_kids = county.get("B11005_002E", 0)
    total_households = county.get("B25003_001E", 0)
    owner_occupied = county.get("B25003_002E", 0)
    college_rate = county.get('college_degree_rate', 0)
    
    tier = detect_tier(user_budget)
    
    # 1. AFFORDABILITY SCORE (0-100) - More realistic for counties
    if income > 0:
        price_to_income = home_value / income
        
        if tier in ["luxury", "ultra_luxury"]:
            # Luxury buyers in counties - more realistic ratios
            if 2.5 <= price_to_income <= 5.0:
                scores['affordability'] = 100  # Realistic luxury range
            elif 2.0 <= price_to_income <= 6.0:
                scores['affordability'] = 80
            elif 1.5 <= price_to_income <= 7.0:
                scores['affordability'] = 60
            else:
                scores['affordability'] = 40
        else:
            # Standard affordability calculation
            if price_to_income <= 2.5:
                scores['affordability'] = 100
            elif price_to_income <= 3.5:
                scores['affordability'] = 80
            elif price_to_income <= 4.5:
                scores['affordability'] = 60
            elif price_to_income <= 6.0:
                scores['affordability'] = 40
            else:
                scores['affordability'] = 20
    else:
        scores['affordability'] = 0
    
    # 2. FAMILY FRIENDLINESS SCORE (0-100) - County-focused
    family_score = 0
    
    # Kids factor (0-35 points)
    if total_households > 0:
        kids_ratio = households_with_kids / total_households
        family_score += min(kids_ratio * 100, 35)
    
    # Income stability (0-30 points) - More realistic for counties
    if tier in ["luxury", "ultra_luxury"]:
        if income >= 80000:
            family_score += 30
        elif income >= 65000:
            family_score += 25
        elif income >= 50000:
            family_score += 15
    else:
        if income >= 60000:
            family_score += 30
        elif income >= 45000:
            family_score += 20
        elif income >= 35000:
            family_score += 10
    
    # Population size (0-35 points) - County sweet spots
    if tier in ["luxury", "ultra_luxury"]:
        # Large counties with good infrastructure
        if 200000 <= population <= 1000000:
            family_score += 35  # Major metro counties
        elif 100000 <= population <= 1500000:
            family_score += 25
        elif 75000 <= population:
            family_score += 15
    else:
        # Standard population preferences
        if 50000 <= population <= 500000:
            family_score += 35
        elif 25000 <= population <= 750000:
            family_score += 25
        elif population >= 15000:
            family_score += 15
    
    scores['family_friendly'] = min(family_score, 100)
    
    # 3. ECONOMIC VITALITY SCORE (0-100) - County-level adjustments
    vitality_score = 0
    
    # Income relative to state (0-35 points)
    if state_medians.get("income", 0) > 0:
        income_ratio = income / state_medians["income"]
        vitality_score += min(income_ratio * 35, 35)
    
    # Education level (0-40 points) - More realistic expectations
    if tier in ["luxury", "ultra_luxury"]:
        if college_rate >= 35:
            vitality_score += 40
        elif college_rate >= 25:
            vitality_score += 30
        elif college_rate >= 18:
            vitality_score += 20
        elif college_rate >= 12:
            vitality_score += 10
    else:
        if college_rate >= 25:
            vitality_score += 40
        elif college_rate >= 18:
            vitality_score += 30
        elif college_rate >= 12:
            vitality_score += 20
        elif college_rate >= 8:
            vitality_score += 10
    
    # Population economic potential (0-25 points)
    if population >= 250000:
        vitality_score += 25  # Major economic centers
    elif population >= 100000:
        vitality_score += 20
    elif population >= 50000:
        vitality_score += 15
    elif population >= 25000:
        vitality_score += 10
    
    scores['economic_vitality'] = min(vitality_score, 100)
    
    # 4. HOUSING MARKET STABILITY (0-100) - Same as before
    stability_score = 0
    
    # Homeownership rate (0-50 points)
    if total_households > 0:
        homeownership_rate = owner_occupied / total_households
        stability_score += homeownership_rate * 50
    
    # Home value relative to state (0-50 points)
    if state_medians.get("home_value", 0) > 0:
        value_ratio = home_value / state_medians["home_value"]
        
        if tier in ["luxury", "ultra_luxury"]:
            # Expect above-average values but be realistic
            if 1.1 <= value_ratio <= 2.5:
                stability_score += 50
            elif 0.9 <= value_ratio <= 3.0:
                stability_score += 40
            elif 0.7 <= value_ratio <= 4.0:
                stability_score += 25
        else:
            if 0.8 <= value_ratio <= 1.5:
                stability_score += 50
            elif 0.6 <= value_ratio <= 2.0:
                stability_score += 35
            elif 0.4 <= value_ratio <= 3.0:
                stability_score += 20
    
    scores['housing_stability'] = min(stability_score, 100)
    
    # 5. BUDGET COMPATIBILITY (0-100) - More realistic
    budget_score = 0
    
    if tier == "luxury":
        # Realistic luxury expectations
        if user_budget * 1.0 <= home_value <= user_budget * 2.5:
            budget_score += 40
        if income >= 60000:  # Realistic county income
            budget_score += 30
        if college_rate >= 20:
            budget_score += 30
        if population >= 100000:
            budget_score += 20
    elif tier == "ultra_luxury":
        # Ultra-luxury but realistic
        if home_value >= user_budget * 0.8:
            budget_score += 30
        if income >= 70000:  # Realistic county income
            budget_score += 30
        if college_rate >= 25:
            budget_score += 25
        if population >= 150000:
            budget_score += 25
    
    scores['budget_compatibility'] = min(budget_score, 100)
    
    return scores

def calculate_weighted_score(scores, user_priority, tier):
    """
    Calculate final weighted score based on user priorities and tier.
    Enhanced to include safety scoring.
    """
    # Base weights including safety
    weights = {
        'affordability': 0.18,
        'family_friendly': 0.18,
        'economic_vitality': 0.16,
        'housing_stability': 0.13,
        'budget_compatibility': 0.15,
        'safety': 0.20  # Safety is important for families
    }
    
    # Adjust weights based on user priorities
    if user_priority.get("family"):
        weights['family_friendly'] += 0.10
        weights['safety'] += 0.10  # Families care more about safety
        weights['affordability'] -= 0.05
        weights['economic_vitality'] -= 0.05
        weights['housing_stability'] -= 0.05
        weights['budget_compatibility'] -= 0.05
    
    if user_priority.get("growth"):
        weights['economic_vitality'] += 0.15
        weights['safety'] -= 0.05
        weights['family_friendly'] -= 0.05
        weights['housing_stability'] -= 0.05
    
    # Tier-based weight adjustments
    if tier in ["luxury", "ultra_luxury"]:
        weights['budget_compatibility'] += 0.08
        weights['safety'] += 0.07  # Luxury buyers prioritize safety
        weights['affordability'] -= 0.15
    elif tier == "affordable":
        weights['affordability'] += 0.15
        weights['budget_compatibility'] -= 0.08
        weights['economic_vitality'] -= 0.07
    
    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v/total_weight for k, v in weights.items()}
    
    # Calculate weighted score
    final_score = sum(scores.get(metric, 50) * weight for metric, weight in weights.items())
    return final_score

def get_lifestyle_description(county, scores):
    """Generate a rich description of what life would be like in this county."""
    population = county.get("B01003_001E", 0)
    income = county.get("B19013_001E", 0)
    college_rate = county.get('college_degree_rate', 0)
    home_value = county.get("B25077_001E", 0)
    
    descriptions = []
    
    # Community size and feel
    if population >= 300000:
        descriptions.append("Major metro area with full city amenities")
    elif population >= 100000:
        descriptions.append("Mid-size city with urban conveniences")
    elif population >= 50000:
        descriptions.append("Suburban community with local charm")
    elif population >= 25000:
        descriptions.append("Small town atmosphere with necessary services")
    else:
        descriptions.append("Rural/small town setting")
    
    # Economic character
    if income >= 100000:
        descriptions.append("affluent community")
    elif income >= 70000:
        descriptions.append("upper-middle class area")
    elif income >= 50000:
        descriptions.append("middle-class neighborhood")
    else:
        descriptions.append("working-class community")
    
    # Education/Culture
    if college_rate >= 35:
        descriptions.append("highly educated population")
    elif college_rate >= 25:
        descriptions.append("well-educated residents")
    
    # Housing market
    if home_value >= 500000:
        descriptions.append("premium housing market")
    elif home_value >= 300000:
        descriptions.append("solid property values")
    elif home_value >= 200000:
        descriptions.append("affordable housing options")
    else:
        descriptions.append("budget-friendly real estate")
    
    # Quality indicators
    if scores['family_friendly'] >= 80:
        descriptions.append("excellent for families")
    elif scores['family_friendly'] >= 60:
        descriptions.append("family-friendly environment")
    
    if scores['economic_vitality'] >= 80:
        descriptions.append("strong job market")
    elif scores['economic_vitality'] >= 60:
        descriptions.append("stable employment opportunities")
    
    # Safety indicators (only if available)
    if 'safety' in scores:
        if scores['safety'] >= 75:
            descriptions.append("very safe community")
        elif scores['safety'] >= 60:
            descriptions.append("safe neighborhood")
    
    return "; ".join(descriptions)

def smart_filter_counties(counties_data, user_priority, user_budget, keep_top_n=30):
    """
    Simplified version - main filtering happens in process_counties_with_tagging
    """
    if not counties_data:
        return []
    
    # Just basic viability check - detailed filtering happens later
    min_population = 10000
    min_income = 30000
    min_home_value = 50000
    
    viable_counties = []
    for county in counties_data:
        if (county.get('B01003_001E', 0) >= min_population and
            county.get('B19013_001E', 0) >= min_income and
            county.get('B25077_001E', 0) >= min_home_value):
            viable_counties.append(county)
    
    return viable_counties[:keep_top_n]

def calculate_college_degree_rate(county):
    """Calculate the percentage of adults (25+) with a bachelor's degree or higher."""
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
    """Calculate state medians for dynamic filtering and tier-based scoring."""
    if not counties_data:
        return {"population": 0, "income": 0, "home_value": 0, "degree_rate": 0}
    
    populations = [c.get('B01003_001E', 0) for c in counties_data if c.get('B01003_001E', 0) > 0]
    incomes = [c.get('B19013_001E', 0) for c in counties_data if c.get('B19013_001E', 0) > 0]
    home_values = [c.get('B25077_001E', 0) for c in counties_data if c.get('B25077_001E', 0) > 0]
    degree_rates = [c.get('college_degree_rate', 0) for c in counties_data if c.get('college_degree_rate', 0) > 0]
    
    return {
        "population": statistics.median(populations) if populations else 0,
        "income": statistics.median(incomes) if incomes else 0,
        "home_value": statistics.median(home_values) if home_values else 0,
        "degree_rate": statistics.median(degree_rates) if degree_rates else 0
    }

def detect_tier(user_budget):
    """Returns budget/income tier string."""
    if user_budget >= 5_000_000:
        return "ultra_luxury"
    elif user_budget >= 1_000_000:
        return "luxury"
    elif user_budget >= 400_000:
        return "move_up"
    else:
        return "affordable"

def parse_user_priority(user_preferences: str) -> dict:
    """Enhanced priority parsing that captures lifestyle preferences."""
    priority = {
        "budget": True,
        "family": False,
        "community_type": None,
        "growth": False,
        "lifestyle": user_preferences.lower() if user_preferences else ""
    }
    
    if not user_preferences:
        return priority
        
    pref_lower = user_preferences.lower()
    
    # Family priorities
    family_keywords = ["family", "children", "kids", "school", "safety", "child"]
    if any(keyword in pref_lower for keyword in family_keywords):
        priority["family"] = True
        
    # Community type - ENHANCED detection
    if any(word in pref_lower for word in ["urban", "city", "downtown", "metropolitan"]):
        priority["community_type"] = "urban"
    elif any(word in pref_lower for word in ["suburban", "suburb", "neighborhood", "good schools", "family"]):
        priority["community_type"] = "suburban"  
    elif any(word in pref_lower for word in ["rural", "small town", "country", "quiet"]):
        priority["community_type"] = "rural"
        
    # Growth priorities
    growth_keywords = ["growth", "investment", "job", "economic", "opportunity", "tech", "development"]
    if any(keyword in pref_lower for keyword in growth_keywords):
        priority["growth"] = True
        
    return priority

def calculate_homeownership_rate_for_tags(county):
    """Calculate homeownership rate for tags dictionary"""
    owner_occupied = county.get('B25003_002E', 0)
    total_households = county.get('B25003_001E', 0)
    
    if total_households > 0:
        rate = (owner_occupied / total_households) * 100
        return f"{rate:.1f}%"
    return "N/A"

def process_counties_with_tagging(counties, user_priority, state_medians, user_budget, state_name=None):
    """
    Apply improved scoring and sorting to counties with strict filtering for high-income users.
    """
    if not counties:
        return []
    
    tier = detect_tier(user_budget)
    
    # STEP 1: Apply strict pre-filtering based on user requirements
    filtered_counties = apply_smart_filtering(counties, user_priority, user_budget, tier)
    
    if not filtered_counties:
        return []
    
    # STEP 2: Apply best counties filter for higher tiers
    if tier in ("move_up", "luxury", "ultra_luxury") and state_name and state_name in BEST_COUNTIES_PER_STATE:
        best_county_names = BEST_COUNTIES_PER_STATE[state_name]
        best_counties = [c for c in filtered_counties if c.get("name") in best_county_names]
        
        if best_counties:
            filtered_counties = best_counties
    
    # STEP 3: Calculate comprehensive scores for each county
    for county in filtered_counties:
        # Add college degree rate
        county['college_degree_rate'] = calculate_college_degree_rate(county)
        
        # Calculate multi-dimensional scores
        scores = calculate_comprehensive_scores(county, state_medians, user_budget)
        
        # Calculate weighted final score
        final_score = calculate_weighted_score(scores, user_priority, tier)
        
        # Store scores and metadata
        county['scores'] = scores
        county['final_score'] = final_score
        county['lifestyle_description'] = get_lifestyle_description(county, scores)
        county['tier'] = tier
        
        # Create user-friendly tags
        county['tags'] = {
            'budget_friendly': scores['affordability'] >= 70,
            'family_friendly': scores['family_friendly'] >= 70,
            'strong_economy': scores['economic_vitality'] >= 70,
            'stable_housing': scores['housing_stability'] >= 70,
            'tier_match': scores['budget_compatibility'] >= 70,
            'homeownership_rate': calculate_homeownership_rate_for_tags(county),
            'notable_family_feature': get_notable_feature(county, scores)
        }
    
    # STEP 4: Sort by final score and return top counties
    filtered_counties.sort(key=lambda x: x['final_score'], reverse=True)
    
    return filtered_counties[:25]

def apply_smart_filtering(counties, user_priority, user_budget, tier):
    """
    Apply realistic filtering that works with real county data.
    """
    lifestyle = user_priority.get("lifestyle", "").lower()
    community_type = user_priority.get("community_type", "")
    
    # VERY REALISTIC county-level requirements
    if tier == "ultra_luxury":
        min_population = 100000      # Major metros only
        min_income = 45000          # Realistic county medians
        min_home_value = 150000     # Realistic minimums
        min_college_rate = 12       # Achievable education levels
    elif tier == "luxury":
        min_population = 75000      # Substantial counties
        min_income = 40000          # Very achievable
        min_home_value = 130000     # Reasonable minimum
        min_college_rate = 10       # Basic education filter
    elif tier == "move_up":
        min_population = 50000
        min_income = 35000
        min_home_value = 100000
        min_college_rate = 8
    else:  # affordable
        min_population = 25000
        min_income = 30000
        min_home_value = 80000
        min_college_rate = 6
    
    # Lifestyle adjustments (moderate)
    if "suburban" in lifestyle or community_type == "suburban":
        if tier in ["luxury", "ultra_luxury"]:
            min_population = max(min_population, 150000)  # Need substantial metros
        else:
            min_population = max(min_population, 75000)
    elif "urban" in lifestyle or community_type == "urban":
        min_population = max(min_population, 100000)
    elif "rural" in lifestyle or community_type == "rural":
        min_population = max(15000, min_population // 2)
    
    # High-income + suburban = major metro requirement (realistic)
    if user_budget >= 800000 and ("suburban" in lifestyle or community_type == "suburban"):
        min_population = max(min_population, 200000)  # Major metros
        min_income = max(min_income, 50000)           # Still realistic
    
    # Apply filters
    filtered = []
    
    for county in counties:
        population = county.get('B01003_001E', 0)
        income = county.get('B19013_001E', 0)
        home_value = county.get('B25077_001E', 0)
        college_rate = calculate_college_degree_rate(county)
        
        # Check each requirement
        if (population >= min_population and
            income >= min_income and
            home_value >= min_home_value and
            college_rate >= min_college_rate):
            filtered.append(county)
    
    # If we need more counties, be more flexible
    if len(filtered) < 3:
        # Emergency relaxed standards
        emergency_pop = max(50000, min_population // 2)
        emergency_income = max(25000, min_income * 0.7)
        emergency_home = max(60000, min_home_value * 0.6)
        emergency_college = max(5, min_college_rate * 0.5)
        
        additional = []
        for county in counties:
            if county in filtered:
                continue
                
            population = county.get('B01003_001E', 0)
            income = county.get('B19013_001E', 0)
            home_value = county.get('B25077_001E', 0)
            college_rate = calculate_college_degree_rate(county)
            
            if (population >= emergency_pop and
                income >= emergency_income and
                home_value >= emergency_home and
                college_rate >= emergency_college):
                additional.append(county)
        
        filtered.extend(additional)
    
    # Sort by population to prioritize major metros
    filtered.sort(key=lambda x: x.get('B01003_001E', 0), reverse=True)
    
    return filtered

def get_notable_feature(county, scores):
    """Generate a notable feature description based on scores including optional safety"""
    features = []
    
    # Safety indicators (only if available)
    if 'safety' in scores:
        if scores['safety'] >= 90:
            features.append("Exceptionally safe community")
        elif scores['safety'] >= 75:
            features.append("Very safe neighborhood")
    
    if scores['affordability'] >= 90:
        features.append("Exceptional home value")
    elif scores['affordability'] >= 70:
        features.append("Great affordability")
    
    if scores['family_friendly'] >= 90:
        features.append("Outstanding family environment")
    elif scores['family_friendly'] >= 70:
        features.append("Family-friendly community")
    
    if scores['economic_vitality'] >= 90:
        features.append("Thriving job market")
    elif scores['economic_vitality'] >= 70:
        features.append("Strong local economy")
    
    if scores['housing_stability'] >= 90:
        features.append("Rock-solid housing market")
    elif scores['housing_stability'] >= 70:
        features.append("Stable property values")
    
    return features[0] if features else "Solid community choice"

def extract_tool_results_from_messages(messages):
    """Extract and parse tool results from message history"""
    tool_results = [msg for msg in messages if hasattr(msg, 'type') and msg.type == 'tool']
    
    if len(tool_results) == 1:
        content = tool_results[0].content
        if isinstance(content, str):
            try:
                import json
                return json.loads(content)
            except json.JSONDecodeError:
                return {}
        return content if isinstance(content, dict) else {}
    
    elif len(tool_results) >= 2:
        results = {}
        for i, key in enumerate(['state1', 'state2']):
            content = tool_results[-(2-i)].content if hasattr(tool_results[-(2-i)], 'content') else {}
            if isinstance(content, str):
                try:
                    import json
                    results[key] = json.loads(content)
                except json.JSONDecodeError:
                    results[key] = {}
            else:
                results[key] = content if isinstance(content, dict) else {}
        return results
    
    return {}

def real_estate_investment_tool(state_fips: str, state_name: str, comparison_states: str = "", filter_bucket: str = "default") -> Dict[str, Any]:
    """Get residential real estate data for a specific state with NO pre-filtering."""
    if not state_fips or not state_name:
        return {"error": "FIPS code and state name are required."}
    
    # Comprehensive variable set
    variables = "B25077_001E,B19013_001E,B25064_001E,B01003_001E,B11005_002E,B25003_001E,B25003_002E,B15003_022E,B15003_023E,B15003_024E,B15003_025E,B15003_001E"
    result = get_census_data(state_fips, variables)
    
    if result["error"]:
        return {"error": result["error"]}
    
    # Process the data
    header, rows = result["data"][0], result["data"][1:]
    counties_data = []
    
    all_vars = ["B25077_001E", "B19013_001E", "B25064_001E", "B01003_001E", "B11005_002E", 
                "B25003_001E", "B25003_002E", "B15003_022E", "B15003_023E", "B15003_024E", 
                "B15003_025E", "B15003_001E"]
    
    for row in rows:
        county_data = dict(zip(header, row))
        try:
            processed_data = {"name": county_data.get('NAME')}
            for var in all_vars:
                value = county_data.get(var, 0)
                processed_data[var] = int(value) if value and value != '' else 0
            
            # Calculate derived metrics
            processed_data['college_degree_rate'] = calculate_college_degree_rate(processed_data)
            
            # Only exclude counties with truly invalid data
            population = processed_data['B01003_001E']
            income = processed_data['B19013_001E'] 
            home_value = processed_data['B25077_001E']
            
            if population > 0 and income >= 0 and home_value >= 0:
                counties_data.append(processed_data)
                
        except (ValueError, TypeError):
            continue
    
    # Just sort by population to prioritize major metros
    counties_data = sorted(counties_data, key=lambda x: x.get('B01003_001E', 0), reverse=True)
    
    return {
        "data": {state_name: {"data": counties_data}},
        "source": "2022 ACS 5-Year Estimates",
        "state_analyzed": state_name,
        "filter_bucket": filter_bucket,
        "total_counties": len(counties_data)
    }

# Image functions
def fetch_unsplash_image_urls(query, count=1, access_key=UNSPLASH_ACCESS_KEY):
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "per_page": count,
        "orientation": "landscape",
        "client_id": access_key
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("results", [])
        images = [(img["id"], img["urls"]["regular"], "Unsplash") for img in results]
        return images
    except Exception:
        return []

def fetch_pexels_image_urls(query, count=1, api_key=PEXELS_API_KEY):
    url = "https://api.pexels.com/v1/search"
    headers = {
        "Authorization": api_key
    }
    params = {
        "query": query,
        "per_page": count,
        "orientation": "landscape"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("photos", [])
        images = [(img["id"], img["src"]["large"], "Pexels") for img in results]
        return images
    except Exception:
        return []

def fetch_wikipedia_images(county_name, state_name, count=3):
    """Fetch images from Wikipedia for a county/state combination, filtering out road signs."""
    images = []
    
    # Clean county name for search
    county_clean = county_name.replace(" County", "").replace(" Parish", "")
    
    # Try different Wikipedia search strategies
    search_terms = [
        f"{county_clean} County, {state_name}",
        f"{county_clean}, {state_name}",
        f"{state_name} {county_clean}",
        f"{county_clean} County"
    ]
    
    for search_term in search_terms:
        try:
            # Use Wikipedia API to search for pages
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": search_term,
                "srlimit": 5
            }
            
            response = requests.get(search_url, params=search_params, timeout=5)
            response.raise_for_status()
            search_results = response.json()
            
            if "query" in search_results and "search" in search_results["query"]:
                for result in search_results["query"]["search"][:2]:  # Try first 2 results
                    page_id = result["pageid"]
                    
                    # Get images from this page
                    image_params = {
                        "action": "query",
                        "format": "json",
                        "prop": "images",
                        "pageids": page_id,
                        "imlimit": 10
                    }
                    
                    img_response = requests.get(search_url, params=image_params, timeout=5)
                    img_response.raise_for_status()
                    img_results = img_response.json()
                    
                    if "query" in img_results and "pages" in img_results["query"]:
                        page_data = img_results["query"]["pages"].get(str(page_id), {})
                        if "images" in page_data:
                            for img in page_data["images"][:count*2]:  # fetch more to allow filtering
                                img_title = img["title"]
                                # Filter out likely road signs
                                title_lower = img_title.lower()
                                if any(word in title_lower for word in ["sign", "route", "highway", "shield", "svg", "marker", "exit", "interstate", "us_", "state_", "circle", "triangle", "pentagon", "hexagon", "octagon"]):
                                    continue
                                # Get image URL
                                img_url_params = {
                                    "action": "query",
                                    "format": "json",
                                    "prop": "imageinfo",
                                    "titles": img_title,
                                    "iiprop": "url|size|mime"
                                }
                                img_url_response = requests.get(search_url, params=img_url_params, timeout=5)
                                img_url_response.raise_for_status()
                                img_url_results = img_url_response.json()
                                if "query" in img_url_results and "pages" in img_url_results["query"]:
                                    for page_id_str, page_info in img_url_results["query"]["pages"].items():
                                        if "imageinfo" in page_info and page_info["imageinfo"]:
                                            img_info = page_info["imageinfo"][0]
                                            # Only include images that are reasonable size and format
                                            url = img_info.get("url", "")
                                            if (img_info.get("width", 0) >= 300 and 
                                                img_info.get("height", 0) >= 200 and
                                                img_info.get("mime", "").startswith("image/") and
                                                not any(word in url.lower() for word in ["sign", "route", "highway", "shield", "svg", "marker", "exit", "interstate", "us_", "state_", "circle", "triangle", "pentagon", "hexagon", "octagon"])):
                                                images.append((url, "Wikipedia"))

                                                if len(images) >= count:
                                                    return images
                                    
        except Exception:
            # Continue to next search term if this one fails
            continue
    
    return images

def fetch_serper_image_urls(query, count=3, api_key=None):
    if api_key is None:
        api_key = os.getenv("SERPER_API_KEY")
    url = "https://google.serper.dev/images"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    params = {"q": query, "num": count}
    try:
        response = requests.post(url, headers=headers, json=params, timeout=5)
        response.raise_for_status()
        results = response.json().get("images", [])
        images = []
        for img in results:
            title = img.get("title", "").lower()
            img_url = img.get("imageUrl", "")
            # Filter out road signs and similar irrelevant images
            if any(word in title for word in ["sign", "route", "highway", "shield", "svg", "marker", "exit", "interstate", "us_", "state_", "circle", "triangle", "pentagon", "hexagon", "octagon"]):
                continue
            if any(word in img_url.lower() for word in ["sign", "route", "highway", "shield", "svg", "marker", "exit", "interstate", "us_", "state_", "circle", "triangle", "pentagon", "hexagon", "octagon"]):
                continue
            images.append((img_url, "Google"))
            if len(images) >= count:
                break
        return images
    except Exception:
        return []

def get_county_images(county_name, state_name, county_seat=None, used_urls=None):
    seen_urls = set() if used_urls is None else set(used_urls)
    images = []
    county_clean = county_name.replace(" County", "").replace(" Parish", "")
    import hashlib
    county_hash = hashlib.md5(f"{county_name}{state_name}".encode()).hexdigest()
    seed_offset = int(county_hash[:4], 16) % 1000
    queries = []
    if county_seat:
        queries.append(f"{county_seat} {county_clean} {state_name} downtown")
        queries.append(f"{county_seat} {county_clean} {state_name} main street")
        queries.append(f"{county_seat} {county_clean} {state_name} courthouse")
        queries.append(f"{county_seat} {county_clean} {state_name} aerial")
        queries.append(f"{county_seat} {county_clean} {state_name} landmark")
        queries.append(f"{county_seat} {county_clean} {state_name} historic")
    queries.append(f"{county_clean} {state_name} downtown")
    queries.append(f"{county_clean} {state_name} main street")
    queries.append(f"{county_clean} {state_name} courthouse")
    queries.append(f"{county_clean} {state_name} aerial")
    queries.append(f"{county_clean} {state_name} landmark")
    queries.append(f"{county_clean} {state_name} historic")
    queries.append(f"{county_clean} {state_name} cityscape")
    queries.append(f"{county_clean} {state_name} architecture")
    for i, query in enumerate(queries):
        if len(images) >= 10:
            return images[:10]
        modified_query = f"{query} {seed_offset + i}"
        # Serper (Google Images)
        serper_images = fetch_serper_image_urls(modified_query, 2)
        for url, source in serper_images:
            if url not in seen_urls:
                images.append((url, source))
                seen_urls.add(url)
                if len(images) >= 10:
                    return images[:10]
        # Unsplash
        id_url_source_pairs = fetch_unsplash_image_urls(modified_query, 2)
        for _id, url, source in id_url_source_pairs:
            if url not in seen_urls:
                images.append((url, source))
                seen_urls.add(url)
                if len(images) >= 10:
                    return images[:10]
        # Pexels
        id_url_source_pairs = fetch_pexels_image_urls(modified_query, 2)
        for _id, url, source in id_url_source_pairs:
            if url not in seen_urls:
                images.append((url, source))
                seen_urls.add(url)
                if len(images) >= 10:
                    return images[:10]
    # Wikipedia
    wiki_images = fetch_wikipedia_images(county_name, state_name, 3)
    for url, source in wiki_images:
        if url not in seen_urls:
            images.append((url, source))
            seen_urls.add(url)
            if len(images) >= 10:
                return images[:10]
    return images[:10]

def calculate_comprehensive_scores(county, state_medians, user_budget):
    """
    Calculate multiple scoring dimensions for more nuanced ranking.
    Crime data is optional - if not available, uses other metrics.
    Returns a dictionary of scores (0-100 scale).
    """
    scores = {}
    
    # Extract key metrics
    home_value = county.get("B25077_001E", 0)
    income = county.get("B19013_001E", 0)
    population = county.get("B01003_001E", 0)
    households_with_kids = county.get("B11005_002E", 0)
    total_households = county.get("B25003_001E", 0)
    owner_occupied = county.get("B25003_002E", 0)
    college_rate = county.get('college_degree_rate', 0)
    
    # 1. AFFORDABILITY SCORE (0-100)
    if income > 0:
        price_to_income = home_value / income
        if price_to_income <= 2.5:
            scores['affordability'] = 100
        elif price_to_income <= 3.5:
            scores['affordability'] = 80
        elif price_to_income <= 4.5:
            scores['affordability'] = 60
        elif price_to_income <= 6.0:
            scores['affordability'] = 40
        else:
            scores['affordability'] = 20
    else:
        scores['affordability'] = 0
    
    # 2. FAMILY FRIENDLINESS SCORE (0-100)
    family_score = 0
    
    # Kids factor (0-40 points)
    if total_households > 0:
        kids_ratio = households_with_kids / total_households
        family_score += min(kids_ratio * 100, 40)
    
    # Income stability (0-30 points)
    if income >= 70000:
        family_score += 30
    elif income >= 50000:
        family_score += 20
    elif income >= 35000:
        family_score += 10
    
    # Population size (0-30 points) - sweet spot for families
    if 50000 <= population <= 200000:
        family_score += 30
    elif 25000 <= population <= 300000:
        family_score += 20
    elif 10000 <= population <= 500000:
        family_score += 10
    
    scores['family_friendly'] = min(family_score, 100)
    
    # 3. ECONOMIC VITALITY SCORE (0-100)
    vitality_score = 0
    
    # Income relative to state (0-40 points)
    if state_medians.get("income", 0) > 0:
        income_ratio = income / state_medians["income"]
        vitality_score += min(income_ratio * 40, 40)
    
    # Education level (0-35 points)
    if college_rate >= 35:
        vitality_score += 35
    elif college_rate >= 25:
        vitality_score += 25
    elif college_rate >= 15:
        vitality_score += 15
    
    # Population growth potential (0-25 points)
    if population >= 100000:
        vitality_score += 25
    elif population >= 50000:
        vitality_score += 15
    elif population >= 25000:
        vitality_score += 10
    
    scores['economic_vitality'] = min(vitality_score, 100)
    
    # 4. HOUSING MARKET STABILITY (0-100)
    stability_score = 0
    
    # Homeownership rate (0-50 points)
    if total_households > 0:
        homeownership_rate = owner_occupied / total_households
        stability_score += homeownership_rate * 50
    
    # Home value relative to state (0-50 points)
    if state_medians.get("home_value", 0) > 0:
        value_ratio = home_value / state_medians["home_value"]
        if 0.8 <= value_ratio <= 1.5:
            stability_score += 50
        elif 0.6 <= value_ratio <= 2.0:
            stability_score += 35
        elif 0.4 <= value_ratio <= 3.0:
            stability_score += 20
    
    scores['housing_stability'] = min(stability_score, 100)
    
    # 5. BUDGET COMPATIBILITY (0-100)
    budget_score = 0
    tier = detect_tier(user_budget)
    
    if tier == "affordable":
        # Prioritize affordability and value
        if home_value <= user_budget * 3:
            budget_score += 50
        if income >= 40000:
            budget_score += 30
        if price_to_income <= 3.5:
            budget_score += 20
    elif tier == "move_up":
        # Balance of quality and price
        if user_budget * 2 <= home_value <= user_budget * 4:
            budget_score += 40
        if income >= 70000:
            budget_score += 30
        if college_rate >= 20:
            budget_score += 30
    elif tier == "luxury":
        # Quality and prestige
        if home_value >= user_budget * 2:
            budget_score += 30
        if income >= 100000:
            budget_score += 35
        if college_rate >= 30:
            budget_score += 35
    elif tier == "ultra_luxury":
        # Premium everything
        if home_value >= user_budget * 1.5:
            budget_score += 25
        if income >= 150000:
            budget_score += 25
        if college_rate >= 35:
            budget_score += 25
        if population >= 100000:
            budget_score += 25
    
    scores['budget_compatibility'] = min(budget_score, 100)
    
    # 6. SAFETY SCORE (0-100) - OPTIONAL
    crime_data = county.get('crime_data')
    if crime_data:
        safety_score = crime_data.get('overall_safety_score', 50)
        if isinstance(safety_score, (int, float)) and safety_score > 0:
            scores['safety'] = safety_score
        else:
            scores['safety'] = 50  # Neutral score if invalid data
    # If no crime data, don't include safety in scores
    
    return scores

def calculate_weighted_score(scores, user_priority, tier):
    """
    Calculate final weighted score based on user priorities and tier.
    Automatically adjusts weights if safety data is not available.
    """
    has_safety = 'safety' in scores
    
    if has_safety:
        # Base weights including safety
        weights = {
            'affordability': 0.18,
            'family_friendly': 0.18,
            'economic_vitality': 0.16,
            'housing_stability': 0.13,
            'budget_compatibility': 0.15,
            'safety': 0.20
        }
    else:
        # Weights without safety - redistribute safety weight
        weights = {
            'affordability': 0.22,  # +0.04
            'family_friendly': 0.23,  # +0.05  
            'economic_vitality': 0.20,  # +0.04
            'housing_stability': 0.16,  # +0.03
            'budget_compatibility': 0.19   # +0.04
        }
    
    # Adjust weights based on user priorities
    if user_priority.get("family"):
        weights['family_friendly'] += 0.10
        if has_safety:
            weights['safety'] += 0.10
        else:
            weights['affordability'] += 0.05  # Extra emphasis if no safety data
            weights['housing_stability'] += 0.05
        
        # Reduce other weights proportionally
        reduction_per_category = 0.20 / (len(weights) - 1 - (1 if has_safety else 0))
        for key in weights:
            if key not in ['family_friendly', 'safety']:
                weights[key] = max(0.05, weights[key] - reduction_per_category)
    
    if user_priority.get("growth"):
        weights['economic_vitality'] += 0.15
        # Reduce other weights proportionally
        reduction_per_category = 0.15 / (len(weights) - 1)
        for key in weights:
            if key != 'economic_vitality':
                weights[key] = max(0.05, weights[key] - reduction_per_category)
    
    # Tier-based weight adjustments
    if tier in ["luxury", "ultra_luxury"]:
        weights['budget_compatibility'] += 0.08
        if has_safety:
            weights['safety'] += 0.07
        weights['affordability'] = max(0.05, weights['affordability'] - 0.15)
    elif tier == "affordable":
        weights['affordability'] += 0.15
        weights['budget_compatibility'] = max(0.05, weights['budget_compatibility'] - 0.08)
        weights['economic_vitality'] = max(0.05, weights['economic_vitality'] - 0.07)
    
    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v/total_weight for k, v in weights.items()}
    
    # Calculate weighted score using only available metrics
    final_score = sum(scores.get(metric, 50) * weight for metric, weight in weights.items() if metric in scores)
    return final_score