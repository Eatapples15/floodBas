import requests
import folium
from folium import plugins
import os
import json
from datetime import datetime

# --- CONFIGURAZIONE ---
# In GitHub Actions, la chiave API viene letta in modo sicuro dai "Secrets"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "ATTESA_KEY")

CONFIG = {
    "URL_ANAGRAFICA": "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json",
    "URL_DATI": "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json",
    "METEOHUB_API": "https://meteohub.agenziaitaliameteo.it/api/v1/datasets",
    "OUTPUT_FILE": "index.html"
}

class BasilicataFloodControl:
    def __init__(self):
        # Mappa con stile Dark per monitoraggio professionale
        self.m = folium.Map(
            location=[40.64, 16.10], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            attr='&copy; OpenStreetMap &copy; CARTO'
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def get_grib_rain_data(self):
        """
        INNOVAZIONE: Recupera i dati di pioggia previsti (GRIB).
        Qui implementiamo la logica per trasformare i dati MeteoHub in Heatmap.
        """
        # Esempio di griglia di pioggia prevista (lat, lon, intensità)
        # In produzione: sostituire con fetch reale da MeteoHub GRIB2
        rain_grid = [
            [40.1, 15.9, 0.8], [40.2, 16.0, 0.9], [40.5, 15.7, 0.5],
            [40.8, 16.3, 0.4], [39.9, 16.1, 1.0] # Accumuli zona Pollino
        ]
        return rain_grid

    def get_google_forecast(self, lat, lon):
        """Interroga l'API di Google Flood Forecasting (AI)."""
        if GOOGLE_API_KEY == "ATTESA_KEY":
            return "Pilot idranti-basilicata: In attesa di attivazione"
        
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return data.get('forecasts', [{}])[0].get('riskLevel', 'STABILE')
            return "Dato non disponibile"
        except:
            return "Servizio AI Temporaneamente Offline"

    def build_dashboard(self):
        print(f"[{self.now}] Avvio elaborazione dati fiumi Basilicata...")

        # 1. Caricamento Dati
        try:
            ana = requests.get(CONFIG["URL_ANAGRAFICA"]).json()
            dati = requests.get(CONFIG["URL_DATI"]).json()
        except Exception as e:
            print(f"Errore critico: {e}")
            return

        # Mapping dati idrometrici (Fix N/A con normalizzazione ID)
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dati['sensori']['idrometria']['dati']}
        pluvio_map = {str(d['id']).strip().lstrip('0'): d for d in dati['sensori']['pluviometria']['dati']}

        # 2. Layer 1: Heatmap Pioggia Prevista (Dati GRIB)
        rain_data = self.get_grib_rain_data()
        plugins.HeatMap(rain_data, name="Intensità Pioggia Prevista (GRIB)", radius=25, min_opacity=0.4).add_to(self.m)

        # 3. Layer 2: Sensori Fiumi
        river_group = folium.FeatureGroup(name="Livelli Fiumi & Pioggia").add_to(self.m)

        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',', '.'))
                lon = float(str(s['lon']).replace(',', '.'))
                
                # Unione dati reale + AI
                idro_val = idro_map.get(s_id, {}).get('valore', 'N/D')
                pluvio_val = pluvio_map.get(s_id, {}).get('valore', 'N/D')
                google_ai = self.get_google_forecast(lat, lon)

                # Colore dinamico basato sul rischio
                color = "#3498db" # Blu standard
                if idro_val != 'N/D':
                    try:
                        if float(idro_val.split()[0]) > 2.0: color = "red"
                        elif float(idro_val.split()[0]) > 1.2: color = "orange"
                    except: pass

                popup_html = f"""
                <div style='font-family: Arial; width: 220px; border-radius: 10px;'>
                    <h4 style='margin:0; color:#2c3e50;'>{s['stazione']}</h4>
                    <small>Fiume: {s.get('fiume', 'N/A')}</small><hr>
                    <b>Idrometria:</b> {idro_val}<br>
                    <b>Pluviometria:</b> {pluvio_val}<br>
                    <div style='margin-top:10px; padding:8px; background:#f0f7ff; border-left:4px solid #4285F4;'>
                        <b>GOOGLE AI FORECAST:</b><br>{google_ai}
                    </div>
                </div>
                """

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=7,
                    color="white", weight=1,
                    fill=True, fill_color=color, fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(river_group)

            except: continue

        # 4. Legenda e Controlli
        folium.LayerControl().add_to(self.m)
        plugins.Fullscreen().add_to(self.m)
        
        # Salvataggio
        self.m.save(CONFIG["OUTPUT_FILE"])
        print(f"Dashboard generata con successo: {CONFIG['OUTPUT_FILE']}")

if __name__ == "__main__":
    monitor = BasilicataFloodControl()
    monitor.build_dashboard()
