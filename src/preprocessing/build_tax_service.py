"""Build the reviewed Tax taxonomy and four-seed pilot assets."""

import argparse

from service_pilot_framework import build_pilot, build_taxonomy, print_build_summary


def leaf(identifier, name, description, includes, excludes, seeds, **kwargs):
    return {
        "id": identifier,
        "display_name": name,
        "description": description,
        "includes": includes,
        "excludes": excludes,
        "seeds": seeds,
        **kwargs,
    }


def parent(identifier, name, description, covers, leaves):
    return {
        "id": identifier,
        "display_name": name,
        "description": description,
        "default_evidence_status": "official_service_supported",
        "covers": covers,
        "leaves": leaves,
    }


PARENTS = [
    parent(
        "TAX_TIN_REGISTRATION", "Taxpayer Registration and TIN",
        "Taxpayer registration, e-TIN lifecycle and access to the taxpayer certificate.",
        ["TIN registration", "e-TIN certificate", "TIN correction", "TIN cancellation"],
        [
            leaf("TAX_TIN_REGISTRATION_PROCESS", "TIN Registration Process", "How to register as a taxpayer and obtain a TIN.", ["How to register for TIN", "New taxpayer registration process"], ["Whether a person needs a TIN", "Registering only for an e-Return account"], ["নতুন করদাতা হিসেবে টিআইএন নিবন্ধনের প্রক্রিয়াটি কী?", "TIN করতে চাই, শুরুটা কোথা থেকে করব?", "e-TIN registration process ta kivabe complete korbo?", "ব্যবসা শুরু করেছি, taxpayer হিসেবে first registrationটা কীভাবে করব?" ]),
            leaf("TAX_TIN_ELIGIBILITY", "TIN Registration Eligibility", "Whether a citizen or organization needs or may obtain a TIN.", ["Who should obtain a TIN", "Whether TIN registration applies"], ["How to register", "Whether an income-tax return must be filed"], ["কারা টিআইএন নিবন্ধন করতে পারেন বা প্রয়োজন হয়?", "আমার income কম, তবুও TIN লাগবে নাকি?", "amar jonno e-TIN registration applicable kina janbo kivabe?", "freelancing শুরু করেছি—আমার ক্ষেত্রে taxpayer registration দরকার কি?"], pilot_review=True),
            leaf("TAX_TIN_ONLINE_REGISTRATION", "Online e-TIN Registration", "Starting or completing taxpayer registration through the online e-TIN service.", ["Apply for e-TIN online", "Online taxpayer registration"], ["General TIN process without online focus", "e-Return account registration"], ["অনলাইনে ই-টিআইএন নিবন্ধন কীভাবে সম্পন্ন করব?", "e-TIN online করতে কোন option-এ যাব?", "online e-TIN application ta kothay start korbo?", "ঘরে বসে taxpayer registration submit করার উপায় জানতে চাই।"]),
            leaf("TAX_TIN_REQUIRED_INFORMATION", "TIN Registration Information and Documents", "Information or supporting records needed for taxpayer registration.", ["Information needed for TIN", "TIN registration documents"], ["Return-filing documents", "A missing e-Return password"], ["টিআইএন নিবন্ধনের জন্য কী তথ্য ও কাগজপত্র প্রয়োজন?", "e-TIN করতে কী কী details দিতে হবে?", "taxpayer registration er required information ki ki?", "নিজের নামে TIN খুলতে form-এ কোন পরিচয়সংক্রান্ত তথ্য চাইবে?" ]),
            leaf("TAX_TIN_CERTIFICATE_DOWNLOAD", "e-TIN Certificate Download", "Obtaining or downloading an existing e-TIN certificate.", ["Download TIN certificate", "Get another e-TIN certificate copy"], ["Tax certificate after return filing", "Return acknowledgement"], ["আমার ই-টিআইএন সনদ কীভাবে ডাউনলোড করব?", "TIN certificate-এর আরেকটা copy কোথায় পাব?", "e-TIN certificate download korar option kothay?", "taxpayer registration হয়ে গেছে, এখন certificateটা print করতে চাই।"]),
            leaf("TAX_TIN_INFORMATION_UPDATE", "TIN Information Correction or Update", "Correcting or updating information associated with an existing TIN.", ["Correct TIN information", "Update taxpayer profile data"], ["Correcting a submitted return", "Changing only e-Return login credentials"], ["ই-টিআইএনে ভুল তথ্য কীভাবে সংশোধন করব?", "TIN profile-এর address update করতে চাই।", "e-TIN information correction er process ki?", "taxpayer record-এ নামের spelling ভুল দেখাচ্ছে, update করব কীভাবে?"], priority="Medium"),
            leaf("TAX_TIN_CANCELLATION", "TIN Cancellation or Inactivation", "Questions about requesting cancellation or inactivation of an existing TIN.", ["Cancel a TIN", "TIN no longer required"], ["Closing an online account", "Amending a tax return"], ["বিদ্যমান টিআইএন বাতিলের আবেদন কীভাবে করব?", "TIN আর দরকার নেই, deactivate করা যাবে?", "e-TIN cancellation request kivabe dite hoy?", "দুইটা TIN হয়ে গেছে—একটা বন্ধ করার official process জানতে চাই।"], priority="Medium", pilot_review=True, evidence_status="needs_pilot_validation"),
        ],
    ),
    parent(
        "TAX_RETURN_FILING", "Income Tax Return Filing",
        "Return obligation, preparation, online submission, information entry, amendment and deadlines.",
        ["Return obligation", "Return filing", "Online return", "Return amendment", "Deadline"],
        [
            leaf("TAX_RETURN_OBLIGATION", "Tax Return Filing Obligation", "Whether the citizen is required or expected to file an income-tax return.", ["Who must file a return", "Whether return filing applies"], ["Whether a TIN is needed", "How to file a return"], ["কার আয়কর রিটার্ন দাখিল করা প্রয়োজন?", "TIN আছে, return file করতেই হবে নাকি?", "amar income tax return submit kora mandatory kina?", "চাকরির আয় আছে—আমার ক্ষেত্রে return filing obligation আছে কি?"], pilot_review=True),
            leaf("TAX_RETURN_PROCESS", "Income Tax Return Filing Process", "General end-to-end questions about preparing and filing a return.", ["How to file a return", "Return submission process"], ["Online-account registration", "Checking a submitted return"], ["আয়কর রিটার্ন দাখিলের সম্পূর্ণ প্রক্রিয়াটি কী?", "tax return করতে চাই, কীভাবে শুরু করব?", "income tax return filing process ta ki?", "প্রথমবার return জমা দেব—ধাপগুলো বুঝতে চাই।"]),
            leaf("TAX_RETURN_ONLINE_SUBMISSION", "Online Tax Return Submission", "Submitting an income-tax return through the official e-Return system.", ["File return online", "Submit e-Return"], ["Registering an e-Return account", "Offline/general filing without online focus"], ["অনলাইনে আয়কর রিটার্ন কীভাবে জমা দেব?", "e-Return portal দিয়ে return submit করব কীভাবে?", "online tax return file korar niyom ki?", "account-এ ঢুকেছি, এখন electronic return submission কোথা থেকে শুরু করব?"] ),
            leaf("TAX_RETURN_REQUIRED_DOCUMENTS", "Tax Return Information and Documents", "Records and supporting information needed to prepare a tax return.", ["Documents for return filing", "Information needed for return"], ["TIN registration documents", "Payment receipt only"], ["আয়কর রিটার্ন তৈরির জন্য কী কী নথি ও তথ্য প্রয়োজন?", "return file করতে কোন papers ready রাখব?", "tax return er required documents ki ki?", "বেতন আর ব্যাংকের তথ্যসহ return বানাতে কোন records জোগাড় করতে হবে?"] ),
            leaf("TAX_RETURN_INCOME_INFORMATION", "Income Information in Tax Return", "How income categories or income details are entered in a return.", ["Enter salary income", "Report different income sources"], ["Asset and liability statement", "Current tax rate answers"], ["রিটার্নে আয়ের তথ্য কীভাবে উল্লেখ করতে হয়?", "salary income কোন section-এ দেব?", "different income source return e kivabe show korbo?", "চাকরি আর বাড়িভাড়ার আয় দুটোই আছে—return-এ কীভাবে record করব?"] ),
            leaf("TAX_RETURN_ASSET_LIABILITY", "Assets and Liabilities in Tax Return", "Questions about declaring assets, liabilities or expenses in a return.", ["Enter assets in return", "Report liabilities"], ["Income-only information", "Payment method"], ["আয়কর রিটার্নে সম্পদ ও দায়ের তথ্য কীভাবে দেব?", "return-এ loan আর asset কোথায় লিখব?", "tax return e assets liabilities entry korbo kivabe?", "নিজের savings আর ঋণের তথ্য কোন অংশে দেখাতে হবে বুঝছি না।"] ),
            leaf("TAX_RETURN_AMENDMENT", "Submitted Tax Return Amendment", "Correcting or revising an already submitted return when supported.", ["Correct submitted return", "Amend return information"], ["Editing before submission", "TIN profile correction"], ["জমা দেওয়া আয়কর রিটার্নে ভুল থাকলে সংশোধন কীভাবে করব?", "submitted returnটা revise করা যাবে?", "filed tax return amendment er process ki?", "return submit করার পর একটি income entry ভুল দেখেছি—official correction option জানতে চাই।"], priority="Medium", pilot_review=True, evidence_status="needs_source_review"),
            leaf("TAX_RETURN_DEADLINE", "Tax Return Filing Deadline", "Questions asking when a return must be submitted, without encoding a date.", ["When is return due", "Return submission deadline"], ["Application processing delay", "Penalty amount"], ["আয়কর রিটার্ন জমা দেওয়ার সময়সীমা কীভাবে জানব?", "return submission-এর last date কোথায় দেখব?", "tax return deadline kobe seta kivabe check korbo?", "এই করবর্ষের return কবে পর্যন্ত দেওয়া যাবে—official notice কোথায় পাব?"], evidence_status="needs_source_review"),
        ],
    ),
    parent(
        "TAX_ONLINE_ACCOUNT", "e-Return Online Account",
        "Registration, login, credential recovery and access problems for the e-Return account.",
        ["Account registration", "Login", "Password reset", "Mobile update", "OTP", "Access problem"],
        [
            leaf("TAX_ACCOUNT_REGISTRATION", "e-Return Account Registration", "Creating an account for the e-Return service.", ["Create e-Return account", "Register for online return service"], ["Registering for a TIN", "Submitting a return"], ["ই-রিটার্ন ব্যবহারের জন্য নতুন অ্যাকাউন্ট কীভাবে খুলব?", "e-Return account register করতে চাই।", "tax return portal e account khulbo kivabe?", "TIN আছে, এখন online return service-এর login account বানাতে চাই।"]),
            leaf("TAX_ACCOUNT_LOGIN", "e-Return Account Login", "How or where to sign in to an existing e-Return account.", ["Sign in to e-Return", "Find login page"], ["Login failure", "Password reset"], ["বিদ্যমান ই-রিটার্ন অ্যাকাউন্টে কীভাবে লগইন করব?", "e-Return login page কোথায়?", "tax portal e sign in korbo kivabe?", "account আগে থেকেই আছে, return দেখতে portal-এ ঢোকার নিয়ম কী?"] ),
            leaf("TAX_ACCOUNT_PASSWORD_RESET", "e-Return Password Reset", "Recovering or resetting a forgotten e-Return password.", ["Forgot e-Return password", "Reset password"], ["Generic login failure", "Changing registered mobile"], ["ই-রিটার্নের পাসওয়ার্ড ভুলে গেলে কীভাবে রিসেট করব?", "tax portal password মনে নেই, recover করতে চাই।", "e-Return password reset korbo kivabe?", "TIN মনে আছে কিন্তু account passwordটা ভুলে গেছি—নতুন password সেট করব কীভাবে?"], priority="Medium"),
            leaf("TAX_ACCOUNT_MOBILE_UPDATE", "e-Return Registered Mobile Update", "Changing the mobile number linked to an e-Return account.", ["Change registered mobile", "Old mobile unavailable"], ["TIN information update", "OTP not received on an active number"], ["ই-রিটার্ন অ্যাকাউন্টে নিবন্ধিত মোবাইল নম্বর কীভাবে বদলাব?", "old phone number বন্ধ হয়ে গেছে, tax account-এ নতুনটা update করতে চাই।", "e-Return registered mobile change korar process ki?", "login verification পুরোনো SIM-এ যাচ্ছে—linked numberটা বদলাতে হবে।"], priority="Medium"),
            leaf("TAX_ACCOUNT_OTP_PROBLEM", "e-Return OTP Problem", "OTP delivery or acceptance problems during account access or registration.", ["e-Return OTP not received", "OTP rejected"], ["Forgotten password without OTP issue", "Return verification failure"], ["ই-রিটার্ন নিবন্ধনের ওটিপি না এলে কী করব?", "OTP পেয়েছি কিন্তু tax portal accept করছে না।", "e-Return verification code ashtese na, ki korbo?", "account verify করতে code চেয়েছি, বারবার expired দেখাচ্ছে।"], priority="Medium", pilot_review=True),
            leaf("TAX_ACCOUNT_ACCESS_PROBLEM", "General e-Return Account Access Problem", "An existing account cannot be accessed and no more specific cause is known.", ["Cannot access e-Return account", "Unknown sign-in problem"], ["Forgotten password", "OTP-specific problem"], ["সঠিক তথ্য দিয়েও ই-রিটার্ন অ্যাকাউন্টে প্রবেশ করতে পারছি না।", "tax account open হচ্ছে না, কারণটা বুঝতে পারছি না।", "e-Return account access hocche na, kono clear error nai.", "login করতে গেলেই আবার প্রথম page-এ ফিরিয়ে দেয়—কী সমস্যা বুঝছি না।"], priority="Medium", pilot_review=True),
        ],
    ),
    parent(
        "TAX_PAYMENT", "Tax Payment and Ledger",
        "Tax amount guidance, payment channels, transaction outcomes and payment-record updates.",
        ["Tax calculation", "Payment method", "Payment confirmation", "Payment failure", "Ledger"],
        [
            leaf("TAX_PAYMENT_AMOUNT_CALCULATION", "Tax Amount and Calculation Guidance", "How payable tax is determined without encoding rates or thresholds.", ["How tax amount is calculated", "Where payable tax is shown"], ["Exact current tax answer", "Payment method"], ["প্রদেয় আয়কর কীভাবে হিসাব করা হয়?", "আমার payable tax amount কোথায় দেখাবে?", "tax calculation ta system e kivabe dekhbo?", "return-এর তথ্য দেওয়ার পর কত tax due হয়েছে সেটা কোন section-এ বুঝব?"], evidence_status="needs_source_review"),
            leaf("TAX_PAYMENT_METHOD", "Tax Payment Method", "How or through which supported channel tax is paid.", ["How to pay tax", "Available payment channels"], ["How much tax is due", "Whether payment succeeded"], ["আয়কর কীভাবে পরিশোধ করা যায়?", "tax payment-এর available method কী কী?", "income tax online e pay korbo kivabe?", "return submit করার আগে payable amountটা কোন channel দিয়ে জমা দেব?"] ),
            leaf("TAX_PAYMENT_CONFIRMATION", "Tax Payment Confirmation", "Checking whether an attempted tax payment was recorded successfully.", ["Confirm tax payment", "Payment status"], ["How to pay", "Money deducted but failed"], ["আয়কর পরিশোধ সফল হয়েছে কি না কীভাবে যাচাই করব?", "tax paymentটা system-এ record হয়েছে কিনা দেখব কীভাবে?", "income tax payment confirm hoise kina janbo kivabe?", "transaction শেষ করেছি, return ledger-এ payment reflect করেছে কি না check করতে চাই।"] ),
            leaf("TAX_PAYMENT_FAILURE", "Tax Payment Failure", "A tax-payment attempt fails or cannot be completed.", ["Tax payment failed", "Cannot complete payment"], ["Payment method", "Payment successfully made"], ["আয়কর পরিশোধের চেষ্টা ব্যর্থ হলে কী করব?", "tax payment বারবার fail করছে।", "income tax transaction complete hocche na, ki korbo?", "payment page পর্যন্ত যাই কিন্তু submit দিলেই error আসে।"], priority="Medium"),
            leaf("TAX_PAYMENT_LEDGER_UPDATE", "Tax Payment Ledger Update", "Updating or resolving missing tax-payment information in the e-Return ledger.", ["Update payment ledger", "Payment missing from tax record"], ["Making a new payment", "Downloading acknowledgement"], ["ই-রিটার্ন লেজারে কর পরিশোধের তথ্য কীভাবে আপডেট করব?", "tax paid কিন্তু ledger-এ দেখাচ্ছে না।", "e-Return ledger e payment update korbo kivabe?", "আগের tax paymentটা return record-এ যোগ করতে চাই, কোন service ব্যবহার করব?"], priority="Medium", pilot_review=True),
        ],
    ),
    parent(
        "TAX_STATUS_AND_DOCUMENTS", "Return Status and Tax Documents",
        "Verification of submitted returns and access to acknowledgements, copies and certificates.",
        ["Return verification", "Acknowledgement", "Return copy", "Tax certificate"],
        [
            leaf("TAX_RETURN_STATUS_VERIFICATION", "Submitted Return Status and Verification", "Checking or verifying whether a submitted return is recorded.", ["Verify submitted return", "Check return status"], ["Return filing process", "Payment confirmation"], ["জমা দেওয়া আয়কর রিটার্নের অবস্থা কীভাবে যাচাই করব?", "আমার return submit হয়েছে কিনা online-এ দেখব কীভাবে?", "filed tax return verify korar niyom ki?", "submission শেষ হয়েছে, এখন ReturnVerify দিয়ে recordটা check করতে চাই।"] ),
            leaf("TAX_RETURN_ACKNOWLEDGEMENT", "Return Acknowledgement or Submission Receipt", "Obtaining proof or acknowledgement of return submission.", ["Download return acknowledgement", "Get submission receipt"], ["Tax payment receipt", "Tax certificate"], ["রিটার্ন জমার স্বীকারপত্র কীভাবে ডাউনলোড করব?", "return submission receipt কোথায় পাব?", "tax return acknowledgement download korbo kivabe?", "online return দিয়েছি, এখন proof of submission দরকার।"] ),
            leaf("TAX_RETURN_COPY_DOWNLOAD", "Submitted Tax Return Copy", "Accessing or downloading a copy of the submitted return.", ["Download filed return", "Get return copy"], ["Acknowledgement only", "e-TIN certificate"], ["জমা দেওয়া আয়কর রিটার্নের কপি কীভাবে পাব?", "filed returnটা download করতে চাই।", "submitted tax return copy kothay pabo?", "গত submission-এর full return document আবার দেখতে চাই।"] ),
            leaf("TAX_CERTIFICATE_ACCESS", "Income Tax Certificate Access", "Obtaining an available income-tax certificate after the relevant tax workflow.", ["Download tax certificate", "Get income-tax certificate"], ["e-TIN registration certificate", "Return acknowledgement"], ["আয়কর সনদ কীভাবে সংগ্রহ বা ডাউনলোড করব?", "tax certificate কোথায় পাওয়া যাবে?", "income tax certificate download korar option kothay?", "return complete হয়েছে, এখন official tax certificateটা নিতে চাই।"], pilot_review=True),
        ],
    ),
    parent(
        "TAX_GENERAL_AND_SUPPORT", "General Tax Information and Support",
        "General service orientation, tax records and official support requests.",
        ["General tax guidance", "Tax record", "Online support"],
        [
            leaf("TAX_GENERAL_SERVICE_GUIDANCE", "General Income Tax Service Guidance", "Broad orientation about available income-tax services without a specific transaction.", ["What tax services exist", "Where to start with tax services"], ["A specific return or payment question", "OOD queries"], ["আয়কর সংক্রান্ত কী কী অনলাইন সেবা পাওয়া যায়?", "tax service নিয়ে শুরুতে কোথা থেকে guidance পাব?", "Bangladesh income tax service gulo somporke jante chai.", "TIN, return আর certificate—কোন কাজের জন্য কোন service ব্যবহার হয় বুঝতে চাই।"], pilot_review=True, evidence_status="needs_pilot_validation"),
            leaf("TAX_RECORD_INFORMATION", "Tax Record Information", "Viewing or understanding the taxpayer's available tax record/history.", ["View tax record", "Find previous return history"], ["Verify a single new submission", "Payment ledger only"], ["আমার আগের কর রেকর্ড কোথায় দেখা যাবে?", "previous tax return history দেখতে চাই।", "amar tax record gulo online e kivabe dekhbo?", "পুরোনো assessment আর return information কোন menu-তে পাওয়া যায়?" ]),
            leaf("TAX_SUPPORT_REQUEST", "e-Return Support Request", "Seeking official help or submitting a support request for an e-Return issue.", ["Get e-Return support", "Submit tax-service ticket"], ["A clearly classifiable account problem", "General tax definition"], ["ই-রিটার্ন সমস্যার জন্য সহায়তার আবেদন কীভাবে করব?", "tax portal issue নিয়ে support ticket দিতে চাই।", "e-Return help request kothay submit korbo?", "online tax service-এর problemটা support team-কে জানাতে কোন ব্যবস্থা আছে?"], priority="Medium"),
        ],
    ),
]


SPEC = {
    "service_id": "TAX",
    "service_name": "Tax",
    "id_prefix": "TAX",
    "row_prefix": "TAXQ",
    "taxonomy_filename": "tax.yaml",
    "pilot_filename": "tax_pilot_v0_1.csv",
    "review_filename": "tax_pilot_v0_1_review.csv",
    "protocol_filename": "TAX_PILOT_PROTOCOL.md",
    "audit_filename": "TAX_PILOT_REVIEW_AUDIT.md",
    "source_inventory_filename": "TAX_SOURCE_INVENTORY.md",
    "semantic_audit_filename": "TAX_SEMANTIC_AUDIT.md",
    "description": "Working intent taxonomy for Bangladesh NBR taxpayer, e-TIN, e-Return, payment, document and support queries.",
    "design_rules": [
        "Classify the citizen's primary information need, not a changing tax answer.",
        "Do not encode current rates, thresholds, dates, payment providers or legal conclusions.",
        "General guidance is a real orientation intent and never an OOD fallback.",
        "Specific account, filing, payment and document intents take precedence over broad labels.",
    ],
    "parents": PARENTS,
    "key_boundaries": [
        "TIN eligibility vs return-filing obligation",
        "TIN registration vs e-Return account registration",
        "return process vs online submission",
        "payment method vs confirmation vs failure vs ledger update",
        "return verification vs acknowledgement vs full return copy",
        "e-TIN certificate vs income-tax certificate",
        "general service guidance vs OOD/low confidence",
    ],
    "source_inventory_markdown": """
# Tax Service Source Inventory

Service: `TAX`

Status: official-domain inventory reviewed

## Official sources reviewed

- [NBR e-Return landing page](https://etaxnbr.gov.bd/) — exposes e-TIN,
  e-Return, ReturnVerify/PSR, e-Return Ledger, e-TaxPayment and e-TaxService.
- [NBR e-Services FAQ](https://nbr.gov.bd/all-faq/eservices/eservices) —
  describes account registration/sign-in, return-submission sections, tax and
  payment information, and official support.
- [NBR Taxpayer User Manual](https://nbr.gov.bd/uploads/publications/e-Return_user_manual.pdf)
  — documents registration, sign-in, password recovery and the e-Return flow.

Access context: official web material reviewed for stable service capability,
not for mutable rates, thresholds, dates or legal advice.

## Stable citizen-demand areas

The sources support taxpayer/TIN registration, e-Return account access,
return preparation and submission, payment and ledger questions, return
verification, certificates and support. TIN cancellation, submitted-return
amendment and deadline questions remain explicit source/pilot review areas.

No mutable tax amount, filing date, legal threshold or provider list is
encoded in the taxonomy.
""",
    "semantic_audit_markdown": """
# Tax Semantic Taxonomy Audit

Service: `TAX`

Result: `PASS_WITH_PILOT_REVIEW_FLAGS`

## Parent review

The six parents separate taxpayer identity/TIN lifecycle, return filing,
online-account access, payment/ledger, status/documents and general support.
This is a citizen-intent hierarchy rather than a copy of portal navigation.

## High-risk boundaries

- TIN eligibility asks whether taxpayer registration applies; return
  obligation asks whether a return must be filed.
- Online e-TIN registration creates a taxpayer identity; e-Return account
  registration creates access to the filing service.
- Return process is general; online submission explicitly concerns the
  electronic workflow.
- Payment amount/calculation, method, confirmation, failure and ledger update
  are distinct requested outcomes.
- Return verification checks a filed record; acknowledgement proves
  submission; return-copy access retrieves the submitted document.
- e-TIN certificate and income-tax certificate remain distinct documents.
- General guidance cannot absorb unsupported, legal-advice or OOD queries.

## Pilot-review flags

Explicit pilot attention is required for TIN eligibility/cancellation,
return obligation/amendment, OTP/access problems, payment-ledger update,
tax-certificate access and broad service guidance. These are coherent enough
to test but must not be treated as unquestionable production labels.

No leaf contains a tax rate, threshold, deadline date, fee, office address or
current provider. The hierarchy is acceptable for a controlled four-seed
pilot. The global shared contract remains unfrozen.
""",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["taxonomy", "pilot", "all"])
    args = parser.parse_args()
    if args.stage in {"taxonomy", "all"}:
        build_taxonomy(SPEC)
    if args.stage in {"pilot", "all"}:
        build_pilot(SPEC)
    print_build_summary(SPEC)


if __name__ == "__main__":
    main()
