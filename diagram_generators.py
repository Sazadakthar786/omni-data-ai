import io
import base64
import matplotlib.pyplot as plt
import numpy as np

BG = "#060b18"
TEXT = "#e8f4fd"
PRI = "#00f5c4"
SEC = "#7b61ff"
ACC = "#ff6b6b"

def _b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def gen_flowchart(steps, title):
    if not steps:
        steps = ["Start", "Process", "End"]
    fig, ax = plt.subplots(figsize=(8, max(4, len(steps)*0.9)))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    y = 0.9
    ax.text(0.5, 0.98, title, color=PRI, ha="center", va="top", fontsize=14, transform=ax.transAxes)
    for i, s in enumerate(steps):
        ax.add_patch(plt.Rectangle((0.2, y-0.05), 0.6, 0.08, edgecolor=PRI, facecolor="none"))
        ax.text(0.5, y-0.01, s, color=TEXT, ha="center", va="center", transform=ax.transAxes)
        if i < len(steps)-1:
            ax.arrow(0.5, y-0.07, 0, -0.06, width=0.001, head_width=0.02, head_length=0.02, color=SEC, length_includes_head=True, transform=ax.transAxes)
        y -= 0.12
    return _b64(fig)

def gen_er_diagram(entities, relationships):
    import networkx as nx
    names = [e["name"] if isinstance(e, dict) else str(e) for e in entities]
    G = nx.Graph()
    for n in names:
        G.add_node(n)
    for r in relationships:
        a, label, b = r
        G.add_edge(a, b, label=label)
    pos = nx.spring_layout(G, seed=7)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    nx.draw_networkx_nodes(G, pos, node_color=PRI, node_size=800, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color=SEC, width=2, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color=TEXT, ax=ax)
    for (u, v, d) in G.edges(data=True):
        x = (pos[u][0]+pos[v][0])/2
        y = (pos[u][1]+pos[v][1])/2
        ax.text(x, y, d.get("label",""), color=TEXT, fontsize=9)
    ax.set_title("Entity Relationship", color=TEXT)
    ax.axis("off")
    return _b64(fig)

def gen_block_diagram(components, connections):
    comps = components or ["Client","API","Database"]
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    layers = {"Frontend": PRI, "Backend": SEC, "Data": ACC}
    xs = [0.15, 0.45, 0.75]
    for i, (layer, color) in enumerate(layers.items()):
        ax.add_patch(plt.Rectangle((xs[i]-0.13, 0.75), 0.26, 0.18, edgecolor=color, facecolor="none"))
        ax.text(xs[i], 0.84, layer, color=color, ha="center", va="center")
    ys = [0.5, 0.3, 0.1]
    for i, c in enumerate(comps[:3]):
        ax.add_patch(plt.Rectangle((xs[i]-0.13, ys[i]-0.06), 0.26, 0.12, edgecolor=PRI, facecolor="none"))
        ax.text(xs[i], ys[i], c, color=TEXT, ha="center", va="center")
    for a, b, label in connections or []:
        ax.arrow(0.45, 0.5, 0.25, 0, head_width=0.02, head_length=0.02, color=SEC, length_includes_head=True)
    ax.set_title("System Architecture", color=TEXT)
    return _b64(fig)

def gen_uml_usecase(actors, use_cases):
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.25, 0.15), 0.5, 0.7, edgecolor=SEC, facecolor="none"))
    x = 0.15
    y = 0.8
    for a in actors[:3]:
        ax.plot([x, x], [y-0.02, y-0.12], color=PRI)
        ax.plot([x-0.03, x+0.03], [y-0.07, y-0.07], color=PRI)
        ax.text(x, y, a, color=TEXT, ha="center")
        x += 0.1
    ux = 0.5
    uy = 0.75
    for uc in use_cases[:6]:
        ax.add_patch(plt.Circle((ux, uy), 0.08, edgecolor=PRI, facecolor="none"))
        ax.text(ux, uy, uc, color=TEXT, ha="center", va="center", fontsize=9)
        uy -= 0.12
    ax.set_title("UML Use Case", color=TEXT)
    return _b64(fig)

def gen_uml_sequence(objects, interactions):
    objs = objects[:5] or ["Client","API","DB"]
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    xs = np.linspace(0.1, 0.9, len(objs))
    for i, o in enumerate(objs):
        ax.add_patch(plt.Rectangle((xs[i]-0.05, 0.9), 0.1, 0.05, edgecolor=SEC, facecolor="none"))
        ax.text(xs[i], 0.925, o, color=TEXT, ha="center", va="center")
        ax.plot([xs[i], xs[i]], [0.85, 0.15], color="#1a2d4a", linestyle="--")
    y = 0.8
    n = 1
    for a, label, b in interactions[:10]:
        if a in objs and b in objs:
            ia = objs.index(a)
            ib = objs.index(b)
            ax.arrow(xs[ia], y, xs[ib]-xs[ia], 0, head_width=0.01, head_length=0.02, color=PRI, length_includes_head=True)
            ax.text((xs[ia]+xs[ib])/2, y+0.02, f"{n}. {label}", color=TEXT, ha="center", fontsize=9)
            y -= 0.06
            n += 1
    ax.set_title("UML Sequence", color=TEXT)
    return _b64(fig)

def gen_network_diagram(nodes, edges):
    import networkx as nx
    ns = [str(n) for n in nodes] or ["A","B","C","D"]
    G = nx.Graph()
    for n in ns:
        G.add_node(n)
    for e in edges or []:
        G.add_edge(str(e[0]), str(e[1]))
    pos = nx.spring_layout(G, seed=3)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(BG)
    nx.draw(G, pos, with_labels=True, node_color=SEC, edge_color=PRI, font_color=TEXT, ax=ax)
    ax.set_title("Network Diagram", color=TEXT)
    ax.set_facecolor(BG)
    return _b64(fig)

def gen_mind_map(central_topic, branches):
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    ax.add_patch(plt.Circle((0.5, 0.5), 0.08, edgecolor=PRI, facecolor="none"))
    ax.text(0.5, 0.5, central_topic, color=TEXT, ha="center", va="center")
    angles = np.linspace(0, 2*np.pi, max(1, len(branches)), endpoint=False)
    r = 0.3
    i = 0
    for k, vs in branches.items():
        x = 0.5 + r*np.cos(angles[i])
        y = 0.5 + r*np.sin(angles[i])
        ax.add_patch(plt.Circle((x, y), 0.06, edgecolor=SEC, facecolor="none"))
        ax.text(x, y, k, color=TEXT, ha="center", va="center", fontsize=10)
        if vs:
            for j, v in enumerate(vs[:4]):
                x2 = x + 0.15*np.cos(angles[i] + 0.3*(j+1))
                y2 = y + 0.15*np.sin(angles[i] + 0.3*(j+1))
                ax.plot([x, x2], [y, y2], color=PRI)
                ax.text(x2, y2, v, color=TEXT, fontsize=9)
        i += 1
    ax.set_title("Mind Map", color=TEXT)
    return _b64(fig)
