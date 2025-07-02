# US Census Language Data API

A simple Python script to connect to the US Census API and pull population data by state by language speaking.

## Features

- Fetches language data from the American Community Survey (ACS)
- No API key required for basic data access
- Supports both summary and detailed language breakdowns
- Returns data in JSON format
- Includes pandas DataFrame conversion for analysis

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the main script to get language data for all states:

```bash
python census_api.py
```

### Example Usage

Run the example script for a formatted output:

```bash
python example_usage.py
```

### Programmatic Usage

```python
from census_api import CensusAPI

# Initialize the API client
census = CensusAPI()

# Get language data by state for 2021
result = census.get_language_by_state(2021)

if result["success"]:
    print(f"Retrieved data for {result['total_states']} states")
    
    # Access the data
    for state in result["data"]:
        state_name = state["NAME"]
        total_pop = state["B16001_001E"]
        english_only = state["B16001_002E"]
        spanish = state["B16001_003E"]
        print(f"{state_name}: {total_pop} total, {english_only} English only, {spanish} Spanish")
```

## Data Variables

The script fetches the following language variables from the ACS:

- `B16001_001E`: Total population 5 years and over
- `B16001_002E`: Speak only English
- `B16001_003E`: Speak Spanish
- `B16001_006E`: Speak other Indo-European languages
- `B16001_009E`: Speak Asian and Pacific Island languages
- `B16001_012E`: Speak other languages

## Output Files

- `census_language_data.json`: Raw API response data
- `census_language_by_state.json`: Formatted state-by-state data

## API Endpoints

The script uses the following Census API endpoints:

- **Base URL**: `https://api.census.gov/data`
- **ACS 5-year estimates**: `/{year}/acs/acs5`
- **Geographic level**: State-level data (`for=state:*`)

## Notes

- No API key is required for basic ACS data access
- Data is from the American Community Survey 5-year estimates
- Latest available year is typically 2021 (5-year estimates lag by 2-3 years)
- All population counts are for people 5 years and older

## Error Handling

The script includes comprehensive error handling for:
- Network connection issues
- API rate limiting
- Invalid parameters
- Missing data

## License

This project is open source and available under the MIT License. 