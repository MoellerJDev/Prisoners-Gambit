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




def test_runtime_non_default_language_changes_multiple_visible_areas_and_runtime_label(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(f"{web_server_runtime}/?lang=en-x-test", wait_until="networkidle")

    assert "Prisoner's Gambit [test]" in page.locator("#appTitle").inner_text()
    assert "Start Run [test]" in page.locator("#startRunBtn").inner_text()
    assert "Current Decision [test]" in page.locator("#currentDecisionHeading").inner_text()
    assert "Summary [test]" in page.locator("#tabSummaryBtn").inner_text()

    page.click("#startRunBtn")
    page.wait_for_timeout(150)
    assert "Next pick [test]" in page.locator("#decisionView").inner_text()
    assert "status[test]: awaiting_decision" in page.locator("#status").inner_text()
    assert page.locator("#actions button", has_text="Cooperate").count() >= 1
    assert page.locator("#actions button", has_text="Defect").count() >= 1

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


def test_runtime_transition_only_state_renders_primary_action_in_current_decision(web_server_runtime, playwright_page) -> None:
    _post_json(web_server_runtime, "/api/run/start")
    _post_json(web_server_runtime, "/api/action", {"type": "manual_move", "move": "C"})
    _post_json(web_server_runtime, "/api/advance")
    _post_json(web_server_runtime, "/api/action", {"type": "manual_vote", "vote": "C"})
    _post_json(web_server_runtime, "/api/advance")

    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")
    page.evaluate("refresh()")
    page.wait_for_timeout(150)

    assert "Review successor options" in page.locator("#decisionType").inner_text()
    assert "Open successor options" in page.locator("#decisionView").inner_text()
    assert page.locator("#actions button.primary-action", has_text="Review successor options").count() == 1

    page.locator("#actions button.primary-action", has_text="Review successor options").click()
    page.wait_for_timeout(150)
    assert "Successor choice" in page.locator("#decisionType").inner_text()


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
    assert page.locator("#decisionView .choice-confirm-btn").count() == 0
    assert "Select an option" in page.locator("#decisionView").inner_text()
    assert page.locator("#actions button.choice-option-selected").count() == 0

    page.locator("#actions button").nth(1).click()
    page.wait_for_timeout(150)
    assert page.locator("#actions button.choice-option-selected").count() == 1
    assert page.locator("#actions button").nth(1).get_attribute("class") is not None
    assert "Confirm choice" in page.locator("#decisionView .choice-confirm-btn").inner_text()

    page.locator("#decisionView .choice-confirm-btn").click()
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


def test_runtime_onboarding_visible_then_dismissed_and_persisted(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")

    onboarding = page.locator("#onboardingPanel")
    assert onboarding.evaluate("el => getComputedStyle(el).display") != "none"

    page.click("#onboardingPanel .onboarding-dismiss")
    page.wait_for_timeout(100)
    assert onboarding.evaluate("el => getComputedStyle(el).display") == "none"

    page.reload(wait_until="networkidle")
    assert onboarding.evaluate("el => getComputedStyle(el).display") == "none"


def test_runtime_glossary_toggle_and_tab_help_updates(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")

    glossary = page.locator("#glossaryPanel")
    assert glossary.evaluate("el => getComputedStyle(el).display") == "none"

    page.click("button:has-text('Doctrine ?')")
    page.wait_for_timeout(50)
    assert "build identity" in glossary.inner_text()

    page.click("#tabBoardBtn")
    assert "gaining pressure" in page.locator("#tabHelpText").inner_text()
    page.click("#tabChronicleBtn")
    assert "changed across floors" in page.locator("#tabHelpText").inner_text()




def test_runtime_controlled_vote_glossary_is_mechanically_explicit(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")

    page.click("button:has-text('Controlled Vote ?')")
    page.wait_for_timeout(50)
    glossary_text = page.locator("#glossaryPanel").inner_text()
    assert "shaped or forced" in glossary_text
    assert "not a free pick" in glossary_text


def test_runtime_phase_helpers_show_for_reward_and_successor_choices(web_server_runtime, playwright_page) -> None:
    _drive_to_successor_choice(web_server_runtime)

    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")
    page.evaluate("refresh()")
    page.wait_for_timeout(150)

    assert "Compare Cause, Pick for, Risk" in page.locator("#phaseActionHelper").inner_text()

    page.locator("#actions button").first.click()
    page.locator("#decisionView .choice-confirm-btn").click()
    page.wait_for_timeout(150)
    assert "Powerup choice" in page.locator("#decisionType").inner_text()
    assert "Pick by the first-line effect" in page.locator("#phaseActionHelper").inner_text()


def test_runtime_successor_choice_select_then_confirm_updates_decision_details(web_server_runtime, playwright_page) -> None:
    _drive_to_successor_choice(web_server_runtime)

    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")
    page.evaluate("refresh()")
    page.wait_for_timeout(150)

    assert "Successor choice" in page.locator("#decisionType").inner_text()
    assert page.locator("#actions button.choice-option-selected").count() == 0
    assert page.locator("#decisionView .choice-confirm-btn").count() == 0
    assert "Select an option" in page.locator("#decisionView").inner_text()

    selected_name = page.locator("#actions button .action-tile-title").first.inner_text()
    page.locator("#actions button").first.click()
    page.wait_for_timeout(150)

    assert page.locator("#actions button.choice-option-selected").count() == 1
    assert page.locator("#decisionView .choice-details-title").inner_text() == selected_name
    assert page.locator("#decisionView .choice-confirm-btn").count() == 1
    assert page.locator("#decisionView").inner_text().count("No direct clue fit") == 0

    page.locator("#decisionView .choice-confirm-btn").click()
    page.wait_for_timeout(150)
    assert "Powerup choice" in page.locator("#decisionType").inner_text()


def test_runtime_choice_selection_does_not_carry_to_new_choice_payload_same_type(web_server_runtime, playwright_page) -> None:
    page = playwright_page
    page.goto(web_server_runtime, wait_until="networkidle")

    page.evaluate(
        """
        () => {
          const firstDecision = {
            decision_type: 'PowerupChoiceState',
            decision: {
              floor_number: 2,
              offers: [
                {name:'Alpha Card', effect:'Gain leverage now', trigger:'When pressure rises'},
                {name:'Beta Card', effect:'Hold stability', trigger:'When ties form'},
              ],
            },
          };
          renderDecision(firstDecision);
          document.querySelector('#actions button:nth-child(2)').click();

          const secondDecision = {
            decision_type: 'PowerupChoiceState',
            decision: {
              floor_number: 2,
              offers: [
                {name:'Gamma Card', effect:'Shift doctrine', trigger:'When outsider leads'},
                {name:'Delta Card', effect:'Protect heir lane', trigger:'When host pressured'},
              ],
            },
          };
          renderDecision(secondDecision);
        }
        """
    )

    assert page.locator("#actions button.choice-option-selected").count() == 0
    assert page.locator("#decisionView .choice-confirm-btn").count() == 0
    assert "Select an option" in page.locator("#decisionView").inner_text()


def test_runtime_mobile_choice_cards_and_detail_panel_are_separate_and_compact(web_server_runtime) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    _drive_to_powerup_choice(web_server_runtime)
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.goto(web_server_runtime, wait_until="networkidle")
            page.evaluate("refresh()")
            page.wait_for_timeout(150)

            assert "Powerup choice" in page.locator("#decisionType").inner_text()
            assert page.locator("#actions button").count() >= 2
            assert page.locator("#decisionView .choice-confirm-btn").count() == 0

            actions_height = page.locator("#actions").evaluate("el => el.getBoundingClientRect().height")
            details_top = page.locator(".decision-details-panel").evaluate("el => el.getBoundingClientRect().top")
            actions_top = page.locator("#actions").evaluate("el => el.getBoundingClientRect().top")
            assert actions_height < 380
            assert details_top >= actions_top
        finally:
            browser.close()


def test_runtime_mobile_onboarding_non_blocking_and_controls_tappable(web_server_runtime) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            page.goto(web_server_runtime, wait_until="networkidle")
            onboarding_box = page.locator("#onboardingPanel").bounding_box()
            viewport = page.viewport_size
            assert onboarding_box is not None
            assert viewport is not None
            assert onboarding_box["height"] < viewport["height"]

            page.click("#onboardingPanel .onboarding-dismiss")
            page.click("text=Start Run")
            page.wait_for_timeout(150)
            assert page.locator("#actions button").count() >= 1
            page.click("#tabBoardBtn")
            assert page.locator("#secondaryTabBoard.active").count() == 1
        finally:
            browser.close()
