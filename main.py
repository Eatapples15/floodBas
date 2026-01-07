import requests
import folium
from folium import plugins
import os
import json
from datetime import datetime

# --- SICUREZZA: L'API viene letta dal sistema, NON è scritta qui ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class BasilicataFloodMaster:
    def __init__(self):
        # Mappa Dark Matter professionale
        self.m = folium.Map(
            location=[40.64, 16.10], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            attr='&copy; OpenStreetMap contributors &copy; CARTO'
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def fetch_data(self):
        """Scarica i dati reali con gestione errori robusta."""
        url_ana = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
        url_dat = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
        
        try:
            ana = requests.get(url_ana, timeout=10).json()
            dati_raw = requests.get(url_dat, timeout=10).json()
            
            # Estrazione idrometria (gestione struttura corretta)
            idro_list = dati_raw.get('sensori', {}).get('idrometria', {}).get('dati', [])
            # Pulizia ID per accoppiamento perfetto
            idro_map = {str(d['id']).strip().lstrip('0'): d for d in idro_list}
            
            return ana, idro_map
        except Exception as e:
            print(f"ERRORE DOWNLOAD: {e}")
            return None, None

    def get_google_prediction(self, lat, lon):
        """Integrazione Google Flood AI (Pilot idranti-basilicata)."""
        if not GOOGLE_API_KEY or GOOGLE_API_KEY == "TUA_CHIAVE_QUI":
            return "In attesa di attivazione API"
        
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                risk = r.json().get('forecasts', [{}])[0].get('riskLevel', 'STABILE')
                return f"Rischio AI: {risk}"
            return "Monitoraggio AI Attivo"
        except:
            return "Sincronizzazione AI..."

    def build(self):
        print(f"--- Generazione Dashboard Fiumi Basilicata ({self.now}) ---")
        ana, idro_map = self.fetch_data()
        
        if not ana: return

        # Layer GRIB (Simulazione Heatmap Pioggia)
        grib_data = [[40.1, 15.8, 0.9], [40.5, 16.2, 0.6], [40.8, 16.5, 0.4]]
        plugins.HeatMap(grib_data, name="Previsione Pioggia (GRIB)", radius=20).add_to(self.m)

        count = 0
        for s in ana:
            try:
                # Normalizzazione ID e Coordinate
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',', '.'))
                lon = float(str(s['lon']).replace(',', '.'))
                
                # Accoppiamento Dato Reale
                valore = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # Chiamata Google AI
                ai_info = self.get_google_prediction(lat, lon)

                # Colore Dinamico
                color = "#3498db" # Blu
                if valore != 'N/D':
                    try:
                        if float(valore.split()[0]) > 1.5: color = "orange"
                    except: pass

                popup_html = f"""
                <div style='font-family:Arial; width:220px;'>
                    <h5 style='margin:0;'>{s.get('stazione')}</h5>
                    <small style='color:grey;'>Bacino: {s.get('fiume', 'N/A')}</small><hr>
                    <b>Livello Reale:</b> {valore}<br>
                    <div style='margin-top:10px; padding:8px; background:#f0f7ff; border-left:4px solid #4285F4;'>
                        <small><b>GOOGLE AI:</b></small><br>{ai_info}
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
        print(f"SUCCESSO: {count} sensori inseriti in index.html")

if __name__ == "__main__":
    BasilicataFloodMaster().build()
