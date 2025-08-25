import os

import pandas as pd
from io import StringIO
import json
import requests
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


AIRPORTDB_API = "https://airportdb.io/api/v1/airport/"
METAR_API = "https://aviationweather.gov/api/data/metar"
PRIORITIZED_TYPES = {"large_airport", "medium_airport"}
WESTERN_EUROPE = {
    "FR", "GB", "IE", "DE", "NL", "BE", "LU", "CH", "AT", "ES", "PT", "IT",
    "AD", "LI", "MC"
}


class AirportDataUpdater:
    def __init__(self, source_url: str, data_dir: Path):
        self.source_url = source_url
        self.data_dir = data_dir
        self.countries_data: Dict[str, List[Dict]] = {}
        self.total_airports = 0
        self.country_names = {}
        # Cache for airport details to avoid hitting the API repeatedly
        self._airport_cache: Dict[str, Dict] = {}
        self.api_key = os.getenv("AIRPORTDB_API_KEY")

    def load_country_names(self) -> None:
        """Load country names from country.io"""
        try:
            print("Loading country names...")
            response = requests.get("https://country.io/names.json")
            response.raise_for_status()
            self.country_names = response.json()
            print(f"Loaded {len(self.country_names)} country names")
        except Exception as e:
            print(f"Warning: Could not load country names: {str(e)}")
            self.country_names = {}

    def get_country_name(self, code: str) -> str:
        """Get full country name from code"""
        return self.country_names.get(code, code)

    def download_source_data(self) -> Optional[pd.DataFrame]:
        try:
            print("Downloading airport data...")
            response = requests.get(self.source_url)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            self.total_airports = len(df)
            print(f"Downloaded {self.total_airports} airports")
            return df
        except Exception as e:
            print(f"Error downloading data: {str(e)}")
            return None

    def fetch_airport_details(self, ident: str) -> Dict:
        """Fetch additional airport information from airportdb.io"""
        if not self.api_key:
            return {}
        if ident in self._airport_cache:
            return self._airport_cache[ident]
        try:
            headers = {"X-API-Key": self.api_key}
            response = requests.get(f"{AIRPORTDB_API}{ident}", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                self._airport_cache[ident] = data
                return data
        except Exception:
            pass
        return {}

    def check_metar_available(self, ident: str) -> bool:
        """Check if METAR data is available for the airport"""
        try:
            params = {"ids": ident, "format": "json"}
            response = requests.get(METAR_API, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                return bool(data)
            if isinstance(data, list):
                return len(data) > 0
            return False
        except Exception:
            return False

    def process_airports(self, df: pd.DataFrame) -> None:
        print("\nProcessing airports...")

        possible_columns = [
            'ident', 'type', 'name', 'elevation_ft', 'continent',
            'iso_country', 'iso_region', 'municipality', 'gps_code',
            'iata_code', 'local_code', 'coordinates'
        ]

        pbar = tqdm(total=self.total_airports, desc="Processing airports")

        for country in df['iso_country'].unique():
            if pd.isna(country):
                continue

            country_data = df[df['iso_country'] == country]
            airports = []

            for _, row in country_data.iterrows():
                airport_data = {}
                for col in possible_columns:
                    if col in row.index and pd.notna(row[col]):
                        value = row[col]
                        if col == 'elevation_ft':
                            value = float(value)
                        airport_data[col] = value

                ident = airport_data.get('ident')
                iso_country = airport_data.get('iso_country')
                airport_type = airport_data.get('type')
                if ident:
                    should_enrich = (
                        airport_type in PRIORITIZED_TYPES and
                        iso_country in WESTERN_EUROPE
                    )
                    if should_enrich:
                        details = self.fetch_airport_details(ident)
                        if details:
                            airport_data.update(details)
                        airport_data['metar_available'] = self.check_metar_available(ident)
                    else:
                        airport_data['metar_available'] = False

                airports.append(airport_data)
                pbar.update(1)

            self.countries_data[country] = airports

        pbar.close()

    def generate_countries_index(self) -> None:
        print("\nGenerating countries index...")
        countries = []
        for country_code, airports in self.countries_data.items():
            types_count = {}
            for airport in airports:
                airport_type = airport.get('type', 'unknown')
                types_count[airport_type] = types_count.get(airport_type, 0) + 1

            countries.append({
                'code': country_code,
                'name': self.get_country_name(country_code),
                'airport_count': len(airports),
                'types_distribution': types_count
            })

        countries.sort(key=lambda x: x['name'])

        with open(self.data_dir / 'countries.json', 'w', encoding='utf-8') as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)

    def save_country_data(self) -> None:
        print("\nSaving country data...")

        for country_code, airports in tqdm(self.countries_data.items(), desc="Saving countries"):
            country_dir = self.data_dir / country_code.lower()
            country_dir.mkdir(exist_ok=True, parents=True)

            types_distribution = {}
            for airport in airports:
                airport_type = airport.get('type', 'unknown')
                types_distribution[airport_type] = types_distribution.get(airport_type, 0) + 1

            with open(country_dir / 'airports.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'country_code': country_code,
                    'country_name': self.get_country_name(country_code),
                    'total_airports': len(airports),
                    'last_updated': pd.Timestamp.now().isoformat(),
                    'types_distribution': types_distribution,
                    'airports': airports
                }, f, ensure_ascii=False, indent=2)

    def update(self) -> bool:
        try:
            self.load_country_names()

            df = self.download_source_data()
            if df is None:
                return False

            self.data_dir.mkdir(exist_ok=True, parents=True)

            self.process_airports(df)
            self.generate_countries_index()
            self.save_country_data()

            return True

        except Exception as e:
            print(f"An error occurred during update: {str(e)}")
            return False


def main():
    source_url = "https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv"
    data_dir = Path(__file__).parent.parent / 'data'

    updater = AirportDataUpdater(source_url, data_dir)
    success = updater.update()

    if success:
        print("\nUpdate completed successfully!")
    else:
        print("\nUpdate failed!")
        exit(1)


if __name__ == "__main__":
    main()