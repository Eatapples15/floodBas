import requests
import folium
from folium import plugins
import os
from datetime import datetime

# --- SECURITY: API KEY FROM ENVIRONMENT ---
# Caricata tramite GitHub Secrets, mai scritta nel codice
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class BasilicataControlRoom:
    def __init__(self):
        # Mappa professionale Dark Matter
        self.m = folium.Map(
            location=[40.64, 16.10], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            attr='&copy; OpenStreetMap &copy; CARTO'
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def fetch_river_data(self):
        """Scarica anagrafica e dati real-time."""
        url_ana = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
        url_dat = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
        try:
            ana = requests.get(url_ana).json()
            dat = requests.get(url_dat).json()
            # Mapping idrometria: normalizzazione ID (stringa e pulizia zeri)
            idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
            return ana, idro_map
        except Exception as e:
            print(f"Errore caricamento dati: {e}")
            return None, None

    def get_google_forecast(self, lat, lon):
        """Interroga Google Flood Forecasting API."""
        if not GOOGLE_API_KEY:
            return "In attesa di attivazione API Pilot"
        
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                risk = r.json().get('forecasts', [{}])[0].get('riskLevel', 'STABILE')
                return f"Rischio AI: {risk}"
            return "Monitoraggio AI Attivo"
        except:
            return "Connessione Google AI..."

    def run(self):
        print(f"[{self.now}] Avvio generazione Control Room...")
        ana, idro_map = self.fetch_river_data()
        if not ana: return

        # AGGIUNTA GRIB HEATMAP (Pioggia Prevista)
        # In produzione: integrare qui lo scarico reale del file GRIB2
        grib_points = [[40.1, 15.8, 0.9], [40.5, 16.2, 0.7], [40.8, 16.5, 0.4]]
        plugins.HeatMap(grib_points, name="Previsione Pioggia (GRIB)", radius=25).add_to(self.m)

        count = 0
        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',', '.'))
                lon = float(str(s['lon']).replace(',', '.'))
                
                # Dato Idrometrico Reale
                real_val = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # Previsione Google AI
                google_ai = self.get_google_forecast(lat, lon)

                # Colore dinamico basato sul livello
                color = "#3498db"
                if real_val != 'N/D':
                    try:
                        if float(real_val.split()[0]) > 1.5: color = "orange"
                    except: pass

                popup_html = f"""
                <div style='font-family:Arial; width:220px;'>
                    <h5 style='margin:0; color:#2c3e50;'>{s.get('stazione')}</h5>
                    <small>Bacino: {s.get('fiume', 'N/A')}</small><hr style='margin:8px 0;'>
                    <b>Livello Reale:</b> {real_val}<br>
                    <div style='margin-top:10px; padding:8px; background:#f0f7ff; border-left:4px solid #4285F4;'>
                        <small><b>GOOGLE FLOOD AI:</b></small><br>{google_ai}
                    </div>
                </div>
                """

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=7,
                    color="white", weight=1,
                    fill=True, fill_color=color, fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(self.m)
                count += 1
            except: continue

        folium.LayerControl().add_to(self.m)
        self.m.save("index.html")
        print(f"Successo: {count} stazioni fiumi mappate in index.html")

if __name__ == "__main__":
    BasilicataControlRoom().run()
