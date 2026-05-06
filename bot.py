import requests
import time
import json
from collections import defaultdict

TELEGRAM_TOKEN = "8674682571:AAENlfNuobfT-jyKU-dLng-KhdbR8zp-V-w"
CHAT_ID = "5799852232"

# Base de données en mémoire
players = {}
matches = defaultdict(list)

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})

def add_player(name):
    name = name.strip().title()
    if name not in players:
        players[name] = True
        return True
    return False

def add_match(player1, player2, score1, score2):
    key = tuple(sorted([player1.title(), player2.title()]))
    matches[key].append({
        "p1": player1.title(),
        "p2": player2.title(),
        "s1": int(score1),
        "s2": int(score2)
    })

def get_player_list():
    if not players:
        return "Aucun joueur enregistre."
    return "Joueurs enregistres :\n" + "\n".join([f"- {p}" for p in sorted(players.keys())])

def predict_match(p1, p2):
    p1 = p1.strip().title()
    p2 = p2.strip().title()
    key = tuple(sorted([p1, p2]))
    history = matches[key]

    if not history:
        return f"Aucun historique trouve pour {p1} vs {p2}.\nAjoute des resultats avec :\nresultat {p1} vs {p2} : 3-1, 3-0, 1-3"

    total = len(history)
    p1_wins = sum(1 for m in history if m["p1"] == p1 and m["s1"] > m["s2"] or m["p2"] == p1 and m["s2"] > m["s1"])
    p2_wins = total - p1_wins

    p1_pct = round(p1_wins / total * 100)
    p2_pct = 100 - p1_pct

    # Compter les scores
    score_count = defaultdict(int)
    total_sets = []
    for m in history:
        s1 = m["s1"] if m["p1"] == p1 else m["s2"]
        s2 = m["s2"] if m["p1"] == p1 else m["s1"]
        score_count[f"{s1}-{s2}"] += 1
        total_sets.append(s1 + s2)

    # Score le plus frequent
    best_score = max(score_count, key=score_count.get)
    best_score_pct = round(score_count[best_score] / total * 100)

    # Moyenne de sets
    avg_sets = round(sum(total_sets) / len(total_sets), 1)

    # Forme recente (5 derniers)
    recent = history[-5:]
    p1_form = ""
    for m in recent:
        if m["p1"] == p1:
            p1_form += "V" if m["s1"] > m["s2"] else "D"
        else:
            p1_form += "V" if m["s2"] > m["s1"] else "D"

    p2_form = ""
    for m in recent:
        if m["p1"] == p2:
            p2_form += "V" if m["s1"] > m["s2"] else "D"
        else:
            p2_form += "V" if m["s2"] > m["s1"] else "D"

    # Vainqueur probable
    winner = p1 if p1_wins > p2_wins else p2
    winner_pct = max(p1_pct, p2_pct)

    def niveau(p):
        if p >= 70:
            return "TRES FIABLE"
        elif p >= 55:
            return "FIABLE"
        else:
            return "RISQUE"

    msg = f"PREDICTION : {p1} vs {p2}\n"
    msg += f"({total} matchs analyses)\n\n"
    msg += f"Vainqueur probable : {winner} - {winner_pct}% {niveau(winner_pct)}\n\n"
    msg += f"Score exact probable : {best_score} ({best_score_pct}%)\n"
    msg += f"Moyenne de sets : {avg_sets} sets par match\n\n"
    msg += f"Tous les scores H2H :\n"
    for score, count in sorted(score_count.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100)
        msg += f"  {p1} {score} : {count}x ({pct}%)\n"
    msg += f"\nForme recente {p1} : {p1_form}\n"
    msg += f"Forme recente {p2} : {p2_form}\n"
    msg += f"\n{p1} : {p1_wins} victoires\n"
    msg += f"{p2} : {p2_wins} victoires"

    return msg

def parse_results(text):
    # Format: "resultat Joueur1 vs Joueur2 : 3-1, 3-0, 1-3"
    try:
        parts = text.lower().split("resultat")[1]
        players_part, scores_part = parts.split(":")
        p1, p2 = players_part.strip().split(" vs ")
        scores = scores_part.strip().split(",")
        count = 0
        for score in scores:
            score = score.strip()
            if "-" in score:
                s1, s2 = score.split("-")
                add_match(p1.strip(), p2.strip(), s1.strip(), s2.strip())
                count += 1
        return p1.strip().title(), p2.strip().title(), count
    except:
        return None, None, 0

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    r = requests.get(url, params=params)
    return r.json().get("result", [])

def handle_message(text):
    text_lower = text.lower().strip()

    # Ajouter joueur
    if text_lower.startswith("joueur "):
        name = text[7:].strip()
        if add_player(name):
            send_message(f"Joueur '{name}' ajoute avec succes !")
        else:
            send_message(f"Joueur '{name}' existe deja.")

    # Liste joueurs
    elif text_lower in ["liste", "joueurs", "liste joueurs"]:
        send_message(get_player_list())

    # Ajouter resultats
    elif text_lower.startswith("resultat "):
        p1, p2, count = parse_results(text)
        if count > 0:
            send_message(f"{count} resultat(s) ajoute(s) pour {p1} vs {p2} !")
        else:
            send_message("Format incorrect. Utilise :\nresultat Joueur1 vs Joueur2 : 3-1, 3-0, 1-3")

    # Prediction
    elif " vs " in text_lower:
        parts = text.split(" vs ")
        if len(parts) == 2:
            result = predict_match(parts[0].strip(), parts[1].strip())
            send_message(result)

    # Aide
    else:
        msg = "Commandes disponibles :\n\n"
        msg += "1. Ajouter joueur :\njoueur Nom Prenom\n\n"
        msg += "2. Voir liste joueurs :\nliste\n\n"
        msg += "3. Ajouter resultats :\nresultat Joueur1 vs Joueur2 : 3-1, 3-0, 1-3\n\n"
        msg += "4. Prediction :\nJoueur1 vs Joueur2"
        send_message(msg)

def run():
    print("Bot Tennis de Table demarre !")
    send_message("Bot Tennis de Table pret !\n\nEnvoie 'aide' pour voir les commandes.")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "")
                if msg:
                    handle_message(msg)
        except Exception as e:
            print("Erreur:", e)
            time.sleep(5)

if __name__ == "__main__":
    run()
