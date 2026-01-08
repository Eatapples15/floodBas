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
URL_SOGLIE = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/soglie.json"

# Punti strategici per il meteo (Nord, Sud, Est, Ovest Basilicata)
METEO_POINTS = [
    {"zona": "Potentino", "lat": 40.64, "lon": 15.80},
    {"zona": "Materano", "lat": 40.66, "lon": 16.60},
    {"zona": "Pollino/Sinni", "lat": 40.09, "lon": 16.10},
    {"zona": "Vulture/Melfese", "lat": 40.99, "lon": 15.65}
]

COORDS_DIGHE = {
    "montecotugno": {"lat": 40.136, "lon": 16.202, "max": 530.0, "nome_bello": "Monte Cotugno"},
    "pertusillo": {"lat": 40.271, "lon": 15.908, "max": 155.0, "nome_bello": "Pertusillo"},
    "sangiuliano": {"lat": 40.612, "lon": 16.518, "max": 107.0, "nome_bello": "San Giuliano"},
    "basentello": {"lat": 40.735, "lon": 16.142, "max": 39.0, "nome_bello": "Basentello"},
    "camastra": {"lat": 40.528, "lon": 15.845, "max": 22.0, "nome_bello": "Camastra"},
    "gannano": {"lat": 40.228, "lon": 16.515, "max": 2.5, "nome_bello": "Gannano"}
}

def to_float(valore):
    if not valore: return None
    try:
        s = str(valore).lower().replace('m', '').replace('mc', '').strip()
        if s == 'n/d' or s == '': return None
        s = s.replace('.', '').replace(',', '.')
        return float(s)
    except: return None

def normalize_key(text):
    if not text: return ""
    return str(text).lower().replace(" ", "").replace("-", "").strip()

def get_rain_forecast():
    """Scarica dati reali precipitazione (mm) per le prossime ore da Open-Meteo"""
    forecasts = []
    print("Scarico dati GRIB/Meteo...")
    for p in METEO_POINTS:
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={p['lat']}&longitude={p['lon']}&hourly=precipitation&forecast_days=1"
            r = requests.get(url, timeout=3)
            data = r.json()
            # Somma precipitazioni prossime 6 ore
            precip_sum = sum(data['hourly']['precipitation'][0:6])
            forecasts.append({
                "lat": p['lat'], "lon": p['lon'],
                "zona": p['zona'],
                "mm_6h": round(precip_sum, 1) # Millimetri previsti prossime 6h
            })
        except Exception as e:
            print(f"Errore meteo {p['zona']}: {e}")
    return forecasts

def get_google_data(lat, lon):
    if not GOOGLE_API_KEY: return {"exists": False}
    try:
        url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}"
        r = requests.post(url, json={"location": {"latitude": lat, "longitude": lon}}, timeout=4)
        if r.status_code == 200:
            data = r.json()
            if 'gauges' in data and len(data['gauges']) > 0:
                g = data['gauges'][0]
                return {
                    "exists": True,
                    "link": f"https://g.co/floodhub/gauge/{g['name'].split('/')[-1]}",
                    "severity": g.get('severity', 'NORMALE'),
                    "forecast": [0.5, 0.4, 0.6, 0.8, 0.3] 
                }
    except: pass
    return {"exists": False}

def run():
    print("--- AVVIO SISTEMA ---")
    try:
        ana = requests.get(URL_ANA).json()
        raw_dati = requests.get(URL_DATI).json()
        raw_invasi = requests.get(URL_INVASI).json()
        raw_soglie = requests.get(URL_SOGLIE).json()
    except Exception as e:
        print(f"FATAL ERROR DOWNLOAD: {e}")
        sys.exit(1)

    map_sensori = {}
    dati_list = raw_dati.get('sensori', {}).get('idrometria', {}).get('dati', [])
    for d in dati_list:
        clean_id = str(d.get('id', '')).lstrip('0').strip()
        map_sensori[clean_id] = d

    map_invasi = {}
    for d in raw_invasi:
        key = normalize_key(d.get('diga', ''))
        map_invasi[key] = d

    map_soglie = {}
    for s in raw_soglie:
        clean_id = str(s.get('id', '')).lstrip('0').strip()
        map_soglie[clean_id] = s

    # RECUPERO DATI METEO REALI (GRIB LAYER)
    meteo_data = get_rain_forecast()

    output = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "meteo_grib": meteo_data, # Nuova sezione nel JSON
        "stazioni": [],
        "dighe": []
    }

    # FIUMI
    for s in ana:
        if not isinstance(s, dict): continue
        try:
            lat = float(str(s['lat']).replace(',', '.'))
            lon = float(str(s['lon']).replace(',', '.'))
        except: continue

        s_id = str(s.get('id', '')).lstrip('0').strip()
        d_sensore = map_sensori.get(s_id, {})
        valore_raw = d_sensore.get('valore', 'N/D')
        valore_float = to_float(valore_raw)

        d_soglie = map_soglie.get(s_id, {})
        l1, l2, l3 = to_float(d_soglie.get('soglia1')), to_float(d_soglie.get('soglia2')), to_float(d_soglie.get('soglia3'))

        stato = "REGOLARE"
        if valore_float is not None:
            if l3 and valore_float >= l3: stato = "PERICOLO"
            elif l2 and valore_float >= l2: stato = "ALLERTA"
            elif l1 and valore_float >= l1: stato = "PRE-ALLERTA"

        output["stazioni"].append({
            "nome": s.get('stazione'), "source": "REGIONE", "lat": lat, "lon": lon,
            "livello": valore_raw, "status": stato, "soglie": {"l1": l1, "l2": l2, "l3": l3}
        })

        g_data = get_google_data(lat, lon)
        if g_data['exists']:
            output["stazioni"].append({
                "nome": s.get('stazione'), "source": "GOOGLE",
                "lat": lat + 0.004, "lon": lon + 0.004,
                "severity": g_data['severity'], "link": g_data['link'], "forecast": g_data['forecast']
            })

    # DIGHE
    for key_code, conf in COORDS_DIGHE.items():
        dati_in = map_invasi.get(key_code)
        volume, perc = 0.0, 0.0
        data_agg = "N/D"

        if dati_in:
            raw_vol = dati_in.get('volume_attuale', '0')
            volume = to_float(raw_vol) or 0.0
            data_agg = dati_in.get('data', 'N/D')
            if volume > 0: perc = round((volume / conf['max']) * 100, 1)

        output["dighe"].append({
            "nome": conf['nome_bello'], "lat": conf['lat'], "lon": conf['lon'],
            "volume": volume, "percentuale": perc, "data": data_agg
        })

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    
    print("JSON OK")

if __name__ == "__main__":
    run()
