# Airport Data Explorer

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/teyk0o/airport-explorer/update-airports.yml?label=data%20update)](https://github.com/teyk0o/airport-explorer/actions)
[![codecov](https://codecov.io/gh/Teyk0o/airport-explorer/branch/master/graph/badge.svg?token=RNW6IGP25H)](https://codecov.io/gh/Teyk0o/airport-explorer)
[![GitHub last commit](https://img.shields.io/github/last-commit/teyk0o/airport-explorer)](https://github.com/teyk0o/airport-explorer/commits/main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Interactive web application for exploring worldwide airport data with an OpenStreetMap integration. Data is automatically updated daily from official sources.

## 🌟 Features

- 🌍 Interactive world map with airport locations
- 🔍 Filter airports by country
- 📊 Detailed statistics for each country
- 🔄 Daily automated data updates
- 📱 Responsive design for mobile and desktop
- 📈 100% test coverage
- 🤖 Automated quality checks

## 🚀 Quick Start

Visit the live site: [https://teyk0o.github.io/airport-explorer](https://teyk0o.github.io/airport-explorer)

Or run locally:

```bash
# Clone the repository
git clone https://github.com/teyk0o/airport-explorer.git

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Update airport data
python src/update_data.py

# Serve the docs directory
python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000` in your browser.

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+
- Git

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run tests:
   ```bash
   pytest tests/ --cov=src --cov-report=html
   ```

## 📁 Project Structure

```
airport-explorer/
├── .github/
│   └── workflows/         # GitHub Actions configurations
├── src/
│   ├── __init__.py
│   └── update_data.py    # Data update script
├── tests/
│   ├── __init__.py
│   └── test_update_data.py
├── docs/                 # Web interface files
├── data/                 # Generated airport data
└── requirements.txt
```

## 🔄 Data Update Process

Data is automatically updated daily through GitHub Actions:
1. Downloads latest airport data
2. Runs comprehensive test suite
3. Processes and validates the data
4. Updates JSON files if changes are detected
5. Deploys to GitHub Pages
6. Updates code coverage reports

## 🤝 Contributing

Contributions are welcome! Please check out our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository
2. Create a feature branch
3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run tests and ensure coverage:
   ```bash
   pytest tests/ --cov=src
   ```
5. Commit your changes
6. Open a Pull Request

## 📊 Code Quality

- Automated testing on each commit
- Daily data validation
- Continuous integration checks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Airport data from [Airport-Codes GitHub Repo](https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv)
- Maps powered by [OpenStreetMap](https://www.openstreetmap.org/)
- Mapping library: [Leaflet.js](https://leafletjs.com/)
- Infrastructure: [GitHub Actions](https://github.com/features/actions)
- Code Coverage: [Codecov](https://codecov.io)
