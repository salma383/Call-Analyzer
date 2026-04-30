"""
MyVA Call Analyzer — utility functions.
Transcription (Groq Whisper), scoring (GPT-4.1-mini), email extraction,
temperature determination, audit logging.
"""

import hashlib
import json
import os
import re
import tempfile
import time
import datetime
from concurrent.futures import ThreadPoolExecutor

from criteria import WHISPER_VOCAB, WHISPER_HALLUCINATIONS, TEMP_LOGIC


# ─── Filename sanitization ───────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    if not name or not name.strip():
        return "unnamed"
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:100] if cleaned else "unnamed"


# ─── Audio file hashing (for transcript caching) ─────────────────────────────

def hash_audio_file(uploaded_file) -> str:
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return hashlib.md5(data).hexdigest()


# ─── Retry wrapper ────────────────────────────────────────────────────────────

def call_with_retry(fn, *args, max_retries=3, **kwargs):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_name = type(e).__name__
            is_transient = (
                "RateLimitError" in err_name
                or "APIStatusError" in err_name
                or "APIConnectionError" in err_name
            )
            if is_transient and attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
                last_exc = e
                continue
            raise
    raise last_exc


# ─── Hallucination deduplication ─────────────────────────────────────────────

def _dedupe_consecutive_lines(lines: list[str]) -> list[str]:
    """
    Remove consecutive duplicate lines that Whisper emits when it gets stuck
    repeating itself (e.g. 'All right. All right. All right.').
    Keeps the first occurrence of each run.
    """
    if not lines:
        return lines
    out = [lines[0]]
    for line in lines[1:]:
        body = re.sub(r'^\[\d{2}:\d{2}\]\s*', '', line).strip().lower()
        prev_body = re.sub(r'^\[\d{2}:\d{2}\]\s*', '', out[-1]).strip().lower()
        if body != prev_body:
            out.append(line)
    return out


def _filter_hallucinations(lines: list[str]) -> list[str]:
    """Drop lines whose full text matches a known Whisper hallucination phrase."""
    result = []
    for line in lines:
        body = re.sub(r'^\[\d{2}:\d{2}\]\s*', '', line).strip().lower()
        if not any(body == h.lower() for h in WHISPER_HALLUCINATIONS):
            result.append(line)
    return result


# ─── Transcription (Groq Whisper) ────────────────────────────────────────────

_WHISPER_PROMPT = (
    "Real estate and business acquisition sales call. "
    f"Vocab: {WHISPER_VOCAB}. "
    "Prospects often spell their name and email letter by letter, "
    "sometimes using phonetic alphabet: 'N as in Nancy', 'T as in Tom'. "
    "They may say 'at gmail dot com' for @gmail.com."
)


def transcribe_audio(client_groq, audio_file):
    """
    Transcribe audio via Groq Whisper (whisper-large-v3).
    Returns (transcript_text, segments, display_transcript).

    NOTE: We do NOT pass temperature=0. Whisper's default uses a fallback
    chain (0→0.2→0.4…) when segments are low-confidence. Forcing temp=0
    disables that chain and causes Whisper to silently drop hard segments.
    """
    suffix = f".{audio_file.name.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            resp = call_with_retry(
                client_groq.audio.transcriptions.create,
                file=(os.path.basename(tmp_path), f.read()),
                model="whisper-large-v3",
                prompt=_WHISPER_PROMPT,
                response_format="verbose_json",
                language="en",
                # temperature intentionally omitted — let Whisper use its
                # internal fallback chain so hard segments don't get dropped
            )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    transcript_text = (_get(resp, "text", "") or "").strip()
    segments = _get(resp, "segments", []) or []

    # Build timestamped display lines from segments
    raw_lines = []
    for seg in segments:
        start = _get(seg, "start", 0) or 0
        text = (_get(seg, "text", "") or "").strip()
        if not text:
            continue
        mins = int(start) // 60
        secs = int(start) % 60
        raw_lines.append(f"[{mins:02d}:{secs:02d}] {text}")

    # Clean: dedup loops + filter hallucinations
    raw_lines = _dedupe_consecutive_lines(raw_lines)
    raw_lines = _filter_hallucinations(raw_lines)

    display_transcript = "\n".join(raw_lines) if raw_lines else transcript_text

    return transcript_text, segments, display_transcript


# ─── Spelled-out email / address reconstruction ──────────────────────────────

def reconstruct_spelled_out(text: str) -> str:
    if not text:
        return text

    # Strip "X as in Word" / "X for Word" → keep just X
    text = re.sub(
        r'\b([A-Za-z])\s+(?:as in|for|like)\s+[A-Za-z]+',
        r'\1', text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r'\b([A-Za-z]{2,})\s+(?:as in|for|like)\s+[A-Za-z]+',
        r'\1', text, flags=re.IGNORECASE,
    )

    # Collapse sequences of single spaced letters/digits
    text = re.sub(r'\b([a-zA-Z0-9] ){2,}[a-zA-Z0-9]\b',
                  lambda m: m.group(0).replace(" ", ""), text)

    # "word at domain dot tld" → "word@domain.tld"
    text = re.sub(
        r'(\b[a-zA-Z0-9][a-zA-Z0-9._+-]*) at (\w+) dot '
        r'(com|net|org|edu|gov|io|co|us|info|biz|me)\b',
        r'\1@\2.\3', text, flags=re.IGNORECASE,
    )

    # "@domain dot tld" remaining dots
    text = re.sub(r'(@\w+) dot (\w+)', r'\1.\2', text)

    # Spaced street numbers
    street_words = (
        r'(?:street|st|avenue|ave|boulevard|blvd|drive|dr|road|rd|lane|ln|'
        r'court|ct|place|pl|way|circle|cir|terrace|ter|parkway|pkwy|highway|hwy|'
        r'north|south|east|west|main|oak|elm|maple|pine|cedar|walnut|broadway)'
    )
    text = re.sub(
        rf'(\b\d(?: \d){{1,5}})\s+({street_words}\b)',
        lambda m: f"{m.group(1).replace(' ', '')} {m.group(2)}",
        text, flags=re.IGNORECASE,
    )

    return text


# ─── Email extraction helpers ─────────────────────────────────────────────────

def _looks_like_spelled_email(text: str) -> bool:
    """Return True when the transcript shows signs of a spelled or dictated email."""
    patterns = [
        r'\bat\s+\w+\s+dot\s+(?:com|net|org|io|me|co|us)\b',
        r'\b[a-z]\s+[a-z]\s+[a-z]\s+[a-z]\b',   # spaced letters
        r'\b(?:as in|for|like)\s+[A-Z][a-z]+\b',  # phonetic alphabet
        r'@gmail|@yahoo|@hotmail|@icloud|@outlook',
        r'[a-z0-9]\s+at\s+gmail',
    ]
    low = text.lower()
    return any(re.search(p, low) for p in patterns)


def extract_email(openai_client, transcript: str) -> str | None:
    """
    Dedicated GPT-4.1-mini pass for resolving the prospect's email.
    Only called when transcript shows spelled/phonetic email patterns.
    Returns a clean email string or None.
    """
    prompt = f"""You resolve a SINGLE email address from a phone call transcript.

Rules — follow exactly:
1. If the prospect was asked for an email but did NOT give one, return null.
2. If letters were spelled phonetically ("sierra alpha romeo alpha" or "S as in Sam"), JOIN the letters into one word.
3. If letters were spelled hyphen-style ("D-U-S-T-I-N"), join into one word.
4. "at <Company>" or "at <Company> dot com" = "@company.com".
5. "dot" between name parts = literal dot (e.g. "john dot smith" = "john.smith").
6. If the prospect CORRECTED themselves ("not plural", "without the s", "actually it's..."), use the CORRECTED version.
7. The prospect's spelling overrides the agent's readback.
8. Always lowercase the final email.
9. If multiple emails appear, return the PROSPECT's (not the agent's).

Return JSON: {{ "email": "<resolved email>" or null, "confidence": "high" | "medium" | "low" }}

TRANSCRIPT:
{transcript}
"""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            timeout=45,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        email = data.get("email")
        if email and isinstance(email, str):
            email = email.strip().lower()
            if re.fullmatch(r'[\w.+\-]+@[\w.\-]+\.[a-z]{2,}', email):
                return email
        return None
    except Exception:
        return None


def _inject_email(template_text: str, email: str) -> str:
    """Overwrite the Email field in the lead template with the extracted email."""
    patterns = [
        r'^(\s*Email Address\s*:)\s*.*$',
        r'^(\s*E-?mail\s*:)\s*.*$',
        r'^(\s*Owner Email\s*:)\s*.*$',
    ]
    for pat in patterns:
        template_text = re.sub(
            pat,
            lambda m: f"{m.group(1)} {email}",
            template_text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    return template_text


def _scrub_preliminary_text(template_text: str, temp: str | None) -> str:
    """Strip any leftover 'Preliminary — recalculate after MV' text from the Temp line."""
    if not template_text:
        return template_text

    def _fix_temp_line(match):
        label = match.group(1)
        body  = match.group(2)
        cleaned = re.sub(
            r'\b(?:preliminary|recalc(?:ulate)?|after\s+mv|tbd|unknown|pending)\b.*$',
            '', body, flags=re.IGNORECASE,
        ).strip(" -—–()[]:.,")
        cleaned = re.sub(r'\s*[\(\[][^)]*[\)\]]\s*$', '', cleaned).strip()
        if not cleaned and temp:
            cleaned = temp
        return f"{label} {cleaned}" if cleaned else f"{label} {temp or ''}"

    return re.sub(
        r'^((?:Lead\s+)?Temp(?:erature)?\s*:)\s*(.*)$',
        _fix_temp_line,
        template_text,
        flags=re.IGNORECASE | re.MULTILINE,
    )


# ─── Temperature recalculation (Python-side, after user enters MV) ───────────

def recalculate_temp(call_data: dict, mv: float | None) -> str:
    """
    Re-apply the TEMP_LOGIC rules in Python given call_data extracted by GPT
    and a user-supplied MV. Returns the new concrete temperature string.

    call_data shape: {
      "ap": <float|null>,
      "has_valid_motive": <bool>,
      "timeline_months": <float|null>,
      "open_to_listing": <bool>
    }
    """
    ap              = call_data.get("ap")
    has_motive      = bool(call_data.get("has_valid_motive", False))
    timeline        = call_data.get("timeline_months")
    open_to_listing = bool(call_data.get("open_to_listing", False))

    if not has_motive:
        return "Cold"

    if timeline is not None:
        if timeline > 12:
            return "Nurture"
        if timeline >= 10:
            return "Cold"

    # Short / ASAP timeline (≤ 3 months) or timeline unknown
    if timeline is None or timeline <= 3:
        if mv is None:
            # No MV — pick based on motivation + attitude
            return "Hot" if has_motive else "Warm"
        if ap is not None:
            if ap < mv:
                return "Hot"
            if open_to_listing:
                return "Warm"
            return "Cold"
        return "Warm"

    # Mid timeline (3–10 months)
    return "Warm"


# ─── Prompt construction ─────────────────────────────────────────────────────

def build_scoring_prompt(client_name, criteria, agent_name, call_date,
                         transcript_text, template, universal_rules,
                         stamped_transcript: str = ""):
    checklist_str  = "\n".join(f"- {x}" for x in criteria["checklist"])
    universal_str  = "\n".join(f"- {x}" for x in universal_rules)
    redflags_str   = "\n".join(f"- {r}" for r in criteria["red_flags"])
    disq_str       = "\n".join(f"- {d}" for d in criteria["hard_disqualifiers"])

    is_re = criteria.get("type") == "real_estate"
    mv_note = (
        "Market Value / MV / Zestimate field must NEVER be filled — leave it blank. "
        "The user will look it up on Zillow/Realtor.com manually.\n"
        if is_re else ""
    )
    temp_section = f"""
6. "preliminary_temp": one of Hot / Warm / Cold / Nurture / Throwaway (real estate only, else null).
   ALWAYS return your best concrete pick — never null, never "Preliminary", never "TBD".
   Use this logic:
{TEMP_LOGIC}

6b. "temp_is_preliminary": boolean. True only if MV would meaningfully change your pick.
    False if call has hard disqualifier, no valid motive, very long timeline, or any
    signal strong enough that MV cannot change the answer.

7. "call_data": object used for recalculation when user supplies MV:
   {{ "ap": <asking price as number or null>, "has_valid_motive": <true|false>,
      "timeline_months": <estimated months or null>, "open_to_listing": <true|false> }}
""" if is_re else ""

    numbered_stamped = ""
    if stamped_transcript:
        lines = [l for l in stamped_transcript.splitlines() if l.strip()]
        numbered_stamped = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))

    return f"""You are an expert call quality analyst for MyVA.
Analyze this transcript and respond ONLY in valid JSON (no markdown, no preamble).

CLIENT LABEL (the company being serviced — NOT the prospect): {client_name}
FRAMEWORK: {criteria['framework']}
AGENT (the MyVA rep making the call — NOT the prospect): {agent_name or 'Unknown'}
SCRIPT NOTES: {criteria.get('script_notes', '')}

CRITICAL — CONTACT NAME BOUNDARY:
"Contact Name" / "Prospect Name" / "Owner Name" refers to the PROSPECT (the person being called).
It is NEVER "{client_name}" and NEVER "{agent_name or 'Unknown'}".
If the prospect's name is not clearly stated, write "Not captured".

--- TRANSCRIPT ---
{transcript_text}
--- END TRANSCRIPT ---

CHECKLIST:
{checklist_str}

UNIVERSAL RULES:
{universal_str}

HARD DISQUALIFIERS:
{disq_str}

RED FLAGS:
{redflags_str}

LEAD TEMPLATE TO FILL:
{template}

Instructions for lead template:
- Fill every field using ONLY information extracted from the transcript.
- If a field was not discussed, write "Not captured".
- For the agent name/date line, use: {agent_name or '[Agent Name]'} / {call_date}
- For Call Recording: leave as "[Paste link here]"
- {mv_note}- For real estate clients: fill the Temp line with a single concrete word
  (Hot / Warm / Cold / Nurture / Throwaway). NEVER write "Preliminary", "recalculate
  after MV", "TBD", "unknown", or "pending" in the Temp line.
- Preserve the exact template structure including all labels.

EMAIL EXTRACTION — follow every rule:
- "X as in Word" or "X for Word" → only the letter X, discard the reference word.
- Hyphened letters ("D-U-S-T-I-N") → join into one word ("dustin").
- "at <Company>" or "at <Company> dot com" → "@company.com".
- "dot" between parts → literal dot: "john dot smith" → "john.smith".
- Concatenate ALL spoken letters/digits in sequence for the local-part.
- If prospect CORRECTED themselves ("not plural", "without the s", "actually it's…"),
  use the CORRECTED version, always.
- Always lowercase the final email.
- Example: "MCC L, EESE as in Earl, N as in Nancy, T as in Tom 85 at gmail dot com"
  → mccleesent85@gmail.com

CRITICAL — ASR-MANGLED GMAIL:
A lone "Mail" (no preceding G) almost always means "gmail" where the G got dropped.
"3308 Jim Carr Incorporated. Mail." → 3308jimcarrincorporated@gmail.com

Respond with this exact JSON:
{{
  "overall_score": <0-100>,
  "disposition_suggested": "<Hot/Warm/Cold/Not Interested/Appointment Set/etc.>",
  "qualified": <true/false>,
  "disqualifier_triggered": "<disqualifier name or null>",
  "lead_template_filled": "<the filled template as a plain string, newlines as \\n>",
  "checklist_results": [
    {{"item": "<text>", "result": "<YES/NO/PARTIAL/N/A>", "note": "<observation>"}}
  ],
  "universal_results": [
    {{"item": "<text>", "result": "<YES/NO/PARTIAL/N/A>", "note": "<observation>"}}
  ],
  "red_flags_found": ["<flag>"],
  "coaching_notes": ["<note1>", "<note2>", "<note3>"],
  "strengths": ["<strength1>", "<strength2>"],
  "summary": "<2-3 sentence summary>",
  "speaker_labels": ["<A or P per numbered line in STAMPED TRANSCRIPT>"],
  "preliminary_temp": "<Hot|Warm|Cold|Nurture|Throwaway or null>",
  "temp_is_preliminary": <true|false>,
  "call_data": {{"ap": <number or null>, "has_valid_motive": <true|false>, "timeline_months": <number or null>, "open_to_listing": <true|false>}}
}}

STAMPED TRANSCRIPT (numbered lines — use for "speaker_labels" field, one A or P per line):
{numbered_stamped if numbered_stamped else '(none)'}
"""


# ─── JSON parsing ─────────────────────────────────────────────────────────────

def parse_llm_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for suffix in ["}", '"}', '"]}', '"]}}']:
        try:
            return json.loads(text + suffix)
        except json.JSONDecodeError:
            continue
    matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if matches:
        longest = max(matches, key=len)
        try:
            return json.loads(longest)
        except json.JSONDecodeError:
            pass
    return {"parse_error": True, "raw": raw}


# ─── Scoring (GPT-4.1-mini via OpenAI) ────────────────────────────────────────

def score_transcript(openai_client, prompt: str) -> dict:
    """Score the call using GPT-4.1-mini. Returns parsed JSON result dict."""
    resp = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
        timeout=90,
    )
    raw = resp.choices[0].message.content.strip()
    return parse_llm_json(raw)


# ─── Speaker-labeled transcript builder ───────────────────────────────────────

def build_labeled_transcript(stamped_transcript: str, labels: list[str], agent_name: str) -> str:
    """
    Merge stamped transcript with A/P labels from GPT into a readable,
    speaker-tagged display.
    """
    lines = [l for l in stamped_transcript.splitlines() if l.strip()]
    merged = []
    for i, line in enumerate(lines):
        m = re.match(r'(\[\d{2}:\d{2}\])\s+(.*)', line)
        if not m:
            merged.append(line)
            continue
        stamp, text = m.group(1), m.group(2)
        label   = labels[i] if i < len(labels) else "A"
        speaker = agent_name if label == "A" else "Prospect"
        arrow   = "→" if label == "A" else "◆"
        merged.append(f"{stamp} {arrow} {speaker}: {text}")
    return "\n".join(merged)


# ─── Transcript chunking for very long calls ──────────────────────────────────

def chunk_transcript(text: str, max_tokens=6000) -> list:
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current, current_len = [], [], 0
    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current))
            current, current_len = [sentence], len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def merge_scoring_results(results: list) -> dict:
    if len(results) == 1:
        return results[0]
    merged = {
        "overall_score":         min(r.get("overall_score", 0) for r in results),
        "disposition_suggested": results[0].get("disposition_suggested", "—"),
        "qualified":             any(r.get("qualified", False) for r in results),
        "disqualifier_triggered": None,
        "lead_template_filled":  results[0].get("lead_template_filled", ""),
        "checklist_results":     [],
        "universal_results":     [],
        "red_flags_found":       [],
        "coaching_notes":        [],
        "strengths":             [],
        "summary":               "",
        "speaker_labels":        results[0].get("speaker_labels", []),
        "preliminary_temp":      results[0].get("preliminary_temp"),
        "temp_is_preliminary":   results[0].get("temp_is_preliminary", False),
        "call_data":             results[0].get("call_data", {}),
    }
    seen_checklist = set()
    seen_universal = set()
    seen_flags     = set()
    seen_coaching  = set()
    seen_strengths = set()
    summaries      = []
    for r in results:
        if not merged["disqualifier_triggered"] and r.get("disqualifier_triggered"):
            merged["disqualifier_triggered"] = r["disqualifier_triggered"]
        for item in r.get("checklist_results", []):
            key = item.get("item", "")
            if key not in seen_checklist:
                seen_checklist.add(key)
                merged["checklist_results"].append(item)
        for item in r.get("universal_results", []):
            key = item.get("item", "")
            if key not in seen_universal:
                seen_universal.add(key)
                merged["universal_results"].append(item)
        for flag in r.get("red_flags_found", []):
            if flag not in seen_flags:
                seen_flags.add(flag)
                merged["red_flags_found"].append(flag)
        for note in r.get("coaching_notes", []):
            if note not in seen_coaching:
                seen_coaching.add(note)
                merged["coaching_notes"].append(note)
        for s in r.get("strengths", []):
            if s not in seen_strengths:
                seen_strengths.add(s)
                merged["strengths"].append(s)
        if r.get("summary"):
            summaries.append(r["summary"])
    merged["summary"] = " ".join(summaries)
    return merged


# ─── Audit logging ───────────────────────────────────────────────────────────

def append_audit_log(entry: dict, log_path="audit_log.jsonl"):
    entry["logged_at"] = datetime.datetime.now().isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
