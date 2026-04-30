import streamlit as st
import json
import os
import datetime
import threading
from groq import Groq
from openai import OpenAI
from criteria import CLIENT_CRITERIA, UNIVERSAL_RULES, LEAD_TEMPLATES
from utils import (
    sanitize_filename, hash_audio_file,
    transcribe_audio, build_scoring_prompt, score_transcript,
    chunk_transcript, merge_scoring_results,
    reconstruct_spelled_out, append_audit_log,
    extract_email, _inject_email, _scrub_preliminary_text,
    _looks_like_spelled_email, build_labeled_transcript, recalculate_temp,
)

# ─── Page config (MUST be first Streamlit call) ───────────────────────────────
st.set_page_config(page_title="MyVA Call Analyzer", page_icon="📞", layout="wide")


# ─── Password gate ────────────────────────────────────────────────────────────
def _get_secret(key, fallback=""):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, fallback)

_APP_PASSWORD = _get_secret("APP_PASSWORD")
if _APP_PASSWORD:
    _entered = st.text_input("🔒 Enter password to access MyVA Call Analyzer",
                             type="password", key="_pw")
    if _entered != _APP_PASSWORD:
        st.stop()


# ─── API keys ─────────────────────────────────────────────────────────────────
GROQ_API_KEY   = _get_secret("GROQ_API_KEY")
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

if not GROQ_API_KEY:
    st.error("No Groq API key found. Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()
if not OPENAI_API_KEY:
    st.error("No OpenAI API key found. Add OPENAI_API_KEY to Streamlit Secrets.")
    st.stop()


# ─── Session state init ───────────────────────────────────────────────────────
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "results_store" not in st.session_state:
    st.session_state.results_store = {}   # keyed by audio hash


# ─── CSS ──────────────────────────────────────────────────────────────────────
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

  [data-testid="metric-container"] {
    background: white; border-radius: 10px;
    padding: 1rem; border: 1px solid #e0e0e0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .sec-hdr {
    font-size: 1rem; font-weight: 700; color: #1a1a2e;
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 0.3rem; margin: 1.2rem 0 0.8rem;
  }
  .coaching { background:#fff8e1; border-left:4px solid #FFC107;
    border-radius:6px; padding:0.6rem 1rem; margin-bottom:0.4rem;
    font-size:0.9rem; color:#1a1a1a; }
  .redflag  { background:#fce4ec; border-left:4px solid #e53935;
    border-radius:6px; padding:0.6rem 1rem; margin-bottom:0.4rem;
    font-size:0.9rem; color:#1a1a1a; }
  .lead-template {
    background: white; border: 1.5px solid #c8e6c9;
    border-radius: 10px; padding: 1.2rem 1.5rem;
    font-family: 'Courier New', monospace; font-size: 0.85rem;
    color: #1a1a1a; white-space: pre-wrap; line-height: 1.7;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }
  .transcript {
    background: white; border: 1px solid #e0e0e0;
    border-radius: 8px; padding: 1rem 1.5rem;
    font-family: 'Courier New', monospace; font-size: 0.83rem;
    color: #1a1a1a; max-height: 380px; overflow-y: auto;
    white-space: pre-wrap; line-height: 1.6;
  }
  .chk-row { display:flex; align-items:flex-start; gap:0.5rem;
    padding:0.35rem 0; border-bottom:1px solid #f0f0f0; color:#1a1a1a; }
  .badge { display:inline-block; padding:0.15rem 0.55rem;
    border-radius:20px; font-size:0.75rem; font-weight:700; white-space:nowrap; }
  .badge-yes  { background:#e8f5e9; color:#2e7d32; }
  .badge-no   { background:#ffebee; color:#c62828; }
  .badge-part { background:#fff3e0; color:#e65100; }
  .badge-na   { background:#f5f5f5; color:#757575; }
  .snap-card {
    background:white; border-radius:10px; padding:1rem 1.2rem;
    border:1px solid #e0e0e0; margin-bottom:0.5rem;
  }
  .snap-card p { margin:0.2rem 0; font-size:0.88rem; color:#1a1a1a; }
  .temp-hot     { background:#e8f5e9; color:#1b5e20; border-radius:8px;
    padding:0.5rem 1rem; font-weight:700; display:inline-block; }
  .temp-warm    { background:#fff3e0; color:#e65100; border-radius:8px;
    padding:0.5rem 1rem; font-weight:700; display:inline-block; }
  .temp-cold    { background:#e3f2fd; color:#0d47a1; border-radius:8px;
    padding:0.5rem 1rem; font-weight:700; display:inline-block; }
  .temp-nurture { background:#f3e5f5; color:#6a1b9a; border-radius:8px;
    padding:0.5rem 1rem; font-weight:700; display:inline-block; }
  .temp-pending { background:#fafafa; color:#555; border:1px dashed #aaa;
    border-radius:8px; padding:0.5rem 1rem; font-weight:600; display:inline-block; }
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <h1>📞 MyVA Call Analyzer</h1>
  <p>Transcribe · Score · Extract Lead · Coach · Temperature — powered by Groq Whisper + GPT-4.1-mini</p>
</div>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Call Details")
    client_name = st.selectbox("Client / Campaign", list(CLIENT_CRITERIA.keys()))
    agent_name  = st.text_input("Agent Name", placeholder="e.g. Joy, Nehal…")
    call_date   = st.date_input("Call Date")
    st.markdown("---")
    st.markdown("### 🎚️ Options")
    show_transcript = st.checkbox("Show full transcript", value=True)
    show_universal  = st.checkbox("Universal rules check", value=True)
    export_json     = st.checkbox("Enable JSON export",   value=False)

    if st.session_state.analysis_history:
        st.markdown("---")
        st.markdown("### 📊 Past Analyses")
        for h in reversed(st.session_state.analysis_history):
            st.markdown(
                f"**{h['agent']}** — {h['client']} — "
                f"{h['score']}/100 ({h['timestamp']})"
            )


# ─── Main layout ──────────────────────────────────────────────────────────────
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
  <p><strong>Default Agent:</strong> {c.get('agent','—')}</p>
  <p><strong>Dialer:</strong> {c.get('dialer','—')}</p>
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

    client_groq   = Groq(api_key=GROQ_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    criteria      = CLIENT_CRITERIA[client_name]
    template_key  = criteria.get("type", "real_estate")
    template      = LEAD_TEMPLATES.get(template_key, LEAD_TEMPLATES["real_estate"])
    safe_agent    = sanitize_filename(agent_name)

    for file_idx, audio_file in enumerate(audio_files):
        container = (
            st.expander(f"Results: {audio_file.name}", expanded=(file_idx == 0))
            if len(audio_files) > 1 else st.container()
        )

        with container:
            # ── Transcribe ────────────────────────────────────────────────────
            audio_hash = hash_audio_file(audio_file)
            cache_key  = f"transcript_{audio_hash}"

            if cache_key in st.session_state:
                transcript_text, utterances, stamped_transcript = st.session_state[cache_key]
                st.info("Using cached transcript.")
            else:
                with st.spinner("🎙️ Transcribing with Groq Whisper…"):
                    try:
                        transcript_text, utterances, stamped_transcript = transcribe_audio(
                            client_groq, audio_file
                        )
                        st.session_state[cache_key] = (
                            transcript_text, utterances, stamped_transcript
                        )
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
                        continue

            transcript_text    = reconstruct_spelled_out(transcript_text)
            stamped_transcript = reconstruct_spelled_out(stamped_transcript)
            st.success(
                f"✅ Transcribed — {len(transcript_text.split())} words · "
                f"{len(utterances) if utterances else '?'} segments"
            )

            # ── Score + parallel email extraction ──────────────────────────────
            MAX_CHARS = 24_000
            needs_email = _looks_like_spelled_email(transcript_text)

            def _run_score(chunks_or_text):
                if isinstance(chunks_or_text, list):
                    results = []
                    for i, chunk in enumerate(chunks_or_text):
                        prompt = build_scoring_prompt(
                            client_name, criteria, agent_name, call_date,
                            chunk, template, UNIVERSAL_RULES,
                            stamped_transcript=(stamped_transcript if i == 0 else ""),
                        )
                        results.append(score_transcript(openai_client, prompt))
                    return merge_scoring_results(results)
                else:
                    prompt = build_scoring_prompt(
                        client_name, criteria, agent_name, call_date,
                        chunks_or_text, template, UNIVERSAL_RULES,
                        stamped_transcript=stamped_transcript,
                    )
                    return score_transcript(openai_client, prompt)

            score_input = (
                chunk_transcript(transcript_text)
                if len(transcript_text) > MAX_CHARS
                else transcript_text
            )

            verified_email = None

            with st.spinner("🧠 Analyzing call (GPT-4.1-mini)…"):
                if needs_email:
                    result_holder = [None]
                    email_holder  = [None]
                    err_holder    = [None]

                    def _t_score():
                        try:
                            result_holder[0] = _run_score(score_input)
                        except Exception as e:
                            err_holder[0] = str(e)

                    def _t_email():
                        email_holder[0] = extract_email(openai_client, transcript_text)

                    t1 = threading.Thread(target=_t_score)
                    t2 = threading.Thread(target=_t_email)
                    t1.start(); t2.start()
                    t1.join();  t2.join()

                    if err_holder[0]:
                        st.error(f"Analysis failed: {err_holder[0]}")
                        continue
                    result         = result_holder[0]
                    verified_email = email_holder[0]
                else:
                    try:
                        result = _run_score(score_input)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        continue

            if result.get("parse_error"):
                st.warning("Could not parse the AI response as JSON.")
                with st.expander("Raw AI response"):
                    st.code(result.get("raw", ""))
                continue

            # ── Post-process template ──────────────────────────────────────────
            template_filled = result.get("lead_template_filled", "")

            # Inject dedicated email if extracted
            if verified_email:
                template_filled = _inject_email(template_filled, verified_email)

            # Strip any stray "Preliminary — recalc after MV" leftovers
            prelim_temp = result.get("preliminary_temp")
            template_filled = _scrub_preliminary_text(template_filled, prelim_temp)
            template_filled = reconstruct_spelled_out(template_filled)
            result["lead_template_filled"] = template_filled

            # ── Audit log + session history ────────────────────────────────────
            try:
                append_audit_log({
                    "agent": agent_name, "client": client_name,
                    "call_date": str(call_date),
                    "score": result.get("overall_score"),
                    "qualified": result.get("qualified"),
                    "disposition": result.get("disposition_suggested"),
                    "red_flags_count": len(result.get("red_flags_found", [])),
                    "audio_filename": audio_file.name,
                })
            except Exception:
                pass

            st.session_state.analysis_history.append({
                "agent": agent_name, "client": client_name,
                "call_date": str(call_date),
                "score": result.get("overall_score", 0),
                "disposition": result.get("disposition_suggested", "—"),
                "qualified": result.get("qualified", False),
                "summary": result.get("summary", ""),
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            })

            # Store full result indexed by audio_hash for MV recalculation
            st.session_state.results_store[audio_hash] = {
                "result": result,
                "template_filled": template_filled,
                "stamped_transcript": stamped_transcript,
                "is_re": criteria.get("type") == "real_estate",
            }

            # ── Summary metrics ────────────────────────────────────────────────
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

            # ── Tabs ───────────────────────────────────────────────────────────
            is_re = criteria.get("type") == "real_estate"
            tab_labels = ["📋 Lead Template", "🌡️ Temperature", "✅ Checklist",
                          "🚨 Red Flags & Coaching", "💪 Strengths", "📄 Transcript"]
            tab1, tab_temp, tab2, tab3, tab4, tab5 = st.tabs(tab_labels)

            with tab1:
                st.markdown('<div class="sec-hdr">Auto-filled Lead Template</div>', unsafe_allow_html=True)
                filled = result.get("lead_template_filled", "Not available")
                st.markdown(f'<div class="lead-template">{filled}</div>', unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Copy Lead Template (.txt)", data=filled,
                    file_name=f"lead_{safe_agent}_{call_date}.txt",
                    mime="text/plain", key=f"dl_lead_{file_idx}",
                )

            # ── Temperature tab ──────────────────────────────────────────────
            with tab_temp:
                if not is_re:
                    st.info("Temperature determination is for real estate clients only.")
                else:
                    temp     = result.get("preliminary_temp") or "—"
                    is_prelim = result.get("temp_is_preliminary", False)
                    call_data = result.get("call_data", {})

                    # Colour-coded badge
                    temp_cls = {
                        "hot": "temp-hot", "warm": "temp-warm", "cold": "temp-cold",
                        "nurture": "temp-nurture", "throwaway": "temp-cold",
                    }.get((temp or "").lower(), "temp-pending")

                    prelim_note = " ⚠️ <small>(MV not yet factored in)</small>" if is_prelim else ""
                    st.markdown(
                        f'<div class="{temp_cls}">{temp.upper()}</div>{prelim_note}',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    # Raw call signals
                    ap       = call_data.get("ap")
                    timeline = call_data.get("timeline_months")
                    motive   = call_data.get("has_valid_motive", False)
                    listing  = call_data.get("open_to_listing", False)

                    st.markdown("**Call signals extracted by AI:**")
                    sig_col1, sig_col2 = st.columns(2)
                    sig_col1.markdown(
                        f"- **Asking Price:** {'${:,.0f}'.format(ap) if ap else 'Not captured'}\n"
                        f"- **Timeline:** {f'{timeline:.0f} months' if timeline else 'Not captured'}"
                    )
                    sig_col2.markdown(
                        f"- **Valid Motive:** {'✅ Yes' if motive else '❌ No'}\n"
                        f"- **Open to Listing:** {'✅ Yes' if listing else '❌ No'}"
                    )

                    # MV entry + recalculation
                    st.markdown("---")
                    st.markdown("**Enter Market Value (MV) to recalculate:**")
                    mv_input = st.text_input(
                        "Market Value",
                        placeholder="$280,000  or  N/A",
                        key=f"mv_{audio_hash}_{file_idx}",
                        label_visibility="collapsed",
                    )

                    if st.button("🔄 Recalculate Temperature", key=f"recalc_{audio_hash}_{file_idx}"):
                        mv_val = None
                        mv_clean = mv_input.strip().replace(",", "").replace("$", "").lower()
                        if mv_clean not in ("", "n/a", "na", "none", "n.a."):
                            try:
                                mv_val = float(mv_clean)
                            except ValueError:
                                st.warning("Could not parse MV — enter a number like 280000 or N/A.")
                                mv_val = None

                        new_temp = recalculate_temp(call_data, mv_val)
                        mv_label = f"${mv_val:,.0f}" if mv_val else "N/A"

                        new_cls = {
                            "hot": "temp-hot", "warm": "temp-warm", "cold": "temp-cold",
                            "nurture": "temp-nurture",
                        }.get(new_temp.lower(), "temp-pending")

                        st.markdown(
                            f"**Recalculated with MV = {mv_label}:**<br>"
                            f'<div class="{new_cls}">{new_temp.upper()}</div>',
                            unsafe_allow_html=True,
                        )

                        # Update the stored template with new temp
                        stored = st.session_state.results_store.get(audio_hash, {})
                        if stored:
                            updated_template = re.sub(
                                r'^((?:Lead\s+)?Temp(?:erature)?\s*:)\s*.*$',
                                rf'\1 {new_temp}',
                                stored.get("template_filled", ""),
                                flags=re.IGNORECASE | re.MULTILINE,
                            )
                            st.session_state.results_store[audio_hash]["template_filled"] = updated_template
                            st.markdown("**Updated Lead Template:**")
                            st.markdown(
                                f'<div class="lead-template">{updated_template}</div>',
                                unsafe_allow_html=True,
                            )
                            st.download_button(
                                "⬇️ Download Updated Template",
                                data=updated_template,
                                file_name=f"lead_{safe_agent}_{call_date}_updated.txt",
                                mime="text/plain",
                                key=f"dl_updated_{audio_hash}_{file_idx}",
                            )

            with tab2:
                st.markdown(
                    f'<div class="sec-hdr">Client Checklist — {criteria["framework"]}</div>',
                    unsafe_allow_html=True,
                )
                for item in result.get("checklist_results", []):
                    r = item["result"]
                    badge_cls = {
                        "YES": "badge-yes", "NO": "badge-no",
                        "PARTIAL": "badge-part", "N/A": "badge-na",
                    }.get(r.upper() if r else "", "badge-na")
                    icon = {"YES": "✅", "NO": "❌", "PARTIAL": "⚠️", "N/A": "➖"}.get(
                        r.upper() if r else "", "➖"
                    )
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
                        icon = {"YES": "✅", "NO": "❌", "PARTIAL": "⚠️", "N/A": "➖"}.get(
                            r.upper() if r else "", "➖"
                        )
                        st.markdown(
                            f"{icon} **{item['item']}** — "
                            f"<small style='color:#555'>{item.get('note','')}</small>",
                            unsafe_allow_html=True,
                        )

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

                st.markdown(
                    f'<div class="sec-hdr">📌 Standard Coaching — {client_name}</div>',
                    unsafe_allow_html=True,
                )
                for point in criteria["coaching_focus"]:
                    st.markdown(f'<div class="coaching">📌 {point}</div>', unsafe_allow_html=True)

            with tab4:
                for s in result.get("strengths", []):
                    st.markdown(f"✅ {s}")
                if not result.get("strengths"):
                    st.info("No specific strengths identified.")

            with tab5:
                if show_transcript:
                    # Build speaker-labeled transcript if labels were returned
                    raw_labels = result.get("speaker_labels") or []
                    if raw_labels and isinstance(raw_labels, list):
                        labeled = build_labeled_transcript(
                            stamped_transcript, raw_labels, agent_name
                        )
                        st.markdown(
                            '<div class="sec-hdr">Transcript — Speaker Labeled</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"→ = {agent_name} (Agent)   ◆ = Prospect")
                        st.markdown(
                            f'<div class="transcript">{labeled}</div>',
                            unsafe_allow_html=True,
                        )
                        st.download_button(
                            "⬇️ Transcript (.txt)", data=labeled,
                            file_name=f"transcript_{safe_agent}_{call_date}.txt",
                            mime="text/plain", key=f"dl_transcript_{file_idx}",
                        )
                    else:
                        st.markdown(
                            '<div class="sec-hdr">Transcript with Timestamps</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="transcript">{stamped_transcript}</div>',
                            unsafe_allow_html=True,
                        )
                        st.download_button(
                            "⬇️ Transcript (.txt)", data=stamped_transcript,
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
    st.caption("MyVA Call Analyzer · Groq Whisper + GPT-4.1-mini · Built for Salma @ MyVA")
