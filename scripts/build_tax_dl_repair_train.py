"""Build a targeted TAX + Driving Licence NLU repair training set.

This script:
- starts from the frozen original TRAIN split;
- adds only manually controlled hard-confusion examples;
- never modifies DEV or TEST;
- performs duplicate/leakage/schema checks;
- writes a separate derived training CSV.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

TRAIN = ROOT / "data" / "splits" / "train.csv"
DEV = ROOT / "data" / "splits" / "dev.csv"
TEST = ROOT / "data" / "splits" / "test.csv"

OUTPUT = ROOT / "data" / "splits" / "train_tax_dl_repair.csv"
REPORT = ROOT / "data" / "evaluation" / "tax_dl_repair_report.json"

EXPECTED_REPAIR_ROWS = 196

STYLE_CYCLE = [
    "Formal",
    "Informal",
    "Mixed",
    "Informal",
]


# ---------------------------------------------------------------------
# Manually controlled repair examples.
#
# Four examples per target intent.
# These deliberately emphasize the semantic discriminator between
# sibling intents rather than generic paraphrasing.
# ---------------------------------------------------------------------

REPAIR = {
    # ================================================================
    # TAX — ACCOUNT
    # ================================================================
    "TAX_ACCOUNT_ACCESS_PROBLEM": [
        "সঠিক তথ্য দেওয়ার পরও আমার ই-রিটার্ন অ্যাকাউন্টে ঢুকতে পারছি না।",
        "login details ঠিক আছে, তবুও tax account access হচ্ছে না কেন?",
        "আমার e-Return account খুলছে না, credentials ঠিক থাকার পরও access পাচ্ছি না।",
        "ই-রিটার্ন অ্যাকাউন্ট আছে কিন্তু ভেতরে প্রবেশ করতে পারছি না, কী করব?",
    ],
    "TAX_ACCOUNT_LOGIN": [
        "ই-রিটার্ন অ্যাকাউন্টে ঢোকার জন্য login কোথা থেকে করব?",
        "আমার existing tax account-এ sign in করার নিয়ম কী?",
        "e-Return account already আছে, এখন login করব কীভাবে?",
        "tax portal-এ আমার account login করার জায়গাটা কোথায়?",
    ],
    "TAX_ACCOUNT_MOBILE_UPDATE": [
        "ই-রিটার্ন অ্যাকাউন্টের মোবাইল নম্বর পরিবর্তন করতে চাই।",
        "tax account-এ দেওয়া পুরোনো mobile number কীভাবে update করব?",
        "আমার e-Return profile-এর phone number বদলাতে হবে, কীভাবে করব?",
        "account ঠিক আছে, শুধু registered mobile number change করতে চাই।",
    ],
    "TAX_ACCOUNT_OTP_PROBLEM": [
        "ই-রিটার্ন অ্যাকাউন্টের OTP আমার মোবাইলে আসছে না।",
        "tax portal OTP পাঠাচ্ছে না, কীভাবে সমস্যাটা সমাধান করব?",
        "OTP পেয়েছি কিন্তু code দিলে e-Return portal accept করছে না।",
        "tax account verification-এর OTP বারবার invalid দেখাচ্ছে।",
    ],
    "TAX_ACCOUNT_PASSWORD_RESET": [
        "ই-রিটার্ন অ্যাকাউন্টের password ভুলে গেছি, reset করব কীভাবে?",
        "tax portal-এর password মনে নেই, নতুন password সেট করতে চাই।",
        "আমার e-Return login password recover করার নিয়ম কী?",
        "password ভুলে যাওয়ার কারণে tax account-এ ঢুকতে পারছি না, reset করতে চাই।",
    ],
    "TAX_ACCOUNT_REGISTRATION": [
        "ই-রিটার্ন ব্যবহারের জন্য নতুন account তৈরি করতে চাই।",
        "আমার e-Return account এখনো নেই, registration কীভাবে করব?",
        "tax portal-এ প্রথমবার নতুন user হিসেবে account খুলব কীভাবে?",
        "আমি নতুন e-Return account register করতে চাই, প্রক্রিয়াটা কী?",
    ],

    # ================================================================
    # TAX — CERTIFICATE
    # ================================================================
    "TAX_CERTIFICATE_ACCESS": [
        "আমার tax certificate অনলাইনে কোথা থেকে দেখা যাবে?",
        "TIN certificate ছাড়া অন্য tax certificate access করতে চাই, কোথায় পাব?",
        "আমার tax-related certificate portal থেকে কীভাবে খুলব?",
        "tax certificate দেখতে চাই, কোন section থেকে access করা যায়?",
    ],

    # ================================================================
    # TAX — PAYMENT
    # ================================================================
    "TAX_PAYMENT_AMOUNT_CALCULATION": [
        "আমার কত টাকা আয়কর দিতে হবে সেটা কীভাবে হিসাব করব?",
        "payable tax amount কত হবে তা নির্ণয়ের উপায় কী?",
        "আমার income অনুযায়ী tax amount কীভাবে calculate হবে?",
        "কত টাকা tax payable হয়েছে সেটা কীভাবে বের করব?",
    ],
    "TAX_PAYMENT_METHOD": [
        "কোন কোন মাধ্যমে আয়কর পরিশোধ করা যায়?",
        "tax payment করার available payment methods কী কী?",
        "আমি কীভাবে tax fee পরিশোধ করতে পারি, কোন মাধ্যম ব্যবহার করা যায়?",
        "আয়কর দেওয়ার জন্য bank, online বা mobile payment-এর কোন option আছে?",
    ],
    "TAX_PAYMENT_CONFIRMATION": [
        "আমি tax payment করেছি, successful হয়েছে কি না কীভাবে নিশ্চিত হব?",
        "payment complete করার পর transaction successful কিনা কোথায় দেখব?",
        "আমার আয়কর payment confirm হয়েছে কি না check করতে চাই।",
        "tax payment successful হওয়ার confirmation কীভাবে পাব?",
    ],
    "TAX_PAYMENT_FAILURE": [
        "tax payment করতে গেলে transaction fail করছে, কী করব?",
        "আয়কর দিতে গিয়ে payment unsuccessful দেখাচ্ছে।",
        "বারবার tax payment attempt fail হচ্ছে, কীভাবে সমাধান করব?",
        "payment submit করছি কিন্তু transaction complete হচ্ছে না।",
    ],
    "TAX_PAYMENT_LEDGER_UPDATE": [
        "tax payment successful হয়েছে কিন্তু ledger-এ দেখাচ্ছে না।",
        "আমি কর পরিশোধ করেছি, কিন্তু e-Return ledger এখনো update হয়নি।",
        "paid tax amount ledger-এ reflect করছে না, কী করব?",
        "payment complete হলেও tax ledger-এ payment record আসেনি।",
    ],

    # ================================================================
    # TAX — RETURN
    # ================================================================
    "TAX_RETURN_ACKNOWLEDGEMENT": [
        "return জমা দিয়েছি, acknowledgement slip কোথায় পাব?",
        "tax return submission-এর receipt download করতে চাই।",
        "রিটার্ন দাখিলের প্রমাণ বা acknowledgement কীভাবে সংগ্রহ করব?",
        "submitted return-এর acknowledgement copy কোথা থেকে পাওয়া যাবে?",
    ],
    "TAX_RETURN_AMENDMENT": [
        "জমা দেওয়া tax return-এ ভুল হয়েছে, এখন amend করব কীভাবে?",
        "submitted return-এর তথ্য correction করতে চাই।",
        "return submit করার পরে ভুল ধরেছি, revised return কীভাবে দেব?",
        "আগে জমা দেওয়া আয়কর রিটার্ন সংশোধনের প্রক্রিয়া কী?",
    ],
    "TAX_RETURN_ASSET_LIABILITY": [
        "tax return-এ assets আর liabilities কোথায় উল্লেখ করতে হবে?",
        "আমার সম্পদ ও দায়ের তথ্য return-এ কীভাবে দেখাব?",
        "asset liability statement return-এর কোন অংশে দিতে হয়?",
        "return filing-এর সময় সম্পদ ও দায়ের তথ্য কীভাবে পূরণ করব?",
    ],
    "TAX_RETURN_COPY_DOWNLOAD": [
        "আগে জমা দেওয়া tax return-এর copy download করতে চাই।",
        "submitted income tax return PDF কোথা থেকে পাব?",
        "আমার filed return-এর একটি copy কীভাবে নামাব?",
        "পুরোনো জমা দেওয়া return document download করার উপায় কী?",
    ],
    "TAX_RETURN_DEADLINE": [
        "এই বছরের আয়কর রিটার্ন জমা দেওয়ার শেষ তারিখ কবে?",
        "tax return submission deadline কখন শেষ হবে?",
        "কোন তারিখের মধ্যে return জমা দিতে হবে?",
        "return filing-এর last date জানতে চাই।",
    ],
    "TAX_RETURN_ONLINE_SUBMISSION": [
        "e-Return portal দিয়ে online return submit করব কীভাবে?",
        "আয়কর রিটার্ন অনলাইনে দাখিল করার ধাপগুলো কী?",
        "online portal-এ completed return কীভাবে submit করব?",
        "আমি electronicভাবে tax return জমা দিতে চাই, কীভাবে করব?",
    ],
    "TAX_RETURN_PROCESS": [
        "আয়কর রিটার্ন করার পুরো প্রক্রিয়াটা শুরু থেকে শেষ পর্যন্ত কী?",
        "tax return filing-এর overall process বুঝতে চাই।",
        "প্রথমবার return দেব, পুরো filing procedure কী?",
        "income tax return প্রস্তুত ও দাখিল করার সাধারণ ধাপগুলো কী?",
    ],
    "TAX_RETURN_STATUS_VERIFICATION": [
        "আমি return জমা দিয়েছি, এখন submission status কীভাবে দেখব?",
        "submitted tax return processing status check করতে চাই।",
        "আমার return system-এ received হয়েছে কি না কোথায় দেখব?",
        "আগে submit করা return-এর বর্তমান status জানতে চাই।",
    ],

    # ================================================================
    # TAX — TIN
    # ================================================================
    "TAX_TIN_INFORMATION_UPDATE": [
        "আমার TIN-এর তথ্য update করতে চাই, কীভাবে করব?",
        "e-TIN profile-এ পুরোনো তথ্য পরিবর্তন করার নিয়ম কী?",
        "TIN registration-এর existing information edit করতে চাই।",
        "আমার TIN details ভুল আছে, update করার process কী?",
    ],

    # ================================================================
    # DRIVING LICENCE — ACCOUNT
    # ================================================================
    "DRIVING_LICENCE_ACCOUNT_ACCESS_PROBLEM": [
        "BSP account আছে কিন্তু সঠিক তথ্য দিয়েও ঢুকতে পারছি না।",
        "BRTA portal credentials ঠিক, তবুও account access হচ্ছে না।",
        "আমার BSP account খুলছে না, login information ঠিক আছে।",
        "existing BRTA account-এ প্রবেশ করতে পারছি না, কী করব?",
    ],
    "DRIVING_LICENCE_ACCOUNT_LOGIN": [
        "আমার existing BSP account-এ login করব কীভাবে?",
        "BRTA service portal-এ sign in করার জায়গা কোথায়?",
        "account already আছে, এখন portal-এ login করতে চাই।",
        "BSP account login করার নিয়মটা কী?",
    ],
    "DRIVING_LICENCE_ACCOUNT_OTP": [
        "BRTA portal-এর OTP আমার ফোনে আসছে না।",
        "BSP login-এর OTP পাচ্ছি না, কী করব?",
        "OTP পেয়েছি কিন্তু BRTA portal code accept করছে না।",
        "BSP verification code invalid দেখাচ্ছে, সমস্যাটা কী?",
    ],
    "DRIVING_LICENCE_ACCOUNT_REGISTRATION": [
        "BRTA service portal-এ নতুন account খুলতে চাই।",
        "আমার BSP account নেই, driver account registration কীভাবে করব?",
        "প্রথমবার BRTA portal ব্যবহার করব, account create করার নিয়ম কী?",
        "নতুন driving licence portal account register করতে চাই।",
    ],
    "DRIVING_LICENCE_PASSWORD_RESET": [
        "BSP account-এর password ভুলে গেছি, reset করব কীভাবে?",
        "BRTA portal password মনে নেই, নতুন password সেট করতে চাই।",
        "আমার driving licence portal password recover করতে হবে।",
        "password ভুলে যাওয়ায় BSP-তে ঢুকতে পারছি না, reset করতে চাই।",
    ],

    # ================================================================
    # DRIVING LICENCE — APPLICATION / COLLECTION
    # ================================================================
    "DRIVING_LICENCE_APPLICATION_STATUS": [
        "আমার driving licence application এখন কোন stage-এ আছে?",
        "লাইসেন্স আবেদনের current status কীভাবে check করব?",
        "application submit করেছি, এখন এর বর্তমান অবস্থা জানতে চাই।",
        "BRTA portal-এ licence application status কোথায় দেখা যায়?",
    ],
    "DRIVING_LICENCE_APPLICATION_DELAY": [
        "আমার driving licence application অনেকদিন ধরে pending আছে।",
        "অনেক সময় হয়ে গেছে, licence application এগোচ্ছে না কেন?",
        "আবেদনটি দীর্ঘদিন একই stage-এ আটকে আছে, কী করব?",
        "expected সময় পেরিয়ে গেছে কিন্তু licence application complete হয়নি।",
    ],
    "DRIVING_LICENCE_COLLECTION_DELIVERY": [
        "আমার driving licence ready হয়েছে, এখন কোথা থেকে সংগ্রহ করব?",
        "smart card তৈরি হয়ে গেছে, collection location জানতে চাই।",
        "লাইসেন্স প্রস্তুত হওয়ার পর হাতে পাওয়ার প্রক্রিয়া কী?",
        "ready driving licence card কীভাবে collect করব?",
    ],

    # ================================================================
    # DRIVING LICENCE — PAYMENT
    # ================================================================
    "DRIVING_LICENCE_FEE_INFORMATION": [
        "driving licence করতে মোট সরকারি fee কত?",
        "লাইসেন্সের জন্য কত টাকা fee দিতে হবে?",
        "driving licence service charge কত জানতে চাই।",
        "আমার licence application-এর fee amount কত হবে?",
    ],
    "DRIVING_LICENCE_PAYMENT_METHOD": [
        "driving licence fee কোন কোন মাধ্যমে দেওয়া যায়?",
        "BSP-তে licence fee payment করার method কী কী?",
        "mobile banking বা অন্য কোন মাধ্যমে licence fee দিতে পারব?",
        "লাইসেন্সের payment কীভাবে করা যায়?",
    ],
    "DRIVING_LICENCE_PAYMENT_FAILURE": [
        "driving licence fee দিতে গিয়ে transaction fail করছে।",
        "BSP payment complete হচ্ছে না, কী করব?",
        "লাইসেন্সের fee payment বারবার unsuccessful হচ্ছে।",
        "payment attempt করছি কিন্তু transaction শেষ হচ্ছে না।",
    ],
    "DRIVING_LICENCE_PAYMENT_VERIFICATION": [
        "লাইসেন্সের payment successful হয়েছে কি না কীভাবে check করব?",
        "BSP-তে আমার fee paid দেখাচ্ছে কি না জানতে চাই।",
        "driving licence payment confirmation কোথায় দেখা যায়?",
        "payment করার পর BRTA system সেটা received করেছে কি না কীভাবে বুঝব?",
    ],

    # ================================================================
    # DRIVING LICENCE — TEST
    # ================================================================
    "DRIVING_LICENCE_TEST_PROCESS": [
        "driving test কীভাবে নেওয়া হয়, পুরো processটা কী?",
        "ড্রাইভিং পরীক্ষায় কোন কোন ধাপ থাকে?",
        "competency test-এর procedure শুরু থেকে শেষ পর্যন্ত জানতে চাই।",
        "driving licence test দেওয়ার overall process কী?",
    ],
    "DRIVING_LICENCE_TEST_REQUIREMENTS": [
        "driving test-এর দিন কী কী সঙ্গে নিতে হবে?",
        "পরীক্ষায় অংশ নিতে কোন documents বা requirements লাগবে?",
        "driving test দিতে যাওয়ার আগে কী প্রস্তুতি দরকার?",
        "test attend করার জন্য কী কী requirement পূরণ করতে হবে?",
    ],
    "DRIVING_LICENCE_TEST_RESULT": [
        "আমি driving test-এ pass করেছি কি না কোথায় দেখব?",
        "ড্রাইভিং পরীক্ষার result কীভাবে check করব?",
        "competency test-এর ফল প্রকাশ হয়েছে কি না জানতে চাই।",
        "আমার driving test result online-এ কোথায় পাওয়া যাবে?",
    ],
    "DRIVING_LICENCE_TEST_RETAKE": [
        "driving test-এ fail করেছি, আবার পরীক্ষা কীভাবে দেব?",
        "পরীক্ষায় পাস করতে পারিনি, next attempt নেওয়ার নিয়ম কী?",
        "failed driving test-এর পরে retake কীভাবে করতে হয়?",
        "আগের test fail হয়েছে, পুনরায় পরীক্ষার জন্য কী করতে হবে?",
    ],
    "DRIVING_LICENCE_TEST_SCHEDULE": [
        "আমার driving test-এর তারিখ কবে?",
        "ড্রাইভিং পরীক্ষার schedule কোথায় check করব?",
        "test date এবং সময় কীভাবে জানতে পারব?",
        "আমার competency test কখন হবে সেটা কোথায় দেখা যায়?",
    ],

    # ================================================================
    # DRIVING LICENCE — RENEWAL
    # ================================================================
    "DRIVING_LICENCE_EXPIRED_RENEWAL": [
        "আমার driving licence ইতিমধ্যে expired, এখন কীভাবে renew করব?",
        "মেয়াদ শেষ হয়ে যাওয়া licence renewal-এর নিয়ম কী?",
        "expired driving licence আবার valid করতে কী করতে হবে?",
        "লাইসেন্সের মেয়াদ শেষ হয়ে গেছে, renewal শুরু করব কীভাবে?",
    ],
    "DRIVING_LICENCE_RENEWAL_DOCUMENTS": [
        "driving licence renew করতে কী কী documents লাগবে?",
        "renewal application-এর জন্য প্রয়োজনীয় কাগজপত্র কী?",
        "লাইসেন্স নবায়নের সময় কোন documents জমা দিতে হবে?",
        "renewal করতে যাওয়ার আগে কী কী document প্রস্তুত রাখব?",
    ],
    "DRIVING_LICENCE_RENEWAL_PROCESS": [
        "driving licence renewal-এর পুরো process কী?",
        "লাইসেন্স নবায়নের আবেদন কীভাবে করব?",
        "existing licence renew করার ধাপগুলো জানতে চাই।",
        "renewal application শুরু থেকে শেষ পর্যন্ত কীভাবে হয়?",
    ],

    # ================================================================
    # DRIVING LICENCE — REPLACEMENT
    # ================================================================
    "DRIVING_LICENCE_LOST_REPLACEMENT": [
        "আমার driving licence হারিয়ে গেছে, replacement কীভাবে পাব?",
        "লাইসেন্স খুঁজে পাচ্ছি না, নতুন replacement card চাই।",
        "lost driving licence পুনরায় পাওয়ার process কী?",
        "লাইসেন্স হারানোর পরে reissue করতে কী করতে হবে?",
    ],
    "DRIVING_LICENCE_DAMAGED_REPLACEMENT": [
        "আমার driving licence card নষ্ট হয়ে গেছে, replacement চাই।",
        "লাইসেন্সটি damaged হয়েছে, নতুন card কীভাবে পাব?",
        "ভাঙা বা ক্ষতিগ্রস্ত driving licence reissue করার নিয়ম কী?",
        "card আছে কিন্তু ব্যবহারযোগ্য নয়, replacement করতে চাই।",
    ],
    "DRIVING_LICENCE_DUPLICATE_PROCESS": [
        "driving licence-এর duplicate copy পেতে কী করতে হবে?",
        "আমার licence-এর duplicate issue করার process জানতে চাই।",
        "duplicate driving licence card-এর জন্য কীভাবে আবেদন করব?",
        "existing licence-এর আরেকটি official duplicate প্রয়োজন।",
    ],

    # ================================================================
    # DRIVING LICENCE — LEARNER
    # ================================================================
    "DRIVING_LICENCE_LEARNER_COPY": [
        "আমার learner licence-এর copy কোথা থেকে download করব?",
        "learner permit-এর PDF copy কীভাবে পাব?",
        "আগে করা learner licence-এর একটি copy চাই।",
        "learner document online থেকে কীভাবে নামাব?",
    ],
    "DRIVING_LICENCE_LEARNER_DOCUMENTS": [
        "learner licence করতে কী কী documents প্রয়োজন?",
        "learner permit application-এর কাগজপত্র কী কী?",
        "learner licence-এর জন্য কোন documents জমা দিতে হবে?",
        "learner application করার আগে কী কী document লাগবে?",
    ],
    "DRIVING_LICENCE_LEARNER_PROCESS": [
        "learner driving licence করার পুরো process কী?",
        "learner permit-এর জন্য কীভাবে আবেদন শুরু করব?",
        "learner licence application-এর ধাপগুলো কী?",
        "প্রথমবার learner licence নিতে কী প্রক্রিয়া অনুসরণ করব?",
    ],

    # ================================================================
    # DRIVING LICENCE — TYPE
    # ================================================================
    "DRIVING_LICENCE_TYPE_SELECTION": [
        "আমার জন্য কোন ধরনের driving licence apply করা উচিত?",
        "professional না non-professional licence কোনটা নির্বাচন করব?",
        "driving licence category select করার নিয়ম কী?",
        "আমি কোন licence type-এর জন্য eligible সেটা কীভাবে বুঝব?",
    ],
    "DRIVING_LICENCE_TYPE_CHANGE": [
        "আমার existing driving licence-এর type পরিবর্তন করতে চাই।",
        "non-professional licence professional করতে কী করতে হবে?",
        "বর্তমান licence category change করার process কী?",
        "এক ধরনের driving licence থেকে অন্য type-এ পরিবর্তন করা যাবে কীভাবে?",
    ],
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text))
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    train = read_csv(TRAIN)
    dev = read_csv(DEV)
    test = read_csv(TEST)

    dev_hash_before = sha256(DEV)
    test_hash_before = sha256(TEST)

    expected_columns = list(train.columns)

    if len(train) != 1584:
        raise ValueError(
            f"Expected frozen TRAIN to have 1584 rows, found {len(train)}"
        )

    if train["query_topic_id"].nunique() != 264:
        raise ValueError("Frozen TRAIN does not contain all 264 intents")

    repair_intents = set(REPAIR)

    missing = repair_intents - set(train["query_topic_id"])
    if missing:
        raise ValueError(
            f"Repair intents missing from frozen TRAIN: {sorted(missing)}"
        )

    repair_count = sum(len(values) for values in REPAIR.values())

    if repair_count != EXPECTED_REPAIR_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_REPAIR_ROWS} repair rows, "
            f"but REPAIR contains {repair_count}"
        )

    for intent_id, examples in REPAIR.items():
        if len(examples) != 4:
            raise ValueError(
                f"{intent_id} must have exactly 4 repair examples"
            )

    existing_text = {
        normalized(text)
        for frame in (train, dev, test)
        for text in frame["text"]
    }

    generated_text: set[str] = set()
    new_rows: list[dict[str, str]] = []

    for intent_id in sorted(REPAIR):
        target = train[
            train["query_topic_id"].eq(intent_id)
        ]

        if target.empty:
            raise ValueError(
                f"No training template found for {intent_id}"
            )

        template = target.iloc[0].to_dict()
        service = template["service"]

        if service not in {
            "TAX",
            "DRIVING_LICENCE",
        }:
            raise ValueError(
                f"{intent_id} unexpectedly belongs to {service}"
            )

        for index, text in enumerate(
            REPAIR[intent_id],
            start=1,
        ):
            key = normalized(text)

            if not key:
                raise ValueError(
                    f"{intent_id} repair example {index} is blank"
                )

            if key in existing_text:
                raise ValueError(
                    f"{intent_id} repair example {index} duplicates "
                    f"existing TRAIN/DEV/TEST text: {text!r}"
                )

            if key in generated_text:
                raise ValueError(
                    f"{intent_id} repair example {index} duplicates "
                    f"another repair example: {text!r}"
                )

            generated_text.add(key)

            row = dict(template)

            row["id"] = (
                f"REPAIR_{intent_id}_{index:02d}"
            )
            row["text"] = text
            row["language_style"] = (
                STYLE_CYCLE[index - 1]
            )
            row["privacy_present"] = "FALSE"
            row["privacy_types"] = ""
            row["source_type"] = "SYNTHETIC"
            row["parent_query_id"] = (
                f"{intent_id}_REPAIR_F{index:02d}"
            )
            row["difficulty"] = "Hard"
            row["is_ood"] = "FALSE"
            row["annotation_notes"] = (
                "TRAIN-only manually controlled hard-confusion "
                "repair example; no REAL provenance claimed."
            )

            new_rows.append(row)

    repair = pd.DataFrame(
        new_rows,
        columns=expected_columns,
    )

    if len(repair) != EXPECTED_REPAIR_ROWS:
        raise ValueError(
            f"Repair dataframe has {len(repair)} rows; "
            f"expected {EXPECTED_REPAIR_ROWS}"
        )

    if repair["id"].duplicated().any():
        raise ValueError("Duplicate repair row IDs")

    if repair["text"].map(normalized).duplicated().any():
        raise ValueError(
            "Duplicate normalized text inside repair set"
        )

    combined = pd.concat(
        [train, repair],
        ignore_index=True,
    )

    if list(combined.columns) != expected_columns:
        raise ValueError("Derived TRAIN schema changed")

    expected_total = len(train) + EXPECTED_REPAIR_ROWS

    if len(combined) != expected_total:
        raise ValueError(
            f"Expected {expected_total} total rows, "
            f"found {len(combined)}"
        )

    if combined["id"].duplicated().any():
        raise ValueError(
            "Duplicate row IDs in derived TRAIN"
        )

    normalized_combined = combined["text"].map(
        normalized
    )

    if normalized_combined.duplicated().any():
        duplicate_rows = combined[
            normalized_combined.duplicated(
                keep=False
            )
        ][
            [
                "id",
                "query_topic_id",
                "text",
            ]
        ]

        raise ValueError(
            "Duplicate text found in derived TRAIN:\n"
            + duplicate_rows.to_string(
                index=False
            )
        )

    dev_text = set(
        dev["text"].map(normalized)
    )

    test_text = set(
        test["text"].map(normalized)
    )

    repair_text = set(
        repair["text"].map(normalized)
    )

    repair_dev_overlap = (
        repair_text & dev_text
    )

    repair_test_overlap = (
        repair_text & test_text
    )

    if repair_dev_overlap:
        raise ValueError(
            "Repair text overlaps DEV"
        )

    if repair_test_overlap:
        raise ValueError(
            "Repair text overlaps TEST"
        )

    dev_families = set(
        dev["parent_query_id"]
    )

    test_families = set(
        test["parent_query_id"]
    )

    repair_families = set(
        repair["parent_query_id"]
    )

    if repair_families & dev_families:
        raise ValueError(
            "Repair family overlaps DEV"
        )

    if repair_families & test_families:
        raise ValueError(
            "Repair family overlaps TEST"
        )

    intent_counts_before = (
        train.groupby(
            "query_topic_id"
        )
        .size()
        .to_dict()
    )

    intent_counts_after = (
        combined.groupby(
            "query_topic_id"
        )
        .size()
        .to_dict()
    )

    for intent_id in repair_intents:
        expected = (
            intent_counts_before[intent_id]
            + 4
        )

        if (
            intent_counts_after[intent_id]
            != expected
        ):
            raise ValueError(
                f"{intent_id}: expected "
                f"{expected} rows after repair, "
                f"found "
                f"{intent_counts_after[intent_id]}"
            )

    non_target_intents = (
        set(intent_counts_before)
        - repair_intents
    )

    for intent_id in non_target_intents:
        if (
            intent_counts_after[intent_id]
            != intent_counts_before[intent_id]
        ):
            raise ValueError(
                f"Non-target intent changed: "
                f"{intent_id}"
            )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    dev_hash_after = sha256(DEV)
    test_hash_after = sha256(TEST)

    report = {
        "base_train": str(
            TRAIN.relative_to(ROOT)
        ),
        "output_train": str(
            OUTPUT.relative_to(ROOT)
        ),
        "original_train_rows": len(train),
        "repair_rows": len(repair),
        "derived_train_rows": len(combined),
        "repair_intents": len(REPAIR),
        "tax_repair_rows": int(
            repair["service"]
            .eq("TAX")
            .sum()
        ),
        "driving_licence_repair_rows": int(
            repair["service"]
            .eq(
                "DRIVING_LICENCE"
            )
            .sum()
        ),
        "unique_intents_total": int(
            combined[
                "query_topic_id"
            ].nunique()
        ),
        "repair_text_dev_overlap": len(
            repair_dev_overlap
        ),
        "repair_text_test_overlap": len(
            repair_test_overlap
        ),
        "repair_family_dev_overlap": len(
            repair_families
            & dev_families
        ),
        "repair_family_test_overlap": len(
            repair_families
            & test_families
        ),
        "dev_sha256_before": (
            dev_hash_before
        ),
        "dev_sha256_after": (
            dev_hash_after
        ),
        "test_sha256_before": (
            test_hash_before
        ),
        "test_sha256_after": (
            test_hash_after
        ),
        "dev_unchanged": (
            dev_hash_before
            == dev_hash_after
        ),
        "test_unchanged": (
            test_hash_before
            == test_hash_after
        ),
        "validation_passed": True,
    }

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print(
        "TAX + DRIVING LICENCE "
        "REPAIR DATASET VALIDATION PASSED"
    )

    print(
        "Output:",
        OUTPUT,
    )


if __name__ == "__main__":
    main()