"""Independent service evidence for deciding whether to display an automatic answer."""

from __future__ import annotations

from src.models.service_anchors import service_anchors


BANGLA_SERVICE_TERMS = {
    "NID": ("এনআইডি", "জাতীয় পরিচয়পত্র", "ভোটার আইডি"),
    "BIRTH_REGISTRATION": ("জন্ম নিবন্ধন", "জন্ম সনদ"),
    "PASSPORT": ("পাসপোর্ট",),
    "TAX": ("আয়কর", "ই-টিন", "ট্যাক্স"),
    "POLICE_GD": ("জিডি", "সাধারণ ডায়েরি"),
    "DRIVING_LICENCE": ("ড্রাইভিং লাইসেন্স", "লার্নার লাইসেন্স"),
}


def evidenced_services(text: str) -> set[str]:
    lowered = text.lower()
    evidence = set(service_anchors(text))
    evidence.update(
        service for service, terms in BANGLA_SERVICE_TERMS.items()
        if any(term in lowered for term in terms)
    )
    return evidence


def supported_service(text: str, predicted: str | None) -> bool:
    return bool(predicted) and evidenced_services(text) == {predicted}
