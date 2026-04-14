""" 
MyVA Client Criteria — embedded for call analysis scoring.
Each client has: checklist items, disqualifiers, red flags, coaching focus areas.
"""

CLIENT_CRITERIA = {
    "Rejigg / Michael (M&A)": {
        "type": "business",
        "dialer": "PhoneBurner",
        "agent": "Lilly / Nada",
        "framework": "RAT (Revenue · Authority · Timeline)",
        "checklist": [
            "Did agent confirm revenue is $1M+ (minimum $900k)?",
            "Did agent confirm prospect is the owner / decision-maker?",
            "Did agent confirm prospect is open to exploring a sale?",
            "Did agent avoid mentioning SaaS companies? (disqualifier)",
            "Did agent avoid California-based businesses? (disqualifier)",
            "Did agent book appointment with Devon / use axia.cal.com/rejigg link?",
            "Did agent get prospect's email and ask them to accept calendar invite?",
            "Did agent avoid pushing hard after firm no — offer 6-month follow-up instead?",
        ],
        "hard_disqualifiers": [
            "Revenue under $900k",
            "SaaS company",
            "California-based business",
        ],
        "red_flags": [
            "Agent said 'my manager will make you an offer'",
            "Agent didn't confirm revenue threshold",
            "Agent didn't confirm owner/decision-maker status",
            "Agent gave up after first objection without pivot",
        ],
        "coaching_focus": [
            "RAT framework — Revenue, Authority, Timeline must all be confirmed",
            "Use one of the three approved openers — don't freestyle the intro",
            "When prospect says 'not interested' → pivot to 6-month follow-up, not goodbye",
            "Lock in specific appointment time — don't accept 'call me later'",
            "Always verify email on verifalia.com before submitting lead",
        ],
        "script_notes": "Opener must be disarming ('this is a cold call, feel free to hang up'). Hook = 'have you ever thought about what [company] might be worth?'"
    },

    "Stuart Moss / CIC Partners (Business)": {
        "type": "business",
        "dialer": "Call Tools",
        "agent": "Marie",
        "framework": "5-Step Script Flow",
        "checklist": [
            "Did agent confirm business is 5+ years in operation?",
            "Did agent ask about long-term plans (sell, partner, step back)?",
            "Did agent get business nature and number of employees?",
            "Did agent get estimated annual revenues?",
            "Did agent get email address?",
            "Did agent schedule a callback with the acquisitions team?",
            "Did agent use CIC backstory when prospect seemed skeptical?",
        ],
        "hard_disqualifiers": [
            "Business less than 5 years old",
            "Owner not open to any discussion",
        ],
        "red_flags": [
            "Agent didn't ask about long-term exit plans",
            "Agent skipped revenue/employee questions",
            "Agent pushed hard sale instead of exploratory framing",
        ],
        "coaching_focus": [
            "Frame as exploratory — NOT a sales call",
            "Use '5+ years, steady cash flow, good team' as qualifier language",
            "If skeptical: use full CIC backstory (20 years, 50+ deals, $250M capital)",
            "Always close with a specific date/time for the intro call",
        ],
        "script_notes": "NOT real estate. Must sound like a private introduction, not a pitch."
    },

    "Tristen / Loftey (RE Sellers)": {
        "type": "real_estate",
        "dialer": "Enzo",
        "agent": "Joy",
        "framework": "Motivation · Timeline · Email",
        "checklist": [
            "Did agent say 'home' (NOT 'house' or 'property')?",
            "Did agent ask if prospect is considering selling?",
            "Did agent get the timeline (within 2 years)?",
            "Did agent get the motivation (why selling)?",
            "Did agent ask for email?",
            "Did agent schedule a callback?",
            "Did agent avoid revealing 'Loftey Group' name before qualification?",
        ],
        "hard_disqualifiers": [
            "No timeline + no email = not a lead",
            "Confirmed not selling within 24 months and no email given",
        ],
        "red_flags": [
            "Agent said 'house' or 'property' instead of 'home'",
            "Agent revealed 'Loftey Group' before prospect qualified",
            "Agent skipped asking for email",
            "Agent didn't ask about motivation",
        ],
        "coaching_focus": [
            "ALWAYS say 'home' — this is Tristen's hard rule, no exceptions",
            "Email is required even for cold leads — always ask",
            "Motivation is key: retiring, downsizing, divorce, kids graduating, etc.",
            "Lock in specific callback time — not 'call anytime'",
        ],
        "script_notes": "Cold/email leads still count if email is captured. Conversion target: 1.5%."
    },

    "Smithton / Boone (RE Cash Buyer)": {
        "type": "real_estate",
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
            "Prospect said 'I'm not looking to sell'",
            "Prospect said 'I don't need to sell' / 'I'd just keep it'",
            "No motivation and no equity indication",
        ],
        "red_flags": [
            "Agent skipped price question",
            "Agent skipped mortgage/equity question",
            "Agent didn't identify motivation",
            "Agent submitted throwaway lead",
        ],
        "coaching_focus": [
            "Price anchor starts at 40% of Zillow — work up slowly",
            "Mortgage balance is key — no equity = deal won't work",
            "Throwaway = no motivation, don't submit",
            "Always use ReSimpli form AND Discord post",
        ],
        "script_notes": "Cash offer framing: no repairs, no commissions, fast close, cover closing costs."
    },

    "Jordyn / Barracuda (RE Multifamily)": {
        "type": "real_estate",
        "dialer": "Enzo",
        "agent": "Nehal",
        "framework": "Multifamily Qualification",
        "checklist": [
            "Did agent ask number of units?",
            "Did agent ask unit mix (1-bed, 2-bed)?",
            "Did agent ask how many units are occupied?",
            "Did agent ask monthly rent per unit?",
            "Did agent ask how long they've owned it?",
            "Did agent ask about CapEx / repairs done or needed?",
            "Did agent ask about asking price?",
            "Did agent ask about timeline (if numbers worked)?",
            "Did agent ask about motivation?",
            "Did agent confirm phone + email before ending call?",
            "Did agent send notes to Barracuda WhatsApp?",
        ],
        "hard_disqualifiers": [
            "Single-family home (not multifamily)",
            "Owner not open to any offer",
        ],
        "red_flags": [
            "Agent skipped occupancy/rent questions",
            "Agent didn't clarify it's multifamily only",
            "Notes not sent to Barracuda WhatsApp",
        ],
        "coaching_focus": [
            "This is multifamily ONLY — single-family doesn't qualify",
            "Get all financial details: units, occupancy, rent, CapEx",
            "On price: 'I don't run numbers — I'll check with Jordyn after this'",
            "Always send notes to Barracuda WhatsApp after call",
        ],
        "script_notes": "Focus areas: St. Louis, Columbia, Jefferson City. NOT a wholesaler — they close on deals themselves."
    },

    "Integrity (RE Sellers)": {
        "type": "real_estate",
        "dialer": "Call Tools",
        "agent": "Menna",
        "framework": "Cash Buyer Qualification",
        "checklist": [
            "Did agent confirm owner name and property address?",
            "Did agent gauge selling interest?",
            "Did agent ask about property details (beds/baths/sqft)?",
            "Did agent explain cash offer benefits (no repairs, no commissions, fast close)?",
            "Did agent ask about mortgage balance / equity?",
            "Did agent get motivation?",
            "Did agent schedule specific callback date/time?",
            "Did agent get email?",
        ],
        "hard_disqualifiers": [
            "Won't consider below-market cash offer AND won't list",
            "No equity (mortgage too high)",
        ],
        "red_flags": [
            "Agent skipped mortgage/equity question",
            "Agent gave up without setting specific callback",
            "Agent didn't explain cash offer advantages",
        ],
        "coaching_focus": [
            "Foreclosure leads: show empathy + mention limited time before auction",
            "Tax lien leads: explain you'll pay off back taxes at closing",
            "Inherited property: emphasize avoiding headache of maintenance",
            "ALWAYS end with specific callback date — motivated sellers go cold fast",
        ],
        "script_notes": "Website: integritylps.com. Submit via ReSimpli link."
    },

    "Integrity (Buyers Camp)": {
        "type": "real_estate",
        "dialer": "Call Tools",
        "agent": "Menna",
        "framework": "Investor Buyer List Building",
        "checklist": [
            "Did agent confirm prospect owns multiple properties?",
            "Did agent ask if they're looking to acquire more?",
            "Did agent get state + city (minimum required)?",
            "Did agent get property type?",
            "Did agent ask about specific zip codes (for major cities)?",
            "Did agent ask about property manager interest?",
            "Did agent ask about insurance review interest?",
        ],
        "hard_disqualifiers": [
            "Only owns one property",
            "Not looking to acquire more",
        ],
        "red_flags": [
            "Agent didn't get state + city (minimum info)",
            "Agent treated this like a seller call",
        ],
        "coaching_focus": [
            "This is a BUYER list — you're building Integrity's acquisition pipeline",
            "Minimum: state + city + property type. Always try for more.",
            "For big cities: get specific zip codes",
        ],
        "script_notes": "Opening: 'I noticed from public records you own multiple properties...'"
    },

    "Scott Fuller / Haven Senior (Senior Housing)": {
        "type": "referral",
        "dialer": "Call Tools",
        "agent": "Sam",
        "framework": "Referral Capture",
        "checklist": [
            "Did agent make clear this is NOT asking if their facility is for sale?",
            "Did agent ask if they know someone who might be selling a senior facility?",
            "Did agent get the owner's email (primary goal)?",
            "Did agent speak confidentially and avoid operational questions?",
            "Did agent use the correct voicemail rotation (VM1/VM2/VM3)?",
            "Did agent pivot to email capture when owner was unavailable?",
        ],
        "hard_disqualifiers": [
            "Wrong type of facility (not senior housing)",
        ],
        "red_flags": [
            "Agent asked if THEIR facility is for sale (wrong framing)",
            "Agent gave operational details or discussed specifics",
            "Agent didn't attempt email capture when owner unavailable",
        ],
        "coaching_focus": [
            "CRITICAL: Never ask if their community is for sale — ask if they KNOW someone",
            "Primary goal every call = owner email",
            "When gatekeeper blocks: clarify it's not a sales call, pivot to email",
            "Use VM rotation exactly: VM1 Day 1, VM2 Day 5, VM3 Day 10",
        ],
        "script_notes": "Say: 'Scott recently sold a community in Missouri' — confidently, no elaboration unless asked."
    },

    "Sir Charles / Premier Site (RE + Construction)": {
        "type": "real_estate",
        "dialer": "Call Tools",
        "agent": "Rawan",
        "framework": "Dual Path: Seller OR Construction",
        "checklist": [
            "Did agent confirm owner + property address?",
            "Did agent attempt seller qualification first (Path A)?",
            "If not selling: did agent pivot to construction path (Path B)?",
            "Did agent ask about property condition (beds/baths/sqft/repairs)?",
            "Did agent ask about mortgage / liens / taxes owed?",
            "Did agent ask about timeline and motivation?",
            "Did agent get price anchor ('what number would you need to move forward')?",
            "Did agent get email?",
            "Did agent tag correctly in Call Tools (Warm Lead-Seller / Listing Lead / Construction Lead)?",
        ],
        "hard_disqualifiers": [
            "No to selling AND no renovation project",
        ],
        "red_flags": [
            "Agent gave up after 'not selling' without pivoting to construction",
            "Agent took on small handyman requests (below threshold)",
            "Agent didn't tag correctly in Call Tools",
        ],
        "coaching_focus": [
            "Always try BOTH paths — don't leave after seller says no",
            "Construction minimum: paint, roofing, gutters, floors, kitchens, baths, sheetrock",
            "Too small: minor patches, single fixture replacements — politely decline",
            "If wants market value → pivot to listing path (in-house realtor)",
        ],
        "script_notes": "Two GHL pipelines: Acquisition Pipeline (seller) and Construction Pipeline."
    },

    "Shiraz (RE Listing)": {
        "type": "real_estate",
        "dialer": "Enzo",
        "agent": "Sam",
        "framework": "Listing Agent Script",
        "checklist": [
            "Did agent ask if prospect is considering selling within 2 years?",
            "Did agent ask if they're open to working with a realtor?",
            "Did agent get timeline?",
            "Did agent get motivation?",
            "Did agent get email?",
            "Did agent schedule callback?",
        ],
        "hard_disqualifiers": [
            "Not selling within 2 years and no email",
            "Firmly not open to working with a realtor",
        ],
        "red_flags": [
            "Agent didn't ask about realtor openness",
            "Agent skipped email capture",
        ],
        "coaching_focus": [
            "Same script as Kyle — listing agent focus",
            "Ask: 'Do you have a realtor you like working with?' (soft opener)",
            "Always capture email even for cold/no-timeline leads",
        ],
        "script_notes": "Listing script — same flow as Kyle/Biancardi."
    },

    "Kyle / Biancardi (RE Listing)": {
        "type": "real_estate",
        "dialer": "Call Tools",
        "agent": "Marie",
        "framework": "Listing + HubSpot Appointment",
        "checklist": [
            "Did agent ask if prospect is considering selling?",
            "Did agent ask about timeline and motivation?",
            "Did agent attempt to book appointment via HubSpot calendar?",
            "Did agent get email?",
            "Did agent get callback confirmation?",
        ],
        "hard_disqualifiers": [
            "Not selling and no email",
        ],
        "red_flags": [
            "Agent didn't push for HubSpot appointment booking",
            "Agent skipped email",
        ],
        "coaching_focus": [
            "Goal is appointment booking — push HubSpot calendar hard",
            "Always get email even if they won't book now",
        ],
        "script_notes": "Appointments go to HubSpot calendar — this is the primary close."
    },

    "Giancarlo / Real Broker NJ (RE Seller + Referral)": {
        "type": "real_estate",
        "dialer": "Enzo",
        "agent": "TBD",
        "framework": "Seller + Referral (5 Campaigns)",
        "checklist": [
            "Did agent ask if prospect is considering selling?",
            "Did agent ask if they know anyone else considering selling (referral)?",
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
        ],
        "coaching_focus": [
            "ALWAYS ask referral question — even if not selling themselves",
            "6pm callback cutoff — never schedule beyond that",
            "5 campaigns active — confirm which campaign before analyzing",
        ],
        "script_notes": "5 active campaigns. Referral question is mandatory."
    },
}

# ─── Lead templates by type ──────────────────────────────────────────────────

LEAD_TEMPLATES = {
    "real_estate": """(Agent name and date)
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
Call Recording:""",

    "business": """(Agent name and date)
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

Call Recording:""",

    "referral": """(Agent name and date)
Temp:
Contact Name:
Facility Name:
Facility Type:
Owner Name:
Owner Email:
Owner Phone:
Referral Source:
Notes:
Call Recording:""",
}


# ─── Whisper vocabulary prompt ───────────────────────────────────────────────

WHISPER_VOCAB = (
    "mortgage, equity, foreclosure, tax lien, sqft, square feet, "
    "owner-occupied, Zillow, MLS, realtor, cash offer, escrow, HOA, "
    "appraisal, earnest money, refinance, ARV, CapEx, multifamily, "
    "duplex, triplex, EBITDA, ReSimpli, HubSpot, GHL, "
    "Rejigg, Loftey, Barracuda, Integrity, Haven Senior, Biancardi, "
    "Smithton, Boone, CIC Partners, Giancarlo, Shiraz"
)

# Known Whisper hallucinations to filter out of transcripts
WHISPER_HALLUCINATIONS = [
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "email addresses should be written",
    "not spelled out letter by letter",
]


# ─── Universal rules ────────────────────────────────────────────────────────

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
