"""Gan ung vien <-> track toi uu (thuat toan Hungarian), thuan Python (repo khong co scipy).

`assign(cost, gate)` -> [(hang, cot)] co tong chi phi nho nhat, bo cap co chi phi > gate. Kiem bang vet can
(brute force) trong tests/unit/test_perception_tracking.py.
"""
from __future__ import annotations

from collections.abc import Sequence

_INF = float("inf")
_BIG = 1e9


def _hungarian(cost: list[list[float]]) -> list[int]:  # noqa: C901, PLR0912 - thuat toan Kuhn-Munkres kinh dien
    """cost n x m (n <= m) -> cot duoc gan cho moi hang."""
    n, m = len(cost), len(cost[0])
    u, v = [0.0] * (n + 1), [0.0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [_INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], _INF, 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    ans = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            ans[p[j] - 1] = j - 1
    return ans


def assign(cost: Sequence[Sequence[float]], gate: float) -> list[tuple[int, int]]:
    """Cap (hang, cot) toi uu; o co chi phi > gate khong duoc phep gan."""
    if not cost or not cost[0]:
        return []
    n, m = len(cost), len(cost[0])
    c = [[x if x <= gate else _BIG for x in row] for row in cost]
    if n <= m:
        pairs = [(i, j) for i, j in enumerate(_hungarian(c))]
    else:
        t = [[c[i][j] for i in range(n)] for j in range(m)]
        pairs = [(i, j) for j, i in enumerate(_hungarian(t))]
    return [(i, j) for i, j in pairs if j >= 0 and cost[i][j] <= gate]
