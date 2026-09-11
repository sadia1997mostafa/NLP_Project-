"""Build the reviewed Driving Licence taxonomy and four-seed pilot assets."""

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
    parent("DRIVING_LICENCE_LEARNER", "Learner Driving Licence", "Eligibility, application, supporting evidence, medical certificate and access to a learner licence.", ["Learner eligibility", "Learner application", "Documents", "Medical", "Learner copy"], [
        leaf("DRIVING_LICENCE_LEARNER_ELIGIBILITY", "Learner Licence Eligibility", "Whether a person qualifies or may apply for a learner licence.", ["Who may get learner licence", "Learner eligibility conditions"], ["Full licence eligibility", "How to apply"], ["শিক্ষানবিশ ড্রাইভিং লাইসেন্সের জন্য কারা আবেদন করতে পারেন?", "learner licence করার eligibility কী?", "ami learner driving licence er jonno eligible kina?", "গাড়ি চালানো শেখা শুরু করব—learner permit-এর জন্য qualify করি কি না জানতে চাই।"], pilot_review=True, evidence_status="needs_source_review"),
        leaf("DRIVING_LICENCE_LEARNER_PROCESS", "Learner Licence Application Process", "General end-to-end process for obtaining a learner licence.", ["How to apply for learner", "Learner licence steps"], ["Full smart-card licence process", "Test scheduling only"], ["শিক্ষানবিশ ড্রাইভিং লাইসেন্স করার প্রক্রিয়াটি কী?", "learner licence করতে চাই, কীভাবে শুরু করব?", "learner driving licence application process ta ki?", "প্রথমে learner permit নেওয়ার ধাপগুলো সহজভাবে জানতে চাই।"]),
        leaf("DRIVING_LICENCE_LEARNER_DOCUMENTS", "Learner Licence Required Documents", "Documents and information needed for a learner application.", ["Learner documents", "Information for learner form"], ["Full licence documents", "Test-day preparation"], ["লার্নার ড্রাইভিং লাইসেন্সের জন্য কী কী কাগজপত্র লাগে?", "learner application-এ কোন documents লাগবে?", "learner licence er required papers ki ki?", "learner form জমা দেওয়ার আগে কোন পরিচয় আর supporting records ready রাখব?"] ),
        leaf("DRIVING_LICENCE_LEARNER_MEDICAL", "Learner Licence Medical Certificate", "Questions about the medical-certificate requirement for learner or licence processing.", ["Medical certificate for licence", "Where medical form is used"], ["General documents", "Medical diagnosis or advice"], ["ড্রাইভিং লাইসেন্স আবেদনে মেডিকেল সার্টিফিকেট কীভাবে জমা দেব?", "learner licence করতে medical form লাগবে?", "driving licence medical certificate er process ki?", "application-এর health certificate কোন stage-এ attach করতে হয় জানতে চাই।"], pilot_review=True),
        leaf("DRIVING_LICENCE_LEARNER_COPY", "Learner Licence Copy or Download", "Obtaining or printing an issued learner licence or permit.", ["Download learner licence", "Print learner permit"], ["Smart-card collection", "Learner application status"], ["ইস্যু হওয়া লার্নার লাইসেন্স কীভাবে ডাউনলোড করব?", "learner permit-এর print copy কোথায় পাব?", "learner licence download korar option kothay?", "application approve হয়েছে, এখন learner documentটা ফোনে নিতে চাই।"]),
    ]),
    parent("DRIVING_LICENCE_APPLICATION", "New Driving Licence Application", "Application for a new full/smart-card driving licence, including online submission, licence type and vehicle class.", ["New licence", "Online application", "Professional type", "Vehicle class"], [
        leaf("DRIVING_LICENCE_NEW_PROCESS", "New Driving Licence Application Process", "General process for obtaining a full driving licence after the appropriate preceding steps.", ["How to get new licence", "Full licence process"], ["Learner application", "Renewal"], ["নতুন পূর্ণাঙ্গ ড্রাইভিং লাইসেন্স পাওয়ার প্রক্রিয়াটি কী?", "learner আছে, এখন main driving licence করতে কী হবে?", "new smart card driving licence process ta ki?", "driving test-এর ধাপ পেরিয়ে licence issue করার application কীভাবে করব?"] ),
        leaf("DRIVING_LICENCE_ONLINE_APPLICATION", "Online Driving Licence Application", "Starting or submitting a driving-licence application through BSP.", ["Apply for licence online", "Submit BSP application"], ["BSP account registration", "General offline process"], ["বিআরটিএ সার্ভিস পোর্টালে ড্রাইভিং লাইসেন্সের আবেদন কীভাবে করব?", "driving licence online apply করতে কোথায় যাব?", "BSP diye licence application submit korbo kivabe?", "portal account আছে, এখন new licence formটা online-এ শুরু করতে চাই।"] ),
        leaf("DRIVING_LICENCE_TYPE_SELECTION", "Professional or Non-Professional Licence Type", "Choosing or understanding the requested professional/non-professional licence type.", ["Professional licence type", "Non-professional licence choice"], ["Vehicle class selection", "Eligibility answer with mutable rules"], ["পেশাদার ও অপেশাদার ড্রাইভিং লাইসেন্সের মধ্যে কোন ধরন নির্বাচন করব?", "professional licence আর non-professional-এর application type কীভাবে choose করব?", "driving licence type selection ta bujhbo kivabe?", "নিজের গাড়ি আর পেশাগত driving-এর জন্য licence category আলাদা কি না guidance চাই।"], pilot_review=True),
        leaf("DRIVING_LICENCE_VEHICLE_CLASS", "Driving Licence Vehicle Class Selection", "Selecting the relevant motor-vehicle class for a licence application.", ["Select vehicle class", "Motorcycle/car class"], ["Professional/non-professional type", "Adding a class to existing licence"], ["ড্রাইভিং লাইসেন্স আবেদনে মোটরযানের শ্রেণি কীভাবে নির্বাচন করব?", "motorcycle আর car-এর জন্য কোন class select হবে?", "licence vehicle class choose korar niyom ki?", "একেবারে নতুন application-এ কোন vehicle category চাই সেটা form-এ কোথায় দেব?"] ),
    ]),
    parent("DRIVING_LICENCE_TEST", "Driving Competency Test", "Test process, scheduling, preparation, results and another attempt after an unsuccessful test.", ["Test process", "Schedule", "Requirements", "Result", "Retake"], [
        leaf("DRIVING_LICENCE_TEST_PROCESS", "Driving Test Process", "General questions about stages of the driving competency test.", ["What happens in driving test", "Test stages"], ["Test schedule", "Test result"], ["ড্রাইভিং লাইসেন্সের যোগ্যতা পরীক্ষায় কী কী ধাপ থাকে?", "driving test দিতে গেলে processটা কী?", "DCTC test process ta kivabe hoy?", "written আর practical অংশসহ পুরো পরীক্ষার flow জানতে চাই।"] ),
        leaf("DRIVING_LICENCE_TEST_SCHEDULE", "Driving Test Schedule or Appointment", "Finding or arranging the date/time of a driving test.", ["Find test date", "Schedule driving test"], ["Test result", "General test process"], ["ড্রাইভিং পরীক্ষার তারিখ কীভাবে নির্ধারণ বা দেখব?", "আমার driving test কবে, কোথায় check করব?", "driving test schedule online e kivabe dekhbo?", "learner licence হয়ে গেছে—competency test-এর appointment কোন step-এ পাব?"] ),
        leaf("DRIVING_LICENCE_TEST_REQUIREMENTS", "Driving Test Requirements and Preparation", "What to bring or prepare for the driving test.", ["Documents for test day", "How to prepare for test"], ["Learner application documents", "Current test answers"], ["ড্রাইভিং পরীক্ষার দিনে কী কী সঙ্গে নিতে হবে?", "test attend করার আগে কী preparation দরকার?", "driving test day er requirements ki ki?", "exam venue-তে যাওয়ার আগে documents আর vehicle নিয়ে কী প্রস্তুতি রাখব?"] ),
        leaf("DRIVING_LICENCE_TEST_RESULT", "Driving Test Result", "Checking the result of a completed driving competency test.", ["Check DCTC result", "Driving test pass status"], ["Test schedule", "Licence application status"], ["ড্রাইভিং কম্পিটেন্সি পরীক্ষার ফলাফল কীভাবে দেখব?", "driving test pass করেছি কিনা কোথায় check করব?", "DCTC result online e kivabe dekhbo?", "exam শেষ হয়েছে, এখন division-wise result list থেকে নিজের outcome জানতে চাই।"] ),
        leaf("DRIVING_LICENCE_TEST_RETAKE", "Driving Test Retake Guidance", "Questions about the next test attempt after an unsuccessful or missed test.", ["Retake failed driving test", "Missed test next step"], ["First test schedule", "Current legal retake interval"], ["ড্রাইভিং পরীক্ষায় উত্তীর্ণ না হলে পুনরায় পরীক্ষার প্রক্রিয়া কী?", "test miss করেছি, next attempt কীভাবে পাব?", "driving test retake er jonno ki korte hobe?", "result unsuccessful এসেছে—আবার competency test দেওয়ার official step জানতে চাই।"], priority="Medium", pilot_review=True, evidence_status="needs_source_review"),
    ]),
    parent("DRIVING_LICENCE_ONLINE_ACCOUNT", "BRTA Service Portal Account", "BSP account registration, login, password, OTP and general access problems.", ["Account registration", "Login", "Password", "OTP", "Access problem"], [
        leaf("DRIVING_LICENCE_ACCOUNT_REGISTRATION", "BRTA Portal Account Registration", "Creating a service-recipient account on BSP.", ["Create BSP account", "Register as driver"], ["Submit licence application", "Login to existing account"], ["বিআরটিএ সার্ভিস পোর্টালে নতুন অ্যাকাউন্ট কীভাবে খুলব?", "BSP-তে driver হিসেবে register করতে চাই।", "BRTA portal account create korbo kivabe?", "licence apply করার আগে service recipient profile বানানোর ধাপ কী?"] ),
        leaf("DRIVING_LICENCE_ACCOUNT_LOGIN", "BRTA Portal Account Login", "How or where to sign in to an existing BSP account.", ["Login to BSP", "Find sign-in"], ["Login failure", "Password reset"], ["বিদ্যমান বিআরটিএ সার্ভিস পোর্টাল অ্যাকাউন্টে কীভাবে লগইন করব?", "BSP login কোথা থেকে করব?", "BRTA account e sign in korbo kivabe?", "driver profile আগে বানানো আছে, এখন আবার portal-এ ঢোকার নিয়ম কী?"] ),
        leaf("DRIVING_LICENCE_PASSWORD_RESET", "BRTA Portal Password Reset", "Recovering or resetting a forgotten BSP password.", ["Forgot BSP password", "Reset password"], ["Generic access problem", "OTP-only issue"], ["বিআরটিএ পোর্টালের পাসওয়ার্ড ভুলে গেলে কীভাবে রিসেট করব?", "BSP password মনে নেই, recover করতে চাই।", "BRTA portal password reset korbo kivabe?", "account user information আছে কিন্তু password হারিয়েছি—নতুনটা সেট করতে চাই।"], priority="Medium"),
        leaf("DRIVING_LICENCE_ACCOUNT_OTP", "BRTA Portal OTP Problem", "OTP delivery or acceptance problems in a portal workflow.", ["BSP OTP not received", "OTP invalid"], ["Password forgotten", "Payment verification"], ["বিআরটিএ পোর্টালের ওটিপি না এলে কী করব?", "OTP code পেয়েছি কিন্তু BSP accept করছে না।", "BRTA verification code ashtese na.", "account verify করার SMS দেরিতে এসে expired দেখাচ্ছে—কীভাবে complete করব?"], priority="Medium", pilot_review=True),
        leaf("DRIVING_LICENCE_ACCOUNT_ACCESS_PROBLEM", "General BRTA Portal Access Problem", "An existing BSP account cannot be accessed and no specific known cause is stated.", ["Cannot access BSP account", "Unknown portal-account error"], ["Known password issue", "Portal entirely unavailable"], ["সঠিক তথ্য দিয়েও বিআরটিএ পোর্টাল অ্যাকাউন্টে ঢুকতে পারছি না।", "BSP account খুলছে না, error-এর কারণ বুঝছি না।", "BRTA account access hocche na, ki korbo?", "login দেওয়ার পর page আবার শুরুতে আসে—কোন specific messageও নেই।"], priority="Medium", pilot_review=True),
    ]),
    parent("DRIVING_LICENCE_PAYMENT", "Driving Licence Fees and Payment", "Fee information, payment channels, verification and failed transactions.", ["Fee", "Payment method", "Verification", "Failure"], [
        leaf("DRIVING_LICENCE_FEE_INFORMATION", "Driving Licence Fee Information", "Whether a licence service has a charge or how to find its official fee.", ["Licence fee amount", "Official fee calculator"], ["How to pay", "Exact fee embedded in label"], ["ড্রাইভিং লাইসেন্স সেবার সরকারি ফি কীভাবে জানব?", "learner বা renewal-এর fee কত, কোথায় check করব?", "driving licence fee calculator use korbo kivabe?", "যে licence service select করেছি তার current charge portal-এ কোথায় দেখাবে?"] ),
        leaf("DRIVING_LICENCE_PAYMENT_METHOD", "Driving Licence Payment Method", "How or through which supported channel a licence fee is paid.", ["Pay licence fee", "Payment channel"], ["Fee amount", "Payment verification"], ["ড্রাইভিং লাইসেন্সের ফি কীভাবে পরিশোধ করব?", "BSP payment-এর available method কী?", "driving licence fee online e pay korbo kivabe?", "application তৈরি হয়েছে, এখন chargeটা কোন channel দিয়ে জমা দেব?"] ),
        leaf("DRIVING_LICENCE_PAYMENT_VERIFICATION", "Driving Licence Payment Verification", "Checking whether a completed licence payment was successfully recorded.", ["Verify licence payment", "Payment status"], ["How to pay", "Failed transaction"], ["ড্রাইভিং লাইসেন্সের payment সফল হয়েছে কি না কীভাবে যাচাই করব?", "BSP-তে fee paid দেখাচ্ছে কিনা check করতে চাই।", "licence payment verify korar option kothay?", "transaction শেষ করেছি—application-এর সঙ্গে টাকা record হয়েছে কি না জানতে চাই।"] ),
        leaf("DRIVING_LICENCE_PAYMENT_FAILURE", "Driving Licence Payment Failure", "A licence-fee transaction cannot be completed or fails.", ["Licence payment failed", "Transaction error"], ["Payment method", "Successful payment verification"], ["ড্রাইভিং লাইসেন্সের ফি পরিশোধ ব্যর্থ হলে কী করব?", "BSP payment বারবার fail করছে।", "licence fee transaction complete hocche na.", "pay button দেওয়ার পর error আসে এবং application এগোয় না।"], priority="Medium"),
    ]),
    parent("DRIVING_LICENCE_STATUS_DELIVERY", "Licence Status, Issuance and Delivery", "Application tracking, delays, readiness and collection/delivery of the issued licence.", ["Status", "Delay", "Ready", "Collection", "Digital verification"], [
        leaf("DRIVING_LICENCE_APPLICATION_STATUS", "Driving Licence Application Status", "Checking the current stage of a submitted licence application.", ["Track licence application", "Check current status"], ["Explicit delay", "Test result"], ["ড্রাইভিং লাইসেন্স আবেদনের বর্তমান অবস্থা কীভাবে দেখব?", "আমার licence application কোন stage-এ আছে?", "driving licence status check korbo kivabe?", "payment আর submission শেষ—BRTA processing update কোথায় পাওয়া যাবে?"] ),
        leaf("DRIVING_LICENCE_APPLICATION_DELAY", "Driving Licence Application Delay", "A submitted licence application appears stuck longer than expected.", ["Licence pending too long", "Application delayed"], ["Normal status check", "Current processing-time promise"], ["ড্রাইভিং লাইসেন্স আবেদন দীর্ঘদিন pending থাকলে কী করব?", "অনেক সময় হয়ে গেছে, licence-এর update আসছে না।", "amar driving licence application atke ache.", "status বহুদিন একই জায়গায় আছে—follow-up কোথায় করব?"], priority="Medium", pilot_review=True),
        leaf("DRIVING_LICENCE_READY", "Driving Licence Ready for Collection", "Checking whether the physical/smart-card licence is ready.", ["Licence ready", "Card produced"], ["How to collect", "Application general status"], ["ড্রাইভিং লাইসেন্স সংগ্রহের জন্য প্রস্তুত হয়েছে কি না কীভাবে জানব?", "smart card ready হয়েছে কিনা কোথায় check করব?", "licence collect korar jonno ready kina janbo kivabe?", "application complete দেখাচ্ছে—physical card produced হয়েছে কি না জানতে চাই।"] ),
        leaf("DRIVING_LICENCE_COLLECTION_DELIVERY", "Driving Licence Collection or Delivery", "How or where to receive an issued physical/smart-card licence.", ["Collect licence card", "Licence delivery"], ["Whether card is ready", "Download learner permit"], ["প্রস্তুত ড্রাইভিং লাইসেন্স কীভাবে সংগ্রহ করব?", "smart card ready, এখন কোথা থেকে নেব?", "driving licence collection process ta ki?", "card issue হয়েছে—delivery বা pickup-এর next step জানতে চাই।"] ),
        leaf("DRIVING_LICENCE_VERIFICATION", "Driving Licence Verification", "Checking the validity or record of an existing driving licence through an official service.", ["Verify driving licence", "Check e-license record"], ["Application status", "Test result"], ["বিদ্যমান ড্রাইভিং লাইসেন্স কীভাবে অনলাইনে যাচাই করব?", "e-license record verify করার option কোথায়?", "driving licence verification korbo kivabe?", "লাইসেন্স নম্বর দিয়ে official record আছে কি না check করার service জানতে চাই।"], pilot_review=True),
    ]),
    parent("DRIVING_LICENCE_RENEWAL", "Driving Licence Renewal", "Renewal process, renewal documents and expiry-related renewal guidance.", ["Renewal process", "Documents", "Expired licence"], [
        leaf("DRIVING_LICENCE_RENEWAL_PROCESS", "Driving Licence Renewal Process", "General process for renewing an existing driving licence.", ["How to renew licence", "Renewal application"], ["Duplicate replacement", "New licence"], ["ড্রাইভিং লাইসেন্স নবায়নের প্রক্রিয়াটি কী?", "licence renew করতে চাই, কীভাবে apply করব?", "driving licence renewal process ta ki?", "বর্তমান licence-এর মেয়াদ বাড়াতে BSP-তে কোন service select করব?"] ),
        leaf("DRIVING_LICENCE_RENEWAL_DOCUMENTS", "Driving Licence Renewal Documents", "Supporting documents or information needed for renewal.", ["Renewal documents", "Old licence requirement"], ["New learner documents", "Renewal fee"], ["ড্রাইভিং লাইসেন্স নবায়নে কী কী কাগজপত্র লাগে?", "renewal application-এ old licence copy দিতে হবে?", "licence renew er required documents ki ki?", "মেয়াদ বাড়ানোর form জমা দেওয়ার আগে কোন supporting papers ready রাখব?"] ),
        leaf("DRIVING_LICENCE_EXPIRED_RENEWAL", "Expired Driving Licence Renewal", "Renewal guidance when the existing licence has already expired.", ["Renew expired licence", "Licence validity ended"], ["Licence expiring in future without special issue", "Lost licence duplicate"], ["মেয়াদ শেষ হওয়া ড্রাইভিং লাইসেন্স কীভাবে নবায়ন করব?", "licence already expired, এখন renewal কীভাবে হবে?", "expired driving licence renew korbo kivabe?", "অনেক আগে validity শেষ হয়েছে—existing licence-এর renewal route জানতে চাই।"], priority="Medium", pilot_review=True),
    ]),
    parent("DRIVING_LICENCE_REPLACEMENT", "Duplicate or Replacement Driving Licence", "Duplicate/replacement process for a lost, damaged or otherwise unavailable licence.", ["Duplicate", "Lost", "Damaged"], [
        leaf("DRIVING_LICENCE_DUPLICATE_PROCESS", "Duplicate Driving Licence Process", "General duplicate/replacement application without a more specific cause.", ["Apply for duplicate licence", "Replacement process"], ["Renewal", "Specific lost or damaged cause"], ["ডুপ্লিকেট ড্রাইভিং লাইসেন্সের আবেদন কীভাবে করব?", "replacement licence করতে কী process?", "duplicate driving licence application ta ki?", "existing licence-এর আরেকটি official copy নিতে কোন BRTA service ব্যবহার করব?"] ),
        leaf("DRIVING_LICENCE_LOST_REPLACEMENT", "Lost Driving Licence Replacement", "Obtaining a duplicate/replacement because the licence was lost.", ["Lost licence duplicate", "Missing licence replacement"], ["Damaged licence", "Lost learner-application reference"], ["ড্রাইভিং লাইসেন্স হারিয়ে গেলে replacement কীভাবে পাব?", "licence হারিয়ে গেছে, duplicate করতে চাই।", "lost driving licence reissue korbo kivabe?", "smart cardটা পথে হারিয়েছে—নতুন copy পাওয়ার application কোনটি?"], priority="Medium"),
        leaf("DRIVING_LICENCE_DAMAGED_REPLACEMENT", "Damaged Driving Licence Replacement", "Obtaining a duplicate/replacement because the licence is damaged or unusable.", ["Damaged licence duplicate", "Broken card replacement"], ["Lost licence", "Information correction"], ["নষ্ট ড্রাইভিং লাইসেন্সের replacement কীভাবে করব?", "licence card ভেঙে গেছে, duplicate লাগবে।", "damaged driving licence replace korbo kivabe?", "smart card-এর লেখা পড়া যাচ্ছে না—usable copy পাওয়ার process কী?"], priority="Medium"),
    ]),
    parent("DRIVING_LICENCE_CHANGES", "Driving Licence Information and Class Changes", "Corrections, address changes, vehicle-class additions/changes and licence-type changes.", ["Information correction", "Address", "Vehicle class", "Licence type"], [
        leaf("DRIVING_LICENCE_INFORMATION_CORRECTION", "Driving Licence Information Correction", "Correcting wrong personal information on an existing licence.", ["Correct licence name", "Fix personal data"], ["Address-only change", "Damaged card"], ["ড্রাইভিং লাইসেন্সে ভুল ব্যক্তিগত তথ্য কীভাবে সংশোধন করব?", "licence-এ নামের spelling ভুল, update করতে চাই।", "driving licence information correction er process ki?", "existing card-এ জন্মতারিখ ভুল দেখাচ্ছে—official correction service কোনটি?"], priority="Medium"),
        leaf("DRIVING_LICENCE_ADDRESS_CHANGE", "Driving Licence Address Change", "Changing the address recorded for an existing driving licence.", ["Change licence address", "Update present address"], ["General information correction", "Office selection"], ["ড্রাইভিং লাইসেন্সের ঠিকানা কীভাবে পরিবর্তন করব?", "বাসা বদলেছি, licence address update করতে চাই।", "driving licence address change korbo kivabe?", "existing smart card record-এ নতুন ঠিকানা যোগ করার application কোথায়?"] ),
        leaf("DRIVING_LICENCE_VEHICLE_CLASS_CHANGE", "Vehicle Class Addition or Change", "Adding or changing a motor-vehicle class on an existing licence.", ["Add vehicle class", "Change class"], ["Choose class for new application", "Professional type change"], ["বিদ্যমান লাইসেন্সে নতুন মোটরযান শ্রেণি কীভাবে যোগ করব?", "licence-এ motorcycle class add করতে চাই।", "driving licence vehicle class change korbo kivabe?", "আগের card-এ এক ধরনের vehicle আছে—আরেকটি category সংযোজনের process কী?"], pilot_review=True),
        leaf("DRIVING_LICENCE_TYPE_CHANGE", "Professional/Non-Professional Licence Type Change", "Changing the professional or non-professional type of an existing licence.", ["Change licence type", "Professional conversion"], ["New-application type selection", "Vehicle class addition"], ["বিদ্যমান ড্রাইভিং লাইসেন্সের ধরন কীভাবে পরিবর্তন করব?", "non-professional থেকে professional type change করতে চাই।", "licence type conversion process ta ki?", "existing licence-এর applicant category বদলানোর official application কোনটি?"], pilot_review=True, evidence_status="needs_source_review"),
    ]),
    parent("DRIVING_LICENCE_GENERAL", "General Driving Licence Information", "Broad service guidance that does not express a more specific licence workflow.", ["General service guidance", "Available licence services"], [
        leaf("DRIVING_LICENCE_GENERAL_GUIDANCE", "General Driving Licence Service Guidance", "Broad questions about available BRTA driving-licence services and where to begin.", ["What licence services exist", "General BRTA guidance"], ["Specific application question", "OOD fallback"], ["ড্রাইভিং লাইসেন্স সংক্রান্ত কী কী সেবা পাওয়া যায়?", "licence নিয়ে কোন কাজের জন্য কোন BRTA option ব্যবহার করব?", "driving licence services somporke general guidance chai.", "learner, renewal আর duplicate-এর মধ্যে আমার প্রয়োজনের service কীভাবে চিনব?"], pilot_review=True, evidence_status="needs_pilot_validation"),
        leaf("DRIVING_LICENCE_PORTAL_UNAVAILABLE", "BRTA Service Portal Unavailable", "The BSP website itself does not load or appears generally unavailable.", ["BSP portal down", "Website not opening"], ["Known account access issue", "Single payment failure"], ["বিআরটিএ সার্ভিস পোর্টাল না খুললে কী করব?", "BSP website load হচ্ছে না।", "BRTA portal down dekhacche.", "বিভিন্ন device দিয়ে চেষ্টা করেও service portal-এর কোনো page open হচ্ছে না।"], priority="Medium"),
    ]),
]


SPEC = {
    "service_id": "DRIVING_LICENCE", "service_name": "Driving Licence", "id_prefix": "DRIVING_LICENCE",
    "row_prefix": "DLQ", "taxonomy_filename": "driving_licence.yaml",
    "pilot_filename": "driving_licence_pilot_v0_1.csv", "review_filename": "driving_licence_pilot_v0_1_review.csv",
    "protocol_filename": "DRIVING_LICENCE_PILOT_PROTOCOL.md", "audit_filename": "DRIVING_LICENCE_PILOT_REVIEW_AUDIT.md",
    "source_inventory_filename": "DRIVING_LICENCE_SOURCE_INVENTORY.md", "semantic_audit_filename": "DRIVING_LICENCE_SEMANTIC_AUDIT.md",
    "description": "Working citizen-intent taxonomy for Bangladesh BRTA learner and driving licence services.",
    "design_rules": ["Classify the stable citizen need rather than current fees, ages, dates or office details.", "Keep learner, new licence, renewal, replacement and record-change lifecycles distinct.", "Separate test scheduling, requirements, results and retake needs.", "General guidance is never an OOD fallback."],
    "parents": PARENTS,
    "key_boundaries": ["learner application vs new full licence", "new-application vehicle class vs class addition on an existing licence", "test schedule vs test result vs licence status", "fee information vs payment method vs verification vs failure", "application status vs delay vs ready for collection", "renewal vs lost/damaged duplicate", "general information correction vs address/type/class change"],
    "source_inventory_markdown": """
# Driving Licence Service Source Inventory

Service: `DRIVING_LICENCE`

Status: official-domain inventory reviewed

## Official sources reviewed

- [Bangladesh Road Transport Authority](https://brta.gov.bd/) — lists the
  driving-licence application process, renewal, competency-test results and
  the BRTA Service Portal.
- [BRTA Service Portal](https://bsp.brta.gov.bd/?lan=en) — identifies learner
  licence, smart-card licence, renewal, duplicate, fee calculation, payment
  verification and driving-test result services.
- [BRTA driving-licence forms](https://brta.gov.bd/site/page/543c3d0c-5798-4f9c-a11e-809b9b475edf/-)
  — supports learner, medical, issue, renewal, duplicate, class/type/address
  change and information-correction workflows.

The taxonomy uses those stable capabilities only. Current eligibility ages,
fees, test dates, processing periods, office addresses and document rules are
not encoded as classifier facts.
""",
    "semantic_audit_markdown": """
# Driving Licence Semantic Taxonomy Audit

Service: `DRIVING_LICENCE`

Result: `PASS_WITH_PILOT_REVIEW_FLAGS`

The ten parents represent distinct licence lifecycle and access needs:
learner, new application, competency test, online account, payment,
status/delivery, renewal, replacement, record changes and general service
information.

## Critical boundaries

- Learner application precedes and differs from a full/smart-card licence.
- Professional/non-professional type differs from motor-vehicle class.
- Selecting a class for a new application differs from adding/changing a
  class on an existing licence.
- Test process, schedule, preparation, result and retake are separable goals.
- Account registration differs from submitting a licence application.
- Fee information, payment method, verification and failure are distinct.
- Application status, abnormal delay, readiness and collection/delivery are
  consecutive but independently requested stages.
- Renewal extends an existing licence; duplicate/replacement addresses an
  unavailable or unusable licence.
- General correction excludes explicit address, vehicle-class and type
  changes.

Pilot attention is required for eligibility/medical evidence, licence type,
test retake, portal OTP/access, application delay, verification, expired
renewal, class/type changes and broad guidance. No mutable rule or current
government answer is embedded. The shared contract remains unfrozen.
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
