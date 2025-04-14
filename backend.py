# ---------- backend.py ----------
import pandas as pd

PHASE_FACTORS = {
    "Poule": {"Victoire": 1.0, "Défaite": 1.0},
    "Tableau": {"Victoire": 1.25, "Défaite": 0.75},
}

COMPETITION_FACTORS = {"Tour": 1.0, "Interclubs": 0.9, "Mixte": 0.8, "Masters": 1.1}

RANKING_THRESHOLDS_MEN = {
    "P100": {"drop": 40, "up1": 40, "up2": 90},
    "P200": {"drop": 15, "up1": 50, "up2": 90},
    "P300": {"drop": 20, "up1": 55, "up2": 90},
    "P400": {"drop": 25, "up1": 60, "up2": 100},
    "P500": {"drop": 30, "up1": 65, "up2": 100},
    "P700": {"drop": 35, "up1": 70, "up2": 100},
    "P1000": {"drop": 35, "up1": 35, "up2": 100},
}

RANKING_THRESHOLDS_WOMEN = {
    "P50": {"drop": 40, "up1": 40, "up2": 90},
    "P100": {"drop": 15, "up1": 50, "up2": 90},
    "P200": {"drop": 20, "up1": 60, "up2": 100},
    "P300": {"drop": 25, "up1": 60, "up2": 100},
    "P400": {"drop": 25, "up1": 75, "up2": 100},
    "P500": {"drop": 25, "up1": 25, "up2": 100},
}


def get_ranking_correction(player, partner, opp1, opp2):
    my_sum = player + partner
    opp_sum = opp1 + opp2

    delta_sum = (my_sum - opp_sum) // 100
    delta_individual = (player - partner) // 100

    delta_sum = max(min(int(delta_sum), 3), -3)
    delta_individual = max(min(int(delta_individual), 3), -3)

    correction_matrix = {
        -3: {-3: 1.70, -2: 1.50, -1: 1.40, 0: 1.00, 1: 0.85, 2: 0.70, 3: 0.45},
        -2: {-3: 1.65, -2: 1.45, -1: 1.35, 0: 1.00, 1: 0.80, 2: 0.65, 3: 0.40},
        -1: {-3: 1.60, -2: 1.40, -1: 1.30, 0: 1.00, 1: 0.75, 2: 0.60, 3: 0.35},
        0: {-3: 1.55, -2: 1.35, -1: 1.25, 0: 1.00, 1: 0.70, 2: 0.55, 3: 0.30},
        1: {-3: 1.50, -2: 1.30, -1: 1.20, 0: 1.00, 1: 0.65, 2: 0.50, 3: 0.25},
        2: {-3: 1.45, -2: 1.25, -1: 1.15, 0: 1.00, 1: 0.60, 2: 0.45, 3: 0.20},
        3: {-3: 1.40, -2: 1.20, -1: 1.10, 0: 1.00, 1: 0.55, 2: 0.40, 3: 0.15},
    }

    return correction_matrix[delta_sum][delta_individual]


def compute_win_ratio(df: pd.DataFrame) -> tuple:
    total_points = 0
    total_weights = 0

    for _, row in df.iterrows():
        result = row["resultat"]
        comp_type = row["type_competition"]
        phase = row["phase"]
        player = row["classement_joueur"]
        partner = row["classement_partenaire"]
        opp1 = row["classement_adversaire_1"]
        opp2 = row["classement_adversaire_2"]

        phase_factor = PHASE_FACTORS[phase][result]
        comp_factor = COMPETITION_FACTORS[comp_type]
        rank_factor = get_ranking_correction(player, partner, opp1, opp2)

        base_score = 1 if result.lower() == "victoire" else 0
        weight = phase_factor * comp_factor * rank_factor

        total_points += base_score * weight
        total_weights += weight

    if total_weights == 0:
        return 0.0, "Pas de matchs valides."

    ratio = round((total_points / total_weights) * 100, 2)
    category = df["categorie"].iloc[0]
    gender = df["genre"].iloc[0]
    recommendation = generate_recommendation(ratio, len(df), category, gender)
    return ratio, recommendation


def generate_recommendation(
    ratio: float, match_count: int, category: str, gender: str
) -> str:
    thresholds = (
        RANKING_THRESHOLDS_WOMEN
        if gender.lower() == "dames"
        else RANKING_THRESHOLDS_MEN
    )

    if category not in thresholds or match_count < 10:
        return "❕ Pas de recommandation (catégorie inconnue ou <10 matchs)."

    limits = thresholds[category]
    if ratio < limits["drop"]:
        return "\U0001f7e5 Descente recommandée"
    elif limits["up2"] <= 100 and ratio > limits["up2"]:
        return "\U0001f7e9 Montée de 2 niveaux possible"
    elif ratio > limits["up1"]:
        return "\U0001f7e8 Montée de 1 niveau possible"
    else:
        return "\U00002b1c Maintien conseillé"
