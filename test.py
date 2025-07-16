# Test script - create test_census.py
from tools import debug_census_data_retrieval

# Test Texas specifically
texas_counties = debug_census_data_retrieval("48", "Texas")
print(f"Found {len(texas_counties)} Texas counties")