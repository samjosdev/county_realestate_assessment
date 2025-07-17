import os
from typing import Dict, Any
from dotenv import load_dotenv

# Import from new modular structure
from data_sources.census_api import get_census_data
from data_sources.image_apis import get_county_images
from scoring.county_scoring import calculate_state_medians
from scoring.filtering import process_counties_with_tagging
from utils.user_preferences import parse_user_priority
from utils.data_processing import extract_tool_results_from_messages

load_dotenv()

def real_estate_investment_tool(state_fips: str, state_name: str, comparison_states: str = "", filter_bucket: str = "default") -> Dict[str, Any]:
    """Get residential real estate data for a specific state with NO pre-filtering."""
    if not state_fips or not state_name:
        return {"error": "FIPS code and state name are required."}
    
    # Define census variables to fetch
    variables = (
        "B01003_001E,"  # Total population
        "B19013_001E,"  # Median household income
        "B25077_001E,"  # Median home value
        "B25003_001E,"  # Total occupied housing units
        "B25003_002E,"  # Owner-occupied housing units
        "B11005_002E,"  # Households with children
        "B15003_001E,"  # Total population 25+ for education
        "B15003_022E,"  # Bachelor's degree
        "B15003_023E,"  # Master's degree
        "B15003_024E,"  # Professional degree
        "B15003_025E"   # Doctorate degree
    )
    
    # Fetch census data
    census_result = get_census_data(state_fips, variables)
    
    if census_result.get("error"):
        return {"error": f"Census API error: {census_result['error']}"}
    
    raw_data = census_result.get("data", [])
    if not raw_data or len(raw_data) < 2:  # Header + at least one county
        return {"error": "No county data found for this state."}
    
    # Process the data
    headers = raw_data[0]
    counties_data = []
    
    for row in raw_data[1:]:
        try:
            # Create county data dictionary
            processed_data = dict(zip(headers, row))
            
            # Convert numeric fields
            for key in ["B01003_001E", "B19013_001E", "B25077_001E", "B25003_001E", 
                       "B25003_002E", "B11005_002E", "B15003_001E", "B15003_022E",
                       "B15003_023E", "B15003_024E", "B15003_025E"]:
                try:
                    processed_data[key] = int(processed_data.get(key, 0))
                except (ValueError, TypeError):
                    processed_data[key] = 0
            
            # Extract county name
            county_name = processed_data.get("NAME", "")
            if "," in county_name:
                county_name = county_name.split(",")[0].strip()
            processed_data["name"] = county_name
            
            # Add college degree rate
            from scoring.county_scoring import calculate_college_degree_rate
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