from wyraj.core.rng import RngStreams


def test_same_seed_same_draws() -> None:
    a = RngStreams(42)
    b = RngStreams(42)
    assert [a.combat.random() for _ in range(10)] == [b.combat.random() for _ in range(10)]
    assert [a.worldgen.randint(0, 99) for _ in range(10)] == [
        b.worldgen.randint(0, 99) for _ in range(10)
    ]


def test_streams_are_independent() -> None:
    a = RngStreams(42)
    b = RngStreams(42)
    # Drain one stream in `a` only; the others must be unaffected.
    for _ in range(100):
        a.narration.random()
    assert a.combat.random() == b.combat.random()
    assert a.loot.random() == b.loot.random()


def test_different_seeds_differ() -> None:
    assert RngStreams(1).combat.random() != RngStreams(2).combat.random()
