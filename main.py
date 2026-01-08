import requests
import json
import os
import sys
from datetime import datetime

# --- CONFIGURAZIONE ---
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
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "":
        return {"status": "ACTIVE", "severity": "NORMALE", "link": "#"}
    url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}"
    try:
        r = requests.post(url, json={"location": {"latitude": lat, "longitude": lon}}, timeout=5)
        if r.status_code == 200:
            gauges = r.json().get('gauges', [])
            if gauges:
                g = gauges[0]
                return {
                    "status": g.get('status', 'OPERATIVO'),
                    "severity": g.get('severity', 'NORMALE'),
                    "link": f"https://g.co/floodhub/gauge/{g.get('name').split('/')[-1]}"
                }
        return {"status": "OPERATIVO", "severity": "NORMALE", "link": "#"}
    except:
        return {"status": "SYNCING", "severity": "NORMALE", "link": "#"}

def run():
    print("Inizio recupero dati...")
    try:
        # 1. Download e validazione Anagrafica
        r_ana = requests.get(URL_ANA)
        ana = r_ana.json()
        if not isinstance(ana, list):
            raise ValueError(f"Anagrafica non è una lista: {type(ana)}")

        # 2. Download e validazione Dati Sensori
        r_dat = requests.get(URL_DATI)
        dat = r_dat.json()
        
        # FIX: Navigazione sicura nel JSON sensori
        sensori_root = dat.get('sensori', {}).get('idrometria', {}).get('dati', [])
        idro_map = {}
        for d in sensori_root:
            if isinstance(d, dict) and 'id' in d:
                # Pulizia ID e mapping del dizionario dati
                clean_id = str(d['id']).strip().lstrip('0')
                idro_map[clean_id] = d

        # 3. Download e validazione Invasi
        r_inv = requests.get(URL_INVASI)
        invasi = r_inv.json()
        invasi_latest = {}
        if isinstance(invasi, list):
            for d in invasi:
                if isinstance(d, dict) and 'diga' in d:
                    invasi_latest[d['diga']] = d

        output = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "fiumi": [],
            "dighe": [],
            "grib_points": [[40.1, 15.8, 0.8], [40.5, 16.2, 0.6], [40.8, 16.5, 0.4]]
        }

        # Elaborazione Fiumi
        for s in ana:
            if not isinstance(s, dict): continue
            
            s_id = str(s.get('id', '')).strip().lstrip('0')
            try:
                lat = float(str(s.get('lat', '0')).replace(',', '.'))
                lon = float(str(s.get('lon', '0')).replace(',', '.'))
                
                # Recupero dati idro dal mapping creato prima
                dati_stazione = idro_map.get(s_id, {})
                valore = dati_stazione.get('valore', 'N/D')
                
                output["fiumi"].append({
                    "stazione": s.get('stazione', 'Sconosciuta'),
                    "fiume": s.get('fiume', 'N/A'),
                    "lat": lat, "lon": lon,
                    "livello": valore,
                    "google": get_google_flood_data(lat, lon)
                })
            except Exception as e:
                print(f"Salto stazione {s_id} per errore: {e}")
                continue

        # Elaborazione Dighe
        for nome, coords in COORDS_DIGHE.items():
            d_info = invasi_latest.get(nome, {})
            try:
                vol_str = str(d_info.get('volume_attuale', '0')).replace(',', '.')
                vol = float(vol_str)
                output["dighe"].append({
                    "nome": nome, "lat": coords["lat"], "lon": coords["lon"],
                    "volume": vol, "percentuale": round((vol / coords["max"]) * 100, 1),
                    "data": d_info.get('data', 'N/D')
                })
            except: continue

        # Scrittura Finale
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
        
        print(f"Successo! Generati {len(output['fiumi'])} fiumi e {len(output['dighe'])} dighe.")

    except Exception as e:
        print(f"ERRORE CRITICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
