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

def clean_val(v):
    """Pulisce e converte stringhe numeriche italiane (es '1.234,56' -> 1234.56)."""
    if not v or v == 'N/D': return None
    try:
        return float(str(v).split()[0].replace('.', '').replace(',', '.'))
    except: return None

def get_google_flood_data(lat, lon):
    if not GOOGLE_API_KEY: return {"severity": "NORMALE", "exists": False}
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
                    "forecast": [0.2, 0.4, 0.7, 0.5, 0.3], # Mock forecast
                    "exists": True
                }
        return {"severity": "NORMALE", "exists": False}
    except: return {"severity": "NORMALE", "exists": False}

def run():
    print("Avvio Engine Monitoraggio...")
    output = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "stazioni": [],
        "dighe": []
    }

    # 1. Recupero Anagrafica
    try:
        ana = requests.get(URL_ANA).json()
        if not isinstance(ana, list): ana = []
    except: ana = []

    # 2. Recupero Dati Idro (Parsing sicuro per evitare 'string indices' error)
    idro_map = {}
    try:
        dat_raw = requests.get(URL_DATI).json()
        if isinstance(dat_raw, dict):
            dati_list = dat_raw.get('sensori', {}).get('idrometria', {}).get('dati', [])
            for item in dati_list:
                if isinstance(item, dict) and 'id' in item:
                    s_id = str(item['id']).strip().lstrip('0')
                    idro_map[s_id] = item
    except Exception as e: print(f"Avviso: Errore parsing sensori: {e}")

    # 3. Recupero Invasi (Parsing sicuro)
    invasi_map = {}
    try:
        inv_raw = requests.get(URL_INVASI).json()
        if isinstance(inv_raw, list):
            for entry in inv_raw:
                if isinstance(entry, dict) and 'diga' in entry:
                    invasi_map[entry['diga'].strip()] = entry
    except Exception as e: print(f"Avviso: Errore parsing invasi: {e}")

    # 4. Elaborazione Stazioni (Regione + Google)
    for s in ana:
        if not isinstance(s, dict): continue
        s_id = str(s.get('id', '')).strip().lstrip('0')
        try:
            lat = float(str(s.get('lat', '0')).replace(',', '.'))
            lon = float(str(s.get('lon', '0')).replace(',', '.'))
            
            val_info = idro_map.get(s_id, {})
            val_str = val_info.get('valore', 'N/D')
            val_num = clean_val(val_str)

            # Aggiungi Stazione Regione (Forma: Cerchio)
            output["stazioni"].append({
                "nome": s.get('stazione'),
                "source": "REGIONE",
                "lat": lat, "lon": lon,
                "livello": val_str,
                "warning": (val_num is not None and val_num > 1.8)
            })

            # Aggiungi Stazione Google se esiste (Forma: Quadrato) con offset
            g_data = get_google_flood_data(lat, lon)
            if g_data["exists"]:
                output["stazioni"].append({
                    "nome": f"Google AI: {s.get('stazione')}",
                    "source": "GOOGLE",
                    "lat": lat + 0.003, "lon": lon + 0.003,
                    "severity": g_data["severity"],
                    "link": g_data["link"],
                    "forecast": g_data["forecast"],
                    "warning": (g_data["severity"] != "NORMALE")
                })
        except: continue

    # 5. Elaborazione Dighe
    for nome, coords in COORDS_DIGHE.items():
        info = invasi_map.get(nome, {})
        vol = clean_val(info.get('volume_attuale', 0))
        perc = round((vol / coords["max"]) * 100, 1) if vol else 0
        output["dighe"].append({
            "nome": nome, "lat": coords["lat"], "lon": coords["lon"],
            "volume": vol or 0, "percentuale": perc
        })

    # Scrittura JSON
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print(f"Completato: {len(output['stazioni'])} stazioni processate.")

if __name__ == "__main__":
    run()
