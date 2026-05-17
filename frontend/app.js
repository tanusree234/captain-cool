/**
 * Captain Cool — Full Dashboard Frontend
 * SSE streaming, live scorecard, debate transcript, multi-perspective commentary
 */
const API = window.location.origin;

// ── DOM ──────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const inputPanel = $('input-panel');
const dashboard = $('dashboard');
const matchForm = $('match-form');
const submitBtn = $('submit-btn');
const backBtn = $('back-btn');
const debateContent = $('debate-content');
const debateToggle = $('debate-toggle');
const intelToggle = $('intel-toggle');
const intelContent = $('intel-content');

const steps = {
    stats: $('step-stats'),
    conditions: $('step-conditions'),
    debate: $('step-debate'),
    reflection: $('step-reflection'),
    commentary: $('step-commentary'),
};

// Scorecard update fields
const scFields = ['innings','over','ball','runs','wickets','target','batting-team','bowling-team','striker','non-striker'];

// ── Live Scorecard Preview ───────────────────────────────────
function updateScorecardPreview() {
    const runs = +$('runs').value || 0;
    const wkts = +$('wickets').value || 0;
    const over = +$('over').value || 0;
    const ball = +$('ball').value || 0;
    const target = +$('target').value || 0;
    const inn = +$('innings').value;
    const batTeam = $('batting-team').value;

    $('sc-bat-team').textContent = batTeam;
    $('sc-score').textContent = `${runs}/${wkts}`;
    $('sc-overs').textContent = `(${over}.${ball} ov)`;
    $('sc-striker-name').textContent = $('striker').value.split(' ').pop();
    $('sc-nonstriker-name').textContent = $('non-striker').value.split(' ').pop();

    const targetRow = $('sc-target-row');
    if (inn === 2 && target > 0) {
        targetRow.style.display = 'flex';
        const need = target - runs;
        const ballsLeft = (20 - over) * 6 - ball;
        const rrr = ballsLeft > 0 ? ((need / ballsLeft) * 6).toFixed(2) : '∞';
        $('sc-need').textContent = need;
        $('sc-balls').textContent = ballsLeft;
        $('sc-rrr').textContent = rrr;
    } else {
        targetRow.style.display = 'none';
    }
}

scFields.forEach(id => {
    const el = $(id);
    if (el) el.addEventListener('input', updateScorecardPreview);
    if (el) el.addEventListener('change', updateScorecardPreview);
});
updateScorecardPreview();

// ── Form Submit ──────────────────────────────────────────────
matchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = buildMessage();
    showDashboard();
    updateDashScorecard();

    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').style.display = 'none';
    submitBtn.querySelector('.btn-loading').style.display = 'inline';

    try {
        await runPipeline(msg);
    } catch (err) {
        $('captain-call-panel').style.display = 'block';
        $('captain-call-body').innerHTML = `<span style="color:var(--accent-red)">⚠️ ${esc(err.message)}</span><br><br><span style="color:var(--text-muted)">Make sure the server is running: <code>python server.py</code></span>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').style.display = 'inline';
        submitBtn.querySelector('.btn-loading').style.display = 'none';
    }
});

function showDashboard() {
    inputPanel.style.display = 'none';
    dashboard.style.display = 'block';
    debateContent.innerHTML = '<div class="debate-placeholder"><p>⏳ Agents assembling...</p></div>';
    // Reset panels
    ['captain-call-panel','confidence-panel','commentary-panel','extras-panel'].forEach(id => $(id).style.display = 'none');
    $('stats-report-text').textContent = 'Waiting...';
    $('conditions-report-text').textContent = 'Waiting...';
    $('comm-for').innerHTML = '';
    $('comm-against').innerHTML = '';
    $('comm-neutral').innerHTML = '';
    // Reset pipeline
    Object.values(steps).forEach(s => { s.classList.remove('active','done'); s.querySelector('.step-status').textContent = 'waiting'; });
    $('debate-round-indicator').textContent = '';
}

function updateDashScorecard() {
    $('ds-team').textContent = $('batting-team').value;
    $('ds-score').textContent = `${$('runs').value}/${$('wickets').value}`;
    $('ds-overs').textContent = `(${$('over').value}.${$('ball').value})`;
    $('ds-bowl-team').textContent = $('bowling-team').value;
    const t = +$('target').value;
    $('ds-target').textContent = t > 0 ? `Target: ${t}` : '1st Innings';
}

// ── Build Message ────────────────────────────────────────────
function buildMessage() {
    const s = f => $(f).value;
    const n = f => +$(f).value || 0;
    const bowlers = s('bowlers').split(',').map(b => { const p = b.trim().split(':'); return p.length===2 ? `${p[0].trim()} (${p[1].trim()} ov)` : b.trim(); }).join(', ');

    let m = `Match Situation:\n`;
    m += `- ${s('batting-team')} vs ${s('bowling-team')}\n`;
    m += `- Innings: ${s('innings')}, Score: ${n('runs')}/${n('wickets')} after ${n('over')}.${n('ball')} overs\n`;
    if (n('innings') === 2 && n('target') > 0) {
        const need = n('target') - n('runs');
        const bl = (20 - n('over')) * 6 - n('ball');
        m += `- Target: ${n('target')}, Need ${need} from ${bl} balls (RRR: ${(need/bl*6).toFixed(2)})\n`;
    }
    m += `- On strike: ${s('striker')}, Non-striker: ${s('non-striker')}\n`;
    m += `- Venue: ${s('venue')}, Pitch: ${s('pitch')}, Dew: ${s('dew')}\n`;
    m += `- Bowlers: ${bowlers}\n`;
    m += `- Impact Player: ${s('impact-player')}, Phase: ${s('phase')}\n`;
    m += `\nWhat should the captain do next?`;
    return m;
}

// ── Run Pipeline via SSE ─────────────────────────────────────
async function runPipeline(message) {
    const resp = await fetch(`${API}/api/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ match_state: message })
    });
    if (!resp.ok) throw new Error(`Server ${resp.status}: ${resp.statusText}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let firstDebate = true;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop() || '';
        for (const part of parts) {
            if (part.startsWith('data: ')) {
                try { handleEvent(JSON.parse(part.slice(6).trim())); if (firstDebate) { debateContent.innerHTML = ''; firstDebate = false; } } catch {}
            }
        }
    }
    if (buf.startsWith('data: ')) {
        try { handleEvent(JSON.parse(buf.slice(6).trim())); } catch {}
    }
}

// ── Handle Events ────────────────────────────────────────────
function handleEvent(ev) {
    const { agent, phase, status, text, round } = ev;

    if (agent === 'Pipeline') {
        if (phase === 'intelligence') { mark('stats','active'); mark('conditions','active'); }
        else if (phase === 'debate' && status === 'running') { mark('stats','done'); mark('conditions','done'); mark('debate','active'); }
        else if (phase === 'debate' && status === 'done') { mark('debate','done'); }
        else if (phase === 'reflection') { mark('reflection','active'); }
        else if (phase === 'commentary') { mark('reflection','done'); mark('commentary','active'); }
        else if (phase === 'complete') { mark('commentary','done'); }
        if (ev.debate_round) { $('debate-round-indicator').textContent = `Round ${ev.debate_round}/5`; }
        return;
    }

    if (agent === 'StatsAnalyst' && text) {
        mark('stats','done');
        $('stats-report-text').innerHTML = fmt(text);
    }
    if (agent === 'ConditionsAgent' && text) {
        mark('conditions','done');
        $('conditions-report-text').innerHTML = fmt(text);
    }
    if (agent === 'StrategistCaptain' && text) addDebateMsg('🧠 Strategist Captain', text, 'strategist', round);
    if (agent === 'DevilsAdvocate' && text) addDebateMsg("😈 Devil's Advocate", text, 'advocate', round);
    if (agent === 'JudgeAgent' && text) addDebateMsg('⚖️ Judge', text, 'judge', round);
    if (agent === 'ReflectionAgent' && text) { mark('reflection','done'); parseReflection(text); }
    if (agent === 'MatchCommentator' && text) { mark('commentary','done'); parseCommentary(text); }
    if (agent === 'CommentaryFor' && text) { $('comm-for').innerHTML = fmt(text); $('commentary-panel').style.display = 'block'; }
    if (agent === 'CommentaryAgainst' && text) { $('comm-against').innerHTML = fmt(text); }
    if (agent === 'CommentaryNeutral' && text) { $('comm-neutral').innerHTML = fmt(text); }
}

// ── Debate Messages ──────────────────────────────────────────
let lastRound = 0;
function addDebateMsg(name, text, cls, round) {
    if (round && round > lastRound) {
        lastRound = round;
        const tag = document.createElement('div');
        tag.className = 'debate-round-tag';
        tag.textContent = `⚔️ DEBATE ROUND ${round}`;
        debateContent.appendChild(tag);
    }
    const el = document.createElement('div');
    el.className = `debate-msg ${cls}`;
    el.innerHTML = `<div class="msg-agent">${name}</div><div class="msg-text">${fmt(text)}</div>`;
    debateContent.appendChild(el);
    debateContent.scrollTop = debateContent.scrollHeight;
}

// ── Parse Reflection → Confidence + Extras ───────────────────
function parseReflection(text) {
    // Extract confidence score
    const confMatch = text.match(/(\d+)\s*\/\s*10/);
    if (confMatch) {
        const score = parseInt(confMatch[1]);
        $('confidence-panel').style.display = 'block';
        $('confidence-score').textContent = `${score}/10`;
        $('confidence-bar').style.width = `${score * 10}%`;
        const labels = ['','Desperate','Desperate','Risky','Risky','Coin-flip','Coin-flip','Strong','Strong','No-brainer','No-brainer'];
        $('confidence-label').textContent = labels[score] || '';
        // Color the bar based on score
        if (score >= 7) $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-green), var(--accent-cyan))';
        else if (score >= 5) $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-gold), var(--accent-blue))';
        else $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-red), var(--accent-gold))';
    }

    // Extract counterfactual & flashback
    const sections = text.split(/\*\*(?:Counterfactual|COUNTERFACTUAL|Road Not Taken|Blind Spot|IPL Parallel|HISTORICAL|Historical|IPL Flashback)\*\*/i);
    
    // Show extras panel with full reflection text split
    $('extras-panel').style.display = 'block';
    
    // Try to extract specific sections
    const counterMatch = text.match(/(?:Counterfactual|COUNTERFACTUAL|Road Not Taken)[:\s*]*\n?([\s\S]*?)(?=\*\*|$)/i);
    const flashMatch = text.match(/(?:IPL Parallel|HISTORICAL|Historical|IPL Flashback|Parallel)[:\s*]*\n?([\s\S]*?)(?=\*\*|$)/i);
    
    $('counterfactual-text').innerHTML = counterMatch ? fmt(counterMatch[1].trim()) : fmt(text.substring(0, 300));
    $('flashback-text').innerHTML = flashMatch ? fmt(flashMatch[1].trim()) : '<span style="color:var(--text-muted)">See reflection report</span>';
}

// ── Parse Commentary → Multi-perspective ─────────────────────
function parseCommentary(text) {
    $('captain-call-panel').style.display = 'block';
    
    // Extract Captain's Call section
    const callMatch = text.match(/(?:THE CAPTAIN'S CALL|Captain's Call)[:\s*]*\n?([\s\S]*?)(?=📊|WHY|$)/i);
    $('captain-call-body').innerHTML = callMatch ? fmt(callMatch[1].trim()) : fmt(text.substring(0, 200));

    // The full commentary goes to "For" tab (supporting the decision)
    $('commentary-panel').style.display = 'block';
    $('comm-for').innerHTML = fmt(text);
    
    // The against/neutral will be populated by separate agent calls from server
    if (!$('comm-against').innerHTML) {
        $('comm-against').innerHTML = '<span style="color:var(--text-muted)">⏳ Generating opposing viewpoint...</span>';
    }
    if (!$('comm-neutral').innerHTML) {
        $('comm-neutral').innerHTML = '<span style="color:var(--text-muted)">⏳ Generating balanced analysis...</span>';
    }
}

// ── Pipeline Steps ───────────────────────────────────────────
function mark(id, state) {
    const s = steps[id]; if (!s) return;
    s.classList.remove('active','done');
    s.classList.add(state);
    s.querySelector('.step-status').textContent = state === 'active' ? 'running...' : state === 'done' ? '✓ done' : 'waiting';
}

// ── Format Text ──────────────────────────────────────────────
function fmt(text) {
    let h = esc(text);
    h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/^### (.*$)/gm, '<h4 style="margin:10px 0 4px;font-size:0.88rem;color:var(--text-primary)">$1</h4>');
    h = h.replace(/^## (.*$)/gm, '<h3 style="margin:12px 0 6px;font-size:0.95rem;color:var(--text-primary)">$1</h3>');
    h = h.replace(/^# (.*$)/gm, '<h2 style="margin:14px 0 8px;font-size:1.05rem;color:var(--accent-gold)">$1</h2>');
    h = h.replace(/^- (.*$)/gm, '<span style="display:block;padding-left:14px;position:relative"><span style="position:absolute;left:0;color:var(--accent-gold)">•</span>$1</span>');
    h = h.replace(/\n/g, '<br>');
    return h;
}
function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

// ── Toggles ──────────────────────────────────────────────────
debateToggle.addEventListener('click', () => {
    const show = debateContent.style.display === 'none';
    debateContent.style.display = show ? 'flex' : 'none';
    debateToggle.querySelector('.toggle-icon').textContent = show ? '▼' : '▶';
});
intelToggle.addEventListener('click', () => {
    const show = intelContent.style.display === 'none';
    intelContent.style.display = show ? 'flex' : 'none';
    intelToggle.querySelector('.toggle-icon').textContent = show ? '▼' : '▶';
});

// Commentary tabs
document.querySelectorAll('.comm-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.comm-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.comm-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        $(`comm-${tab.dataset.tab}`).classList.add('active');
    });
});

backBtn.addEventListener('click', () => { dashboard.style.display = 'none'; inputPanel.style.display = 'block'; lastRound = 0; });

// Innings toggle
$('innings').addEventListener('change', e => {
    const t = $('target');
    t.disabled = e.target.value === '1';
    if (e.target.value === '1') t.value = 0;
    updateScorecardPreview();
});

// Health check
fetch(`${API}/api/health`).then(r => r.ok && ($('status-badge').textContent = '● Online', $('status-badge').classList.add('online'))).catch(() => {});
