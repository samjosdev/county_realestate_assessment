import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

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