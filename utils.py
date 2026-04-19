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


# ─── Transcription (AssemblyAI — real speaker diarization) ──────────────────

def transcribe_audio(aai_api_key, audio_file):
    """
    Transcribe audio via AssemblyAI REST API with real speaker diarization.
    Returns (transcript_text, utterances, diarized_transcript).

    Speakers are labeled A/B/C... by AssemblyAI. The first speaker
    is assumed to be the Agent (they initiate the call).

    Uses raw HTTP (not the SDK) because the SDK is out of sync with
    the current API schema (speech_models plural).
    """
    import httpx

    base_url = "https://api.assemblyai.com/v2"
    headers = {"authorization": aai_api_key}

    suffix = f".{audio_file.name.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name

    try:
        # 1. Upload file
        with open(tmp_path, "rb") as f:
            upload_resp = httpx.post(
                f"{base_url}/upload",
                headers=headers,
                content=f.read(),
                timeout=300.0,
            )
        upload_resp.raise_for_status()
        audio_url = upload_resp.json()["upload_url"]

        # 2. Submit transcription job
        submit_resp = httpx.post(
            f"{base_url}/transcript",
            headers=headers,
            json={
                "audio_url": audio_url,
                "speaker_labels": True,
                "language_code": "en",
                "speech_models": ["universal-2"],
            },
            timeout=60.0,
        )
        submit_resp.raise_for_status()
        transcript_id = submit_resp.json()["id"]

        # 3. Poll for completion
        while True:
            poll_resp = httpx.get(
                f"{base_url}/transcript/{transcript_id}",
                headers=headers,
                timeout=60.0,
            )
            poll_resp.raise_for_status()
            data = poll_resp.json()
            status = data.get("status")
            if status == "completed":
                break
            if status == "error":
                raise RuntimeError(f"AssemblyAI error: {data.get('error')}")
            time.sleep(3)

        transcript_text = data.get("text") or ""
        utterances = data.get("utterances") or []

        # Build diarized transcript
        first_speaker = utterances[0]["speaker"] if utterances else "A"
        diarized_lines = []
        for utt in utterances:
            start_ms = utt.get("start", 0)
            mins = (start_ms // 1000) // 60
            secs = (start_ms // 1000) % 60
            ts = f"{mins:02d}:{secs:02d}"
            label = "Agent" if utt["speaker"] == first_speaker else "Prospect"
            diarized_lines.append(f"[{ts}] {label}: {utt['text']}")

        diarized_transcript = "\n".join(diarized_lines) if diarized_lines else transcript_text

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return transcript_text, utterances, diarized_transcript


# ─── Spelled-out email / address reconstruction ──────────────────────────────

def reconstruct_spelled_out(text: str) -> str:
    """
    Fix spelled-out emails and addresses in transcribed text.
    e.g. "s a l m a at gmail dot com" → "salma@gmail.com"
    e.g. "1 2 3 Main Street" → "123 Main Street"
    """
    if not text:
        return text

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

CLIENT: {client_name}
FRAMEWORK: {criteria['framework']}
AGENT: {agent_name or 'Unknown'}
SCRIPT NOTES: {criteria['script_notes']}

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
