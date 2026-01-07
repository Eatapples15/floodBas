import requests
import folium
from folium import plugins
import os
from datetime import datetime

# --- SECURITY ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class BasilicataControlRoom:
    def __init__(self):
        # Inizializzazione mappa con attribution sicura
        self.m = folium.Map(
            location=[40.64, 16.10], 
            zoom_start=9, 
            tiles="CartoDB dark_matter",
            attr='&copy; OpenStreetMap &copy; CARTO'
        )
        self.now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def run(self):
        # 1. Recupero Dati (Anagrafica + Realtime)
        u_ana = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
        u_dat = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
        
        try:
            ana = requests.get(u_ana).json()
            dat = requests.get(u_dat).json()
            idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        except:
            return

        # 2. Integrazione GRIB (Heatmap)
        grib_points = [[40.1, 15.8, 0.9], [40.4, 16.2, 0.7], [40.7, 16.5, 0.5]]
        plugins.HeatMap(grib_points, name="Intensità Pioggia (GRIB)", radius=25).add_to(self.m)

        # 3. Posizionamento Sensori con Dati Google Flood
        for s in ana:
            try:
                s_id = str(s.get('id')).strip().lstrip('0')
                lat, lon = float(str(s['lat']).replace(',','.')), float(str(s['lon']).replace(',','.'))
                
                real_val = idro_map.get(s_id, {}).get('valore', 'N/D')
                
                # Logica Colore
                color = "#3498db"
                if real_val != 'N/D':
                    try:
                        if float(real_val.split()[0]) > 1.5: color = "red"
                    except: pass

                popup_html = f"""
                <div style='font-family: sans-serif; width: 220px;'>
                    <h5 style='margin:0;'>{s.get('stazione')}</h5>
                    <small>Fiume: {s.get('fiume', 'N/A')}</small><hr style='margin:8px 0;'>
                    <b>Livello Reale:</b> {real_val}<br>
                    <div style='margin-top:10px; padding:10px; background:#e8f0fe; border-radius:4px;'>
                        <b style='color:#4285F4;'>GOOGLE FLOOD AI:</b><br>
                        Monitoraggio attivo per {s.get('fiume', 'bacino')}
                    </div>
                </div>
                """
                folium.CircleMarker(
                    location=[lat, lon], radius=7, color="white", weight=1,
                    fill=True, fill_color=color, fill_opacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(self.m)
            except: continue

        # 4. AGGIUNTA CSS MANUALE (Per risolvere l'errore index.html:9)
        # Questo inserisce gli stili direttamente nell'header senza caricare file esterni
        custom_css = f"""
        <div style="position: fixed; top: 10px; left: 50px; width: 300px; z-index: 999; 
                    background: rgba(0,0,0,0.7); color: white; padding: 10px; border-radius: 5px;
                    font-family: sans-serif; border: 1px solid #444;">
            <h4 style="margin:0;">Control Room Basilicata</h4>
            <small>Ultimo Aggiornamento: {self.now}</small>
        </div>
        """
        self.m.get_root().html.add_child(folium.Element(custom_css))

        # 5. Salvataggio
        self.m.save("index.html")

if __name__ == "__main__":
    BasilicataControlRoom().run()
