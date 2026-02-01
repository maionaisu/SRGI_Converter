import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import os
import re
import utide  # Library standar Oseanografi untuk Analisis Harmonik

class HydroTideArchitect:
    """
    HydroTide Architect - Professional Edition
    1. Auto-Detect Location (Lat/Lon) dari Header.
    2. Auto-Convert Timezone (WIB/WITA/WIT).
    3. Analisis Pasut (Harmonic Analysis via UTide) -> AKURASI TINGGI.
    4. Fieldwork Planner (Spring Tide).
    5. Visualisasi Transversal (Filled Area) dengan Smart Ticks.
    """
    
    def __init__(self, file_path=None, raw_data_string=None):
        self.df = None
        self.metadata = {
            'lat': None, 
            'lon': None, 
            'tz_name': 'UTC', 
            'tz_offset': 0
        }
        self.tide_type = "Unknown" 
        self.formzahl = 0.0 
        self.constituents = {} # Menyimpan hasil harmonik (A & g)
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
        """Deteksi Zona Waktu berdasarkan Longitude di header."""
        self.metadata['lon'] = None
        self.metadata['lat'] = None
        
        for line in lines[:20]: 
            match_lon = re.search(r'Lon:\s*([\d\.]+)', line)
            match_lat = re.search(r'Lat:\s*([-\d\.]+)', line)
            
            if match_lon: self.metadata['lon'] = float(match_lon.group(1))
            if match_lat: self.metadata['lat'] = float(match_lat.group(1))
        
        lon = self.metadata['lon']
        if lon is not None:
            if lon < 114.8:
                self.metadata['tz_name'], self.metadata['tz_offset'] = 'WIB', 7
            elif 114.8 <= lon < 129.0:
                self.metadata['tz_name'], self.metadata['tz_offset'] = 'WITA', 8
            else:
                self.metadata['tz_name'], self.metadata['tz_offset'] = 'WIT', 9
            
            print(f"[GEO-AI] Lokasi: {self.metadata['lat']}, {lon} | Zona: {self.metadata['tz_name']}")
        else:
            print("[WARN] Koordinat tidak ditemukan. Default ke WIB (UTC+7).")
            self.metadata['tz_name'], self.metadata['tz_offset'] = 'WIB', 7
            self.metadata['lat'] = -8.0 # Default lat jika null (perlu untuk utide)

    def process_data(self):
        """Pipeline: Parsing -> Auto-Timezone -> Cleaning"""
        lines = self.raw_content.strip().split('\n')
        self._detect_timezone_by_coords(lines)
        
        header_idx = 0
        for i, line in enumerate(lines):
            if 'Lat' in line and 'Lon' in line and 'z(m)' in line:
                header_idx = i
                break
        
        try:
            data_io = io.StringIO(self.raw_content)
            temp_df = pd.read_csv(
                data_io, sep=r'\s+', skiprows=header_idx + 1, header=None,
                names=['Lat', 'Lon', 'Date', 'Time', 'elevation_m'], engine='python'
            )
            
            temp_df['datetime_utc'] = pd.to_datetime(temp_df['Date'] + ' ' + temp_df['Time'])
            
            # Simpan waktu lokal untuk visualisasi
            offset = self.metadata['tz_offset']
            temp_df['datetime_local'] = temp_df['datetime_utc'] + pd.Timedelta(hours=offset)
            
            # UTide membutuhkan format waktu matplotlib date number atau datetime object
            self.df = temp_df[['datetime_utc', 'datetime_local', 'elevation_m']].copy()
            
            # Hapus data kosong agar analisis harmonik tidak error
            self.df.dropna(subset=['elevation_m'], inplace=True)
            
            print(f"[SYSTEM] Data berhasil dimuat: {len(self.df)} baris data.")
            return self.df
            
        except Exception as e:
            print(f"[ERROR] Parsing gagal: {e}")
            return None

    def analyze_tide_type(self):
        """
        Analisis Harmonik menggunakan UTide (Least Squares).
        Mengekstrak Amplitudo M2, S2, K1, O1 untuk menghitung Formzahl Wyrtki.
        """
        if self.df is None: return
        
        print("\n" + "="*40)
        print("   ANALISIS HARMONIK (UTIDE)   ")
        print("="*40)

        # Persiapan Data untuk UTide
        time_vals = self.df['datetime_utc'] # Gunakan UTC untuk analisis
        elev_vals = self.df['elevation_m'].values
        lat_val = self.metadata['lat'] if self.metadata['lat'] else -8.0

        # Jalankan Solver UTide
        try:
            coef = utide.solve(
                time_vals, elev_vals,
                lat=lat_val,
                nodal=True,       # Koreksi nodal (penting untuk akurasi)
                trend=True,       # Deteksi kenaikan muka air (SLR)
                method='ols',     # Ordinary Least Squares
                conf_int='linear',
                verbose=False     # Supress output bawaan utide
            )
        except Exception as e:
            print(f"[ERROR] UTide gagal: {e}")
            return

        # Ekstrak Amplitudo Konstituen Utama
        names = coef['name'].tolist()
        amplitudes = coef['A'].tolist()
        
        target_constituents = ['M2', 'S2', 'K1', 'O1']
        found_amps = {k: 0.0 for k in target_constituents}

        print("[RESULT] Amplitudo Konstituen Utama:")
        for name, amp in zip(names, amplitudes):
            if name in target_constituents:
                found_amps[name] = amp
                self.constituents[name] = amp
                print(f"   - {name}: {amp:.4f} m")

        # Hitung Formzahl (Wyrtki, 1961)
        numerator = found_amps['K1'] + found_amps['O1']
        denominator = found_amps['M2'] + found_amps['S2']
        
        if denominator == 0:
            print("[WARN] Amplitudo Semidiurnal 0, tidak bisa membagi.")
            self.formzahl = 999.0
        else:
            self.formzahl = numerator / denominator

        F = self.formzahl
        
        # Klasifikasi Wyrtki (1961)
        if 0 < F <= 0.25:
            self.tide_type = "Semidiurnal (Ganda)"
        elif 0.25 < F <= 1.5:
            self.tide_type = "Mixed, prevailing semidiurnal (Campuran condong Ganda)"
        elif 1.5 < F <= 3.0:
            self.tide_type = "Mixed, prevailing diurnal (Campuran condong Tunggal)"
        elif F > 3.0:
            self.tide_type = "Diurnal (Tunggal)"
        else:
            self.tide_type = "Undefined"
            
        print("-" * 40)
        print(f"Formzahl (F) : {F:.4f}")
        print(f"Klasifikasi  : {self.tide_type}")
        print("="*40 + "\n")

    def recommend_fieldwork_window(self):
        """Mencari 3 hari terbaik (Spring Tide) untuk Fieldwork."""
        if self.df is None: return

        daily = self.df.set_index('datetime_local').resample('D')['elevation_m'].agg(['min', 'max'])
        daily['range'] = daily['max'] - daily['min']
        daily['3d_range_sum'] = daily['range'].rolling(window=3).sum()
        
        best_end_date = daily['3d_range_sum'].idxmax()
        if pd.isna(best_end_date): return

        start_date = best_end_date - pd.Timedelta(days=2)
        
        tz = self.metadata['tz_name']
        print(f"REKOMENDASI FIELDWORK ({tz}): {start_date.strftime('%d %b')} - {best_end_date.strftime('%d %b %Y')}")
        print(f"Total Range (3 Hari): {daily.loc[best_end_date, '3d_range_sum']:.2f} m")

    def export_excel_pro(self, filename=None):
        if self.df is None: return
        if filename is None: filename = f"Laporan_Pasut_{self.metadata['tz_name']}.xlsx"

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        # Simpan data utama
        self.df[['datetime_local', 'elevation_m']].to_excel(writer, sheet_name='Data', index=False)
        
        # Simpan Konstanta Harmonik di sheet terpisah
        if self.constituents:
            df_const = pd.DataFrame(list(self.constituents.items()), columns=['Konstituen', 'Amplitudo (m)'])
            df_const.loc[len(df_const)] = ['Formzahl', self.formzahl]
            df_const.loc[len(df_const)] = ['Tipe', self.tide_type]
            df_const.to_excel(writer, sheet_name='Harmonik', index=False)

        # Buat Grafik
        workbook = writer.book
        worksheet = writer.sheets['Data']
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        max_row = len(self.df) + 1
        
        chart.add_series({
            'name': 'Elevasi (m)',
            'categories': ['Data', 1, 0, max_row, 0],
            'values': ['Data', 1, 1, max_row, 1],
            'line': {'color': '#0070C0', 'width': 1.5},
        })
        
        tz = self.metadata['tz_name']
        chart.set_title({'name': f'Hidrograf ({tz}) - F={self.formzahl:.2f} ({self.tide_type})'})
        chart.set_x_axis({'name': f'Waktu ({tz})', 'date_axis': True, 'num_format': 'dd/mm'})
        chart.set_size({'width': 1000, 'height': 400})
        worksheet.insert_chart('D2', chart)
        writer.close()
        print(f"[SUCCESS] Excel generated: {filename}")

    def export_html_pro(self, filename=None):
        if self.df is None: return
        if filename is None: filename = f"Visualisasi_Pasut_{self.metadata['tz_name']}.html"
            
        tz = self.metadata['tz_name']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self.df['datetime_local'],
            y=self.df['elevation_m'],
            mode='lines',
            fill='tozeroy', 
            name='Elevasi Air',
            line=dict(color='#0077be', width=2), 
            fillcolor='rgba(0, 119, 190, 0.4)'
        ))
        
        # Tambahkan Garis MSL (Mean Sea Level)
        msl = self.df['elevation_m'].mean()
        fig.add_hline(y=msl, line_dash="dash", line_color="red", 
                     annotation_text=f"MSL ({msl:.2f}m)", annotation_position="top right")

        # Format nilai F untuk ditampilkan di HTML
        f_display = f"&#8776; {self.formzahl:.3f}" 

        fig.update_layout(
            title=dict(
                text=f"<b>Analisis Pasang Surut Harmonik</b><br><sub>Lokasi: {self.metadata['lat']}, {self.metadata['lon']} | Zona: {tz} | <b>Tipe: {self.tide_type} (F {f_display})</b></sub>",
                font=dict(size=18)
            ),
            xaxis=dict(
                title=f"Waktu ({tz})",
                gridcolor='rgba(0,0,0,0.1)',
                rangeslider=dict(visible=True),
                # === RESTORED FEATURE: Smart Ticks untuk Hari ===
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
    target_file = 'wg2pasut1-28jan.txt' 
    
    # Dummy data untuk testing (2 komponen sinus)
    t = pd.date_range(start='2025-01-01', periods=24*30, freq='H')
    y = 1.0 * np.sin(2 * np.pi * (t.hour / 12.42)) + 0.5 * np.sin(2 * np.pi * (t.hour / 23.93))
    dummy_csv = "Lat: -8.5 Lon: 112.5 z(m)\nLat Lon Date Time elevation_m\n"
    for time, val in zip(t, y):
        dummy_csv += f"-8.5 112.5 {time.strftime('%Y-%m-%d %H:%M:%S')} {val:.3f}\n"

    if os.path.exists(target_file):
        print(f"[SYSTEM] Membaca file: {target_file}")
        architect = HydroTideArchitect(file_path=target_file)
    else:
        print("[SYSTEM] Menggunakan Data Dummy Simulasi.")
        architect = HydroTideArchitect(raw_data_string=dummy_csv)

    df = architect.process_data()
    
    if df is not None:
        architect.analyze_tide_type() 
        architect.recommend_fieldwork_window()
        architect.export_excel_pro()
        architect.export_html_pro()
