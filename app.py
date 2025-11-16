import os
import requests
from flask import Flask, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

SPOLKI = {'CDR': 'CDPROJEKT', 'PKN': 'PKNORLEN', 'PEO': 'PEKAO', 'PGE': 'PGE', 'PKO': 'PKOBP'}

class MonitorGieldowy:
    def __init__(self):
        self.historia_trendow = {}
    
    def pobierz_cene(self, symbol):
        try:
            url = f'https://stooq.pl/q/l/?s={symbol}&f=sd2t2ohlc&h&e=json'
            response = requests.get(url, timeout=10)
            data = response.json()
            return float(data['symbols'][0]['close']) if data['symbols'] else None
        except:
            return None
    
    def analizuj_trend(self, symbol, cena):
        if symbol not in self.historia_trendow:
            self.historia_trendow[symbol] = []
        
        self.historia_trendow[symbol].append({'czas': datetime.now(), 'cena': cena})
        cutoff_time = datetime.now() - timedelta(hours=2)
        self.historia_trendow[symbol] = [p for p in self.historia_trendow[symbol] if p['czas'] > cutoff_time]
        
        if len(self.historia_trendow[symbol]) < 2:
            return "BRAK_DANYCH"
        
        ostatnie = self.historia_trendow[symbol][-2:]
        zmiana = ostatnie[1]['cena'] - ostatnie[0]['cena']
        procent = (zmiana / ostatnie[0]['cena']) * 100
        
        return "WZROST" if procent > 0.5 else "SPADEK" if procent < -0.5 else "STABILNY"
    
    def wyslij_telegram(self, wiadomosc):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return False
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': wiadomosc, 'parse_mode': 'HTML'})
            return True
        except:
            return False

monitor = MonitorGieldowy()

@app.route('/')
def home():
    return jsonify({"status": "MONITORING GIEWŁDOWY DZIAŁA", "wersja": "1.0"})

@app.route('/run-monitoring')
def run_monitoring():
    wyniki, alerty = [], []
    for symbol, nazwa in SPOLKI.items():
        cena = monitor.pobierz_cene(symbol)
        if cena:
            trend = monitor.analizuj_trend(symbol, cena)
            wyniki.append({'symbol': symbol, 'cena': cena, 'trend': trend})
            if trend in ["WZROST", "SPADEK"]:
                alerty.append(f"🚨 {symbol} - TREND {trend}\nCena: {cena:.2f} PLN")
    
    if alerty:
        monitor.wyslij_telegram("📈 ALERTY:\n\n" + "\n".join(alerty))
    
    return jsonify({"status": "OK", "alerty": len(alerty)})

@app.route('/status')
def status():
    return jsonify({"status": "OK", "czas": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
