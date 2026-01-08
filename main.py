import requests
import json
import os
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
    """Interroga Google Flood Forecasting API v1."""
    if not GOOGLE_API_KEY:
        return {"status": "KEY_MISSING", "severity": "UNKNOWN"}
    
    # Endpoint per cercare stazioni di monitoraggio (gauges) vicino alle coordinate
    url = f"https://floodforecasting.googleapis.com/v1/gauges:search?key={GOOGLE_API_KEY}"
    payload = {"location": {"latitude": lat, "longitude": lon}}
    
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 200:
            gauges = r.json().get('gauges', [])
            if gauges:
                g = gauges[0]
                # Estraiamo i dettagli reali
                return {
                    "gauge_id": g.get('name'),
                    "status": g.get('status', 'STABILE'),
                    "severity": g.get('severity', 'MINIMA'),
                    "forecast_link": f"https://g.co/floodhub/gauge/{g.get('name').split('/')[-1]}"
                }
        return {"status": "OPERATIVO", "severity": "NORMALE"}
    except Exception as e:
        return {"status": "ERRORE_SYNC", "severity": "UNKNOWN"}

def run():
    try:
        ana = requests.get(URL_ANA).json()
        dat = requests.get(URL_DATI).json()
        invasi = requests.get(URL_INVASI).json()
        
        idro_map = {str(d['id']).strip().lstrip('0'): d for d in dat.get('sensori', {}).get('idrometria', {}).get('dati', [])}
        invasi_latest = {d['diga']: d for d in invasi}
        
        output = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "fiumi": [],
            "dighe": []
        }

        # Elaborazione Fiumi con Google Flood Hub Reale
        for s in ana:
            s_id = str(s.get('id')).strip().lstrip('0')
            lat, lon = float(str(s['lat']).replace(',','.')), float(str(s['lon']).replace(',','.'))
            valore = idro_map.get(s_id, {}).get('valore', 'N/D')
            
            # CHIAMATA REALE GOOGLE
            google_data = get_google_flood_data(lat, lon)
            
            output["fiumi"].append({
                "stazione": s.get('stazione'),
                "fiume": s.get('fiume'),
                "lat": lat, "lon": lon,
                "livello": valore,
                "google_ai": google_data
            })

        # Elaborazione Dighe
        for nome, coords in COORDS_DIGHE.items():
            d_info = invasi_latest.get(nome, {})
            vol = float(d_info.get('volume_attuale', 0))
            output["dighe"].append({
                "nome": nome,
                "lat": coords["lat"], "lon": coords["lon"],
                "volume": vol,
                "percentuale": round((vol / coords["max"]) * 100, 1),
                "data": d_info.get('data', 'N/D')
            })

        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    run()
