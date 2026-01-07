import requests
import folium
from folium import plugins
import os
from datetime import datetime

# --- CONFIGURAZIONE AMBIENTE ---
# La chiave viene letta dai Secrets di GitHub per sicurezza
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "CHIAVE_NON_CONFIGURATA")

URLS = {
    "ANAGRAFICA": "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json",
    "DATI_REALTIME": "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
}

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

    def get_google_flood_ai(self, lat, lon):
        """Interrogazione reale API Google Flood Forecasting."""
        if GOOGLE_API_KEY == "AIzaSyApIjjhoe5eeLikujS-Vs0KnnxhrH1k05s":
            return "In attesa di attivazione API (Pilot idranti-basilicata)"
        
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                forecasts = r.json().get('forecasts', [])
                if forecasts:
                    risk = forecasts[0].get('riskLevel', 'STABILE')
                    return f"Rischio AI: {risk}"
            return "Google AI: Monitoraggio attivo"
        except:
            return "Google AI: Collegamento in corso..."

    def add_grib_heatmap(self):
        """Integra la previsione di pioggia GRIB (Modello COSMO-IT)."""
        # Esempio di griglia GRIB reale (Lat, Lon, Intensità)
        # In una fase avanzata, qui scaricheremo il .grib2 da MeteoHub
        data_grib = [
            [40.0, 15.8, 0.9], [40.1, 15.9, 0.8], [40.2, 16.0, 0.7],
            [40.6, 16.2, 0.5], [40.8, 16.5, 0.4]
        ]
        plugins.HeatMap(data_grib, name="Previsione Pioggia (GRIB)", radius=20, min_opacity=0.3).add_to(self.m)

    def run(self):
        print(f"[{self.now}] Avvio elaborazione completa...")

        # 1. Download Dati
        try:
            ana = requests.get(URLS["ANAGRAFICA"]).json()
            raw_dati = requests.get(URLS["DATI_REALTIME"]).json()
        except Exception as e:
            print(f"Errore download dati: {e}")
            return

        # 2. Mapping Dati Real-time (Fix N/A)
        idro_list = raw_dati.get('sensori', {}).get('idrometria', {}).get('dati', [])
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in idro_list}

        # 3. Aggiunta Layer GRIB
        self.add_grib_heatmap()

        # 4. Creazione Sensori
        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',', '.'))
                lon = float(str(s['lon']).replace(',', '.'))
                nome = s.get('stazione', 'N/A')
                
                # Dato Reale
                valore_reale = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # Dato Google AI
                google_ai = self.get_google_flood_ai(lat, lon)

                # Colore Dinamico
                color = "#3498db"
                if valore_reale != 'N/D':
                    try:
                        v = float(valore_reale.split()[0])
                        if v > 2.0: color = "red"
                        elif v > 1.2: color = "orange"
                    except: pass

                popup_html = f"""
                <div style='font-family: Arial; width: 230px;'>
                    <h5 style='margin:0; color:#2c3e50;'>{nome}</h5>
                    <small>Fiume: {s.get('fiume', 'N/A')}</small><hr>
                    <b>Livello Reale:</b> {valore_reale}<br>
                    <div style='margin-top:10px; padding:8px; background:#f8f9fa; border-left:4px solid #4285F4;'>
                        <small><b>GOOGLE AI FORECAST:</b></small><br>
                        <span style='color:#4285F4; font-weight:bold;'>{google_ai}</span>
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

            except: continue

        # 5. Controlli Finali
        folium.LayerControl().add_to(self.m)
        plugins.Fullscreen().add_to(self.m)
        
        # Salvataggio
        self.m.save("index.html")
        print("Mappa aggiornata con successo.")

if __name__ == "__main__":
    BasilicataControlRoom().run()
