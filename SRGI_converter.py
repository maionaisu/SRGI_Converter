import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.signal import periodogram
import io
import os
import re

class HydroTideArchitect:
    """
    1. Auto-Detect Location (Lat/Lon) dari Header.
    2. Auto-Convert Timezone (WIB/WITA/WIT).
    3. Analisis Pasut (FFT) -> HASIL DITAMPILKAN JELAS DI GRAFIK.
    4. Fieldwork Planner (Spring Tide).
    5. Visualisasi Transversal (Filled Area).
    """
    
    def __init__(self, file_path=None, raw_data_string=None):
        self.df = None
        self.metadata = {
            'lat': None, 
            'lon': None, 
            'tz_name': 'UTC', 
            'tz_offset': 0
        }
        self.tide_type = "Unknown" # Default value
        self.raw_content = ""
        
        if file_path and os.path.exists(file_path):
            with open(file_path, 'r') as f:
                self.raw_content = f.read()
            self.file_name = os.path.basename(file_path)
        elif raw_data_string:
            self.raw_content = raw_data_string
            self.file_name = "Raw_Data_Input"
        else:
            raise ValueError("Input data tidak valid.")

    def _detect_timezone_by_coords(self, lines):
        """
        Logika Cerdas: Mencari 'Lon:' di header dan menentukan Zona Waktu.
        """
        self.metadata['lon'] = None
        self.metadata['lat'] = None
        
        for line in lines[:15]: # Cek 15 baris pertama
            # Regex menangkap angka desimal (termasuk negatif untuk Lat)
            match_lon = re.search(r'Lon:\s*([\d\.]+)', line)
            match_lat = re.search(r'Lat:\s*([-\d\.]+)', line)
            
            if match_lon:
                self.metadata['lon'] = float(match_lon.group(1))
            if match_lat:
                self.metadata['lat'] = float(match_lat.group(1))
        
        # Logika Penentuan Zona Waktu Indonesia
        lon = self.metadata['lon']
        if lon is not None:
            if lon < 114.8: # Barat Selat Bali (Jawa, Sumatera, dkk)
                self.metadata['tz_name'] = 'WIB'
                self.metadata['tz_offset'] = 7
            elif 114.8 <= lon < 129.0: # Bali, Nusa Tenggara, Sulawesi
                self.metadata['tz_name'] = 'WITA'
                self.metadata['tz_offset'] = 8
            else: # Maluku, Papua
                self.metadata['tz_name'] = 'WIT'
                self.metadata['tz_offset'] = 9
            
            print(f"[GEO-AI] Lokasi Terdeteksi: Lon {lon} E")
            print(f"[GEO-AI] Auto-Set Timezone: {self.metadata['tz_name']} (UTC+{self.metadata['tz_offset']})")
        else:
            print("[WARN] Koordinat tidak ditemukan di header. Default ke WIB (UTC+7).")
            self.metadata['tz_name'] = 'WIB'
            self.metadata['tz_offset'] = 7

    def process_data(self):
        """
        Pipeline: Parsing -> Auto-Timezone -> Cleaning
        """
        lines = self.raw_content.strip().split('\n')
        
        # 1. Deteksi Zona Waktu Dulu
        self._detect_timezone_by_coords(lines)
        
        # 2. Cari Header Data
        header_idx = 0
        for i, line in enumerate(lines):
            if 'Lat' in line and 'Lon' in line and 'z(m)' in line:
                header_idx = i
                break
        
        # 3. Parsing Robust
        try:
            data_io = io.StringIO(self.raw_content)
            temp_df = pd.read_csv(
                data_io,
                sep=r'\s+',
                skiprows=header_idx + 1,
                header=None,
                names=['Lat', 'Lon', 'Date', 'Time', 'elevation_m'],
                engine='python'
            )
            
            # 4. Gabung Waktu (UTC)
            temp_df['datetime_utc'] = pd.to_datetime(
                temp_df['Date'] + ' ' + temp_df['Time'], 
                format='%Y-%m-%d %H:%M:%S'
            )
            
            # 5. KONVERSI DINAMIS SESUAI LOKASI
            offset_jam = self.metadata['tz_offset']
            temp_df['datetime_local'] = temp_df['datetime_utc'] + pd.Timedelta(hours=offset_jam)
            
            self.df = temp_df[['datetime_local', 'elevation_m']].copy()
            return self.df
            
        except Exception as e:
            print(f"[ERROR] Parsing gagal: {e}")
            return None

    def analyze_tide_type(self):
        """
        Menentukan tipe pasut (Diurnal/Semidiurnal/Mixed) menggunakan FFT.
        """
        if self.df is None: return
        
        y = self.df['elevation_m'].values
        fs = 1.0 
        freqs, psd = periodogram(y, fs)
        
        # Filter energi di frekuensi diurnal (24h) dan semidiurnal (12h)
        power_semi = psd[np.where((freqs > 0.07) & (freqs < 0.09))].max()
        power_diur = psd[np.where((freqs > 0.035) & (freqs < 0.05))].max()
        
        # Hitung rasio
        ratio = power_diur / power_semi if power_semi > 0 else 999
        
        # Klasifikasi (Formzahl sederhana)
        if ratio < 0.25: 
            self.tide_type = "Semidiurnal (Ganda Murni)"
        elif ratio > 3.0: 
            self.tide_type = "Diurnal (Tunggal Murni)"
        else: 
            self.tide_type = "Mixed Tide (Campuran)"
            
        print(f"[ANALYSIS] Tipe Pasut: {self.tide_type} (Ratio Energi: {ratio:.2f})")

    def recommend_fieldwork_window(self):
        """
        Mencari 3 hari terbaik (Spring Tide) untuk Fieldwork.
        """
        if self.df is None: return

        daily = self.df.set_index('datetime_local').resample('D')['elevation_m'].agg(['min', 'max'])
        daily['range'] = daily['max'] - daily['min']
        daily['3d_range_sum'] = daily['range'].rolling(window=3).sum()
        
        best_end_date = daily['3d_range_sum'].idxmax()
        if pd.isna(best_end_date): return

        start_date = best_end_date - pd.Timedelta(days=2)
        
        tz = self.metadata['tz_name']
        print("\n" + "="*50)
        print(f"   REKOMENDASI JADWAL FIELDWORK ({tz})   ")
        print("="*50)
        print(f"Jendela Waktu Terbaik : {start_date.strftime('%d %b')} - {best_end_date.strftime('%d %b %Y')}")
        print(f"Fase                  : Spring Tide (Pasang Purnama)")
        print(f"Total Tidal Range     : {daily.loc[best_end_date, '3d_range_sum']:.2f} m (Kumulatif 3 hari)")
        print(f"Tipe Pasut            : {self.tide_type}") # Tampilkan juga di sini
        print("-" * 50)
        print("Notes:")
        print(f"- Jam operasional mengacu pada waktu {tz}.")
        print("="*50 + "\n")

    def export_excel_pro(self, filename=None):
        """
        Export Excel dengan grafik Transversal dan Label Timezone yang benar.
        """
        if self.df is None: return
        
        if filename is None:
            filename = f"Laporan_Pasut_{self.metadata['tz_name']}.xlsx"

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        self.df.to_excel(writer, sheet_name='Data', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Data']
        date_format = workbook.add_format({'num_format': 'dd mmm hh:mm', 'align': 'left'})
        worksheet.set_column('A:A', 20, date_format)
        
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        max_row = len(self.df) + 1
        
        chart.add_series({
            'name':       'Elevasi (m)',
            'categories': ['Data', 1, 0, max_row, 0],
            'values':     ['Data', 1, 1, max_row, 1],
            'line':       {'color': '#0070C0', 'width': 1.5},
        })
        
        tz = self.metadata['tz_name']
        # Tipe Pasut dikembalikan ke Judul Grafik
        chart.set_title({'name': f'Hidrograf ({tz}) - {self.tide_type}'})
        chart.set_x_axis({
            'name': f'Waktu ({tz})', 
            'date_axis': True,
            'num_format': 'dd/mm',
            'major_gridlines': {'visible': True}
        })
        chart.set_y_axis({'name': 'Elevasi (m)', 'major_gridlines': {'visible': True}})
        chart.set_size({'width': 1000, 'height': 400}) # Wide Aspect Ratio
        
        worksheet.insert_chart('D2', chart)
        writer.close()
        print(f"[SUCCESS] Excel generated: {filename}")

    def export_html_pro(self, filename=None):
        """
        Export HTML Plotly dengan Filled Area (Transversal) dan Smart Axis Tick.
        """
        if self.df is None: return
        
        if filename is None:
            filename = f"Visualisasi_Pasut_{self.metadata['tz_name']}.html"
            
        tz = self.metadata['tz_name']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df['datetime_local'],
            y=self.df['elevation_m'],
            mode='lines',
            fill='tozeroy',  # Transversal Style
            name='Elevasi Air',
            line=dict(color='#0077be', width=2), 
            fillcolor='rgba(0, 119, 190, 0.4)'
        ))
        
        msl = self.df['elevation_m'].mean()
        fig.add_hline(y=msl, line_dash="dash", line_color="red", 
                     annotation_text=f"MSL ({msl:.2f}m)", annotation_position="top right")

        lat_str = str(self.metadata.get('lat', '-'))
        lon_str = str(self.metadata.get('lon', '-'))
        
        fig.update_layout(
            title=dict(
                text=f"<b>Analisis Pasang Surut</b><br><sub>Lokasi: {lat_str}, {lon_str} | Zona: {tz} | Tipe: {self.tide_type}</sub>",
                font=dict(size=20)
            ),
            xaxis=dict(
                title=f"Waktu ({tz})",
                # Logika Anti-Tumpang Tindih (Smart Ticks)
                # tickformatstops digunakan untuk mengubah format teks berdasarkan zoom level.
                gridcolor='rgba(0,0,0,0.1)',
                rangeslider=dict(visible=True),
                tickformatstops=[
                    dict(dtickrange=[None, 86400000], value="%A\n%d %b %H:%M"), # Zoom In (< 1 hari): Detail
                    dict(dtickrange=[86400000, 604800000], value="%d %b\n%A"),   # 1 Hari - 1 Minggu: Tgl + Hari
                    dict(dtickrange=[604800000, None], value="%d %b %Y")         # > 1 Minggu: Tanggal Simple
                ]
            ),
            yaxis=dict(
                title="Elevasi (m)",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            template="plotly_white",
            height=600,
            margin=dict(l=50, r=50, t=100, b=50),
            hovermode="x unified"
        )
        
        fig.write_html(filename)
        print(f"[SUCCESS] HTML generated: {filename}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # GANTI NAMA FILE ANDA DI SINI
    target_file = 'wg2pasut1-28jan.txt' 
    
    # Gunakan dummy string jika file tidak ada (hanya untuk demo sistem)
    dummy_input = """Prediksi Pasang Surut BIG 
Lat: -8.437600  Lon: 112.667364 
 
     Lat       Lon        yyyy-mm-dd hh:mm:ss (UTC)     z(m)
    -8.4376  112.6674     2026-01-01 00:00:00     0.135
"""

    if os.path.exists(target_file):
        print(f"[SYSTEM] Membaca file: {target_file}")
        architect = HydroTideArchitect(file_path=target_file)
    else:
        print("[SYSTEM] File tidak ditemukan, menggunakan dummy data internal.")
        architect = HydroTideArchitect(raw_data_string=dummy_input)

    # 1. Proses Data
    df = architect.process_data()
    
    if df is not None:
        # 2. Analisis
        architect.analyze_tide_type()
        
        # 3. Fieldwork Plan
        architect.recommend_fieldwork_window()
        
        # 4. Export
        architect.export_excel_pro()
        architect.export_html_pro()