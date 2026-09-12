"""Build the reviewed Police GD taxonomy and four-seed pilot assets."""

import argparse

from service_pilot_framework import build_pilot, build_taxonomy, print_build_summary


def leaf(identifier, name, description, includes, excludes, seeds, **kwargs):
    return {"id": identifier, "display_name": name, "description": description,
            "includes": includes, "excludes": excludes, "seeds": seeds, **kwargs}


def parent(identifier, name, description, covers, leaves):
    return {"id": identifier, "display_name": name, "description": description,
            "default_evidence_status": "official_service_supported",
            "covers": covers, "leaves": leaves}


PARENTS = [
    parent("POLICE_GD_GUIDANCE", "GD Purpose and Routing Guidance",
           "What a GD is, when citizens seek it and when urgent or case-oriented routing needs clarification.",
           ["GD purpose", "Appropriate use", "Emergency routing", "GD versus case"], [
        leaf("POLICE_GD_PURPOSE", "General Diary Purpose", "General questions about what a GD is and why it is used.", ["What is a GD", "Purpose of General Diary"], ["How to file a GD", "A specific lost-item report"], ["সাধারণ ডায়েরি বা জিডি কী এবং এর উদ্দেশ্য কী?", "GD আসলে কী কাজে লাগে?", "general diary keno kora hoy?", "পুলিশের কাছে GD করা বলতে ঠিক কী বোঝায়?" ]),
        leaf("POLICE_GD_APPROPRIATE_USE", "Whether a Matter Is Appropriate for GD", "Questions asking whether a described non-emergency matter may be reported through GD.", ["Can this matter be a GD", "When GD is used"], ["Immediate danger", "How to submit an already-decided GD"], ["কোন ধরনের ঘটনায় সাধারণত জিডি করা যায়?", "আমার জিনিস হারানোর বিষয়টা GD-তে জানানো যাবে?", "ei ghotonar jonno GD kora appropriate hobe kina?", "ঘটনাটা পুলিশকে record করাতে চাই—GD service ব্যবহার করা যায় কি?"], pilot_review=True),
        leaf("POLICE_GD_EMERGENCY_ROUTING", "Emergency or Immediate-Danger Routing", "Queries asking whether an urgent safety situation should use GD or immediate emergency help.", ["Immediate danger and GD", "Urgent police help versus GD"], ["Routine administrative GD", "Legal determination of offence"], ["তাৎক্ষণিক বিপদের ঘটনায় জিডি করব, নাকি জরুরি পুলিশি সহায়তা চাইব?", "এখনই danger আছে, online GD কি এই situation-এর জন্য?", "immediate safety risk hole GD na emergency help konta lagbe?", "ঘটনা চলমান এবং দ্রুত পুলিশ দরকার—কোন service-এ যোগাযোগ করা উচিত?"], priority="High", pilot_review=True, evidence_status="needs_pilot_validation"),
        leaf("POLICE_GD_CASE_VS_GD_GUIDANCE", "GD Versus Case/Complaint Guidance", "Queries seeking routing guidance between an administrative GD and a matter that may require station attendance or a case process.", ["GD or case guidance", "Complaint route clarification"], ["A legal conclusion", "Emergency response instructions"], ["আমার অভিযোগটি জিডি হবে নাকি মামলার প্রক্রিয়ায় যাবে, কীভাবে জানব?", "complaint submit করলে থানায় যেতে হবে কিনা বুঝব কীভাবে?", "GD ar case process er moddhe amar report ta kothay pore?", "online complaint দেওয়ার পর station attendance দরকার হতে পারে কি—official guidance চাই।"], priority="Medium", pilot_review=True, evidence_status="needs_pilot_validation"),
    ]),
    parent("POLICE_GD_FILING", "GD Filing and Submission", "Preparing and submitting a General Diary complaint, including information, attachments and jurisdiction.", ["Filing process", "Online submission", "Required information", "Attachments", "Jurisdiction"], [
        leaf("POLICE_GD_FILING_PROCESS", "General Diary Filing Process", "General end-to-end questions about making a GD.", ["How to file GD", "GD submission steps"], ["Online-only focus", "Status after submission"], ["সাধারণ ডায়েরি করার সম্পূর্ণ প্রক্রিয়াটি কী?", "GD করতে চাই, কীভাবে শুরু করব?", "general diary file korar steps ki?", "একটি ঘটনা থানায় GD হিসেবে record করার নিয়ম জানতে চাই।"]),
        leaf("POLICE_GD_ONLINE_SUBMISSION", "Online GD Submission", "Starting or completing a GD through the online portal/app.", ["File GD online", "Submit online complaint"], ["General offline GD process", "Online account registration"], ["অনলাইনে জিডি কীভাবে জমা দেব?", "Online GD app দিয়ে complaint submit করব কীভাবে?", "online e GD file korar process ta ki?", "portal account আছে, এখন digital GD application কোথা থেকে শুরু করব?"] ),
        leaf("POLICE_GD_REQUIRED_INFORMATION", "Information Required for GD", "Information that must be entered about the complainant or incident.", ["Information needed for GD", "Details required in complaint"], ["Supporting files", "Account identity verification"], ["জিডি করতে কী কী তথ্য দিতে হয়?", "GD form-এ incident-এর কোন details লাগবে?", "online GD er required information ki ki?", "ঘটনার সময়, স্থান আর বর্ণনার মধ্যে কোন তথ্যগুলো প্রস্তুত রাখব?"] ),
        leaf("POLICE_GD_ATTACHMENTS", "GD Supporting Documents and Attachments", "Supporting documents, images or files attached to a GD complaint.", ["Attach documents to GD", "Supporting evidence upload"], ["Information typed in form", "Digital GD copy download"], ["জিডির সঙ্গে সহায়ক কাগজ বা ছবি কীভাবে যুক্ত করব?", "complaint-এর proof upload করা যাবে?", "online GD te supporting document attach korbo kivabe?", "ঘটনার একটি image আছে—application-এর কোন ধাপে attachment দেব?"] ),
        leaf("POLICE_GD_INCIDENT_DETAILS", "Incident Time, Place and Description", "How to describe when, where and how the reported event occurred.", ["Enter incident location", "Write incident description"], ["Select responsible police station", "Account address information"], ["জিডিতে ঘটনার সময় ও স্থান কীভাবে লিখব?", "incident description-এ কতটা detail দেব?", "GD te ghotonar jayga o shomoy kivabe mention korbo?", "ঘটনাটা কয়েক ধাপে হয়েছে—complaint narrative কীভাবে সাজাব?"] ),
        leaf("POLICE_GD_JURISDICTION", "Police Station and Jurisdiction Selection", "Choosing the district or police station responsible for a GD submission.", ["Which station for GD", "Select district and thana"], ["Incident address entry", "Contacting assigned investigating officer"], ["জিডির জন্য কোন থানা নির্বাচন করব?", "ঘটনা অন্য এলাকায় হয়েছে, কোন police station select হবে?", "online GD te district thana choose korbo kivabe?", "বাসা এক থানায় আর ঘটনাস্থল অন্য থানায়—application কোন jurisdiction-এ দেব?"], pilot_review=True),
        leaf("POLICE_GD_IDENTITY_REQUIREMENTS", "Online GD Identity and Registration Requirements", "Identity and contact requirements for using the online GD service.", ["Identity needed for online GD", "Registration requirements"], ["Incident supporting documents", "Providing real identifiers in pilot text"], ["অনলাইন GD complaint জমা দেওয়ার আগে পরিচয় যাচাইয়ের জন্য কী কী প্রয়োজন?", "Online GD complaint submit করার আগে কোন identity information verify করতে হয়?", "online GD complaint submit korte identity verification er requirements ki ki?", "complaint file করার আগে user identity verification-এর কোন stepগুলো complete করতে হয়?"] ),
    ]),
    parent("POLICE_GD_INCIDENT_TYPE", "GD Incident and Item Type", "The kind of loss, theft, found property or other incident the citizen wants recorded.", ["Lost document", "Lost item", "Stolen item", "Found property", "Other incident"], [
        leaf("POLICE_GD_LOST_DOCUMENT", "Lost Document GD", "Reporting a lost identity, education, travel or other document.", ["Lost document GD", "Missing certificate report"], ["Lost phone/item", "Lost Passport replacement instructions"], ["গুরুত্বপূর্ণ কাগজপত্র হারিয়ে গেলে জিডি কীভাবে করব?", "certificate হারিয়েছে, GD করতে চাই।", "lost document er jonno online GD file korbo kivabe?", "একটি পরিচয়পত্র খুঁজে পাচ্ছি না, loss report হিসেবে কোন category নেব?"], priority="Medium"),
        leaf("POLICE_GD_LOST_ITEM_DEVICE", "Lost Item or Device GD", "Reporting a lost phone, device or other property that is not primarily a document.", ["Lost phone GD", "Lost property report"], ["Stolen property", "Found item report"], ["মোবাইল বা অন্য কোনো জিনিস হারালে জিডি কীভাবে করব?", "আমার bag হারিয়েছে, online GD দিতে চাই।", "lost device er GD category konta?", "যাতায়াতের পথে একটি জিনিস পড়ে গেছে—loss complaint কীভাবে submit করব?"], priority="Medium"),
        leaf("POLICE_GD_STOLEN_ITEM", "Stolen Item GD/Complaint", "Reporting property believed to have been stolen.", ["Stolen item complaint", "Theft report through portal"], ["Merely misplaced item", "Emergency in progress"], ["জিনিস চুরি হলে অনলাইন GD-তে কোন incident category নির্বাচন করব?", "phone stolen হলে কোন complaint category ব্যবহার করব?", "churi jawa item er jonno kon GD category select korbo?", "wallet চুরি হয়েছে—online report-এ stolen item category কোনটি?"], priority="Medium", pilot_review=True),
        leaf("POLICE_GD_FOUND_ITEM", "Found Item Report", "Reporting property the citizen found and wants to notify police about.", ["Report found property", "Found item GD"], ["Recovering the citizen's lost property", "Stolen-item complaint"], ["কুড়িয়ে পাওয়া জিনিস report করতে কোন GD category নির্বাচন করব?", "একটা lost phone পেয়েছি—found item হিসেবে কোন category select করব?", "found item er jonno kon report category select korbo?", "রাস্তায় একটি ব্যাগ পেয়েছি—found property category কোনটি?"], priority="Medium"),
        leaf("POLICE_GD_OTHER_INCIDENT", "Other Non-Emergency GD Complaint", "A non-emergency complaint that does not fit the supported lost/stolen/found item groups.", ["Other GD complaint", "Non-emergency incident report"], ["Unknown/OOD question", "Immediate danger"], ["হারানো, চুরি বা পাওয়া জিনিস নয়—এমন ঘটনার জন্য কোন GD category ব্যবহার করব?", "non-emergency incident টি কোন other complaint category-তে পড়ে?", "other non-emergency complaint er jonno kon GD category select korbo?", "ঘটনাটি lost, stolen বা found item নয়—কোন other incident category নির্বাচন করব?"], priority="Medium", pilot_review=True, evidence_status="needs_pilot_validation"),
    ]),
    parent("POLICE_GD_ONLINE_ACCOUNT", "Online GD Account and Access", "Account registration, login, password, OTP, verification and general access problems.", ["Account registration", "Login", "Password", "OTP", "Identity verification", "Access problem"], [
        leaf("POLICE_GD_ACCOUNT_REGISTRATION", "Online GD Account Registration", "Creating and registering an online GD user account.", ["Create GD account", "Register for GD portal"], ["Submit complaint", "Login to existing existing account"], ["অনলাইন জিডির জন্য নতুন user account কীভাবে খুলব?", "GD portal-এ নতুন account register করার নিয়ম কী?", "online GD account create korbo kivabe?", "complaint দেওয়ার আগে নতুন GD user account বানানোর steps কী?"] ),
        leaf("POLICE_GD_ACCOUNT_LOGIN", "Online GD Account Login", "How or where to sign in to an existing online GD account.", ["GD portal login", "Sign in to account"], ["Login failure", "Password reset"], ["বিদ্যমান অনলাইন জিডি অ্যাকাউন্টে কীভাবে লগইন করব?", "GD app login option কোথায়?", "online GD account e sign in korbo kivabe?", "আগে account খুলেছি, complaint দেখতে আবার ঢোকার নিয়ম কী?"] ),
        leaf("POLICE_GD_PASSWORD_RESET", "Online GD Password Reset", "Resetting or recovering a forgotten online GD password.", ["Forgot GD password", "Reset password"], ["Generic access failure", "OTP issue"], ["অনলাইন জিডি অ্যাকাউন্টের পাসওয়ার্ড ভুলে গেলে কী করব?", "GD portal password reset করতে চাই।", "online GD password recover korbo kivabe?", "mobile number মনে আছে কিন্তু account password ভুলে গেছি—নতুনটা সেট করব কীভাবে?"], priority="Medium"),
        leaf("POLICE_GD_OTP_PROBLEM", "Online GD OTP Problem", "OTP delivery or acceptance problems during registration or access.", ["GD OTP not received", "OTP rejected"], ["Password reset without OTP issue", "Complaint reference number"], ["অনলাইন জিডির ওটিপি না এলে কী করব?", "OTP code পেয়েছি কিন্তু verify হচ্ছে না।", "GD registration code ashtese na, ki korbo?", "verification SMS দেরিতে এসে expired দেখাচ্ছে—account complete করব কীভাবে?"], priority="Medium", pilot_review=True),
        leaf("POLICE_GD_IDENTITY_VERIFICATION_PROBLEM", "Online GD Identity Verification Problem", "Problems completing identity or live-photo verification for an online GD account.", ["Identity verification failed", "Live photo not accepted"], ["Incident attachment problem", "OTP-only problem"], ["অনলাইন জিডিতে পরিচয় যাচাই সম্পন্ন হচ্ছে না; কী করব?", "live photo accept করছে না, account verify হচ্ছে না।", "GD identity verification fail hocche kivabe solve korbo?", "registration-এর face capture step বারবার error দিচ্ছে।"], priority="Medium", pilot_review=True),
        leaf("POLICE_GD_ACCOUNT_ACCESS_PROBLEM", "General Online GD Account Access Problem", "An existing account cannot be accessed and no specific credential cause is clear.", ["Cannot access GD account", "Unknown account error"], ["Known password issue", "OTP-specific issue"], ["সঠিক তথ্য দিয়েও আমার existing Online GD account-এ login করতে পারছি না।", "আমার existing GD account-এ ঢুকতে পারছি না, clear errorও দেখাচ্ছে না।", "existing online GD account e login korte parchi na, reason bujhte parchi na.", "login দেওয়ার পর account page আবার শুরুতে চলে আসে—existing account access হচ্ছে না।"], priority="Medium", pilot_review=True),
    ]),
    parent("POLICE_GD_STATUS_FOLLOWUP", "GD Status and Follow-Up", "Tracking a submitted complaint, delay, officer contact and police-station follow-up.", ["Status", "Delay", "Investigating officer", "Follow-up"], [
        leaf("POLICE_GD_STATUS", "GD Application Status", "Checking the current state of a submitted online GD complaint.", ["Check GD status", "Track complaint"], ["Complaint explicitly delayed", "Download GD copy"], ["জমা দেওয়া জিডির বর্তমান অবস্থা কীভাবে দেখব?", "আমার GD application কোন stage-এ আছে?", "online GD status check korbo kivabe?", "complaint submit হয়েছে—এখন police review-এর update কোথায় পাওয়া যাবে?"] ),
        leaf("POLICE_GD_DELAY", "GD Review or Processing Delay", "A submitted GD complaint appears stuck longer than expected.", ["GD pending too long", "Complaint delayed"], ["Normal status check", "Mutable processing-time promise"], ["জিডির আবেদন দীর্ঘদিন pending থাকলে কী করব?", "অনেক সময় হয়ে গেছে, complaint-এর update আসছে না।", "amar GD review onekdin dhore atke ache.", "submit করার পর থেকে একই status দেখাচ্ছে—follow-up কোথায় করব?"], priority="Medium", pilot_review=True),
        leaf("POLICE_GD_OFFICER_CONTACT", "Investigating Officer Contact", "Using the service to identify or communicate with the officer assigned to a complaint.", ["Contact investigating officer", "Find assigned officer"], ["Choose filing police station", "Emergency contact"], ["জিডির দায়িত্বপ্রাপ্ত তদন্তকারী কর্মকর্তার সঙ্গে কীভাবে যোগাযোগ করব?", "আমার complaint-এর assigned officer কে, কোথায় দেখব?", "investigating officer er sathe online e contact korbo kivabe?", "status page-এ officer details আছে—follow-up message পাঠানোর নিয়ম কী?"] ),
        leaf("POLICE_GD_STATION_FOLLOWUP", "Police Station Follow-Up", "Questions about when or how to follow up at the relevant police station after online submission.", ["Follow up at station", "Attend station after complaint"], ["Selecting jurisdiction before submission", "Immediate emergency response"], ["অনলাইন অভিযোগের পর থানায় follow-up কীভাবে করব?", "GD submit করেছি, police station-এ যেতে হবে কিনা কোথায় জানব?", "online complaint er por thana follow-up process ki?", "portal থেকে station attendance-এর message পেয়েছি—পরবর্তী official step জানতে চাই।"], priority="Medium", pilot_review=True),
    ]),
    parent("POLICE_GD_COPY_REFERENCE", "GD Copy, Receipt and Reference", "Access to the digital GD copy, submission acknowledgement and complaint reference.", ["GD copy", "Receipt", "Reference code"], [
        leaf("POLICE_GD_COPY_DOWNLOAD", "Digital GD Copy Download", "Downloading or sharing the digital copy of a completed GD when available.", ["Download GD copy", "Get digital GD document"], ["Submission receipt", "Application status"], ["ডিজিটাল জিডির কপি কীভাবে ডাউনলোড করব?", "completed GD copyটা কোথায় পাব?", "online GD copy download korar option kothay?", "GD number হয়েছে, এখন digital documentটা সংরক্ষণ করতে চাই।"] ),
        leaf("POLICE_GD_SUBMISSION_RECEIPT", "GD Submission Acknowledgement", "Obtaining confirmation or receipt immediately associated with complaint submission.", ["GD submission receipt", "Complaint acknowledgement"], ["Final digital GD copy", "Payment receipt"], ["জিডির অভিযোগ জমা দেওয়ার স্বীকারপত্র কোথায় পাব?", "complaint submit হয়েছে—receiptটা দরকার।", "online GD acknowledgement kivabe pabo?", "application জমা দেওয়ার proof হিসেবে confirmation copy নিতে চাই।"] ),
        leaf("POLICE_GD_REFERENCE_RECOVERY", "GD Complaint Reference Recovery", "Finding or recovering a complaint code, reference or GD number needed for access.", ["Lost complaint code", "Recover GD reference"], ["Recover account password", "Download known GD copy"], ["জিডির অভিযোগ কোড বা রেফারেন্স হারালে কীভাবে ফিরে পাব?", "আমার GD number খুঁজে পাচ্ছি না।", "complaint reference recover korbo kivabe?", "status check করার tracking codeটা সংরক্ষণ করা হয়নি—এখন কোথায় পাব?"], priority="Medium", pilot_review=True),
    ]),
    parent("POLICE_GD_TECHNICAL_PROBLEMS", "Online GD Technical Problems", "Submission failures and portal-level availability problems.", ["Submission failure", "Portal unavailable"], [
        leaf("POLICE_GD_SUBMISSION_FAILURE", "Online GD Submission Failure", "A completed complaint cannot be submitted because of an error.", ["GD submit failed", "Complaint form error"], ["Account login issue", "Attachment-only question"], ["অনলাইন জিডির অভিযোগ submit না হলে কী করব?", "সব fill up করেছি কিন্তু GD form জমা হচ্ছে না।", "online GD submission fail hocche, ki korbo?", "final button চাপলে error আসে এবং complaint number তৈরি হয় না।"], priority="Medium"),
        leaf("POLICE_GD_PORTAL_UNAVAILABLE", "Online GD Portal Unavailable", "The GD website or app itself does not load or appears unavailable.", ["GD portal down", "App not opening"], ["One complaint submission failure", "Known login problem"], ["অনলাইন জিডি website-টাই খুলছে না।", "GD app নিজেই load হচ্ছে না।", "online GD portal down dekhacche; website open hocche na.", "বিভিন্ন page try করেও GD website/app খুলছে না—service unavailable মনে হচ্ছে।"], priority="Medium"),
    ]),
    parent("POLICE_GD_GENERAL_INFORMATION", "General Online GD Service Information", "Broad orientation about available Online GD service capabilities.", ["Available GD services", "General guidance"], [
        leaf("POLICE_GD_GENERAL_SERVICE_GUIDANCE", "General Online GD Service Guidance", "Broad questions about what help and functions the online GD service provides.", ["What online GD services exist", "Where to start"], ["Specific filing question", "OOD fallback"], ["অনলাইন জিডি সেবায় কী কী ধরনের সহায়তা পাওয়া যায়?", "GD portal দিয়ে কী কী কাজ করা যায়?", "online GD service gulo somporke general guidance chai.", "complaint, status আর copy—কোন প্রয়োজনের জন্য কোন option ব্যবহার হয় বুঝতে চাই।"], pilot_review=True, evidence_status="needs_pilot_validation"),
    ]),
]


SPEC = {
    "service_id": "POLICE_GD", "service_name": "Police GD", "id_prefix": "POLICE_GD",
    "row_prefix": "PGDQ", "taxonomy_filename": "police_gd.yaml",
    "pilot_filename": "police_gd_pilot_v0_1.csv", "review_filename": "police_gd_pilot_v0_1_review.csv",
    "protocol_filename": "POLICE_GD_PILOT_PROTOCOL.md", "audit_filename": "POLICE_GD_PILOT_REVIEW_AUDIT.md",
    "source_inventory_filename": "POLICE_GD_SOURCE_INVENTORY.md", "semantic_audit_filename": "POLICE_GD_SEMANTIC_AUDIT.md",
    "description": "Working citizen-intent taxonomy for Bangladesh Police General Diary and Online GD services.",
    "design_rules": ["Classify administrative GD intent without making a legal determination.", "Keep emergency/immediate-danger routing distinct from ordinary GD guidance.", "Incident type and procedural goal are different dimensions; use the dominant request.", "General guidance is never an OOD fallback."],
    "parents": PARENTS,
    "key_boundaries": ["ordinary GD guidance vs emergency/immediate danger", "GD appropriate-use question vs filing process", "lost document vs lost item vs stolen item vs found item", "account registration vs complaint submission", "status vs abnormal delay", "final GD copy vs submission acknowledgement vs reference recovery", "station selection before filing vs follow-up after submission"],
    "source_inventory_markdown": """
# Police GD Service Source Inventory

Service: `POLICE_GD`

Status: official-domain inventory reviewed

## Official sources reviewed

- [Bangladesh Police Online GD](https://gd.police.gov.bd/) — describes
  complaint submission, identity/account prerequisites, district and station
  selection, incident details, attachments, status, investigating-officer
  contact and digital GD-copy download.
- [Online GD login](https://gd.police.gov.bd/Auth/Account/Login) — exposes
  account login and password recovery.
- [Official Online GD user manual](https://gd.police.gov.bd/UserManual/%E0%A6%85%E0%A6%A8%E0%A6%B2%E0%A6%BE%E0%A6%87%E0%A6%A8%20%E0%A6%9C%E0%A6%BF%E0%A6%A1%E0%A6%BF%20%E0%A6%87%E0%A6%89%E0%A6%9C%E0%A6%BE%E0%A6%B0%20%E0%A6%AE%E0%A7%8D%E0%A6%AF%E0%A6%BE%E0%A6%A8%E0%A7%81%E0%A7%9F%E0%A6%BE%E0%A6%B2.pdf)
  — supports the account and online-submission workflow.

The inventory records service capabilities only. It does not assert that a
particular event legally must be a GD or case, and it does not replace
emergency help. Current contact details and legal rules are excluded from
taxonomy labels.
""",
    "semantic_audit_markdown": """
# Police GD Semantic Taxonomy Audit

Service: `POLICE_GD`

Result: `PASS_WITH_PILOT_REVIEW_FLAGS`

The eight parents separate routing guidance, filing, incident type, account
access, post-submission follow-up, copy/reference access, technical failures
and broad service orientation.

## Critical boundaries

- Immediate danger is not treated as routine administrative GD guidance.
- Appropriate-use questions ask which route fits; filing questions ask how to
  carry out a chosen GD workflow. Neither leaf makes a legal conclusion.
- Lost documents, lost property, stolen property and found property are
  separable incident descriptions; emergency context overrides routine use.
- Online-account registration is not online complaint submission.
- Status asks for current state; delay reports an application stuck longer
  than expected.
- A final digital GD copy, submission acknowledgement and lost reference code
  are different access needs.
- Jurisdiction selection occurs before filing; station follow-up occurs after
  submission.

Pilot flags cover emergency/case routing, jurisdiction, ambiguous incident
types, OTP/identity/access issues, delay/follow-up, reference recovery and
general guidance. General guidance must never absorb OOD queries.

No emergency instructions, legal claims, current contact details or mutable
processing promises are encoded. The taxonomy is fit for a reviewed pilot;
the global shared contract remains unfrozen.
""",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["taxonomy", "pilot", "all"])
    args = parser.parse_args()
    if args.stage in {"taxonomy", "all"}: build_taxonomy(SPEC)
    if args.stage in {"pilot", "all"}: build_pilot(SPEC)
    print_build_summary(SPEC)


if __name__ == "__main__": main()
