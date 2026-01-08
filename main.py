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

COORDS_DIGHE = {
    "Monte Cotugno": {"lat": 40.136, "lon": 16.202, "max": 530.0},
    "Pertusillo": {"lat": 40.271, "lon": 15.908, "max": 155.0},
    "San Giuliano": {"lat": 40.612, "lon": 16.518, "max": 107.0},
    "Basentello": {"lat": 40.735, "lon": 16.142, "max": 39.0},
    "Camastra": {"lat": 40.528, "lon": 15.845, "max": 22.0}
}

def clean_val(v):
    if not v or v == 'N/D': return None
    try:
        # Gestisce formati come "1.234,56", "1,50 m", "0.50"
        s = str(v).replace('m', '').replace('Mmc', '').strip()
        if ',' in s and '.' in s: s = s.replace('.', '')
        return float(s.replace(',', '.'))
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
                    "forecast": [0.1, 0.3, 0.6, 0.4, 0.2],
                    "exists": True
                }
        return {"severity": "NORMALE", "exists": False}
    except: return {"severity": "NORMALE", "exists": False}

def run():
    print("Avvio Engine Basilicata River AI...")
    output = {"last_update": datetime.now().strftime("%d/%m/%Y %H:%M"), "stazioni": [], "dighe": []}

    try:
        # Download dati
        ana = requests.get(URL_ANA).json()
        dat_raw = requests.get(URL_DATI).json()
        inv_raw = requests.get(URL_INVASI).json()
        soglie_raw = requests.get(URL_SOGLIE).json()

        # Mapping dati
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat_raw.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        invasi_map = {d['diga'].strip(): d for d in inv_raw if isinstance(d, dict)}
        # Soglie map: ID -> {L1, L2, L3}
        soglie_map = {str(s['id']).strip().lstrip('0'): s for s in soglie_raw if isinstance(s, dict)}

        for s in ana:
            if not isinstance(s, dict): continue
            s_id = str(s.get('id', '')).strip().lstrip('0')
            lat = float(str(s.get('lat', '0')).replace(',', '.'))
            lon = float(str(s.get('lon', '0')).replace(',', '.'))
            
            val_info = idro_map.get(s_id, {})
            val_str = val_info.get('valore', 'N/D')
            val_num = clean_val(val_str)
            
            # Recupero Soglie
            s_lim = soglie_map.get(s_id, {})
            l1, l2, l3 = clean_val(s_lim.get('soglia1')), clean_val(s_lim.get('soglia2')), clean_val(s_lim.get('soglia3'))

            # Determina stato criticità
            status = "REGOLARE"
            if val_num is not None:
                if l3 and val_num >= l3: status = "PERICOLO"
                elif l2 and val_num >= l2: status = "ALLERTA"
                elif l1 and val_num >= l1: status = "PRE-ALLERTA"

            output["stazioni"].append({
                "nome": s.get('stazione'),
                "source": "REGIONE", "lat": lat, "lon": lon,
                "livello": val_str, "status": status,
                "soglie": {"L1": l1, "L2": l2, "L3": l3}
            })

            # Google Integration
            g_data = get_google_flood_data(lat, lon)
            if g_data["exists"]:
                output["stazioni"].append({
                    "nome": f"Google AI: {s.get('stazione')}",
                    "source": "GOOGLE", "lat": lat + 0.002, "lon": lon + 0.002,
                    "severity": g_data["severity"], "link": g_data["link"],
                    "forecast": g_data["forecast"], "warning": g_data["severity"] != "NORMALE"
                })

        for nome, coords in COORDS_DIGHE.items():
            info = invasi_map.get(nome, {})
            vol = clean_val(info.get('volume_attuale', 0))
            perc = round((vol / coords["max"]) * 100, 1) if vol else 0
            output["dighe"].append({
                "nome": nome, "lat": coords["lat"], "lon": coords["lon"],
                "volume": vol or 0, "percentuale": perc
            })

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
        print("Successo.")

    except Exception as e:
        print(f"Errore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
