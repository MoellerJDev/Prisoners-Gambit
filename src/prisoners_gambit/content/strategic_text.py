from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from prisoners_gambit.systems.offers import OfferCategory


@dataclass(frozen=True, slots=True)
class PowerupStrategicProfile:
    hook: str
    plan: str
    cost: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenomeStrategicProfile:
    rewrite: str
    doctrine_shift: str
    tempo_note: str
    stability_note: str


# This module is the main edit surface for backend-generated strategic copy.
# The goal is to keep most user-facing choice text in a few deliberate files so
# wording and future language substitution do not require editing gameplay logic.

DOCTRINE_TITLES: dict[str, str] = {
    "trust": "Consensus House",
    "control": "Control Machine",
    "retaliation": "Retaliation Creed",
    "opportunist": "Shadow Court",
    "referendum": "Bloc Empire",
    "chaos": "Chaos Succession",
}

POWERUP_TAG_LABELS: dict[str, str] = {
    "anchor": "Anchor Piece",
    "amplifier": "Amplifier",
    "bridge": "Bridge Piece",
    "chaos": "Chaos Play",
    "coalition": "Coalition Play",
    "control": "Control Pressure",
    "creates_force": "Forced Line",
    "creates_lock": "Lock Pattern",
    "enabler": "Enabler",
    "final_round_payoff": "Final-Round Burst",
    "opportunist": "Opening Tempo",
    "payoff": "Payoff Piece",
    "referendum_control": "Vote Control",
    "rewards_betrayal": "Betrayal Payoff",
    "rewards_force": "Forced Payoff",
    "rewards_mutual_coop": "Peace Payoff",
    "retaliation_payoff": "Retaliation Payoff",
}

OFFER_FIT_DETAILS: dict[OfferCategory, str] = {
    "familiar_line": "Deepens the doctrine your house already trusts.",
    "hybrid_line": "Adds a second wing and broadens future heir options.",
    "temptation": "Offers a high ceiling, but can pull the house off its best read.",
}

POWERUP_PROFILES: dict[str, PowerupStrategicProfile] = {
    "Opening Gambit": PowerupStrategicProfile(
        hook="Jump the scoreboard before rivals settle.",
        plan="Best in lines that can turn an opening betrayal into lasting tempo.",
        cost="Falls off if the floor stabilizes before you cash the lead.",
        tags=("Opening Tempo", "Betrayal Payoff", "Enabler"),
    ),
    "Trust Dividend": PowerupStrategicProfile(
        hook="Turn peace loops into reliable score drip.",
        plan="Pair with peace locks, forgiving genomes, and coalition-heavy floors.",
        cost="Runs thin when mirrors stay hostile or chaotic.",
        tags=("Peace Payoff", "Coalition Play", "Payoff Piece"),
    ),
    "Last Laugh": PowerupStrategicProfile(
        hook="Save your cleanest theft for the closing bell.",
        plan="Strong when your line can disguise betrayal until the last round.",
        cost="Telegraphs a closing knife and gives up long-cycle trust equity.",
        tags=("Final-Round Burst", "Betrayal Payoff", "Payoff Piece"),
    ),
    "Spite Engine": PowerupStrategicProfile(
        hook="Make every grudge worth points.",
        plan="Thrives in retaliation mirrors and dirty tables that keep score through grudges.",
        cost="Low ceiling if opponents never give you a reason to punish.",
        tags=("Retaliation Payoff", "Betrayal Payoff", "Payoff Piece"),
    ),
    "Mercy Shield": PowerupStrategicProfile(
        hook="Make repeat betrayal expensive for the other side.",
        plan="Use it to survive predatory floors long enough to seize the midgame.",
        cost="Mostly defensive if the table stays cooperative.",
        tags=("Retaliation Payoff", "Control Pressure", "Amplifier"),
    ),
    "Golden Handshake": PowerupStrategicProfile(
        hook="Force the room to open in peace on your terms.",
        plan="Seeds trust engines and lets slow, consensus lines get established.",
        cost="Gives up the surprise edge of an opening knife.",
        tags=("Lock Pattern", "Peace Payoff", "Anchor Piece"),
    ),
    "Coercive Control": PowerupStrategicProfile(
        hook="Turn one clean betrayal into a scripted follow-up.",
        plan="Best when you can bait cooperation once and then leash the next round.",
        cost="Weak if opponents never hand you the first clean opening.",
        tags=("Forced Line", "Forced Payoff", "Anchor Piece"),
    ),
    "Counter-Intel": PowerupStrategicProfile(
        hook="Turn their betrayal into your setup.",
        plan="Counter-picks retaliatory floors by converting their last betrayal into your next scoring lane.",
        cost="Light pressure when the table never defects first.",
        tags=("Forced Line", "Retaliation Payoff", "Bridge Piece"),
    ),
    "Panic Button": PowerupStrategicProfile(
        hook="Lock a bad fight into an even uglier spiral you can score from.",
        plan="Use it when the floor is already cracking and steady lines look doomed.",
        cost="Accelerates instability for everyone, including your own branch.",
        tags=("Lock Pattern", "Chaos Play", "Anchor Piece"),
    ),
    "Compliance Dividend": PowerupStrategicProfile(
        hook="Cash every obedience window for extra value.",
        plan="Scales hardest when your kit can repeatedly force or bait cooperation.",
        cost="Does very little without betrayal-conversion windows.",
        tags=("Forced Payoff", "Betrayal Payoff", "Payoff Piece"),
    ),
    "Unity Ticket": PowerupStrategicProfile(
        hook="Guarantee that your vote joins the cooperation bloc.",
        plan="Stabilizes referendum floors and protects consensus doctrine runs.",
        cost="You give up defection flexibility when the bloc is a trap.",
        tags=("Vote Control", "Peace Payoff", "Enabler"),
    ),
    "Saboteur Bloc": PowerupStrategicProfile(
        hook="Guarantee that your vote defects against the bloc.",
        plan="Crack peaceful floors when denial value matters more than public trust.",
        cost="Hardens outsider suspicion and can starve your own coalition future.",
        tags=("Vote Control", "Betrayal Payoff", "Enabler"),
    ),
    "Bloc Politics": PowerupStrategicProfile(
        hook="Make majority-building pay better than mere survival.",
        plan="Strong in runs already leaning into coalition management and vote shaping.",
        cost="Quiet on floors decided by duel tempo instead of bloc math.",
        tags=("Peace Payoff", "Vote Control", "Amplifier"),
    ),
    "Concordat Protocol": PowerupStrategicProfile(
        hook="Make peace self-reinforcing once it starts.",
        plan="A crown move for consensus houses that want to snowball calm into control.",
        cost="Fragile once betrayal breaks the trust chain.",
        tags=("Lock Pattern", "Peace Payoff", "Anchor Piece"),
    ),
    "Iron Decree": PowerupStrategicProfile(
        hook="Script periodic compliance turns into your scoring plan.",
        plan="Ideal for control houses that want guaranteed conversion windows every cycle.",
        cost="Predictable cadence lets sharp rivals plan around the decree.",
        tags=("Forced Line", "Forced Payoff", "Anchor Piece"),
    ),
    "Vendetta Statute": PowerupStrategicProfile(
        hook="Write revenge directly into the family code.",
        plan="Turns retaliation lines from deterrence into a real win condition.",
        cost="Can trap you in feud tempo when a reset would be better.",
        tags=("Retaliation Payoff", "Lock Pattern", "Payoff Piece"),
    ),
    "Shadow Succession": PowerupStrategicProfile(
        hook="Build a house around timed betrayal windows.",
        plan="A crown move for knife-first runs that want both opener and closer pressure.",
        cost="Trust evaporates quickly once the line becomes obvious.",
        tags=("Opening Tempo", "Betrayal Payoff", "Anchor Piece"),
    ),
    "Mandate Forge": PowerupStrategicProfile(
        hook="Own referendum tempo instead of merely reacting to it.",
        plan="Lets vote-control houses plan around floor parity and forced bloc swings.",
        cost="Predictable cadence can strand you on the wrong parity floor.",
        tags=("Vote Control", "Amplifier", "Anchor Piece"),
    ),
    "Schism Ritual": PowerupStrategicProfile(
        hook="Weaponize unpredictability into raw tempo swings.",
        plan="Use it when you want the whole table playing around your unstable rhythm.",
        cost="Turns your own line into a volatile read that is hard to protect.",
        tags=("Chaos Play", "Amplifier", "Anchor Piece"),
    ),
}

GENOME_PROFILES: dict[str, GenomeStrategicProfile] = {
    "Open With Trust": GenomeStrategicProfile(
        rewrite="Open matches with cooperation.",
        doctrine_shift="Lean harder into trust-first play.",
        tempo_note="Tempo: slower opener, better alliance ceiling.",
        stability_note="Cost: vulnerable if the floor rewards first-hit knives.",
    ),
    "Open With Knife": GenomeStrategicProfile(
        rewrite="Open matches with defection.",
        doctrine_shift="Pivot toward tempo-first pressure.",
        tempo_note="Tempo: faster starts and more forced reactions.",
        stability_note="Cost: trust loops get harder to build later.",
    ),
    "Punish Betrayal": GenomeStrategicProfile(
        rewrite="After C into D, answer with D.",
        doctrine_shift="Codify retaliation into the branch.",
        tempo_note="Tempo: earlier punish window against exploiters.",
        stability_note="Cost: grudges can crowd out reconciliation lines.",
    ),
    "Preserve Peace": GenomeStrategicProfile(
        rewrite="After C/C, stay on cooperation.",
        doctrine_shift="Deepen a peace-holding doctrine.",
        tempo_note="Tempo: steadier scoring in long trust loops.",
        stability_note="Cost: gives up some burst when rivals pivot sharp.",
    ),
    "Press Advantage": GenomeStrategicProfile(
        rewrite="After D into C, stay on defection.",
        doctrine_shift="Teach the line to press winning tempo.",
        tempo_note="Tempo: converts clean openings into repeat pressure.",
        stability_note="Cost: makes it harder to step off the knife.",
    ),
    "Calm the Noise": GenomeStrategicProfile(
        rewrite="Lower autopilot noise.",
        doctrine_shift="Move toward a predictable line.",
        tempo_note="Tempo: fewer throw turns and cleaner planning.",
        stability_note="Cost: less upset potential against stronger branches.",
    ),
    "Embrace Chaos": GenomeStrategicProfile(
        rewrite="Raise autopilot noise.",
        doctrine_shift="Drift toward chaotic succession.",
        tempo_note="Tempo: more swing turns and surprise breaks.",
        stability_note="Cost: self-inflicted collapse becomes more likely.",
    ),
    "Fortress Doctrine": GenomeStrategicProfile(
        rewrite="Open C, hold peace, forgive D/D, and reduce noise.",
        doctrine_shift="Commit the house to durable defense.",
        tempo_note="Tempo: slower races, stronger floor control.",
        stability_note="Cost: explosive cousins can outrun you in short duels.",
    ),
    "Tyrant Doctrine": GenomeStrategicProfile(
        rewrite="Open D and keep pressing after advantage or betrayal.",
        doctrine_shift="Hard pivot into coercive rule.",
        tempo_note="Tempo: relentless pressure once you have initiative.",
        stability_note="Cost: attracts backlash and can overheat ecosystem floors.",
    ),
    "Wildcard Doctrine": GenomeStrategicProfile(
        rewrite="Flip core responses and spike noise.",
        doctrine_shift="Break into an unstable, high-variance branch.",
        tempo_note="Tempo: harder to read, harder to mirror cleanly.",
        stability_note="Cost: reliability collapses if chaos does not pay immediately.",
    ),
}


def doctrine_family_title(family: str | None) -> str:
    if not family:
        return "Unformed House"
    return DOCTRINE_TITLES.get(family, family.replace("_", " ").title())


def doctrine_commitment_summary(*, house: str | None, primary: str | None, secondary: str | None) -> tuple[str, str]:
    primary_title = doctrine_family_title(primary)
    if not primary:
        return ("Doctrine: unformed", "The house has not settled on a doctrine yet.")
    if house is None or house == primary:
        if secondary:
            return (
                f"Doctrine: {primary_title} + {doctrine_family_title(secondary)} wing",
                "Deepens the house doctrine while opening a second wing.",
            )
        return (
            f"Doctrine: {primary_title}",
            "Deepens the inherited house doctrine.",
        )
    if secondary:
        return (
            f"Doctrine: {primary_title} over {doctrine_family_title(house)}",
            "Mutates the house doctrine into a hybrid and raises succession friction.",
        )
    return (
        f"Doctrine: {primary_title} over {doctrine_family_title(house)}",
        "Pulls the line away from its inherited doctrine toward a sharper identity.",
    )


def doctrine_commitment_line(*, house: str | None, primary: str | None, secondary: str | None, branch_identity: str) -> str:
    title, detail = doctrine_commitment_summary(house=house, primary=primary, secondary=secondary)
    doctrine_name = title.removeprefix("Doctrine: ").strip()
    return f"{detail} Pulls toward {branch_identity.lower()} through {doctrine_name.lower()}."


def offer_fit_detail(category: OfferCategory) -> str:
    return OFFER_FIT_DETAILS.get(category, OFFER_FIT_DETAILS["temptation"])


def curated_powerup_tags(*, keywords: Sequence[str], crown_piece: bool) -> list[str]:
    labels = [POWERUP_TAG_LABELS.get(keyword, keyword.replace("_", " ").title()) for keyword in keywords]
    if crown_piece:
        labels.append("Crown Move")
    seen: set[str] = set()
    result: list[str] = []
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        result.append(label)
    return result


def powerup_profile(name: str) -> PowerupStrategicProfile | None:
    return POWERUP_PROFILES.get(name)


def fallback_powerup_profile(*, description: str, fallback_tags: Sequence[str]) -> PowerupStrategicProfile:
    return PowerupStrategicProfile(
        hook=description.rstrip("."),
        plan="Take it when your doctrine and the current threat mix both point the same way.",
        cost="If the floor shifts away from its trigger, the value drops quickly.",
        tags=tuple(fallback_tags) or ("Flexible Piece",),
    )


def genome_profile(name: str) -> GenomeStrategicProfile | None:
    return GENOME_PROFILES.get(name)


def fallback_genome_profile(*, description: str) -> GenomeStrategicProfile:
    return GenomeStrategicProfile(
        rewrite=description.rstrip("."),
        doctrine_shift="Moves the branch without forcing a full doctrine rewrite.",
        tempo_note="Tempo: changes the line's default rhythm.",
        stability_note="Cost: every rewrite closes off some fallback patterns.",
    )


def identity_primary_descriptor(tags: Sequence[str]) -> str:
    tag_set = set(tags)
    if "Cooperative" in tag_set and "Retaliatory" in tag_set:
        return "Reciprocal cooperator"
    if "Aggressive" in tag_set and "Exploitative" in tag_set:
        return "Predatory opener"
    if "Cooperative" in tag_set:
        return "Trust-leaning strategist"
    if "Aggressive" in tag_set:
        return "Pressure-oriented strategist"
    return "Adaptive strategist"


def identity_tool_descriptor(tags: Sequence[str]) -> str | None:
    tag_set = set(tags)
    if "Control" in tag_set:
        return "with move control"
    if "Referendum" in tag_set:
        return "with vote pressure"
    if "Consensus" in tag_set:
        return "with peace incentives"
    if "Punishing" in tag_set:
        return "with punishing counters"
    if "Defensive" in tag_set:
        return "with defensive tools"
    return None


def identity_variance_descriptor(tags: Sequence[str]) -> str | None:
    tag_set = set(tags)
    if "Unstable" in tag_set:
        return "and volatile behavior"
    if "Tempo" in tag_set:
        return "and timing spikes"
    if "Precise" in tag_set:
        return "and a predictable line"
    return None


def successor_headline(kind: str, *, branch_role: str, descriptor: str) -> str:
    return {
        "reciprocal": "Reciprocal heir that protects trust but punishes broken peace.",
        "knife_first": "Knife-first heir that races tempo before rivals organize.",
        "referendum_control": "Bloc operator that can turn public order into coercive leverage.",
        "referendum": "Coalition heir that wins by controlling who gets paid.",
        "discipline": "Disciplinarian heir built to script and punish the table.",
        "unstable": "Volatile heir that can steal tempo or throw it away.",
        "defensive": "Defensive heir that survives pressure and drags rivals long.",
        "civil_war_monster": "Hardline heir that looks built for civil-war mirrors.",
        "safe_heir": "Steady heir that favors control over fireworks.",
        "default": f"{branch_role} with a {descriptor.lower()} profile.",
    }[kind]


def successor_shaping_cause(kind: str) -> str:
    return {
        "cooperative": "Cooperative opener and reciprocity bias",
        "aggressive": "Aggressive opener with duel pressure",
        "referendum": "Referendum-focused perk package",
        "control": "Control effects shaping move outcomes",
        "unstable": "High noise driving swingy turns and variance",
        "default": "Mixed profile from prior edits and inheritance",
    }[kind]


def successor_tradeoff_text(kind: str, side: str) -> str:
    return {
        "safety": f"Safe vs explosive: {side}",
        "phase": f"Ecosystem vs civil war: {side}",
        "stability": f"Stable vs volatile: {side}",
        "control": f"Trust vs coercion: {side}",
        "referendum": f"Referendum vs duel: {side}",
    }[kind]


def successor_strength_text(kind: str) -> str:
    return {
        "coalition": "Can stabilize alliances and referendum pacing",
        "tempo": "Punishes passivity and can swing duels quickly",
        "referendum": "Can convert floor-vote dynamics into value",
        "control": "Applies directive pressure that scales in civil-war mirrors",
        "default": "Balanced profile with flexible adaptation",
    }[kind]


def successor_liability_text(kind: str) -> str:
    return {
        "volatility": "Volatility can throw critical successor turns",
        "retaliation": "Can trigger retaliation spirals in long rounds",
        "referendum": "May underperform in referendum-heavy floors",
        "exploitation": "May get farmed by exploiters before adapting",
        "default": "No obvious hard weakness, but the ceiling may be lower",
    }[kind]


def doctrine_relation_text(kind: str) -> str:
    return {
        "continues": "continues the current lineage doctrine",
        "moderates": "moderates the current doctrine",
        "pivots": "pivots sharply away from the current doctrine",
    }[kind]


def successor_play_pattern(kind: str) -> str:
    return {
        "reciprocal": "Wins by opening clean, banking trust, then punishing the first betrayal.",
        "knife_first": "Wins by taking tempo early and forcing rivals to answer the knife.",
        "referendum_control": "Wins by scripting votes and then cashing the disorder that follows.",
        "referendum": "Wins by turning bloc politics and legitimacy into steady floor value.",
        "control": "Wins by scripting opponent behavior until the matchup turns lopsided.",
        "punishing": "Wins by making every hostile action cost more than it gains.",
        "unstable": "Wins through awkward, hard-to-mirror swing turns.",
        "default": "Wins through balanced coverage and cleaner adaptation than the room expects.",
    }[kind]


def successor_break_point(kind: str) -> str:
    return {
        "unstable": "Breaks when variance turns a close floor into a self-inflicted stumble.",
        "referendum": "Breaks when the room stops paying for public legitimacy and starts racing tempo.",
        "control": "Breaks if forced lines miss and the table unites around backlash.",
        "reciprocal": "Breaks in betrayal mirrors where trust never gets the chance to compound.",
        "knife_first": "Breaks if the opener gets answered and the heir has no clean reset.",
        "safe_heir": "Breaks when slower value lines suddenly need to win a short race.",
        "default": "Breaks when the next floor asks for a sharper doctrine than this line can offer.",
    }[kind]


def successor_current_fit_text(kind: str) -> str:
    return {
        "no_threat_tempo": "No rival lane is dominant yet, so this heir can seize initiative before the floor settles.",
        "no_threat_referendum": "No rival lane is dominant yet, so this heir can claim bloc value before a public leader emerges.",
        "no_threat_stability": "No rival lane is dominant yet, so this heir can stabilize the room and build legitimacy.",
        "no_threat_flexible": "No rival lane is dominant yet, so this heir keeps the house flexible.",
        "vs_aggressive_absorb": "Absorbs knife-first pressure without letting the whole floor snowball.",
        "vs_aggressive_discipline": "Answers knife-first pressure with discipline instead of conceding the pace.",
        "vs_referendum_contest": "Contests bloc value before referendum specialists can monopolize it.",
        "vs_control_answer": "Can meet directive-heavy rivals on even footing instead of being scripted.",
        "vs_cooperative_punish": "Punishes soft cooperative pressure before those trust loops harden.",
        "vs_unstable_contain": "Keeps a swingy floor from stealing the whole pressure cycle.",
        "default_tempo": "Brings proactive tempo into a threat mix that wants you reacting.",
        "default_referendum": "Adds a second axis of pressure through bloc math instead of pure duels.",
        "default_flexible": "Keeps the next floor playable without overcommitting the house.",
    }[kind]


def successor_future_risk_text(kind: str) -> str:
    return {
        "civil_war_monster": "Visible power makes this heir the branch everyone prepares to contain.",
        "unstable": "Variance can flip a winning floor into a self-inflicted collapse.",
        "referendum_in_civil_war": "Vote leverage fades fast once civil-war mirrors settle things head to head.",
        "hardline_in_ecosystem": "Hardline pressure can unite outsiders before the war phase even starts.",
        "pure_trust": "Pure trust lines can be farmed if the next floor never rewards peace.",
        "safe_heir": "Stable value lines can lose the race when the next floor demands burst.",
        "default": "This specialty becomes a trap if the next floor asks for the opposite tempo.",
    }[kind]


def successor_lineage_future_text(kind: str, *, relation_text: str, lineage_doctrine: str | None = None) -> str:
    if kind == "civil_war_force":
        return f"{relation_text} and breeds heirs built to win civil-war mirrors by force."
    if kind == "civil_war_survival":
        return f"{relation_text} and commits the line to surviving civil-war pressure."
    if kind == "referendum":
        return f"{relation_text} and teaches the house to win through bloc leverage."
    if kind == "legitimacy":
        return f"{relation_text} and grows a legitimacy-focused house."
    if kind == "tempo":
        return f"{relation_text} and sharpens the lineage into a tempo-first family."
    if kind == "unstable":
        return f"{relation_text} and opens the house to volatile successor futures."
    if kind == "quoted_lineage" and lineage_doctrine is not None:
        return f"{relation_text} relative to '{lineage_doctrine}'."
    return f"{relation_text} while keeping the branch arc open."


def successor_succession_pitch_text(kind: str) -> str:
    return {
        "civil_war_force": "Take this heir to decide civil-war mirrors on your pressure, not theirs.",
        "pivot": "Take this heir if you want to break from the current house and force a new doctrine.",
        "referendum_contest": "Take this heir to own the bloc math before referendum specialists run away with it.",
        "reciprocal": "Take this heir to build trusted tempo and punish anyone who breaks it.",
        "knife_first": "Take this heir to seize pace early and ask the floor to survive it.",
        "discipline": "Take this heir to make discipline and scripted pressure the family brand.",
        "referendum": "Take this heir to win through coalition control instead of raw duel speed.",
        "default": "Take this heir if you want flexible coverage without locking the house too far in one direction.",
    }[kind]


def successor_succession_risk_text(kind: str) -> str:
    return {
        "unstable": "Carries swing-heavy variance, including self-inflicted elimination turns.",
        "hardline_in_ecosystem": "Coercive lines can unite outsiders before civil war even starts.",
        "weak_referendum": "Low referendum resilience can leak floor value every time blocs matter.",
        "thin_recovery": "If the opener misses, the recovery lane is thinner than it looks.",
        "peace_without_punish": "If peace never sticks, this heir can end up taking hits without returning any.",
        "default": "Commits the house to a narrower set of fallback plans if the threat mix turns.",
    }[kind]


def successor_anti_score_text(kind: str) -> str:
    return {
        "referendum_trail": "Score trails, but bloc control can matter more than duel totals on the next floor.",
        "fit_trail": "Score trails, but doctrine fit makes the transition cleaner for this pressure cycle.",
        "war_ready_trail": "Score trails, but this heir is more war-ready than the scoreboard suggests.",
        "tempo_lead_brittle": "Top score is tempo-driven and may be brittle against retaliation-heavy tables.",
        "referendum_lead_exposed": "Top score hides referendum exposure; floor-value leaks can erase that lead quickly.",
        "default": "Score matters, but doctrine fit and matchup coverage should break the tie.",
    }[kind]


def featured_inference_summary_clues(observed_clues: Sequence[str]) -> str:
    return f"Clues seen: {' | '.join(observed_clues)}"


def featured_inference_summary_tags(inferred_tags: Sequence[str]) -> str:
    return "Likely featured tags this floor: " + ", ".join(inferred_tags) + ". Use them to compare heirs and risk."


def featured_inference_summary_scope() -> str:
    return "Clues only: this does not reveal hidden opponents."


def featured_inference_future_text(kind: str) -> str:
    return {
        "hybrid": "Hybrid branch that mixes coercive tools with coalition habits.",
        "hardline": "Hardline branch built around control, punishment, and deception pressure.",
        "consensus": "Consensus branch built around reciprocity, legitimacy, and bloc trust.",
        "ambiguous": "Ambiguous branch with no single doctrine fully confirmed.",
    }[kind]


def featured_inference_stability_text(kind: str) -> str:
    return {
        "hybrid_confirmed": "Stable for now, but rivals can split the branch by attacking either doctrine wing.",
        "hybrid_unconfirmed": "Fragile until the floor confirms both halves of the hybrid plan.",
        "hardline_confirmed": "Stable while hardline reads stay live, but brittle if the room swings back to legitimacy.",
        "hardline_unconfirmed": "Fragile because the floor has not confirmed a hardline future yet.",
        "consensus_confirmed": "Stable while trust loops hold, but betrayal mirrors can still collapse it.",
        "consensus_unconfirmed": "Fragile because consensus reads are not fully confirmed this floor.",
        "ambiguous": "Unclear because the clues do not anchor a single doctrine path.",
    }[kind]


def featured_inference_confidence_label(match_count: int) -> str:
    if match_count >= 2:
        return "High"
    if match_count == 1:
        return "Medium"
    return "Low"


def featured_inference_confidence_detail(aligned: Sequence[str]) -> str:
    if len(aligned) >= 2:
        return f"High: featured clues reinforce this branch on {_natural_join(tag.lower() for tag in aligned[:2])}."
    if len(aligned) == 1:
        return f"Medium: only {aligned[0].lower()} is directly reinforced."
    return "Low: featured clues do not directly reinforce this branch."


def civil_war_featured_inference_lines(kind: str) -> str:
    return {
        "mixed": "Clue read: both trust and force plans look live right now.",
        "coercive": "Clue read: force-heavy pressure is rising; backlash risk is real if hardline branches stumble.",
        "legitimacy": "Clue read: trust-heavy pressure is rising; betrayal spikes can break that trust quickly.",
        "retaliation": "Clue read: retaliation risk is high; one betrayal can snowball.",
        "deception": "Clue read: deception risk is live; mirror rounds can flip on bait-and-punish traps.",
    }[kind]


def _natural_join(items: Sequence[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"
