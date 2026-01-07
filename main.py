import requests
import folium
from folium import plugins
import os
from datetime import datetime

# --- SECURITY ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class BasilicataControlRoom:
    def __init__(self):
        self.m = folium.Map(
            location=[40.64, 16.10], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            attr='&copy; OpenStreetMap contributors'
        )

    def get_google_flood_data(self, lat, lon):
        """
        Interroga Google Flood Forecasting API per ottenere 
        il forecast dettagliato (Previsione a 7 giorni).
        """
        if not GOOGLE_API_KEY:
            return {"risk": "API Key mancante", "trend": "N/D"}
        
        # Endpoint per cercare il gauge più vicino alle coordinate della stazione
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                # Estraiamo i dati di previsione se presenti
                forecasts = data.get('forecasts', [])
                if forecasts:
                    latest = forecasts[0]
                    return {
                        "risk": latest.get('riskLevel', 'STABILE'),
                        "perc": latest.get('extrapolatedProbability', 'N/D'),
                        "time": latest.get('forecastTime', 'N/D')
                    }
            return {"risk": "Monitoraggio Attivo", "trend": "Stabile"}
        except:
            return {"risk": "In aggiornamento", "trend": "N/D"}

    def run(self):
        # Caricamento dati regionali (Anagrafica + Realtime)
        url_ana = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
        url_dat = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
        
        ana = requests.get(url_ana).json()
        dat = requests.get(url_dat).json()
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}

        # Heatmap GRIB Meteo (Integrazione grafica)
        grib_points = [[40.2, 15.9, 0.8], [40.6, 16.3, 0.5]]
        plugins.HeatMap(grib_points, name="Previsione Pioggia (GRIB)", radius=25).add_to(self.m)

        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat, lon = float(str(s['lat']).replace(',','.')), float(str(s['lon']).replace(',','.'))
                
                # 1. Dato Reale Regionale
                val_reale = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # 2. Dato Google Flood Hub AI
                ai = self.get_google_flood_data(lat, lon)

                # Logica Colore Dinamico (Unione Real-time + AI)
                marker_color = "#3498db" # Blu default
                if ai['risk'] in ['HIGH', 'EXTREME']: 
                    marker_color = "red"
                elif ai['risk'] == 'MEDIUM' or (val_reale != 'N/D' and float(val_reale.split()[0]) > 1.2):
                    marker_color = "orange"

                # Layout Popup Professionale con Dati Google
                popup_html = f"""
                <div style='font-family: sans-serif; width: 240px; color: #2c3e50;'>
                    <h5 style='margin:0; border-bottom:2px solid {marker_color}; padding-bottom:5px;'>{s['stazione']}</h5>
                    <div style='margin-top:10px;'>
                        <b>Stato Reale:</b> <span style='float:right;'>{val_reale}</span><br>
                        <b>Fiume:</b> <span style='float:right;'>{s.get('fiume', 'N/A')}</span>
                    </div>
                    <div style='margin-top:15px; padding:10px; background:#e8f0fe; border-radius:8px; border:1px solid #4285F4;'>
                        <img src='https://www.gstatic.com/images/branding/product/1x/googleg_48dp.png' width='15' style='vertical-align:middle;'>
                        <b style='color:#4285F4; font-size:12px;'>GOOGLE FLOOD AI PREDICTION</b><br>
                        <div style='margin-top:5px; font-size:14px;'>
                            <b>Rischio:</b> <span style='color:{marker_color}; font-weight:bold;'>{ai['risk']}</span><br>
                            <small>Probabilità: {ai['perc']}</small>
                        </div>
                    </div>
                    <hr>
                    <a href='https://sites.research.google/floods/l/{lat}/{lon}/12' target='_blank' 
                       style='text-decoration:none; color:white; background:#4285F4; display:block; text-align:center; padding:5px; border-radius:4px; font-size:11px;'>
                       Apri Analisi Idrografica Completa
                    </a>
                </div>
                """

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8,
                    color="white", weight=1,
                    fill=True, fill_color=marker_color, fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{s['stazione']} - AI: {ai['risk']}"
                ).add_to(self.m)
            except: continue

        folium.LayerControl().add_to(self.m)
        self.m.save("index.html")

if __name__ == "__main__":
    BasilicataControlRoom().run()
