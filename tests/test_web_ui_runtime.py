import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

import pytest

from prisoners_gambit.web.server import Handler


def _post_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = Request(f"{base_url}{path}", data=body if payload is not None else None, method="POST", headers=headers)
    with urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _drive_to_successor_choice(base_url: str) -> None:
    _post_json(base_url, "/api/run/start")
    _post_json(base_url, "/api/action", {"type": "manual_move", "move": "C"})
    _post_json(base_url, "/api/advance")
    _post_json(base_url, "/api/action", {"type": "manual_vote", "vote": "C"})
    _post_json(base_url, "/api/advance")
    _post_json(base_url, "/api/advance")


def _drive_to_powerup_choice(base_url: str) -> None:
    _drive_to_successor_choice(base_url)
    _post_json(base_url, "/api/action", {"type": "choose_successor", "candidate_index": 0})
    _post_json(base_url, "/api/advance")


@pytest.fixture
def web_server_runtime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PG_ROUNDS_PER_MATCH", "1")
    monkeypatch.setenv("PG_SEED", "17")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"

    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


@pytest.fixture
def playwright_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            yield page
        finally:
            browser.close()


def test_runtime_tabs_switch_and_debug_not_default(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")

    assert page.locator("#secondaryTabSummary.active").count() == 1
    assert page.locator("#secondaryTabDebug.active").count() == 0

    page.click("#tabBoardBtn")
    assert page.locator("#secondaryTabBoard.active").count() == 1

    page.click("#tabChronicleBtn")
    assert page.locator("#secondaryTabChronicle.active").count() == 1

    page.click("#tabDebugBtn")
    assert page.locator("#secondaryTabDebug.active").count() == 1


def test_runtime_powerup_cards_render_compact_and_click_to_genome(web_server_runtime, playwright_page) -> None:
    _drive_to_powerup_choice(web_server_runtime)

    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")
    page.evaluate("refresh()")
    page.wait_for_timeout(150)

    decision_text = page.locator("#decisionType").inner_text()
    assert "Powerup choice" in decision_text

    assert page.locator("#actions button details").count() == 0
    assert page.locator("#actions .choice-card-effect").count() >= 1

    page.locator("#actions button").first.click()
    page.wait_for_timeout(150)
    decision_after = page.locator("#decisionType").inner_text()
    assert "Genome edit" in decision_after


def test_runtime_successor_comparison_visible_and_survives_tab_switch(web_server_runtime, playwright_page) -> None:
    _drive_to_successor_choice(web_server_runtime)

    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")
    page.evaluate("refresh()")
    page.wait_for_timeout(150)

    assert "Successor choice" in page.locator("#decisionType").inner_text()
    assert page.locator("#successorComparisonSection").evaluate("el => getComputedStyle(el).display") != "none"
    assert page.locator("#successorComparison .muted-label", has_text="Cause").count() >= 1
    assert page.locator("#successorComparison .muted-label", has_text="Pick for").count() >= 1

    page.click("#tabBoardBtn")
    assert page.locator("#secondaryTabBoard.active").count() == 1
    page.click("#tabSummaryBtn")
    assert page.locator("#secondaryTabSummary.active").count() == 1
    assert page.locator("#successorComparison .comparison-card").count() >= 1


def test_runtime_mobile_view_keeps_decision_panel_prominent_and_tabs_accessible(web_server_runtime) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.goto(web_server_runtime, wait_until="networkidle")
            page.click("text=Start Run")
            page.wait_for_timeout(150)

            decision_top = page.locator(".decision-actions-panel").evaluate("el => el.getBoundingClientRect().top")
            details_top = page.locator(".decision-details-panel").evaluate("el => el.getBoundingClientRect().top")
            assert decision_top <= details_top

            assert page.locator(".tab-controls button").count() == 4
            assert page.locator("#actions button").count() >= 1
        finally:
            browser.close()
