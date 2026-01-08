import requests
import json
import os
import sys
from datetime import datetime

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
URL_ANA = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
URL_DATI = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
URL_INVASI = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/storico_invasi.json"

COORDS_DIGHE = {
    "Monte Cotugno": {"lat": 40.136, "lon": 16.202, "max": 530.0},
    "Pertusillo": {"lat": 40.271, "lon": 15.908, "max": 155.0},
    "San Giuliano": {"lat": 40.612, "lon": 16.518, "max": 107.0},
    "Basentello": {"lat": 40.735, "lon": 16.142, "max": 39.0},
    "Camastra": {"lat": 40.528, "lon": 15.845, "max": 22.0}
}

def get_google_flood_data(lat, lon):
    # Dati di default
    default_data = {"severity": "NORMALE", "link": "#", "forecast": [0.1, 0.1, 0.1, 0.1, 0.1], "exists": False}
    if not GOOGLE_API_KEY: return default_data
    
    url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}"
    try:
        r = requests.post(url, json={"location": {"latitude": lat, "longitude": lon}}, timeout=5)
        if r.status_code == 200:
            gauges = r.json().get('gauges', [])
            if gauges:
                g = gauges[0]
                return {
                    "severity": g.get('severity', 'NORMALE'),
                    "link": f"https://g.co/floodhub/gauge/{g.get('name').split('/')[-1]}",
                    "forecast": [0.2, 0.5, 0.9, 0.6, 0.3], # Qui andrebbero i dati storici reali se disponibili
                    "exists": True
                }
        return default_data
    except: return default_data

def run():
    try:
        print("Scaricamento dati...")
        ana = requests.get(URL_ANA).json()
        dat = requests.get(URL_DATI).json()
        invasi = requests.get(URL_INVASI).json()
        
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        invasi_latest = {d['diga'].strip(): d for d in invasi}
        
        output = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "stazioni": []
        }

        # Integrazione Sensori
        for s in ana:
            s_id = str(s.get('id', '')).strip().lstrip('0')
            lat = float(str(s['lat']).replace(',', '.'))
            lon = float(str(s['lon']).replace(',', '.'))
            valore = idro_map.get(s_id, {}).get('valore', 'N/D')
            
            # Recupero dati Google per questa posizione
            g_data = get_google_flood_data(lat, lon)
            
            # Aggiungiamo il sensore regionale
            output["stazioni"].append({
                "nome": s.get('stazione'),
                "source": "REGIONE",
                "lat": lat, "lon": lon,
                "livello": valore,
                "warning": (valore != 'N/D' and float(valore.split()[0].replace(',','.')) > 1.5)
            })
            
            # Se Google ha un sensore qui, aggiungiamo un'entità separata per la mappa
            if g_data["exists"]:
                output["stazioni"].append({
                    "nome": f"Google AI: {s.get('stazione')}",
                    "source": "GOOGLE",
                    "lat": lat + 0.005, # Piccolo offset per non sovrapporli perfettamente
                    "lon": lon + 0.005,
                    "severity": g_data["severity"],
                    "link": g_data["link"],
                    "forecast": g_data["forecast"],
                    "warning": g_data["severity"] != "NORMALE"
                })

        # Gestione Dighe (Fix 0%)
        output["dighe"] = []
        for nome, coords in COORDS_DIGHE.items():
            d_info = invasi_latest.get(nome, {})
            raw_vol = str(d_info.get('volume_attuale', '0')).replace(',', '.').strip()
            try:
                vol = float(raw_vol)
                perc = round((vol / coords["max"]) * 100, 1)
            except:
                vol, perc = 0, 0
                
            output["dighe"].append({
                "nome": nome, "lat": coords["lat"], "lon": coords["lon"],
                "volume": vol, "percentuale": perc
            })

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
        print("JSON Generato con successo.")

    except Exception as e:
        print(f"Errore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
