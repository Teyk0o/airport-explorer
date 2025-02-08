# Airport Data Directory

This directory contains the processed airport data organized by country and region.

## Directory Structure

```
data/
├── countries.json          # Index of all countries with airport counts
└── {country_code}/        # Country-specific directories (lowercase)
    └── airports.json      # Airport data for the country
```

## File Formats

### countries.json
```json
[
  {
    "code": "US",
    "name": "United States",
    "airport_count": 21458
  },
  ...
]
```

### airports.json
```json
[
  {
    "name": "John F Kennedy International Airport",
    "type": "large_airport",
    "coordinates": "40.6398, -73.7789",
    "elevation_ft": 13,
    "iata_code": "JFK",
    "local_code": "JFK",
    "region": "US-NY"
  },
  ...
]
```

## Data Update Process

1. Data is automatically updated daily via GitHub Actions
2. Only changed files are committed to avoid unnecessary updates
3. Each update preserves the existing structure
4. Missing or invalid data is handled gracefully

## Usage Notes

- All coordinates are in decimal degrees (latitude, longitude)
- Elevation is in feet
- Region codes follow ISO 3166-2 standard
- IATA codes may be null for smaller airports

## Error Handling

If data files are missing or corrupted:
1. The web interface will show appropriate error messages
2. The update process will log errors in GitHub Actions
3. Previous valid data will be preserved

## Contributing

If you notice any data inconsistencies, please:
1. Open an issue describing the problem
2. Provide the country and airport details
3. Include any relevant source information