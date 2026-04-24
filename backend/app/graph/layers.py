import networkx as nx
from typing import Any

def stress_layer(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    sub = nx.MultiDiGraph()
    for n, d in G.nodes(data=True):
        if d.get('type') == 'Person':
            sub.add_node(n, **d)
    return sub

def collab_layer(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    sub = nx.MultiDiGraph()
    for n, d in G.nodes(data=True):
        if d.get('type') == 'Person':
            sub.add_node(n, **d)
    for u, v, d in G.edges(data=True):
        if d.get('type') in ('co_authored', 'reviews_pr') and sub.has_node(u) and sub.has_node(v):
            sub.add_edge(u, v, **d)
    return sub

def workload_layer(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    sub = nx.MultiDiGraph()
    for n, d in G.nodes(data=True):
        if d.get('type') in ('Person', 'Task'):
            sub.add_node(n, **d)
    for u, v, d in G.edges(data=True):
        if d.get('type') == 'assigned_to' and sub.has_node(u) and sub.has_node(v):
            sub.add_edge(u, v, **d)
    return sub

def to_json(G: nx.MultiDiGraph, layer: str) -> dict[str, Any]:
    nodes = []
    for n, d in G.nodes(data=True):
        nodes.append({"id": n, **d})
    links = []
    for u, v, d in G.edges(data=True):
        links.append({"source": u, "target": v, **d})
    return {"layer": layer, "nodes": nodes, "links": links}
