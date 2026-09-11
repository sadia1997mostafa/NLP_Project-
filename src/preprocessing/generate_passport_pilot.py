from pathlib import Path
import csv
import re
import unicodedata

import yaml


TAXONOMY_PATH = Path("taxonomy/passport.yaml")
OUTPUT_PATH = Path("data/annotations/passport_pilot_v0_1.csv")

EXPECTED_SERVICE = "PASSPORT"
EXPECTED_VERSION = "0.2.0"
EXPECTED_LEAVES = 56
SEEDS_PER_LEAF = 4
EXPECTED_ROWS = EXPECTED_LEAVES * SEEDS_PER_LEAF

FIELDNAMES = [
    "id",
    "text",
    "service",
    "parent_topic_id",
    "parent_topic",
    "query_topic_id",
    "query_topic",
    "priority",
    "language_style",
    "privacy_present",
    "privacy_types",
    "source_type",
    "parent_query_id",
    "difficulty",
    "is_ood",
    "annotation_notes",
]

LANGUAGE_STYLES = [
    "Formal",
    "Informal",
    "Mixed",
    "Mixed",
]

DIFFICULTIES = [
    "Easy",
    "Medium",
    "Medium",
    "Hard",
]

MEDIUM_PRIORITY_TOPICS = {
    "PASSPORT_DOCUMENTS_MISSING",
    "PASSPORT_ONLINE_ACCOUNT_ACTIVATION_EMAIL_NOT_RECEIVED",
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM",
    "PASSPORT_APPOINTMENT_PROBLEM",
    "PASSPORT_REISSUE_WITH_INFORMATION_CHANGE",
    "PASSPORT_REISSUE_LOST",
    "PASSPORT_REISSUE_STOLEN",
    "PASSPORT_REISSUE_DAMAGED",
    "PASSPORT_PAYMENT_FAILURE",
    "PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED",
    "PASSPORT_PAYMENT_REFUND",
    "PASSPORT_APPLICATION_DELAY",
    "PASSPORT_DELIVERY_SLIP_LOST",
}

MANDATORY_REVIEW_TOPICS = {
    "PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC",
    "PASSPORT_DOCUMENTS_MISSING",
    "PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC",
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM",
    "PASSPORT_APPOINTMENT_PROBLEM",
    "PASSPORT_APPLICATION_DELAY",
    "PASSPORT_GENERAL_SERVICE_GUIDANCE",
}

BASE_NOTE = (
    "Passport pilot v0.1 synthetic independent seed; "
    "human semantic review required before training."
)

SEEDS = {

    # =========================================================
    # PASSPORT_APPLICATION — 7 leaves
    # =========================================================

    "PASSPORT_APPLICATION_PROCESS": [
        "নতুন ই-পাসপোর্টের জন্য আবেদন করার পুরো প্রক্রিয়াটি কী?",
        "প্রথমবার passport করতে চাই, শুরুটা কীভাবে করব?",
        "new e-passport apply korar process ta ki?",
        "আগে কখনো passport করিনি—কোন step থেকে application শুরু করব?",
    ],

    "PASSPORT_APPLICATION_ONLINE": [
        "অনলাইনে ই-পাসপোর্টের আবেদন কীভাবে জমা দেব?",
        "passport application online এ fill up করে submit করব কীভাবে?",
        "e-passport er online application kothay korte hoy?",
        "portal account আছে, এখন online passport applicationটা complete করব কীভাবে?",
    ],

    "PASSPORT_APPLICATION_OFFICE_SELECTION": [
        "ই-পাসপোর্টের আবেদন করার সময় কোন পাসপোর্ট অফিস নির্বাচন করব?",
        "আমার এলাকার জন্য কোন passport office select করতে হবে বুঝছি না।",
        "amar address onujayi kon passport office select korbo?",
        "application submit করার আগে responsible passport officeটা কীভাবে নির্ধারণ করব?",
    ],

    "PASSPORT_APPLICATION_INFORMATION": [
        "ই-পাসপোর্ট আবেদনপত্রে কী কী ব্যক্তিগত তথ্য দিতে হয়?",
        "passport form fill up করতে কোন কোন information লাগবে?",
        "e-passport application e ki ki info dite hoy?",
        "documents না, form-এর ভেতরে কোন details লিখতে হবে সেটা জানতে চাই।",
    ],

    "PASSPORT_APPLICATION_PASSPORT_OPTIONS": [
        "ই-পাসপোর্ট আবেদনে কী কী মেয়াদ ও পৃষ্ঠাসংখ্যার অপশন পাওয়া যায়?",
        "passport apply করার সময় validity আর page option কীভাবে choose করব?",
        "passport er validity o page option gulo ki?",
        "fee না, application-এর সময় কোন passport option select করা যায় সেটা জানতে চাই।",
    ],

    "PASSPORT_APPLICATION_OVERSEAS": [
        "বিদেশে অবস্থান করে নতুন বাংলাদেশি ই-পাসপোর্টের আবেদন কীভাবে করব?",
        "আমি abroad থাকি, first passport embassy দিয়ে করতে পারব?",
        "bidesh theke new Bangladesh passport apply korbo kivabe?",
        "আগে passport ছিল না; overseas থেকে new application কোন mission-এর মাধ্যমে করব?",
    ],

    "PASSPORT_APPLICATION_OFFICIAL_DIPLOMATIC": [
        "অফিশিয়াল বা ডিপ্লোম্যাটিক পাসপোর্টের জন্য আবেদন প্রক্রিয়া কী?",
        "government employee হিসেবে official passport apply করব কীভাবে?",
        "diplomatic passport application process ta ki?",
        "GO বা NOC-এর list না, official passport-এর application workflow জানতে চাই।",
    ],

    # =========================================================
    # PASSPORT_DOCUMENTS — 8 leaves
    # =========================================================

    "PASSPORT_DOCUMENTS_REQUIRED": [
        "ই-পাসপোর্ট আবেদনের জন্য সাধারণভাবে কী কী কাগজপত্র প্রয়োজন?",
        "passport করতে overall কোন documents লাগবে?",
        "passport application er required documents ki ki?",
        "NID নিয়ে আলাদা প্রশ্ন না—পুরো document checklistটা জানতে চাই।",
    ],

    "PASSPORT_DOCUMENTS_NID_REQUIREMENT": [
        "ই-পাসপোর্ট করতে জাতীয় পরিচয়পত্র প্রয়োজন কি?",
        "passport application-এর জন্য NID mandatory নাকি?",
        "passport korte NID lagbe ki?",
        "general documents না, specifically NID লাগবে কিনা জানতে চাই।",
    ],

    "PASSPORT_DOCUMENTS_BIRTH_REGISTRATION_REQUIREMENT": [
        "ই-পাসপোর্ট আবেদনে জন্মনিবন্ধন সনদ ব্যবহার করা যায় কি?",
        "passport করতে birth registration লাগবে?",
        "birth certificate diye passport apply kora jabe?",
        "NID না থাকলে passport-এর জন্য Birth Registration গ্রহণ করা হয় কি?",
    ],

    "PASSPORT_DOCUMENTS_PREVIOUS_PASSPORT": [
        "পাসপোর্ট পুনরায় ইস্যুর সময় আগের পাসপোর্টটি কি সঙ্গে দিতে হবে?",
        "reissue করতে old passport নিয়ে যেতে হবে?",
        "previous passport document hisebe lagbe ki?",
        "reissue process না, existing passportটা supporting document হিসেবে প্রয়োজন কিনা জানতে চাই।",
    ],

    "PASSPORT_DOCUMENTS_MINOR_APPLICANT": [
        "অপ্রাপ্তবয়স্ক শিশুর পাসপোর্টের জন্য কী কী কাগজপত্র লাগে?",
        "আমার বাচ্চার passport করতে কোন documents লাগবে?",
        "minor applicant er passport documents ki ki?",
        "adult applicant না—child passport-এর supporting papers জানতে চাই।",
    ],

    "PASSPORT_DOCUMENTS_ENROLMENT": [
        "ই-পাসপোর্ট এনরোলমেন্টের দিনে কোন কোন কাগজপত্র সঙ্গে নিতে হবে?",
        "biometric দিতে গেলে কী documents নিয়ে যাব?",
        "passport enrolment er din kon papers carry korte hoy?",
        "appointment preparation না, specifically enrolment day-এর document list চাই।",
    ],

    "PASSPORT_DOCUMENTS_MISSING": [
        "পাসপোর্ট আবেদনের প্রয়োজনীয় একটি কাগজ আমার কাছে নেই; কী করব?",
        "required passport document একটা missing, এখন application কীভাবে এগোব?",
        "passport er ekta dorkarer document nai, ki korbo?",
        "passport হারায়নি—supporting document unavailable হলে কী করতে হবে?",
    ],

    "PASSPORT_DOCUMENTS_OFFICIAL_DIPLOMATIC": [
        "অফিশিয়াল বা ডিপ্লোম্যাটিক পাসপোর্টের জন্য কী কী সহায়ক কাগজপত্র লাগে?",
        "official passport-এর জন্য GO বা NOC লাগবে কিনা জানতে চাই।",
        "diplomatic passport er supporting documents ki?",
        "application process না—official passport-এর required administrative papers জানতে চাই।",
    ],

    # =========================================================
    # PASSPORT_ONLINE_ACCOUNT — 8 leaves
    # =========================================================

    "PASSPORT_ONLINE_ACCOUNT_REGISTRATION": [
        "ই-পাসপোর্ট অনলাইন সেবার জন্য নতুন অ্যাকাউন্ট কীভাবে তৈরি করব?",
        "passport portal-এ account খুলতে চাই, কী করতে হবে?",
        "e-passport account register korbo kivabe?",
        "application submit না—আগে portal account create করতে চাই।",
    ],

    "PASSPORT_ONLINE_ACCOUNT_LOGIN": [
        "আমার বিদ্যমান ই-পাসপোর্ট অ্যাকাউন্টে কীভাবে লগইন করব?",
        "passport portal login কোথা থেকে করব?",
        "e-passport account e sign in korbo kivabe?",
        "password ভুলিনি; শুধু existing account-এ login করার নিয়ম জানতে চাই।",
    ],

    "PASSPORT_ONLINE_ACCOUNT_PASSWORD_RESET": [
        "ই-পাসপোর্ট অ্যাকাউন্টের পাসওয়ার্ড ভুলে গেলে কীভাবে রিসেট করব?",
        "passport portal-এর password মনে নেই, recover করব কীভাবে?",
        "e-passport password reset korar niyom ki?",
        "account আছে কিন্তু password ভুলে গেছি—access ফেরত পেতে কী করব?",
    ],

    "PASSPORT_ONLINE_ACCOUNT_ACTIVATION": [
        "নতুন ই-পাসপোর্ট অ্যাকাউন্ট কীভাবে সক্রিয় করব?",
        "passport account create করেছি, activate করব কীভাবে?",
        "e-passport account activation process ta ki?",
        "activation email পেয়েছি; এখন account activate করার next step কী?",
    ],

    "PASSPORT_ONLINE_ACCOUNT_ACTIVATION_EMAIL_NOT_RECEIVED": [
        "ই-পাসপোর্ট অ্যাকাউন্ট খোলার পর activation email পাইনি; কী করব?",
        "passport portal-এ register করেছি কিন্তু verification mail আসেনি।",
        "account khulsi but activation email paini, ki korbo?",
        "password reset না—new account-এর activation link-টাই email-এ আসছে না।",
    ],

    "PASSPORT_ONLINE_ACCOUNT_EMAIL_CHANGE": [
        "ই-পাসপোর্ট অ্যাকাউন্টে নিবন্ধিত ইমেইল ঠিকানা কীভাবে পরিবর্তন করব?",
        "passport account-এর old email change করতে চাই।",
        "registered email update korbo kivabe passport portal e?",
        "activation mail issue না—account-এর linked emailটাই replace করতে চাই।",
    ],

    "PASSPORT_ONLINE_ACCOUNT_MOBILE_CHANGE": [
        "ই-পাসপোর্ট অ্যাকাউন্টে নিবন্ধিত মোবাইল নম্বর কীভাবে পরিবর্তন করব?",
        "passport portal-এ পুরোনো phone number বদলাতে চাই।",
        "passport account er registered mobile change korbo kivabe?",
        "application form-এর number না—account-এর linked mobile update করতে চাই।",
    ],

    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM": [
        "আমার বিদ্যমান ই-পাসপোর্ট অ্যাকাউন্টে প্রবেশ করতে পারছি না; কী করব?",
        "passport account আছে কিন্তু portal-এ ঢুকতে পারছি না।",
        "existing e-passport account access hocche na, ki korbo?",
        "password ভুলে যাইনি বা activation issue নেই—তবুও account open হচ্ছে না।",
    ],

    # =========================================================
    # PASSPORT_APPOINTMENT_AND_ENROLMENT — 7 leaves
    # =========================================================

    "PASSPORT_APPOINTMENT_SCHEDULING": [
        "ই-পাসপোর্ট এনরোলমেন্টের জন্য অ্যাপয়েন্টমেন্ট কীভাবে নির্ধারণ করব?",
        "passport appointment book করব কীভাবে?",
        "e-passport appointment schedule korbo kivabe?",
        "date already assigned না—নতুন appointment obtain করার নিয়ম জানতে চাই।",
    ],

    "PASSPORT_APPOINTMENT_DATE": [
        "আমার ই-পাসপোর্ট অ্যাপয়েন্টমেন্টের তারিখ কীভাবে দেখব?",
        "passport appointment কবে সেটা কোথায় check করব?",
        "amar passport appointment date kothay dekhbo?",
        "নতুন appointment book করতে চাই না—already scheduled dateটা জানতে চাই।",
    ],

    "PASSPORT_APPOINTMENT_PROBLEM": [
        "ই-পাসপোর্ট অ্যাপয়েন্টমেন্ট ধাপে সমস্যা হচ্ছে; কী করব?",
        "আমার passport appointment ঠিকমতো কাজ করছে না।",
        "passport appointment niye problem hocche, ki korbo?",
        "login ঠিক আছে এবং date-ও জানি, কিন্তু appointment step complete হচ্ছে না।",
    ],

    "PASSPORT_APPOINTMENT_REQUIREMENTS": [
        "পাসপোর্ট অ্যাপয়েন্টমেন্টে যাওয়ার আগে কী কী প্রস্তুতি নিতে হবে?",
        "passport appointment attend করার আগে কী করতে হবে?",
        "appointment e jawar age ki preparation lagbe?",
        "documents list না—appointment attend করার general requirements জানতে চাই।",
    ],

    "PASSPORT_ENROLMENT_PROCESS": [
        "ই-পাসপোর্টের শারীরিক এনরোলমেন্ট প্রক্রিয়ায় কী কী হয়?",
        "passport office-এ enrolment করতে গেলে কী process হয়?",
        "e-passport enrolment process ta kivabe hoy?",
        "biometric-এর specific details না—পুরো physical enrolment stageটা জানতে চাই।",
    ],

    "PASSPORT_ENROLMENT_LOCATION": [
        "ই-পাসপোর্টের শারীরিক এনরোলমেন্ট কোথায় সম্পন্ন করতে হবে?",
        "passport biometric দিতে কোন জায়গায় যেতে হবে?",
        "passport enrolment location kothay hobe?",
        "application-এর office select না—এখন physical enrolment-এর জন্য কোথায় যাব জানতে চাই।",
    ],

    "PASSPORT_ENROLMENT_BIOMETRICS": [
        "ই-পাসপোর্ট বায়োমেট্রিক এনরোলমেন্টে কী কী তথ্য নেওয়া হয়?",
        "passport biometric দিতে গেলে আসলে কী হয়?",
        "e-passport biometric capture e ki ki ney?",
        "general enrolment না—specifically biometric stage সম্পর্কে জানতে চাই।",
    ],

    # =========================================================
    # PASSPORT_REISSUE — 8 leaves
    # =========================================================

    "PASSPORT_REISSUE_PROCESS": [
        "আগে পাসপোর্ট ছিল; এখন সাধারণভাবে পুনরায় ইস্যু করতে কী করতে হবে?",
        "passport reissue করতে চাই, processটা কী?",
        "passport reissue korar niyom ki?",
        "হারায়নি, নষ্ট হয়নি, expiry বা info change বলছি না—general reissue process জানতে চাই।",
    ],

    "PASSPORT_REISSUE_EXPIRY": [
        "আমার পাসপোর্টের মেয়াদ শেষ হয়ে গেছে; পুনরায় ইস্যু কীভাবে করব?",
        "passport expire হতে যাচ্ছে, renew/reissue করতে কী হবে?",
        "expired passport reissue korbo kivabe?",
        "passport হারায়নি—শুধু মেয়াদ শেষ হওয়ায় নতুনটা নিতে চাই।",
    ],

    "PASSPORT_REISSUE_WITH_INFORMATION_CHANGE": [
        "তথ্য পরিবর্তনসহ পাসপোর্ট পুনরায় ইস্যু করতে কী করতে হবে?",
        "passport reissue-এর সময় personal information change করতে চাই।",
        "information change kore passport reissue korbo kivabe?",
        "same information না—reissue-এর সঙ্গে passport details update করতে চাই।",
    ],

    "PASSPORT_REISSUE_LOST": [
        "আমার পাসপোর্ট হারিয়ে গেছে; পুনরায় ইস্যু বা replacement কীভাবে পাব?",
        "passport খুঁজে পাচ্ছি না, নতুনটা করতে কী হবে?",
        "passport hariye geche, reissue korbo kivabe?",
        "delivery slip না—passportটিই missing, replacement দরকার।",
    ],

    "PASSPORT_REISSUE_STOLEN": [
        "আমার পাসপোর্ট চুরি হয়েছে; replacement পেতে কী করতে হবে?",
        "passport stolen হয়েছে, এখন reissue করব কীভাবে?",
        "passport churi hoye geche, notun ta kivabe pabo?",
        "হারিয়ে ফেলিনি—passportটা stolen হয়েছে এবং replacement চাই।",
    ],

    "PASSPORT_REISSUE_DAMAGED": [
        "আমার পাসপোর্ট নষ্ট হয়ে গেছে; পুনরায় ইস্যু কীভাবে করব?",
        "passport ছিঁড়ে গেছে, replacement পেতে কী করতে হবে?",
        "damaged passport reissue korbo kivabe?",
        "passport আছে কিন্তু usable না—damage-এর কারণে নতুনটা দরকার।",
    ],

    "PASSPORT_REISSUE_WITHOUT_INFORMATION_CHANGE": [
        "কোনো তথ্য পরিবর্তন না করে পাসপোর্ট পুনরায় ইস্যু কীভাবে করব?",
        "সব details same থাকবে, শুধু passport reissue করতে চাই।",
        "same information diye passport reissue korbo kivabe?",
        "personal info change করব না—existing details রেখেই reissue চাই।",
    ],

    "PASSPORT_REISSUE_OVERSEAS": [
        "বিদেশে অবস্থান করে আমার বর্তমান বাংলাদেশি পাসপোর্ট পুনরায় ইস্যু কীভাবে করব?",
        "abroad থেকে existing passport renew/reissue করতে চাই।",
        "bidesh theke Bangladesh passport reissue korbo kivabe?",
        "first passport না—আগের passport আছে, overseas থেকে reissue দরকার।",
    ],

    # =========================================================
    # PASSPORT_FEES_AND_PAYMENT — 8 leaves
    # =========================================================

    "PASSPORT_FEES_INFORMATION": [
        "বাংলাদেশ ই-পাসপোর্টের সাধারণ ফি কত?",
        "passport করতে মোট fee কত লাগে?",
        "e-passport er fee koto?",
        "payment method না—passport service-এর charge কত সেটা জানতে চাই।",
    ],

    "PASSPORT_PAYMENT_METHOD": [
        "ই-পাসপোর্টের ফি কীভাবে পরিশোধ করা যায়?",
        "passport fee pay করার কী কী method আছে?",
        "passport payment korbo kivabe?",
        "fee amount জানি; এখন online বা offline কীভাবে payment করব জানতে চাই।",
    ],

    "PASSPORT_PAYMENT_CONFIRMATION": [
        "আমার ই-পাসপোর্ট ফি সফলভাবে জমা হয়েছে কি না কীভাবে যাচাই করব?",
        "passport payment successful হয়েছে কিনা check করব কীভাবে?",
        "passport payment confirm hoise kina kivabe janbo?",
        "failed বলছে না—payment system-এ record হয়েছে কিনা নিশ্চিত হতে চাই।",
    ],

    "PASSPORT_PAYMENT_FAILURE": [
        "আমার ই-পাসপোর্ট ফি পরিশোধের চেষ্টা ব্যর্থ হয়েছে; কী করব?",
        "passport payment বারবার fail করছে।",
        "passport fee payment fail hocche, ki korbo?",
        "টাকা কাটা যায়নি—শুধু transaction unsuccessful দেখাচ্ছে।",
    ],

    "PASSPORT_PAYMENT_DEDUCTED_BUT_FAILED": [
        "টাকা কেটে নেওয়া হয়েছে, কিন্তু ই-পাসপোর্ট payment failed দেখাচ্ছে; কী করব?",
        "passport fee account থেকে কেটেছে কিন্তু payment successful হয়নি।",
        "taka kete niyeche but passport payment failed dekhacche.",
        "ordinary failure না—money deducted হয়েছে অথচ transaction record হয়নি।",
    ],

    "PASSPORT_PAYMENT_REFUND": [
        "ব্যর্থ পাসপোর্ট payment-এর টাকা ফেরত পাওয়ার প্রক্রিয়া কী?",
        "passport payment fail হওয়ার পর refund কীভাবে পাব?",
        "failed passport payment er taka refund pabo kivabe?",
        "deduction problem already হয়েছে—এখন আমার main question টাকা ফেরত পাওয়ার ব্যাপারে।",
    ],

    "PASSPORT_PAYMENT_RECEIPT": [
        "ই-পাসপোর্ট ফি পরিশোধের রসিদ কোথা থেকে পাব?",
        "passport payment receipt print করতে চাই।",
        "passport fee payment slip kothay pabo?",
        "payment successful কিনা check না—proof of payment বা receipt দরকার।",
    ],

    "PASSPORT_FEES_DELIVERY_CATEGORY": [
        "রেগুলার ও এক্সপ্রেস পাসপোর্ট সেবার ফি কত?",
        "express passport-এর fee কত হয়?",
        "regular ar express passport fee koto?",
        "delivery speed-এর difference না—specifically service category অনুযায়ী price জানতে চাই।",
    ],

    # =========================================================
    # PASSPORT_STATUS_AND_DELIVERY — 7 leaves
    # =========================================================

    "PASSPORT_APPLICATION_STATUS": [
        "আমার ই-পাসপোর্ট আবেদনের বর্তমান অবস্থা কীভাবে যাচাই করব?",
        "passport application এখন কোন stage-এ আছে দেখব কীভাবে?",
        "passport application er status check korbo kivabe?",
        "delay complaint না—শুধু current application stage বা approval state জানতে চাই।",
    ],

    "PASSPORT_APPLICATION_DELAY": [
        "আমার ই-পাসপোর্ট আবেদন অস্বাভাবিকভাবে দেরি হচ্ছে; কী করব?",
        "passport application অনেকদিন ধরে same stage-এ stuck।",
        "amar passport onekdin dhore pending, ki korbo?",
        "status শুধু জানতে চাই না—application expected সময়ের চেয়ে অনেক বেশি delay হচ্ছে।",
    ],

    "PASSPORT_PROCESSING_TIME": [
        "সাধারণভাবে ই-পাসপোর্ট প্রক্রিয়াকরণে কত সময় লাগে?",
        "passport হতে normally কতদিন লাগে?",
        "passport processing time normally koto?",
        "আমার specific case delayed না—usual processing duration জানতে চাই।",
    ],

    "PASSPORT_DELIVERY_CATEGORY": [
        "রেগুলার, এক্সপ্রেস ও অন্যান্য পাসপোর্ট processing category-এর পার্থক্য কী?",
        "passport-এর regular আর express service কীভাবে আলাদা?",
        "passport delivery category gulo ki ki?",
        "fee না—different processing or delivery option-এর service difference জানতে চাই।",
    ],

    "PASSPORT_READY_FOR_COLLECTION": [
        "আমার পাসপোর্ট সংগ্রহের জন্য প্রস্তুত হয়েছে কি না কীভাবে জানব?",
        "passport ready for collection হয়েছে কিনা কোথায় check করব?",
        "amar passport collect korar jonno ready hoise kina kivabe janbo?",
        "general status না—এখন passport pickup করার মতো ready হয়েছে কিনা জানতে চাই।",
    ],

    "PASSPORT_COLLECTION": [
        "প্রস্তুত হওয়া পাসপোর্ট কীভাবে সংগ্রহ করব?",
        "passport ready হয়েছে, এখন কোথা থেকে collect করব?",
        "ready passport collect korar process ki?",
        "ready কিনা সেটা জানি—এখন physical collection procedure জানতে চাই।",
    ],

    "PASSPORT_DELIVERY_SLIP_LOST": [
        "পাসপোর্ট সংগ্রহের delivery slip হারিয়ে ফেলেছি; কী করব?",
        "passport ready কিন্তু collection slip খুঁজে পাচ্ছি না।",
        "passport delivery slip hariye geche, collect korbo kivabe?",
        "passportটা হারায়নি এবং payment receipt-ও না—collection slipটাই missing।",
    ],

    # =========================================================
    # PASSPORT_GENERAL_INFORMATION — 3 leaves
    # =========================================================

    "PASSPORT_GENERAL_EPASSPORT_INFORMATION": [
        "ই-পাসপোর্ট কী এবং এটি সাধারণ পাসপোর্ট থেকে কীভাবে আলাদা?",
        "e-passport আসলে কী জিনিস?",
        "Bangladesh e-passport somporke general information chai.",
        "apply করার process না—শুধু e-Passport সম্পর্কে basic ধারণা জানতে চাই।",
    ],

    "PASSPORT_GENERAL_NEW_VS_REISSUE": [
        "আমার ক্ষেত্রে নতুন পাসপোর্ট আবেদন করব নাকি re-issue করব কীভাবে বুঝব?",
        "আগে passport ছিল, এখন new নাকি reissue select করব?",
        "new passport ar reissue er moddhe konta amar jonno?",
        "specific reissue reason বলছি না—আগে passport থাকলে কোন workflow choose করতে হয় জানতে চাই।",
    ],

    "PASSPORT_GENERAL_SERVICE_GUIDANCE": [
        "পাসপোর্ট সংক্রান্ত কী কী ধরনের সেবা ও সহায়তা পাওয়া যায়?",
        "passport নিয়ে কোন কোন বিষয়ে help পাওয়া যায়?",
        "passport service gulo ki ki, kothay theke start korbo?",
        "specific application বা payment problem না—কোন passport service আমার প্রয়োজন বুঝতে guidance চাই।",
    ],
}


def normalize_text(text):
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_taxonomy():
    if not TAXONOMY_PATH.exists():
        raise FileNotFoundError(
            f"Taxonomy file not found: {TAXONOMY_PATH}"
        )

    with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
        taxonomy = yaml.safe_load(file)

    if taxonomy.get("service_id") != EXPECTED_SERVICE:
        raise ValueError(
            f"Expected service_id {EXPECTED_SERVICE}, "
            f"found {taxonomy.get('service_id')}"
        )

    if taxonomy.get("taxonomy_version") != EXPECTED_VERSION:
        raise ValueError(
            f"Expected taxonomy version {EXPECTED_VERSION}, "
            f"found {taxonomy.get('taxonomy_version')}"
        )

    if not taxonomy.get("freeze_status", {}).get(
        "semantic_audit_passed", False
    ):
        raise ValueError(
            "Passport semantic audit must be passed before pilot generation."
        )

    return taxonomy


def build_leaf_index(taxonomy):
    leaf_index = {}

    for parent_id, parent_data in taxonomy["parent_topics"].items():
        parent_name = parent_data["display_name"]

        for query_topic_id, query_topic_data in parent_data[
            "query_topics"
        ].items():
            if query_topic_id in leaf_index:
                raise ValueError(
                    f"Duplicate query topic ID in taxonomy: {query_topic_id}"
                )

            leaf_index[query_topic_id] = {
                "parent_topic_id": parent_id,
                "parent_topic": parent_name,
                "query_topic": query_topic_data["display_name"],
            }

    return leaf_index


def validate_seed_inventory(leaf_index):
    taxonomy_topics = set(leaf_index.keys())
    seed_topics = set(SEEDS.keys())

    missing = taxonomy_topics - seed_topics
    extra = seed_topics - taxonomy_topics

    if missing:
        raise ValueError(
            "Missing seed definitions for: "
            + ", ".join(sorted(missing))
        )

    if extra:
        raise ValueError(
            "Seed definitions exist for unknown taxonomy topics: "
            + ", ".join(sorted(extra))
        )

    if len(leaf_index) != EXPECTED_LEAVES:
        raise ValueError(
            f"Expected {EXPECTED_LEAVES} taxonomy leaves, "
            f"found {len(leaf_index)}"
        )

    for topic_id, queries in SEEDS.items():
        if len(queries) != SEEDS_PER_LEAF:
            raise ValueError(
                f"{topic_id} must contain exactly "
                f"{SEEDS_PER_LEAF} seeds; found {len(queries)}"
            )

        if any(not isinstance(query, str) or not query.strip()
               for query in queries):
            raise ValueError(
                f"{topic_id} contains an empty or invalid query."
            )


def validate_text_uniqueness():
    all_texts = []

    for topic_id, queries in SEEDS.items():
        for query in queries:
            all_texts.append((topic_id, query))

    exact_texts = [query for _, query in all_texts]

    if len(exact_texts) != len(set(exact_texts)):
        raise ValueError("Exact duplicate query text found in seed inventory.")

    normalized_seen = {}

    for topic_id, query in all_texts:
        normalized = normalize_text(query)

        if normalized in normalized_seen:
            previous_topic, previous_query = normalized_seen[normalized]

            raise ValueError(
                "Normalized duplicate query found:\n"
                f"  First: {previous_topic}: {previous_query}\n"
                f"  Second: {topic_id}: {query}"
            )

        normalized_seen[normalized] = (topic_id, query)


def priority_for(query_topic_id):
    if query_topic_id in MEDIUM_PRIORITY_TOPICS:
        return "Medium"

    return "Low"


def note_for(query_topic_id):
    note = BASE_NOTE

    if query_topic_id in MANDATORY_REVIEW_TOPICS:
        note += " Mandatory pilot-review leaf."

    return note


def generate_rows(taxonomy, leaf_index):
    rows = []
    row_number = 1

    # Preserve taxonomy order rather than alphabetical order.
    for parent_id, parent_data in taxonomy["parent_topics"].items():
        for query_topic_id in parent_data["query_topics"].keys():

            metadata = leaf_index[query_topic_id]
            queries = SEEDS[query_topic_id]

            for family_number, query in enumerate(queries, start=1):

                row_id = f"PASSQ_{row_number:04d}"
                parent_query_id = (
                    f"{query_topic_id}_F{family_number:02d}"
                )

                row = {
                    "id": row_id,
                    "text": query,
                    "service": EXPECTED_SERVICE,
                    "parent_topic_id": metadata["parent_topic_id"],
                    "parent_topic": metadata["parent_topic"],
                    "query_topic_id": query_topic_id,
                    "query_topic": metadata["query_topic"],
                    "priority": priority_for(query_topic_id),
                    "language_style": LANGUAGE_STYLES[
                        family_number - 1
                    ],
                    "privacy_present": "FALSE",
                    "privacy_types": "",
                    "source_type": "SYNTHETIC",
                    "parent_query_id": parent_query_id,
                    "difficulty": DIFFICULTIES[
                        family_number - 1
                    ],
                    "is_ood": "FALSE",
                    "annotation_notes": note_for(query_topic_id),
                }

                rows.append(row)
                row_number += 1

    return rows


def validate_generated_rows(rows, leaf_index):
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} rows, found {len(rows)}"
        )

    row_ids = [row["id"] for row in rows]
    family_ids = [row["parent_query_id"] for row in rows]
    texts = [row["text"] for row in rows]
    normalized_texts = [normalize_text(text) for text in texts]

    if len(row_ids) != len(set(row_ids)):
        raise ValueError("Duplicate row IDs found.")

    if len(family_ids) != len(set(family_ids)):
        raise ValueError(
            "Pilot requires one independent seed per family, "
            "but duplicate parent_query_id values were found."
        )

    if len(texts) != len(set(texts)):
        raise ValueError("Duplicate text found.")

    if len(normalized_texts) != len(set(normalized_texts)):
        raise ValueError("Normalized duplicate text found.")

    topic_counts = {}

    for row in rows:
        topic_id = row["query_topic_id"]

        topic_counts[topic_id] = topic_counts.get(topic_id, 0) + 1

        if row["service"] != EXPECTED_SERVICE:
            raise ValueError(
                f"{row['id']} has invalid service."
            )

        if topic_id not in leaf_index:
            raise ValueError(
                f"{row['id']} has unknown query topic {topic_id}."
            )

        expected_parent = leaf_index[topic_id]["parent_topic_id"]

        if row["parent_topic_id"] != expected_parent:
            raise ValueError(
                f"{row['id']} has incorrect parent for {topic_id}."
            )

        if row["source_type"] != "SYNTHETIC":
            raise ValueError(
                f"{row['id']} must be SYNTHETIC."
            )

        if row["privacy_present"] != "FALSE":
            raise ValueError(
                f"{row['id']} must have privacy_present FALSE."
            )

        if row["privacy_types"] != "":
            raise ValueError(
                f"{row['id']} must have empty privacy_types."
            )

        if row["is_ood"] != "FALSE":
            raise ValueError(
                f"{row['id']} must have is_ood FALSE."
            )

        if row["priority"] not in {"Low", "Medium", "High"}:
            raise ValueError(
                f"{row['id']} has invalid priority."
            )

        if row["language_style"] not in {
            "Formal",
            "Informal",
            "Mixed",
        }:
            raise ValueError(
                f"{row['id']} has invalid language_style."
            )

        if row["difficulty"] not in {
            "Easy",
            "Medium",
            "Hard",
        }:
            raise ValueError(
                f"{row['id']} has invalid difficulty."
            )

    for topic_id in leaf_index:
        count = topic_counts.get(topic_id, 0)

        if count != SEEDS_PER_LEAF:
            raise ValueError(
                f"{topic_id} must have {SEEDS_PER_LEAF} rows; "
                f"found {count}."
            )


def write_csv(rows):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows, taxonomy):
    print("=" * 72)
    print("PASSPORT PILOT DATASET GENERATION")
    print("=" * 72)
    print(f"Taxonomy: {TAXONOMY_PATH}")
    print(f"Taxonomy version: {taxonomy['taxonomy_version']}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Rows: {len(rows)}")
    print(f"Parents: {len(taxonomy['parent_topics'])}")
    print(f"Query topics: {len(SEEDS)}")
    print(f"Families: {len({row['parent_query_id'] for row in rows})}")
    print()

    print("Rows by parent:")

    parent_counts = {}

    for row in rows:
        parent_id = row["parent_topic_id"]
        parent_counts[parent_id] = parent_counts.get(parent_id, 0) + 1

    for parent_id in taxonomy["parent_topics"].keys():
        print(
            f"  {parent_id}: "
            f"{parent_counts.get(parent_id, 0)}"
        )

    print()

    priority_counts = {}

    for row in rows:
        priority = row["priority"]
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    print("Priority counts:")

    for priority in ["Low", "Medium", "High"]:
        print(
            f"  {priority}: "
            f"{priority_counts.get(priority, 0)}"
        )

    print()
    print("RESULT: PASS")
    print(
        "224 independent synthetic Passport pilot seeds generated."
    )
    print(
        "DO NOT TRAIN: human semantic review is required first."
    )


def main():
    taxonomy = load_taxonomy()

    leaf_index = build_leaf_index(taxonomy)

    validate_seed_inventory(leaf_index)
    validate_text_uniqueness()

    rows = generate_rows(
        taxonomy=taxonomy,
        leaf_index=leaf_index,
    )

    validate_generated_rows(
        rows=rows,
        leaf_index=leaf_index,
    )

    write_csv(rows)

    print_summary(
        rows=rows,
        taxonomy=taxonomy,
    )


if __name__ == "__main__":
    main()