from __future__ import annotations

from prisoners_gambit.core.analysis import analyze_agent_identity, analyze_floor_heir_pressure
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    FeaturedMatchPrompt,
    FeaturedRoundResult,
    FloorVotePrompt,
    FloorVoteResult,
    GenomeEditOfferView,
    PowerupOfferView,
    RosterEntry,
    SuccessorCandidateView,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.utils.formatting import move_symbol


def _history_text(history: list[int]) -> str:
    if not history:
        return "-"
    return " ".join(move_symbol(move) for move in history)


def _tag_text(tags: list[str]) -> str:
    if not tags:
        return "No tags"
    return ", ".join(tags)


def format_agent_line(index: int, agent: Agent) -> str:
    marker = "[YOU] " if agent.is_player else ""
    identity = analyze_agent_identity(agent)
    return (
        f"{index}. {marker}{agent.name} | score={agent.score} | wins={agent.wins} | "
        f"{_tag_text(identity.tags)}"
    )


def format_powerup_line(index: int, powerup: Powerup) -> str:
    return f"{index}. {powerup.name} - {powerup.description}"


def format_roster_line(index: int, entry: RosterEntry) -> str:
    powerups = ", ".join(entry.known_powerups) if entry.known_powerups else "No visible powerups"
    return (
        f"{index}. {entry.name} | {entry.public_profile}\n"
        f"   Tags: {_tag_text(entry.tags)}\n"
        f"   Read: {entry.descriptor}\n"
        f"   Visible powerups: {powerups}"
    )


def format_genome_edit_line(index: int, edit: GenomeEdit) -> str:
    return f"{index}. {edit.name} - {edit.description}"


def _offer_doctrine_lines(offer: PowerupOfferView | GenomeEditOfferView) -> list[str]:
    lines: list[str] = []
    if isinstance(offer, PowerupOfferView):
        if offer.hook:
            lines.append(f"Why now: {offer.hook}")
        if offer.timing:
            lines.append(f"When: {offer.timing}")
        if offer.plan:
            lines.append(f"Plan: {offer.plan}")
        if offer.cost:
            lines.append(f"Cost: {offer.cost}")
        if offer.fit_detail:
            lines.append(f"Fit detail: {offer.fit_detail}")
        if offer.doctrine_commitment:
            lines.append(f"Doctrine commitment: {offer.doctrine_commitment}")
    if isinstance(offer, GenomeEditOfferView):
        if offer.rewrite:
            lines.append(f"Rewrite: {offer.rewrite}")
        if offer.doctrine_shift:
            lines.append(f"Shift: {offer.doctrine_shift}")
        if offer.tempo_note:
            lines.append(offer.tempo_note)
        if offer.stability_note:
            lines.append(offer.stability_note)
        if offer.doctrine_commitment:
            lines.append(f"Doctrine commitment: {offer.doctrine_commitment}")
    if offer.lineage_commitment:
        lines.append(f"Lineage commitment: {offer.lineage_commitment}")
    if offer.doctrine_vector and not offer.lineage_commitment:
        lines.append(f"Doctrine vector: {offer.doctrine_vector}")
    if offer.branch_identity:
        lines.append(f"Branch identity: {offer.branch_identity}")
    if offer.tradeoff:
        lines.append(f"Tradeoff: {offer.tradeoff}")
    if offer.phase_support:
        lines.append(f"Phase support: {offer.phase_support}")
    if offer.successor_pressure:
        lines.append(f"Successor pressure: {offer.successor_pressure}")
    if isinstance(offer, PowerupOfferView):
        if offer.trigger:
            lines.append(f"When: {offer.trigger}")
        if offer.effect:
            lines.append(f"Effect: {offer.effect}")
        if offer.role:
            lines.append(f"Role: {offer.role}")
        if offer.tags:
            lines.append(f"Synergy tags: {', '.join(offer.tags)}")
        if offer.relevance_hint:
            lines.append(f"Offer rationale: {offer.relevance_hint}")
        if offer.crown_hint:
            lines.append(offer.crown_hint)
    if isinstance(offer, GenomeEditOfferView):
        if offer.doctrine_drift:
            lines.append(f"Doctrine drift: {offer.doctrine_drift}")
        if offer.current_summary or offer.projected_summary:
            lines.append(f"Build: {offer.current_summary or '-'} -> {offer.projected_summary or '-'}")
    return lines


def format_powerup_offer_view(index: int, offer: PowerupOfferView) -> str:
    lines = [f"{index}. {offer.name} - {offer.description}"]
    lines.extend(f"   {line}" for line in _offer_doctrine_lines(offer))
    return "\n".join(lines)


def format_genome_edit_offer_view(index: int, offer: GenomeEditOfferView) -> str:
    projected_suffix = f" -> {offer.projected_summary}" if offer.projected_summary else ""
    lines = [f"{index}. {offer.name} - {offer.description}{projected_suffix}"]
    lines.extend(f"   {line}" for line in _offer_doctrine_lines(offer))
    return "\n".join(lines)


def format_successor_candidate_view(index: int, candidate: SuccessorCandidateView) -> str:
    powerups = ", ".join(candidate.powerups) if candidate.powerups else "No powerups"
    shaping_causes = "; ".join(candidate.shaping_causes)
    tradeoffs = "; ".join(candidate.tradeoffs)
    strengths = "; ".join(candidate.strengths)
    liabilities = "; ".join(candidate.liabilities)
    lines = [
        f"{index}. {candidate.name} | depth={candidate.lineage_depth} | score={candidate.score} | wins={candidate.wins}",
        f"   Role: {candidate.branch_role}",
        f"   Doctrine: {candidate.branch_doctrine}",
        f"   Tags: {_tag_text(candidate.tags)}",
        f"   Shaping causes: {shaping_causes}",
        f"   Read: {candidate.descriptor}",
    ]
    if candidate.headline:
        lines.append(f"   Headline: {candidate.headline}")
    if candidate.play_pattern:
        lines.append(f"   Pattern: {candidate.play_pattern}")
    if candidate.why_now:
        lines.append(f"   Why now: {candidate.why_now}")
    if candidate.watch_out:
        lines.append(f"   Watch out: {candidate.watch_out}")
    if candidate.dynasty_future:
        lines.append(f"   Dynasty future: {candidate.dynasty_future}")
    lines.extend([
        f"   Tradeoffs: {tradeoffs}",
        f"   Strengths: {strengths}",
        f"   Liabilities: {liabilities}",
        f"   Attractive now: {candidate.attractive_now}",
        f"   Danger later: {candidate.danger_later}",
        f"   Succession play: {candidate.succession_pitch}",
        f"   Succession risk: {candidate.succession_risk}",
        f"   Anti-score note: {candidate.anti_score_note}",
        f"   Implied future: {candidate.lineage_future}",
        f"   Build: {candidate.genome_summary}",
        f"   Powerups: {powerups}",
    ])
    if candidate.clue_future:
        lines.append(f"   Clue future: {candidate.clue_future}")
    if candidate.clue_stability:
        lines.append(f"   Clue stability: {candidate.clue_stability}")
    if candidate.clue_confidence:
        lines.append(f"   Clue confidence: {candidate.clue_confidence}")
    if candidate.featured_inference_context:
        lines.append(f"   Featured inference: {candidate.featured_inference_context}")
    return "\n".join(lines)


def format_featured_inference_summary(summary: list[str]) -> str:
    if not summary:
        return "[Featured inference summary] No confirmed featured clues survived this floor."
    lines = "\n".join(f"- {line}" for line in summary)
    return f"[Featured inference summary]\n{lines}"


def format_featured_prompt(prompt: FeaturedMatchPrompt) -> str:
    roster_hint = ""
    if prompt.roster_entries:
        roster_hint = "Use the floor roster and move patterns to infer who this may be.\n"

    clue_lines = ""
    if prompt.clue_channels:
        clue_lines = "\n".join(f"- {line}" for line in prompt.clue_channels)
        clue_lines = f"Clues in play:\n{clue_lines}\n"

    floor_log = ""
    if prompt.floor_clue_log:
        recent = prompt.floor_clue_log[-3:]
        floor_log = "\n".join(f"- {line}" for line in recent)
        floor_log = f"Floor clue memory:\n{floor_log}\n"

    focus = f"Inference focus: {prompt.inference_focus}\n" if prompt.inference_focus else ""

    return (
        f"\n[Featured Match] {prompt.masked_opponent_label}\n"
        f"Round {prompt.round_index + 1}/{prompt.total_rounds}\n"
        f"Match score: You {prompt.my_match_score} - {prompt.opp_match_score} Opponent\n"
        f"Your history: {_history_text(prompt.my_history)}\n"
        f"Their history: {_history_text(prompt.opp_history)}\n"
        f"{roster_hint}"
        f"{clue_lines}"
        f"{floor_log}"
        f"{focus}"
        f"Autopilot suggests: {move_symbol(prompt.suggested_move)}"
    )


def format_round_result(result: FeaturedRoundResult) -> str:
    score_adjustments = "none"
    if result.breakdown.score_adjustments:
        lines = [
            f"{adjustment.source}: {adjustment.player_delta:+}/{adjustment.opponent_delta:+}"
            for adjustment in result.breakdown.score_adjustments
        ]
        score_adjustments = ", ".join(lines)

    inference = ""
    if result.inference_update:
        inference = "\n".join(f"  • {line}" for line in result.inference_update)
        inference = f"\n- Inference update:\n{inference}"

    return (
        f"Round {result.round_index + 1}/{result.total_rounds}\n"
        f"- Autopilot planned: You={move_symbol(result.breakdown.player_plan)}, "
        f"Opp={move_symbol(result.breakdown.opponent_plan)}\n"
        f"- Directives: You={result.player_reason} | Opp={result.opponent_reason}\n"
        f"- Final moves: You={move_symbol(result.player_move)}, Opp={move_symbol(result.opponent_move)}\n"
        f"- Base payoff: {result.breakdown.base_player_points} / {result.breakdown.base_opponent_points}\n"
        f"- Score modifiers: {score_adjustments}\n"
        f"- Final payoff: {result.player_delta} / {result.opponent_delta}\n"
        f"- Match total: {result.player_total} / {result.opponent_total}"
        f"{inference}"
    )


def format_floor_vote_prompt(prompt: FloorVotePrompt) -> str:
    powerups = ", ".join(prompt.powerups) if prompt.powerups else "No powerups"
    return (
        f"\n[Floor Referendum] Floor {prompt.floor_number} - {prompt.floor_label}\n"
        f"Current floor score: {prompt.current_floor_score}\n"
        f"Your visible powerups: {powerups}\n"
        f"Autopilot suggests: {move_symbol(prompt.suggested_vote)}\n"
        f"If cooperation reaches a majority or better, cooperators gain floor reward.\n"
        f"If defection is the majority, nobody gains anything."
    )


def format_floor_vote_result(result: FloorVoteResult) -> str:
    outcome = "Cooperation prevailed" if result.cooperation_prevailed else "Defection spoiled the vote"
    return (
        f"\n[Referendum Result] Floor {result.floor_number}\n"
        f"{outcome}\n"
        f"Cooperators: {result.cooperators} | Defectors: {result.defectors}\n"
        f"Your vote: {move_symbol(result.player_vote)} | Your reward: {result.player_reward}"
    )


def format_successor_line(index: int, agent: Agent) -> str:
    powerups = ", ".join(powerup.name for powerup in agent.powerups) if agent.powerups else "No powerups"
    identity = analyze_agent_identity(agent)
    return (
        f"{index}. {agent.name} | depth={agent.lineage_depth} | score={agent.score} | wins={agent.wins}\n"
        f"   Tags: {_tag_text(identity.tags)}\n"
        f"   Read: {identity.descriptor}\n"
        f"   Build: {agent.genome.summary()}\n"
        f"   Powerups: {powerups}"
    )


def format_floor_heir_pressure(ranked: list[Agent]) -> str:
    player = next((agent for agent in ranked if agent.is_player), None)
    pressure = analyze_floor_heir_pressure(ranked, player.lineage_id if player else None)

    lines: list[str] = ["[Future Successor Pressure]", pressure.branch_doctrine]

    if pressure.successor_candidates:
        lines.append("Potential successors if you die next floor:")
        for candidate in pressure.successor_candidates:
            lines.append(
                f"- {candidate.name} (score={candidate.score}, wins={candidate.wins}) | "
                f"{candidate.branch_role} | {_tag_text(candidate.tags)} | causes: {'; '.join(candidate.shaping_causes)} | {candidate.rationale}"
            )
    else:
        lines.append("Potential successors if you die next floor: none visible yet.")

    if pressure.future_threats:
        lines.append("Emerging external threats:")
        for threat in pressure.future_threats:
            lines.append(
                f"- {threat.name} (score={threat.score}, wins={threat.wins}) | "
                f"{threat.branch_role} | {_tag_text(threat.tags)} | causes: {'; '.join(threat.shaping_causes)} | {threat.rationale}"
            )
    else:
        lines.append("Emerging external threats: none (civil war pressure dominates).")

    return "\n".join(lines)
