"""
MyVA Call Analyzer — utility functions.
Transcription, scoring, caching, email reconstruction, audit logging.
"""

import hashlib
import json
import os
import re
import tempfile
import time
import datetime


# ─── Filename sanitization ───────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Replace non-alphanumeric chars with underscore, truncate to 100 chars."""
    if not name or not name.strip():
        return "unnamed"
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:100] if cleaned else "unnamed"


# ─── Audio file hashing (for transcript caching) ─────────────────────────────

def hash_audio_file(uploaded_file) -> str:
    """Return MD5 hex digest of file contents, then reset seek position."""
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return hashlib.md5(data).hexdigest()


# ─── Retry wrapper for Groq API calls ────────────────────────────────────────

def call_with_retry(fn, *args, max_retries=3, **kwargs):
    """Call fn(*args, **kwargs) with exponential backoff on transient errors."""
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


# ─── Transcription (Groq Whisper) ────────────────────────────────────────────

# Phonetic-aware Whisper prompt: domain vocab + spelling guidance.
# Whisper uses the prompt as style/context hints, not as instructions.
# Keeping it to example phrases helps it transcribe similar speech accurately.
_WHISPER_PROMPT = (
    "Real estate and business acquisition sales call. "
    "Vocab: mortgage, equity, foreclosure, tax lien, sqft, owner-occupied, "
    "Zillow, MLS, realtor, cash offer, escrow, HOA, appraisal, earnest money, "
    "refinance, ARV, EBITDA, ReSimpli, HubSpot, GHL, Call Tools, Enzo, "
    "Rejigg, Loftey, Barracuda, Integrity, Haven Senior, Biancardi, "
    "Smithton, Boone, CIC Partners, Giancarlo, Shiraz, Stuart Moss. "
    "Prospects often spell their name and email letter by letter, "
    "sometimes using phonetic alphabet: 'N as in Nancy', 'T as in Tom', "
    "'J for Juliet'. They may say 'at gmail dot com' for @gmail.com. "
    "Example: MCC L, EESE as in Earl, N as in Nancy, T as in Tom 85 at gmail dot com."
)


def transcribe_audio(client_groq, audio_file):
    """
    Transcribe audio via Groq Whisper (whisper-large-v3).
    Returns (transcript_text, segments, display_transcript).

    Whisper has no speaker diarization, so `display_transcript` is the
    plain text (optionally with segment timestamps). `segments` is the
    list of verbose_json segments (may be empty).
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
                temperature=0.0,
                language="en",
            )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Groq SDK returns a pydantic-like object; access via attribute or dict
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    transcript_text = (_get(resp, "text", "") or "").strip()
    segments = _get(resp, "segments", []) or []

    # Build a timestamped display transcript from segments if available
    display_lines = []
    for seg in segments:
        start = _get(seg, "start", 0) or 0
        text = (_get(seg, "text", "") or "").strip()
        if not text:
            continue
        mins = int(start) // 60
        secs = int(start) % 60
        display_lines.append(f"[{mins:02d}:{secs:02d}] {text}")

    display_transcript = "\n".join(display_lines) if display_lines else transcript_text

    return transcript_text, segments, display_transcript


# ─── Spelled-out email / address reconstruction ──────────────────────────────

def reconstruct_spelled_out(text: str) -> str:
    """
    Fix spelled-out emails and addresses in transcribed text.
    e.g. "s a l m a at gmail dot com" → "salma@gmail.com"
    e.g. "1 2 3 Main Street" → "123 Main Street"
    """
    if not text:
        return text

    # Step 0a: Strip phonetic alphabet — "X as in Word" / "X for Word" / "X like Word" → "X"
    # Handles "N as in Nancy" → "N" and the ASR-glued case "t as in tom85@gmail.com" → "t85@gmail.com"
    text = re.sub(
        r'\b([A-Za-z])\s+(?:as in|for|like)\s+[A-Za-z]+',
        r'\1',
        text,
        flags=re.IGNORECASE,
    )

    # Step 0b: Strip phonetic clarifier after multi-letter groups — "EESE as in Earl" → "EESE"
    text = re.sub(
        r'\b([A-Za-z]{2,})\s+(?:as in|for|like)\s+[A-Za-z]+',
        r'\1',
        text,
        flags=re.IGNORECASE,
    )

    # Step 1: Fix spelled-out emails
    # Pattern: single chars separated by spaces, followed by "at" and domain parts
    # Match: "s a l m a at g m a i l dot c o m" or "s a l m a at gmail dot com"
    def _join_spaced_letters(match):
        letters = match.group(0)
        # Join single-char tokens separated by spaces
        return re.sub(r'(?<= )([a-zA-Z0-9]) (?=[a-zA-Z0-9]( |$))', r'\1', letters)

    # Find sequences of single characters separated by spaces (3+ chars)
    # near email context words (at, dot, @)
    email_pattern = r'(?i)\b([a-zA-Z0-9] ){2,}[a-zA-Z0-9]\b'

    def _reconstruct_email_sequence(match):
        seq = match.group(0)
        # Join all single-spaced characters
        joined = seq.replace(" ", "")
        return joined

    # Replace sequences of spaced single chars (min 3 chars like "a b c")
    text = re.sub(r'\b([a-zA-Z0-9] ){2,}[a-zA-Z0-9]\b', _reconstruct_email_sequence, text)

    # Step 2: Fix "at" → "@" in email context (word at word dot word)
    text = re.sub(
        r'(\b[a-zA-Z0-9][a-zA-Z0-9._+-]*) at (\w+) dot (com|net|org|edu|gov|io|co|us|info|biz|me)\b',
        r'\1@\2.\3',
        text,
        flags=re.IGNORECASE,
    )

    # Step 3: Fix remaining "dot" in domain context (already has @)
    text = re.sub(
        r'(@\w+) dot (\w+)',
        r'\1.\2',
        text,
    )

    # Step 4: Fix spaced-out street numbers before street words
    # "1 2 3 Main" → "123 Main"
    street_words = (
        r'(?:street|st|avenue|ave|boulevard|blvd|drive|dr|road|rd|lane|ln|'
        r'court|ct|place|pl|way|circle|cir|terrace|ter|parkway|pkwy|highway|hwy|'
        r'north|south|east|west|main|oak|elm|maple|pine|cedar|walnut|broadway)'
    )
    def _fix_street_numbers(match):
        digits = match.group(1).replace(" ", "")
        rest = match.group(2)
        return f"{digits} {rest}"

    text = re.sub(
        rf'(\b\d(?: \d){{1,5}})\s+({street_words}\b)',
        _fix_street_numbers,
        text,
        flags=re.IGNORECASE,
    )

    return text


# ─── Prompt construction ─────────────────────────────────────────────────────

def build_scoring_prompt(client_name, criteria, agent_name, call_date,
                         transcript_text, template, universal_rules):
    """Build the LLM scoring prompt from criteria and transcript."""
    checklist_str = "\n".join([f"{i+1}. {x}" for i, x in enumerate(criteria["checklist"])])
    universal_str = "\n".join([f"{i+1}. {x}" for i, x in enumerate(universal_rules)])
    redflags_str = "\n".join([f"- {r}" for r in criteria["red_flags"]])
    disq_str = "\n".join([f"- {d}" for d in criteria["hard_disqualifiers"]])

    return f"""You are an expert call quality analyst for MyVA.
Analyze this transcript and respond ONLY in valid JSON (no markdown, no preamble).

CLIENT LABEL (the company/account being serviced — NOT the prospect): {client_name}
FRAMEWORK: {criteria['framework']}
AGENT (the MyVA rep making the call — NOT the prospect): {agent_name or 'Unknown'}
SCRIPT NOTES: {criteria['script_notes']}

CRITICAL — CONTACT NAME BOUNDARY:
The "Contact Name" / "Prospect Name" / "Owner Name" field in the lead template refers to
the PROSPECT (the person being called — the business owner, homeowner, etc.).
It is NEVER the client label above ("{client_name}") and NEVER the agent name ("{agent_name or 'Unknown'}").
If the prospect's name is not clearly stated in the transcript, write "Not captured".
Do NOT copy the client label or agent name into the contact field.

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
- Fill every field using ONLY information extracted from the transcript
- If a field was not discussed, write "Not captured"
- For the agent name/date line, use: {agent_name or '[Agent Name]'} / {call_date}
- For Call Recording: leave as "[Paste link here]"
- Preserve the exact template structure including all labels
- Write email addresses as complete addresses (e.g. salma@gmail.com), never spelled out letter by letter

CRITICAL — DECODING SPELLED-OUT EMAILS:
When a prospect spells an email, apply these rules strictly:
1. "X as in Word" or "X for Word" or "X like Word" means ONLY the letter X — discard the reference word.
   Example: "N as in Nancy" → N    "T for Tango" → T
2. Letter groups like "MCC" or "EESE" mean each letter separately — keep every letter.
   Example: "MCC" → M, C, C    "EESE" → E, E, S, E
3. Concatenate ALL letters (and digits) spelled before "@" into the username. Ignore commas/spaces between letters.
4. If the transcript contains a typo-like guess at the start (e.g. "McLease.") followed by the spelling, IGNORE the guess and use ONLY the spelled letters.
5. Lowercase the final email address.

Worked example:
  Transcript: "Yes, it's McLease. MCC L, EESE as in Earl, N as in Nancy, T as in Tom 85 at gmail dot com"
  Discard "McLease" (initial guess). Collect spelled letters in order:
    MCC → m,c,c
    L   → l
    EESE (clarified by "as in Earl") → e,e,s,e
    N (as in Nancy) → n
    T (as in Tom) → t
  Followed by "85 at gmail dot com" → "85@gmail.com"
  FINAL: mccleesent85@gmail.com

Another example:
  Transcript: "j as in john, o, h, n at yahoo dot com"
  Letters: j, o, h, n → "john"
  FINAL: john@yahoo.com

CRITICAL — ASR-MANGLED GMAIL ADDRESSES:
Speech recognition often mangles "gmail.com" into fragments. Recognize these patterns:
- A lone word "Mail" (capitalized, often after a period) with no preceding "G" is almost
  always "gmail" where the "G" got dropped. Treat "... Mail." or "... Mail " as "@gmail.com".
- "G mail" with a space → "gmail"
- No explicit "dot com" spoken near "mail" → still assume ".com"

CRITICAL — CONCATENATED LOCAL-PARTS SPLIT BY ASR:
Email local-parts are often single runs of letters/digits (e.g. jimmcarrincorporated),
but ASR splits them into separate Title-Cased words (e.g. "Jim Carr Incorporated").
When you see a sequence of Title-Cased tokens and/or digits immediately followed by
"Mail" / "gmail" / "@" / "at gmail":
- Concatenate ALL those tokens (including leading digits) into one lowercase local-part.
- Do NOT treat leading digits as an address/order number if they flow directly into the name.
- Do NOT split the concatenation with dots or dashes.
- Do NOT invent a new TLD — if only "mail" is mentioned, use ".com".

Worked example:
  Transcript: "Send it to 3308 Jim Carr Incorporated. Mail."
  Tokens before "Mail": 3308, Jim, Carr, Incorporated
  Concatenate lowercase: "3308jimcarrincorporated"
  "Mail" (no preceding G) → "@gmail.com"
  FINAL: 3308jimcarrincorporated@gmail.com
  (NOT jimcarr@incorporated.com — "Incorporated" is part of the local-part, not a domain.)

If spelling was also given earlier in the transcript (e.g. "J-I-M-M-C-A-R-R, double M, double R"),
prefer the spelled letters over the ASR Title-Case guess. Double-letter phrases like
"double M" mean two M's, "double R" means two R's.

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
  "summary": "<2-3 sentence summary>"
}}"""


# ─── JSON parsing (robust) ───────────────────────────────────────────────────

def parse_llm_json(raw: str) -> dict:
    """
    Parse LLM JSON response with fallbacks for common issues:
    markdown fences, truncated output, partial JSON.
    Returns {"parse_error": True, "raw": raw} on total failure.
    """
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try closing truncated JSON (missing closing braces)
    for suffix in ["}", '"}', '"]}', '"]}}']:
        try:
            return json.loads(text + suffix)
        except json.JSONDecodeError:
            continue

    # Try extracting largest {...} block via regex
    matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if matches:
        longest = max(matches, key=len)
        try:
            return json.loads(longest)
        except json.JSONDecodeError:
            pass

    return {"parse_error": True, "raw": raw}


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_transcript(client_groq, prompt: str) -> dict:
    """Send prompt to LLaMA for scoring, return parsed JSON result."""
    resp = call_with_retry(
        client_groq.chat.completions.create,
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content.strip()
    return parse_llm_json(raw)


# ─── Transcript chunking for long calls ──────────────────────────────────────

def chunk_transcript(text: str, max_tokens=6000) -> list:
    """
    Split transcript into chunks at sentence boundaries.
    max_tokens is approximate (1 token ≈ 4 chars).
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > max_chars and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def merge_scoring_results(results: list) -> dict:
    """Merge results from multiple transcript chunks."""
    if len(results) == 1:
        return results[0]

    merged = {
        "overall_score": min(r.get("overall_score", 0) for r in results),
        "disposition_suggested": results[0].get("disposition_suggested", "—"),
        "qualified": any(r.get("qualified", False) for r in results),
        "disqualifier_triggered": None,
        "lead_template_filled": results[0].get("lead_template_filled", ""),
        "checklist_results": [],
        "universal_results": [],
        "red_flags_found": [],
        "coaching_notes": [],
        "strengths": [],
        "summary": "",
    }

    seen_checklist = set()
    seen_universal = set()
    seen_flags = set()
    seen_coaching = set()
    seen_strengths = set()
    summaries = []

    for r in results:
        # Take first non-null disqualifier
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
    """Append a single JSON line to the audit log."""
    entry["logged_at"] = datetime.datetime.now().isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
