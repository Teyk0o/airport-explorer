import pytest
import pandas as pd
import json
import responses
from pathlib import Path
from src.update_data import AirportDataUpdater

@pytest.fixture
def sample_airports_data():
    """Create sample airport data for testing."""
    return pd.DataFrame({
        'ident': ['KJFK', 'KBOS', 'EGLL', 'LFPG'],
        'type': ['large_airport', 'large_airport', 'large_airport', 'large_airport'],
        'name': ['John F Kennedy', 'Boston Logan', 'Heathrow', 'Charles de Gaulle'],
        'elevation_ft': [13, 20, 83, 392],
        'continent': ['NA', 'NA', 'EU', 'EU'],
        'iso_country': ['US', 'US', 'GB', 'FR'],
        'iso_region': ['US-NY', 'US-MA', 'GB-ENG', 'FR-IDF'],
        'municipality': ['New York', 'Boston', 'London', 'Paris'],
        'gps_code': ['KJFK', 'KBOS', 'EGLL', 'LFPG'],
        'iata_code': ['JFK', 'BOS', 'LHR', 'CDG'],
        'local_code': ['JFK', 'BOS', 'LHR', 'CDG'],
        'coordinates': ['40.6398,-73.7789', '42.3643,-71.0052', '51.4775,-0.4614', '49.0128,2.5500']
    })


@pytest.fixture
def sample_country_names():
    """Create sample country names mapping."""
    return {
        'US': 'United States',
        'GB': 'United Kingdom',
        'FR': 'France'
    }


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path


@pytest.fixture
def updater(temp_dir):
    """Create an AirportDataUpdater instance for testing."""
    return AirportDataUpdater(
        source_url="https://example.com/airports.csv",
        data_dir=temp_dir
    )


class TestAirportDataUpdater:

    @responses.activate
    def test_load_country_names(self, updater):
        """Test loading country names from API."""
        # Mock the country names API response
        responses.add(
            responses.GET,
            "https://country.io/names.json",
            json={'US': 'United States', 'GB': 'United Kingdom'},
            status=200
        )

        updater.load_country_names()
        assert updater.country_names['US'] == 'United States'
        assert updater.country_names['GB'] == 'United Kingdom'

    @responses.activate
    def test_load_country_names_failure(self, updater):
        """Test handling of country names API failure."""
        responses.add(
            responses.GET,
            "https://country.io/names.json",
            status=404
        )

        updater.load_country_names()
        assert updater.country_names == {}

    def test_get_country_name(self, updater):
        """Test country name retrieval."""
        updater.country_names = {'US': 'United States'}
        assert updater.get_country_name('US') == 'United States'
        assert updater.get_country_name('XX') == 'XX'  # Unknown country code

    @responses.activate
    def test_download_source_data(self, updater, sample_airports_data):
        """Test downloading airport data."""
        csv_content = sample_airports_data.to_csv(index=False)
        responses.add(
            responses.GET,
            "https://example.com/airports.csv",
            body=csv_content,
            status=200
        )

        df = updater.download_source_data()
        assert df is not None
        assert len(df) == 4
        assert list(df['iso_country'].unique()) == ['US', 'GB', 'FR']

    @responses.activate
    def test_download_source_data_failure(self, updater):
        """Test handling of download failure."""
        responses.add(
            responses.GET,
            "https://example.com/airports.csv",
            status=404
        )

        df = updater.download_source_data()
        assert df is None

    def test_process_airports(self, updater, sample_airports_data):
        """Test processing of airport data."""
        updater.process_airports(sample_airports_data)

        assert len(updater.countries_data) == 3
        assert len(updater.countries_data['US']) == 2
        assert len(updater.countries_data['GB']) == 1
        assert len(updater.countries_data['FR']) == 1

        # Check specific airport data
        us_airports = updater.countries_data['US']
        jfk = next(a for a in us_airports if a['iata_code'] == 'JFK')
        assert jfk['name'] == 'John F Kennedy'
        assert jfk['type'] == 'large_airport'
        assert jfk['coordinates'] == '40.6398,-73.7789'

    def test_generate_countries_index(self, updater, sample_airports_data, temp_dir):
        """Test generation of countries index file."""
        updater.country_names = {'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France'}
        updater.process_airports(sample_airports_data)
        updater.generate_countries_index()

        index_file = temp_dir / 'countries.json'
        assert index_file.exists()

        with open(index_file) as f:
            data = json.load(f)

        assert len(data) == 3
        us_data = next(c for c in data if c['code'] == 'US')
        assert us_data['name'] == 'United States'
        assert us_data['airport_count'] == 2
        assert us_data['types_distribution']['large_airport'] == 2

    def test_save_country_data(self, updater, sample_airports_data, temp_dir):
        """Test saving individual country data files."""
        updater.country_names = {'US': 'United States'}
        updater.process_airports(sample_airports_data)
        updater.save_country_data()

        # Check US data file
        us_dir = temp_dir / 'us'
        assert us_dir.exists()

        us_file = us_dir / 'airports.json'
        assert us_file.exists()

        with open(us_file) as f:
            data = json.load(f)
            assert data['country_name'] == 'United States'
            assert data['total_airports'] == 2
            assert len(data['airports']) == 2
            assert data['types_distribution']['large_airport'] == 2

    def test_full_update_process(self, updater, sample_airports_data):
        """Test the complete update process."""
        with responses.RequestsMock() as rsps:
            # Mock country names API
            rsps.add(
                responses.GET,
                "https://country.io/names.json",
                json={'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France'},
                status=200
            )

            # Mock airports data API
            rsps.add(
                responses.GET,
                "https://example.com/airports.csv",
                body=sample_airports_data.to_csv(index=False),
                status=200
            )

            assert updater.update() is True

            # Verify all files were created
            assert (updater.data_dir / 'countries.json').exists()
            assert (updater.data_dir / 'us' / 'airports.json').exists()
            assert (updater.data_dir / 'gb' / 'airports.json').exists()
            assert (updater.data_dir / 'fr' / 'airports.json').exists()

    def test_handle_missing_data(self, updater):
        """Test handling of missing or invalid data."""
        df = pd.DataFrame({
            'ident': ['TEST1', 'TEST2'],
            'type': ['small_airport', None],
            'name': ['Test Airport', 'Another Airport'],
            'elevation_ft': [100, None],
            'iso_country': ['US', None],
            'coordinates': ['40.0,-73.0', None]
        })

        updater.process_airports(df)
        assert len(updater.countries_data['US']) == 1

        airport = updater.countries_data['US'][0]
        assert 'elevation_ft' in airport
        assert 'type' in airport
        assert airport['ident'] == 'TEST1'

    def test_error_handling(self, updater):
        """Test error handling in the update process."""
        with responses.RequestsMock() as rsps:
            # Mock failed APIs
            rsps.add(
                responses.GET,
                "https://country.io/names.json",
                status=500
            )
            rsps.add(
                responses.GET,
                "https://example.com/airports.csv",
                status=500
            )

            assert updater.update() is False


if __name__ == '__main__':
    pytest.main([__file__])