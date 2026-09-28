# NID Five-Class Annotation Policy V1

## Scope and status

This policy governs annotation against the five frozen source labels in `NID-5CLASS-PHASE0-V1`. It does not rename labels, repair the source, create a sixth training class, or introduce fine-grained intents. Its status is **FROZEN_V1** after targeted human review resolved all three cross-label equivalence boundaries.

## Decision unit

Annotate the citizen's explicit requested action or information need, not isolated tokens. The mentioned entity, channel, document, or lifecycle stage is supporting context. A word such as “Smart,” “online,” “application,” “status,” or “new” is a common cue, never a complete definition.

Use this order:

1. Identify the explicit requested action or problem.
2. Identify lifecycle context: first application, established record, replacement, online-account access, or Smart Card issuance/distribution.
3. Prefer explicit action over the mentioned object. Smart NID does not automatically imply Smart ID Card when the explicit action is loss/damage replacement.
4. Use the narrowest supported one of the five frozen coarse meanings without inventing missing facts.
5. If two meanings remain materially plausible, use the evaluation state `CLARIFY_REQUIRED`.

Do not use model predictions, Phase 0 split membership, lexical similarity scores, or class frequency as annotation evidence.

## CLASSIFIABLE

A query is `CLASSIFIABLE` when explicit information supports one coarse intent strongly enough that the other labels would require adding an unstated event or lifecycle stage. The annotator may use stated action, object, temporal stage, and problem condition together.

Decision logic:

- Changing an established identity record is Information Correction.
- First-time voter/NID enrolment and its application lifecycle is New NID Registration.
- Loss, theft, damage, replacement, or reissue of an issued card is Lost/Stolen NID.
- Online account access, OTP, login, verification, portal availability, or online-copy access is NID Online Problem.
- Smart Card eligibility, issuance, readiness, distribution, collection, status, or delay is Smart ID Card unless an explicit replacement action controls.

## CLARIFY_REQUIRED

`CLARIFY_REQUIRED` is an evaluation/annotation state, not a sixth frozen training label. Use it when:

- two or more frozen labels remain materially plausible from the query alone;
- the requested action is absent or only an entity is named;
- “registration” could mean first-time NID registration or online-account registration;
- “new/another card” could mean first issuance, Smart distribution, or replacement;
- “status” lacks the application lifecycle being tracked;
- a Smart NID is said to be unavailable without distinguishing delay/collection from loss/damage;
- a portal/channel is mentioned but no underlying action or failure is stated;
- choosing a label would require inventing whether the citizen already has an NID.

Future challenge annotations should record the plausible candidate labels and one targeted clarification question. They must not force a gold label by adding unstated context.

## Neighbor rules

### Correction versus New Registration

The decisive context is established record versus first-time/pending enrolment. A form mistake during an uncompleted first application is registration; changing a completed/established NID record is correction. If the record stage is missing and both interpretations remain plausible, clarify.

### Correction versus Online Problem

Correcting the authoritative NID record remains correction even when the citizen intends to use an online channel. Account/profile access or portal/verification failure is online problem. Clarify when “online information is wrong” does not reveal which record is meant.

### New Registration versus Online Problem

First-time NID/voter application is registration. Creating or accessing an online-services account is online problem. “Online registration” without its object requires clarification.

### New Registration versus Smart ID Card

General first-time enrolment is registration. Smart-specific eligibility, application, issuance, readiness, distribution, or routine collection is Smart ID Card. Targeted human review resolved the two conflicting collection pairs to Smart ID Card for future canonical annotation.

### Lost/Stolen versus Smart ID Card

The requested action controls: loss/damage replacement or reissue is Lost/Stolen, including damage-driven Smart NID replacement; ordinary Smart issuance, readiness, distribution, and collection is Smart ID Card. Targeted human review resolved the conflicting damaged-Smart-NID pair to Lost/Stolen NID for future canonical annotation.

### Lifecycle status and online channel

Tracking a clearly identified registration, replacement, or Smart Card application stays with that lifecycle. Use Online Problem only when the information need is account access, verification, portal availability, or a technical online-service failure.

## Source labels and conflicts

Frozen source labels are preserved as provenance, not assumed infallible. Three cross-label equivalent pairs remain recorded in the Git-safe conflict register, alongside their human-confirmed canonical future labels. No row is relabelled by this audit. Any later dataset repair requires a separately versioned task and must not rewrite Phase 0.

## Human-Frozen Boundary Rules

1. Routine collection or distribution of a specifically identified Smart NID is `Smart ID Card`.
2. Replacement or reissue caused by loss, theft, or damage is `Lost/Stolen NID`, including when the damaged or lost object is explicitly called a Smart NID.
3. The requested action and lifecycle stage take precedence over the entity token “Smart NID.”
4. Historical source-label disagreement does not by itself imply semantic ambiguity and is not sufficient for `CLARIFY_REQUIRED`.
5. Historical source labels remain frozen and are not retroactively modified.
6. Future challenge-set annotations follow the canonical `FROZEN_V1` contract rather than inconsistent historical source labels.

## Weak evidence

Frequent cues, script, language style, spelling, and templates may help retrieve evidence but cannot decide a class. English, Bangla, Banglish, and mixed-script forms follow the same semantic rules. Similar wording can encode different actions, while dissimilar wording can encode the same action.
