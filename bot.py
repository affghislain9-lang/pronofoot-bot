import requests
import time

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"
API_KEY = "74f87c4af90801cb16a63efc59c301a5"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def search_team(name):
    url = "https://v3.football.api-sports.io/teams"
    headers = {"x-apisports-key": API_KEY}
    params = {"search": name}
    r = requests.get(url, headers=headers, params=params)
    print(f"Search {name}:", r.status_code, r.text[:200])
    results = r.json().get("response", [])
    if results:
        team = results[0]["team"]
        team_id = team["id"]
        league_id, season = get_current_league(team_id)
        return team_id, team["name"], league_id, season
    return None, None, None, None

def get_current_league(team_id):
    url = "https://v3.football.api-sports.io/leagues"
    headers = {"x-apisports-key": API_KEY}
    params = {"team": team_id, "current": "true", "type": "League"}
    r = requests.get(url, headers=headers, params=params)
    results = r.json().get("response", [])
    if results:
        league_id = results[0]["league"]["id"]
        season = results[0]["seasons"][0]["year"]
        return league_id, season
    return 39, 2024

def get_team_stats(team_id, league_id, season):
    url = "https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": API_KEY}
    params = {"team": team_id, "league": league_id, "season": season}
    r = requests.get(url, headers=headers, params=params)
    return r.json().get("response", {})

def get_h2h(team1_id, team2_id):
    url = "https://v3.football.api-sports.io/fixtures/headtohead"
    headers = {"x-apisports-key": API_KEY}
    params = {"h2h": f"{team1_id}-{team2_id}", "last": 10}
    r = requests.get(url, headers=headers, params=params)
    return r.json().get("response", [])

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

def analyze_h2h(fixtures):
    if not fixtures:
        return 0, 0, 0
    btts = over15 = over25 = 0
    for f in fixtures:
        home = f["goals"]["home"] or 0
        away = f["goals"]["away"] or 0
        total = home + away
        if home > 0 and away > 0:
            btts += 1
        if total > 1:
            over15 += 1
        if total > 2:
            over25 += 1
    n = len(fixtures)
    return round(btts/n*100), round(over15/n*100), round(over25/n*100)

def niveau(p):
    if p >= 75:
        return "TRES FIABLE"
    elif p >= 60:
        return "FIABLE"
    else:
        return "RISQUE"

def predict(home_name, away_name):
    send_message(f"Recherche de {home_name} et {away_name}...")

    home_id, home_full, home_league, home_season = search_team(home_name)
    away_id, away_full, away_league, away_season = search_team(away_name)

    if not home_id:
        send_message(f"Equipe '{home_name}' non trouvee. Essaie un autre nom.")
        return
    if not away_id:
        send_message(f"Equipe '{away_name}' non trouvee. Essaie un autre nom.")
        return

    send_message(f"Equipes trouvees : {home_full} vs {away_full}\nAnalyse en cours...")

    home_stats = get_team_stats(home_id, home_league, home_season)
    away_stats = get_team_stats(away_id, away_league, away_season)
    h2h = get_h2h(home_id, away_id)

    btts_stats = calculate_btts(home_stats, away_stats)
    over15_stats = calculate_over(home_stats, away_stats, 1.5)
    over25_stats = calculate_over(home_stats, away_stats, 2.5)
    btts_h2h, over15_h2h, over25_h2h = analyze_h2h(h2h)

    btts_final = round((btts_stats + btts_h2h) / 2) if btts_h2h > 0 else btts_stats
    over15_final = round((over15_stats + over15_h2h) / 2) if over15_h2h > 0 else over15_stats
    over25_final = round((over25_stats + over25_h2h) / 2) if over25_h2h > 0 else over25_stats

    msg = f"PREDICTION : {home_full} vs {away_full}\n\n"
    msg += f"BTTS : {btts_final}% - {niveau(btts_final)}\n"
    msg += f"+1.5 buts : {over15_final}% - {niveau(over15_final)}\n"
    msg += f"+2.5 buts : {over25_final}% - {niveau(over25_final)}\n\n"
    msg += f"H2H : {len(h2h)} matchs analyses\n\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    r = requests.get(url, params=params)
    return r.json().get("result", [])

def run():
    print("Bot demarre !")
    send_message("Bot PronoFoot pret ! Envoie un match comme : Arsenal vs Chelsea")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "")
                if " vs " in msg.lower():
                    parts = msg.split(" vs ")
                    if len(parts) == 2:
                        predict(parts[0].strip(), parts[1].strip())
        except Exception as e:
            print("Erreur:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
