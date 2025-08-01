import datetime

import requests


def has_multiple_classement_joueur(matches):
    unique_values = set(
        match.get("classement_joueur")
        for match in matches
        if "classement_joueur" in match
    )
    return len(unique_values) > 1


# Get player results from TPPWB API and convert them to replace the JSON of this app
def tppwb_matches(affiliation_number):
    # Use the begining of the previous semester as start date for the matches results
    # (Category change will be computed at the end of the semester, based on the last 12 months at most)
    today = datetime.date.today()
    if today.month <= 6:
        # January to June: use July 1st of the previous year
        date_from = datetime.date(today.year - 1, 7, 7)
    else:
        # July to December: use January 1st of the current year
        date_from = datetime.date(today.year, 1, 1)

    tppwb_data = tppwb_raw_data(affiliation_number, date_from)


    # Sort by ascending order of "Date"
    tppwb_data = sorted(tppwb_data, key=lambda x: x.get("Date", ""))

    matches = []
    for item in tppwb_data:
        if not isinstance(item, dict):
            match = {"genre": "Erreur dict"}
            matches.append(match)
            continue  # skip non-dict items
        if ("0/0" in item.get("Score", "") and item.get("VictoryOrDefeat") == "V") or (
            "Bless." in item.get("Score", "")
        ):
            continue  # Skip WO victories and matches with injury (Bless.)
        match = {
            # Guess the gender from the category
            "genre": "Dames" if item.get("Category").startswith("WD") else "Messieurs",
            "resultat": (
                "Victoire" if item.get("VictoryOrDefeat") == ("V") else "D\u00e9faite"
            ),
            # Guess the type from the category
            "type_competition": (
                "Tour"
                if item.get("Category").startswith("MD")
                or item.get("Category").startswith("WD")
                else "Mixte" if item.get("Category").startswith("MX") else "Interclubs"
            ),
            # Guess the phase
            "phase": (
                "Tableau"
                if item.get("DrawType") == "S" or item.get("TypeTab") == "Tour Final"
                else "Poule"
            ),
            # Compute the category of the player
            "classement_joueur": int(item.get("DoublePairValue", "0"))
            - int(item.get("PartnerDoubleValue", "0")),
            "classement_partenaire": (
                int(item.get("PartnerDoubleValue", "0"))
                if str(item.get("PartnerDoubleValue", "0")).isdigit()
                else 0
            ),
            "classement_adversaire_1": (
                int(item.get("OpponentDoubleValue1", "0"))
                if str(item.get("OpponentDoubleValue1", "0")).isdigit()
                else 0
            ),
            "classement_adversaire_2": (
                int(item.get("OpponentDoubleValue2", "0"))
                if str(item.get("OpponentDoubleValue2", "0")).isdigit()
                else 0
            ),
            "categorie": item.get("Category", "MD100").replace("MD", "P"),
            "date": item.get("Date"),
        }
        # Default to the same ranking for the 2 opponents if one is missing
        if match["classement_adversaire_1"] == 0:
            match["classement_adversaire_1"] = match["classement_adversaire_2"]
        if match["classement_adversaire_2"] == 0:
            match["classement_adversaire_2"] = match["classement_adversaire_1"]
        matches.append(match)

    # Ignore results of past semester if there was a category change
    if has_multiple_classement_joueur(matches):
        # Determine the start date of the current semester
        today = datetime.date.today()
        if today.month <= 6:
            date_from = datetime.date(today.year, 1, 1)
        else:
            date_from = datetime.date(today.year, 7, 7)

        # Filter matches to keep only those from the current semester
        matches = [
            m
            for m in matches
            if datetime.datetime.strptime(m["date"], "%Y-%m-%dT%H:%M:%S").date()
            >= date_from
        ]
        category_change = True
    else:
        category_change = False

    return matches, category_change, date_from



# Get player results from TPPWB API based on affiliation number
# https://padel-webapi.tppwb.be/Help/Api/GET-api-Players-GetResultsByPlayer_affiliationNumber_singleOrDouble_dateFrom_dateTo_top_splitVictoriesAndDefeats_splitSinglesAndDoubles

def tppwb_raw_data(affiliation_number, date_from):
    url = (
        "https://padel-webapi.tppwb.be/api/Players/GetResultsByPlayer"
        f"?affiliationNumber={affiliation_number}"
        f"&singleOrDouble=D"
        f"&splitVictoriesAndDefeats=False"
        f"&splitSinglesAndDoubles=False"
        f"&dateFrom={date_from.strftime('%d%m%Y')}"
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


# Get player info from TPPWB API (Name, FirstName, Rank)
# https://padel-webapi.tppwb.be/Help/Api/GET-api-Players-SearchPlayerForAutoComplete_searchText_isNumFed
def tppwb_player_info(affiliation_number):
    url = (
        "https://padel-webapi.tppwb.be/api/Players/SearchPlayerForAutoComplete"
        f"?searchText={affiliation_number}&isNumFed=true"
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()