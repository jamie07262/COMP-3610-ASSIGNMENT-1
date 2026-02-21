# COMP 3610: Big Data Analytics

## Assignment 1: Data Pipeline & Visualization Dashboard

---

### Overview

This project builds an end-to-end data pipeline for NYC Yellow Taxi Trip data, including ingestion, cleaning, transformation, SQL analysis, and an interactive Streamlit dashboard. The dashboard visualizes trip patterns, fare metrics, payment types, and more.

---

### Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone <your-repo-url>
   cd <your-repo-folder>
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Streamlit dashboard:**

   ```bash
   streamlit run app.py
   ```

5. **Notebook:**
   - Open `assignment1.ipynb` in Jupyter or VS Code for data pipeline, cleaning, SQL analysis, and visualization prototypes.

---

### Deployed Dashboard URL

[View the deployed dashboard here](https://beduddd7bxt7sgtiggwnps.streamlit.app/)

---

### Project Structure

- `comp3610a1.ipynb`: Jupyter notebook with all pipeline steps, SQL queries, and visualization prototypes
- `app.py`: Streamlit dashboard application
- `requirements.txt`: Python dependencies
- `.gitignore`: Excludes data files and unnecessary artifacts

---

### Data Files

**Do NOT commit data files to the repository.**

- Raw data is downloaded programmatically and stored in `data/raw/`.
- Required files:
  - [yellow_tripdata_2024-01.parquet](https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet)
  - [taxi_zone_lookup.csv](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv)

---

### Assignment Requirements

- Data ingestion, validation, cleaning, feature engineering, SQL analysis, and dashboard development as per assignment instructions.
- Interactive filters and five required visualizations.
- AI tools used are disclosed in the notebook.
