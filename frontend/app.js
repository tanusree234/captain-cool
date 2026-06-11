/**
 * Captain Cool — Real-Time Streaming Dashboard Frontend
 * SSE streaming with chunk-by-chunk live rendering, win probability arc,
 * live commentary ticker, and animated debate messages.
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
const tickerText = $('ticker-text');
const tickerWrap = $('ticker-wrap');

// ── Active SSE connection controller ────────────────────────
let currentAbortController = null;

const steps = {
    stats: $('step-stats'),
    conditions: $('step-conditions'),
    debate: $('step-debate'),
    reflection: $('step-reflection'),
    commentary: $('step-commentary'),
};

// Scorecard update fields
const scFields = ['innings','over','ball','runs','wickets','target','batting-team','bowling-team','striker','non-striker'];

// Per-agent streaming buffers
const streamBuffers = {};
// Track active streaming debate messages
const activeDebateMsgs = {};

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

function generateGameSummary() {
    const batTeam = $('batting-team').value;
    const bowlTeam = $('bowling-team').value;
    const runs = +$('runs').value || 0;
    const wkts = +$('wickets').value || 0;
    const over = +$('over').value || 0;
    const ball = +$('ball').value || 0;
    const target = +$('target').value || 0;
    const venue = $('venue').value;
    const pitch = $('pitch').value;
    const dew = $('dew').value;
    const striker = $('striker').value;
    const nonStriker = $('non-striker').value;
    
    let h = `🏏 <strong>HIGH-STAKES CLASH AT THE ${venue.toUpperCase()}!</strong><br><br>`;
    h += `We are live in the <strong>${$('phase').value.toUpperCase()} PHASE</strong> of this thrilling encounter. `;
    h += `<strong>${batTeam}</strong> is currently at <strong>${runs}/${wkts}</strong> after <strong>${over}.${ball} overs</strong> `;
    
    if ($('innings').value === '2' && target > 0) {
        const need = target - runs;
        const ballsLeft = (20 - over) * 6 - ball;
        const rrr = ballsLeft > 0 ? ((need / ballsLeft) * 6).toFixed(2) : '∞';
        h += `chasing a formidable target of <strong>${target}</strong> set by <strong>${bowlTeam}</strong>.<br><br>`;
        h += `The equation is clear: <strong>${need} runs required from ${ballsLeft} deliveries</strong> at a Required Run Rate of <strong>${rrr}</strong>. `;
    } else {
        h += `batting first against a disciplined <strong>${bowlTeam}</strong> bowling attack.<br><br>`;
    }
    
    h += `With the dangerous <strong>${striker}</strong> on strike and the legendary <strong>${nonStriker}</strong> anchoring at the other end, `;
    h += `the atmosphere is electric. The <strong>${pitch} pitch</strong> conditions are playing a crucial role, and the <strong>${dew} dew factor</strong> is sliding the ball rapidly, making it a captain's ultimate tactical chess match. `;
    h += `The next dynamic decision will define the course of the game!`;
    
    return h;
}

function showDashboard() {
    // ── Abort any in-flight SSE connection from a previous query ──
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }

    inputPanel.style.display = 'none';
    dashboard.style.display = 'block';
    debateContent.innerHTML = '<div class="debate-placeholder"><p>⏳ Agents assembling...</p></div>';
    
    // Generate and display Game Summary
    const summaryHTML = generateGameSummary();
    $('game-summary-panel').style.display = 'block';
    $('game-summary-text').innerHTML = summaryHTML;

    // Reset panels
    ['captain-call-panel','confidence-panel','commentary-panel','extras-panel','export-panel','win-prob-panel'].forEach(id => $(id).style.display = 'none');

    // ── Fully reset intelligence reports panel ──
    $('stats-report-text').innerHTML = '<span style="color:var(--text-muted)">Waiting...</span>';
    $('conditions-report-text').innerHTML = '<span style="color:var(--text-muted)">Waiting...</span>';
    // Collapse the intel panel so it starts fresh
    intelContent.style.display = 'none';
    $('intel-toggle').querySelector('.toggle-icon').textContent = '▶';

    $('comm-for').innerHTML = '';
    $('comm-against').innerHTML = '';
    $('comm-neutral').innerHTML = '';
    // Reset pipeline
    Object.values(steps).forEach(s => { 
        s.classList.remove('active','done','streaming'); 
        s.querySelector('.step-status').textContent = 'waiting'; 
    });
    $('debate-round-indicator').textContent = '';

    // Reset streaming buffers
    Object.keys(streamBuffers).forEach(k => delete streamBuffers[k]);
    Object.keys(activeDebateMsgs).forEach(k => delete activeDebateMsgs[k]);
    lastRound = 0;

    // Show ticker
    tickerWrap.style.display = 'flex';
    tickerText.textContent = '🏏 Captain Cool multi-agent pipeline is loading... Agents are assembling in the strategy room...';
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
    // Create a fresh abort controller for this request
    currentAbortController = new AbortController();
    const { signal } = currentAbortController;

    const resp = await fetch(`${API}/api/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ match_state: message }),
        signal
    });
    if (!resp.ok) throw new Error(`Server ${resp.status}: ${resp.statusText}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let firstDebate = true;

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            const parts = buf.split('\n\n');
            buf = parts.pop() || '';
            for (const part of parts) {
                if (part.startsWith('data: ')) {
                    try { 
                        const ev = JSON.parse(part.slice(6).trim());
                        if (firstDebate && (ev.agent === 'StrategistCaptain' || ev.agent === 'DevilsAdvocate')) { 
                            debateContent.innerHTML = ''; 
                            firstDebate = false; 
                        }
                        handleEvent(ev); 
                    } catch {}
                }
            }
        }
        if (buf.startsWith('data: ')) {
            try { handleEvent(JSON.parse(buf.slice(6).trim())); } catch {}
        }
    } catch (err) {
        // AbortError is expected when a new query cancels this one — suppress it
        if (err.name !== 'AbortError') throw err;
    }
}

// ── Handle Events ────────────────────────────────────────────
function handleEvent(ev) {
    const { agent, phase, status, text, round, chunk } = ev;

    // ── Pipeline phase events ──
    if (agent === 'Pipeline') {
        if (phase === 'intelligence') { mark('stats','active'); mark('conditions','active'); }
        else if (phase === 'debate' && status === 'running') { 
            mark('stats','done'); mark('conditions','done'); mark('debate','active'); 
            updateTicker('⚔️ Debate phase starting — agents engaging in tactical battle...');
        }
        else if (phase === 'debate' && status === 'done') { mark('debate','done'); }
        else if (phase === 'reflection') { mark('debate','done'); mark('reflection','active'); }
        else if (phase === 'commentary') { mark('reflection','done'); mark('commentary','active'); }
        else if (phase === 'complete') { mark('commentary','done'); finalizeAll(); }
        if (ev.debate_round) { $('debate-round-indicator').textContent = `Round ${ev.debate_round}/5`; }
        return;
    }

    // ── Win Probability event ──
    if (agent === 'WinProbability') {
        updateWinProbability(ev.before, ev.after, ev.round);
        return;
    }

    // ── Streaming start ──
    if (status === 'streaming_start') {
        streamBuffers[agent] = '';
        handleStreamingStart(agent, round);
        return;
    }

    // ── Chunk event — live rendering ──
    if (status === 'streaming' && chunk !== undefined) {
        streamBuffers[agent] = (streamBuffers[agent] || '') + chunk;
        handleChunk(agent, chunk, round);
        return;
    }

    // ── Done event — finalize ──
    if (status === 'done' && text) {
        handleDone(agent, text, round);
    }
}

// ── Handle streaming start ───────────────────────────────────
function handleStreamingStart(agent, round) {
    if (agent === 'StatsAnalyst') {
        mark('stats', 'streaming');
        $('stats-report-text').innerHTML = '<span class="streaming-cursor"></span>';
        updateTicker('📊 Stats Analyst is gathering player intelligence...');
    }
    if (agent === 'ConditionsAgent') {
        mark('conditions', 'streaming');
        $('conditions-report-text').innerHTML = '<span class="streaming-cursor"></span>';
        updateTicker('🌦️ Conditions Agent is analyzing weather and pitch...');
    }
    if (agent === 'StrategistCaptain') {
        mark('debate', 'streaming');
        $('captain-call-panel').style.display = 'block';
        const el = $('captain-call-body');
        el.innerHTML = '<span class="streaming-cursor" id="strategist-cursor"></span>';
        // Create debate message for streaming
        const msgEl = getOrCreateDebateMsg('StrategistCaptain', '🧠 Strategist Captain', 'strategist', round);
        activeDebateMsgs['StrategistCaptain'] = msgEl;
        updateTicker(`🧠 Strategist Captain is formulating Round ${round} tactical call...`);
    }
    if (agent === 'DevilsAdvocate') {
        const msgEl = getOrCreateDebateMsg('DevilsAdvocate', "😈 Devil's Advocate", 'advocate', round);
        activeDebateMsgs['DevilsAdvocate'] = msgEl;
        updateTicker("😈 Devil's Advocate is challenging the strategy...");
    }
    if (agent === 'ReflectionAgent') {
        mark('reflection', 'streaming');
        updateTicker('🪞 Reflection Agent is performing meta-analysis...');
    }
    if (agent === 'CommentaryFor') {
        mark('commentary', 'streaming');
        $('commentary-panel').style.display = 'block';
        $('comm-live-badge').style.display = 'inline';
        $('comm-for').innerHTML = '<span class="streaming-cursor"></span>';
        updateTicker('🎙️ Commentators delivering live perspectives...');
    }
    if (agent === 'CommentaryAgainst') {
        $('comm-against').innerHTML = '<span class="streaming-cursor"></span>';
    }
    if (agent === 'CommentaryNeutral') {
        $('comm-neutral').innerHTML = '<span class="streaming-cursor"></span>';
    }
}

// ── Handle chunk event ───────────────────────────────────────
function handleChunk(agent, chunk, round) {
    const safe = esc(chunk);

    if (agent === 'StatsAnalyst') {
        const el = $('stats-report-text');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);
        // Open intel panel when content starts flowing
        if (intelContent.style.display === 'none') {
            intelContent.style.display = 'flex';
            $('intel-toggle').querySelector('.toggle-icon').textContent = '▼';
        }
    }

    if (agent === 'ConditionsAgent') {
        const el = $('conditions-report-text');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);
    }

    if (agent === 'StrategistCaptain') {
        // Update captain's call body
        const el = $('captain-call-body');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);

        // Also update debate message
        const msgEl = activeDebateMsgs['StrategistCaptain'];
        if (msgEl) {
            const textEl = msgEl.querySelector('.msg-text');
            const cur = textEl.querySelector('.streaming-cursor');
            const sp = document.createElement('span');
            sp.textContent = chunk;
            if (cur) textEl.insertBefore(sp, cur);
            else textEl.appendChild(sp);
            debateContent.scrollTop = debateContent.scrollHeight;
        }

        // Update ticker with beginning of strategist content
        const currentBuf = streamBuffers['StrategistCaptain'] || '';
        if (currentBuf.length < 80) {
            updateTicker(`🧠 Captain Cool: ${currentBuf.replace(/\n/g, ' ')}...`);
        }
    }

    if (agent === 'DevilsAdvocate') {
        const msgEl = activeDebateMsgs['DevilsAdvocate'];
        if (msgEl) {
            const textEl = msgEl.querySelector('.msg-text');
            const cur = textEl.querySelector('.streaming-cursor');
            const sp = document.createElement('span');
            sp.textContent = chunk;
            if (cur) textEl.insertBefore(sp, cur);
            else textEl.appendChild(sp);
            debateContent.scrollTop = debateContent.scrollHeight;
        }
    }

    if (agent === 'ReflectionAgent') {
        // Buffer reflected; will finalize on done
    }

    if (agent === 'CommentaryFor') {
        const el = $('comm-for');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);
    }

    if (agent === 'CommentaryAgainst') {
        const el = $('comm-against');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);
    }

    if (agent === 'CommentaryNeutral') {
        const el = $('comm-neutral');
        const cursor = el.querySelector('.streaming-cursor');
        const span = document.createElement('span');
        span.textContent = chunk;
        if (cursor) el.insertBefore(span, cursor);
        else el.appendChild(span);
    }
}

// ── Handle done event ────────────────────────────────────────
function handleDone(agent, text, round) {
    if (agent === 'StatsAnalyst') {
        mark('stats','done');
        $('stats-report-text').innerHTML = fmt(text);
    }
    if (agent === 'ConditionsAgent') {
        mark('conditions','done');
        $('conditions-report-text').innerHTML = fmt(text);
    }
    if (agent === 'StrategistCaptain') {
        // Finalize captain call body
        $('captain-call-body').innerHTML = fmt(text);
        // Finalize debate message
        const msgEl = activeDebateMsgs['StrategistCaptain'];
        if (msgEl) {
            msgEl.classList.remove('streaming');
            msgEl.querySelector('.msg-text').innerHTML = fmt(text);
            const dotWrap = msgEl.querySelector('.streaming-dots');
            if (dotWrap) dotWrap.remove();
        }
        streamBuffers['StrategistCaptain'] = text;
    }
    if (agent === 'DevilsAdvocate') {
        const msgEl = activeDebateMsgs['DevilsAdvocate'];
        if (msgEl) {
            msgEl.classList.remove('streaming');
            // Remove the animated typing dots from the agent label
            const dotWrap = msgEl.querySelector('.streaming-dots');
            if (dotWrap) dotWrap.remove();
            msgEl.querySelector('.msg-text').innerHTML = fmt(text);
        }
    }
    if (agent === 'JudgeAgent') {
        addDebateMsg('⚖️ Judge', text, 'judge', round);
    }
    if (agent === 'ReflectionAgent') {
        mark('reflection','done');
        $('captain-call-panel').style.display = 'block';
        parseReflection(text);
    }
    if (agent === 'MatchCommentator') {
        mark('commentary','done');
    }
    if (agent === 'CommentaryFor') {
        $('comm-for').innerHTML = fmt(text);
        $('commentary-panel').style.display = 'block';
    }
    if (agent === 'CommentaryAgainst') {
        $('comm-against').innerHTML = fmt(text);
    }
    if (agent === 'CommentaryNeutral') {
        $('comm-neutral').innerHTML = fmt(text);
        $('comm-live-badge').style.display = 'none';
    }
}

// ── Win Probability Arc ──────────────────────────────────────
function updateWinProbability(before, after, round) {
    $('win-prob-panel').style.display = 'block';
    $('wp-before').textContent = `${before}%`;
    $('wp-after').textContent = `${after}%`;
    $('wp-round').textContent = `Round ${round}`;
    $('win-arc-pct').textContent = `${after}%`;

    // Arc: total arc length = 157 (π * r where r=50)
    // 0% = dashoffset 157 (empty), 100% = dashoffset 0 (full)
    const arcLen = 157;
    const beforeOffset = arcLen - (before / 100) * arcLen;
    const afterOffset = arcLen - (after / 100) * arcLen;

    const beforeArc = $('win-arc-before');
    const afterArc = $('win-arc-after');

    // Animate
    beforeArc.style.strokeDashoffset = beforeOffset;
    afterArc.style.strokeDashoffset = afterOffset;

    // Color the arc based on probability
    if (after >= 60) {
        afterArc.style.stroke = '#3fb950';
        $('win-arc-pct').style.fill = '#3fb950';
    } else if (after >= 45) {
        afterArc.style.stroke = '#f59e0b';
        $('win-arc-pct').style.fill = '#f59e0b';
    } else {
        afterArc.style.stroke = '#f85149';
        $('win-arc-pct').style.fill = '#f85149';
    }

    updateTicker(`📈 Win probability update: ${before}% → ${after}% after Round ${round} strategy revision`);
}

// ── Get or Create Debate Message ─────────────────────────────
function getOrCreateDebateMsg(agentKey, name, cls, round) {
    if (round && round > lastRound) {
        lastRound = round;
        const tag = document.createElement('div');
        tag.className = 'debate-round-tag';
        tag.textContent = `⚔️ DEBATE ROUND ${round}`;
        debateContent.appendChild(tag);
    }
    const el = document.createElement('div');
    el.className = `debate-msg ${cls} streaming`;
    el.innerHTML = `
        <div class="msg-agent">
            ${name}
            <span class="streaming-dots">
                <span class="msg-streaming-dot"></span>
                <span class="msg-streaming-dot"></span>
                <span class="msg-streaming-dot"></span>
            </span>
        </div>
        <div class="msg-text"><span class="streaming-cursor"></span></div>`;
    debateContent.appendChild(el);
    debateContent.scrollTop = debateContent.scrollHeight;
    return el;
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

// ── Finalize All ─────────────────────────────────────────────
function finalizeAll() {
    $('export-panel').style.display = 'block';
    updateTicker('✅ Analysis complete! Captain Cool has made the call. Download the full strategy report below.');
    // Stop ticker animation after a moment
    setTimeout(() => {
        tickerText.style.animation = 'none';
    }, 3000);
}

// ── Update Ticker ────────────────────────────────────────────
function updateTicker(message) {
    tickerText.textContent = message;
    tickerText.style.animation = 'none';
    tickerText.offsetHeight; // reflow
    tickerText.style.animation = 'ticker-scroll 20s linear infinite';
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
        if (score >= 7) $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-green), var(--accent-cyan))';
        else if (score >= 5) $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-gold), var(--accent-blue))';
        else $('confidence-bar').style.background = 'linear-gradient(90deg, var(--accent-red), var(--accent-gold))';
    }

    // Show extras panel
    $('extras-panel').style.display = 'block';
    
    const counterMatch = text.match(/(?:Counterfactual|COUNTERFACTUAL|Road Not Taken)[:\s*]*\n?([\s\S]*?)(?=\*\*|$)/i);
    const flashMatch = text.match(/(?:IPL Parallel|HISTORICAL|Historical|IPL Flashback|Parallel)[:\s*]*\n?([\s\S]*?)(?=\*\*|$)/i);
    
    $('counterfactual-text').innerHTML = counterMatch ? fmt(counterMatch[1].trim()) : fmt(text.substring(0, 300));
    $('flashback-text').innerHTML = flashMatch ? fmt(flashMatch[1].trim()) : '<span style="color:var(--text-muted)">See reflection report</span>';
}

// ── Export Report Feature ────────────────────────────────────
function downloadReport() {
    let md = `# 🏏 CAPTAIN COOL — MULTI-AGENT IPL STRATEGY REPORT\n\n`;
    md += `*Generated on ${new Date().toLocaleString()}*\n\n`;
    md += `## 📋 MATCH SITUATION\n`;
    md += `- **Teams**: ${$('batting-team').value} vs ${$('bowling-team').value}\n`;
    md += `- **Score**: ${$('runs').value}/${$('wickets').value} after ${$('over').value}.${$('ball').value} overs\n`;
    if ($('innings').value === '2') {
        const need = $('sc-need').textContent;
        const balls = $('sc-balls').textContent;
        const rrr = $('sc-rrr').textContent;
        md += `- **Target**: ${$('target').value} (Need ${need} from ${balls} balls, RRR: ${rrr})\n`;
    }
    md += `- **Venue**: ${$('venue').value} (Pitch: ${$('pitch').value}, Dew: ${$('dew').value})\n`;
    md += `- **Batsmen**: Striker: ${$('striker').value}, Non-Striker: ${$('non-striker').value}\n\n`;
    
    md += `## 📊 FIELD INTEL\n`;
    md += `### Stats Analyst Intelligence\n${$('stats-report-text').innerText}\n\n`;
    md += `### Conditions Agent Assessment\n${$('conditions-report-text').innerText}\n\n`;
    
    md += `## 📈 WIN PROBABILITY\n`;
    md += `- **Before**: ${$('wp-before').textContent}\n`;
    md += `- **After**: ${$('wp-after').textContent}\n\n`;
    
    md += `## ⚔️ AGENT DEBATE TRANSCRIPT\n`;
    const msgs = debateContent.querySelectorAll('.debate-msg');
    msgs.forEach(m => {
        const agent = m.querySelector('.msg-agent').innerText.replace(/\n.*/g,'').trim();
        const body = m.querySelector('.msg-text').innerText;
        md += `### ${agent}\n${body}\n\n`;
    });
    
    md += `## 🎯 STRATEGY DECISION & REFLECTION\n`;
    md += `**Confidence Score**: ${$('confidence-score').textContent}\n\n`;
    md += `### Road Not Taken (Counterfactual)\n${$('counterfactual-text').innerText}\n\n`;
    md += `### Historical Parallel (IPL Flashback)\n${$('flashback-text').innerText}\n\n`;
    
    md += `## 🎙️ MULTI-PERSPECTIVE COMMENTARY\n`;
    md += `### 👍 Ravi Shastri (For perspective)\n${$('comm-for').innerText}\n\n`;
    md += `### 👎 Sanjay Manjrekar (Against perspective)\n${$('comm-against').innerText}\n\n`;
    md += `### ⚖️ Harsha Bhogle (Balanced Neutral perspective)\n${$('comm-neutral').innerText}\n\n`;
    
    md += `\n---\n*Powered by Google Gemini 2.5 Pro + Flash, Google ADK & Antigravity. Real-time streaming pipeline.*`;
    
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Captain_Cool_Strategy_${$('batting-team').value}_vs_${$('bowling-team').value}_${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ── Pipeline Steps ───────────────────────────────────────────
function mark(id, state) {
    const s = steps[id]; if (!s) return;
    s.classList.remove('active','done','streaming');
    s.classList.add(state);
    const statusMap = { active: 'running...', done: '✓ done', streaming: '⚡ streaming' };
    s.querySelector('.step-status').textContent = statusMap[state] || 'waiting';
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

backBtn.addEventListener('click', () => { 
    dashboard.style.display = 'none'; 
    inputPanel.style.display = 'block'; 
    lastRound = 0; 
});

// Innings toggle
$('innings').addEventListener('change', e => {
    const t = $('target');
    t.disabled = e.target.value === '1';
    if (e.target.value === '1') t.value = 0;
    updateScorecardPreview();
});

// Health check
fetch(`${API}/api/health`)
    .then(r => r.ok && r.json())
    .then(data => { 
        if (data) {
            $('status-badge').textContent = '● Online'; 
            $('status-badge').classList.add('online');
        }
    })
    .catch(() => {});

// Export Strategy button listener
$('export-btn').addEventListener('click', downloadReport);
