# 🌊 SRGI Tidal Data Converter

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)

**Automated Tidal Data Processing & Visualization Pipeline for SRGI Data.**

Stop plotting manually. **HydroTideArchitect** is a Python class designed to automate the cleaning, time-shifting, analysis, and visualization of raw tidal data from *Badan Informasi Geospasial* (SRGI).

---

## 🚀 Key Features

* **📍 Smart Location Detection**: Automatically detects coordinates from the file header and determines the correct Indonesian Timezone (**WIB/WITA/WIT**) based on Longitude logic.
* **🧠 FFT Analysis**: Uses **Fast Fourier Transform** to mathematically classify tide types (Diurnal, Semidiurnal, or Mixed).
* **📊 Interactive Dashboards**: Generates high-resolution HTML plots with zoomable ranges, hover tooltips, and transversal filled areas using Plotly.
* **📑 Reporting-Ready Excel**: Exports cleaned data into `.xlsx` complete with **native Excel charts** ready for official submission.
* **📅 Fieldwork Planner**: Auto-detects **Spring Tide** windows for optimal survey scheduling.

---

## 🛠️ Installation

Ensure you have Python installed, then install the required libraries:

```bash
pip install pandas numpy scipy plotly xlsxwriter

```

💻 Usage
Place your raw SRGI text file (e.g., data_pasut.txt) in the project folder.

Run the script:
```bash
from hydro_tide import HydroTideArchitect

# Initialize with your file
architect = HydroTideArchitect(file_path='data_pasut.txt')

# 1. Process Data (Clean & Shift)
df = architect.process_data()

# 2. Analyze (FFT & Tide Type)
architect.analyze_tide_type()

# 3. Generate Outputs
architect.export_excel_pro() # Creates Excel Report
architect.export_html_pro()  # Creates Interactive Dashboard
```

📸 Output Examples
Interactive HTML Dashboard
High-resolution visualization with MSL indicators.

Automated Excel Report
Native scatter charts generated automatically.
