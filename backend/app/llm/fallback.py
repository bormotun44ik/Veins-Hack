"""Template-based insight when LLM is unavailable (5xx fallback)."""
from typing import Any


def generate_fallback_insight(ctx: dict[str, Any]) -> dict[str, Any]:
    """Template-based insight когда LLM недоступен.

    Возвращает same shape как нормальный insight response, но без LLM.
    Использует heuristics над сигналами.
    """
    sigs = ctx.get("signals", {})
    name = ctx.get("name", "This person")

    insights: list[str] = []
    actions: list[str] = []

    # Insight 1: топ-3 самых высоких сигнала
    sorted_sigs = sorted(sigs.items(), key=lambda x: -x[1])[:3]
    if sorted_sigs and sorted_sigs[0][1] > 0.5:
        top_three = ", ".join(
            f"{k.replace('_', ' ')} {int(v * 100)}%"
            for k, v in sorted_sigs[:3]
            if v > 0.3
        )
        insights.append(
            f"{name}: {top_three} — composite overload {ctx.get('overload_score', 0):.2f}."
        )

    # Insight 2: trend if available
    trend = ctx.get("trend_narrative", {})
    if trend.get("delta_summary"):
        insights.append(f"Trend (3mo→now): {trend['delta_summary']}")

    # Insight 3: peer comparison if available
    peer = ctx.get("peer_comparison", {})
    if peer.get("rank_in_team"):
        insights.append(
            f"Ranks #{peer['rank_in_team']} most overloaded in team "
            f"(team avg {peer.get('team_avg_overload', 0):.2f})."
        )

    # Fill to 3
    while len(insights) < 3:
        insights.append("Insufficient data for additional patterns.")

    # Actions — role-aware fallback
    role_focus = ctx.get("role_focus", {})
    questions = role_focus.get("manager_questions", [])
    if questions:
        actions.extend(f"Discuss: {q}" for q in questions[:3])

    # Fill to 3
    while len(actions) < 3:
        actions.append("Schedule a 1:1 to discuss workload.")

    return {
        "insights": insights[:3],
        "actions": actions[:3],
    }
