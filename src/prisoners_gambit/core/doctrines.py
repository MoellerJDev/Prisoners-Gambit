from __future__ import annotations

from typing import Literal

BranchFocus = Literal["safe", "ruthless", "unstable", "referendum"]

BRANCH_FOCUS_SAFE: BranchFocus = "safe"
BRANCH_FOCUS_RUTHLESS: BranchFocus = "ruthless"
BRANCH_FOCUS_UNSTABLE: BranchFocus = "unstable"
BRANCH_FOCUS_REFERENDUM: BranchFocus = "referendum"

ALL_BRANCH_FOCI: tuple[BranchFocus, ...] = (
    BRANCH_FOCUS_SAFE,
    BRANCH_FOCUS_RUTHLESS,
    BRANCH_FOCUS_UNSTABLE,
    BRANCH_FOCUS_REFERENDUM,
)

BranchRole = Literal[
    "Safe heir",
    "Ruthless heir",
    "Unstable heir",
    "Referendum heir",
    "Future civil-war monster",
]
