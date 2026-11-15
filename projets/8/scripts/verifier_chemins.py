"""Contrôle indépendant : A* en Python entre les lieux, avec raccord au point le plus proche d'une arête.
Même méthode que dans index.html (nœuds virtuels), pour comparer les distances."""
import json, math, heapq
ch = json.load(open('donnees/chemins.json')); lieux = json.load(open('donnees/lieux.json'))
N = [tuple(p) for p in ch['noeuds']]; A = ch['aretes']
def proj(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]; L2 = dx*dx+dy*dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L2))
    q = (a[0]+t*dx, a[1]+t*dy); return q, t, math.dist(p, q)
def route(p, q):
    nodes = list(N); adj = {i: [] for i in range(len(nodes))}
    for a, b, d, nat, src, v in A: adj[a].append((b, d, v)); adj[b].append((a, d, v))
    def virt(pt):
        best = min(((proj(pt, N[a], N[b]), i) for i, (a, b, *_) in enumerate(A)), key=lambda z: z[0][2])
        (qpt, t, dist), i = best; a, b, d, nat, src, v = A[i]
        nodes.append(qpt); k = len(nodes)-1; adj[k] = []
        adj[k].append((a, d*t, v)); adj[a].append((k, d*t, v)); adj[k].append((b, d*(1-t), v)); adj[b].append((k, d*(1-t), v))
        return k, dist
    s, ds = virt(p); t, dt = virt(q)
    pq = [(0, s)]; g = {s: 0}; prev = {}; tout_voiture = {s: True}
    while pq:
        f, u = heapq.heappop(pq)
        if u == t: break
        for w, d, v in adj[u]:
            ng = g[u]+d
            if ng < g.get(w, 1e18): g[w] = ng; prev[w] = (u, v); heapq.heappush(pq, (ng+math.dist(nodes[w], nodes[t]), w))
    chemin = [t]; voiture = True
    while chemin[-1] != s: u, v = prev[chemin[-1]]; voiture &= bool(v); chemin.append(u)
    return g[t], ds, dt, voiture
ordre = ['Mobil-home exemple', 'Piscine', 'Accueil', 'Plage des Dunes']
tot = 0
for a, b in zip(ordre[:-1], ordre[1:]):
    d, ds, dt, v = route(lieux[a], lieux[b]); tot += d + ds + dt
    print(f"{a} -> {b}: ligne droite {math.dist(lieux[a], lieux[b]):.0f} m ; réseau {d:.0f} m + raccords {ds:.0f} m et {dt:.0f} m ; voiture: {'oui' if v else 'non'}")
print('total %.0f m, %.1f min à 1,3 m/s' % (tot, tot/1.3/60))
