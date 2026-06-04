# DataTrust AI: Intelligent Automated Data Quality Management System

**DataTrust AI** is a comprehensive, automated platform designed to audit, score, and improve the quality of enterprise datasets. By combining traditional rule-based validation with advanced Machine Learning techniques (Isolation Forest), it identifies errors, anomalies, and inconsistencies that often go undetected in manual data preparation processes.

---

## 🚀 Features

- **Automated Data Ingestion:** Seamlessly upload and process CSV and Excel (`.xlsx`) files.
- **Dynamic Quality Scoring:** Generates a real-time data quality score based on completeness, uniqueness, and accuracy.
- **ML-Powered Anomaly Detection:** Utilizes the **Isolation Forest** algorithm to detect statistical outliers and unusual data patterns.
- **Intelligent Validation:** Suggests and applies validation rules (email formats, phone numbers, numeric ranges) based on column heuristics.
- **Automated Data Cleaning:** Provides tools to handle missing values (mean, median, forward fill, etc.) and remove duplicate records.
- **Professional PDF Reporting:** Generates detailed data quality audit reports for compliance and decision-making.

---

## 🛠️ Tech Stack

- **Backend:** [Python 3.x](https://www.python.org/), [Flask](https://flask.palletsprojects.com/)
- **Data Processing:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Machine Learning:** [Scikit-learn](https://scikit-learn.org/) (Isolation Forest, StandardScaler)
- **Reporting:** [FPDF](http://www.fpdf.org/) (PDF Generation)
- **Database:** [SQLite](https://www.sqlite.org/) (Metadata and Upload History)
- **Frontend:** HTML5, CSS3 (Bootstrap 5), JavaScript (Chart.js)

---

## 📂 Project Structure

```text
├── modules/               # Core business logic
│   ├── anomaly.py         # ML-based anomaly detection
│   ├── cleaning.py        # Data transformation and imputation
│   ├── scoring.py         # Quality scoring algorithms
│   └── validation.py      # Format and range validation
├── static/                # Frontend assets (CSS, JS)
├── templates/             # HTML templates (Jinja2)
├── utils/                 # Helper utilities
│   ├── file_handler.py    # Safe file reading and writing
│   └── report_generator.py# PDF report generation engine
├── uploads/               # Temporary storage for uploaded datasets
├── outputs/               # Generated PDF reports
├── app.py                 # Main Flask application and routing
├── database.db            # SQLite database for metadata
└── requirements.txt       # Project dependencies
```

---

## ⚙️ Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation


   ```

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the application:**
   Open your browser and navigate to `http://127.0.0.1:5000/`.

---

## 📊 Usage

1. **Upload:** Select a CSV or Excel file on the homepage.
2. **Analyze:** View the dashboard for a high-level overview of quality scores, missing values, and anomalies.
3. **Clean:** Navigate to the "Cleaning" section to handle missing data or remove duplicates.
4. **Report:** Generate and download a professional PDF report from the "Reports" section.

---

## 📄 License

This project is developed as a Final Year Project for [Your University/Department]. All rights reserved.
