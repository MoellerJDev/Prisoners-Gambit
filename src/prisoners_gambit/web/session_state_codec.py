from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import hmac
import json
import zlib
from typing import Any, get_type_hints

from prisoners_gambit.core.constants import COOPERATE, DEFECT
from prisoners_gambit.core.genome_edits import GenomeEdit
from prisoners_gambit.core.interaction import (
    ChooseFloorVoteAction,
    ChooseGenomeEditAction,
    ChoosePowerupAction,
    ChooseRoundAutopilotAction,
    ChooseRoundMoveAction,
    ChooseRoundStanceAction,
    ChooseSuccessorAction,
    FloorVoteDecisionState,
    GenomeEditChoiceState,
    PowerupChoiceState,
    FeaturedRoundDecisionState,
    RunSnapshot,
    SuccessorChoiceState,
)
from prisoners_gambit.core.models import Agent
from prisoners_gambit.core.powerups import Powerup
from prisoners_gambit.core.strategy import StrategyGenome


def serialize_state_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def export_save_code(payload_json: str, secret: bytes, *, version: int) -> str:
    signature = hmac.new(secret, payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
    envelope = {
        "version": version,
        "compressed": True,
        "payload": base64.urlsafe_b64encode(zlib.compress(payload_json.encode("utf-8"))).decode("ascii"),
        "signature": signature,
    }
    encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii")


def import_save_code(save_code: str, secret: bytes, *, version: int) -> dict:
    try:
        raw = base64.urlsafe_b64decode(save_code.encode("ascii")).decode("utf-8")
        envelope = json.loads(raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid save code") from exc

    if not isinstance(envelope, dict) or envelope.get("version") != version:
        raise ValueError("Unsupported save state version")
    payload_b64 = envelope.get("payload")
    signature = envelope.get("signature")
    if not isinstance(payload_b64, str) or not isinstance(signature, str):
        raise ValueError("Invalid save code")

    try:
        payload_json = zlib.decompress(base64.urlsafe_b64decode(payload_b64.encode("ascii"))).decode("utf-8")
    except (ValueError, zlib.error, UnicodeDecodeError) as exc:
        raise ValueError("Invalid save code") from exc

    expected = hmac.new(secret, payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid save code")

    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("Invalid save code")
    return payload


def serialize_powerup(powerup: Powerup) -> dict:
    payload = asdict(powerup)
    payload["type"] = type(powerup).__name__
    return payload


def deserialize_powerup(payload: dict, powerup_types: dict[str, type[Powerup]]) -> Powerup:
    powerup_type_name = payload.get("type")
    if powerup_type_name not in powerup_types:
        raise ValueError("Unsupported powerup type in save state")
    powerup_type = powerup_types[powerup_type_name]
    kwargs = {key: value for key, value in payload.items() if key != "type"}
    return powerup_type(**kwargs)


def serialize_genome_edit(edit: GenomeEdit) -> dict:
    return {"type": type(edit).__name__}


def deserialize_genome_edit(payload: dict, genome_edit_types: dict[str, type[GenomeEdit]]) -> GenomeEdit:
    genome_edit_type_name = payload.get("type")
    if genome_edit_type_name not in genome_edit_types:
        raise ValueError("Unsupported genome edit type in save state")
    return genome_edit_types[genome_edit_type_name]()


def serialize_agent(agent: Agent) -> dict:
    return {
        "name": agent.name,
        "public_profile": agent.public_profile,
        "powerups": [serialize_powerup(powerup) for powerup in agent.powerups],
        "score": agent.score,
        "wins": agent.wins,
        "is_player": agent.is_player,
        "lineage_id": agent.lineage_id,
        "lineage_depth": agent.lineage_depth,
        "agent_id": agent.agent_id,
        "genome": serialize_genome(agent.genome),
    }


def deserialize_agent(
    payload: dict,
    *,
    powerup_types: dict[str, type[Powerup]],
) -> Agent:
    return Agent(
        name=payload["name"],
        genome=deserialize_genome(payload["genome"]),
        public_profile=payload["public_profile"],
        powerups=[deserialize_powerup(entry, powerup_types) for entry in payload.get("powerups", [])],
        score=payload["score"],
        wins=payload["wins"],
        is_player=payload["is_player"],
        lineage_id=payload["lineage_id"],
        lineage_depth=payload["lineage_depth"],
        agent_id=payload["agent_id"],
    )


def serialize_genome(genome: StrategyGenome) -> dict:
    return {
        "first_move": genome.first_move,
        "noise": genome.noise,
        "response_table": {
            "cc": genome.response_table[(COOPERATE, COOPERATE)],
            "cd": genome.response_table[(COOPERATE, DEFECT)],
            "dc": genome.response_table[(DEFECT, COOPERATE)],
            "dd": genome.response_table[(DEFECT, DEFECT)],
        },
    }


def deserialize_genome(payload: dict) -> StrategyGenome:
    table = payload["response_table"]
    return StrategyGenome(
        first_move=payload["first_move"],
        noise=payload["noise"],
        response_table={
            (COOPERATE, COOPERATE): table["cc"],
            (COOPERATE, DEFECT): table["cd"],
            (DEFECT, COOPERATE): table["dc"],
            (DEFECT, DEFECT): table["dd"],
        },
    )


def deserialize_decision(decision_type_name: str | None, payload: dict | None, decision_types: dict[str, type]):
    if decision_type_name is None or payload is None:
        return None
    decision_type = decision_types.get(decision_type_name)
    if decision_type is None:
        raise ValueError("Unsupported decision type in save state")
    return build_dataclass(decision_type, payload)


def resolve_expected_action_types(expected_type_names: list[str], decision) -> tuple[type, ...]:
    if expected_type_names:
        type_map = {
            "ChooseRoundMoveAction": ChooseRoundMoveAction,
            "ChooseRoundAutopilotAction": ChooseRoundAutopilotAction,
            "ChooseRoundStanceAction": ChooseRoundStanceAction,
            "ChooseFloorVoteAction": ChooseFloorVoteAction,
            "ChoosePowerupAction": ChoosePowerupAction,
            "ChooseGenomeEditAction": ChooseGenomeEditAction,
            "ChooseSuccessorAction": ChooseSuccessorAction,
        }
        resolved_types: list[type] = []
        for expected_name in expected_type_names:
            if expected_name not in type_map:
                raise ValueError("Unsupported expected action type in save state")
            resolved_types.append(type_map[expected_name])
        return tuple(resolved_types)
    if isinstance(decision, FeaturedRoundDecisionState):
        return (ChooseRoundMoveAction, ChooseRoundAutopilotAction, ChooseRoundStanceAction)
    if isinstance(decision, FloorVoteDecisionState):
        return (ChooseFloorVoteAction,)
    if isinstance(decision, PowerupChoiceState):
        return (ChoosePowerupAction,)
    if isinstance(decision, GenomeEditChoiceState):
        return (ChooseGenomeEditAction,)
    if isinstance(decision, SuccessorChoiceState):
        return (ChooseSuccessorAction,)
    return ()


def deserialize_run_snapshot(payload: dict) -> RunSnapshot:
    return build_dataclass(RunSnapshot, payload)


def build_dataclass(dataclass_type: type, payload: dict):
    field_values = {}
    hints = get_type_hints(dataclass_type)
    for field in dataclass_type.__dataclass_fields__.values():  # type: ignore[attr-defined]
        if field.name not in payload:
            continue
        annotation = hints.get(field.name, field.type)
        field_values[field.name] = decode_value(annotation, payload[field.name])
    return dataclass_type(**field_values)


def decode_value(annotation, value):
    if value is None:
        return None
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    if origin is list and args:
        return [decode_value(args[0], item) for item in value]
    if origin is tuple and args:
        return tuple(decode_value(args[0], item) for item in value)
    if origin is None and hasattr(annotation, "__dataclass_fields__") and isinstance(value, dict):
        return build_dataclass(annotation, value)

    is_union = str(origin) in {"typing.Union", "types.UnionType"} or (
        origin is None and bool(args) and not hasattr(annotation, "__dataclass_fields__")
    )
    if is_union:
        for candidate in args:
            if candidate is type(None):
                continue
            try:
                return decode_value(candidate, value)
            except Exception:  # noqa: BLE001
                continue
    return value


def serialize_rng_state(state: tuple) -> dict:
    version, internal_state, gauss_next = state
    return {
        "version": int(version),
        "internal_state": encode_tuple(internal_state),
        "gauss_next": gauss_next,
    }


def deserialize_rng_state(payload: dict) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("Invalid rng_state payload")
    if "version" not in payload or "internal_state" not in payload:
        raise ValueError("Invalid rng_state payload")
    internal_state = decode_tuple(payload["internal_state"])
    gauss_next = payload.get("gauss_next")
    if gauss_next is not None and not isinstance(gauss_next, (int, float)):
        raise ValueError("Invalid rng_state payload")
    return (int(payload["version"]), internal_state, gauss_next)


def encode_tuple(value: Any):
    if isinstance(value, tuple):
        return [encode_tuple(item) for item in value]
    if isinstance(value, list):
        return [encode_tuple(item) for item in value]
    return value


def decode_tuple(value: Any):
    if isinstance(value, list):
        return tuple(decode_tuple(item) for item in value)
    return value
