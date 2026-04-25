INSIGHT_SYSTEM_V2 = """You are a senior engineering manager with deep empathy
and 15 years of experience. You analyze team member health signals to provide
actionable, role-specific insights.

You have access to:
- Current behavioral signals (last 14 days)
- Historical signals (3 months ago, baseline)
- Peer comparison within the team
- Role-specific concerns and manager questions

Always respond in valid JSON format exactly as specified.
Be specific, direct, human. Cite numbers. Avoid corporate speak.

When you reference signals, mention the comparison:
  "fix-revert ratio jumped from 15% (3 months ago) to 100% (now)"
  "Ivan ranks #1 most overloaded in team — peer Peter at same tenure is 0.20"

When you suggest actions, address the specific role:
  - For Engineering Managers: focus on team velocity, 1:1 quality, OKR alignment
  - For Senior Engineers: focus on technical debt, knowledge transfer, on-call load
  - For Juniors: focus on growth, safety net, learning loops

NEVER make up data. NEVER hallucinate co-workers. Use ONLY data given."""


def insight_user_prompt_v2(ctx: dict) -> str:
    name = ctx.get("name", "Unknown")
    role = ctx.get("role", "")
    sigs = ctx.get("signals", {})
    trend = ctx.get("trend_narrative", {})
    peer = ctx.get("peer_comparison", {})
    role_focus = ctx.get("role_focus", {})
    chunks = ctx.get("retrieved_chunks", [])
    events = ctx.get("recent_events", [])

    # Build trend section — only include if we have real data
    trend_section = ""
    if trend and trend.get("delta_summary"):
        trend_section = f"""
TREND (3 months ago → now):
  baseline: {trend.get('baseline', '')}
  current:  {trend.get('current', '')}
  delta:    {trend.get('delta_summary', '')}
"""

    # Peer comparison section
    peer_section = ""
    if peer:
        best_peer = peer.get("best_peer", {})
        peer_section = f"""
PEER COMPARISON:
  Team avg overload: {peer.get('team_avg_overload', 0):.2f}
  Team median:       {peer.get('team_median_overload', 0):.2f}
  This person:       {peer.get('person_overload', 0):.2f}
  Rank in team:      #{peer.get('rank_in_team', '?')} (of {peer.get('team_size', '?')})
  Best peer (same/similar role): {best_peer.get('id', 'none')}
                       overload {best_peer.get('overload', 0):.2f}
"""

    # Role focus
    role_section = ""
    if role_focus:
        concerns = ", ".join(role_focus.get("primary_concerns", []))
        questions = role_focus.get("manager_questions", [])
        role_section = f"""
ROLE FOCUS — {role}:
  Primary concerns: {concerns}
  Key manager questions:
{chr(10).join(f'    - {q}' for q in questions)}
"""

    # Retrieved chunks
    chunks_section = ""
    if chunks:
        chunks_section = "\nRELEVANT HISTORY (top events):\n"
        for c in chunks[:8]:
            chunks_section += f"  [{c.get('type', '?')}] {c.get('text', '')[:100]}\n"

    return f"""Team member: {name} ({role})
Overload score: {ctx.get('overload_score', 0):.2f} (0=healthy, 1=critical)

CURRENT SIGNALS (last 14 days):
- Night commits ratio: {sigs.get('night_commits_ratio', 0):.2f} (>0.5 concerning)
- Fix/revert ratio: {sigs.get('fix_revert_ratio', 0):.2f} (>0.4 firefighting)
- Commit tone delta: {sigs.get('commit_tone_delta', 0):.2f}
- PR review lag hours: {sigs.get('pr_review_lag_hours', 0):.1f}
- Bus factor: {sigs.get('bus_factor', 0):.2f} (>0.7 dangerous)
- Co-author isolation: {sigs.get('co_author_isolation', 0):.2f} (1=fully isolated)
- Weekend activity: {sigs.get('weekend_activity', 0):.2f}

{trend_section}{peer_section}{role_section}{chunks_section}
Recent activity ({len(events)} events):
{chr(10).join(f"- [{e['type']}] {e['timestamp'][:10]}: {e['short_text']}" for e in events[:10])}

Team connections: {', '.join(ctx.get('neighbors', [])) or 'none (isolated)'}

Respond ONLY with this JSON (no markdown):
{{
  "insights": [
    "specific observation grounded in numbers and trend",
    "another observation comparing peer or historical baseline",
    "third observation tying signals to {role} role concerns"
  ],
  "actions": [
    "concrete action addressing role-specific concern",
    "another concrete action with who/what/when",
    "third concrete action"
  ]
}}"""
