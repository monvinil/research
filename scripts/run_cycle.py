#!/usr/bin/env python3
"""Research cycle runner — LLM-powered multi-agent research engine.

Pulls live data from 12 connectors (US + international), runs derived
analytics (z-scores, cross-correlations, composite indices), then routes
through 4 LLM agents (Agent A/C/B/Master) using Claude Code CLI.

No API key needed — uses existing Claude Code subscription via CLI.

Usage:
    python scripts/run_cycle.py                     # full cycle
    python scripts/run_cycle.py --scan-only         # data pull only (no LLM)
    python scripts/run_cycle.py --analytics-only    # scan + analytics (no LLM)
    python scripts/run_cycle.py --model opus        # use opus for all agents
    python scripts/run_cycle.py --verbose           # show raw LLM responses
    python scripts/run_cycle.py --use-api           # use Anthropic API instead of CLI
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'agents')
sys.path.insert(0, PROJECT_ROOT)

# Load .env
_env_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_state():
    return load_json(os.path.join(DATA_DIR, 'context', 'state.json')) or {
        'current_cycle': 0,
        'agent_a': {}, 'agent_b': {}, 'agent_c': {},
    }


def save_state(state):
    save_json(os.path.join(DATA_DIR, 'context', 'state.json'), state)


def load_agent_prompt(name):
    """Load an agent's system prompt from agents/*.md."""
    path = os.path.join(AGENTS_DIR, name)
    with open(path) as f:
        return f.read()


def load_context_summaries():
    """Load accumulated cycle summaries for context feeding."""
    path = os.path.join(DATA_DIR, 'context', 'cycle_summaries.json')
    return load_json(path) or {'cycles': []}


def save_context_summary(cycle_num, summary):
    """Append a cycle summary to the accumulated context."""
    path = os.path.join(DATA_DIR, 'context', 'cycle_summaries.json')
    data = load_json(path) or {'cycles': []}
    data['cycles'].append({
        'cycle': cycle_num,
        'date': datetime.now(timezone.utc).isoformat(),
        'summary': summary,
    })
    # Keep last 10 cycles of full context, compress older ones
    if len(data['cycles']) > 10:
        old = data['cycles'][:-10]
        data['compressed'] = data.get('compressed', '') + '\n'.join(
            f"Cycle {c['cycle']}: {(c.get('summary') or c.get('master_synthesis') or c.get('note') or '')[:200]}" for c in old
        ) + '\n'
        data['cycles'] = data['cycles'][-10:]
    save_json(path, data)


def load_kill_index():
    """Load the kill index."""
    path = os.path.join(DATA_DIR, 'context', 'kill_index.json')
    return load_json(path) or {'kill_patterns': [], 'stats': {}}


def save_kill_index(kill_index):
    save_json(os.path.join(DATA_DIR, 'context', 'kill_index.json'), kill_index)


# ---------------------------------------------------------------------------
# LLM Engine — supports both Claude Code CLI (subscription) and API
# ---------------------------------------------------------------------------

MODELS = {
    'sonnet': 'claude-sonnet-4-5-20250929',
    'opus': 'claude-opus-4-6',
    'haiku': 'claude-haiku-4-5-20251001',
}

_client = None
_total_input_tokens = 0
_total_output_tokens = 0
_use_api = False  # Default: use CLI


def get_client():
    global _client
    if _client is None:
        import anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            raise RuntimeError(
                'ANTHROPIC_API_KEY not set. Add it to .env:\n'
                '  ANTHROPIC_API_KEY=sk-ant-...\n'
                'Get your key at: https://console.anthropic.com/settings/keys'
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def llm_call_cli(system_prompt, user_message, model='sonnet', max_tokens=8192):
    """Call Claude via Claude Code CLI — uses existing subscription, no API key.

    Requires `claude` CLI: npm install -g @anthropic-ai/claude-code
    Auto-falls back to API if CLI is not available.
    """
    import subprocess
    import shutil

    claude_path = shutil.which('claude')
    if not claude_path:
        for path in ['/usr/local/bin/claude', os.path.expanduser('~/.local/bin/claude'),
                     os.path.expanduser('~/.npm/bin/claude')]:
            if os.path.exists(path):
                claude_path = path
                break

    if not claude_path:
        print('    [CLI] claude binary not found — falling back to API')
        if os.environ.get('ANTHROPIC_API_KEY'):
            return llm_call_api(system_prompt, user_message, model, max_tokens)
        raise RuntimeError(
            'Neither claude CLI nor ANTHROPIC_API_KEY available.\n'
            'Install CLI: npm install -g @anthropic-ai/claude-code\n'
            'Or set ANTHROPIC_API_KEY in .env'
        )

    model_id = MODELS.get(model, model)
    combined_prompt = f'{system_prompt}\n\n---\n\n{user_message}'

    t0 = time.time()
    try:
        result = subprocess.run(
            [claude_path, '--print', '--model', model_id, '--max-tokens', str(max_tokens)],
            input=combined_prompt,
            capture_output=True, text=True, timeout=300,
        )
        elapsed = time.time() - t0
        text = result.stdout.strip()

        if result.returncode != 0:
            err = result.stderr.strip()
            print(f'    [CLI {model}] ERROR: {err[:200]}')
            if os.environ.get('ANTHROPIC_API_KEY'):
                print('    Falling back to API...')
                return llm_call_api(system_prompt, user_message, model, max_tokens)
            raise RuntimeError(f'Claude CLI failed: {err[:500]}')

        chars = len(text)
        est_tokens = chars // 4
        print(f'    [CLI {model}] ~{est_tokens:,} tokens / {elapsed:.1f}s')
        return text
    except FileNotFoundError:
        print('    [CLI] claude not executable — falling back to API')
        if os.environ.get('ANTHROPIC_API_KEY'):
            return llm_call_api(system_prompt, user_message, model, max_tokens)
        raise


def llm_call_api(system_prompt, user_message, model='sonnet', max_tokens=8192):
    """Call Claude API directly — requires ANTHROPIC_API_KEY."""
    global _total_input_tokens, _total_output_tokens

    client = get_client()
    model_id = MODELS.get(model, model)

    t0 = time.time()
    response = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{'role': 'user', 'content': user_message}],
    )

    elapsed = time.time() - t0
    usage = response.usage
    _total_input_tokens += usage.input_tokens
    _total_output_tokens += usage.output_tokens

    text = response.content[0].text
    print(f'    [{model_id}] {usage.input_tokens} in / {usage.output_tokens} out / {elapsed:.1f}s')
    return text


def llm_call(system_prompt, user_message, model='sonnet', max_tokens=8192):
    """Route to CLI or API based on configuration."""
    if _use_api:
        return llm_call_api(system_prompt, user_message, model, max_tokens)
    return llm_call_cli(system_prompt, user_message, model, max_tokens)


def parse_json_response(text):
    """Extract JSON from an LLM response, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    if text.startswith('{') or text.startswith('['):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from ```json ... ``` blocks
    import re
    blocks = re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    for block in blocks:
        block = block.strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    # Try finding the first { ... } or [ ... ] block
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    break

    raise ValueError(f'Could not parse JSON from LLM response:\n{text[:500]}...')


# ---------------------------------------------------------------------------
# Data formatting helpers — prepare raw data for LLM context
# ---------------------------------------------------------------------------

def format_fred_data(raw):
    """Format FRED data into a readable text block."""
    lines = ['## FRED Economic Data\n']
    for key in ['fred_labor_squeeze', 'fred_credit_stress', 'fred_job_gaps', 'fred_rates',
                'fred_profitability', 'fred_stress', 'fred_sector_costs', 'fred_small_biz',
                'fred_assets']:
        if key not in raw:
            continue
        data = raw[key].get('data', {})
        label = key.replace('fred_', '').replace('_', ' ').title()
        lines.append(f'### {label}')
        for series_name, series_data in data.items():
            obs = series_data.get('observations', [])
            pretty_name = series_name.replace('_', ' ').title()
            if obs:
                latest = obs[0]
                lines.append(f'- {pretty_name}: {latest.get("value", "N/A")} (date: {latest.get("date", "?")})')
                if len(obs) >= 2:
                    prev = obs[1]
                    lines.append(f'  Previous: {prev.get("value", "N/A")} ({prev.get("date", "?")})')
                if len(obs) >= 13:
                    yoy = obs[12]
                    lines.append(f'  Year-ago: {yoy.get("value", "N/A")} ({yoy.get("date", "?")})')
        lines.append('')
    return '\n'.join(lines)


def format_bls_data(raw):
    """Format BLS data into readable text."""
    lines = ['## BLS Employment & Wage Data\n']
    for key in ['bls_industry', 'bls_wages', 'bls_jolts', 'bls_occupational', 'bls_wage_premium']:
        if key not in raw:
            continue
        data = raw[key].get('data', {})
        label = key.replace('bls_', '').replace('_', ' ').title()
        lines.append(f'### {label}')
        for series_name, series_data in data.items():
            obs = series_data.get('observations', [])
            pretty_name = series_name.replace('_', ' ').title()
            if obs:
                latest = obs[0]
                lines.append(f'- {pretty_name}: {latest.get("value", "N/A")} (period: {latest.get("period", latest.get("date", "?"))})')
                if len(obs) >= 2:
                    lines.append(f'  Previous: {obs[1].get("value", "N/A")}')
        lines.append('')
    return '\n'.join(lines)


def format_edgar_data(raw):
    """Format EDGAR data, truncating long filing lists."""
    lines = ['## SEC EDGAR Filings\n']
    for key in ['edgar_distress', 'edgar_ai_failures', 'edgar_ai_risk']:
        if key not in raw:
            continue
        data = raw[key]
        label = key.replace('edgar_', '').replace('_', ' ').title()
        lines.append(f'### {label}')
        if isinstance(data, dict):
            if 'total_hits' in data:
                lines.append(f'Total hits: {data["total_hits"]}')
            filings = data.get('filings', data.get('results', []))
            if isinstance(filings, list):
                lines.append(f'Filings found: {len(filings)}')
                for f in filings[:15]:  # Cap at 15 to manage tokens
                    name = f.get('company_name', f.get('entity_name', '?'))
                    form = f.get('form_type', f.get('form', '?'))
                    date = f.get('filed_date', f.get('filed', '?'))
                    lines.append(f'  - {name} | {form} | filed {date}')
        lines.append('')
    return '\n'.join(lines)


def format_web_data(raw):
    """Format web search results."""
    lines = ['## Web Search Results\n']
    for key in sorted(k for k in raw if k.startswith('web_')):
        data = raw[key]
        label = key.replace('web_', '').replace('_', ' ').title()
        lines.append(f'### {label}')
        # Handle both list and dict formats
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = data.get('results', [])
        else:
            continue
        for r in results[:8]:
            if isinstance(r, dict):
                title = r.get('title', '?')
                snippet = r.get('snippet', r.get('body', ''))[:200]
                lines.append(f'  - {title}')
                if snippet:
                    lines.append(f'    {snippet}')
        lines.append('')
    return '\n'.join(lines)


def format_international_data(raw):
    """Format international data (World Bank, OECD, Eurostat)."""
    lines = ['## International Comparative Data\n']

    # World Bank
    for key in ['wb_business_env', 'wb_labor_markets', 'wb_services_trade', 'wb_tech_readiness']:
        if key not in raw:
            continue
        data = raw[key]
        label = key.replace('wb_', '').replace('_', ' ').title()
        lines.append(f'### World Bank: {label}')
        interpretation = data.get('interpretation', '')
        if interpretation:
            lines.append(f'  Analysis: {interpretation[:300]}')
        inner = data.get('data', {})
        if isinstance(inner, dict):
            for ind_id, ind_data in list(inner.items())[:3]:
                desc = ind_data.get('description', ind_id) if isinstance(ind_data, dict) else ind_id
                lines.append(f'  - {desc}')
                country_data = ind_data.get('data', {}) if isinstance(ind_data, dict) else {}
                for country, cdata in list(country_data.items())[:4]:
                    obs = cdata.get('observations', [])
                    if obs and obs[0].get('value') is not None:
                        lines.append(f'    {cdata.get("country", country)}: {obs[0]["value"]} ({obs[0].get("year", "?")})')
        lines.append('')

    # OECD
    for key in ['oecd_leading', 'oecd_labor', 'oecd_tech']:
        if key not in raw:
            continue
        data = raw[key]
        label = key.replace('oecd_', '').replace('_', ' ').title()
        lines.append(f'### OECD: {label}')
        interpretation = data.get('interpretation', '')
        if interpretation:
            lines.append(f'  {interpretation[:300]}')
        obs = data.get('data', [])
        if isinstance(obs, list):
            lines.append(f'  Data points: {len(obs)}')
            for o in obs[:5]:
                if isinstance(o, dict):
                    parts = [f'{k}={v}' for k, v in o.items() if k != 'value']
                    lines.append(f'    {", ".join(parts[:3])}: {o.get("value", "?")}')
        lines.append('')

    # Eurostat
    for key in ['eu_labor_costs', 'eu_ai_adoption', 'eu_biz_demography']:
        if key not in raw:
            continue
        data = raw[key]
        label = key.replace('eu_', '').replace('_', ' ').title()
        lines.append(f'### Eurostat: {label}')
        interpretation = data.get('interpretation', '')
        if interpretation:
            lines.append(f'  {interpretation[:300]}')
        lines.append(f'  Records: {data.get("record_count", "?")}')
        lines.append('')

    return '\n'.join(lines)


def format_market_data(raw):
    """Format Yahoo Finance and Google Trends data."""
    lines = ['## Market & Search Data\n']

    # Sector performance
    if 'market_sectors' in raw:
        data = raw['market_sectors']
        lines.append('### Sector ETF Performance (6mo)')
        ranked = data.get('ranked', [])
        for symbol, name, perf in ranked:
            emoji = '+' if perf > 0 else ''
            lines.append(f'  {symbol} ({name}): {emoji}{perf}%')
        lines.append('')

    # Staffing canary
    if 'market_staffing_canary' in raw:
        data = raw['market_staffing_canary']
        lines.append('### Staffing Company Stocks (P2 canary)')
        for symbol, info in data.get('data', {}).items():
            lines.append(f'  {symbol} ({info.get("name", "")}): {info.get("performance_pct", "?")}%')
        interpretation = data.get('interpretation', '')
        if interpretation:
            lines.append(f'  {interpretation[:200]}')
        lines.append('')

    # AI infrastructure
    if 'market_ai_infra' in raw:
        data = raw['market_ai_infra']
        lines.append('### AI Infrastructure Stocks (P1)')
        for symbol, info in data.get('data', {}).items():
            lines.append(f'  {symbol} ({info.get("name", "")}): {info.get("performance_pct", "?")}%')
        lines.append('')

    # Google Trends
    for key in ['trends_distress', 'trends_ai_adoption']:
        if key not in raw:
            continue
        data = raw[key]
        label = key.replace('trends_', '').replace('_', ' ').title()
        lines.append(f'### Search Trends: {label}')
        interpretation = data.get('interpretation', '')
        if interpretation:
            lines.append(f'  {interpretation[:300]}')
        obs = data.get('data', [])
        if obs:
            lines.append(f'  Data points: {len(obs)}')
        lines.append('')

    return '\n'.join(lines)


def format_raw_for_agent_a(raw, context_summaries, kill_index, analytics_result=None):
    """Build the full user message for Agent A."""
    sections = []

    # Derived analytics first (most valuable)
    if analytics_result:
        sections.append('# DERIVED ANALYTICS — COMPUTED INDICATORS\n')
        sections.append(format_analytics_for_agent(analytics_result))

    # Raw data
    sections.append('# RAW DATA FROM THIS CYCLE\'S SCAN\n')
    sections.append(format_fred_data(raw))
    sections.append(format_bls_data(raw))
    sections.append(format_market_data(raw))
    sections.append(format_edgar_data(raw))
    sections.append(format_web_data(raw))
    sections.append(format_international_data(raw))

    # Previous cycle context
    cycles = context_summaries.get('cycles', [])
    if cycles:
        sections.append('# CONTEXT FROM PREVIOUS CYCLES\n')
        for c in cycles[-3:]:  # Last 3 cycles
            sections.append(f'## Cycle {c["cycle"]} ({c.get("date", "?")[:10]})')
            summary = c.get('summary') or c.get('master_synthesis') or c.get('note') or ''
            if summary:
                sections.append(summary[:2000])
            sections.append('')

    # Kill index
    patterns = kill_index.get('kill_patterns', [])
    if patterns:
        sections.append('# KILL INDEX — Do NOT produce signals matching these patterns\n')
        for p in patterns:
            if p.get('still_active', True):
                sections.append(f'- [{p.get("pattern_id", "?")}] {p.get("kill_reason", "?")}')
                sections.append(f'  Affects: {p.get("signal_type_affected", "?")} in {p.get("industries_affected", [])}')
        sections.append('')

    # Directive
    sections.append('# SCAN DIRECTIVE')
    sections.append('Systemic Pattern Focus: Liquidation cascades, demographic labor gaps, '
                    'infrastructure overhang exploitation, dead business revival, cost-structure kills')
    sections.append('Horizon: H1, H2, H3')
    sections.append('Sources Priority: All categories — government data (FRED, BLS, EDGAR) + web signals')
    sections.append('')
    sections.append('Extract 20-50 signals from the raw data above. Return a JSON array of signal objects '
                    'following your Signal Extraction Format. Focus on structural patterns, not industry picks.')
    sections.append('')
    sections.append('Return ONLY a JSON array of signal objects. No preamble.')

    return '\n'.join(sections)


def format_for_agent_c(signals, state, kill_index):
    """Build user message for Agent C grading."""
    sections = []
    sections.append('# SIGNALS FROM AGENT A\n')
    sections.append(json.dumps(signals, indent=2)[:15000])  # Token management

    sections.append('\n# CURRENT STATE\n')
    sections.append(json.dumps(state, indent=2)[:3000])

    sections.append('\n# KILL INDEX\n')
    sections.append(json.dumps(kill_index, indent=2)[:2000])

    sections.append('\n# INSTRUCTIONS')
    sections.append('1. Deduplicate and merge related signals')
    sections.append('2. Grade each signal using the grading rubric (0-10)')
    sections.append('3. Check against kill index — flag matches')
    sections.append('4. Cluster signals into opportunity themes')
    sections.append('5. Identify cross-signal patterns and contradictions')
    sections.append('')
    sections.append('Return a JSON object with this structure:')
    sections.append('```json')
    sections.append('''{
  "graded_signals": [...signals with relevance_score added...],
  "opportunity_clusters": [
    {
      "name": "...",
      "thesis": "...",
      "score": 0-100,
      "horizon": "H1/H2/H3",
      "principles_passed": ["P1", ...],
      "signal_count": N,
      "key_data": ["..."],
      "vc_hook": "...",
      "status": "scanning"
    }
  ],
  "cross_signal_patterns": [
    {"pattern": "...", "signals_involved": [...], "strength": "weak/moderate/strong"}
  ],
  "contradictions": ["..."],
  "next_cycle_suggestions": ["..."]
}''')
    sections.append('```')
    sections.append('Return ONLY the JSON object. No preamble.')

    return '\n'.join(sections)


def format_for_agent_b(opportunities, signals, state):
    """Build user message for Agent B verification."""
    sections = []
    sections.append('# TOP OPPORTUNITIES TO VERIFY\n')
    sections.append(json.dumps(opportunities[:5], indent=2))

    sections.append('\n# SUPPORTING SIGNALS\n')
    # Send only the signals relevant to these opportunities
    opp_principles = set()
    for o in opportunities[:5]:
        for p in o.get('principles_passed', []):
            opp_principles.add(p)
    relevant = [s for s in signals if s.get('principle', '').split(',')[0] in opp_principles]
    sections.append(json.dumps(relevant[:30], indent=2)[:10000])

    sections.append('\n# FOUNDING CONSTRAINTS')
    sections.append('''
CAPITAL: $500K-$1M starting. Can raise more. Capital is a variable, not a constraint.
FOUNDERS: 2 people. One ML/AI Masters (Georgia Tech). One operator (Argentina native, US resident).
LANGUAGES: English + Spanish natively. Others = ops cost adder.
LOCATION: Davis, CA — 1hr from SF.
LEGAL: US citizen + US resident. Resident may have visa limits on govt/defense.
LICENSES: Willing to acquire existing licensed businesses. Price the acquisition.
VC NETWORK: Active angel/VC relationships.
''')

    sections.append('\n# INSTRUCTIONS')
    sections.append('For each opportunity, run your full verification framework:')
    sections.append('- V1: Unit Economics Model')
    sections.append('- V2: Liquidation Cascade Position')
    sections.append('- V3: Incumbent Response Analysis')
    sections.append('- V4: Regulatory & Legal Check')
    sections.append('- V5: Technical Feasibility')
    sections.append('- V6: Market Timing')
    sections.append('- V10-V15: Extended checks (Regulatory Capture, Competitive Equilibrium, Trust & Liability, Switching Friction, Macro Stress Test, Network Effects)')
    sections.append('- Opportunity Quality Assessment (Execution + VC Differentiation)')
    sections.append('')
    sections.append('Return a JSON array of verification objects following your output format.')
    sections.append('Return ONLY the JSON array. No preamble.')

    return '\n'.join(sections)


def format_for_master(signals, opportunities, verifications, context_summaries, state):
    """Build user message for Master synthesis."""
    sections = []

    sections.append('# CYCLE RESULTS\n')

    sections.append('## Agent A: Signal Summary')
    sections.append(f'Total signals: {len(signals)}')
    by_principle = {}
    for s in signals:
        p = s.get('principle', 'unknown').split(',')[0]
        by_principle.setdefault(p, []).append(s)
    for p in sorted(by_principle.keys()):
        sigs = by_principle[p]
        avg = sum(s.get('relevance_score', 0) for s in sigs) / max(len(sigs), 1)
        sections.append(f'  {p}: {len(sigs)} signals, avg score {avg:.1f}')
    sections.append('')

    sections.append('## Top Signals (score >= 7)')
    top = [s for s in signals if s.get('relevance_score', 0) >= 7]
    for s in top[:15]:
        sections.append(f'  [{s.get("relevance_score", 0)}] {s.get("headline", "?")} ({s.get("source", "?")})')
    sections.append('')

    sections.append('## Agent C: Opportunity Clusters')
    sections.append(json.dumps(opportunities[:5], indent=2)[:5000])

    if verifications:
        sections.append('\n## Agent B: Verification Results')
        sections.append(json.dumps(verifications[:5], indent=2)[:8000])

    # Previous context
    cycles = context_summaries.get('cycles', [])
    if cycles:
        sections.append('\n## Previous Cycle Context')
        for c in cycles[-3:]:
            summary = c.get('summary') or c.get('master_synthesis') or c.get('note') or ''
            sections.append(f'Cycle {c["cycle"]}: {summary[:1500]}')
        sections.append('')

    sections.append('\n# INSTRUCTIONS')
    sections.append('Synthesize this cycle\'s results. Produce:')
    sections.append('1. Cross-cycle pattern analysis — what structural shifts are emerging?')
    sections.append('2. Second-order effects — connections between principles that no single signal reveals')
    sections.append('3. Emergent patterns that may not fit P1-P6 — potential new principles')
    sections.append('4. Gaps in our scanning — what are we missing?')
    sections.append('5. Direction for next cycle — what to focus on, what to deprioritize')
    sections.append('6. Grading weight adjustments for next cycle')
    sections.append('7. Kill index updates — what patterns should we stop investigating?')
    sections.append('')
    sections.append('Return a JSON object:')
    sections.append('```json')
    sections.append('''{
  "synthesis": "2-3 paragraph narrative of what this cycle reveals about the economy",
  "cross_principle_patterns": [
    {"pattern": "...", "principles": ["P1", "P2"], "evidence": "...", "strength": "..."}
  ],
  "emergent_principles": [
    {"name": "...", "description": "...", "supporting_evidence": "..."}
  ],
  "scanning_gaps": ["..."],
  "next_cycle_direction": {
    "focus_areas": ["..."],
    "deprioritize": ["..."],
    "new_queries": ["..."],
    "weight_adjustments": {}
  },
  "kill_index_updates": [
    {"pattern": "...", "kill_reason": "...", "still_active": true}
  ],
  "cycle_summary": "1-paragraph summary for context accumulation"
}''')
    sections.append('```')
    sections.append('Return ONLY the JSON object. No preamble.')

    return '\n'.join(sections)


# ---------------------------------------------------------------------------
# Phase 1: SCAN — pull raw data (unchanged from original)
# ---------------------------------------------------------------------------

def phase_scan(verbose=False):
    """Pull data from all 12 connectors and return raw results."""
    print('\n' + '=' * 60)
    print('PHASE 1: SCANNING — pulling live data from 12 connectors')
    print('=' * 60)

    raw = {}
    connector_count = 0

    # --- FRED ---
    print('\n[FRED] Pulling macro economic indicators...')
    try:
        from connectors.fred import FredConnector
        fred = FredConnector()
        raw['fred_labor_squeeze'] = fred.get_labor_cost_squeeze()
        raw['fred_credit_stress'] = fred.get_credit_stress()
        raw['fred_job_gaps'] = fred.get_job_market_gaps()
        raw['fred_rates'] = fred.get_interest_rate_environment()
        raw['fred_profitability'] = fred.get_industry_profitability()
        raw['fred_stress'] = fred.get_market_stress_indicators()
        raw['fred_sector_costs'] = fred.get_sector_employment_costs()
        raw['fred_small_biz'] = fred.get_small_business_indicators()
        raw['fred_assets'] = fred.get_asset_prices_and_transactions()
        connector_count += 1
        print('  [FRED] OK — 9 datasets')
    except Exception as e:
        print(f'  [FRED] ERROR: {e}')

    # --- BLS ---
    print('\n[BLS] Pulling employment and wage data...')
    try:
        from connectors.bls import BLSConnector
        bls = BLSConnector()
        raw['bls_industry'] = bls.get_employment_by_industry()
        raw['bls_wages'] = bls.get_wage_inflation()
        raw['bls_jolts'] = bls.get_job_openings_and_quits()
        raw['bls_occupational'] = bls.get_occupational_exposure()
        raw['bls_wage_premium'] = bls.get_industry_wage_premium()
        connector_count += 1
        print('  [BLS] OK — 5 datasets')
    except Exception as e:
        print(f'  [BLS] ERROR: {e}')

    # --- BEA ---
    print('\n[BEA] Pulling GDP by industry and services trade...')
    try:
        from connectors.bea import BEAConnector
        bea = BEAConnector()
        raw['bea_gdp_by_industry'] = bea.get_gdp_by_industry()
        raw['bea_services_trade'] = bea.get_international_services_trade()
        raw['bea_regional_gdp'] = bea.get_regional_gdp()
        connector_count += 1
        print('  [BEA] OK — 3 datasets')
    except Exception as e:
        print(f'  [BEA] SKIP: {e}')

    # --- Census ---
    print('\n[CENSUS] Pulling business dynamics and establishment data...')
    try:
        from connectors.census import CensusConnector
        census = CensusConnector()
        raw['census_business_dynamics'] = census.get_business_dynamics()
        raw['census_cbp_professional'] = census.get_county_business_patterns(naics='54')
        raw['census_cbp_healthcare'] = census.get_county_business_patterns(naics='62')
        raw['census_nonemployer'] = census.get_nonemployer_statistics()
        connector_count += 1
        print('  [CENSUS] OK — 4 datasets')
    except Exception as e:
        print(f'  [CENSUS] SKIP: {e}')

    # --- EDGAR ---
    print('\n[EDGAR] Scanning SEC filings...')
    try:
        from connectors.edgar import EdgarConnector
        edgar = EdgarConnector()
        raw['edgar_distress'] = edgar.scan_for_distress()
        raw['edgar_ai_failures'] = edgar.scan_for_ai_adoption_failures()
        raw['edgar_ai_risk'] = edgar.scan_ai_risk_factors()
        connector_count += 1
        print('  [EDGAR] OK — 3 scans')
    except Exception as e:
        print(f'  [EDGAR] ERROR: {e}')

    # --- Yahoo Finance ---
    print('\n[MARKET] Pulling sector performance and canary stocks...')
    try:
        from connectors.yfinance import YFinanceConnector
        yf = YFinanceConnector()
        raw['market_sectors'] = yf.get_sector_etf_performance()
        raw['market_staffing_canary'] = yf.get_staffing_canary()
        raw['market_ai_infra'] = yf.get_ai_infrastructure_momentum()
        connector_count += 1
        print('  [MARKET] OK — 3 datasets')
    except Exception as e:
        print(f'  [MARKET] SKIP: {e}')

    # --- Google Trends ---
    print('\n[TRENDS] Pulling search interest signals...')
    try:
        from connectors.google_trends import GoogleTrendsConnector
        gt = GoogleTrendsConnector()
        raw['trends_distress'] = gt.get_distress_signals()
        raw['trends_ai_adoption'] = gt.get_ai_adoption_interest()
        connector_count += 1
        print('  [TRENDS] OK — 2 datasets')
    except Exception as e:
        print(f'  [TRENDS] SKIP: {e}')

    # --- Web Search ---
    print('\n[WEB] Scanning web signals...')
    try:
        from connectors.websearch import WebSearchConnector
        ws = WebSearchConnector()
        raw['web_liquidation'] = ws.scan_liquidation_signals(num_results=5)
        raw['web_practitioner'] = ws.scan_practitioner_pain(num_results=5)
        raw['web_dead_revival'] = ws.scan_dead_business_revival(num_results=5)
        raw['web_demographics'] = ws.scan_demographic_gaps(num_results=5)
        raw['web_inference'] = ws.scan_inference_cost_drops(num_results=5)
        connector_count += 1
        print('  [WEB] OK — 5 scans')
    except Exception as e:
        print(f'  [WEB] ERROR: {e}')

    # --- INTERNATIONAL SOURCES (no keys needed) ---

    # --- World Bank ---
    print('\n[WORLD BANK] Pulling international comparative data...')
    try:
        from connectors.worldbank import WorldBankConnector
        wb = WorldBankConnector()
        raw['wb_business_env'] = wb.get_business_environment_comparison()
        raw['wb_labor_markets'] = wb.get_labor_market_comparison()
        raw['wb_services_trade'] = wb.get_services_trade_flows()
        raw['wb_tech_readiness'] = wb.get_technology_readiness()
        connector_count += 1
        print('  [WORLD BANK] OK — 4 datasets')
    except Exception as e:
        print(f'  [WORLD BANK] SKIP: {e}')

    # --- OECD ---
    print('\n[OECD] Pulling leading indicators and labor stats...')
    try:
        from connectors.oecd import OECDConnector
        oecd = OECDConnector()
        raw['oecd_leading'] = oecd.get_composite_leading_indicators()
        raw['oecd_labor'] = oecd.get_labor_statistics()
        raw['oecd_tech'] = oecd.get_technology_indicators()
        connector_count += 1
        print('  [OECD] OK — 3 datasets')
    except Exception as e:
        print(f'  [OECD] SKIP: {e}')

    # --- Eurostat ---
    print('\n[EUROSTAT] Pulling EU economic data...')
    try:
        from connectors.eurostat import EurostatConnector
        eu = EurostatConnector()
        raw['eu_labor_costs'] = eu.get_labor_cost_index()
        raw['eu_ai_adoption'] = eu.get_ai_adoption()
        raw['eu_biz_demography'] = eu.get_business_demography()
        connector_count += 1
        print('  [EUROSTAT] OK — 3 datasets')
    except Exception as e:
        print(f'  [EUROSTAT] SKIP: {e}')

    print(f'\n  SCAN COMPLETE: {connector_count} connectors, {len(raw)} datasets')
    return raw


# ---------------------------------------------------------------------------
# Phase 1.5: ANALYTICS — compute derived indicators from raw data
# ---------------------------------------------------------------------------

def phase_analytics(raw, verbose=False):
    """Run derived analytics on raw scan data.

    Computes: z-scores, momentum, regime changes, cross-correlations,
    composite indices, structural indicators.
    """
    print('\n' + '=' * 60)
    print('PHASE 1.5: ANALYTICS — computing derived indicators')
    print('=' * 60)

    analytics_result = {}

    try:
        from analytics.timeseries import TimeSeriesAnalyzer
        from analytics.cross_correlation import CrossCorrelator
        from analytics.composite_indices import CompositeIndexBuilder

        ts = TimeSeriesAnalyzer()
        cc = CrossCorrelator()
        ci = CompositeIndexBuilder()

        # Extract FRED series for analytics
        fred_series = {}
        for key, data in raw.items():
            if key.startswith('fred_') and isinstance(data, dict):
                inner_data = data.get('data', {})
                for series_name, series_data in inner_data.items():
                    if isinstance(series_data, dict) and 'observations' in series_data:
                        series_id = series_data.get('series_id', series_name.upper())
                        fred_series[series_id] = series_data

        if fred_series:
            # Time series analysis on each FRED series
            print('  Computing time series indicators...')
            ts_results = {}
            for series_id, data in fred_series.items():
                analysis = ts.analyze_series(data)
                if 'error' not in analysis:
                    ts_results[series_id] = analysis
            analytics_result['timeseries'] = ts_results
            print(f'    Analyzed {len(ts_results)} series')

            # Cross-correlations
            print('  Computing cross-correlations...')
            correlations = cc.analyze_principle_relationships(fred_series)
            analytics_result['cross_correlations'] = correlations
            print(f'    Found {len(correlations)} relationships')

            # Composite indices
            print('  Building composite indices...')
            indices = ci.build_all_indices(fred_series)
            analytics_result['composite_indices'] = indices
            for name, idx in indices.items():
                if 'latest' in idx and idx['latest']:
                    print(f'    {name}: {idx["latest"][1]:.1f}')

    except Exception as e:
        print(f'  ANALYTICS ERROR: {e}')
        if verbose:
            traceback.print_exc()

    return analytics_result


def format_analytics_for_agent(analytics_result):
    """Format analytics output into readable text for LLM consumption."""
    lines = ['## DERIVED ANALYTICS\n']

    # Composite indices
    indices = analytics_result.get('composite_indices', {})
    if indices:
        lines.append('### Composite Principle Indices (0-100 scale)')
        for name, idx in indices.items():
            if idx.get('latest'):
                date, val = idx['latest']
                lines.append(f'- {idx.get("index_name", name)}: {val:.1f} (as of {date})')
                components = idx.get('components', [])
                if components:
                    lines.append(f'  Components: {", ".join(components)}')
        lines.append('')

    # Key cross-correlations
    correlations = analytics_result.get('cross_correlations', {})
    if correlations:
        lines.append('### Key Cross-Correlations')
        for name, rel in correlations.items():
            if isinstance(rel, dict):
                best_lag = rel.get('best_lag', 0)
                best_corr = rel.get('best_correlation', 0)
                desc = rel.get('description', '')
                if best_corr is not None:
                    lines.append(f'- {name}: r={best_corr:.3f}, lag={best_lag} periods')
                    if desc:
                        lines.append(f'  {desc[:200]}')
                # Divergence events
                divs = rel.get('divergence', [])
                if divs:
                    lines.append(f'  DIVERGENCE EVENTS: {len(divs)} detected')
                    for d in divs[:3]:
                        lines.append(f'    {d.get("date", "?")}: z={d.get("z_score", 0):.2f} — {d.get("direction", "?")}')
        lines.append('')

    # Notable regime changes
    ts_results = analytics_result.get('timeseries', {})
    regime_changes = []
    for series_id, analysis in ts_results.items():
        changes = analysis.get('regime_changes', [])
        for rc in changes:
            regime_changes.append((series_id, rc[0], rc[1], rc[2]))

    if regime_changes:
        lines.append('### Regime Changes Detected')
        regime_changes.sort(key=lambda x: abs(x[3]), reverse=True)
        for series_id, date, direction, magnitude in regime_changes[:10]:
            lines.append(f'- {series_id}: {direction} shift at {date} (magnitude: {magnitude:.2f}σ)')
        lines.append('')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Phase 2: AGENT A — LLM-powered signal extraction
# ---------------------------------------------------------------------------

def phase_agent_a(raw, context_summaries, kill_index, analytics_result=None,
                   model='sonnet', verbose=False):
    """Agent A: Extract signals from raw data using LLM reasoning."""
    print('\n' + '=' * 60)
    print('PHASE 2: AGENT A — LLM signal extraction')
    print('=' * 60)

    system_prompt = load_agent_prompt('agent_a_trends_scanner.md')
    user_message = format_raw_for_agent_a(raw, context_summaries, kill_index,
                                           analytics_result=analytics_result)

    print(f'  Sending {len(user_message):,} chars to Agent A...')
    response = llm_call(system_prompt, user_message, model=model, max_tokens=12000)

    if verbose:
        print(f'\n--- Agent A raw response ({len(response)} chars) ---')
        print(response[:2000])
        print('---')

    try:
        signals = parse_json_response(response)
        if isinstance(signals, dict) and 'signals' in signals:
            signals = signals['signals']
        if not isinstance(signals, list):
            signals = [signals]
        print(f'  Agent A produced {len(signals)} signals')
        return signals
    except Exception as e:
        print(f'  ERROR parsing Agent A response: {e}')
        print(f'  Response starts with: {response[:300]}')
        return []


# ---------------------------------------------------------------------------
# Phase 3: AGENT C — LLM-powered grading & clustering
# ---------------------------------------------------------------------------

def phase_agent_c(signals, state, kill_index, model='sonnet', verbose=False):
    """Agent C: Grade, deduplicate, rank, and cluster signals."""
    print('\n' + '=' * 60)
    print('PHASE 3: AGENT C — LLM grading & clustering')
    print('=' * 60)

    system_prompt = load_agent_prompt('agent_c_sync.md')
    user_message = format_for_agent_c(signals, state, kill_index)

    print(f'  Sending {len(user_message):,} chars to Agent C...')
    response = llm_call(system_prompt, user_message, model=model, max_tokens=12000)

    if verbose:
        print(f'\n--- Agent C raw response ({len(response)} chars) ---')
        print(response[:2000])
        print('---')

    try:
        result = parse_json_response(response)
        graded = result.get('graded_signals', signals)
        opportunities = result.get('opportunity_clusters', [])
        patterns = result.get('cross_signal_patterns', [])
        suggestions = result.get('next_cycle_suggestions', [])

        print(f'  Graded {len(graded)} signals')
        print(f'  Identified {len(opportunities)} opportunity clusters')
        print(f'  Found {len(patterns)} cross-signal patterns')

        return {
            'graded_signals': graded,
            'opportunities': opportunities,
            'cross_patterns': patterns,
            'suggestions': suggestions,
        }
    except Exception as e:
        print(f'  ERROR parsing Agent C response: {e}')
        # Return signals as-is with default scoring
        for s in signals:
            s.setdefault('relevance_score', 5.0)
        return {
            'graded_signals': signals,
            'opportunities': [],
            'cross_patterns': [],
            'suggestions': [],
        }


# ---------------------------------------------------------------------------
# Phase 4: AGENT B — LLM-powered verification
# ---------------------------------------------------------------------------

def phase_agent_b(opportunities, signals, state, model='sonnet', verbose=False):
    """Agent B: Verify top opportunities against founding constraints."""
    print('\n' + '=' * 60)
    print('PHASE 4: AGENT B — LLM verification & stress testing')
    print('=' * 60)

    if not opportunities:
        print('  No opportunities to verify. Skipping.')
        return []

    system_prompt = load_agent_prompt('agent_b_practitioner.md')
    user_message = format_for_agent_b(opportunities, signals, state)

    print(f'  Sending {len(user_message):,} chars to Agent B with {len(opportunities[:5])} opportunities...')
    response = llm_call(system_prompt, user_message, model=model, max_tokens=16000)

    if verbose:
        print(f'\n--- Agent B raw response ({len(response)} chars) ---')
        print(response[:2000])
        print('---')

    try:
        verifications = parse_json_response(response)
        if isinstance(verifications, dict):
            verifications = verifications.get('verifications', [verifications])
        if not isinstance(verifications, list):
            verifications = [verifications]
        print(f'  Agent B returned {len(verifications)} verification results')
        for v in verifications:
            verdict = v.get('verdict', {})
            name = v.get('opportunity_name', '?')
            score = verdict.get('viability_score', '?')
            rec = verdict.get('recommendation', '?')
            print(f'    {name}: {score}/10 → {rec}')
        return verifications
    except Exception as e:
        print(f'  ERROR parsing Agent B response: {e}')
        return []


# ---------------------------------------------------------------------------
# Phase 5: MASTER — LLM-powered synthesis
# ---------------------------------------------------------------------------

def phase_master(signals, opportunities, verifications, context_summaries, state,
                 model='sonnet', verbose=False):
    """Master: Synthesize cycle results, identify cross-patterns, set direction."""
    print('\n' + '=' * 60)
    print('PHASE 5: MASTER — LLM synthesis & direction setting')
    print('=' * 60)

    system_prompt = load_agent_prompt('master.md')
    user_message = format_for_master(signals, opportunities, verifications,
                                      context_summaries, state)

    print(f'  Sending {len(user_message):,} chars to Master...')
    response = llm_call(system_prompt, user_message, model=model, max_tokens=8000)

    if verbose:
        print(f'\n--- Master raw response ({len(response)} chars) ---')
        print(response[:2000])
        print('---')

    try:
        synthesis = parse_json_response(response)
        print(f'  Synthesis: {len(synthesis.get("cross_principle_patterns", []))} cross-patterns')
        print(f'  Emergent principles: {len(synthesis.get("emergent_principles", []))}')
        print(f'  Scanning gaps: {len(synthesis.get("scanning_gaps", []))}')
        return synthesis
    except Exception as e:
        print(f'  ERROR parsing Master response: {e}')
        return {'synthesis': response[:3000], 'cycle_summary': response[:1000]}


# ---------------------------------------------------------------------------
# Phase 6: COMPILE — write results to dashboard JSON
# ---------------------------------------------------------------------------

def compile_results(cycle_num, signals, agent_c_result, verifications, master_synthesis):
    """Write all results to data files and dashboard JSON."""
    print('\n' + '=' * 60)
    print('PHASE 6: COMPILING results to dashboard')
    print('=' * 60)

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    graded_signals = agent_c_result.get('graded_signals', signals)
    opportunities = agent_c_result.get('opportunities', [])

    # Update opportunity scores from verifications
    if verifications:
        verified_map = {}
        for v in verifications:
            name = v.get('opportunity_name', '')
            verified_map[name.lower()] = v

        for opp in opportunities:
            v = verified_map.get(opp['name'].lower())
            if v:
                verdict = v.get('verdict', {})
                opp['viability_score'] = verdict.get('viability_score', None)
                opp['recommendation'] = verdict.get('recommendation', 'SCANNING')
                opp['vc_score'] = v.get('opportunity_quality', {}).get('vc_differentiation_score', None)
                opp['verified'] = True
                # Update status based on recommendation
                rec = verdict.get('recommendation', '').upper()
                if rec == 'PURSUE':
                    opp['status'] = 'verified'
                elif rec == 'KILL':
                    opp['status'] = 'killed'
                elif rec == 'INVESTIGATE_FURTHER':
                    opp['status'] = 'investigating'
                elif rec == 'PARK':
                    opp['status'] = 'parked'

    # Sort opportunities by score
    opportunities.sort(key=lambda o: o.get('score', 0), reverse=True)

    # Build sector heatmap
    sector_map = {}
    for s in graded_signals:
        sector = s.get('sector', s.get('affected_industries', ['mixed']))
        if isinstance(sector, list):
            for sec in sector:
                sector_map.setdefault(sec, {'signal_count': 0, 'avg_score': 0, 'total_score': 0})
                sector_map[sec]['signal_count'] += 1
                sector_map[sec]['total_score'] += s.get('relevance_score', 0)
        else:
            sector_map.setdefault(sector, {'signal_count': 0, 'avg_score': 0, 'total_score': 0})
            sector_map[sector]['signal_count'] += 1
            sector_map[sector]['total_score'] += s.get('relevance_score', 0)
    for v in sector_map.values():
        v['avg_score'] = round(v['total_score'] / max(v['signal_count'], 1), 1)
        del v['total_score']

    # Build geography heatmap
    geo_map = {}
    for s in graded_signals:
        geos = s.get('affected_geographies', [s.get('sector', 'US')])
        if isinstance(geos, str):
            geos = [geos]
        for g in geos:
            geo_map.setdefault(g, {'signal_count': 0, 'avg_score': 0, 'total_score': 0})
            geo_map[g]['signal_count'] += 1
            geo_map[g]['total_score'] += s.get('relevance_score', 0)
    for v in geo_map.values():
        v['avg_score'] = round(v['total_score'] / max(v['signal_count'], 1), 1)
        del v['total_score']

    # Dashboard JSON
    verified_count = sum(1 for o in opportunities if o.get('status') == 'verified')
    dashboard = {
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'current_cycle': cycle_num,
        'total_signals_scanned': len(graded_signals),
        'total_opportunities_verified': verified_count,
        'active_opportunities': len([o for o in opportunities if o.get('status') not in ('killed', 'parked')]),
        'top_opportunities': opportunities[:10],
        'sector_heatmap': sector_map,
        'geography_heatmap': geo_map,
        'cycle_history': [],
        'master_synthesis': master_synthesis.get('synthesis', ''),
        'cross_principle_patterns': master_synthesis.get('cross_principle_patterns', []),
        'emergent_principles': master_synthesis.get('emergent_principles', []),
    }

    # Load existing cycle history
    existing = load_json(os.path.join(DATA_DIR, 'ui', 'dashboard.json'))
    if existing and 'cycle_history' in existing:
        dashboard['cycle_history'] = existing['cycle_history']
    dashboard['cycle_history'].append({
        'cycle': cycle_num,
        'signals': len(graded_signals),
        'verified': verified_count,
        'top_score': max((o.get('score', 0) for o in opportunities), default=0),
    })

    # Signals feed JSON
    feed_signals = []
    for s in graded_signals:
        feed_signals.append({
            'headline': s.get('headline', ''),
            'principle': s.get('signal_type', s.get('principle', '?')),
            'category': s.get('source_category', s.get('category', '?')),
            'source': s.get('source_name', s.get('source', '?')),
            'relevance_score': s.get('relevance_score', 0),
            'status': s.get('status', 'new'),
            'detail': s.get('detail', ''),
            'time_horizon': s.get('time_horizon', '?'),
            'confidence': s.get('confidence', 'medium'),
        })
    feed_signals.sort(key=lambda s: s.get('relevance_score', 0), reverse=True)
    signals_feed = {
        'cycle': cycle_num,
        'updated': datetime.now(timezone.utc).isoformat(),
        'recent_signals': feed_signals,
    }

    # Write files
    save_json(os.path.join(DATA_DIR, 'ui', 'dashboard.json'), dashboard)
    save_json(os.path.join(DATA_DIR, 'ui', 'signals_feed.json'), signals_feed)
    save_json(os.path.join(DATA_DIR, 'signals', f'{today}.json'), graded_signals)
    save_json(os.path.join(DATA_DIR, 'opportunities', f'{today}.json'), {
        'cycle': cycle_num, 'date': today, 'opportunities': opportunities,
    })
    if verifications:
        save_json(os.path.join(DATA_DIR, 'verified', f'{today}.json'), {
            'cycle': cycle_num, 'date': today, 'verifications': verifications,
        })

    print(f'  Dashboard: {len(graded_signals)} signals, {len(opportunities)} opportunities')
    print(f'  Verified: {verified_count}')
    print(f'  Files written to data/ui/, data/signals/, data/opportunities/')

    return dashboard


# ---------------------------------------------------------------------------
# Main cycle runner
# ---------------------------------------------------------------------------

def run_cycle(model='sonnet', scan_only=False, analytics_only=False,
              skip_verify=False, verbose=False, use_api=False):
    """Run a full research cycle with LLM-powered agents."""
    global _use_api
    _use_api = use_api

    t0 = time.time()

    print('\n' + '#' * 60)
    print('#  AI ECONOMIC RESEARCH ENGINE — LLM-POWERED CYCLE')
    print(f'#  LLM Mode: {"API" if use_api else "CLI (subscription)"}')
    print('#' * 60)

    # Load state
    state = load_state()
    cycle_num = state.get('current_cycle', 0) + 1
    state['current_cycle'] = cycle_num
    print(f'\nCycle {cycle_num} starting...')
    print(f'Model: {MODELS.get(model, model)}')

    context_summaries = load_context_summaries()
    kill_index = load_kill_index()

    # Phase 1: SCAN
    raw = phase_scan(verbose=verbose)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    save_json(os.path.join(DATA_DIR, 'raw', f'{today}.json'), raw)

    if scan_only:
        print('\n  --scan-only: stopping after data pull.')
        save_state(state)
        return

    # Phase 1.5: ANALYTICS
    analytics_result = phase_analytics(raw, verbose=verbose)
    save_json(os.path.join(DATA_DIR, 'analytics', f'{today}.json'), analytics_result)

    if analytics_only:
        print('\n  --analytics-only: stopping after analytics.')
        save_state(state)
        return

    # Phase 2: AGENT A
    signals = phase_agent_a(raw, context_summaries, kill_index,
                             analytics_result=analytics_result, model=model, verbose=verbose)
    if not signals:
        print('\n  ERROR: Agent A produced no signals. Aborting cycle.')
        save_state(state)
        return

    # Phase 3: AGENT C
    agent_c_result = phase_agent_c(signals, state, kill_index, model=model, verbose=verbose)
    opportunities = agent_c_result.get('opportunities', [])

    # Phase 4: AGENT B (optional — can skip for fast iterations)
    verifications = []
    if not skip_verify and opportunities:
        verifications = phase_agent_b(opportunities, signals, state, model=model, verbose=verbose)

        # Update kill index from KILL verdicts
        for v in verifications:
            verdict = v.get('verdict', {})
            if verdict.get('recommendation', '').upper() == 'KILL':
                kill_reason = verdict.get('kill_reason', 'Unknown')
                kill_index['kill_patterns'].append({
                    'pattern_id': f'K-{cycle_num}-{len(kill_index["kill_patterns"])+1}',
                    'created_cycle': cycle_num,
                    'kill_reason': kill_reason,
                    'signal_type_affected': '',
                    'industries_affected': [],
                    'still_active': True,
                })
        save_kill_index(kill_index)

    # Phase 5: MASTER
    master_synthesis = phase_master(
        agent_c_result.get('graded_signals', signals),
        opportunities, verifications, context_summaries, state,
        model=model, verbose=verbose,
    )

    # Save context summary for next cycle
    cycle_summary = master_synthesis.get('cycle_summary',
                                         master_synthesis.get('synthesis', 'No summary'))
    if isinstance(cycle_summary, str):
        save_context_summary(cycle_num, cycle_summary)

    # Phase 6: COMPILE
    dashboard = compile_results(cycle_num, signals, agent_c_result,
                                verifications, master_synthesis)

    # Update state
    graded = agent_c_result.get('graded_signals', signals)
    above_threshold = sum(1 for s in graded if s.get('relevance_score', 0) >= 5)
    avg_score = (sum(s.get('relevance_score', 0) for s in graded) / max(len(graded), 1))
    state['agent_a'] = {
        'signals_produced': len(signals),
        'signals_above_threshold': above_threshold,
        'avg_relevance_score': round(avg_score, 2),
    }
    state['agent_b'] = {
        'verifications_completed': len(verifications),
        'pursue_count': sum(1 for v in verifications
                           if v.get('verdict', {}).get('recommendation', '').upper() == 'PURSUE'),
        'kill_count': sum(1 for v in verifications
                          if v.get('verdict', {}).get('recommendation', '').upper() == 'KILL'),
    }
    state['last_run'] = datetime.now(timezone.utc).isoformat()
    state['next_cycle_direction'] = master_synthesis.get('next_cycle_direction', {})
    save_state(state)

    elapsed = time.time() - t0
    print('\n' + '#' * 60)
    print(f'#  CYCLE {cycle_num} COMPLETE — {elapsed:.1f}s')
    print(f'#  Signals: {len(signals)} | Opportunities: {len(opportunities)} | Verified: {len(verifications)}')
    print(f'#  LLM tokens: {_total_input_tokens:,} in / {_total_output_tokens:,} out')
    print('#' * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='AI Economic Research Engine — LLM Cycle Runner')
    parser.add_argument('--model', default='sonnet',
                        choices=['sonnet', 'opus', 'haiku'],
                        help='Claude model (default: sonnet)')
    parser.add_argument('--scan-only', action='store_true',
                        help='Only pull data, skip analytics and LLM processing')
    parser.add_argument('--analytics-only', action='store_true',
                        help='Run scan + analytics, skip LLM processing')
    parser.add_argument('--skip-verify', action='store_true',
                        help='Skip Agent B verification (faster cycles)')
    parser.add_argument('--use-api', action='store_true',
                        help='Use Anthropic API instead of Claude Code CLI')
    parser.add_argument('--verbose', action='store_true',
                        help='Print raw LLM responses')
    args = parser.parse_args()

    try:
        run_cycle(
            model=args.model,
            scan_only=args.scan_only,
            analytics_only=args.analytics_only,
            skip_verify=args.skip_verify,
            use_api=args.use_api,
            verbose=args.verbose,
        )
    except RuntimeError as e:
        print(f'\n  SETUP ERROR: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'\n  FATAL ERROR: {e}')
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
