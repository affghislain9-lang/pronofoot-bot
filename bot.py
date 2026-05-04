import requests
from datetime import datetime
import schedule
import time

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"
API_KEY = "74f87c4af90801cb16a63efc59c301a5"

TOP_LEAGUES = [39, 140, 135, 78, 61, 2, 3, 848, 529, 207, 233, 235, 88, 94, 144, 203, 197, 196, 169, 383]

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    print("Telegram:", r.status_code)

def get_fixtures():
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"date": today}
    response = requests.get(url, headers=headers, params=params)
    print("Fixtures response:", response.status_code)
    data = response.json()
    fixtures = data.get("response", [])
    print("Total fixtures:", len(fixtures))
    return [f for f in fixtures if f["fixture"]["status"]["short"] == "NS"]

def get_team_stats(team_id, league_id, season):
    url = "https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": API_KEY}
    params = {"team": team_id, "league": league_id, "season": season}
    response = requests.get(url, headers=headers, params=params)
    return response.json().get("response", {})

def calculate_btts(home_stats, away_stats):
    try:
        h_scored = float(home_stats["goals"]["for"]["average"]["home"] or 0)
        h_conceded = float(home_stats["goals"]["against"]["average"]["home"] or 0)
        a_scored = float(away_stats["goals"]["for"]["average"]["away"] or 0)
        a_conceded = float(away_stats["goals"]["against"]["average"]["away"] or 0)
        home_scores = (h_scored + a_conceded) / 2
        away_scores = (a_scored + h_conceded) / 2
        prob = min(home_scores, 1.5) * min(away_scores, 1.5) * 50
        return min(round(prob), 95)
    except:
        return 0

def calculate_over(home_stats, away_stats, threshold):
    try:
        home_avg = float(home_stats["goals"]["for"]["average"]["home"] or 0)
        away_avg = float(away_stats["goals"]["for"]["average"]["away"] or 0)
        total = home_avg + away_avg
        if threshold == 1.5:
            return min(round((total / 2.5) * 85), 95)
        else:
            return min(round((total / 3.5) * 75), 95)
    except:
        return 0

def analyze_matches():
    print("Analyse en cours...")
    send_message("Analyse des matchs du jour en cours...")
    fixtures = get_fixtures()

    if not fixtures:
        send_message("Aucun match programme aujourd'hui.")
        return

    top = []
    count = 0
    for fixture in fixtures:
        if count >= 30:
            break
        try:
            league_id = fixture["league"]["id"]
            season = fixture["league"]["season"]
            home_team = fixture["teams"]["home"]["name"]
            away_team = fixture["teams"]["away"]["name"]
            home_id = fixture["teams"]["home"]["id"]
            away_id = fixture["teams"]["away"]["id"]
            match_time = fixture["fixture"]["date"][11:16]
            league_name = fixture["league"]["name"]

            home_stats = get_team_stats(home_id, league_id, season)
            away_stats = get_team_stats(away_id, league_id, season)
            count += 1

            if not home_stats or not away_stats:
                continue

            btts = calculate_btts(home_stats, away_stats)
            over15 = calculate_over(home_stats, away_stats, 1.5)
            over25 = calculate_over(home_stats, away_stats, 2.5)
            best = max(btts, over15, over25)

            if best >= 60:
                top.append({
                    "match": f"{home_team} vs {away_team}",
                    "league": league_name,
                    "time": match_time,
                    "btts": btts,
                    "over15": over15,
                    "over25": over25,
                    "best": best
                })
        except Exception as e:
            print("Erreur:", e)
            continue

    top.sort(key=lambda x: x["best"], reverse=True)
    top5 = top[:5]

    if not top5:
        send_message("Aucun pronostic fiable trouve aujourd'hui.")
        return

    today = datetime.now().strftime("%d/%m/%Y")
    msg = f"PRONOSTICS DU JOUR - {today}\n\n"
    for i, p in enumerate(top5, 1):
        msg += f"{i}. {p['match']}\n"
        msg += f"   Ligue: {p['league']}\n"
        msg += f"   Heure: {p['time']} UTC\n"
        msg += f"   BTTS: {p['btts']}%\n"
        msg += f"   +1.5 buts: {p['over15']}%\n"
        msg += f"   +2.5 buts: {p['over25']}%\n\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def run():
    print("Bot demarre !")
    send_message("Bot PronoFoot demarre !")
    analyze_matches()
    schedule.every().day.at("08:00").do(analyze_matches)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run()
