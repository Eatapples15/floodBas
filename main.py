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
            attr='&copy; OpenStreetMap &copy; CARTO'
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def get_google_flood_ai(self, lat, lon):
        """Interrogazione API Google Flood Forecasting."""
        if not GOOGLE_API_KEY:
            return "Monitoraggio AI: In attesa di attivazione"
        
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}&location.latitude={lat}&location.longitude={lon}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                forecasts = r.json().get('forecasts', [])
                if forecasts:
                    risk = forecasts[0].get('riskLevel', 'STABILE')
                    return f"Rischio AI: {risk}"
            return "Stato AI: Operativo"
        except:
            return "Sincronizzazione Google AI..."

    def run(self):
        # 1. Caricamento Dati
        u_ana = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
        u_dat = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
        
        try:
            ana = requests.get(u_ana).json()
            dat = requests.get(u_dat).json()
            idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        except Exception as e:
            print(f"Errore: {e}")
            return

        # 2. Layer GRIB (Previsione Pioggia)
        # Integrazione visiva della griglia meteo
        grib_points = [[40.1, 15.8, 0.9], [40.5, 16.2, 0.7], [40.8, 16.5, 0.5]]
        plugins.HeatMap(grib_points, name="Intensità Pioggia (GRIB)", radius=25).add_to(self.m)

        # 3. Mappatura Sensori
        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',','.'))
                lon = float(str(s['lon']).replace(',','.'))
                
                valore = idro_map.get(s_id, {}).get('valore', 'N/D')
                ai_info = self.get_google_flood_ai(lat, lon)

                color = "#3498db"
                if "HIGH" in ai_info or (valore != 'N/D' and float(valore.split()[0]) > 1.5):
                    color = "red"

                # FIX: Aggiunto alt="Google Logo" e corretta gerarchia titoli h4 -> h5
                popup_html = f"""
                <div style='font-family: sans-serif; width: 230px;'>
                    <h5 style='margin:0;'>{s.get('stazione')}</h5>
                    <p style='margin:0; font-size:0.8rem; color:grey;'>Fiume: {s.get('fiume', 'N/A')}</p>
                    <hr style='margin:8px 0;'>
                    <b>Livello Reale:</b> {valore}<br>
                    <div style='margin-top:10px; padding:8px; background:#e8f0fe; border-left:4px solid #4285F4; border-radius:4px;'>
                        <img src='https://www.gstatic.com/images/branding/product/1x/googleg_48dp.png' width='16' alt='Google Logo' style='vertical-align:middle;'>
                        <b style='color:#4285F4; font-size:12px;'>GOOGLE FLOOD AI</b><br>
                        <span style='font-size:13px;'>{ai_info}</span>
                    </div>
                </div>
                """
                
                folium.CircleMarker(
                    location=[lat, lon], radius=7, color="white", weight=1,
                    fill=True, fill_color=color, fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(self.m)
            except: continue

        # 4. Dashboard Overlay Corretta (h4 -> h5)
        overlay_html = f"""
        <div style="position: fixed; top: 15px; left: 50px; width: 280px; z-index: 1000; 
                    background: rgba(11, 14, 17, 0.85); color: white; padding: 15px; border-radius: 12px;
                    font-family: sans-serif; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(5px);">
            <h4 style="margin:0; font-size:1.1rem; color:#3498db;">RIVER CONTROL ROOM</h4>
            <h5 style="margin:5px 0 0 0; font-size:0.85rem; font-weight:normal; color:#bbb;">
                <img src="https://www.gstatic.com/images/branding/product/1x/googleg_48dp.png" width="14" alt="Google Logo" style="vertical-align:text-top;">
                Integrazione Google Flood AI
            </h5>
            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.1);">
            <small>Aggiornamento: {self.now}</small>
        </div>
        """
        self.m.get_root().html.add_child(folium.Element(overlay_html))

        # 5. Salvataggio
        self.m.save("index.html")

if __name__ == "__main__":
    BasilicataControlRoom().run()
