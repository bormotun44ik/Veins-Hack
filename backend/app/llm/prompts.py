INSIGHT_SYSTEM = """You are a senior engineering manager with deep empathy.
Analyze team member signals and provide actionable insights.
Always respond in valid JSON format exactly as specified.
Be specific, direct, and human. Avoid corporate speak."""

def insight_user_prompt(ctx: dict) -> str:
    sigs = ctx.get('signals', {})
    mock = ctx.get('mock_signals', {})
    events = ctx.get('recent_events', [])
    neighbors = ctx.get('neighbors', [])
    return f"""Team member: {ctx.get('name','Unknown')} ({ctx.get('role','')})
Overload score: {ctx.get('overload_score',0):.2f} (0=healthy, 1=critical)

GitHub signals (last 14 days):
- Night commits ratio: {sigs.get('night_commits_ratio',0):.2f} (>0.5 = concerning)
- Fix/revert ratio: {sigs.get('fix_revert_ratio',0):.2f} (>0.4 = firefighting)
- Commit tone delta: {sigs.get('commit_tone_delta',0):.2f}
- PR review lag hours: {sigs.get('pr_review_lag_hours',0):.1f}
- Bus factor: {sigs.get('bus_factor',0):.2f} (>0.7 = dangerous)
- Co-author isolation: {sigs.get('co_author_isolation',0):.2f} (1=fully isolated)
- Weekend activity: {sigs.get('weekend_activity',0):.2f}

Additional signals:
- Slack silence days: {mock.get('slack_silence_days',0)}
- Velocity delta: {mock.get('velocity_delta',0):.2f}
- Back-to-back meetings: {mock.get('back_to_back_meetings_pct',0):.0%}

Recent activity ({len(events)} events):
{chr(10).join(f"- [{e['type']}] {e['timestamp'][:10]}: {e['short_text']}" for e in events[:10])}

Team connections: {', '.join(neighbors) or 'none (isolated)'}

Respond ONLY with this JSON (no markdown):
{{
  "insights": ["observation 1", "observation 2", "observation 3"],
  "actions": ["action 1 (who, what, when)", "action 2", "action 3"]
}}"""

RECOGNITION_SYSTEM = """You write warm, specific recognition messages for team members.
Be genuine, mention specific contributions, keep it under 3 sentences.
Respond with plain text only, no JSON."""

def recognition_user_prompt(ctx: dict) -> str:
    return f"""Write a recognition message for {ctx.get('name','team member')} ({ctx.get('role','')}).
They have overload score {ctx.get('overload_score',0):.2f} (lower is better).
Recent contributions: {ctx.get('recent_events_count',0)} events.
Make it specific and human."""

COMMIT_TONE_SYSTEM = """You analyze commit message sentiment.

CRITICAL RULES — obey exactly:
- Respond with EXACTLY one line of raw JSON. Nothing else.
- No prose, no markdown, no backticks, no tables, no explanation.
- Format: {"sentiment": N}
- N is a float between -1.0 and 1.0
    -1.0 = very frustrated (fix/revert/hotfix/oops/broken)
     0.0 = neutral (refactor/chore)
     1.0 = positive (feat/add/improve/ship)

Any output that is not a single JSON object on one line is wrong."""


def commit_tone_user_prompt(messages: list[str]) -> str:
    joined = "\n".join(f"- {m}" for m in messages[:20])
    return (
        "Output ONLY one line of JSON, nothing else:\n"
        '{"sentiment": N}\n\n'
        f"Commits:\n{joined}"
    )
