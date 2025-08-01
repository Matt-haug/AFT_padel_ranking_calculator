# ---------- backend.py ----------
import pandas as pd

PHASE_FACTORS = {
    "Poule": {"victoire": 1.0, "défaite": 1.0},
    "Tableau": {"victoire": 1.25, "défaite": 0.75},
}

COMPETITION_FACTORS = {"Tour": 1.0, "Interclubs": 1.0, "Mixte": 0.8, "Masters": 1.2}

RANKING_THRESHOLDS_MEN = {
    "P100": {"drop": 0, "up1": 50, "up2": 90},
    "P200": {"drop": 20, "up1": 55, "up2": 90},
    "P300": {"drop": 25, "up1": 60, "up2": 100},
    "P400": {"drop": 30, "up1": 65, "up2": 100},
    "P500": {"drop": 30, "up1": 70, "up2": 100},
    "P700": {"drop": 35, "up1": 75, "up2": 100},
    "P1000": {"drop": 35, "up1": 100, "up2": 100},
}

RANKING_THRESHOLDS_WOMEN = {
    "P50": {"drop": 0, "up1": 50, "up2": 90},
    "P100": {"drop": 5, "up1": 55, "up2": 90},
    "P200": {"drop": 25, "up1": 60, "up2": 100},
    "P300": {"drop": 25, "up1": 65, "up2": 100},
    "P400": {"drop": 30, "up1": 70, "up2": 100},
    "P500": {"drop": 30, "up1": 100, "up2": 100},
}


def get_ranking_correction(player, partner, opp1, opp2, result):
    my_sum = player + partner
    opp_sum = opp1 + opp2

    delta_sum = (my_sum - opp_sum) // 100
    delta_individual = (player - partner) // 100

    delta_sum = max(min(int(delta_sum), 3), -3)
    delta_individual = max(min(int(delta_individual), 3), -3)

    correction_matrix = {
        -3: {-3: 1.70, -2: 1.65, -1: 1.60, 0: 1.55, 1: 1.50, 2: 1.45, 3: 1.40},
        -2: {-3: 1.50, -2: 1.45, -1: 1.40, 0: 1.35, 1: 1.30, 2: 1.25, 3: 1.20},
        -1: {-3: 1.40, -2: 1.35, -1: 1.30, 0: 1.25, 1: 1.20, 2: 1.15, 3: 1.10},
        0: {-3: 1.00, -2: 1.00, -1: 1.00, 0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00},
        1: {-3: 0.85, -2: 0.80, -1: 0.75, 0: 0.70, 1: 0.65, 2: 0.60, 3: 0.55},
        2: {-3: 0.70, -2: 0.65, -1: 0.60, 0: 0.55, 1: 0.50, 2: 0.45, 3: 0.40},
        3: {-3: 0.45, -2: 0.40, -1: 0.35, 0: 0.30, 1: 0.25, 2: 0.20, 3: 0.15},
    }

    if result == "victoire":
        factor = correction_matrix[delta_sum][delta_individual]
    else:
        factor = correction_matrix[-delta_sum][-delta_individual]

    return factor


def compute_win_ratio(df: pd.DataFrame) -> tuple:
    total_points = 0
    total_weights = 0
    match_weights = []

    for _, row in df.iterrows():
        result = row["resultat"].lower()
        comp_type = row["type_competition"]
        phase = row["phase"]
        player = row["classement_joueur"]
        partner = row["classement_partenaire"]
        opp1 = row["classement_adversaire_1"]
        opp2 = row["classement_adversaire_2"]

        phase_factor = PHASE_FACTORS[phase][result]
        comp_factor = COMPETITION_FACTORS[comp_type]
        rank_factor = get_ranking_correction(player, partner, opp1, opp2, result)

        weight = phase_factor * comp_factor * rank_factor
        score = weight if result.lower() == "victoire" else 0
        match_weights.append(weight)

        total_points += score
        total_weights += weight

    if total_weights == 0:
        return 0.0, "Pas de matchs valides."

    ratio = round((total_points / total_weights) * 100, 2)
    category = "P" + str(df["classement_joueur"].iloc[0])
    gender = df["genre"].iloc[0]
    recommendation = generate_recommendation(ratio, len(df), category, gender)
    return ratio, recommendation, match_weights


def generate_recommendation(
    ratio: float, match_count: int, category: str, gender: str
) -> str:
    thresholds = (
        RANKING_THRESHOLDS_WOMEN
        if gender.lower() == "dames"
        else RANKING_THRESHOLDS_MEN
    )

    # Seulement 12 matchs nécessaires sauf si montée de 2 classements alors 24 sont nécessaires
    required_matches = 12
    required_matches_up2 = 24

    if category not in thresholds or match_count < required_matches:
        return f"❕ Pas de recommandation (catégorie inconnue ou moins de {required_matches} matchs effectués)."

    limits = thresholds[category]
    if ratio < limits["drop"]:
        return f"\U0001f7e5 Descente recommandée, le ratio est inférieur au seuil de {limits['drop']}%"

    elif (
        limits["up2"] <= 100
        and ratio > limits["up2"]
        and match_count >= required_matches_up2
    ):
        return f"\U0001f7e9 Vous pouvez monter de 2 niveaux, le seuil requis de {limits['up2']}% a été atteint"

    elif ratio > limits["up1"]:
        return f"\U0001f7e9 Vous pouvez monter de 1 niveau, le seuil requis de {limits['up1']}% a été atteint"
    else:
        return f"\U00002b1c Maintien conseillé, pour info: le seuil de montée est égal à {limits['up1']}%"

