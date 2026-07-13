"""Heatmap pure helpers (neighbor extraction). No network."""

from app.services.heatmap_engine import _neighbor_scores


def test_neighbor_scores_gathers_surrounding_cells():
    scores = {
        (75, 1.0): 80, (75, 2.0): 81, (75, 3.0): 82,
        (80, 1.0): 83, (80, 2.0): 84, (80, 3.0): 85,
        (85, 1.0): 86, (85, 2.0): 87, (85, 3.0): 88,
    }
    got = _neighbor_scores(scores, 80, 2.0)
    assert set(got) == set(scores.values())  # all 9 neighbors found
    assert max(got) - min(got) == 8


def test_neighbor_scores_edge_cell_has_fewer_neighbors():
    scores = {(80, 2.0): 84, (85, 2.0): 87, (80, 3.0): 85, (85, 3.0): 88}
    got = _neighbor_scores(scores, 80, 2.0)
    assert 84 in got
    assert len(got) == 4  # only the in-grid neighbors
