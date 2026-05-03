import os
import requests
from datetime import datetime
import schedule
import time

TELEGRAM_TOKEN = os.environ.get("8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w")
CHAT_ID = os.environ.get("5799852232")
API_KEY = os.environ.get("74f87c4af90801cb16a63efc59c301a5")

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    print("Telegram response:", r.status_code, r.text)

def get_fixtures():
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"date": today, "status": "NS"}
    response = requests.get(url, headers=headers, params=params)
    print("Fixtures response:", response.status_code)
    data = response.json()
    print("Total fixtures:", len(data.get("response", [])))
    return data.get("response", [])

def get_team_stats(team_id, league_id, season):
    url = "https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": API_KEY}
    params = {"team": team_id, "league": league_id, "season": season}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("response", {})

def calculate_btts_probability(home_stats, away_stats):
    try:
        home_scored = home_stats["goals"]["for"]["average"]["home"]
        home_conceded = home_stats["goals"]["against"]["average"]["home"]
        away_scored = away_stats["goals"]["for"]["average"]["away"]
        away_conceded = away_stats["goals"]["against"]["average"]["away"]
        home_scores = (float(home_scored) + float(away_conceded)) / 2
        away_scores = (float(away_scored) + float(home_conceded)) / 2
        btts_prob = min(home_scores, 1.5) * min(away_scores, 1.5) * 50
        return min(round(btts_prob), 95)
    except:
        return 0

def calculate_over_probability(home_stats, away_stats, threshold):
    try:
        home_avg = float(home_stats["goals"]["for"]["average"]["home"])
        away_avg = float(away_stats["goals"]["for"]["average"]["away"])
        total_avg = home_avg + away_avg
        if threshold == 1.5:
            prob = min(round((total_avg / 2.5) * 85), 95)
        else:
            prob = min(round((total_avg / 3.5) * 75), 95)
        return prob
    except:
        return 0

def analyze_matches():
    print("Analyse des matchs en cours...")
    send_message("🔍 Analyse des matchs du jour en cours...")
    fixtures = get_fixtures()
    if not fixtures:
        send_message("⚠️ Aucun match trouvé pour aujourd'hui.")
        return

    top_pronostics = []
    for fixture in fixtures[:20]:
        try:
            league_id = fixture["league"]["id"]
            season = fixture["league"]["season"]
            home_team = fixture["teams"]["home"]["name"]
            away_team = fixture["teams"]["away"]["name"]
            home_id = fixture["teams"]["home"]["id"]
            away_id = fixture["teams"]["away"]["id"]
            match_time = fixture["fixture"]["date"][11:16]
            home_stats = get_team_stats(home_id, league_id, season)
            away_stats = get_team_stats(away_id, league_id, season)
            if not home_stats or not away_stats:
                continue
            btts = calculate_btts_probability(home_stats, away_stats)
            over15 = calculate_over_probability(home_stats, away_stats, 1.5)
            over25 = calculate_over_probability(home_stats, away_stats, 2.5)
            best_prob = max(btts, over15, over25)
            if best_prob >= 65:
                top_pronostics.append({
                    "match": f"{home_team} vs {away_team}",
                    "time": match_time,
                    "btts": btts,
                    "over15": over15,
                    "over25": over25,
                    "best": best_prob
                })
        except Exception as e:
            print("Erreur:", e)
            continue

    top_pronostics.sort(key=lambda x: x["best"], reverse=True)
    top_5 = top_pronostics[:5]

    if not top_5:
        send_message("⚠️ Aucun pronostic fiable trouvé aujourd'hui.")
        return

    today = datetime.now().strftime("%d/%m/%Y")
    message = f"🗓 *PRONOSTICS DU JOUR — {today}*\n\n"
    for i, p in enumerate(top_5, 1):
        message += f"*{i}. {p['match']}* — 🕐 {p['time']}\n"
        message += f"   ✅ BTTS : *{p['btts']}%*\n"
        message += f"   ✅ +1.5 buts : *{p['over15']}%*\n"
        message += f"   ✅ +2.5 buts : *{p['over25']}%*\n\n"
    message += "⚠️ _Pariez avec responsabilité_"
    send_message(message)

def run():
    print("Bot démarré !")
    send_message("🤖 Bot PronoFoot démarré avec succès !")
    analyze_matches()
    schedule.every().day.at("08:00").do(analyze_matches)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run()
