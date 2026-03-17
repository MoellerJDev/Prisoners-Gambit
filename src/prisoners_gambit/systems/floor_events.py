from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Literal

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.dynasty import DynastyState
from prisoners_gambit.core.interaction import FloorEventChoiceState, FloorEventResponseView, FloorEventState
from prisoners_gambit.core.powerups import ROUND_EVENT_RETALIATION_TRIGGERED, RoundContext

DoctrineFamily = Literal["trust", "control", "retaliation", "opportunist", "referendum", "chaos"]

_CLUE_LEVELS = ("murky", "shaky", "clear")
_CLUE_LABELS = {
    "murky": "Murky reads",
    "shaky": "Shaky reads",
    "clear": "Clear reads",
}


@dataclass(frozen=True, slots=True)
class MatchModifier:
    cooperate_bonus: int = 0
    defect_bonus: int = 0
    mutual_coop_bonus: int = 0
    betrayal_bonus: int = 0
    retaliation_bonus: int = 0


@dataclass(frozen=True, slots=True)
class ReferendumModifier:
    vote_cooperate_bonus: int = 0
    vote_defect_bonus: int = 0
    cooperation_win_bonus: int = 0
    sabotage_win_bonus: int = 0


@dataclass(frozen=True, slots=True)
class DynastyModifier:
    legitimacy_delta: int = 0
    cohesion_delta: int = 0
    leverage_delta: int = 0
    contingencies_delta: int = 0


@dataclass(frozen=True, slots=True)
class FloorEventResponse:
    key: str
    name: str
    summary: str
    duel_angle: str
    vote_angle: str
    dynasty_impact: str
    offer_drift: str
    risk: str
    cost: str | None = None
    match_modifier: MatchModifier = MatchModifier()
    referendum_modifier: ReferendumModifier = ReferendumModifier()
    dynasty_modifier: DynastyModifier = DynastyModifier()
    favored_doctrine_bias: tuple[DoctrineFamily, ...] = ()
    threat_tags: tuple[str, ...] = ()
    clue_shift: int = 0


@dataclass(frozen=True, slots=True)
class FloorEventTemplate:
    key: str
    title: str
    summary: str
    pressure: str
    rule_text: str
    clue_reliability: Literal["murky", "shaky", "clear"]
    favored_doctrines: tuple[DoctrineFamily, ...]
    threat_tags: tuple[str, ...]
    global_match_modifier: MatchModifier = MatchModifier()
    global_referendum_modifier: ReferendumModifier = ReferendumModifier()
    responses: tuple[FloorEventResponse, ...] = ()


@dataclass(frozen=True, slots=True)
class ActiveFloorEvent:
    floor_number: int
    phase: Literal["ecosystem", "civil_war"]
    template: FloorEventTemplate
    response: FloorEventResponse | None = None

    @property
    def favored_doctrines(self) -> tuple[DoctrineFamily, ...]:
        values = list(self.template.favored_doctrines)
        if self.response is not None:
            for family in self.response.favored_doctrine_bias:
                if family not in values:
                    values.append(family)
        return tuple(values)

    @property
    def threat_tags(self) -> tuple[str, ...]:
        values = list(self.template.threat_tags)
        if self.response is not None:
            for tag in self.response.threat_tags:
                if tag not in values:
                    values.append(tag)
        return tuple(values)

    @property
    def clue_reliability(self) -> Literal["murky", "shaky", "clear"]:
        current_index = _CLUE_LEVELS.index(self.template.clue_reliability)
        if self.response is not None:
            current_index = max(0, min(len(_CLUE_LEVELS) - 1, current_index + self.response.clue_shift))
        return _CLUE_LEVELS[current_index]  # type: ignore[return-value]


def _response(
    key: str,
    *,
    name: str,
    summary: str,
    duel_angle: str,
    vote_angle: str,
    dynasty_impact: str,
    offer_drift: str,
    risk: str,
    cost: str | None = None,
    match_modifier: MatchModifier = MatchModifier(),
    referendum_modifier: ReferendumModifier = ReferendumModifier(),
    dynasty_modifier: DynastyModifier = DynastyModifier(),
    favored_doctrine_bias: tuple[DoctrineFamily, ...] = (),
    threat_tags: tuple[str, ...] = (),
    clue_shift: int = 0,
) -> FloorEventResponse:
    return FloorEventResponse(
        key=key,
        name=name,
        summary=summary,
        duel_angle=duel_angle,
        vote_angle=vote_angle,
        dynasty_impact=dynasty_impact,
        offer_drift=offer_drift,
        risk=risk,
        cost=cost,
        match_modifier=match_modifier,
        referendum_modifier=referendum_modifier,
        dynasty_modifier=dynasty_modifier,
        favored_doctrine_bias=favored_doctrine_bias,
        threat_tags=threat_tags,
        clue_shift=clue_shift,
    )


FLOOR_EVENTS: tuple[FloorEventTemplate, ...] = (
    FloorEventTemplate(
        key="public_unrest",
        title="Public Unrest",
        summary="Crowds are testing whether this floor will be steadied, exploited, or broken.",
        pressure="Order is fragile.",
        rule_text="Stable answers pay off differently than hard squeezes on this floor.",
        clue_reliability="shaky",
        favored_doctrines=("trust", "control", "opportunist"),
        threat_tags=("legitimacy", "control", "opportunist"),
        global_match_modifier=MatchModifier(mutual_coop_bonus=1, betrayal_bonus=1),
        global_referendum_modifier=ReferendumModifier(cooperation_win_bonus=1),
        responses=(
            _response(
                "relief",
                name="Fund Relief",
                summary="Calm the street and turn patience into legitimacy.",
                duel_angle="Your cooperation lines gain extra value.",
                vote_angle="Backing cooperation pays more if the bloc holds.",
                dynasty_impact="Legitimacy rises, leverage is spent.",
                offer_drift="Offers lean toward trust and referendum tools.",
                risk="If rivals race tempo, you may look soft.",
                cost="Spend hard-won leverage.",
                match_modifier=MatchModifier(cooperate_bonus=1, mutual_coop_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1, leverage_delta=-1),
                favored_doctrine_bias=("trust", "referendum"),
                clue_shift=1,
            ),
            _response(
                "crackdown",
                name="Crack Down",
                summary="Restore order through force and visible punishment.",
                duel_angle="Your defect and retaliation lines hit harder.",
                vote_angle="Defection lines gain immediate floor leverage.",
                dynasty_impact="Leverage rises, legitimacy frays.",
                offer_drift="Offers lean toward control and retaliation.",
                risk="The house can start looking like a usurper.",
                match_modifier=MatchModifier(defect_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1, sabotage_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("control", "retaliation"),
                threat_tags=("punishment",),
                clue_shift=-1,
            ),
            _response(
                "black_market",
                name="Work the Black Market",
                summary="Turn the chaos into private channels and dirty leverage.",
                duel_angle="Betrayal spikes hard, but only if you find clean openings.",
                vote_angle="Defection gains value even if the floor goes unstable.",
                dynasty_impact="Leverage rises, cohesion slips.",
                offer_drift="Offers lean toward opportunist and chaos plays.",
                risk="The house starts reading as self-dealing.",
                match_modifier=MatchModifier(betrayal_bonus=2),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=2),
                favored_doctrine_bias=("opportunist", "chaos"),
                threat_tags=("deception",),
                clue_shift=-1,
            ),
        ),
    ),
    FloorEventTemplate(
        key="intelligence_leak",
        title="Intelligence Leak",
        summary="Someone opened the archive. The floor is now fighting over what everyone knows.",
        pressure="Information is live.",
        rule_text="Reads are clearer when exposed, but manipulation pays when players can distort the leak.",
        clue_reliability="clear",
        favored_doctrines=("control", "trust", "chaos"),
        threat_tags=("deception", "control"),
        global_match_modifier=MatchModifier(retaliation_bonus=1),
        responses=(
            _response(
                "publish",
                name="Publish the Leak",
                summary="Expose the board and force rivals to play in the light.",
                duel_angle="Cooperate and retaliation lines become easier to read.",
                vote_angle="Clean cooperation wins more cleanly.",
                dynasty_impact="Legitimacy rises as your house looks transparent.",
                offer_drift="Offers lean toward trust and control answers.",
                risk="You lose some surprise leverage.",
                match_modifier=MatchModifier(cooperate_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1, leverage_delta=-1),
                favored_doctrine_bias=("trust", "control"),
                clue_shift=1,
            ),
            _response(
                "bury",
                name="Bury the Leak",
                summary="Clamp down on the story and keep the board guessing.",
                duel_angle="Defect lines become harder to punish.",
                vote_angle="Defection becomes easier to sell as necessity.",
                dynasty_impact="Leverage rises, legitimacy slips.",
                offer_drift="Offers lean toward control and opportunist tools.",
                risk="Your own reads become less reliable too.",
                match_modifier=MatchModifier(defect_bonus=1, betrayal_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("control", "opportunist"),
                clue_shift=-1,
            ),
            _response(
                "false_trail",
                name="Plant a False Trail",
                summary="Turn the leak into a decoy and weaponize uncertainty.",
                duel_angle="Betrayal and chaos lines get room to breathe.",
                vote_angle="Referendum reads get muddy either way.",
                dynasty_impact="Short-term leverage, long-term cohesion damage.",
                offer_drift="Offers lean toward chaos and opportunist hybrids.",
                risk="You can fool your own house along with your enemies.",
                match_modifier=MatchModifier(betrayal_bonus=1, defect_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("chaos", "opportunist"),
                threat_tags=("ambiguity",),
                clue_shift=-2,
            ),
        ),
    ),
    FloorEventTemplate(
        key="succession_rumor",
        title="Succession Rumor",
        summary="Whispers of a rival claimant are moving faster than your official line.",
        pressure="The house is listening sideways.",
        rule_text="This floor sharpens branch identity and makes succession reads matter sooner.",
        clue_reliability="shaky",
        favored_doctrines=("trust", "retaliation", "control"),
        threat_tags=("succession", "legitimacy"),
        responses=(
            _response(
                "affirm_heir",
                name="Affirm the Heir",
                summary="Make legitimacy the story and dare rivals to oppose it.",
                duel_angle="Steady lines become more attractive.",
                vote_angle="Cooperative blocs reinforce your mandate.",
                dynasty_impact="Legitimacy and cohesion rise together.",
                offer_drift="Offers lean toward trust and referendum continuity.",
                risk="You commit publicly to a stable line.",
                match_modifier=MatchModifier(cooperate_bonus=1, mutual_coop_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1, cohesion_delta=1),
                favored_doctrine_bias=("trust", "referendum"),
                threat_tags=("stable-heir",),
                clue_shift=1,
            ),
            _response(
                "purge_claims",
                name="Purge Claimants",
                summary="Shut down rival branches before they can organize.",
                duel_angle="Retaliation and punishment lines pay immediately.",
                vote_angle="Defection buys room, but burns goodwill.",
                dynasty_impact="Cohesion drops while leverage rises.",
                offer_drift="Offers lean toward retaliation and control.",
                risk="Civil war gets sharper if the purge fails.",
                match_modifier=MatchModifier(defect_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, cohesion_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("retaliation", "control"),
                threat_tags=("civil-war", "punishment"),
            ),
            _response(
                "court_branches",
                name="Court the Branches",
                summary="Buy time by bargaining with rival cousins and fence-sitters.",
                duel_angle="Mixed lines stay flexible and reads improve.",
                vote_angle="Either vote can be defended if you keep options open.",
                dynasty_impact="Leverage falls, but cohesion stabilizes.",
                offer_drift="Offers lean toward trust-control hybrids.",
                risk="You may end the floor with less raw tempo.",
                cost="Spend leverage to keep the family intact.",
                dynasty_modifier=DynastyModifier(cohesion_delta=1, leverage_delta=-2, contingencies_delta=1),
                favored_doctrine_bias=("trust", "control"),
                threat_tags=("coalition",),
                clue_shift=1,
            ),
        ),
    ),
    FloorEventTemplate(
        key="trade_summit",
        title="Trade Summit",
        summary="Foreign houses want a clean deal, but everyone at the table can smell side payments.",
        pressure="Reputation is priced in.",
        rule_text="Cooperation earns durable value here, but betrayal has a bigger headline when it lands.",
        clue_reliability="clear",
        favored_doctrines=("trust", "opportunist", "referendum"),
        threat_tags=("coalition", "tempo"),
        global_match_modifier=MatchModifier(mutual_coop_bonus=1, betrayal_bonus=1),
        global_referendum_modifier=ReferendumModifier(cooperation_win_bonus=1),
        responses=(
            _response(
                "honor_accords",
                name="Honor the Accords",
                summary="Play straight and convert trust into a durable mandate.",
                duel_angle="Mutual cooperation becomes your safest cashout.",
                vote_angle="Backing cooperation compounds the summit bonus.",
                dynasty_impact="Legitimacy rises faster than leverage.",
                offer_drift="Offers lean toward trust and referendum lines.",
                risk="You give up some surprise kill pressure.",
                match_modifier=MatchModifier(mutual_coop_bonus=1, cooperate_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1),
                favored_doctrine_bias=("trust", "referendum"),
            ),
            _response(
                "play_both_sides",
                name="Play Both Sides",
                summary="Smile publicly, then pick the one betrayal that matters.",
                duel_angle="Betrayal spikes if you find a clean trust pocket.",
                vote_angle="You keep room to pivot the referendum late.",
                dynasty_impact="Leverage rises, legitimacy softens.",
                offer_drift="Offers lean toward opportunist-control hybrids.",
                risk="A miss leaves you looking cynical and weak.",
                match_modifier=MatchModifier(betrayal_bonus=2),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("opportunist", "control"),
            ),
            _response(
                "strong_arm",
                name="Strong-Arm Concessions",
                summary="Use the summit as cover for open coercion.",
                duel_angle="Control and defect lines become more direct.",
                vote_angle="Defection becomes a threat-backed bargaining chip.",
                dynasty_impact="Leverage up, cohesion down.",
                offer_drift="Offers lean toward control and retaliation.",
                risk="You turn every later accord into a harder sell.",
                match_modifier=MatchModifier(defect_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1, sabotage_win_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("control", "retaliation"),
                threat_tags=("coercion",),
                clue_shift=-1,
            ),
        ),
    ),
    FloorEventTemplate(
        key="border_raid",
        title="Border Raid",
        summary="A rival strike has everyone asking whether the house can punish fast enough.",
        pressure="Security is on the ballot.",
        rule_text="Punishment and retaliation lines are easier to justify, but pure stability loses tempo.",
        clue_reliability="shaky",
        favored_doctrines=("retaliation", "control", "trust"),
        threat_tags=("punishment", "tempo"),
        global_match_modifier=MatchModifier(retaliation_bonus=1, defect_bonus=1),
        responses=(
            _response(
                "rally_house",
                name="Rally the House",
                summary="Unify around discipline and controlled retaliation.",
                duel_angle="Retaliation lines get paid without fully collapsing into chaos.",
                vote_angle="Either vote works if it looks coordinated.",
                dynasty_impact="Cohesion rises, leverage holds.",
                offer_drift="Offers lean toward retaliation and trust anchors.",
                risk="You may still be slower than raw killers.",
                match_modifier=MatchModifier(retaliation_bonus=2),
                dynasty_modifier=DynastyModifier(cohesion_delta=1),
                favored_doctrine_bias=("retaliation", "trust"),
            ),
            _response(
                "hire_mercenaries",
                name="Hire Mercenaries",
                summary="Buy sharp force and let tempo solve the problem.",
                duel_angle="Defection and betrayal become more explosive.",
                vote_angle="Defection lines get extra short-term punch.",
                dynasty_impact="Leverage drops, but immediate floor tempo spikes.",
                offer_drift="Offers lean toward opportunist and control power.",
                risk="Outside force weakens house cohesion.",
                cost="Spend leverage for tempo.",
                match_modifier=MatchModifier(defect_bonus=1, betrayal_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=-1),
                favored_doctrine_bias=("opportunist", "control"),
            ),
            _response(
                "fortify",
                name="Fortify the Frontier",
                summary="Choose endurance over spectacle and dare the floor to outlast you.",
                duel_angle="Cooperation and mutual stability pay off more cleanly.",
                vote_angle="Cooperative mandates feel safer.",
                dynasty_impact="Legitimacy rises, leverage slows.",
                offer_drift="Offers lean toward trust and survival edits.",
                risk="You can get outraced by branches willing to swing harder.",
                match_modifier=MatchModifier(cooperate_bonus=1, mutual_coop_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1),
                favored_doctrine_bias=("trust",),
                clue_shift=1,
            ),
        ),
    ),
    FloorEventTemplate(
        key="sacred_festival",
        title="Sacred Festival",
        summary="The floor is watching for sincerity, spectacle, and signs of hidden blasphemy.",
        pressure="Symbolic play matters.",
        rule_text="Trust lines gain soft power here, but cynical exploitation can still steal the room.",
        clue_reliability="clear",
        favored_doctrines=("trust", "referendum", "chaos"),
        threat_tags=("legitimacy", "mask"),
        global_match_modifier=MatchModifier(cooperate_bonus=1),
        global_referendum_modifier=ReferendumModifier(cooperation_win_bonus=1),
        responses=(
            _response(
                "public_vow",
                name="Make a Public Vow",
                summary="Bind yourself to visible restraint and force rivals to answer it.",
                duel_angle="Cooperation becomes easier to convert into score and reads.",
                vote_angle="Cooperation blocs gain extra legitimacy.",
                dynasty_impact="Legitimacy rises sharply.",
                offer_drift="Offers lean toward trust and referendum doctrine.",
                risk="Breaking the vow later will sting harder.",
                match_modifier=MatchModifier(cooperate_bonus=1, mutual_coop_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=2),
                favored_doctrine_bias=("trust", "referendum"),
                clue_shift=1,
            ),
            _response(
                "secret_rites",
                name="Conduct Secret Rites",
                summary="Keep a second script behind the public liturgy.",
                duel_angle="Betrayal and deception lines gain cover.",
                vote_angle="You keep room to pivot late without looking naked.",
                dynasty_impact="Leverage rises while cohesion frays.",
                offer_drift="Offers lean toward opportunist and chaos lines.",
                risk="The house starts reading divided even when it wins.",
                match_modifier=MatchModifier(betrayal_bonus=1, defect_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("opportunist", "chaos"),
                clue_shift=-1,
            ),
            _response(
                "stage_spectacle",
                name="Stage a Spectacle",
                summary="Overwhelm the room with symbolism and make reality harder to read.",
                duel_angle="Mixed lines stay flexible, but clarity drops.",
                vote_angle="Either referendum lane can be sold if momentum is strong.",
                dynasty_impact="Cohesion stabilizes, leverage ticks up.",
                offer_drift="Offers lean toward referendum-chaos hybrids.",
                risk="Future reads become noisier for everyone, including you.",
                dynasty_modifier=DynastyModifier(cohesion_delta=1, leverage_delta=1),
                favored_doctrine_bias=("referendum", "chaos"),
                clue_shift=-2,
            ),
        ),
    ),
    FloorEventTemplate(
        key="embargo_shock",
        title="Embargo Shock",
        summary="Supply routes locked up overnight. Every promise now has to survive scarcity.",
        pressure="Leverage is being rationed.",
        rule_text="This floor rewards houses that can either share pain cleanly or weaponize shortages faster than rivals can answer.",
        clue_reliability="shaky",
        favored_doctrines=("referendum", "opportunist", "control"),
        threat_tags=("supply", "leverage", "tempo"),
        global_match_modifier=MatchModifier(mutual_coop_bonus=1, defect_bonus=1),
        responses=(
            _response(
                "ration_share",
                name="Ration and Share",
                summary="Take the political hit early and turn discipline into credibility.",
                duel_angle="Stable cooperation lines stay efficient under pressure.",
                vote_angle="Backing cooperation reads like stewardship rather than weakness.",
                dynasty_impact="Legitimacy and cohesion rise, but leverage is spent.",
                offer_drift="Offers lean toward trust, referendum, and endurance tools.",
                risk="You can fall behind if sharper houses cash the shortage out faster.",
                cost="Spend leverage to calm the table.",
                match_modifier=MatchModifier(cooperate_bonus=1, mutual_coop_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1, cohesion_delta=1, leverage_delta=-1),
                favored_doctrine_bias=("trust", "referendum"),
                clue_shift=1,
            ),
            _response(
                "smuggle",
                name="Smuggle Through",
                summary="Build private channels and let scarcity turn into private leverage.",
                duel_angle="Betrayal and sharp defect lines hit harder if you find a clean mark.",
                vote_angle="Defection gains value because the floor already assumes hoarding.",
                dynasty_impact="Leverage spikes, but legitimacy softens.",
                offer_drift="Offers lean toward opportunist and chaos pivots.",
                risk="If the smuggling ring is obvious, the whole house starts to look crooked.",
                match_modifier=MatchModifier(defect_bonus=1, betrayal_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1, sabotage_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, leverage_delta=2),
                favored_doctrine_bias=("opportunist", "chaos"),
                threat_tags=("deception",),
                clue_shift=-1,
            ),
            _response(
                "seize_stores",
                name="Seize the Stores",
                summary="Make the shortage everyone else's problem and govern through coercion.",
                duel_angle="Control and retaliation lines become easier to justify openly.",
                vote_angle="Defection becomes a threat-backed mandate rather than a gamble.",
                dynasty_impact="Leverage rises, cohesion frays.",
                offer_drift="Offers lean toward control and retaliation.",
                risk="A hard seizure makes every future promise more expensive.",
                match_modifier=MatchModifier(defect_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(cohesion_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("control", "retaliation"),
                threat_tags=("coercion",),
            ),
        ),
    ),
    FloorEventTemplate(
        key="oath_tribunal",
        title="Oath Tribunal",
        summary="Old betrayals are back on the record, and the floor is judging whether your line can justify its own history.",
        pressure="Memory is prosecuting the present.",
        rule_text="Predictable lines become easier to punish here unless you can reconcile them, redirect the blame, or bury the record in noise.",
        clue_reliability="clear",
        favored_doctrines=("trust", "retaliation", "control"),
        threat_tags=("legitimacy", "memory", "punishment"),
        global_match_modifier=MatchModifier(retaliation_bonus=1, mutual_coop_bonus=1),
        global_referendum_modifier=ReferendumModifier(cooperation_win_bonus=1),
        responses=(
            _response(
                "confess",
                name="Confess and Reconcile",
                summary="Admit enough to look principled and turn transparency into a shield.",
                duel_angle="Cooperation and honest retaliation reads more clearly.",
                vote_angle="Backing cooperation reinforces that the house is answering its own past.",
                dynasty_impact="Legitimacy and cohesion improve together.",
                offer_drift="Offers lean toward trust and referendum continuity.",
                risk="If you break the reconciled line, the tribunal remembers.",
                match_modifier=MatchModifier(cooperate_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_cooperate_bonus=1, cooperation_win_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=1, cohesion_delta=1),
                favored_doctrine_bias=("trust", "referendum"),
                clue_shift=1,
            ),
            _response(
                "cross_examine",
                name="Cross-Examine Rivals",
                summary="Turn judgment outward and make every other branch defend its own record first.",
                duel_angle="Retaliation and opportunistic defections punish soft targets more cleanly.",
                vote_angle="Defection becomes easier to justify as necessary exposure.",
                dynasty_impact="Leverage rises, legitimacy stays contested.",
                offer_drift="Offers lean toward control-retaliation hybrids.",
                risk="If the attack looks theatrical, the tribunal only gets hungrier.",
                match_modifier=MatchModifier(defect_bonus=1, retaliation_bonus=1),
                referendum_modifier=ReferendumModifier(vote_defect_bonus=1),
                dynasty_modifier=DynastyModifier(leverage_delta=1),
                favored_doctrine_bias=("control", "retaliation"),
                threat_tags=("counterattack",),
            ),
            _response(
                "stonewall",
                name="Stonewall the Tribunal",
                summary="Drown the record in noise and dare the room to prove anything cleanly.",
                duel_angle="Deception and flexible lines get more room, but read quality collapses.",
                vote_angle="Either vote can be sold if you can muddy motive fast enough.",
                dynasty_impact="Leverage rises, legitimacy bleeds.",
                offer_drift="Offers lean toward chaos and opportunist lines.",
                risk="Your own heirs inherit the same poisoned record later.",
                match_modifier=MatchModifier(betrayal_bonus=1, defect_bonus=1),
                dynasty_modifier=DynastyModifier(legitimacy_delta=-1, leverage_delta=1),
                favored_doctrine_bias=("chaos", "opportunist"),
                threat_tags=("ambiguity", "memory"),
                clue_shift=-2,
            ),
        ),
    ),
)


def generate_floor_event(
    rng: random.Random,
    *,
    floor_number: int,
    phase: Literal["ecosystem", "civil_war"],
    dynasty_state: DynastyState,
    previous_event_key: str | None = None,
    stable_line_streak: int = 0,
) -> ActiveFloorEvent:
    templates = list(FLOOR_EVENTS)
    weights: list[float] = []
    for template in templates:
        weight = 1.0
        if template.key == previous_event_key:
            weight *= 0.35
        if dynasty_state.legitimacy <= 3 and "legitimacy" in template.threat_tags:
            weight += 1.5
        if dynasty_state.cohesion <= 3 and template.key in {"succession_rumor", "border_raid", "public_unrest"}:
            weight += 1.5
        if dynasty_state.leverage <= 2 and template.key in {"trade_summit", "sacred_festival"}:
            weight += 1.0
        if phase == "civil_war" and template.key in {"succession_rumor", "border_raid", "intelligence_leak"}:
            weight += 1.3
        if floor_number <= 2 and template.key in {"trade_summit", "sacred_festival", "public_unrest"}:
            weight += 0.6
        if stable_line_streak >= 2 and floor_number >= 4 and template.key in {
            "intelligence_leak",
            "border_raid",
            "embargo_shock",
            "oath_tribunal",
        }:
            weight += 1.6 + (stable_line_streak - 2) * 0.45
        weights.append(weight)
    template = rng.choices(templates, weights=weights, k=1)[0]
    return ActiveFloorEvent(floor_number=floor_number, phase=phase, template=template)


def choose_floor_event_response(active_event: ActiveFloorEvent, response_index: int) -> ActiveFloorEvent:
    responses = active_event.template.responses
    if response_index < 0 or response_index >= len(responses):
        raise ValueError("Event response index out of range.")
    return ActiveFloorEvent(
        floor_number=active_event.floor_number,
        phase=active_event.phase,
        template=active_event.template,
        response=responses[response_index],
    )


def to_choice_state(active_event: ActiveFloorEvent) -> FloorEventChoiceState:
    return FloorEventChoiceState(
        floor_number=active_event.floor_number,
        phase=active_event.phase,
        title=active_event.template.title,
        summary=active_event.template.summary,
        pressure=active_event.template.pressure,
        rule_text=active_event.template.rule_text,
        clue_reliability=_CLUE_LABELS[active_event.clue_reliability],
        responses=[
            FloorEventResponseView(
                name=response.name,
                summary=response.summary,
                duel_angle=response.duel_angle,
                vote_angle=response.vote_angle,
                dynasty_impact=response.dynasty_impact,
                offer_drift=response.offer_drift,
                risk=response.risk,
                cost=response.cost,
            )
            for response in active_event.template.responses
        ],
    )


def to_snapshot_state(active_event: ActiveFloorEvent) -> FloorEventState:
    response = active_event.response
    return FloorEventState(
        floor_number=active_event.floor_number,
        title=active_event.template.title,
        summary=active_event.template.summary,
        pressure=active_event.template.pressure,
        rule_text=active_event.template.rule_text,
        clue_reliability=_CLUE_LABELS[active_event.clue_reliability],
        favored_doctrines=list(active_event.favored_doctrines),
        threat_tags=list(active_event.threat_tags),
        response_name=response.name if response is not None else None,
        response_summary=response.summary if response is not None else None,
        response_tradeoff=response.risk if response is not None else None,
    )


def response_dynasty_modifier(active_event: ActiveFloorEvent) -> DynastyModifier:
    return active_event.response.dynasty_modifier if active_event.response is not None else DynastyModifier()


def _dominant_round_move(round_history: list[int]) -> int | None:
    if not round_history:
        return None
    cooperate_count = sum(1 for move in round_history if move == COOPERATE)
    defect_count = len(round_history) - cooperate_count
    if cooperate_count == defect_count:
        return None
    return COOPERATE if cooperate_count > defect_count else DEFECT


def preferred_round_move(active_event: ActiveFloorEvent | None) -> int | None:
    if active_event is None:
        return None
    response = active_event.response
    if response is None:
        return None
    cooperative_weight = response.match_modifier.cooperate_bonus + response.match_modifier.mutual_coop_bonus
    aggressive_weight = (
        response.match_modifier.defect_bonus
        + response.match_modifier.betrayal_bonus
        + response.match_modifier.retaliation_bonus
    )
    if cooperative_weight == aggressive_weight:
        return None
    return COOPERATE if cooperative_weight > aggressive_weight else DEFECT


def preferred_vote(active_event: ActiveFloorEvent | None) -> int | None:
    if active_event is None:
        return None
    response = active_event.response
    if response is None:
        return None
    cooperative_weight = (
        response.referendum_modifier.vote_cooperate_bonus
        + response.referendum_modifier.cooperation_win_bonus
    )
    aggressive_weight = (
        response.referendum_modifier.vote_defect_bonus
        + response.referendum_modifier.sabotage_win_bonus
    )
    if cooperative_weight == aggressive_weight:
        return None
    return COOPERATE if cooperative_weight > aggressive_weight else DEFECT


def response_commitment_modifier(
    active_event: ActiveFloorEvent | None,
    *,
    round_history: list[int],
    final_vote: int,
) -> DynastyModifier:
    if active_event is None or active_event.response is None:
        return DynastyModifier()

    legitimacy_delta = 0
    cohesion_delta = 0

    preferred_round = preferred_round_move(active_event)
    actual_round = _dominant_round_move(round_history)
    if preferred_round is not None and actual_round is not None and actual_round != preferred_round:
        legitimacy_delta -= 1

    preferred_vote_choice = preferred_vote(active_event)
    if preferred_vote_choice is not None and final_vote != preferred_vote_choice:
        legitimacy_delta -= 1

    if legitimacy_delta <= -2:
        cohesion_delta -= 1

    return DynastyModifier(legitimacy_delta=legitimacy_delta, cohesion_delta=cohesion_delta)


def apply_match_event_bonus(
    active_event: ActiveFloorEvent | None,
    *,
    owner_is_player: bool,
    my_move: int,
    opp_move: int,
    context: RoundContext,
    my_points: int,
) -> tuple[int, int]:
    if active_event is None:
        return my_points, 0

    def bonus_for(modifier: MatchModifier) -> int:
        bonus = 0
        if my_move == COOPERATE:
            bonus += modifier.cooperate_bonus
        if my_move == DEFECT:
            bonus += modifier.defect_bonus
        if my_move == COOPERATE and opp_move == COOPERATE:
            bonus += modifier.mutual_coop_bonus
        if my_move == DEFECT and opp_move == COOPERATE:
            bonus += modifier.betrayal_bonus
        if ROUND_EVENT_RETALIATION_TRIGGERED in context.combo_events:
            bonus += modifier.retaliation_bonus
        return bonus

    bonus = bonus_for(active_event.template.global_match_modifier)
    if active_event.response is not None:
        bonus += bonus_for(active_event.response.match_modifier)
    return my_points + bonus, bonus


def apply_referendum_event_bonus(
    active_event: ActiveFloorEvent | None,
    *,
    owner_is_player: bool,
    my_vote: int,
    cooperation_prevailed: bool,
    current_reward: int,
) -> tuple[int, int]:
    if active_event is None:
        return current_reward, 0

    def bonus_for(modifier: ReferendumModifier) -> int:
        bonus = 0
        if my_vote == COOPERATE:
            bonus += modifier.vote_cooperate_bonus
        if my_vote == DEFECT:
            bonus += modifier.vote_defect_bonus
        if cooperation_prevailed:
            bonus += modifier.cooperation_win_bonus
        else:
            bonus += modifier.sabotage_win_bonus
        return bonus

    bonus = bonus_for(active_event.template.global_referendum_modifier)
    if active_event.response is not None:
        bonus += bonus_for(active_event.response.referendum_modifier)
    return current_reward + bonus, bonus


def favored_offer_biases(active_event: ActiveFloorEvent | None) -> tuple[DoctrineFamily, ...]:
    return active_event.favored_doctrines if active_event is not None else ()


def clue_prefix(active_event: ActiveFloorEvent | None) -> str | None:
    if active_event is None:
        return None
    if active_event.clue_reliability == "clear":
        return "Signal is unusually clear this floor."
    if active_event.clue_reliability == "murky":
        return "Signal is distorted this floor; treat reads as noisy."
    return "Signal is uneven this floor; confirm patterns before committing."
