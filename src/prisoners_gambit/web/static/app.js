let latest = null;
let previousTotals = null;
let activeSecondaryTab = 'summary';
let pendingChoiceSelection = null;
const SAVE_STORAGE_KEY = 'prisoners_gambit_web_save_v1';
const ONBOARDING_DISMISSED_KEY = 'prisoners_gambit_onboarding_dismissed_v1';
const PANEL_LIMITS = Object.freeze({
  floorLeaders: 4,
  floorHeirs: 1,
  floorThreats: 1,
  successorCards: 2,
  chronicleEntries: 4,
  rules: 2,
});

function escapeHtml(s){ const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function cleanCauseLine(text){
  if (!text) return '';
  return String(text).replace(/^because\s+/i, '').trim();
}
function moveLabel(v){ return v === 0 ? 'C' : 'D'; }
function effectToken(label){ return `<span class='token effect'>✦ ${escapeHtml(label)}</span>`; }
function relationToken(relation){
  const labels = {host:t('relation_tokens.host'), kin:t('relation_tokens.kin'), outsider:t('relation_tokens.outsider')};
  return `<span class='token branch'>${escapeHtml(labels[relation] || t('relation_tokens.outsider'))}</span>`;
}
function movementGlyph(delta){
  if (delta > 0) return `↑${delta}`;
  if (delta < 0) return `↓${Math.abs(delta)}`;
  return '→0';
}
function branchToken(label){ return `<span class='token branch'>⎇ ${escapeHtml(label)}</span>`; }
function t(key, fallback=''){ return getNestedText(key, fallback); }
function powerupToken(label){ return `<span class='token powerup'>⚡ ${escapeHtml(label)}</span>`; }
function genomeToken(label){ return `<span class='token genome'>🧬 ${escapeHtml(label)}</span>`; }

function actionTile(label, meta){
  const metaText = meta ? `<span class='action-tile-meta'>${escapeHtml(meta)}</span>` : '';
  return `<span class='action-tile-title'>${escapeHtml(label)}</span>${metaText}`;
}

function formatCountMore(extra){
  return t('messages.more_count', '+{count} more').replace('{count}', String(extra));
}

function compactTokenPreview(items, renderer, limit=3, emptyLabel=''){
  const values = items || [];
  if (!values.length) return emptyLabel || t('fallbacks.none');
  const shown = values.slice(0, limit).map(renderer).join(' ');
  const extra = values.length - limit;
  return extra > 0 ? `${shown} <span class='choice-card-more'>${escapeHtml(formatCountMore(extra))}</span>` : shown;
}

function compactEffectLine(parts){
  return (parts || []).find(part => Boolean(part && String(part).trim())) || t('fallbacks.effect_details_in_notes');
}

function renderCardTags(tags, limit=4){
  const values = (tags || []).filter(Boolean).slice(0, limit);
  return values.length ? `<div class='choice-card-tags'>${values.map(tag => `<span class='choice-mini-tag'>${escapeHtml(tag)}</span>`).join('')}</div>` : '';
}

function renderPowerupChoiceCard(offer, idx){
  const label = `${idx + 1}. ${offer.name}`;
  const effectLine = offer.hook || offer.plan || offer.effect || t('fallbacks.effect_details_in_notes');
  const fit = offer.relevance_hint || offer.crown_label || offer.crown_hint || '';
  const compactTags = (offer.player_tags || offer.tags || []).slice(0, 3);
  return `
    <span class='action-tile-title'>${escapeHtml(label)}</span>
    <span class='choice-card-effect'>${escapeHtml(effectLine)}</span>
    ${renderCardTags(compactTags, 3)}
    ${fit ? `<span class='choice-card-fit'>${escapeHtml(getNestedText('labels.fit'))}: ${escapeHtml(fit)}</span>` : ''}
  `;
}

function renderGenomeChoiceCard(offer, idx){
  const label = `${idx + 1}. ${offer.name}`;
  const effectLine = offer.rewrite || offer.doctrine_shift || offer.lineage_commitment || t('fallbacks.tuning_lineage_behavior');
  const tags = [offer.tempo_note, offer.stability_note, offer.doctrine_drift].filter(Boolean).slice(0, 3);
  return `
    <span class='action-tile-title'>${escapeHtml(label)}</span>
    <span class='choice-card-effect'>${escapeHtml(effectLine)}</span>
    ${renderCardTags(tags, 3)}
  `;
}

function renderFloorEventChoiceCard(response, idx){
  const label = `${idx + 1}. ${response.name}`;
  const tags = [response.duel_angle, response.vote_angle, response.dynasty_impact].filter(Boolean).slice(0, 3);
  return `
    <span class='action-tile-title'>${escapeHtml(label)}</span>
    <span class='choice-card-effect'>${escapeHtml(response.summary || t('fallbacks.not_available'))}</span>
    ${renderCardTags(tags, 3)}
  `;
}

function stableSerialize(value){
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return `[${value.map(stableSerialize).join(',')}]`;
  if (typeof value === 'object') {
    const entries = Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableSerialize(value[key])}`);
    return `{${entries.join(',')}}`;
  }
  return JSON.stringify(value);
}

function choicePayloadForSignature(decisionType, decision){
  if (!decision) return null;
  if (decisionType === 'FloorEventChoiceState') {
    return {
      floor_number: decision.floor_number || null,
      phase: decision.phase || null,
      title: decision.title || '',
      responses: decision.responses || [],
    };
  }
  if (decisionType === 'PowerupChoiceState' || decisionType === 'GenomeEditChoiceState') {
    return {
      floor_number: decision.floor_number || null,
      offers: decision.offers || [],
    };
  }
  if (decisionType === 'SuccessorChoiceState') {
    return {
      floor_number: decision.floor_number || null,
      candidates: decision.candidates || [],
    };
  }
  return null;
}

function choiceSignatureFor(decisionType, decision){
  const payload = choicePayloadForSignature(decisionType, decision);
  return `${decisionType}:${stableSerialize(payload)}`;
}

function clearPendingChoiceSelection(){
  pendingChoiceSelection = null;
}

function setPendingChoiceSelection(decisionType, choiceSignature, selectedIndex){
  pendingChoiceSelection = {decisionType, choiceSignature, selectedIndex};
}

function getPendingChoiceSelection(decisionType, choiceSignature, itemCount){
  if (!pendingChoiceSelection) return null;
  if (pendingChoiceSelection.decisionType !== decisionType || pendingChoiceSelection.choiceSignature !== choiceSignature) {
    clearPendingChoiceSelection();
    return null;
  }
  const idx = pendingChoiceSelection.selectedIndex;
  if (!Number.isInteger(idx) || idx < 0 || idx >= itemCount) {
    clearPendingChoiceSelection();
    return null;
  }
  return idx;
}

function renderChoiceSelectionPrompt(){
  return `<div class='muted decision-select-prompt'>${escapeHtml(t('messages.select_to_preview'))}</div>`;
}

function detailRow(label, value){
  if (!value) return '';
  return `<li><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</li>`;
}

function renderFloorEventChoiceDetails(decision, response, idx){
  const listItems = [
    detailRow(t('labels.pressure', 'Pressure'), decision.pressure),
    detailRow(t('labels.floor_rule', 'Floor rule'), decision.rule_text),
    detailRow(t('labels.read_quality', 'Read quality'), decision.clue_reliability),
    detailRow(t('labels.duel_angle', 'Duel angle'), response.duel_angle),
    detailRow(t('labels.vote_angle', 'Vote angle'), response.vote_angle),
    detailRow(t('labels.dynasty_impact', 'Dynasty impact'), response.dynasty_impact),
    detailRow(t('labels.offer_drift', 'Offer drift'), response.offer_drift),
    detailRow(t('labels.cost', 'Cost'), response.cost),
    detailRow(t('labels.watch_out', 'Watch out'), response.risk),
  ].filter(Boolean).join('');
  return `
    <div class='choice-details-title'>${escapeHtml(`${idx + 1}. ${response.name}`)}</div>
    <div class='muted choice-event-summary'>${escapeHtml(decision.title)} · ${escapeHtml(decision.summary)}</div>
    <ul class='list tight choice-details-list'>${listItems || `<li>${escapeHtml(t('fallbacks.not_available'))}</li>`}</ul>
    <button class='btn primary-action choice-confirm-btn' onclick="sendAction({type:'choose_floor_event', response_index:${idx}})">${escapeHtml(t('buttons.confirm_choice'))}</button>
  `;
}

function renderPowerupChoiceDetails(offer, idx){
  const listItems = [
    detailRow(t('labels.why_now', 'Why now'), offer.hook || offer.effect),
    detailRow(t('labels.when', 'When'), offer.timing || offer.trigger),
    detailRow(t('labels.plan', 'Plan'), offer.plan),
    detailRow(t('labels.cost', 'Cost'), offer.cost || offer.tradeoff),
    detailRow(t('labels.fit', 'Fit'), offer.relevance_hint),
    detailRow(t('labels.fit_detail', 'Fit detail'), offer.fit_detail),
    detailRow(t('labels.doctrine_commitment', 'Doctrine commitment'), offer.doctrine_commitment),
    detailRow(t('labels.doctrine', 'Doctrine'), offer.doctrine_vector),
    detailRow(t('labels.heir_pressure', 'Heir pressure'), offer.successor_pressure),
    detailRow(t('labels.phase', 'Phase'), offer.phase_support),
  ].filter(Boolean).join('');
  return `
    <div class='choice-details-title'>${escapeHtml(`${idx + 1}. ${offer.name}`)}</div>
    <ul class='list tight choice-details-list'>${listItems || `<li>${escapeHtml(t('fallbacks.not_available'))}</li>`}</ul>
    <button class='btn primary-action choice-confirm-btn' onclick="sendAction({type:'choose_powerup', offer_index:${idx}})">${escapeHtml(t('buttons.confirm_choice'))}</button>
  `;
}

function renderGenomeChoiceDetails(offer, idx){
  const listItems = [
    detailRow(t('labels.rewrite', 'Rewrite'), offer.rewrite || offer.description),
    detailRow(t('labels.shift', 'Shift'), offer.doctrine_shift || offer.doctrine_drift),
    detailRow(t('labels.tempo', 'Tempo'), offer.tempo_note),
    detailRow(t('labels.cost', 'Cost'), offer.stability_note || offer.tradeoff),
    detailRow(t('labels.commitment', 'Commitment'), offer.lineage_commitment),
    detailRow(t('labels.doctrine_commitment', 'Doctrine commitment'), offer.doctrine_commitment),
    detailRow(t('labels.current_build', 'Current build'), offer.current_summary),
    detailRow(t('labels.projected_build', 'Projected build'), offer.projected_summary),
  ].filter(Boolean).join('');
  return `
    <div class='choice-details-title'>${escapeHtml(`${idx + 1}. ${offer.name}`)}</div>
    <ul class='list tight choice-details-list'>${listItems || `<li>${escapeHtml(t('fallbacks.not_available'))}</li>`}</ul>
    <button class='btn primary-action choice-confirm-btn' onclick="sendAction({type:'choose_genome_edit', offer_index:${idx}})">${escapeHtml(t('buttons.confirm_choice'))}</button>
  `;
}

function renderSuccessorChoiceCard(candidate, idx){
  const headline = candidate.headline || candidate.play_pattern || t('fallbacks.not_available');
  const whyNow = candidate.why_now || candidate.attractive_now || t('fallbacks.not_available');
  const tags = [
    candidate.branch_role || t('fallbacks.unknown_role'),
    candidate.clue_confidence_label ? `${t('labels.clue_confidence', 'Clue confidence')}: ${candidate.clue_confidence_label}` : '',
    `${t('labels.score')}: ${candidate.score ?? '-'}`,
  ].filter(Boolean);
  return `
    <span class='action-tile-title'>${escapeHtml(`${idx + 1}. ${candidate.name}`)}</span>
    <span class='choice-card-effect'>${escapeHtml(headline)}</span>
    ${renderCardTags(tags, 3)}
    <span class='choice-card-fit'>${escapeHtml(`${t('labels.why_now', 'Why now')}: ${whyNow}`)}</span>
  `;
}

function renderSuccessorChoiceDetails(candidate, idx){
  const listItems = [
    detailRow(t('labels.pattern', 'Pattern'), candidate.play_pattern || (candidate.shaping_causes || [])[0]),
    detailRow(t('labels.why_now', 'Why now'), candidate.why_now || candidate.attractive_now),
    detailRow(t('labels.watch_out', 'Watch out'), candidate.watch_out || candidate.danger_later),
    detailRow(t('labels.dynasty_future', 'Dynasty future'), candidate.dynasty_future || candidate.lineage_future),
    detailRow(t('labels.doctrine_arc', 'Doctrine arc'), candidate.doctrine_arc || candidate.succession_pitch),
    detailRow(t('labels.clue_future', 'Clue future'), candidate.clue_future),
    detailRow(t('labels.clue_stability', 'Clue stability'), candidate.clue_stability),
    detailRow(t('labels.clue_confidence', 'Clue confidence'), candidate.clue_confidence || candidate.featured_inference_context || t('fallbacks.no_direct_clue_fit')),
    `<li><strong>${escapeHtml(t('labels.score'))}:</strong> ${escapeHtml(candidate.score ?? '-')} · ${escapeHtml(t('successor_comparison.labels.wins'))}: ${escapeHtml(candidate.wins ?? '-')} · ${escapeHtml(candidate.branch_role || t('fallbacks.unknown_role'))}</li>`,
  ].join('');
  return `
    <div class='choice-details-title'>${escapeHtml(`${idx + 1}. ${candidate.name}`)}</div>
    <ul class='list tight choice-details-list'>${listItems}</ul>
    <button class='btn primary-action choice-confirm-btn' onclick="sendAction({type:'choose_successor', candidate_index:${idx}})">${escapeHtml(t('buttons.confirm_choice'))}</button>
  `;
}

function renderSuccessorComparisonCard(candidate){
  return `<li class='comparison-card'>
    <div class='comparison-top'>
      <span class='comparison-name'>${escapeHtml(candidate.name)} · ${escapeHtml(candidate.branch_role || t('fallbacks.unknown_role'))}</span>
      <span class='comparison-score'>${escapeHtml(candidate.score ?? '-')} ${escapeHtml(t('successor_comparison.labels.score'))} / ${escapeHtml(candidate.wins ?? '-')} ${escapeHtml(t('successor_comparison.labels.wins'))}</span>
    </div>
    <div class='comparison-row'><span class='muted-label'>${escapeHtml(t('labels.pattern', 'Pattern'))}</span>${escapeHtml(candidate.play_pattern || candidate.headline || t('fallbacks.not_available'))}</div>
    <div class='comparison-row'><span class='muted-label'>${escapeHtml(t('labels.why_now', 'Why now'))}</span>${escapeHtml(candidate.why_now || candidate.attractive_now || t('fallbacks.not_available'))}</div>
    <div class='comparison-row'><span class='muted-label'>${escapeHtml(t('labels.watch_out', 'Watch out'))}</span>${escapeHtml(candidate.watch_out || candidate.danger_later || t('fallbacks.not_available'))}</div>
    <div class='comparison-row'><span class='muted-label'>${escapeHtml(t('labels.dynasty_future', 'Dynasty future'))}</span>${escapeHtml(candidate.dynasty_future || candidate.lineage_future || t('fallbacks.not_available'))}</div>
    <div class='comparison-row'><span class='muted-label'>${escapeHtml(t('labels.clue_confidence', 'Clue confidence'))}</span>${escapeHtml(candidate.clue_confidence || candidate.featured_inference_context || t('fallbacks.no_direct_clue_fit'))}</div>
  </li>`;
}


function getNestedText(path, fallback=''){
  return String(path.split('.').reduce((acc, part) => (acc && Object.prototype.hasOwnProperty.call(acc, part) ? acc[part] : undefined), UI_STRINGS) ?? fallback);
}

function localizeDomFromBundle(){
  const htmlValueTargets = new Set(['onboardingPoint1', 'onboardingPoint2', 'onboardingPoint3', 'onboardingPoint4', 'onboardingPoint5']);
  document.querySelectorAll('[data-i18n]').forEach(node => {
    const key = node.getAttribute('data-i18n');
    if (!key) return;
    const value = getNestedText(key, '');
    if (!value) return;
    if (htmlValueTargets.has(node.id)) {
      node.innerHTML = value;
      return;
    }
    node.textContent = value;
  });
  document.querySelectorAll('[data-i18n-title]').forEach(node => {
    const key = node.getAttribute('data-i18n-title');
    if (!key) return;
    const value = t(key, '');
    if (value) node.setAttribute('title', value);
  });
  document.querySelectorAll('[data-i18n-aria-label]').forEach(node => {
    const key = node.getAttribute('data-i18n-aria-label');
    if (!key) return;
    const value = t(key, '');
    if (value) node.setAttribute('aria-label', value);
  });
  document.title = getNestedText('app.page_title', document.title || "Prisoner's Gambit");
}

const TAB_HELP_TEXT = Object.freeze({
  summary: getNestedText('tabs.summary.help'),
  board: getNestedText('tabs.board.help'),
  chronicle: getNestedText('tabs.chronicle.help'),
  debug: getNestedText('tabs.debug.help'),
});

const GLOSSARY_TERMS = Object.freeze({
  doctrine: getNestedText('glossary.doctrine'),
  heir_pressure: getNestedText('glossary.heir_pressure'),
  civil_war_danger: getNestedText('glossary.civil_war_danger'),
  central_rival: getNestedText('glossary.central_rival'),
  controlled_vote: getNestedText('glossary.controlled_vote'),
  clue_fit: getNestedText('glossary.clue_fit'),
  lineage_direction: getNestedText('glossary.lineage_direction'),
});

const DECISION_HELP_TEXT = Object.freeze({
  FloorEventChoiceState: getNestedText('decision_help.floor_event_choice'),
  FeaturedRoundDecisionState: getNestedText('decision_help.featured_round'),
  FloorVoteDecisionState: getNestedText('decision_help.floor_vote'),
  PowerupChoiceState: getNestedText('decision_help.powerup_choice'),
  GenomeEditChoiceState: getNestedText('decision_help.genome_edit_choice'),
  SuccessorChoiceState: getNestedText('decision_help.successor_choice'),
  generic: getNestedText('decision_help.generic'),
});

function toggleInfoPanel(key, text){
  const panel = document.getElementById('glossaryPanel');
  if (!panel || !text) return;
  if (panel.dataset.term === key && panel.style.display !== 'none') {
    panel.style.display = 'none';
    panel.textContent = '';
    panel.dataset.term = '';
    return;
  }
  panel.dataset.term = key;
  panel.style.display = 'block';
  panel.textContent = text;
}

function toggleGlossaryTerm(term){
  if (!GLOSSARY_TERMS[term]) return;
  toggleInfoPanel(`glossary:${term}`, GLOSSARY_TERMS[term]);
}

function currentDecisionHelpText(){
  const decisionType = latest?.decision_type;
  if (decisionType && DECISION_HELP_TEXT[decisionType]) {
    return DECISION_HELP_TEXT[decisionType];
  }
  if (latest?.pending_screen === 'floor_summary') {
    return DECISION_HELP_TEXT.SuccessorChoiceState || DECISION_HELP_TEXT.generic;
  }
  return DECISION_HELP_TEXT.generic;
}

function toggleDecisionHelp(){
  const decisionType = latest?.decision_type || latest?.pending_screen || 'generic';
  toggleInfoPanel(`decision:${decisionType}`, currentDecisionHelpText());
}

function dismissOnboarding(){
  localStorage.setItem(ONBOARDING_DISMISSED_KEY, '1');
  const panel = document.getElementById('onboardingPanel');
  if (panel) panel.style.display = 'none';
}

function maybeShowOnboarding(){
  const dismissed = localStorage.getItem(ONBOARDING_DISMISSED_KEY) === '1';
  const panel = document.getElementById('onboardingPanel');
  if (!panel) return;
  panel.style.display = dismissed ? 'none' : 'block';
}

function shortDecisionLabel(type){
  const labels = {
    FloorEventChoiceState: getNestedText('decision_types.floor_event_choice'),
    FeaturedRoundDecisionState: getNestedText('decision_types.featured_round'),
    FloorVoteDecisionState: getNestedText('decision_types.floor_vote'),
    PowerupChoiceState: getNestedText('decision_types.powerup_choice'),
    GenomeEditChoiceState: getNestedText('decision_types.genome_edit'),
    SuccessorChoiceState: getNestedText('decision_types.successor_choice'),
  };
  return labels[type] || type || getNestedText('fallbacks.no_active_decision');
}

function hasVisibleTransitionAction(data){
  return Boolean(data?.transition_action_visible && transitionDecisionCopy(data));
}

function transitionDecisionCopy(data){
  const transitionKind = data?.transition_action_kind || '';
  if (transitionKind === 'successor_review') {
    return {
      decisionLabel: getNestedText('transition_decisions.successor_review.label'),
      helper: getNestedText('transition_decisions.successor_review.helper'),
      explanation: getNestedText('transition_decisions.successor_review.explanation'),
      actionMeta: getNestedText('transition_decisions.successor_review.action_meta'),
    };
  }
  if (transitionKind === 'reward_selection') {
    return {
      decisionLabel: getNestedText('transition_decisions.reward_selection.label'),
      helper: getNestedText('transition_decisions.reward_selection.helper'),
      explanation: getNestedText('transition_decisions.reward_selection.explanation'),
      actionMeta: getNestedText('transition_decisions.reward_selection.action_meta'),
    };
  }
  if (transitionKind === 'civil_war_start') {
    return {
      decisionLabel: getNestedText('transition_decisions.civil_war_start.label'),
      helper: getNestedText('transition_decisions.civil_war_start.helper'),
      explanation: getNestedText('transition_decisions.civil_war_start.explanation'),
      actionMeta: getNestedText('transition_decisions.civil_war_start.action_meta'),
    };
  }
  return {
    decisionLabel: getNestedText('transition_decisions.generic.label'),
    helper: getNestedText('transition_decisions.generic.helper'),
    explanation: getNestedText('transition_decisions.generic.explanation'),
    actionMeta: getNestedText('transition_decisions.generic.action_meta'),
  };
}

function setSecondaryTab(tab){
  activeSecondaryTab = tab;
  const tabs = ['summary', 'board', 'chronicle', 'debug'];
  tabs.forEach(name => {
    const btn = document.getElementById(`tab${name.charAt(0).toUpperCase()}${name.slice(1)}Btn`);
    const panel = document.getElementById(`secondaryTab${name.charAt(0).toUpperCase()}${name.slice(1)}`);
    const isActive = name === tab;
    if (btn) {
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    }
    if (panel) panel.classList.toggle('active', isActive);
  });
  const tabHelp = document.getElementById('tabHelpText');
  if (tabHelp) tabHelp.textContent = TAB_HELP_TEXT[tab] || TAB_HELP_TEXT.summary;
}

function updateContextualPanel(decisionType, snapshot){
  const panelTitle = document.getElementById('contextualPanelTitle');
  const sections = {
    round: document.getElementById('contextRoundPanel'),
    summary: document.getElementById('contextSummaryPanel'),
    successor: document.getElementById('contextSuccessorPanel'),
    reward: document.getElementById('contextRewardPanel'),
    completion: document.getElementById('contextCompletionPanel'),
  };
  Object.values(sections).forEach(section => {
    section.style.display = 'none';
  });

  if (snapshot?.completion) {
    panelTitle.textContent = getNestedText('context_panel.run_completion');
    sections.completion.style.display = 'block';
    return;
  }
  if (decisionType === 'SuccessorChoiceState') {
    panelTitle.textContent = getNestedText('context_panel.successor_options');
    sections.successor.style.display = 'block';
    return;
  }
  if (decisionType === 'PowerupChoiceState' || decisionType === 'GenomeEditChoiceState') {
    panelTitle.textContent = getNestedText('context_panel.reward_selection');
    sections.reward.style.display = 'block';
    return;
  }
  if (snapshot?.floor_summary?.entries?.length) {
    panelTitle.textContent = getNestedText('context_panel.floor_summary');
    sections.summary.style.display = 'block';
    return;
  }
  panelTitle.textContent = getNestedText('context_panel.latest_round_result');
  sections.round.style.display = 'block';
}

function renderDecision(data){
  const decision = data.decision;
  const decisionType = data.decision_type;
  const actions = document.getElementById('actions');
  const actionsPrimaryLabel = document.getElementById('actionsPrimaryLabel');
  const advanced = document.getElementById('advancedActions');
  const advancedLabel = document.getElementById('advancedActionsLabel');
  const advancedGrid = document.getElementById('advancedActionsGrid');
  const phaseActionHelper = document.getElementById('phaseActionHelper');
  const decisionView = document.getElementById('decisionView');
  actions.innerHTML = '';
  decisionView.className = 'kv muted';
  actionsPrimaryLabel.textContent = getNestedText('fallbacks.main_choice_now');
  phaseActionHelper.textContent = getNestedText('decision_helpers.generic_phase_choice');
  advancedGrid.innerHTML = '';
  advanced.open = false;
  advanced.style.display = 'none';
  document.getElementById('decisionType').textContent = decisionType ? `${getNestedText('labels.decision_prefix')} ${shortDecisionLabel(decisionType)}` : getNestedText('fallbacks.no_active_decision');
  if (!decision) {
    if (hasVisibleTransitionAction(data)) {
      const transitionCopy = transitionDecisionCopy(data);
      actionsPrimaryLabel.textContent = getNestedText('transition_decisions.primary_label');
      phaseActionHelper.textContent = transitionCopy.helper;
      document.getElementById('decisionType').textContent = `${getNestedText('labels.decision_prefix')} ${transitionCopy.decisionLabel}`;
      decisionView.innerHTML = escapeHtml(transitionCopy.explanation);
      actions.innerHTML = `<button class='btn primary-action' onclick='advanceFlow()'>${actionTile(transitionCopy.decisionLabel, transitionCopy.actionMeta)}</button>`;
      return;
    }
    actionsPrimaryLabel.textContent = '';
    phaseActionHelper.textContent = '';
    decisionView.innerHTML = getNestedText('fallbacks.no_active_decision');
    return;
  }

  if (decisionType === 'FloorEventChoiceState') {
    actionsPrimaryLabel.textContent = getNestedText('labels.choose_response');
    phaseActionHelper.textContent = getNestedText('decision_helpers.floor_event_choice');
    const choiceSignature = choiceSignatureFor(decisionType, decision);
    const selectedIdx = getPendingChoiceSelection(decisionType, choiceSignature, decision.responses.length);
    decisionView.className = 'muted choice-details-surface';
    decisionView.innerHTML = selectedIdx === null
      ? renderChoiceSelectionPrompt()
      : renderFloorEventChoiceDetails(decision, decision.responses[selectedIdx], selectedIdx);
    decision.responses.forEach((response, idx) => {
      const btn = document.createElement('button');
      btn.className = `btn action-tile-secondary choice-option ${selectedIdx === idx ? 'choice-option-selected' : ''}`;
      btn.innerHTML = renderFloorEventChoiceCard(response, idx);
      btn.title = [response.duel_angle, response.vote_angle, response.dynasty_impact, response.offer_drift, response.risk].filter(Boolean).join(' | ');
      btn.onclick = () => {
        setPendingChoiceSelection(decisionType, choiceSignature, idx);
        renderDecision(data);
      };
      actions.appendChild(btn);
    });
    return;
  }

  if (decisionType === 'FeaturedRoundDecisionState') {
    const p = decision.prompt;
    const clues = (p.clue_channels || []).map(c => `<li>${escapeHtml(c)}</li>`).join('') || `<li class="muted">${escapeHtml(t('fallbacks.no_explicit_clues'))}</li>`;
    const floorLog = (p.floor_clue_log || []).slice(-3).map(c => `<li>${escapeHtml(c)}</li>`).join('') || `<li class="muted">${escapeHtml(t('fallbacks.no_prior_featured_clues'))}</li>`;
    decisionView.innerHTML = `
      <div>${escapeHtml(t('labels.next_pick'))}</div><div>${effectToken(`${t('labels.autopilot')}: ${moveLabel(p.suggested_move)}`)}</div>
      <div>${escapeHtml(t('labels.round'))}</div><div>${p.round_index + 1}/${p.total_rounds}</div>
      <div>${escapeHtml(t('labels.score'))}</div><div class='scoreline'>${escapeHtml(t('labels.you'))} <span class='good'>${p.my_match_score}</span> : <span class='danger'>${p.opp_match_score}</span> ${escapeHtml(t('labels.opponent_short'))}</div>
      <div>${escapeHtml(t('labels.rival'))}</div><div>${branchToken(p.masked_opponent_label)}</div>
      <div>${escapeHtml(t('labels.read_on_rival'))}</div><div>${escapeHtml(p.inference_focus || t('fallbacks.pattern_check'))}</div>
      <div>${escapeHtml(t('labels.live_clues'))}</div><div><ul class='list tight'>${clues}</ul></div>
      <div>${escapeHtml(t('labels.recent_floor_notes'))}</div><div><ul class='list tight'>${floorLog}</ul></div>`;
    phaseActionHelper.textContent = getNestedText('decision_helpers.featured_round');
    actions.innerHTML = `
      <button class='btn ${p.suggested_move === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'C'})">${actionTile(t('actions.cooperate'), t('actions.manual_move_primary'))}</button>
      <button class='btn ${p.suggested_move === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_move', move:'D'})">${actionTile(t('actions.defect'), t('actions.manual_move_primary'))}</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_round'})">${actionTile(t('actions.autopilot'), `${t('actions.recommended')} · ${moveLabel(p.suggested_move)}`)}</button>`;
    advanced.style.display = 'block';
    advancedLabel.textContent = getNestedText('labels.advanced_tactic_setup');
    advancedGrid.innerHTML = `
      <button class='btn action-tile-secondary' onclick="sendAction({type:'set_round_stance', stance:'cooperate_until_betrayed'})">${actionTile(t('actions.c_until_betrayed'), t('actions.stance'))}</button>
      <button class='btn action-tile-secondary' onclick="sendAction({type:'set_round_stance', stance:'defect_until_punished'})">${actionTile(t('actions.d_until_punished'), t('actions.stance'))}</button>
      <button class='btn action-tile-secondary' onclick="sendStanceN('follow_autopilot_for_n_rounds')">${actionTile(t('actions.autopilot_n'), t('actions.stance_with_duration'))}</button>
      <button class='btn action-tile-secondary' onclick="sendStanceN('lock_last_manual_move_for_n_rounds')">${actionTile(t('actions.lock_last_n'), t('actions.stance_with_duration'))}</button>`;
    return;
  }

  if (decisionType === 'FloorVoteDecisionState') {
    actionsPrimaryLabel.textContent = getNestedText('fallbacks.main_choice_now');
  phaseActionHelper.textContent = getNestedText('decision_helpers.floor_vote');
    const p = decision.prompt;
    decisionView.innerHTML = `
      <div>${escapeHtml(t('labels.floor'))}</div><div>${p.floor_number} (${escapeHtml(p.floor_label)})</div>
      <div>${escapeHtml(t('labels.next_pick'))}</div><div>${effectToken(`${t('labels.autopilot')}: ${moveLabel(p.suggested_vote)}`)}</div>
      <div>${escapeHtml(t('labels.floor_score'))}</div><div>${p.current_floor_score}</div>
      <div>${escapeHtml(t('labels.powerups'))}</div><div>${compactTokenPreview(p.powerups || [], powerupToken, 3, t('fallbacks.none'))}</div>`;
    actions.innerHTML = `
      <button class='btn ${p.suggested_vote === 0 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'C'})">${actionTile(t('actions.vote_cooperate'), t('actions.manual_vote_primary'))}</button>
      <button class='btn ${p.suggested_vote === 1 ? 'primary-action' : ''}' onclick="sendAction({type:'manual_vote', vote:'D'})">${actionTile(t('actions.vote_defect'), t('actions.manual_vote_primary'))}</button>
      <button class='btn primary-action' onclick="sendAction({type:'autopilot_vote'})">${actionTile(t('actions.autopilot_vote'), `${t('actions.recommended')} · ${moveLabel(p.suggested_vote)}`)}</button>`;
    return;
  }

  if (decisionType === 'PowerupChoiceState') {
    actionsPrimaryLabel.textContent = getNestedText('labels.choose_one_offer');
    phaseActionHelper.textContent = getNestedText('decision_helpers.powerup_choice');
    const choiceSignature = choiceSignatureFor(decisionType, decision);
    const selectedIdx = getPendingChoiceSelection(decisionType, choiceSignature, decision.offers.length);
    decisionView.className = 'muted choice-details-surface';
    decisionView.innerHTML = selectedIdx === null
      ? renderChoiceSelectionPrompt()
      : renderPowerupChoiceDetails(decision.offers[selectedIdx], selectedIdx);
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = `btn action-tile-secondary choice-option ${selectedIdx === idx ? 'choice-option-selected' : ''}`;
      btn.innerHTML = renderPowerupChoiceCard(offer, idx);
      btn.title = [offer.hook, offer.plan, offer.cost, offer.doctrine_commitment, offer.fit_detail].filter(Boolean).join(' | ');
      btn.onclick = () => {
        setPendingChoiceSelection(decisionType, choiceSignature, idx);
        renderDecision(data);
      };
      actions.appendChild(btn);
    });
    return;
  }

  if (decisionType === 'GenomeEditChoiceState') {
    actionsPrimaryLabel.textContent = getNestedText('labels.choose_one_offer');
    phaseActionHelper.textContent = getNestedText('decision_helpers.genome_edit_choice');
    const choiceSignature = choiceSignatureFor(decisionType, decision);
    const selectedIdx = getPendingChoiceSelection(decisionType, choiceSignature, decision.offers.length);
    decisionView.className = 'muted choice-details-surface';
    decisionView.innerHTML = selectedIdx === null
      ? renderChoiceSelectionPrompt()
      : renderGenomeChoiceDetails(decision.offers[selectedIdx], selectedIdx);
    decision.offers.forEach((offer, idx) => {
      const btn = document.createElement('button');
      btn.className = `btn action-tile-secondary choice-option ${selectedIdx === idx ? 'choice-option-selected' : ''}`;
      btn.innerHTML = renderGenomeChoiceCard(offer, idx);
      btn.title = [offer.rewrite, offer.doctrine_shift, offer.tempo_note, offer.stability_note, offer.doctrine_commitment].filter(Boolean).join(' | ');
      btn.onclick = () => {
        setPendingChoiceSelection(decisionType, choiceSignature, idx);
        renderDecision(data);
      };
      actions.appendChild(btn);
    });
    return;
  }

  if (decisionType === 'SuccessorChoiceState') {
    actionsPrimaryLabel.textContent = getNestedText('labels.choose_next_host');
    phaseActionHelper.textContent = getNestedText('decision_helpers.successor_choice');
    const choiceSignature = choiceSignatureFor(decisionType, decision);
    const selectedIdx = getPendingChoiceSelection(decisionType, choiceSignature, decision.candidates.length);
    decisionView.className = 'muted choice-details-surface';
    decisionView.innerHTML = selectedIdx === null
      ? renderChoiceSelectionPrompt()
      : renderSuccessorChoiceDetails(decision.candidates[selectedIdx], selectedIdx);
    decision.candidates.forEach((candidate, idx) => {
      const btn = document.createElement('button');
      btn.className = `btn action-tile-secondary choice-option ${selectedIdx === idx ? 'choice-option-selected' : ''}`;
      btn.innerHTML = renderSuccessorChoiceCard(candidate, idx);
      btn.title = [candidate.headline, candidate.play_pattern, candidate.why_now, candidate.watch_out, candidate.dynasty_future].filter(Boolean).join(' | ');
      btn.onclick = () => {
        setPendingChoiceSelection(decisionType, choiceSignature, idx);
        renderDecision(data);
      };
      actions.appendChild(btn);
    });
    return;
  }
}

function renderRoundEffects(round) {
  const root = document.getElementById('roundEffects');
  if (!round) {
    root.innerHTML = '';
    return;
  }
  const modifiers = round.breakdown?.score_adjustments || [];
  const modifierLines = modifiers.length
    ? modifiers.map(entry => `<div class='fx-item'>${powerupToken(entry.source)} → ${t('round_effects.labels.you')} ${entry.player_delta >= 0 ? '+' : ''}${entry.player_delta}, ${t('round_effects.labels.opp')} ${entry.opponent_delta >= 0 ? '+' : ''}${entry.opponent_delta}</div>`).join('')
    : `<div class='fx-item muted'>${escapeHtml(t('round_result.empty.no_score_modifiers'))}</div>`;
  root.innerHTML = `
    <div class='fx-item'>${effectToken(`${t('round_result.labels.directive_you')} ${round.player_reason}`)}</div>
    <div class='fx-item'>${effectToken(`${t('round_result.labels.directive_opp')} ${round.opponent_reason}`)}</div>
    ${modifierLines}`;
}

function renderSnapshot(snapshot){
  document.getElementById('phase').textContent = t('status_formats.phase', '{label}: {value}').replace('{label}', t('status_labels.phase')).replace('{value}', String(snapshot.current_phase || '-')); 
  document.getElementById('floor').textContent = t('status_formats.floor', '{label}: {value}').replace('{label}', t('status_labels.floor')).replace('{value}', String(snapshot.current_floor || '-')); 

  const stance = snapshot.active_featured_stance;
  document.getElementById('activeStance').textContent = stance
    ? t('status_formats.stance_active', '{label}: {stance} ({rounds})').replace('{label}', t('status_labels.stance')).replace('{stance}', String(stance.stance)).replace('{rounds}', String(stance.rounds_remaining ?? '∞'))
    : t('status_formats.stance_none', '{label}: none').replace('{label}', t('status_labels.stance'));

  const round = snapshot.latest_featured_round;
  const roundResult = document.getElementById('roundResult');
  if (round) {
    const totals = `${round.player_total}:${round.opponent_total}`;
    const deltaClass = previousTotals && previousTotals !== totals ? 'score-pop' : '';
    roundResult.className = deltaClass;
    previousTotals = totals;
    roundResult.innerHTML = `
      <div class='kv'>
        <div>${escapeHtml(t('round_result.labels.round'))}</div><div>${round.round_index + 1}/${round.total_rounds}</div>
        <div>${escapeHtml(t('round_result.labels.moves'))}</div><div>${escapeHtml(t('round_result.labels.you_short'))} ${moveLabel(round.player_move)} ${escapeHtml(t('round_result.labels.vs'))} ${escapeHtml(t('round_result.labels.opp_short'))} ${moveLabel(round.opponent_move)}</div>
        <div>${escapeHtml(t('round_result.labels.round_delta'))}</div><div><span class='good'>${round.player_delta >= 0 ? '+' : ''}${round.player_delta}</span> / <span class='danger'>${round.opponent_delta >= 0 ? '+' : ''}${round.opponent_delta}</span></div>
        <div>${escapeHtml(t('round_result.labels.match_total'))}</div><div class='scoreline'><span class='good'>${round.player_total}</span> : <span class='danger'>${round.opponent_total}</span></div>
      </div>`;
  } else {
    roundResult.className = 'muted';
    roundResult.textContent = t('fallbacks.no_rounds_resolved');
  }
  renderRoundEffects(round);

  const vote = snapshot.floor_vote_result;
  document.getElementById('voteResult').innerHTML = vote
    ? `${effectToken(`${t('vote_result.labels.vote')} ${moveLabel(vote.player_vote)}`)} — ${t('vote_result.labels.cooperators')} ${vote.cooperators}, ${t('vote_result.labels.defectors')} ${vote.defectors}, ${t('vote_result.labels.reward')} <span class='good'>+${vote.player_reward}</span>`
    : t('vote_result.empty.no_vote_yet');

  const capLines = (items, limit=2) => (items || []).slice(0, limit);
  const strategic = snapshot.strategic_snapshot;
  document.getElementById('strategicSnapshotHeadline').textContent = strategic?.headline || t('strategic_snapshot.empty.no_snapshot');
  document.getElementById('strategicSnapshotChips').innerHTML = strategic
    ? (strategic.chips || []).map(chip => effectToken(chip)).join('')
    : '';
  document.getElementById('strategicSnapshotDetails').innerHTML = strategic
    ? (strategic.details || []).slice(0, 2).map(line => `<li>${escapeHtml(line)}</li>`).join('')
    : `<li>${escapeHtml(t('strategic_snapshot.empty.no_snapshot'))}</li>`;

  const floorIdentity = snapshot.floor_identity;
  document.getElementById('floorIdentityHeadline').textContent = floorIdentity
    ? floorIdentity.headline
    : t('floor_identity.empty.no_identity');
  document.getElementById('floorIdentity').innerHTML = floorIdentity
    ? `
      <li><strong>${escapeHtml(t('floor_identity.labels.dominant_pressure'))}</strong>: ${escapeHtml(floorIdentity.dominant_pressure)}</li>
      <li><strong>${escapeHtml(t('floor_identity.labels.why_it_matters'))}</strong>: ${escapeHtml(floorIdentity.pressure_reason)}</li>
      <li><strong>${escapeHtml(t('floor_identity.labels.lineage_direction'))}</strong>: ${escapeHtml(floorIdentity.lineage_direction)}</li>
      <li><strong>${escapeHtml(t('floor_identity.labels.focus_this_floor'))}</strong>: ${escapeHtml(floorIdentity.strategic_focus)}</li>
      <li><strong>${escapeHtml(t('floor_identity.labels.host'))}</strong>: ${branchToken(floorIdentity.host_name)} · F${escapeHtml(floorIdentity.target_floor)}</li>`
    : `<li>${escapeHtml(t('floor_identity.empty.no_identity'))}</li>`;

  const summary = snapshot.floor_summary?.entries || [];
  const pressure = snapshot.floor_summary?.heir_pressure;
  const featuredInference = snapshot.floor_summary?.featured_inference_summary || [];
  const civilWar = snapshot.civil_war_context;
  const successorPreview = capLines(pressure?.successor_candidates || [], PANEL_LIMITS.floorHeirs).map(entry =>
    `<li>${branchToken(entry.name)} ${escapeHtml(entry.branch_role)} · <span class='muted'>${escapeHtml((entry.shaping_causes || [entry.rationale])[0] || entry.rationale)}</span></li>`
  ).join('');
  const threatPreview = capLines(pressure?.future_threats || [], PANEL_LIMITS.floorThreats).map(entry =>
    `<li>${branchToken(entry.name)} ${escapeHtml(entry.branch_role)} · <span class='muted'>${escapeHtml((entry.shaping_causes || [entry.rationale])[0] || entry.rationale)}</span></li>`
  ).join('');
  const featuredLead = capLines(featuredInference, 1).map(line => `<li>${escapeHtml(line)}</li>`).join('') || `<li class="muted">${escapeHtml(t('floor_summary.empty.no_solid_clue_read'))}</li>`;
  const pressureBlock = pressure
    ? `<li><strong>${escapeHtml(t('floor_summary.labels.succession_trend'))}</strong>: ${escapeHtml(pressure.branch_doctrine)}</li>`
      + `<li><strong>${escapeHtml(t('floor_summary.labels.best_heir_lead'))}</strong><ul>${successorPreview || `<li class="muted">${escapeHtml(t('floor_summary.empty.no_clear_heir'))}</li>`}</ul></li>`
      + `<li><strong>${escapeHtml(t('floor_summary.labels.main_threat'))}</strong><ul>${threatPreview || `<li class="muted">${escapeHtml(t('floor_summary.empty.no_outside_pressure'))}</li>`}</ul></li>`
    : '';
  const civilWarBlock = civilWar
    ? `<li><strong>${escapeHtml(t('floor_summary.labels.conflict'))}</strong>: ${escapeHtml(civilWar.thesis)}</li>`
      + `<li><strong>${escapeHtml(t('floor_summary.labels.key_rules'))}</strong><ul>${capLines(civilWar.scoring_rules || [], PANEL_LIMITS.rules).map(rule => `<li>${escapeHtml(rule)}</li>`).join('') || `<li class="muted">${escapeHtml(t('floor_summary.empty.no_active_score_rules'))}</li>`}</ul></li>`
      + `<li><strong>${escapeHtml(t('floor_summary.labels.main_pressure'))}</strong>: ${escapeHtml(capLines(civilWar.dangerous_branches || [], 1).join(' · ') || t('floor_summary.empty.unknown'))}</li>`
    : '';
  const floorSummaryFull = summary.length
    ? summary.slice(0, PANEL_LIMITS.floorLeaders).map(entry => {
        const continuity = entry.survived_previous_floor ? `↺F${entry.continuity_streak}` : t('fallbacks.new');
        const trend = entry.pressure_trend === 'rising' ? '↗' : (entry.pressure_trend === 'falling' ? '↘' : '→');
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} <span class='muted'>${escapeHtml(entry.descriptor)}</span> · <span class='good'>${entry.score}</span> ${escapeHtml(t('labels.points_short'))} · ${movementGlyph(entry.score_delta || 0)}S ${movementGlyph(entry.wins_delta || 0)}W · ${continuity} · P${trend}</li>`;
      }).join('') + `<li><strong>${escapeHtml(t('floor_summary.labels.featured_read'))}</strong><ul>${featuredLead}</ul></li>` + pressureBlock + civilWarBlock
    : `<li>${escapeHtml(t('fallbacks.no_summary_yet'))}</li>`;
  const floorSummaryPrimary = summary.length
    ? summary.slice(0, 2).map(entry => `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} <span class='good'>${entry.score}</span> ${escapeHtml(t('labels.points_short'))} · <span class='muted'>${escapeHtml(entry.descriptor)}</span></li>`).join('')
      + `<li class='context-note'>${escapeHtml(t('hints.summary_tab_context'))}</li>`
    : `<li>${escapeHtml(t('fallbacks.no_summary_yet'))}</li>`;
  document.getElementById('floorSummaryFull').innerHTML = floorSummaryFull;
  document.getElementById('floorSummaryPrimary').innerHTML = floorSummaryPrimary;

  const successors = snapshot.successor_options?.candidates || [];
  const successorState = snapshot.successor_options;
  const successorContext = successorState
    ? `<li><strong>${escapeHtml(t('successor_preview.labels.why_this_choice_matters'))}</strong>: ${escapeHtml(successorState.current_phase || t('successor_preview.empty.unknown'))} ${t('successor_preview.labels.phase')} ${t('successor_preview.labels.pressure')} ${escapeHtml(successorState.civil_war_pressure || t('successor_preview.empty.unknown'))}</li>`
      + `<li><strong>${escapeHtml(t('successor_preview.labels.main_threats'))}</strong>: ${escapeHtml(capLines(successorState.threat_profile || [], 2).join(', ') || t('fallbacks.none'))}</li>`
      + `<li><strong>${escapeHtml(t('successor_preview.labels.clue_memory'))}</strong>: ${escapeHtml((successorState.featured_inference_summary || [])[0] || t('successor_preview.empty.no_clue_memory'))}</li>`
    : '';
  const successorPrimary = successors.length
    ? successors.slice(0, PANEL_LIMITS.successorCards).map(candidate => {
        const topCause = (candidate.shaping_causes || [])[0] || candidate.succession_pitch;
        return `<li>${branchToken(candidate.name)} · ${escapeHtml(candidate.branch_role)} · ${candidate.score} ${escapeHtml(t('labels.points_short'))}<br/><span class='muted'>${escapeHtml(topCause)}</span></li>`;
      }).join('') + `<li class='context-note'>${t('successor_preview.hints.open_summary_successor_comparison')}</li>`
    : `${successorContext}<li>${escapeHtml(getNestedText('messages.no_successor_choice'))}</li>`;
  document.getElementById('successorsPrimary').innerHTML = successorPrimary;

  const successorComparisonSection = document.getElementById('successorComparisonSection');
  const successorComparison = document.getElementById('successorComparison');
  const activeSuccessorDecision = latest?.decision_type === 'SuccessorChoiceState' ? latest?.decision : null;
  const comparisonCandidates = activeSuccessorDecision?.candidates || successors;
  if (latest?.decision_type === 'SuccessorChoiceState' && comparisonCandidates.length) {
    successorComparisonSection.style.display = 'block';
    successorComparison.innerHTML = comparisonCandidates.map(renderSuccessorComparisonCard).join('');
  } else {
    successorComparisonSection.style.display = 'none';
    successorComparison.innerHTML = `<li>${escapeHtml(getNestedText('messages.no_successor_choice'))}</li>`;
  }

  const rewardContext = document.getElementById('rewardContext');
  if (latest?.decision_type === 'PowerupChoiceState') {
    rewardContext.innerHTML = `${effectToken(getNestedText('messages.powerup_choice_active'))} ${escapeHtml(getNestedText('messages.pick_one_offer'))} <div class='context-note'>${escapeHtml(getNestedText('hints.summary_tab_choose'))}</div>`;
  } else if (latest?.decision_type === 'GenomeEditChoiceState') {
    rewardContext.innerHTML = `${effectToken(getNestedText('messages.genome_edit_active'))} ${escapeHtml(getNestedText('messages.pick_one_genome'))} <div class='context-note'>${escapeHtml(getNestedText('hints.summary_tab_choose'))}</div>`;
  } else {
    rewardContext.textContent = getNestedText('fallbacks.no_reward_choice_active');
  }

  const dynastyEntries = snapshot.dynasty_board?.entries || [];
  document.getElementById('dynastyBoard').innerHTML = dynastyEntries.length
    ? dynastyEntries.map(entry => {
        const markerTokens = [
          entry.is_current_host ? effectToken(t('marker_labels.you')) : '',
          entry.has_successor_pressure ? effectToken(t('marker_labels.heir')) : '',
          entry.has_civil_war_danger ? effectToken(t('marker_labels.risk')) : '',
          entry.is_central_rival ? effectToken(entry.is_new_central_rival ? t('marker_labels.new_rival') : t('marker_labels.rival')) : '',
        ].filter(Boolean);
        const markerCauses = [
          entry.has_successor_pressure && entry.successor_pressure_cause ? `${t('marker_labels.heir_prefix')} ${escapeHtml(cleanCauseLine(entry.successor_pressure_cause))}` : '',
          entry.has_civil_war_danger && entry.civil_war_danger_cause ? `${t('marker_labels.risk_prefix')} ${escapeHtml(cleanCauseLine(entry.civil_war_danger_cause))}` : '',
        ].filter(Boolean);
        const markerBlock = markerTokens.length
          ? `${markerTokens.join(' ')}${markerCauses.length ? `<br/><span class="muted">${markerCauses.slice(0, 2).join(' · ')}</span>` : ''}`
          : `<span class="muted">${escapeHtml(t('dynasty_board.empty.no_active_markers'))}</span>`;
        const continuity = entry.survived_previous_floor ? `↺F${entry.continuity_streak}` : t('fallbacks.new');
        const trend = entry.pressure_trend === 'rising' ? '↗' : (entry.pressure_trend === 'falling' ? '↘' : '→');
        const perkPreview = compactTokenPreview(entry.visible_powerups || [], powerupToken, 2, '');
        const perkLine = perkPreview ? `<br/><span class='muted'>${escapeHtml(t('dynasty_board.labels.perks'))} ${perkPreview}</span>` : '';
        return `<li>${branchToken(entry.name)} ${relationToken(entry.lineage_relation)} · ${escapeHtml(entry.role)} · ${escapeHtml(t('dynasty_board.labels.score'))} ${entry.score} (${movementGlyph(entry.score_delta || 0)}S, ${movementGlyph(entry.wins_delta || 0)}W) · ${continuity} · P${trend} · ${escapeHtml(t('dynasty_board.labels.depth'))} ${entry.lineage_depth}<br/>${markerBlock}${perkLine}</li>`;
      }).join('')
    : `<li>${escapeHtml(getNestedText('fallbacks.no_lineage_board'))}</li>`;

  const completion = snapshot.completion;
  document.getElementById('completion').innerHTML = completion
    ? `${effectToken(completion.outcome.toUpperCase())} ${t('completion.labels.on_floor')} ${completion.floor_number} ${t('completion.labels.as')} ${branchToken(completion.player_name)}`
    : getNestedText('fallbacks.run_in_progress');

  const chronicle = snapshot.lineage_chronicle || [];
  const chronicleLabels = {
    run_start: t('chronicle_labels.run_start'),
    floor_complete: t('chronicle_labels.floor_complete'),
    doctrine_pivot: t('chronicle_labels.doctrine_pivot'),
    successor_pressure: t('chronicle_labels.successor_pressure'),
    successor_choice: t('chronicle_labels.successor_choice'),
    phase_transition: t('chronicle_labels.phase_transition'),
    civil_war_round_start: t('chronicle_labels.civil_war_round_start'),
    run_outcome: t('chronicle_labels.run_outcome'),
  };
  document.getElementById('chronicle').innerHTML = chronicle.length
    ? chronicle.slice(-PANEL_LIMITS.chronicleEntries).reverse().map(entry => `<li><strong>${escapeHtml(chronicleLabels[entry.event_type] || entry.event_type.replaceAll('_', ' '))}</strong> · F${escapeHtml(entry.floor_number ?? '-')} · ${escapeHtml(entry.summary)}${entry.cause ? `<br/><span class='muted'>${escapeHtml(cleanCauseLine(entry.cause))}</span>` : ''}</li>`).join('')
    : `<li>${escapeHtml(getNestedText('fallbacks.no_lineage_events'))}</li>`;

  const pending = latest?.pending_message ? `${t('labels.next_action')}: ${latest.pending_message}` : '';
  document.getElementById('pending').textContent = pending;

  const advanceBtn = document.getElementById('advanceBtn');
  const transitionCopy = transitionDecisionCopy(latest);
  const transitionVisible = hasVisibleTransitionAction(latest);
  advanceBtn.style.display = transitionVisible ? 'inline-flex' : 'none';
  advanceBtn.textContent = transitionVisible ? transitionCopy.decisionLabel : getNestedText('buttons.continue_next_phase');

  updateContextualPanel(latest?.decision_type || null, snapshot);
}

async function refresh(){
  const response = await fetch('/api/state');
  latest = await response.json();
  document.getElementById('status').textContent = t('status_formats.status', '{label}: {value}').replace('{label}', t('status_labels.status')).replace('{value}', String(latest.status));
  renderDecision(latest);
  renderSnapshot(latest.snapshot || {});
  setSecondaryTab(activeSecondaryTab || 'summary');
  document.getElementById('stateJson').textContent = JSON.stringify(latest, null, 2);
  await autosaveFromServer();
}

function setSaveNotice(message){
  const notice = document.getElementById('saveNotice');
  if (notice) notice.textContent = message;
}

function getSavedSaveCode(){
  const raw = localStorage.getItem(SAVE_STORAGE_KEY);
  if (!raw) return null;
  return typeof raw === 'string' && raw.length > 0 ? raw : null;
}

function setSavedSaveCode(saveCode){
  localStorage.setItem(SAVE_STORAGE_KEY, saveCode);
}

function clearSavedRun(){
  localStorage.removeItem(SAVE_STORAGE_KEY);
  document.getElementById('resumePanel').style.display = 'none';
  setSaveNotice(getNestedText('saved_run.messages.cleared'));
}

async function autosaveFromServer(){
  if (!latest || latest.status === 'not_started') return;
  const response = await fetch('/api/run/export', {method:'POST'});
  if (!response.ok) return;
  const payload = await response.json();
  if (payload && payload.save_code) {
    setSavedSaveCode(payload.save_code);
    setSaveNotice(getNestedText('saved_run.messages.autosaved'));
  }
}

async function restoreSavedCode(saveCode){
  clearPendingChoiceSelection();
  await fetch('/api/run/import', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({save_code: saveCode}),
  });
  await refresh();
}

async function resumeSavedRun(){
  const saveCode = getSavedSaveCode();
  if (!saveCode) {
    setSaveNotice(getNestedText('saved_run.messages.not_found'));
    return;
  }
  await restoreSavedCode(saveCode);
  document.getElementById('resumePanel').style.display = 'none';
  setSaveNotice(getNestedText('saved_run.messages.resumed'));
}

async function startNewRunFromPrompt(){
  await startRun();
  setSaveNotice(getNestedText('saved_run.messages.new_run_started'));
  document.getElementById('resumePanel').style.display = 'none';
}

async function startRun(){
  clearPendingChoiceSelection();
  await fetch('/api/run/start', {method:'POST'});
  await refresh();
}
async function clearRun(){
  clearPendingChoiceSelection();
  await fetch('/api/run/clear', {method:'POST'});
  clearSavedRun();
  latest = null;
  previousTotals = null;
  await refresh();
}
async function advanceFlow(){
  clearPendingChoiceSelection();
  await fetch('/api/advance', {method:'POST'});
  await refresh();
}
async function sendAction(payload){
  if (payload?.type && String(payload.type).startsWith('choose_')) clearPendingChoiceSelection();
  await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
  await refresh();
}
async function exportSaveCode(){
  const response = await fetch('/api/run/export', {method:'POST'});
  if (!response.ok) return;
  const payload = await response.json();
  if (!payload.save_code) return;
  prompt(getNestedText('prompts.copy_save_code'), payload.save_code);
}
async function importSaveCode(){
  const code = prompt(getNestedText('prompts.paste_save_code'));
  if (!code) return;
  clearPendingChoiceSelection();
  const response = await fetch('/api/run/import', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({save_code: code.trim()}),
  });
  if (!response.ok) {
    setSaveNotice(getNestedText('saved_run.messages.invalid_code'));
    return;
  }
  await refresh();
}
async function sendStanceN(stance){
  const raw = prompt(getNestedText('prompts.rounds_n'), '2');
  const rounds = Number.parseInt(raw || '0', 10);
  if (!Number.isFinite(rounds) || rounds <= 0) return;
  await sendAction({type:'set_round_stance', stance, rounds});
}

window.addEventListener('load', async () => {
  localizeDomFromBundle();
  maybeShowOnboarding();
  const saved = getSavedSaveCode();
  if (saved) {
    document.getElementById('resumePanel').style.display = 'block';
    setSaveNotice(getNestedText('saved_run.messages.local_autosave_available'));
    return;
  }
  await refresh();
});
