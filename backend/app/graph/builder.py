"""Knowledge graph builder — events → NetworkX MultiDiGraph.

Агрегирует 14-дневную активность в 5 типов рёбер:
commits_to, co_authored, reviews_pr, assigned_to, attended.
"""
import json
import logging
import sqlite3
from collections import defaultdict

import networkx as nx

logger = logging.getLogger(__name__)


def _status(score: float) -> str:
    if score > 0.7:
        return "red"
    if score > 0.4:
        return "yellow"
    return "green"


def build_graph(conn: sqlite3.Connection) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()

    people = conn.execute(
        "SELECT id, name, role, avatar_url, overload_score, baseline_sentiment "
        "FROM people"
    ).fetchall()
    if not people:
        return G

    for pid, name, role, avatar, score, baseline in people:
        score = score or 0.0
        G.add_node(
            pid,
            type="Person",
            name=name,
            role=role,
            avatar_url=avatar or f"https://i.pravatar.cc/150?u={pid}",
            overload_score=score,
            status=_status(score),
            baseline_sentiment=baseline or 0.0,
        )

    # ─── commits_to + co_authored ─────────────────────────────
    commits = conn.execute(
        "SELECT person_id, payload_json FROM events WHERE type='commit'"
    ).fetchall()

    repo_counts: dict[tuple[str, str], int] = defaultdict(int)
    repo_night: dict[tuple[str, str], int] = defaultdict(int)
    coauthor_counts: dict[tuple[str, str], int] = defaultdict(int)

    for pid, pj in commits:
        try:
            p = json.loads(pj)
        except (json.JSONDecodeError, TypeError):
            continue
        repo = p.get("repo_id", "unknown")
        repo_counts[(pid, repo)] += 1

        # co_authors: author → each coauthor
        for co in p.get("co_authors", []):
            if co and co != pid and G.has_node(co):
                coauthor_counts[(pid, co)] += 1

    for (pid, repo), count in repo_counts.items():
        if not G.has_node(repo):
            G.add_node(repo, type="Repo", name=repo, url="")
        G.add_edge(
            pid, repo,
            type="commits_to",
            weight=float(count),
            metadata={"count": count, "recency_days": 14},
        )

    for (src, dst), count in coauthor_counts.items():
        G.add_edge(
            src, dst,
            type="co_authored",
            weight=float(count),
            metadata={"count_2weeks": count},
        )

    # ─── reviews_pr: reviewer → PR author (не self-loop) ─────
    # Нужен join: review.pr_number → pr_author = events(type=pr).person_id
    pr_author_by_number: dict[int, str] = {}
    prs = conn.execute(
        "SELECT person_id, payload_json FROM events WHERE type='pr'"
    ).fetchall()
    for author_pid, pj in prs:
        try:
            p = json.loads(pj)
        except (json.JSONDecodeError, TypeError):
            continue
        num = p.get("number")
        if num is not None:
            pr_author_by_number[num] = author_pid

    reviews = conn.execute(
        "SELECT person_id, payload_json FROM events WHERE type='review'"
    ).fetchall()

    review_agg: dict[tuple[str, str], list[float]] = defaultdict(list)
    for reviewer_pid, pj in reviews:
        try:
            p = json.loads(pj)
        except (json.JSONDecodeError, TypeError):
            continue
        num = p.get("pr_number")
        author = pr_author_by_number.get(num)
        if not author or author == reviewer_pid:
            # Не знаем автора — пропускаем, не рисуем self-loop
            continue
        lag = p.get("lag_hours", 0) or 0
        review_agg[(reviewer_pid, author)].append(lag)

    for (src, dst), lags in review_agg.items():
        count = len(lags)
        avg = sum(lags) / count if count else 0.0
        G.add_edge(
            src, dst,
            type="reviews_pr",
            weight=float(count),
            metadata={"count": count, "avg_lag_hours": round(avg, 2)},
        )

    # ─── assigned_to (Task → Person) ──────────────────────────
    try:
        tasks = conn.execute(
            "SELECT id, title, priority, status, deadline, assignee_id FROM tasks"
        ).fetchall()
        for tid, title, priority, status, deadline, assignee in tasks:
            G.add_node(
                tid,
                type="Task",
                name=title,
                title=title,
                priority=priority,
                status=status,
                deadline=deadline,
            )
            if assignee and G.has_node(assignee):
                G.add_edge(
                    tid, assignee,
                    type="assigned_to",
                    weight=1.0,
                    metadata={
                        "priority": priority,
                        "overdue": bool(deadline),  # truthy, точнее посчитаем в layer
                    },
                )
    except sqlite3.OperationalError:
        logger.debug("tasks table not ready")

    # ─── attended (Person → Meeting) ──────────────────────────
    try:
        meetings = conn.execute(
            "SELECT id, title, datetime, duration_minutes FROM meetings"
        ).fetchall()
        for mid, title, dt, dur in meetings:
            G.add_node(
                mid,
                type="Meeting",
                name=title or mid,
                title=title,
                datetime=dt,
                duration_minutes=dur,
            )

        mtgs = conn.execute(
            "SELECT person_id, payload_json FROM events WHERE type='meeting_attended'"
        ).fetchall()
        for pid, pj in mtgs:
            try:
                p = json.loads(pj)
            except (json.JSONDecodeError, TypeError):
                continue
            mid = p.get("meeting_id")
            if not mid or not G.has_node(mid) or not G.has_node(pid):
                continue
            G.add_edge(
                pid, mid,
                type="attended",
                weight=1.0,
                metadata={
                    "talk_ratio": p.get("talk_ratio", 0),
                    "sentiment": p.get("sentiment", 0),
                },
            )
    except sqlite3.OperationalError:
        logger.debug("meetings table not ready")

    return G
