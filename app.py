import streamlit as st
import json
import os
import datetime
from groq import Groq
from criteria import CLIENT_CRITERIA, UNIVERSAL_RULES, LEAD_TEMPLATES, WHISPER_VOCAB
from utils import (
    sanitize_filename, hash_audio_file, transcribe_audio,
    build_scoring_prompt, score_transcript, chunk_transcript,
    merge_scoring_results, reconstruct_spelled_out, append_audit_log,
)

# ─── API Key ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
if not GROQ_API_KEY:
    st.error("No Groq API key found. Add GROQ_API_KEY to Streamlit Secrets or environment.")
    st.stop()

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="MyVA Call Analyzer", page_icon="📞", layout="wide")

# ─── Session state init ─────────────────────────────────────────────────────
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []

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
    client_name = st.selectbox("Client / Campaign", list(CLIENT_CRITERIA.keys()))
    agent_name  = st.text_input("Agent Name", placeholder="e.g. Joy, Nehal…")
    call_date   = st.date_input("Call Date")
    st.markdown("---")
    st.markdown("### 🎚️ Options")
    show_transcript = st.checkbox("Show full transcript", value=True)
    show_universal  = st.checkbox("Universal rules check", value=True)
    export_json     = st.checkbox("Enable JSON export",    value=False)

    # Session history
    if st.session_state.analysis_history:
        st.markdown("---")
        st.markdown("### 📊 Past Analyses")
        for h in reversed(st.session_state.analysis_history):
            st.markdown(
                f"**{h['agent']}** — {h['client']} — "
                f"{h['score']}/100 ({h['timestamp']})"
            )

# ─── Main layout ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.3, 1])

with col1:
    st.markdown("#### 🎙️ Upload Call Recording")
    audio_files = st.file_uploader(
        "MP3, MP4, M4A, WAV, OGG, FLAC, WEBM",
        type=["mp3", "mp4", "m4a", "wav", "ogg", "flac", "webm"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if audio_files:
        for af in audio_files:
            st.audio(af)
            st.caption(f"📁 {af.name} · {af.size/1024/1024:.1f} MB")

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

# ─── Analyze button ───────────────────────────────────────────────────────────
st.markdown("---")
analyze_btn = st.button("🚀 Transcribe & Analyze", type="primary", use_container_width=True)

if analyze_btn:
    if not agent_name or not agent_name.strip():
        st.error("Please enter the agent name.")
        st.stop()
    if not audio_files:
        st.error("Please upload a call recording.")
        st.stop()

    client_groq = Groq(api_key=GROQ_API_KEY)
    criteria = CLIENT_CRITERIA[client_name]
    template = criteria.get(
        "lead_template",
        LEAD_TEMPLATES.get(criteria["type"], LEAD_TEMPLATES["real_estate"])
    )
    safe_agent = sanitize_filename(agent_name)

    for file_idx, audio_file in enumerate(audio_files):
        expanded = file_idx == 0
        container = st.expander(f"Results: {audio_file.name}", expanded=expanded) if len(audio_files) > 1 else st.container()

        with container:
            # ── Transcribe ────────────────────────────────────────────────
            audio_hash = hash_audio_file(audio_file)
            cache_key = f"transcript_{audio_hash}"

            if cache_key in st.session_state:
                transcript_text, segments, diarized_transcript = st.session_state[cache_key]
                st.info("Using cached transcript.")
            else:
                with st.spinner("🎙️ Transcribing with Whisper…"):
                    try:
                        transcript_text, segments, diarized_transcript = transcribe_audio(
                            client_groq, audio_file, WHISPER_VOCAB
                        )
                        st.session_state[cache_key] = (transcript_text, segments, diarized_transcript)
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
                        continue

            # Post-process spelled-out emails/addresses in transcript
            transcript_text = reconstruct_spelled_out(transcript_text)
            diarized_transcript = reconstruct_spelled_out(diarized_transcript)

            st.success(f"✅ Transcribed — {len(transcript_text.split())} words · {len(segments) if segments else '?'} segments")

            # ── Score (with chunking for long calls) ──────────────────────
            MAX_TRANSCRIPT_CHARS = 24000

            if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
                chunks = chunk_transcript(transcript_text)
                results = []
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"🧠 Scoring chunk {i+1}/{len(chunks)}…"):
                        try:
                            prompt = build_scoring_prompt(
                                client_name, criteria, agent_name,
                                call_date, chunk, template, UNIVERSAL_RULES,
                            )
                            results.append(score_transcript(client_groq, prompt))
                        except Exception as e:
                            st.error(f"Scoring failed on chunk {i+1}: {e}")
                            break
                if not results:
                    continue
                result = merge_scoring_results(results)
            else:
                with st.spinner("🧠 Scoring against client criteria…"):
                    try:
                        prompt = build_scoring_prompt(
                            client_name, criteria, agent_name,
                            call_date, transcript_text, template, UNIVERSAL_RULES,
                        )
                        result = score_transcript(client_groq, prompt)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        continue

            # Check for parse errors
            if result.get("parse_error"):
                st.warning("Could not parse the AI response as JSON.")
                with st.expander("Raw AI response"):
                    st.code(result.get("raw", ""))
                continue

            # Post-process filled template for spelled-out emails
            if result.get("lead_template_filled"):
                result["lead_template_filled"] = reconstruct_spelled_out(
                    result["lead_template_filled"]
                )

            # ── Audit log ─────────────────────────────────────────────────
            try:
                append_audit_log({
                    "agent": agent_name,
                    "client": client_name,
                    "call_date": str(call_date),
                    "score": result.get("overall_score"),
                    "qualified": result.get("qualified"),
                    "disposition": result.get("disposition_suggested"),
                    "red_flags_count": len(result.get("red_flags_found", [])),
                    "audio_filename": audio_file.name,
                })
            except Exception:
                pass  # Don't break the app if logging fails

            # ── Session history ───────────────────────────────────────────
            st.session_state.analysis_history.append({
                "agent": agent_name,
                "client": client_name,
                "call_date": str(call_date),
                "score": result.get("overall_score", 0),
                "disposition": result.get("disposition_suggested", "—"),
                "qualified": result.get("qualified", False),
                "summary": result.get("summary", ""),
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            })

            # ── Display ──────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("## 📊 Results")

            score  = result.get("overall_score", 0)
            flags  = result.get("red_flags_found", [])
            disq   = result.get("disqualifier_triggered")
            qualif = result.get("qualified", False)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Score",       f"{score}/100")
            m2.metric("Qualified",   "✅ Yes" if qualif else "❌ No")
            m3.metric("Disposition", result.get("disposition_suggested", "—"))
            m4.metric("Red Flags",   f"🚩 {len(flags)}" if flags else "✅ None")
            st.progress(score / 100)

            if disq:
                st.error(f"🚫 Hard Disqualifier Triggered: {disq}")

            st.info(result.get("summary", ""))

            # Tabs
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Lead Template", "✅ Checklist",
                "🚨 Red Flags & Coaching", "💪 Strengths", "📄 Transcript",
            ])

            # Tab 1 — Filled lead template
            with tab1:
                st.markdown('<div class="sec-hdr">Auto-filled Lead Template</div>', unsafe_allow_html=True)
                filled = result.get("lead_template_filled", "Not available")
                st.markdown(f'<div class="lead-template">{filled}</div>', unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Copy Lead Template (.txt)", data=filled,
                    file_name=f"lead_{safe_agent}_{call_date}.txt",
                    mime="text/plain", key=f"dl_lead_{file_idx}",
                )

            # Tab 2 — Checklist
            with tab2:
                st.markdown(f'<div class="sec-hdr">Client Checklist — {criteria["framework"]}</div>', unsafe_allow_html=True)
                for item in result.get("checklist_results", []):
                    r = item["result"]
                    badge_cls = {"YES": "badge-yes", "NO": "badge-no", "PARTIAL": "badge-part", "N/A": "badge-na"}.get(r, "badge-na")
                    icon = {"YES": "✅", "NO": "❌", "PARTIAL": "⚠️", "N/A": "➖"}.get(r, "➖")
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
                        r = item["result"]
                        icon = {"YES": "✅", "NO": "❌", "PARTIAL": "⚠️", "N/A": "➖"}.get(r, "➖")
                        st.markdown(
                            f"{icon} **{item['item']}** — <small style='color:#555'>{item.get('note','')}</small>",
                            unsafe_allow_html=True,
                        )

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
                    st.download_button(
                        "⬇️ Transcript (.txt)", data=diarized_transcript,
                        file_name=f"transcript_{safe_agent}_{call_date}.txt",
                        mime="text/plain", key=f"dl_transcript_{file_idx}",
                    )
                else:
                    st.info("Enable transcript in sidebar.")

            if export_json:
                export_data = {
                    "call_date": str(call_date), "agent": agent_name,
                    "client": client_name,
                    "transcript": transcript_text, "analysis": result,
                }
                st.download_button(
                    "⬇️ Full JSON Export",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"analysis_{safe_agent}_{call_date}.json",
                    mime="application/json", key=f"dl_json_{file_idx}",
                )

    st.markdown("---")
    st.caption("MyVA Call Analyzer · Groq Whisper + LLaMA 3.3 · Built for Salma @ MyVA")
