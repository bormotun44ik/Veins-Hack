import json, sqlite3, logging
import networkx as nx
logger = logging.getLogger(__name__)

def build_graph(conn: sqlite3.Connection) -> nx.MultiDiGraph:
    G = nx.MultiDiGraph()
    people = conn.execute("SELECT id, name, role, avatar_url, overload_score, baseline_sentiment FROM people").fetchall()
    if not people:
        return G
    for p in people:
        score = p[4] or 0.0
        status = "red" if score > 0.7 else "yellow" if score > 0.4 else "green"
        G.add_node(p[0], type="Person", name=p[1], role=p[2],
                   avatar_url=p[3] or f"https://i.pravatar.cc/150?u={p[0]}",
                   overload_score=score, status=status, baseline_sentiment=p[5] or 0.0)
    # Edges from events
    commits = conn.execute("SELECT person_id, payload_json FROM events WHERE type='commit'").fetchall()
    repo_counts: dict = {}
    for pid, pj in commits:
        p = json.loads(pj)
        repo = p.get('repo_id', 'unknown')
        key = (pid, repo)
        repo_counts[key] = repo_counts.get(key, 0) + 1
        for co in p.get('co_authors', []):
            if G.has_node(co):
                G.add_edge(pid, co, type='co_authored', weight=1.0, count_2weeks=1)
    for (pid, repo), count in repo_counts.items():
        if not G.has_node(repo):
            G.add_node(repo, type="Repo", name=repo, url="")
        G.add_edge(pid, repo, type='commits_to', weight=float(count), count=count)
    # Reviews
    reviews = conn.execute("SELECT person_id, payload_json FROM events WHERE type='review'").fetchall()
    for pid, pj in reviews:
        p = json.loads(pj)
        lag = p.get('lag_hours', 0)
        G.add_edge(pid, pid, type='reviews_pr', weight=1.0, count=1, avg_lag_hours=lag)
    # Tasks
    try:
        tasks = conn.execute("SELECT id, title, priority, status, deadline, assignee_id FROM tasks").fetchall()
        for t in tasks:
            G.add_node(t[0], type="Task", title=t[1], priority=t[2], status=t[3], deadline=t[4])
            if t[5] and G.has_node(t[5]):
                overdue = bool(t[4])
                G.add_edge(t[0], t[5], type='assigned_to', weight=1.0, priority=t[2], overdue=overdue)
    except Exception:
        pass
    return G
