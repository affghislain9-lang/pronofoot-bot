import requests
import time

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"
API_KEY = "74f87c4af90801cb16a63efc59c301a5"

TEAMS = {
    "psg": (85, 61, 2024),
    "paris": (85, 61, 2024),
    "lyon": (80, 61, 2024),
    "marseille": (81, 61, 2024),
    "monaco": (91, 61, 2024),
    "arsenal": (42, 39, 2024),
    "chelsea": (49, 39, 2024),
    "manchester city": (50, 39, 2024),
    "man city": (50, 39, 2024),
    "liverpool": (40, 39, 2024),
    "manchester united": (33, 39, 2024),
    "man united": (33, 39, 2024),
    "tottenham": (47, 39, 2024),
    "real madrid": (541, 140, 2024),
    "barcelona": (529, 140, 2024),
    "atletico madrid": (530, 140, 2024),
    "sevilla": (536, 140, 2024),
    "juventus": (496, 135, 2024),
    "milan": (489, 135, 2024),
    "inter": (505, 135, 2024),
    "napoli": (492, 135, 2024),
    "roma": (497, 135, 2024),
    "bayern": (157, 78, 2024),
    "dortmund": (165, 78, 2024),
    "leipzig": (173, 78, 2024),
    "velez": (435, 128, 2024),
    "newells": (436, 128, 2024),
    "river plate": (403, 128, 2024),
    "boca juniors": (405, 128, 2024),
}

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def find_team(name):
    name = name.lower().strip()
    for key, val in TEAMS.items():
        if key in name or name in key:
            return val
    return None

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
    btts_count = over15_count = over25_count = 0
    for f in fixtures:
        home = f["goals"]["home"] or 0
        away = f["goals"]["away"] or 0
        total = home + away
        if home > 0 and away > 0:
            btts_count += 1
        if total > 1:
            over15_count += 1
        if total > 2:
            over25_count += 1
    n = len(fixtures)
    return round(btts_count/n*100), round(over15_count/n*100), round(over25_count/n*100)

def niveau(p):
    if p >= 75:
        return "TRES FIABLE"
    elif p >= 60:
        return "FIABLE"
    else:
        return "RISQUE"

def predict(home_name, away_name):
    send_message(f"Analyse de {home_name} vs {away_name} en cours...")

    home_data = find_team(home_name)
    away_data = find_team(away_name)

    if not home_data or not away_data:
        equipes_dispo = ", ".join(TEAMS.keys())
        send_message(f"Equipe non trouvee.\n\nEquipes disponibles :\n{equipes_dispo}")
        return

    home_id, home_league, home_season = home_data
    away_id, away_league, away_season = away_data
    league_id = home_league
    season = home_season

    home_stats = get_team_stats(home_id, league_id, season)
    away_stats = get_team_stats(away_id, away_league, away_season)
    h2h = get_h2h(home_id, away_id)

    btts_stats = calculate_btts(home_stats, away_stats)
    over15_stats = calculate_over(home_stats, away_stats, 1.5)
    over25_stats = calculate_over(home_stats, away_stats, 2.5)
    btts_h2h, over15_h2h, over25_h2h = analyze_h2h(h2h)

    btts_final = round((btts_stats + btts_h2h) / 2) if btts_h2h > 0 else btts_stats
    over15_final = round((over15_stats + over15_h2h) / 2) if over15_h2h > 0 else over15_stats
    over25_final = round((over25_stats + over25_h2h) / 2) if over25_h2h > 0 else over25_stats

    msg = f"PREDICTION : {home_name} vs {away_name}\n\n"
    msg += f"BTTS : {btts_final}% - {niveau(btts_final)}\n"
    msg += f"+1.5 buts : {over15_final}% - {niveau(over15_final)}\n"
    msg += f"+2.5 buts : {over25_final}% - {niveau(over25_final)}\n\n"
    msg += f"H2H : {len(h2h)} matchs trouves\n\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    r = requests.get(url, params=params)
    return r.json().get("result", [])

def run():
    print("Bot demarre !")
    send_message("Bot PronoFoot pret ! Envoie un match comme : PSG vs Lyon")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "")
                if " vs " in msg.lower():
                    parts = msg.lower().split(" vs ")
                    if len(parts) == 2:
                        predict(parts[0].strip(), parts[1].strip())
        except Exception as e:
            print("Erreur:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
