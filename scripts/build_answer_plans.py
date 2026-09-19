"""Build the auditable 264-intent answer-plan catalogue from frozen sources."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.models.hierarchy import load_contract
from src.response.facts import facts_for, render_fact
from src.retrieval.corpus import load_records


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "knowledge_base" / "answer_plans.json"
TAXONOMIES = {
    "NID": ROOT / "taxonomy" / "nid.yaml",
    "BIRTH_REGISTRATION": ROOT / "taxonomy" / "birth_registration.yaml",
    "PASSPORT": ROOT / "taxonomy" / "passport.yaml",
    "TAX": ROOT / "taxonomy" / "tax.yaml",
    "POLICE_GD": ROOT / "taxonomy" / "police_gd.yaml",
    "DRIVING_LICENCE": ROOT / "taxonomy" / "driving_licence.yaml",
}
SERVICE_NAMES = {
    "NID": ("NID services", "এনআইডি সেবা"),
    "BIRTH_REGISTRATION": ("Birth Registration services", "জন্ম নিবন্ধন সেবা"),
    "PASSPORT": ("e-Passport services", "ই-পাসপোর্ট সেবা"),
    "TAX": ("NBR tax services", "এনবিআর করসেবা"),
    "POLICE_GD": ("Bangladesh Police GD services", "বাংলাদেশ পুলিশ জিডি সেবা"),
    "DRIVING_LICENCE": ("BRTA driving-licence services", "বিআরটিএ ড্রাইভিং লাইসেন্স সেবা"),
}


def loc(en: str, bn: str) -> dict[str, str]:
    return {"en": en, "bn": bn}


CUSTOM_DIRECT = {
    "NID_ONLINE_OTP_NOT_RECEIVED": loc(
        "This is an NID account OTP-delivery problem. The reviewed sources do not provide a reliable OTP troubleshooting sequence.",
        "এটি NID account-এর OTP না পাওয়ার সমস্যা। যাচাইকৃত তথ্যে নির্ভরযোগ্য OTP troubleshooting ধাপ নিশ্চিত করা নেই।",
    ),
    "NID_ONLINE_OTP_VERIFICATION": loc(
        "This is an NID account OTP-verification problem. The reviewed sources do not establish why a received code may be rejected.",
        "এটি NID account-এ পাওয়া OTP verify না হওয়ার সমস্যা। code reject হওয়ার নির্দিষ্ট কারণ যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "BR_REGISTRATION_OTP_NOT_RECEIVED": loc(
        "Your problem is at the Birth Registration OTP-delivery step. The reviewed sources do not provide a reliable troubleshooting sequence for a missing OTP.",
        "আপনার সমস্যাটি জন্ম নিবন্ধনের OTP না পাওয়ার ধাপে হচ্ছে। OTP না আসার নির্দিষ্ট troubleshooting ধাপ যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "BR_VERIFICATION_FAILURE": loc(
        "Your Birth Registration record-verification attempt is failing. The reviewed sources confirm the verification service but not the cause of this specific failure.",
        "আপনার জন্ম নিবন্ধন record verification চেষ্টা ব্যর্থ হচ্ছে। যাচাই সেবাটি নিশ্চিত, তবে এই নির্দিষ্ট failure-এর কারণ যাচাইকৃত তথ্যে নেই।",
    ),
    "BR_APPLICATION_DELAY": loc(
        "Your submitted Birth Registration application appears delayed. The reviewed sources do not establish a standard completion time or a case-specific cause.",
        "আপনার জমা দেওয়া জন্ম নিবন্ধন আবেদনটি দেরি হচ্ছে। নির্দিষ্ট কারণ বা standard completion time যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "PASSPORT_APPLICATION_DELAY": loc(
        "Your passport application appears to have remained pending longer than expected. The reviewed sources do not establish the reason or promise a completion date.",
        "আপনার passport application প্রত্যাশার চেয়ে বেশি সময় pending আছে। এর কারণ বা completion date যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "PASSPORT_ONLINE_ACCOUNT_ACCESS_PROBLEM": loc(
        "This is an e-Passport account-access problem. The next safe step depends on whether sign-in, password recovery, activation, or contact verification is failing.",
        "এটি e-Passport account access-এর সমস্যা। sign-in, password recovery, activation, নাকি contact verification—কোন ধাপে সমস্যা হচ্ছে তার ওপর পরের সহায়তা নির্ভর করে।",
    ),
    "TAX_RETURN_DEADLINE": loc(
        "You are asking about the current tax-return deadline. No current deadline is asserted because the reviewed sources do not verify one for your exact situation.",
        "আপনি বর্তমান tax return deadline জানতে চাইছেন। আপনার নির্দিষ্ট পরিস্থিতির deadline যাচাইকৃত উৎসে নিশ্চিত নয়, তাই এখানে কোনো তারিখ বলা হচ্ছে না।",
    ),
    "TAX_PAYMENT_FAILURE": loc(
        "This is a tax-payment failure. The reviewed sources do not identify the cause or confirm the transaction outcome for an individual case.",
        "এটি tax payment failure-এর সমস্যা। ব্যক্তিগত transaction-এর কারণ বা ফল যাচাইকৃত তথ্যে নিশ্চিত করা সম্ভব নয়।",
    ),
    "POLICE_GD_OTHER_INCIDENT": loc(
        "You want to know whether another non-emergency incident fits the Online GD service. The reviewed sources do not confirm coverage for every incident type.",
        "আপনি জানতে চাইছেন অন্য কোনো non-emergency ঘটনা Online GD-তে করা যায় কি না। প্রতিটি incident type-এর coverage যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "DRIVING_LICENCE_TEST_RETAKE": loc(
        "You need guidance after an unsuccessful driving test. The reviewed sources do not establish the current retake booking, fee, or timing rules.",
        "আপনি driving test-এ সফল না হওয়ার পর retake guidance চাইছেন। বর্তমান retake booking, fee বা timing-এর নিয়ম যাচাইকৃত তথ্যে নিশ্চিত করা নেই।",
    ),
    "DRIVING_LICENCE_GENERAL_GUIDANCE": loc(
        "Your question is about a Driving Licence service, but the exact task is not yet clear enough for a specific answer.",
        "আপনার প্রশ্নটি Driving Licence সেবা নিয়ে, তবে নির্দিষ্ট কাজটি পরিষ্কার না হওয়ায় exact উত্তর দেওয়া যাচ্ছে না।",
    ),
}


def answer_type(topic_id: str) -> str:
    value = topic_id.upper()
    checks = (
        (("EMERGENCY",), "EMERGENCY"),
        (("FAIL", "PROBLEM", "DELAY", "NOT_RECEIVED", "LOCKED", "ERROR", "RETAKE"), "TROUBLESHOOTING"),
        (("DOCUMENT",), "DOCUMENTS"),
        (("FEE", "COST"), "FEE"),
        (("PAYMENT", "RECEIPT", "REFUND"), "PAYMENT"),
        (("STATUS", "TRACK", "READY"), "STATUS"),
        (("ELIGIB",), "ELIGIBILITY"),
        (("CORRECTION", "CHANGE", "AMEND"), "CORRECTION"),
        (("REPLACEMENT", "REISSUE", "LOST", "STOLEN", "DAMAGED"), "REPLACEMENT"),
        (("VERIFY", "VERIFICATION"), "VERIFICATION"),
        (("ACCOUNT", "LOGIN", "PASSWORD", "OTP", "ACTIVATION"), "ACCOUNT_ACCESS"),
        (("PROCESS", "APPLICATION", "REGISTRATION", "RENEWAL", "PRINT", "COLLECTION", "CANCELLATION", "SUBMISSION", "RETURN"), "PROCEDURE"),
        (("GENERAL", "INFORMATION", "GUIDANCE", "PURPOSE"), "GENERAL_INFORMATION"),
    )
    for terms, result in checks:
        if any(term in value for term in terms):
            return result
    return "CLARIFICATION"


def clarification(kind: str) -> dict[str, str]:
    questions = {
        "DOCUMENTS": loc(
            "Are you asking about a new application, a correction, a renewal, or a replacement?",
            "আপনি নতুন আবেদন, সংশোধন, নবায়ন, নাকি প্রতিস্থাপনের কাগজপত্র জানতে চাইছেন?",
        ),
        "STATUS": loc(
            "Have you already submitted the request, and what status or error is shown? Please do not share the actual reference number.",
            "আপনি কি আবেদনটি জমা দিয়েছেন, এবং কোন status বা error দেখাচ্ছে? আসল reference number শেয়ার করবেন না।",
        ),
        "ELIGIBILITY": loc(
            "Which applicant category or personal situation should the eligibility answer cover?",
            "যোগ্যতার উত্তরটি কোন আবেদনকারী শ্রেণি বা পরিস্থিতির জন্য দরকার?",
        ),
        "FEE": loc(
            "Which exact transaction or service option do you need the current fee for?",
            "কোন নির্দিষ্ট কাজ বা service option-এর বর্তমান fee জানতে চান?",
        ),
        "CORRECTION": loc(
            "Which recorded field is wrong, and has the document or record already been issued?",
            "কোন তথ্যটি ভুল, এবং সনদ বা রেকর্ডটি কি ইতিমধ্যে ইস্যু হয়েছে?",
        ),
        "REPLACEMENT": loc(
            "Was the document lost, stolen, damaged, expired, or do you only need another copy?",
            "নথিটি হারিয়েছে, চুরি হয়েছে, নষ্ট হয়েছে, মেয়াদ শেষ হয়েছে, নাকি শুধু আরেকটি কপি দরকার?",
        ),
        "TROUBLESHOOTING": loc(
            "At which step does the problem occur, and what message is shown? Do not share any OTP, password, or identifier.",
            "সমস্যাটি কোন ধাপে হচ্ছে এবং কী message দেখাচ্ছে? OTP, password বা পরিচয় নম্বর শেয়ার করবেন না।",
        ),
        "VERIFICATION": loc(
            "Are you asking how to verify the record, or did a verification attempt fail?",
            "আপনি কীভাবে রেকর্ড verify করতে হয় জানতে চাইছেন, নাকি verification চেষ্টা ব্যর্থ হয়েছে?",
        ),
        "ACCOUNT_ACCESS": loc(
            "Is the problem registration, sign-in, password recovery, OTP delivery, or OTP acceptance?",
            "সমস্যাটি registration, sign-in, password recovery, OTP না পাওয়া, নাকি OTP accept না হওয়া—কোনটি?",
        ),
        "PAYMENT": loc(
            "Is your question about how to pay, a failed payment, confirmation, receipt, or refund?",
            "আপনার প্রশ্নটি payment method, failed payment, confirmation, receipt, নাকি refund নিয়ে?",
        ),
        "PROCEDURE": loc(
            "Which step have you reached, and what do you need help doing next?",
            "আপনি কোন ধাপ পর্যন্ত এসেছেন এবং পরের কোন কাজটিতে সহায়তা দরকার?",
        ),
        "GENERAL_INFORMATION": loc(
            "Which part of this service would you like explained?",
            "এই সেবার কোন অংশটি বিস্তারিত জানতে চান?",
        ),
        "CLARIFICATION": loc(
            "What outcome are you trying to achieve, and what has already happened?",
            "আপনি কী ফল চান এবং এখন পর্যন্ত কী ঘটেছে?",
        ),
    }
    return questions.get(kind, questions["CLARIFICATION"])


def taxonomy_topics() -> dict[str, dict]:
    output = {}
    for service, path in TAXONOMIES.items():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for parent_id, parent in data["parent_topics"].items():
            default = parent.get("default_evidence_status")
            for topic_id, topic in parent["query_topics"].items():
                output[topic_id] = {
                    "service": service,
                    "parent_topic_id": parent_id,
                    "title": topic["display_name"],
                    "evidence_status": topic.get("evidence_status", default),
                }
    return output


def specific_plan(topic: dict, record: dict) -> dict:
    units = facts_for(record)
    for_language = {}
    for language in ("en", "bn"):
        lead = [unit for unit in units[1:] if unit.get("prominence") == "lead"]
        rest = [unit for unit in units[1:] if unit.get("prominence") != "lead"]
        for_language[language] = {
            "direct": " ".join(render_fact(unit, language) for unit in [units[0], *lead]),
            "steps": [render_fact(unit, language) for unit in rest],
        }
    return {
        "query_topic_id": record["query_topic_id"],
        "service": record["service"],
        "parent_topic_id": record["parent_topic_id"],
        "title": record["title"],
        "answer_type": answer_type(record["query_topic_id"]),
        "grounding_level": "VERIFIED_SPECIFIC",
        "direct_answer": loc(for_language["en"]["direct"], for_language["bn"]["direct"]),
        "steps": [loc(en, bn) for en, bn in zip(for_language["en"]["steps"], for_language["bn"]["steps"])],
        "required_documents": record["required_documents"],
        "warnings": [],
        "clarification_question": None,
        "official_source": record["official_source"],
        "source_url": record["source_url"],
        "last_verified": record["last_verified"],
        "scope_note": loc(
            "This answer is limited to the reviewed official instructions for this exact topic.",
            "এই উত্তরটি এই নির্দিষ্ট বিষয়ে পর্যালোচিত সরকারি নির্দেশনার মধ্যেই সীমিত।",
        ),
    }


def bounded_plan(topic_id: str, topic: dict, source: dict) -> dict:
    kind = answer_type(topic_id)
    official = str(topic.get("evidence_status") or "").startswith("official_")
    level = "VERIFIED_GENERAL" if official else "SAFE_CLARIFICATION"
    service_en, service_bn = SERVICE_NAMES[topic["service"]]
    title = topic["title"]
    if level == "VERIFIED_GENERAL":
        direct = loc(
            f"Your question is about {title}. This is handled within {service_en}, but the available verified guidance does not establish more specific current details for this exact case.",
            f"“{title}” বিষয়টি {service_bn}-এর আওতায় পড়ে। তবে এই নির্দিষ্ট পরিস্থিতির বিস্তারিত বর্তমান নিয়ম যাচাইকৃত তথ্যে নিশ্চিত নয়।",
        )
        steps = [loc(
            f"Check the current official {service_en} instructions for the option that matches {title}.",
            f"“{title}”-এর সঙ্গে মিলে এমন option-এর বর্তমান নির্দেশনা সরকারি {service_bn}-এ দেখুন।",
        )]
    else:
        direct = loc(
            f"I understand that your issue is {title}. The available verified guidance does not contain enough detail for a reliable case-specific answer without clarification.",
            f"আপনার সমস্যাটি “{title}” বিষয়ে। নির্ভরযোগ্য case-specific উত্তর দেওয়ার মতো পর্যাপ্ত detail যাচাইকৃত তথ্যে নেই।",
        )
        steps = []
    return {
        "query_topic_id": topic_id,
        "service": topic["service"],
        "parent_topic_id": topic["parent_topic_id"],
        "title": title,
        "answer_type": kind,
        "grounding_level": level,
        "direct_answer": CUSTOM_DIRECT.get(topic_id, direct),
        "steps": steps,
        "required_documents": [],
        "warnings": [loc(
            "No unverified fee, deadline, document, eligibility condition, or processing time is asserted here.",
            "এখানে যাচাই না-করা fee, deadline, document, eligibility condition বা processing time বলা হয়নি।",
        )],
        "clarification_question": clarification(kind),
        "official_source": source["official_source"],
        "source_url": source["source_url"],
        "last_verified": source["last_verified"],
        "scope_note": loc(
            "This is a bounded answer plan; consult the linked official service for current case-specific rules.",
            "এটি সীমিত answer plan; বর্তমান case-specific নিয়মের জন্য সংযুক্ত সরকারি সেবা দেখুন।",
        ),
    }


def build() -> dict:
    contract = load_contract()
    topics = taxonomy_topics()
    records = load_records()
    exact = {record["query_topic_id"]: record for record in records if record["query_topic_id"]}
    by_parent = {
        (record["service"], record["parent_topic_id"]): record
        for record in records if record["parent_topic_id"] and not record["query_topic_id"]
    }
    by_service = {record["service"]: record for record in records if record["parent_topic_id"] is None}
    plans = []
    for service, service_data in contract["services"].items():
        for parent_id, parent in service_data["parent_topics"].items():
            for topic_id in parent["query_topics"]:
                topic = topics[topic_id]
                if topic_id in exact:
                    plans.append(specific_plan(topic, exact[topic_id]))
                else:
                    source = by_parent.get((service, parent_id), by_service[service])
                    plans.append(bounded_plan(topic_id, topic, source))
    return {"version": "1.0.0", "plans": plans}


def main() -> None:
    payload = build()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    levels = {}
    for plan in payload["plans"]:
        levels[plan["grounding_level"]] = levels.get(plan["grounding_level"], 0) + 1
    print(f"SAVED: {OUTPUT}")
    print(f"EXACT INTENT PLANS: {len(payload['plans'])}/264")
    print(f"GROUNDING LEVELS: {levels}")


if __name__ == "__main__":
    main()
