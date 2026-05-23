import requests
import time
import schedule
from datetime import datetime

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"
FOOTBALL_TOKEN = "7ee09027a9a64c1fa75cc0e37dfe9e0c"

HEADERS = {"X-Auth-Token": FOOTBALL_TOKEN}
BASE_URL = "https://api.football-data.org/v4"

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def get_todays_matches():
    today = datetime.now().strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/matches", headers=HEADERS, params={"dateFrom": today, "dateTo": today})
    print("Today matches status:", r.status_code)
    matches = r.json().get("matches", [])
    return [m for m in matches if m["status"] == "TIMED" or m["status"] == "SCHEDULED"]

def get_team_matches(team_id):
    r = requests.get(f"{BASE_URL}/teams/{team_id}/matches", headers=HEADERS, params={"limit": 10, "status": "FINISHED"})
    return r.json().get("matches", [])

def calculate_stats(matches, team_id):
    wins = draws = losses = goals_for = goals_against = 0
    for m in matches:
        home_id = m["homeTeam"]["id"]
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

def calculate_prono(home_id, away_id, home_name, away_name):
    home_matches = get_team_matches(home_id)
    away_matches = get_team_matches(away_id)
    home_stats = calculate_stats(home_matches, home_id)
    away_stats = calculate_stats(away_matches, away_id)
    home_form = get_form(home_matches, home_id)
    away_form = get_form(away_matches, away_id)

    if not home_stats or not away_stats:
        return None, 0

    home_win_rate = home_stats["wins"] / home_stats["total"]
    away_win_rate = away_stats["wins"] / away_stats["total"]
    total_rate = home_win_rate + away_win_rate

    if total_rate > 0:
        home_prob = round(home_win_rate / total_rate * 100)
        away_prob = 100 - home_prob
    else:
        home_prob = away_prob = 50

    btts_prob = min(round((home_stats["goals_against"] + away_stats["goals_against"]) / 2 * 60), 90)
    avg_goals = round((home_stats["goals_for"] + away_stats["goals_for"]) / 2, 1)
    over15_prob = min(round(avg_goals / 2 * 85), 92)
    over25_prob = min(round(avg_goals / 3 * 75), 88)

    best_prob = max(home_prob, away_prob, btts_prob, over15_prob)

    return {
        "home": home_name,
        "away": away_name,
        "home_prob": home_prob,
        "away_prob": away_prob,
        "btts": btts_prob,
        "over15": over15_prob,
        "over25": over25_prob,
        "home_goals": home_stats["goals_for"],
        "away_goals": away_stats["goals_for"],
        "home_form": home_form,
        "away_form": away_form,
        "best": best_prob
    }, best_prob

def niveau(p):
    if p >= 70:
        return "TRES FIABLE"
    elif p >= 55:
        return "FIABLE"
    else:
        return "RISQUE"

def format_prono(p):
    winner = p["home"] if p["home_prob"] > p["away_prob"] else p["away"]
    winner_prob = max(p["home_prob"], p["away_prob"])
    msg = f"{p['home']} vs {p['away']}\n"
    msg += f"Favori : {winner} ({winner_prob}%) - {niveau(winner_prob)}\n"
    msg += f"BTTS : {p['btts']}% - {niveau(p['btts'])}\n"
    msg += f"+1.5 buts : {p['over15']}% - {niveau(p['over15'])}\n"
    msg += f"+2.5 buts : {p['over25']}% - {niveau(p['over25'])}\n"
    msg += f"Forme : {p['home_form']} vs {p['away_form']}\n"
    return msg

def auto_pronostics():
    print("Analyse automatique en cours...")
    send_message("Analyse des matchs du jour en cours...")
    matches = get_todays_matches()

    if not matches:
        send_message("Aucun match trouve pour aujourd'hui.")
        return

    print(f"{len(matches)} matchs trouves")
    pronostics = []

    for m in matches[:30]:
        try:
            home_id = m["homeTeam"]["id"]
            away_id = m["awayTeam"]["id"]
            home_name = m["homeTeam"]["name"]
            away_name = m["awayTeam"]["name"]
            prono, score = calculate_prono(home_id, away_id, home_name, away_name)
            if prono:
                pronostics.append(prono)
            time.sleep(1)
        except Exception as e:
            print("Erreur:", e)
            continue

    if not pronostics:
        send_message("Pas assez de donnees pour aujourd'hui.")
        return

    pronostics.sort(key=lambda x: x["best"], reverse=True)
    top5 = pronostics[:5]

    today = datetime.now().strftime("%d/%m/%Y")
    msg = f"TOP 5 PRONOSTICS DU JOUR - {today}\n\n"
    for i, p in enumerate(top5, 1):
        msg += f"{i}. {format_prono(p)}\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def search_team(name):
    r = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params={"limit": 100})
    teams = r.json().get("teams", [])
    for team in teams:
        if name.lower() in team["name"].lower() or name.lower() in team.get("shortName", "").lower():
            return team["id"], team["name"]
    return None, None

def predict_manual(home_name, away_name):
    send_message(f"Recherche de {home_name} vs {away_name}...")
    home_id, home_full = search_team(home_name)
    away_id, away_full = search_team(away_name)

    if not home_id:
        send_message(f"Equipe '{home_name}' non trouvee.")
        return
    if not away_id:
        send_message(f"Equipe '{away_name}' non trouvee.")
        return

    send_message(f"Analyse de {home_full} vs {away_full}...")
    prono, _ = calculate_prono(home_id, away_id, home_full, away_full)

    if not prono:
        send_message("Pas assez de donnees pour ces equipes.")
        return

    winner = prono["home"] if prono["home_prob"] > prono["away_prob"] else prono["away"]
    winner_prob = max(prono["home_prob"], prono["away_prob"])

    msg = f"PREDICTION : {home_full} vs {away_full}\n\n"
    msg += f"Victoire {prono['home']} : {prono['home_prob']}%\n"
    msg += f"Victoire {prono['away']} : {prono['away_prob']}%\n\n"
    msg += f"Favori : {winner} ({winner_prob}%) - {niveau(winner_prob)}\n\n"
    msg += f"BTTS : {prono['btts']}% - {niveau(prono['btts'])}\n"
    msg += f"+1.5 buts : {prono['over15']}% - {niveau(prono['over15'])}\n"
    msg += f"+2.5 buts : {prono['over25']}% - {niveau(prono['over25'])}\n\n"
    msg += f"Moy. buts {prono['home']} : {prono['home_goals']}/match\n"
    msg += f"Moy. buts {prono['away']} : {prono['away_goals']}/match\n\n"
    msg += f"Forme {prono['home']} : {prono['home_form']}\n"
    msg += f"Forme {prono['away']} : {prono['away_form']}\n\n"
    msg += "Pariez avec responsabilite"
    send_message(msg)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    r = requests.get(url, params=params)
    return r.json().get("result", [])

def run():
    print("Bot demarre !")
    send_message("Bot PronoFoot pret !\nPronostics automatiques chaque matin a 8h00\nOu envoie : Arsenal vs Chelsea")
    auto_pronostics()
    schedule.every().day.at("08:00").do(auto_pronostics)
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
                        predict_manual(parts[0].strip(), parts[1].strip())
            schedule.run_pending()
            time.sleep(5)
        except Exception as e:
            print("Erreur:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
