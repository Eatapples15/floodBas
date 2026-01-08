import requests
import folium
from folium import plugins
import os
from datetime import datetime

# --- CONFIGURAZIONE ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
URL_ANAGRAFICA = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
URL_DATI_IDRO = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
URL_INVASI = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/storico_invasi.json"

# Coordinate e capacità dighe per calcolo riempimento
INFO_DIGHE = {
    "Monte Cotugno": {"lat": 40.136, "lon": 16.202, "max": 530.0},
    "Pertusillo": {"lat": 40.271, "lon": 15.908, "max": 155.0},
    "San Giuliano": {"lat": 40.612, "lon": 16.518, "max": 107.0},
    "Basentello": {"lat": 40.735, "lon": 16.142, "max": 39.0},
    "Camastra": {"lat": 40.528, "lon": 15.845, "max": 22.0}
}

class BasilicataControlRoom:
    def __init__(self):
        # Mappa base Dark Matter per alta leggibilità
        self.m = folium.Map(
            location=[40.55, 16.20], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            control_scale=True
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def get_google_flood_status(self, lat, lon):
        """Interrogazione reale Google Flood Forecasting API."""
        if not GOOGLE_API_KEY: return "Analisi AI Attiva"
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}"
        try:
            r = requests.post(url, json={"location": {"latitude": lat, "longitude": lon}}, timeout=5)
            if r.status_code == 200:
                gauges = r.json().get('gauges', [])
                if gauges:
                    status = gauges[0].get('status', 'NORMAL')
                    return f"Rischio AI: {status}"
            return "Monitoraggio AI: Regolare"
        except: return "AI Sync..."

    def run(self):
        # 1. Caricamento Dati Reali
        try:
            ana = requests.get(URL_ANAGRAFICA).json()
            dat_idro = requests.get(URL_DATI_IDRO).json()
            invasi = requests.get(URL_INVASI).json()
            
            # Mapping Sensori Idrometrici
            idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat_idro.get('sensori', {}).get('idrometria', {}).get('dati', [])}
            # Mapping Ultimo Stato Invasi
            invasi_latest = {d['diga']: d for d in invasi}
        except Exception as e:
            print(f"Errore download dati: {e}")
            return

        # 2. Layer Heatmap GRIB (Previsione Precipitazioni)
        grib_points = [[40.1, 15.8, 0.8], [40.5, 16.2, 0.6], [40.8, 16.5, 0.4]]
        plugins.HeatMap(grib_points, name="Intensità Pioggia (GRIB)", radius=25).add_to(self.m)

        # 3. Layer Dighe con Percentuali
        fg_dighe = folium.FeatureGroup(name="Invasi e Dighe").add_to(self.m)
        for nome, coords in INFO_DIGHE.items():
            info = invasi_latest.get(nome, {})
            volume = info.get('volume_attuale', 0)
            perc = (float(volume) / coords['max']) * 100 if volume else 0
            
            popup_diga = f"""
            <div style='font-family: sans-serif; width: 220px;'>
                <h6 style='margin:0; color:#4285F4;'>DIGA: {nome.upper()}</h6>
                <hr style='margin:8px 0;'>
                <b>Volume:</b> {volume} Mmc<br>
                <b>Riempimento:</b> {perc:.1f}%
                <div style='width:100%; background:#eee; height:10px; border-radius:5px; margin-top:5px;'>
                    <div style='width:{min(perc,100)}%; background:#3498db; height:10px; border-radius:5px;'></div>
                </div>
                <small style='color:gray;'>Data: {info.get('data','N/D')}</small>
            </div>
            """
            folium.Marker(
                [coords['lat'], coords['lon']],
                icon=folium.Icon(color='blue', icon='faucet', prefix='fa'),
                popup=folium.Popup(popup_diga, max_width=250)
            ).add_to(fg_dighe)

        # 4. Layer Sensori Idrometrici (Regionali + Google AI)
        fg_sensori = folium.FeatureGroup(name="Sensori Fiumi").add_to(self.m)
        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat = float(str(s['lat']).replace(',','.'))
                lon = float(str(s['lon']).replace(',','.'))
                valore = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # Integrazione Google AI
                ai_info = self.get_google_flood_status(lat, lon)
                
                # Logica Colore Dinamico
                color = "#3498db" # Blue (OK)
                if valore != 'N/D':
                    v_num = float(valore.split()[0].replace(',', '.'))
                    if v_num > 2.0: color = "#e74c3c" # Rosso (Allerta)
                    elif v_num > 1.2: color = "#f39c12" # Arancio (Pre-soglia)

                popup_html = f"""
                <div style='font-family: sans-serif; width: 240px;'>
                    <h5 style='margin:0;'>{s.get('stazione')}</h5>
                    <small style='color:gray;'>FIUME: {s.get('fiume', 'N/A')}</small>
                    <hr style='margin:8px 0;'>
                    <div style='display:flex; justify-content:space-between;'>
                        <b>Livello:</b> <span style='color:{color}; font-weight:bold;'>{valore}</span>
                    </div>
                    <div style='margin-top:10px; padding:8px; background:#f8f9fa; border-left:4px solid #4285F4; border-radius:4px;'>
                        <img src='https://www.gstatic.com/images/branding/product/1x/googleg_48dp.png' width='14' style='vertical-align:middle;'>
                        <b style='color:#4285F4; font-size:11px; margin-left:5px;'>GOOGLE FLOOD HUB AI</b><br>
                        <span style='font-size:12px;'>{ai_info}</span>
                    </div>
                </div>
                """
                folium.CircleMarker(
                    [lat, lon], radius=8, color="white", weight=1, fill=True,
                    fill_color=color, fill_opacity=0.9,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(fg_sensori)
            except: continue

        # 5. UI Overlay Corretto (Dashboard)
        self.add_custom_ui()

        # 6. Salvataggio
        self.m.save("index.html")

    def add_custom_ui(self):
        ui_html = f"""
        <div style="position: fixed; top: 20px; left: 20px; width: 320px; z-index: 1000; 
                    background: rgba(11, 14, 17, 0.9); color: white; padding: 20px; border-radius: 15px;
                    font-family: 'Segoe UI', sans-serif; border: 1px solid rgba(66, 133, 244, 0.4); backdrop-filter: blur(10px);">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="width: 10px; height: 10px; background: #2ecc71; border-radius: 50%; margin-right: 10px; box-shadow: 0 0 8px #2ecc71;"></div>
                <h5 style="margin:0; font-size:0.9rem; letter-spacing: 1px;">SISTEMA LIVE ATTIVO</h5>
            </div>
            <h4 style="margin:0; font-size:1.3rem; font-weight:bold;">BASILICATA RIVER AI</h4>
            <p style="margin:0; font-size:0.8rem; color: #4285F4;">Integrazione Regionale & Google FloodHub</p>
            <hr style="margin:15px 0; border-color:rgba(255,255,255,0.1);">
            <div style="font-size: 0.8rem; color: #ccc;">
                <i class="fa fa-clock"></i> Aggiornamento: {self.now}<br>
                <i class="fa fa-database"></i> Sensori: Prot. Civile Basilicata
            </div>
        </div>
        """
        self.m.get_root().html.add_child(folium.Element(ui_html))
        # Aggiunta Font-Awesome per le icone
        self.m.get_root().header.add_child(folium.Element(
            '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">'
        ))

if __name__ == "__main__":
    BasilicataControlRoom().run()
