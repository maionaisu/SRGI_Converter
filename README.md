# 🌊 SRGI Tidal Converter

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)
![License](https://img.shields.io/github/license/maionaisu/SRGI_Tidal_Converter?style=for-the-badge)

**Automated Tidal Data Processing & Visualization Pipeline for SRGI Data.**

> Stop plotting manually. **HydroTideArchitect** is a Python class designed to automate the cleaning, time-shifting, analysis, and visualization of raw tidal data from *Badan Informasi Geospasial* (SRGI).

---

## 🚀 Key Features

* **📍 Smart Location Detection**: Automatically parses coordinates from the raw text header and determines the correct Indonesian Timezone (**WIB/WITA/WIT**) based on Longitude.
* **🧠 FFT Analysis**: Uses **Fast Fourier Transform** to scientifically classify tide types (Diurnal, Semidiurnal, or Mixed).
* **📊 Interactive Dashboards**: Generates high-resolution HTML plots with zoomable ranges, smart axis ticks, and transversal filled areas using Plotly.
* **📑 Reporting-Ready Excel**: Exports cleaned data into `.xlsx` complete with **native Excel charts** ready for official submission.
* **📅 Fieldwork Planner**: Auto-detects **Spring Tide** windows for optimal survey scheduling.

---

## 🛠️ Installation

1.  Clone the repository:
    ```bash
    git clone [https://github.com/maionaisu/SRGI_Tidal_Converter.git](https://github.com/maionaisu/SRGI_Tidal_Converter.git)
    cd SRGI_Tidal_Converter
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

---

## 💻 Usage

1.  Place your raw SRGI text file (e.g., `data_pasut.txt`) in the project folder.
2.  Import and run the architect:

```python
from srgi_converter import HydroTideArchitect

# Initialize with your file path
architect = HydroTideArchitect(file_path='data_pasut.txt')

# 1. Process Data (Clean & Shift Timezone)
df = architect.process_data()

# 2. Analyze (FFT & Tide Type)
architect.analyze_tide_type()

# 3. Generate Outputs
architect.export_excel_pro() # Creates Excel Report
architect.export_html_pro()  # Creates Interactive Dashboard
