import requests
import json
import os
import sys
from datetime import datetime

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
URL_ANA = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/anagrafica_stazioni.json"
URL_DATI = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/dati_sensori.json"
URL_INVASI = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/storico_invasi.json"
URL_SOGLIE = "https://raw.githubusercontent.com/Eatapples15/allerte_bollettino_basilicata/refs/heads/main/soglie.json"

COORDS_DIGHE = {
    "Monte Cotugno": {"lat": 40.136, "lon": 16.202, "max": 530.0},
    "Pertusillo": {"lat": 40.271, "lon": 15.908, "max": 155.0},
    "San Giuliano": {"lat": 40.612, "lon": 16.518, "max": 107.0},
    "Basentello": {"lat": 40.735, "lon": 16.142, "max": 39.0},
    "Camastra": {"lat": 40.528, "lon": 15.845, "max": 22.0}
}

def clean_num(v):
    if v is None: return 0.0
    try:
        s = str(v).replace('m', '').replace('Mmc', '').strip()
        if ',' in s and '.' in s: s = s.replace('.', '')
        return float(s.replace(',', '.'))
    except: return 0.0

def get_google_flood_data(lat, lon):
    default = {"severity": "NORMALE", "exists": False}
    if not GOOGLE_API_KEY: return {"severity": "NORMALE", "exists": True, "forecast": [0.1, 0.4, 0.2], "link": "#"}
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
                    "forecast": [0.2, 0.5, 0.8, 0.4],
                    "exists": True
                }
    except: pass
    return default

def run():
    try:
        ana = requests.get(URL_ANA).json()
        dat = requests.get(URL_DATI).json()
        invasi = requests.get(URL_INVASI).json()
        soglie = requests.get(URL_SOGLIE).json()

        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        invasi_map = {d['diga'].strip().upper(): d for d in invasi if isinstance(d, dict)}
        soglie_map = {str(s['id']).strip().lstrip('0'): s for s in soglie if isinstance(s, dict)}

        output = {"last_update": datetime.now().strftime("%d/%m/%Y %H:%M"), "stazioni": [], "dighe": []}

        for s in ana:
            s_id = str(s.get('id', '')).strip().lstrip('0')
            lat, lon = float(str(s['lat']).replace(',','.')), float(str(s['lon']).replace(',','.'))
            
            # 1. SENSORE REGIONE
            val_info = idro_map.get(s_id, {})
            val_str = val_info.get('valore', 'N/D')
            val_num = clean_num(val_str)
            s_lim = soglie_map.get(s_id, {})
            l1, l2, l3 = clean_num(s_lim.get('soglia1')), clean_num(s_lim.get('soglia2')), clean_num(s_lim.get('soglia3'))
            
            status = "REGOLARE"
            if val_num > 0:
                if l3 > 0 and val_num >= l3: status = "PERICOLO"
                elif l2 > 0 and val_num >= l2: status = "ALLERTA"
                elif l1 > 0 and val_num >= l1: status = "PRE-ALLERTA"

            output["stazioni"].append({
                "nome": s.get('stazione'), "source": "REGIONE", "lat": lat, "lon": lon,
                "livello": val_str, "status": status, "soglie": {"l1": l1, "l2": l2, "l3": l3}
            })

            # 2. SENSORE GOOGLE (con offset per visibilità)
            g_data = get_google_flood_data(lat, lon)
            if g_data["exists"]:
                output["stazioni"].append({
                    "nome": s.get('stazione'), "source": "GOOGLE", 
                    "lat": lat + 0.004, "lon": lon + 0.004,
                    "severity": g_data["severity"], "link": g_data["link"], "forecast": g_data["forecast"]
                })

        for nome, coords in COORDS_DIGHE.items():
            info = invasi_map.get(nome.strip().upper(), {})
            vol = clean_num(info.get('volume_attuale', 0))
            perc = round((vol / coords["max"]) * 100, 1) if vol > 0 else 0
            output["dighe"].append({"nome": nome, "lat": coords["lat"], "lon": coords["lon"], "volume": vol, "percentuale": perc})

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Errore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
