"""
MyVA Client Criteria — shared by desktop app and Streamlit website.
All active clients, lead templates, scoring logic, and Whisper config.
"""

# ─── Client Criteria ─────────────────────────────────────────────────────────

CLIENT_CRITERIA = {

    "Dealonomy (M&A)": {
        "type": "business",
        "template_type": "business",
        "dialer": "PhoneBurner",
        "agent": "Lilly / Nada",
        "framework": "RAT (Revenue · Authority · Timeline)",
        "checklist": [
            "Did agent confirm revenue is $1.5M+?",
            "Did agent confirm prospect is the owner / decision-maker?",
            "Did agent confirm prospect is open to exploring a sale?",
            "If prospect mentioned their business is SaaS — did agent disqualify / not proceed?",
            "If prospect mentioned they are California-based — did agent disqualify / not proceed?",
            "If agent reached the owner — did agent book an appointment with Devon?",
            "If agent reached the owner — did agent get email and ask prospect to accept the calendar invite?",
            "Did agent avoid pushing after a firm no — offered 6-month follow-up instead?",
        ],
        "hard_disqualifiers": [
            "Revenue confirmed under $1.5M",
            "Prospect confirmed business is SaaS (only if prospect mentioned it)",
            "Prospect confirmed California-based (only if prospect mentioned it)",
        ],
        "red_flags": [
            "Agent didn't confirm revenue threshold",
            "Agent didn't confirm owner / decision-maker status",
            "Agent pushed hard after firm no without pivoting to 6-month follow-up",
            "Agent booked appointment without speaking to the owner",
        ],
        "coaching_focus": [
            "RAT framework — Revenue, Authority, Timeline must all be confirmed",
            "Only attempt appointment booking and email capture when speaking to the actual owner",
            "When prospect says 'not interested' → pivot to 6-month follow-up, not goodbye",
            "Lock in specific appointment time — don't accept 'call me later'",
        ],
        "script_notes": "Opener should be disarming. Hook = 'have you ever thought about what your company might be worth?'",
    },

    "Stuart Moss / CIC Partners": {
        "type": "business",
        "template_type": "business",
        "dialer": "Call Tools",
        "agent": "Marie",
        "framework": "5-Step Script Flow",
        "checklist": [
            "Did agent confirm business is 5+ years in operation?",
            "If agent reached the owner — did agent ask about long-term plans (sell, partner, step back)?",
            "If agent reached the owner — did agent get business nature and number of employees?",
            "If agent reached the owner — did agent get estimated annual revenues?",
            "Did agent get email? (always — owner or gatekeeper)",
            "If agent reached the owner — did agent schedule a callback with the acquisitions team?",
            "If prospect was skeptical — did agent use the CIC backstory?",
        ],
        "hard_disqualifiers": [
            "Business less than 5 years old",
            "Owner not open to any discussion",
        ],
        "red_flags": [
            "Agent asked key qualification questions to a gatekeeper instead of the owner",
            "Agent pushed hard sale instead of exploratory framing",
            "Agent skipped email capture",
        ],
        "coaching_focus": [
            "Frame as exploratory — NOT a sales call",
            "Key questions (plans, revenue, employees) are only for the owner — don't waste them on gatekeepers",
            "If skeptical: use full CIC backstory (20 years, 50+ deals, $250M capital)",
            "Always close with a specific date/time for the intro call",
        ],
        "script_notes": "Must sound like a private introduction, not a pitch.",
    },

    "Smithton / Boone (RE Cash Buyer)": {
        "type": "real_estate",
        "template_type": "smithton",
        "dialer": "Call Tools",
        "agent": "Nehal",
        "framework": "6-Part: Price · Condition · Timeline · Motivation · Close",
        "checklist": [
            "Did agent confirm seller's name and property address?",
            "Did agent ask asking price?",
            "Did agent ask about property condition (beds/baths/sqft/repairs)?",
            "Did agent ask about occupancy (owner-occupied / rental / vacant)?",
            "Did agent ask about mortgage balance?",
            "Did agent ask about timeline?",
            "Did agent ask about motivation?",
            "Did agent schedule callback with Property Specialist?",
            "Did agent get email?",
            "Did agent submit via ReSimpli form (not just Discord)?",
        ],
        "hard_disqualifiers": [
            "Prospect said they are not looking to sell",
            "No motivation and no equity indication",
        ],
        "red_flags": [
            "Agent skipped asking price question",
            "Agent skipped mortgage / equity question",
            "Agent didn't identify motivation",
            "Agent submitted a throwaway lead (no motivation)",
        ],
        "coaching_focus": [
            "Price anchor starts at 40% of Zillow — work up slowly",
            "Mortgage balance is key — no equity = deal won't work",
            "Throwaway = no motivation — don't submit",
            "Always use ReSimpli form AND Discord post",
        ],
        "script_notes": "Cash offer framing: no repairs, no commissions, fast close, cover closing costs.",
    },

    "Jordyn / Barracuda (RE Multifamily)": {
        "type": "real_estate",
        "template_type": "jordyn",
        "dialer": "Enzo",
        "agent": "Nehal",
        "framework": "Multifamily Qualification",
        "checklist": [
            "Did agent ask number of units?",
            "Did agent ask unit mix (1-bed, 2-bed, etc.)?",
            "Did agent ask how many units are occupied?",
            "Did agent ask monthly rent per unit?",
            "Did agent ask how long they've owned it?",
            "Did agent ask about CapEx / repairs done or needed?",
            "Did agent ask about asking price?",
            "Did agent ask about timeline?",
            "Did agent ask about motivation?",
            "Did agent confirm phone + email before ending call?",
            "Did agent send notes to Barracuda WhatsApp?",
        ],
        "hard_disqualifiers": [
            "Single-family home (not multifamily)",
            "Owner not open to any offer",
        ],
        "red_flags": [
            "Agent skipped occupancy / rent questions",
            "Agent did not clarify this is multifamily only",
            "Agent skipped email or phone confirmation",
            "Notes not sent to Barracuda WhatsApp",
        ],
        "coaching_focus": [
            "Multifamily ONLY — single-family does not qualify",
            "Get all financial details: units, occupancy, rent, CapEx",
            "On price: 'I don't run numbers — I'll check with Jordyn after this'",
            "Always send notes to Barracuda WhatsApp after call",
        ],
        "script_notes": "Focus areas: St. Louis, Columbia, Jefferson City. NOT a wholesaler — they close deals themselves.",
    },

    "Scott Fuller / Haven Senior": {
        "type": "referral",
        "template_type": "scott",
        "dialer": "Call Tools",
        "agent": "Sam",
        "framework": "Referral Capture",
        "checklist": [
            "If agent reached the owner — did agent make clear this is NOT asking if their facility is for sale?",
            "If agent reached the owner — did agent ask if they know someone who might be selling a senior facility?",
            "Did agent get the owner's email? (always)",
            "Did agent speak confidentially and avoid operational questions?",
            "Did agent use the correct voicemail rotation (VM1/VM2/VM3)?",
            "If owner was unavailable — did agent pivot to email capture?",
        ],
        "hard_disqualifiers": [
            "Wrong type of facility (not senior housing)",
        ],
        "red_flags": [
            "Agent asked if THEIR facility is for sale (wrong framing)",
            "Agent gave operational details or discussed specifics",
            "Agent didn't attempt email capture when owner was unavailable",
        ],
        "coaching_focus": [
            "CRITICAL: Never ask if their community is for sale — ask if they KNOW someone",
            "Primary goal every call = owner email",
            "When gatekeeper blocks: clarify it's not a sales call, pivot to email",
            "Use VM rotation exactly: VM1 Day 1, VM2 Day 5, VM3 Day 10",
        ],
        "script_notes": "Say: 'Scott recently sold a community in Missouri' — confidently, no elaboration unless asked.",
    },

    "Sir Charles / Premier Site": {
        "type": "real_estate",
        "template_type": "listing",
        "dialer": "Call Tools",
        "agent": "Rawan",
        "framework": "Dual Path: Seller OR Construction",
        "checklist": [
            "Did agent confirm owner + property address?",
            "Did agent attempt seller qualification first (Path A)?",
            "If not selling — did agent pivot to construction path (Path B)?",
            "Did agent ask about property condition (beds/baths/sqft/repairs)?",
            "Did agent ask about mortgage / liens / taxes owed?",
            "Did agent ask about timeline and motivation?",
            "Did agent get price anchor ('what number would you need to move forward')?",
            "Did agent get email?",
            "Did agent ask if prospect is open to listing the property?",
            "Did agent tag correctly in Call Tools (Warm Lead-Seller / Listing Lead / Construction Lead)?",
        ],
        "hard_disqualifiers": [
            "No to selling AND no renovation project AND not open to listing",
        ],
        "red_flags": [
            "Agent gave up after 'not selling' without pivoting to construction path",
            "Agent took on small handyman requests (below minimum threshold)",
            "Agent didn't ask about listing option",
            "Agent didn't tag correctly in Call Tools",
        ],
        "coaching_focus": [
            "Always try BOTH paths — don't leave after seller says no",
            "Construction minimum: paint, roofing, gutters, floors, kitchens, baths, sheetrock",
            "Too small: minor patches, single fixture replacements — politely decline",
            "If wants market value → pivot to listing path (in-house realtor)",
        ],
        "script_notes": "Two GHL pipelines: Acquisition Pipeline (seller) and Construction Pipeline.",
    },

    "Shiraz (RE Listing)": {
        "type": "real_estate",
        "template_type": "listing",
        "dialer": "Enzo",
        "agent": "Sam",
        "framework": "Listing Agent Script",
        "checklist": [
            "Did agent ask if prospect is considering selling within 2 years?",
            "Did agent ask if they're open to working with a realtor?",
            "Did agent get timeline?",
            "Did agent get motivation?",
            "Did agent ask about property condition?",
            "Did agent ask if there are any updates to the property?",
            "Did agent ask if prospect is open to listing the property?",
            "Did agent get email?",
            "Did agent schedule callback?",
        ],
        "hard_disqualifiers": [
            "Not selling within 2 years and no email",
            "Firmly not open to working with a realtor",
        ],
        "red_flags": [
            "Agent skipped email capture",
            "Agent didn't ask about property condition or updates",
            "Agent didn't ask about listing option",
            "Agent didn't ask about realtor openness",
        ],
        "coaching_focus": [
            "Ask: 'Do you have a realtor you like working with?' (soft opener)",
            "Always capture email even for cold / no-timeline leads",
            "Ask about condition and updates — it helps with valuation",
        ],
        "script_notes": "Listing script — same flow as Kyle/Biancardi.",
    },

    "Kyle / Biancardi (RE Listing)": {
        "type": "real_estate",
        "template_type": "listing",
        "dialer": "Call Tools",
        "agent": "Marie",
        "framework": "Listing + HubSpot Appointment",
        "checklist": [
            "Did agent ask if prospect is considering selling?",
            "Did agent ask about timeline and motivation?",
            "Did agent ask about property condition?",
            "Did agent ask if there are any updates to the property?",
            "Did agent ask if prospect is open to listing the property?",
            "Did agent attempt to book appointment via HubSpot calendar?",
            "Did agent get email?",
            "Did agent get callback confirmation?",
        ],
        "hard_disqualifiers": [
            "Not selling and no email",
        ],
        "red_flags": [
            "Agent skipped email",
            "Agent didn't ask about property condition or updates",
            "Agent didn't ask about listing option",
            "Agent didn't push for HubSpot appointment booking",
        ],
        "coaching_focus": [
            "Goal is appointment booking — push HubSpot calendar hard",
            "Always get email even if they won't book now",
            "Condition and updates matter — ask every time",
        ],
        "script_notes": "Appointments go to HubSpot calendar — this is the primary close.",
    },

    "Giancarlo / Real Broker NJ": {
        "type": "real_estate",
        "template_type": "giancarlo",
        "dialer": "Enzo",
        "agent": "TBD",
        "framework": "Seller + Referral (5 Campaigns)",
        "checklist": [
            "Did agent ask if prospect is considering selling?",
            "Did agent ask if they know anyone else considering selling (referral question)?",
            "Did agent get timeline?",
            "Did agent get motivation?",
            "Did agent get email?",
            "Did agent respect 6pm callback cutoff?",
            "Did agent schedule callback within cutoff time?",
        ],
        "hard_disqualifiers": [
            "Not selling and no referral and no email",
        ],
        "red_flags": [
            "Agent scheduled callback after 6pm (violation)",
            "Agent skipped the referral question",
            "Agent skipped email capture",
        ],
        "coaching_focus": [
            "ALWAYS ask referral question — even if not selling themselves",
            "6pm callback cutoff — never schedule beyond that",
            "5 campaigns active — confirm which campaign before analyzing",
        ],
        "script_notes": "5 active campaigns. Referral question is mandatory.",
    },
}


# ─── Lead Templates ───────────────────────────────────────────────────────────

LEAD_TEMPLATES = {

    "business": """(Agent name and date)
Temp:

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

Call Recording: [Paste link here]""",

    "smithton": """(Agent name and date)
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
Call Recording: [Paste link here]""",

    "jordyn": """(Agent name and date)
Lead Temp:
Lead Type:

Address:
Seller Name:
Phone Number:
Email:

# Units:
Occupancy:
Condition:

Timeline:
Reason:
AP:
MV:

Other Notes:
Call Recording: [Paste link here]""",

    "listing": """(Agent name and date)
Temp:

Contact Info:
  Name:
  Number:
  Email:
  Address:
  Call Back On:

Condition:

Motivation/Pain and Others:
  Notes:
  Residency:
  Timeline:
  Reason:
  AP:
  Zestimate:
  Listing:

Call Recording: [Paste link here]""",

    "giancarlo": """(Agent name and date)
Temp:

• Contact Info:
  Name:
  Number:
  Email:
  Address:
  Call back on:

• Condition:
  Bedrooms:
  Bathrooms:
  Sqft:

• Motivation/Pain and Others:
  Notes:
  Residency:
  Timeline:
  Reason:
  AP:
  Zestimate:
  Listing:

• Call Recording: [Paste link here]""",

    "scott": """(Agent name and date)
Temperature:
Name:
Email:
Phone:
Facility Name:
Title:
Address:

Notes:

Call Recording: [Paste link here]""",

}


# ─── Temperature Logic (injected into GPT scoring prompt) ─────────────────────

TEMP_LOGIC = """
Determine lead temperature using these rules IN ORDER:

1. If prospect has NO valid motive or reason to sell → COLD (regardless of anything else)
2. If timeline is more than 1 year → NURTURE
3. If timeline is around 1 year → COLD
4. If timeline is ASAP to 3 months (soon):
   a. If AP < MV (or MV unknown but seller highly motivated) AND valid motive → HOT
   b. If AP > MV AND valid motive AND open to listing → WARM
   c. If AP > MV AND valid motive AND NOT open to listing → COLD

5. PROSPECT INTEREST LEVEL — always assess tone and engagement:
   - "High": prospect engaged actively, asked questions, volunteered details, sounded genuinely
     motivated. They clearly want to sell and are taking the call seriously.
   - "Medium": open to the idea but no strong urgency. Politely engaged, answered questions
     without pushing back, but didn't show excitement.
   - "Low": clearly not interested. Short dismissive answers, repeated objections, told the
     agent to remove them, or was rude/hung up quickly.

   Store this as "prospect_interest_level" in call_data. Add a 1-sentence reason
   as "prospect_interest_notes" in call_data.

   Interest level adjusts the base temperature by ONE level:
   - High → upgrade one level: Cold→Warm (if motive), Warm→Hot
   - Low  → downgrade one level: Hot→Warm, Warm→Cold
   - Medium → no adjustment

When MV is UNKNOWN, ALWAYS still pick the best concrete temperature from available
signals (motive strength, timeline, asking price, prospect interest, open to listing).
NEVER return null and NEVER write "Preliminary", "recalculate after MV", or "TBD"
in the template. The user will enter the MV afterward and the app recalculates automatically.

Always add any information the prospect provided that does not fit an existing field
into the Notes section.
"""


# ─── Universal Rules (applied to every client) ────────────────────────────────

UNIVERSAL_RULES = [
    "Did agent always ask for email on every call?",
    "Did agent always ask the referral question?",
    "Did agent avoid saying 'My manager will call you with an offer'?",
    "Did agent avoid mentioning offers proactively?",
    "Did agent confirm prospect's name at least once?",
    "Did agent lock in a specific callback time (not 'call anytime')?",
    "Did agent handle DNC immediately if mentioned (hang up, mark DNC)?",
    "Did agent stay within post-call time limits (10 seconds for non-leads)?",
    "Did agent sound natural and not robotic?",
    "Did agent reconfirm phone number before ending a lead call?",
]


# ─── Whisper vocabulary prompt ────────────────────────────────────────────────
# Balanced ~80-token set. Heavy email-shape primers bias Whisper to skip speech.

WHISPER_VOCAB = (
    # Domain terms
    "Zillow, MLS, realtor, duplex, triplex, multifamily, Zestimate, "
    "ARV, HOA, escrow, wholesale, ReSimpli, HubSpot, "
    # Client / company names
    "Dealonomy, Haven Senior, Biancardi, Smithton, Boone, "
    "CIC Partners, Giancarlo, Shiraz, Premier Site Solutions, "
    "Sir Charles, Scott Fuller, Loftey, Barracuda, Integrity, "
    # Phonetic alphabet — preserves spelled names/emails
    "alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, india, "
    "juliet, kilo, lima, mike, november, oscar, papa, quebec, romeo, "
    "sierra, tango, uniform, victor, whiskey, yankee, zulu"
)

# Known Whisper hallucinations to filter
WHISPER_HALLUCINATIONS = [
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "email addresses should be written",
    "not spelled out letter by letter",
]
