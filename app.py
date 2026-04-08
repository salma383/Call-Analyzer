import streamlit as st
import json
import tempfile
import os
from groq import Groq
from criteria import CLIENT_CRITERIA, UNIVERSAL_RULES

# ─── API Key ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MyVA Call Analyzer", page_icon="📞", layout="wide")

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  body, .stApp { background-color: #f5f7fa !important; color: #1a1a1a !important; }
  .header-bar {
    background: linear-gradient(90deg, #1a1a2e, #16213e);
    padding: 1.4rem 2rem; border-radius: 10px;
    margin-bottom: 1.5rem; color: white;
  }
  .header-bar h1 { margin: 0; font-size: 1.8rem; color: white; }
  .header-bar p  { margin: 0.3rem 0 0; opacity: 0.75; font-size: 0.88rem; color: #ccc; }

  /* metric cards */
  [data-testid="metric-container"] {
    background: white; border-radius: 10px;
    padding: 1rem; border: 1px solid #e0e0e0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }

  /* section headers */
  .sec-hdr {
    font-size: 1rem; font-weight: 700; color: #1a1a2e;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 0.3rem; margin: 1.2rem 0 0.8rem;
  }

  /* coaching / flags */
  .coaching { background:#fff8e1; border-left:4px solid #FFC107;
    border-radius:6px; padding:0.6rem 1rem; margin-bottom:0.4rem;
    font-size:0.9rem; color:#1a1a1a; }
  .redflag  { background:#fce4ec; border-left:4px solid #e53935;
    border-radius:6px; padding:0.6rem 1rem; margin-bottom:0.4rem;
    font-size:0.9rem; color:#1a1a1a; }

  /* template output */
  .lead-template {
    background: white; border: 1.5px solid #c8e6c9;
    border-radius: 10px; padding: 1.2rem 1.5rem;
    font-family: 'Courier New', monospace; font-size: 0.85rem;
    color: #1a1a1a; white-space: pre-wrap; line-height: 1.7;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }

  /* transcript */
  .transcript {
    background: white; border: 1px solid #e0e0e0;
    border-radius: 8px; padding: 1rem 1.5rem;
    font-family: 'Courier New', monospace; font-size: 0.83rem;
    color: #1a1a1a; max-height: 320px; overflow-y: auto;
    white-space: pre-wrap; line-height: 1.6;
  }

  /* checklist items */
  .chk-row { display:flex; align-items:flex-start; gap:0.5rem;
    padding:0.35rem 0; border-bottom:1px solid #f0f0f0; color:#1a1a1a; }
  .badge {
    display:inline-block; padding:0.15rem 0.55rem;
    border-radius:20px; font-size:0.75rem; font-weight:700;
    white-space:nowrap;
  }
  .badge-yes  { background:#e8f5e9; color:#2e7d32; }
  .badge-no   { background:#ffebee; color:#c62828; }
  .badge-part { background:#fff3e0; color:#e65100; }
  .badge-na   { background:#f5f5f5; color:#757575; }

  /* snapshot card */
  .snap-card {
    background:white; border-radius:10px; padding:1rem 1.2rem;
    border:1px solid #e0e0e0; margin-bottom:0.5rem;
  }
  .snap-card p { margin:0.2rem 0; font-size:0.88rem; color:#1a1a1a; }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <h1>📞 MyVA Call Analyzer</h1>
  <p>Transcribe · Score · Extract Lead · Coach — powered by Groq</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Call Details")
    client_name   = st.selectbox("Client / Campaign", list(CLIENT_CRITERIA.keys()))
    dialer_source = st.selectbox("Dialer Source", ["Call Tools","Enzo Dialer","Ready Mode","PhoneBurner","Other"])
    agent_name    = st.text_input("Agent Name", placeholder="e.g. Joy, Nehal…")
    call_date     = st.date_input("Call Date")
    st.markdown("---")
    st.markdown("### 🎚️ Options")
    show_transcript = st.checkbox("Show full transcript", value=True)
    show_universal  = st.checkbox("Universal rules check", value=True)
    export_json     = st.checkbox("Enable JSON export",    value=False)

# ─── Main layout ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.3, 1])

with col1:
    st.markdown("#### 🎙️ Upload Call Recording")
    audio_file = st.file_uploader(
        "MP3, MP4, M4A, WAV, OGG, FLAC, WEBM",
        type=["mp3","mp4","m4a","wav","ogg","flac","webm"],
        label_visibility="collapsed"
    )
    if audio_file:
        st.audio(audio_file)
        st.caption(f"📁 {audio_file.name} · {audio_file.size/1024/1024:.1f} MB · {dialer_source}")

with col2:
    if client_name:
        c = CLIENT_CRITERIA[client_name]
        st.markdown(f"""
<div class="snap-card">
  <p><strong>Campaign:</strong> {client_name}</p>
  <p><strong>Framework:</strong> {c['framework']}</p>
  <p><strong>Type:</strong> {c['type'].upper()}</p>
  <p><strong>Default Agent:</strong> {c['agent']}</p>
  <p><strong>Dialer:</strong> {c['dialer']}</p>
</div>""", unsafe_allow_html=True)
        with st.expander("🚫 Hard disqualifiers"):
            for d in c["hard_disqualifiers"]:
                st.markdown(f"🚫 {d}")

# ─── Prompt helpers ───────────────────────────────────────────────────────────
RE_TEMPLATE = """(Agent name and date)
Temp: 
Lead Type: 
Seller Name: 
Address: 
Phone Number: 
Email: 
Motive/Pain: 
Actively Selling? 
List with Realtor? 
What if we didn't give them the price: 
Occupancy: 
Beds/Baths: 
Sqft: 
Condition/Repairs: 
Mortgage: 
Market Value: 
Asking Price: 
Timeline: 
Callback: 
Notes: 
Call Recording:"""

BIZ_TEMPLATE = """(Agent name and date)
Temp: (Cold, Warm, Hot, Nurture, Networking etc.)

Contact Info:
  Contact Name: 
  Business Name: 
  Number: 
  Email: 

Business Details:
  Business Address: 
  Nature of Business: 
  Number of Employees: 
  Est. Annual Revenue: 
  Best Time Window for Intro Call: 
  Notes: 

Call Recording:"""

# ─── Analyze button ───────────────────────────────────────────────────────────
st.markdown("---")
analyze_btn = st.button("🚀 Transcribe & Analyze", type="primary", use_container_width=True)

if analyze_btn:
    if not GROQ_API_KEY:
        st.error("❌ No Groq API key found. Ask your admin to add it to Streamlit Secrets.")
        st.stop()
    if not audio_file:
        st.error("Please upload a call recording.")
        st.stop()

    client_groq = Groq(api_key=GROQ_API_KEY)
    criteria    = CLIENT_CRITERIA[client_name]
    is_biz      = criteria["type"] == "business"
    template    = BIZ_TEMPLATE if is_biz else RE_TEMPLATE

    # ── Transcribe ────────────────────────────────────────────────────────────
    with st.spinner("🎙️ Transcribing with Whisper…"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as f:
                transcription = client_groq.audio.transcriptions.create(
                    file=(audio_file.name, f.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    language="en"
                )
            segments = getattr(transcription, "segments", [])
            transcript_text = transcription.text  # plain text for AI analysis

            # ── Speaker diarization heuristic ────────────────────────────────
            # Gap of >0.6s between segments = speaker likely changed
            PAUSE_THRESHOLD = 0.6
            current_speaker = 1
            diarized_lines  = []
            prev_end        = 0.0

            for seg in segments:
                start = seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0)
                end   = seg.get("end",   0) if isinstance(seg, dict) else getattr(seg, "end",   0)
                text  = (seg.get("text","") if isinstance(seg, dict) else getattr(seg, "text","")).strip()
                if not text:
                    continue
                gap = start - prev_end
                if prev_end > 0 and gap > PAUSE_THRESHOLD:
                    current_speaker = 2 if current_speaker == 1 else 1
                mins  = int(start) // 60
                secs  = int(start) % 60
                ts    = f"{mins:02d}:{secs:02d}"
                label = "Agent" if current_speaker == 1 else "Prospect"
                diarized_lines.append(f"[{ts}] {label}: {text}")
                prev_end = end

            diarized_transcript = "\n".join(diarized_lines) if diarized_lines else transcript_text

        except Exception as e:
            st.error(f"Transcription failed: {e}")
            os.unlink(tmp_path)
            st.stop()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    st.success(f"✅ Transcribed — {len(transcript_text.split())} words · {len(segments) if segments else '?'} segments")

    # ── Build prompt ──────────────────────────────────────────────────────────
    checklist_str  = "\n".join([f"{i+1}. {x}" for i,x in enumerate(criteria["checklist"])])
    universal_str  = "\n".join([f"{i+1}. {x}" for i,x in enumerate(UNIVERSAL_RULES)])
    redflags_str   = "\n".join([f"- {r}" for r in criteria["red_flags"]])
    disq_str       = "\n".join([f"- {d}" for d in criteria["hard_disqualifiers"]])

    prompt = f"""You are an expert call quality analyst for MyVA.
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

    # ── Score ─────────────────────────────────────────────────────────────────
    with st.spinner("🧠 Scoring against client criteria…"):
        try:
            resp = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":prompt}],
                temperature=0.1,
                max_tokens=3000,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            st.error(f"Parse error: {e}")
            st.code(raw)
            st.stop()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # ── Display ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Results")

    score   = result.get("overall_score", 0)
    flags   = result.get("red_flags_found", [])
    disq    = result.get("disqualifier_triggered")
    qualif  = result.get("qualified", False)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Score",       f"{score}/100")
    m2.metric("Qualified",   "✅ Yes" if qualif else "❌ No")
    m3.metric("Disposition", result.get("disposition_suggested","—"))
    m4.metric("Red Flags",   f"🚩 {len(flags)}" if flags else "✅ None")
    st.progress(score / 100)

    if disq:
        st.error(f"🚫 Hard Disqualifier Triggered: {disq}")

    st.info(result.get("summary",""))

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Lead Template", "✅ Checklist", "🚨 Red Flags & Coaching", "💪 Strengths", "📄 Transcript"
    ])

    # Tab 1 — Filled lead template
    with tab1:
        st.markdown('<div class="sec-hdr">Auto-filled Lead Template</div>', unsafe_allow_html=True)
        filled = result.get("lead_template_filled", "Not available")
        st.markdown(f'<div class="lead-template">{filled}</div>', unsafe_allow_html=True)
        st.download_button(
            "⬇️ Copy Lead Template (.txt)", data=filled,
            file_name=f"lead_{agent_name or 'agent'}_{call_date}.txt", mime="text/plain"
        )

    # Tab 2 — Checklist
    with tab2:
        st.markdown(f'<div class="sec-hdr">Client Checklist — {criteria["framework"]}</div>', unsafe_allow_html=True)
        for item in result.get("checklist_results", []):
            r = item["result"]
            badge_cls = {"YES":"badge-yes","NO":"badge-no","PARTIAL":"badge-part","N/A":"badge-na"}.get(r,"badge-na")
            icon = {"YES":"✅","NO":"❌","PARTIAL":"⚠️","N/A":"➖"}.get(r,"➖")
            st.markdown(f"""
<div class="chk-row">
  <span>{icon}</span>
  <span style="flex:1">{item['item']}<br>
    <small style="color:#666">{item.get('note','')}</small>
  </span>
  <span class="badge {badge_cls}">{r}</span>
</div>""", unsafe_allow_html=True)

        if show_universal:
            st.markdown('<div class="sec-hdr">Universal Rules</div>', unsafe_allow_html=True)
            for item in result.get("universal_results", []):
                r    = item["result"]
                icon = {"YES":"✅","NO":"❌","PARTIAL":"⚠️","N/A":"➖"}.get(r,"➖")
                st.markdown(f"{icon} **{item['item']}** — <small style='color:#555'>{item.get('note','')}</small>",
                            unsafe_allow_html=True)

    # Tab 3 — Red flags + coaching
    with tab3:
        if flags:
            st.markdown('<div class="sec-hdr">🚩 Red Flags Found</div>', unsafe_allow_html=True)
            for f in flags:
                st.markdown(f'<div class="redflag">🚩 {f}</div>', unsafe_allow_html=True)
        else:
            st.success("No red flags detected.")

        st.markdown('<div class="sec-hdr">🎯 AI Coaching Notes</div>', unsafe_allow_html=True)
        for note in result.get("coaching_notes", []):
            st.markdown(f'<div class="coaching">💡 {note}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="sec-hdr">📌 Standard Coaching — {client_name}</div>', unsafe_allow_html=True)
        for point in criteria["coaching_focus"]:
            st.markdown(f'<div class="coaching">📌 {point}</div>', unsafe_allow_html=True)

    # Tab 4 — Strengths
    with tab4:
        for s in result.get("strengths", []):
            st.markdown(f"✅ {s}")
        if not result.get("strengths"):
            st.info("No specific strengths identified.")

    # Tab 5 — Transcript
    with tab5:
        if show_transcript:
            st.markdown('<div class="sec-hdr">Transcript with Timestamps & Speakers</div>', unsafe_allow_html=True)
            st.caption("🔵 Agent (Speaker 1) · 🟢 Prospect (Speaker 2) — speaker labels are estimated from pauses between segments")
            st.markdown(f'<div class="transcript">{diarized_transcript}</div>', unsafe_allow_html=True)
            st.download_button("⬇️ Transcript (.txt)", data=diarized_transcript,
                file_name=f"transcript_{agent_name or 'agent'}_{call_date}.txt", mime="text/plain")
        else:
            st.info("Enable transcript in sidebar.")

    if export_json:
        export_data = {
            "call_date": str(call_date), "agent": agent_name,
            "client": client_name, "dialer": dialer_source,
            "transcript": transcript_text, "analysis": result
        }
        st.download_button("⬇️ Full JSON Export", data=json.dumps(export_data, indent=2),
            file_name=f"analysis_{agent_name or 'agent'}_{call_date}.json", mime="application/json")

    st.markdown("---")
    st.caption("MyVA Call Analyzer · Groq Whisper + LLaMA 3.3 · Built for Salma @ MyVA")
