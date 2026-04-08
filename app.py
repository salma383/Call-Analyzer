import streamlit as st
import json
import tempfile
import os
from groq import Groq
from criteria import CLIENT_CRITERIA, UNIVERSAL_RULES

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MyVA Call Analyzer",
    page_icon="📞",
    layout="wide",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1a2e, #16213e);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; }
    .main-header p { margin: 0.3rem 0 0 0; opacity: 0.75; font-size: 0.9rem; }

    .score-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #4CAF50;
    }
    .score-card.fail { border-left-color: #f44336; }
    .score-card.warn { border-left-color: #FF9800; }

    .check-pass { color: #4CAF50; font-weight: 600; }
    .check-fail { color: #f44336; font-weight: 600; }
    .check-warn { color: #FF9800; font-weight: 600; }

    .transcript-box {
        background: #fafafa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    .stProgress > div > div { background-color: #1a1a2e; }
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        border-bottom: 2px solid #1a1a2e;
        padding-bottom: 0.3rem;
        margin: 1.2rem 0 0.8rem 0;
    }
    .coaching-note {
        background: #fff8e1;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        border-left: 4px solid #FFC107;
    }
    .red-flag {
        background: #fce4ec;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        border-left: 4px solid #f44336;
    }
    .disqualifier {
        background: #f3e5f5;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        border-left: 4px solid #9c27b0;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-left: 0.5rem;
    }
    .badge-green { background: #e8f5e9; color: #2e7d32; }
    .badge-red { background: #ffebee; color: #c62828; }
    .badge-orange { background: #fff3e0; color: #e65100; }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📞 MyVA Call Analyzer</h1>
    <p>Transcribe · Score · Coach · Export — powered by Groq</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Setup")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.markdown("---")
    st.markdown("### 📋 Call Details")
    client_name = st.selectbox("Client / Campaign", list(CLIENT_CRITERIA.keys()))
    dialer_source = st.selectbox("Dialer Source", [
        "Call Tools", "Enzo Dialer", "Ready Mode", "PhoneBurner", "Other"
    ])
    agent_name = st.text_input("Agent Name", placeholder="e.g. Joy, Nehal...")
    call_date = st.date_input("Call Date")
    st.markdown("---")
    st.markdown("### 🎚️ Options")
    show_transcript = st.checkbox("Show full transcript", value=True)
    show_universal = st.checkbox("Include universal rules check", value=True)
    export_json = st.checkbox("Enable JSON export", value=False)

# ─── Main area ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("#### 🎙️ Upload Call Recording")
    audio_file = st.file_uploader(
        "Supports MP3, MP4, M4A, WAV, OGG, FLAC, WEBM",
        type=["mp3", "mp4", "m4a", "wav", "ogg", "flac", "webm"],
        label_visibility="collapsed"
    )
    if audio_file:
        st.audio(audio_file)
        file_size_mb = audio_file.size / (1024 * 1024)
        st.caption(f"📁 {audio_file.name} · {file_size_mb:.1f} MB · Source: {dialer_source}")

with col2:
    st.markdown("#### 📌 Client Snapshot")
    if client_name:
        c = CLIENT_CRITERIA[client_name]
        st.markdown(f"**Framework:** {c['framework']}")
        st.markdown(f"**Type:** `{c['type'].upper()}`")
        st.markdown(f"**Default Agent:** {c['agent']}")
        st.markdown(f"**Dialer:** {c['dialer']}")
        with st.expander("View hard disqualifiers"):
            for d in c["hard_disqualifiers"]:
                st.markdown(f"🚫 {d}")

# ─── Analyze button ──────────────────────────────────────────────────────────
st.markdown("---")
analyze_btn = st.button("🚀 Transcribe & Analyze", type="primary", use_container_width=True)

if analyze_btn:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()
    if not audio_file:
        st.error("Please upload a call recording.")
        st.stop()

    client = Groq(api_key=api_key)
    criteria = CLIENT_CRITERIA[client_name]

    # ── Step 1: Transcribe ──────────────────────────────────────────────────
    with st.spinner("🎙️ Transcribing audio with Whisper..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name
        try:
            with open(tmp_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(audio_file.name, f.read()),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language="en"
                )
            transcript_text = transcription.text
            duration_secs = getattr(transcription, "duration", None)
        except Exception as e:
            st.error(f"Transcription failed: {e}")
            os.unlink(tmp_path)
            st.stop()
        finally:
            os.unlink(tmp_path)

    st.success(f"✅ Transcription complete — {len(transcript_text.split())} words")

    # ── Step 2: Build scoring prompt ────────────────────────────────────────
    checklist_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(criteria["checklist"])])
    universal_str = "\n".join([f"{i+1}. {item}" for i, item in enumerate(UNIVERSAL_RULES)])
    red_flags_str = "\n".join([f"- {r}" for r in criteria["red_flags"]])
    disqualifiers_str = "\n".join([f"- {d}" for d in criteria["hard_disqualifiers"]])

    scoring_prompt = f"""You are an expert call quality analyst for MyVA, a virtual assistant company.
Analyze this call transcript and score the agent's performance.

CLIENT: {client_name}
FRAMEWORK: {criteria['framework']}
AGENT BEING ANALYZED: {agent_name or 'Unknown'}
SCRIPT NOTES: {criteria['script_notes']}

--- TRANSCRIPT ---
{transcript_text}
--- END TRANSCRIPT ---

QUALIFICATION CHECKLIST (answer YES / NO / PARTIAL / N/A for each):
{checklist_str}

UNIVERSAL RULES CHECKLIST:
{universal_str}

HARD DISQUALIFIERS (flag if triggered):
{disqualifiers_str}

RED FLAGS TO WATCH FOR:
{red_flags_str}

Respond ONLY in this exact JSON format (no markdown, no preamble):
{{
  "overall_score": <0-100 integer>,
  "disposition_suggested": "<Hot/Warm/Cold/Not Interested/Appointment Set/etc.>",
  "qualified": <true/false>,
  "disqualifier_triggered": "<name of disqualifier or null>",
  "checklist_results": [
    {{"item": "<item text>", "result": "<YES/NO/PARTIAL/N/A>", "note": "<brief observation>"}}
  ],
  "universal_results": [
    {{"item": "<item text>", "result": "<YES/NO/PARTIAL/N/A>", "note": "<brief observation>"}}
  ],
  "red_flags_found": ["<flag1>", "<flag2>"],
  "coaching_notes": [
    "<specific coaching point 1>",
    "<specific coaching point 2>",
    "<specific coaching point 3>"
  ],
  "strengths": ["<strength1>", "<strength2>"],
  "summary": "<2-3 sentence overall summary of the call>"
}}"""

    # ── Step 3: Score ───────────────────────────────────────────────────────
    with st.spinner("🧠 Analyzing call against client criteria..."):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": scoring_prompt}],
                temperature=0.1,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse analysis output: {e}")
            st.code(raw, language="text")
            st.stop()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # ── Step 4: Display results ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    # Score bar + headline metrics
    score = result.get("overall_score", 0)
    score_color = "score-card" if score >= 70 else ("score-card warn" if score >= 50 else "score-card fail")
    score_emoji = "✅" if score >= 70 else ("⚠️" if score >= 50 else "❌")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Overall Score", f"{score}/100")
    with m2:
        qualified = result.get("qualified", False)
        st.metric("Qualified Lead", "✅ Yes" if qualified else "❌ No")
    with m3:
        st.metric("Suggested Disposition", result.get("disposition_suggested", "—"))
    with m4:
        flags = result.get("red_flags_found", [])
        st.metric("Red Flags", f"🚩 {len(flags)}" if flags else "✅ None")

    st.progress(score / 100)

    disq = result.get("disqualifier_triggered")
    if disq:
        st.error(f"🚫 **Hard Disqualifier Triggered:** {disq}")

    st.markdown(f"> {result.get('summary', '')}")

    # Tabs for detailed results
    tab1, tab2, tab3, tab4 = st.tabs([
        "✅ Checklist", "🚨 Red Flags & Coaching", "💪 Strengths", "📄 Transcript"
    ])

    with tab1:
        st.markdown(f'<div class="section-header">Client Checklist — {criteria["framework"]}</div>', unsafe_allow_html=True)
        for item in result.get("checklist_results", []):
            r = item["result"]
            icon = "✅" if r == "YES" else ("⚠️" if r == "PARTIAL" else ("➖" if r == "N/A" else "❌"))
            color = "check-pass" if r == "YES" else ("check-warn" if r == "PARTIAL" else ("" if r == "N/A" else "check-fail"))
            badge_cls = "badge-green" if r == "YES" else ("badge-orange" if r == "PARTIAL" else "badge-red")
            badge_cls = "" if r == "N/A" else badge_cls
            st.markdown(
                f'{icon} {item["item"]} <span class="badge {badge_cls}">{r}</span><br>'
                f'<small style="color:#666; margin-left:1.5rem;">{item.get("note", "")}</small>',
                unsafe_allow_html=True
            )
            st.markdown("")

        if show_universal:
            st.markdown('<div class="section-header">Universal Rules</div>', unsafe_allow_html=True)
            for item in result.get("universal_results", []):
                r = item["result"]
                icon = "✅" if r == "YES" else ("⚠️" if r == "PARTIAL" else ("➖" if r == "N/A" else "❌"))
                st.markdown(
                    f'{icon} {item["item"]} — <small style="color:#666;">{item.get("note", "")}</small>',
                    unsafe_allow_html=True
                )

    with tab2:
        if flags:
            st.markdown('<div class="section-header">🚩 Red Flags Found</div>', unsafe_allow_html=True)
            for f in flags:
                st.markdown(f'<div class="red-flag">🚩 {f}</div>', unsafe_allow_html=True)
        else:
            st.success("No red flags detected.")

        st.markdown('<div class="section-header">🎯 Coaching Notes</div>', unsafe_allow_html=True)
        for note in result.get("coaching_notes", []):
            st.markdown(f'<div class="coaching-note">💡 {note}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Standard Coaching Focus for {}</div>'.format(client_name), unsafe_allow_html=True)
        for point in criteria["coaching_focus"]:
            st.markdown(f'<div class="coaching-note">📌 {point}</div>', unsafe_allow_html=True)

    with tab3:
        strengths = result.get("strengths", [])
        if strengths:
            for s in strengths:
                st.markdown(f"✅ {s}")
        else:
            st.info("No specific strengths identified.")

    with tab4:
        if show_transcript:
            st.markdown('<div class="section-header">Full Transcript</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="transcript-box">{transcript_text}</div>', unsafe_allow_html=True)
            st.download_button(
                "⬇️ Download Transcript (.txt)",
                data=transcript_text,
                file_name=f"transcript_{agent_name or 'agent'}_{call_date}.txt",
                mime="text/plain"
            )
        else:
            st.info("Transcript display is disabled. Enable it in the sidebar.")

    # ── Export ──────────────────────────────────────────────────────────────
    if export_json:
        export_data = {
            "call_date": str(call_date),
            "agent": agent_name,
            "client": client_name,
            "dialer": dialer_source,
            "file": audio_file.name,
            "transcript": transcript_text,
            "analysis": result
        }
        st.download_button(
            "⬇️ Export Full Analysis (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"call_analysis_{agent_name or 'agent'}_{call_date}.json",
            mime="application/json"
        )

    st.markdown("---")
    st.caption("MyVA Call Analyzer · Powered by Groq Whisper + LLaMA 3.3 · Built for Salma @ MyVA")
