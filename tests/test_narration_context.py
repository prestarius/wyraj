import itertools
import random

from wyraj.core.components import AI, Health, Position
from wyraj.core.events import AttackResolved, EntityRef, Outcome
from wyraj.core.game import Game
from wyraj.narration.context import ContextEnricher
from wyraj.narration.forms import FormRegistry
from wyraj.narration.templates import GrammarPack, TemplateNarrator, Variant

PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)
BIES = EntityRef(entity=2, key="bies", name="bies")


def enemy_hit(attacker: EntityRef = BIES) -> AttackResolved:
    return AttackResolved(
        attacker=attacker,
        defender=PLAYER,
        weapon=None,
        damage=3,
        outcome=Outcome.HIT,
        defender_hp_frac=0.5,
    )


def test_hp_band_tags() -> None:
    game = Game(seed=42)
    enricher = ContextEnricher(game)
    assert "player_healthy" in enricher.enrich(enemy_hit())
    game.world.add(game.player, Health(10, 20))
    assert "player_bloodied" in enricher.enrich(enemy_hit())
    game.world.add(game.player, Health(4, 20))
    assert "player_dying" in enricher.enrich(enemy_hit())


def test_unseen_attacker_tag() -> None:
    game = Game(seed=42)
    enricher = ContextEnricher(game)
    bies = game.world.entities_with(AI)[0]
    ref = EntityRef(entity=bies, key="bies", name="bies")

    hidden = next((x, y) for x, y in game.map.floor_tiles() if (x, y) not in game.map.visible)
    game.world.add(bies, Position(*hidden))
    assert "unseen_attacker" in enricher.enrich(enemy_hit(ref))

    ppos = game.world.expect(game.player, Position)
    game.world.add(bies, Position(ppos.x + 1, ppos.y))
    game.map.update_fov((ppos.x, ppos.y), 8)
    assert "unseen_attacker" not in enricher.enrich(enemy_hit(ref))


def test_again_tag_within_window() -> None:
    game = Game(seed=42)
    enricher = ContextEnricher(game)
    assert "again" not in enricher.enrich(enemy_hit())
    assert "again" in enricher.enrich(enemy_hit())


def make_narrator(variants: list[Variant], seed: int = 1) -> TemplateNarrator:
    pack = GrammarPack({("attack_resolved", "enemy_hit"): variants})
    return TemplateNarrator(pack, random.Random(seed), FormRegistry())


def test_tagged_variant_wins_in_matching_context() -> None:
    narrator = make_narrator(
        [
            Variant(en="plain hit"),
            Variant(en="dying hit", tags=["player_dying"]),
        ]
    )
    dying = frozenset({"player_dying"})
    for _ in range(5):
        assert narrator.compose(enemy_hit(), dying)[0].text == "dying hit"
    # The dying-tagged variant must not appear without its context.
    narrator2 = make_narrator(
        [Variant(en="plain hit"), Variant(en="dying hit", tags=["player_dying"])]
    )
    for _ in range(5):
        assert narrator2.compose(enemy_hit())[0].text == "plain hit"


def test_no_consecutive_template_repeats() -> None:
    narrator = make_narrator([Variant(en="one"), Variant(en="two"), Variant(en="three")])
    texts = [narrator.compose(enemy_hit())[0].text for _ in range(20)]
    assert all(a != b for a, b in itertools.pairwise(texts))


def test_compose_turn_coalesces_and_marks_repeats() -> None:
    narrator = make_narrator([Variant(en="The bies bites you.")])
    batch: list[tuple] = [(enemy_hit(), frozenset()), (enemy_hit(), frozenset())]
    lines = narrator.compose_turn(batch)  # type: ignore[arg-type]
    assert len(lines) == 1
    assert lines[0].text == "The bies bites you. And again."


def test_compose_turn_empty_batch_is_silent() -> None:
    narrator = make_narrator([Variant(en="x")])
    assert narrator.compose_turn([]) == []
