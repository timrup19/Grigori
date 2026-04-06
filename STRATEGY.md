# Grigori — Strategic Moat & Product Vision

> *From a Prozorro analytics tool to the definitive intelligence layer for public procurement in emerging markets.*

---

## The Core Problem with "Just Prozorro"

Public API analytics is table stakes. Anyone with a FastAPI backend and scikit-learn can clone the current feature set in a weekend. The moat has to come from data no one else has, intelligence no one else can replicate, and network effects that get stronger with every user.

Here is how to build that.

---

## 1. Proprietary Beneficial Ownership Graph

**The idea:** Prozorro shows you *who won a contract*. It does not tell you *who actually owns that company* — the real human behind layers of shell companies.

**What to build:**
- Ingest Ukraine's Unified State Register (USR), YouControl, OpenSanctions, NABU disclosures, and EU beneficial ownership registries
- Build a persistent entity resolution graph linking:
  - EDRPOU numbers → natural persons (directors, founders, UBOs)
  - Natural persons → politically exposed person (PEP) status
  - Natural persons → sanctioned entities lists (OFAC, EU, UK)
  - Natural persons → asset declarations (Ukrainian e-declaration system)
- Every node in the graph is enriched across *all* of these sources simultaneously

**Why this is a moat:** This graph takes years to build correctly. Entity disambiguation (same person, different name spellings across Cyrillic/Latin transliterations) requires a specialized trained model. Once you have it, no competitor starts from zero — they start from five years behind.

**VC signal:** Panama Papers investigators paid millions for tools that did a fraction of this. ICIJ's OCCRP network would integrate immediately.

---

## 2. Document Intelligence Layer

**The idea:** Prozorro contains structured fields, but the real intelligence is buried in attached PDFs — technical specifications, contract amendments, evaluation reports. These documents are almost entirely unanalyzed.

**What to build:**
- OCR + extraction pipeline for procurement PDFs (specs, justifications, tender modifications)
- Fine-tuned LLM (Mistral or LLaMA on Ukrainian-language procurement corpus) to extract:
  - Specification lock-in signals ("must have X brand" disguised in technical language)
  - Last-minute scope changes (a classic corruption vector — same winner, inflated contract)
  - Abnormal technical requirements that perfectly match one known vendor
- Alert when a specification's language has >N% lexical overlap with a prior winning bid's technical offer — implies the spec was written *for* the winner

**Why this is a moat:** No one has trained a procurement-specific Ukrainian NLP model. The training data is the moat. Every document you process makes the model better, and competitors cannot replicate your dataset.

**VC signal:** This is the difference between flagging *that* something is suspicious and explaining *how* the fraud was engineered. Journalists and prosecutors pay for the "how."

---

## 3. Reconstruction Fund Intelligence

**The idea:** Ukraine's post-war reconstruction is a $500B+ opportunity — and a $500B+ corruption risk. The World Bank, EU, USAID, EBRD, and dozens of bilateral donors are deploying capital that flows through procurement. They have a fiduciary obligation to monitor it and currently have no good tool.

**What to build:**
- Map every international reconstruction grant/loan to the specific Prozorro tenders it funds
- Track whether reconstruction funds flow to contractors with high risk scores or beneficial ownership connections to politically exposed persons
- Generate donor-ready compliance reports (formatted for World Bank procurement guidelines, EU cohesion fund rules)
- Provide API access directly to donor monitoring teams embedded in Kyiv

**Why this is a moat:** This is a *B2B2G* revenue model with institutional lock-in. Once a World Bank procurement monitoring team is running on your data, switching costs are enormous.

**VC signal:** The reconstruction TAM is larger than any other emerging market procurement story in a generation. Position Grigori as the audit infrastructure layer before the money flows — not after.

---

## 4. Cross-Border Expansion — The "Prozorro Stack" for Other Countries

**The idea:** Prozorro is the world's most advanced public procurement system. Moldova, Georgia, and North Macedonia have adopted variants of it (ProZorro.sale, eMDS, e-PS). They have the same transparency mandate and zero analytical tooling.

**What to build:**
- Abstract the data ingestion layer to support multiple ProZorro-variant APIs
- Each country gets its own entity graph, risk model calibration, and regional alert feed
- Single multi-tenant platform — one engineering team, multiple country revenue streams
- Partner with local civil society organizations in each country as distribution channels (they have the journalist relationships and government trust)

**Why this is a moat:** First-mover in each country creates a reference database no competitor can replicate from scratch. The entity graph for each country is a 2–3 year minimum build.

**VC signal:** EU accession candidates (Ukraine, Moldova, Georgia, Western Balkans) all have procurement transparency as a Chapter 5 compliance requirement. The EU is paying for this work — Grigori becomes the technical standard.

---

## 5. Predictive Intelligence — Flag Corruption *Before* Award

**The idea:** Currently every tool in this space is reactive — they analyze what already happened. The real value is flagging a tender *during* the bidding phase, before the contract is awarded.

**What to build:**
- Real-time webhook listener on Prozorro's change feed (they publish it)
- At tender publication, immediately score it using:
  - Historical win-rate of the likely winner (based on spec similarity to prior tenders)
  - Buyer's historical single-bidder rate
  - CPV code risk profile
  - Whether the tender window is abnormally short (a common trick to exclude competitors)
- Publish a "pre-award risk score" that investigators can act on *while the tender is live*

**Why this is a moat:** Post-hoc analysis is a commodity. Real-time pre-award intelligence requires a trained model, a live data pipeline, and years of labeled historical outcomes to validate predictions against. This is not replicable quickly.

**VC signal:** This is the difference between a forensics tool and a prevention tool. Prevention tools command 3–5x the pricing of forensics tools in enterprise compliance markets.

---

## 6. Collaborative Investigation Network

**The idea:** Journalists, NGOs, and government auditors are all independently investigating the same entities and often duplicating work without knowing it. Grigori can become the coordination layer.

**What to build:**
- Private "investigation workspaces" — teams can annotate contractors, add notes, attach documents, share findings internally
- Anonymous tip submission portal — whistleblowers inside procurement agencies submit documents or information; Grigori enriches and routes to verified journalists
- OSINT integration layer — connect Grigori entity profiles to company records in OpenCorporates, LinkedIn scrapers, property registries
- Cross-organization alert sharing: two separate newsrooms investigating the same contractor are optionally notified (privacy-preserving, opt-in)

**Why this is a moat:** This is a pure network effect. The more journalists and NGOs who use it, the more tips come in, the more investigations succeed, the more press coverage, the more credibility, the more users. This loop is impossible to break once established.

**VC signal:** OCCRP, Bellingcat, Transparency International, and regional investigative outlets are the distribution channel. They have the audience. Grigori provides the infrastructure.

---

## 7. Institutional API + Compliance-as-a-Service

**The idea:** Every international bank doing business in Ukraine, every private equity firm investing in reconstruction, every law firm advising on Ukrainian M&A has a KYC and anti-corruption compliance obligation. They currently do this manually or with generic tools like Refinitiv World-Check.

**What to build:**
- REST API: `GET /api/v1/entity/{edrpou}/risk-report` returns a full JSON risk profile, beneficial ownership chain, sanction exposure, and historical procurement flags
- White-label compliance reports (PDF) formatted for AML/KYC workflows
- Webhook alerts: "notify me if any entity in my portfolio receives a new high-risk flag"
- SOC 2 Type II certified, GDPR-compliant data handling (required for EU institutional clients)

**Why this is a moat:** Refinitiv World-Check has zero Ukraine procurement intelligence. Sayari Analytics covers some beneficial ownership but not the Prozorro graph. There is a genuine gap in the institutional compliance market that Grigori can own.

**VC signal:** B2B SaaS compliance API pricing is $50K–$500K/year per institutional client. Ten law firm or bank clients is a Series A story on its own.

---

## 8. The "Ukraine Reconstruction Score" — A Public Index

**The idea:** Publish a free, public, monthly Reconstruction Integrity Index — a ranked transparency score for each oblast (region) and each major procurement category. Make it the authoritative public reference cited by journalists and donors.

**Why this matters strategically:**
- Free press coverage every month when the index updates
- Positions Grigori as the neutral, authoritative source (not a vendor, a standard)
- Embeds Grigori's brand in every donor report, every news story, every government accountability discussion
- Creates a pipeline of institutional clients who want access to the underlying data

**VC signal:** This is the "Corruption Perceptions Index" strategy — Transparency International's CPI generates more institutional trust and deal flow for TI than any paid product ever could. Public credibility is a compounding asset.

---

## Summary: The Moat Stack

| Layer | Moat Type | Replication Time |
|---|---|---|
| Beneficial Ownership Graph | Data + ML | 3–5 years |
| Document Intelligence (NLP) | Proprietary model + training data | 2–4 years |
| Reconstruction Fund Mapping | Institutional relationships | 2–3 years |
| Cross-Border Entity Graph | Data network effects | Per-country: 2–3 years |
| Pre-Award Predictive Scoring | Labeled training data | 3+ years |
| Investigation Network | User network effects | Compounds with time |
| Institutional API | Distribution + compliance trust | 1–2 years + certifications |
| Public Index | Brand + credibility | Cannot be bought |

No single competitor can replicate all of these simultaneously. Each layer reinforces the others: the graph feeds the NLP, the NLP feeds the predictive model, the predictive model feeds the investigation network, the network feeds the graph with new data.

---

## The Pitch in One Sentence

> *Grigori is the intelligence infrastructure for public money in emerging markets — the layer that donors, governments, journalists, and compliance teams rely on to know where the money went and who took it.*

---

*Prepared for internal strategic planning. Not for distribution.*
