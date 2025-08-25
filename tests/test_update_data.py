import pytest
import pandas as pd
import json
import responses
from src.update_data import AirportDataUpdater


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("AIRPORTDB_API_KEY", "testkey")


def mock_airport_apis(rsps, idents):
    for ident in idents:
        rsps.add(
            responses.GET,
            f"https://airportdb.io/api/v1/airport/{ident}",
            json={"ident": ident, "city": "Test City", "runways": [{"id": 1, "le_ident": "08L", "he_ident": "26R"}]},
            status=200,
            match=[responses.matchers.query_param_matcher({"apiToken": "testkey"})],
        )
        rsps.add(
            responses.GET,
            f"https://aviationweather.gov/api/data/metar?ids={ident}&format=json",
            json=[{"id": ident}],
            status=200,
        )

@pytest.fixture
def sample_airports_data():
    """Create sample airport data for testing."""
    return pd.DataFrame({
        'ident': ['KJFK', 'EGLL', 'LFPG'],
        'type': ['large_airport', 'large_airport', 'large_airport'],
        'name': ['John F Kennedy', 'Heathrow', 'Charles de Gaulle'],
        'elevation_ft': [13, 83, 392],
        'continent': ['NA', 'EU', 'EU'],
        'iso_country': ['US', 'GB', 'FR'],
        'iso_region': ['US-NY', 'GB-ENG', 'FR-IDF'],
        'municipality': ['New York', 'London', 'Paris'],
        'gps_code': ['KJFK', 'EGLL', 'LFPG'],
        'iata_code': ['JFK', 'LHR', 'CDG'],
        'local_code': ['JFK', 'LHR', 'CDG'],
        'coordinates': ['40.6398,-73.7789', '51.4775,-0.4614', '49.0128,2.5500']
    })


@pytest.fixture
def sample_country_names():
    """Create sample country names mapping."""
    return {
        'GB': 'United Kingdom',
        'FR': 'France'
    }


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path


@pytest.fixture
def updater(temp_dir, _api_key):
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
        assert len(df) == 3
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

    @responses.activate
    def test_process_airports(self, updater, sample_airports_data):
        """Test processing of airport data."""
        mock_airport_apis(responses, ['EGLL', 'LFPG'])

        updater.process_airports(sample_airports_data)

        assert len(updater.countries_data) == 2
        assert len(updater.countries_data['GB']) == 1
        assert len(updater.countries_data['FR']) == 1

        # Check European airports enriched
        gb_airports = updater.countries_data['GB']
        lhr = next(a for a in gb_airports if a['iata_code'] == 'LHR')
        assert lhr['city'] == 'Test City'
        assert lhr['runways'][0]['id'] == 1
        assert lhr['metar_available'] is True

        fr_airports = updater.countries_data['FR']
        cdg = next(a for a in fr_airports if a['iata_code'] == 'CDG')
        assert cdg['city'] == 'Test City'
        assert cdg['runways'][0]['id'] == 1
        assert cdg['metar_available'] is True

        assert len(responses.calls) == 4

        # Verify API usage stats
        fr_stats = updater.api_stats['FR']
        assert fr_stats['metar_fetched'] == 1
        assert fr_stats['airportdb_fetched'] == 1
        gb_stats = updater.api_stats['GB']
        assert gb_stats['metar_fetched'] == 1
        assert gb_stats['airportdb_fetched'] == 1

    @responses.activate
    def test_skip_existing_runways_and_metar(self, updater, sample_airports_data, temp_dir):
        """Ensure AirportDB and METAR APIs are skipped when data already exists."""
        fr_dir = temp_dir / 'fr'
        fr_dir.mkdir()
        existing = {
            'country_code': 'FR',
            'country_name': 'France',
            'total_airports': 1,
            'types_distribution': {'large_airport': 1},
            'airports': [
                {
                    'ident': 'LFPG',
                    'type': 'large_airport',
                    'runways': [{'id': 99}],
                    'metar_available': True,
                }
            ],
        }
        with open(fr_dir / 'airports.json', 'w') as f:
            json.dump(existing, f)

        responses.add(
            responses.GET,
            "https://airportdb.io/api/v1/airport/LFPG",
            json={"ident": "LFPG", "city": "Test City"},
            status=200,
            match=[responses.matchers.query_param_matcher({"apiToken": "testkey"})],
        )
        mock_airport_apis(responses, ['EGLL'])

        updater.data_dir = temp_dir
        updater.process_airports(sample_airports_data)

        fr_airports = updater.countries_data['FR']
        cdg = next(a for a in fr_airports if a['ident'] == 'LFPG')
        assert cdg['runways'][0]['id'] == 99
        assert cdg['metar_available'] is True

        # Only EGLL should have triggered AirportDB and METAR calls
        assert len(responses.calls) == 2
        fr_stats = updater.api_stats['FR']
        assert fr_stats['airportdb_skipped'] == 1
        assert fr_stats['metar_skipped'] == 1
    @responses.activate
    def test_generate_countries_index(self, updater, sample_airports_data, temp_dir):
        """Test generation of countries index file."""
        updater.country_names = {'GB': 'United Kingdom', 'FR': 'France'}
        mock_airport_apis(responses, ['EGLL', 'LFPG'])
        updater.process_airports(sample_airports_data)
        updater.generate_countries_index()

        index_file = temp_dir / 'countries.json'
        assert index_file.exists()

        with open(index_file) as f:
            data = json.load(f)

        assert len(data) == 2
        fr_data = next(c for c in data if c['code'] == 'FR')
        assert fr_data['name'] == 'France'
        assert fr_data['airport_count'] == 1
        assert fr_data['types_distribution']['large_airport'] == 1

    @responses.activate
    def test_save_country_data(self, updater, sample_airports_data, temp_dir):
        """Test saving individual country data files."""
        updater.country_names = {'FR': 'France'}
        mock_airport_apis(responses, ['EGLL', 'LFPG'])
        updater.process_airports(sample_airports_data)
        updater.save_country_data()

        # Check FR data file
        fr_dir = temp_dir / 'fr'
        assert fr_dir.exists()

        fr_file = fr_dir / 'airports.json'
        assert fr_file.exists()

        with open(fr_file) as f:
            data = json.load(f)
            assert data['country_name'] == 'France'
            assert data['total_airports'] == 1
            assert len(data['airports']) == 1
            assert data['types_distribution']['large_airport'] == 1

    def test_full_update_process(self, updater, sample_airports_data):
        """Test the complete update process."""
        with responses.RequestsMock() as rsps:
            # Mock country names API
            rsps.add(
                responses.GET,
                "https://country.io/names.json",
                json={'GB': 'United Kingdom', 'FR': 'France'},
                status=200
            )

            # Mock airports data API
            rsps.add(
                responses.GET,
                "https://example.com/airports.csv",
                body=sample_airports_data.to_csv(index=False),
                status=200
            )

            mock_airport_apis(rsps, ['EGLL', 'LFPG'])

            assert updater.update() is True

            # Verify all files were created
            assert (updater.data_dir / 'countries.json').exists()
            assert (updater.data_dir / 'gb' / 'airports.json').exists()
            assert (updater.data_dir / 'fr' / 'airports.json').exists()

            enrichment_calls = [
                c for c in rsps.calls
                if "airportdb.io" in c.request.url or "aviationweather.gov" in c.request.url
            ]
            assert len(enrichment_calls) == 4

    @responses.activate
    def test_handle_missing_data(self, updater):
        """Test handling of missing or invalid data."""
        df = pd.DataFrame({
            'ident': ['TEST1', 'TEST2'],
            'type': ['large_airport', None],
            'name': ['Test Airport', 'Another Airport'],
            'elevation_ft': [100, None],
            'iso_country': ['FR', None],
            'coordinates': ['40.0,-73.0', None]
        })

        mock_airport_apis(responses, ['TEST1'])
        updater.process_airports(df)
        assert len(updater.countries_data['FR']) == 1

        airport = updater.countries_data['FR'][0]
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
