import requests
import time

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"
FOOTBALL_TOKEN = "7ee09027a9a64c1fa75cc0e37dfe9e0c"

HEADERS = {"X-Auth-Token": FOOTBALL_TOKEN}
BASE_URL = "https://api.football-data.org/v4"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def search_team(name):
    r = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params={"limit": 100})
    print("Teams status:", r.status_code)
    teams = r.json().get("teams", [])
    for team in teams:
        if name.lower() in team["name"].lower() or name.lower() in team.get("shortName", "").lower():
            return team["id"], team["name"]
    return None, None

def get_team_matches(team_id):
    r = requests.get(f"{BASE_URL}/teams/{team_id}/matches", headers=HEADERS, params={"limit": 20, "status": "FINISHED"})
    print("Matches status:", r.status_code)
    return r.json().get("matches", [])

def get_h2h(match_id):
    r = requests.get(f"{BASE_URL}/matches/{match_id}/head2head", headers=HEADERS, params={"limit": 10})
    return r.json().get("matches", [])

def calculate_stats(matches, team_id):
    wins = draws = losses = goals_for = goals_against = 0
    for m in matches:
        home_id = m["homeTeam"]["id"]
        away_id = m["awayTeam"]["id"]
        home_score = m["score"]["fullTime"]["home"] or 0
        away_score = m["score"]["fullTime"]["away"] or 0

        if home_id == team_id:
            goals_for += home_score
            goals_against += away_score
            if home_score > away_score:
                wins += 1
            elif home_score == away_score:
                draws += 1
            else:
                losses += 1
        else:
            goals_for += away_score
            goals_against += home_score
            if away_score > home_score:
                wins += 1
            elif away_score == home_score:
                draws += 1
            else:
                losses += 1

    total = len(matches)
    if total == 0:
        return None
    return {
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": round(goals_for / total, 1),
        "goals_against": round(goals_against / total, 1),
        "total": total
    }

def get_form(matches, team_id):
    form = ""
    for m in matches[-5:]:
        home_id = m["homeTeam"]["id"]
        home_score = m["score"]["fullTime"]["home"] or 0
        away_score = m["score"]["fullTime"]["away"] or 0
        if home_id == team_id:
            if home_score > away_score:
                form += "V"
            elif home_score == away_score:
                form += "N"
            else:
                form += "D"
        else:
            if away_score > home_score:
                form += "V"
            elif away_score == home_score:
                form += "N"
            else:
                form += "D"
    return form

def predict(home_name, away_name):
    send_message(f"Recherche de {home_name} vs {away_name}...")

    home_id, home_full = search_team(home_name)
    away_id, away_full = search_team(away_name)

    if not home_id:
        send_message(f"Equipe '{home_name}' non trouvee.")
        return
    if not away_id:
        send_message(f"Equipe '{away_name}' non trouvee.")
        return

    send_message(f"Equipes trouvees !\n{home_full} vs {away_full}\nAnalyse en cours...")

    home_matches = get_team_matches(home_id)
    away_matches = get_team_matches(away_id)

    home_stats = calculate_stats(home_matches, home_id)
    away_stats = calculate_stats(away_matches, away_id)
    home_form = get_form(home_matches, home_id)
    away_form = get_form(away_matches, away_id)

    if not home_stats or not away_stats:
        send_message("Pas assez de donnees pour ces equipes.")
        return

    # Probabilites
    home_win_rate = round(home_stats["wins"] / home_stats["total"] * 100)
    away_win_rate = round(away_stats["wins"] / away_stats["total"] * 100)
    total_rate = home_win_rate + away_win_rate
    
    if total_rate > 0:
        home_prob = round(home_win_rate / total_rate * 100)
        away_prob = 100 - home_prob
    else:
        home_prob = away_prob = 50

    # BTTS
    home_btts = home_stats["goals_for"] > 0.8 and home_stats["goals_against"] > 0.8
    away_btts = away_stats["goals_for"] > 0.8 and away_stats["goals_against"] > 0.8
    btts_prob = round((home_stats["goals_against"] + away_stats["goals_against"]) / 2 * 60)
    btts_prob = min(btts_prob, 90)

    # Over 1.5 et 2.5
    avg_goals = round((home_stats["goals_for"] + away_stats["goals_for"]) / 2, 1)
    over15_prob = min(round(avg_goals / 2 * 85), 92)
    over25_prob = min(round(avg_goals / 3 * 75), 88)

    def niveau(p):
        if p >= 70:
            return "TRES FIABLE"
        elif p >= 55:
            return "FIABLE"
        else:
            return "RISQUE"

    winner = home_full if home_prob > away_prob else away_full
    winner_prob = max(home_prob, away_prob)

    msg = f"PREDICTION : {home_full} vs {away_full}\n\n"
    msg += f"Victoire {home_full} : {home_prob}%\n"
    msg += f"Victoire {away_full} : {away_prob}%\n\n"
    msg += f"Favori : {winner} ({winner_prob}%) - {niveau(winner_prob)}\n\n"
    msg += f"BTTS : {btts_prob}% - {niveau(btts_prob)}\n"
    msg += f"+1.5 buts : {over15_prob}% - {niveau(over15_prob)}\n"
    msg += f"+2.5 buts : {over25_prob}% - {niveau(over25_prob)}\n\n"
    msg += f"Moy. buts {home_full} : {home_stats['goals_for']}/match\n"
    msg += f"Moy. buts {away_full} : {away_stats['goals_for']}/match\n\n"
    msg += f"Forme {home_full} : {home_form}\n"
    msg += f"Forme {away_full} : {away_form}\n\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    r = requests.get(url, params=params)
    return r.json().get("result", [])

def run():
    print("Bot demarre !")
    send_message("Bot PronoFoot pret !\nEnvoie un match comme : Arsenal vs Chelsea")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "")
                if msg and " vs " in msg.lower():
                    parts = msg.split(" vs ")
                    if len(parts) == 2:
                        predict(parts[0].strip(), parts[1].strip())
        except Exception as e:
            print("Erreur:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
