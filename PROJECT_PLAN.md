# JobPulse — Job Market Trend Intelligence Platform

**Goal:** Scrape job postings from LinkedIn and other portals → build a labeled dataset → train/apply ML models → surface monthly rankings (in-demand roles, resume keywords HRs notice, top technologies, top languages, top soft skills) on a simple website.

**Profile this doc is built for:** solo builder, beginner in ML (comfortable with basic Python), ~20+ hrs/week, MVP-first. Learning is a first-class goal, so the timeline includes dedicated learning time, not just build time.

---

## 1. Reality check before building anything

Three things will bite you if skipped:

1. **LinkedIn scraping violates its ToS** and LinkedIn actively fingerprints/blocks scrapers (they've sued scrapers before — see *hiQ v. LinkedIn*, which is more nuanced than "scraping is legal" headlines suggest). Building your own scraper against LinkedIn specifically is the highest-risk, highest-maintenance part of this whole project — the DOM changes, CAPTCHAs pop up, and IPs get banned.
   - **Free alternatives** (paid data-as-a-service like Bright Data is off the table under the zero-cost constraint). Scope is **global**, with a dedicated **remote-jobs segment**:
     - **Adzuna API** (primary) — free developer tier, no card, and it operates in ~20 countries (US, UK, India, Germany, Australia, Canada, Brazil, ...) through one API with a country parameter. This single source powers all country-comparison insights. Bonus: it returns salary data for many postings.
     - **Jooble API** — global aggregator (60+ countries), free API key via email.
     - **Careerjet API** — global aggregator (90+ countries), free.
     - **Arbeitnow API** — fully free, no key, Europe-focused; useful for the Europe slice.
     - **Remotive / RemoteOK / Jobicy APIs** — free feeds of remote jobs worldwide, with company-location metadata → powers the remote section ("top countries hiring remote", etc.).
     - **HN "Who is hiring?"** monthly threads — free, text-rich, mostly US/remote tech; side source for NLP practice.
     - **Not available free:** LinkedIn, Indeed (API effectively closed to new developers), Naukri, Glassdoor.
     - **Public pre-scraped datasets** to bootstrap the model *before* live data accumulates: Kaggle has free "LinkedIn Job Postings" and country-specific job datasets already cleaned.
   - **Recommendation for MVP:** Adzuna (2-3 countries to start) + Remotive + a Kaggle seed dataset (zero legal ambiguity, zero anti-bot fighting, zero cost), get the whole pipeline working end-to-end, then widen to more countries and sources. The *trends* are what matter, and aggregators carry the same skill/technology signal as the big-name boards.

2. **"Train a model" is doing a lot of work in your description.** For ranking "top technologies mentioned this month," you don't need a trained model at all — you need *structured extraction* (pull technology/skill/soft-skill mentions out of free text) followed by *counting and ranking*. The ML happens in the extraction step, not in the ranking step. Keep this distinction clear — it changes what you build.

3. **Two viable extraction approaches — pick based on what you want to learn:**
   - **Path A (fast, ships MVP in days, $0):** rule-based extraction with spaCy's `EntityRuler` — a big curated list of known technologies/languages/soft-skills matched against each posting (seed the list from GitHub's free `skills`/`awesome` lists and Stack Overflow survey tag lists). Zero ML, zero API cost, works surprisingly well for ranking purposes because rankings only need counts, not perfect recall. Optionally augment with a **free-tier hosted LLM** for structured extraction — Google Gemini API and Groq both have genuinely free tiers (rate-limited, fine for a few thousand postings processed slowly) — or a **local LLM via Ollama** (free, runs on your own machine, no limits; needs ~8GB RAM for small models). Never a paid API.
   - **Path B (slower, teaches real ML):** trained extraction with custom NER + embeddings + clustering, described in §5. This is the "learn ML" path. Also entirely free — all libraries are open source and run on CPU.
   - **Recommendation:** do Path A (EntityRuler) first to get the website and rankings live fast, then build Path B as your ML-learning project. Both paths share the same downstream ranking/website code, so nothing is wasted.

---

## 2. Insight questions the dashboard will answer

Brainstormed list of everything the site could eventually show. ✅ = possible with the free sources above; ⚠️ = partially possible / data is thin; each marked MVP or Later.

### Core rankings (the original idea) — all MVP
- ✅ Which professions/roles are companies hiring for most this month? [RANK]
- ✅ Top technologies in demand [RANK]
- ✅ Top programming languages in demand [RANK]
- ✅ Top soft skills in demand [RANK]
- ✅ Keywords HRs/companies ask for most (resume-building signal) [RANK]

### Remote work section — MVP-lite, grows Later
- ✅ Top countries whose companies are hiring remote workers
- ✅ Top remote-friendly roles and technologies (do remote jobs want different skills than onsite?)
- ✅ Remote vs onsite share of postings, trending over months
- ⚠️ Which countries' *candidates* remote jobs are open to (only when postings state timezone/region restrictions — parseable from text sometimes)

### Country comparison — Later (needs a few countries' data accumulated)
- ✅ Top skills per country — e.g. what US postings want vs Germany vs India
- ✅ Which country's job volume is growing fastest in a given role
- ✅ "Where should a React dev look?" — country ranking for a chosen skill

### Trends over time — Later (needs 2-3 months of history minimum)
- ✅ Fastest-growing skills this quarter (emerging tech radar)
- ✅ Declining skills (what's fading out)
- ✅ Rank movement arrows month-over-month (↑3, ↓1) on every ranking

### Money — Later
- ✅ Average advertised salary by role / technology / country (Adzuna returns salary for many postings)
- ✅ Which skills correlate with higher advertised salaries
- ⚠️ Salary trends over time (needs months of history + careful normalization across currencies)

### Smart/derived insights — Later, the fun ML ones
- ✅ Skill co-occurrence: "postings asking React usually also ask TypeScript + Next.js" → "if you learn X, also learn Y" recommendations
- ✅ Skill baskets per role: the typical stack a "Data Engineer" posting expects
- ✅ Seniority mix: junior vs mid vs senior demand per role (are companies hiring freshers for X?)
- ✅ Emerging-theme detection via topic modeling: clusters of terms that didn't exist 3 months ago
- ⚠️ Certifications in demand (AWS/GCP certs etc. — parseable from text, mention rate is low but real)
- ⚠️ Contract vs full-time mix (depends on source metadata quality)

Rule of thumb baked into the plan: **MVP ships the Core rankings + a basic Remote section; everything else layers on without pipeline changes** because they're all just different aggregations over the same extracted data.

## 3. Architecture (target end-state)

```
[Sources: Adzuna(multi-country)/Jooble/Careerjet/Remotive free APIs + Kaggle seed]
                    │
                    ▼
        [Ingestion jobs — scheduled, idempotent]
                    │
                    ▼
     [Raw store: SQLite table `raw_postings` (JSON column)]
                    │
                    ▼
   [Cleaning: dedupe, normalize dates, strip HTML, language filter]
                    │
                    ▼
     [Extraction layer: EntityRuler rules (Path A) OR NER+embeddings (Path B)]
                    │
                    ▼
   [Structured store: SQLite tables — postings, skills, technologies,
                       soft_skills, roles, seniority — normalized/joined]
                    │
                    ▼
   [Aggregation: monthly rollups, ranking, trend deltas vs prior month]
                    │
                    ▼
        [Frontend: Streamlit dashboard reading SQLite directly —
         rankings, charts, month picker. (FastAPI layer optional, later)]
```

---

## 4. Tech stack

Every row below is $0 — open-source software running on your own machine, or a service with a real permanent free tier (not a trial).

| Layer | Recommendation | Cost | Why |
|---|---|---|---|
| Language | Python 3.11+ | Free | Best ML/NLP ecosystem, one language for whole backend |
| Ingestion | `httpx` + free job APIs (Adzuna multi-country, Jooble, Careerjet; Remotive/RemoteOK for the remote segment) | Free | No scraper to build or maintain, no ToS risk |
| Scheduling | **GitHub Actions cron** (free & unlimited minutes on public repos) — runs ingestion weekly, commits updated data to the repo | Free | Your laptop doesn't need to stay on; no server needed at all |
| Storage | **SQLite** (a single file in your repo) | Free | Zero hosting, zero setup, plenty for this data volume; you learn the same SQL. Postgres only if you later outgrow it (Supabase/Neon free tiers exist) |
| Data wrangling | `pandas`, `pydantic` | Free | Standard, well-documented |
| Extraction (Path A) | spaCy `EntityRuler` rules; optionally Gemini API free tier / Groq free tier / local Ollama for LLM-assisted extraction | Free | Rule-based costs nothing and needs no training; free LLM tiers are rate-limited but fine at this scale |
| ML/NLP (Path B) | `spaCy`, `sentence-transformers`, `scikit-learn`, `hdbscan` | Free | All open source, all run on CPU — no GPU, no cloud training |
| Topic modeling (stretch) | `BERTopic` | Free | Open source, CPU-friendly at this scale |
| Frontend + hosting | `Streamlit` app deployed on **Streamlit Community Cloud** (permanent free hosting for public repos) — it reads the SQLite file straight from the repo, so you don't even need a separate API server for MVP | Free | Pure Python, free hosting, zero JavaScript, zero servers to pay for |
| API backend (later, optional) | `FastAPI` — only if/when you outgrow Streamlit-reads-SQLite; host free on Render's free tier or Hugging Face Spaces | Free | Not needed for MVP; add it as a learning step, not a requirement |
| Model hosting (Path B) | Run locally; if you want the trained models used in the deployed app, ship them in the repo or on Hugging Face Hub (free) | Free | Models here are small (spaCy NER ~10-50MB, MiniLM ~90MB) |

**The one trap to watch:** many "free tier" clouds (Railway, Heroku, some Render plans) are actually time-limited trials or require a credit card. The stack above deliberately avoids anything that asks for a card. GitHub (public repo) + Streamlit Community Cloud + SQLite is a genuinely $0-forever combination.

---

## 5. ML concepts you'll learn (in the order you'll hit them)

You're starting from beginner ML, so this is ordered as a learning path where each concept unlocks the next project step. The pattern for each: **learn just enough → apply it to your own data immediately**. Working on your own scraped postings beats any course dataset for retention.

### Stage 0 — Foundations (learn before/during Phase 1)
1. **Python data stack basics** — `pandas` (loading, filtering, groupby), reading/writing JSON and CSV. You'll use this daily for every later step. *Resource: pandas "10 minutes to pandas" + just doing Phase 1 with it.*
2. **What "training a model" actually means** — features, labels, train/test split, overfitting. One conceptual pass through Google's free Machine Learning Crash Course (first 3 modules) is enough to start; the project makes it concrete later.

### Stage 1 — Working with text (Phase 2)
3. **Text preprocessing** — tokenization, stopword removal, lemmatization (`spaCy`). Your first hands-on NLP step: turn a messy job description into clean tokens.
4. **TF-IDF & bag-of-words** — the beginner-friendly answer to "which words matter in this document?" No neural nets involved — it's just counting with a smart weighting formula. Great first win: run TF-IDF over your postings and watch real skills float to the top.

### Stage 2 — Extraction (Phase 3, the core "trained model" piece)
5. **Named Entity Recognition (NER)** — teaching a model to tag "Kubernetes" as a TECHNOLOGY inside free text. Start with spaCy's rule-based `EntityRuler` (a big list of known skills — zero ML, works surprisingly well), then graduate to training spaCy's statistical NER on top. This progression *is* the ML lesson: you'll feel exactly where rules stop working and learning takes over.
6. **Hand-labeling data** — unglamorous but foundational: you'll label 100-200 postings yourself to create a validation set. Every ML practitioner learns more from an afternoon of labeling than a week of lectures.

### Stage 3 — Making messy text canonical (Phase 4)
7. **Embeddings** — `sentence-transformers` turns text into vectors where similar meanings land close together ("JS" near "JavaScript"). You don't need to understand transformer internals to *use* embeddings — treat the model as a black box that maps text → coordinates, and learn the internals later if curious.
8. **Clustering (KMeans / HDBSCAN)** — your first unsupervised ML: group skill-mention vectors into canonical buckets with no labels needed. You'll learn to pick cluster counts and eyeball whether clusters make sense.

### Stage 4 — Classification (Phase 5)
9. **Text classification** — your first supervised model end-to-end: TF-IDF features + Logistic Regression to sort postings into role families ("Data Scientist" vs "Data Engineer") and seniority. This is the classic beginner ML pipeline and it's genuinely how you learn train/test/evaluate for real. Upgrading to a fine-tuned transformer (`DistilBERT`) is an optional later step — do it only after the simple version works and you can measure whether it's actually better.
10. **Evaluation** — precision/recall/F1 against your hand-labeled set. Learn why accuracy alone lies to you on imbalanced data.

### Stage 5 — Stretch goals (Phase 6+, only after the above feels comfortable)
11. **Topic modeling (BERTopic)** — let the model surface skill themes you didn't predefine; useful for catching emerging trends.
12. **Basic trend analysis** — month-over-month rank deltas, moving averages. More stats than ML, but it's what makes "trending up" claims defensible instead of noise.

Explicitly **not** needed for this project (common rabbit holes that will stall a beginner): deep learning from scratch, building your own transformer, GPU training infrastructure, RNN/LSTM, reinforcement learning, math-heavy theory before touching code. Depth-first courses can come later; this project is breadth-first with immediate application.

---

## 6. Suggested timeline (solo, ~20+ hrs/week)

Durations include learning time (roughly half of each ML phase is learning the concept, half is applying it). Don't compress the learning halves — that's the point of the project.

| Phase | Work | Duration |
|---|---|---|
| 0 | Setup: Python env, Git, SQLite basics, repo skeleton; get one free API pulling real postings. Learn: pandas basics (Stage 0) | 1 week |
| 1 | Ingestion pipeline for 2-3 free sources, dedupe/clean, land ~2-5k postings. Learn: ML crash-course concepts alongside | 1.5 weeks |
| **MVP extraction (Path A)** | EntityRuler rule-based extraction + monthly aggregation/ranking logic | 1 week |
| **MVP site** | Streamlit dashboard showing the 5 rankings from your idea, deployed free on Streamlit Community Cloud | 1.5 weeks |
| **→ MVP live** | | **~5 weeks total** |
| 2 | Learn text preprocessing + TF-IDF (Stage 1); run TF-IDF analysis over your real postings | 1.5 weeks |
| 3 | Learn + build NER extraction: EntityRuler first, then trained spaCy NER; hand-label validation set (Stage 2) | 2.5-3 weeks |
| 4 | Learn + apply embeddings and clustering for canonical skill normalization (Stage 3) | 1.5-2 weeks |
| 5 | First supervised classifier: role/seniority via TF-IDF+LogReg; evaluation against labeled set (Stage 4) | 2 weeks |
| 6 | Swap Path B extraction into the pipeline, compare quality vs Path A | 1 week |
| 7 | Stretch: topic modeling, trend-delta polish, scheduling automation, dashboard polish, deploy | 2 weeks |
| **→ Full pipeline with real trained models** | | **~15-16 weeks total (~4 months)** |

LinkedIn-shaped data comes from free Kaggle datasets only — live LinkedIn ingestion is out of scope under the zero-cost constraint (the compliant feeds are paid, and DIY scraping is a ToS/blocking fight not worth having).

---

## 7. Suggested repo structure

```
jobpulse/                # one public GitHub repo (public = free CI + free hosting)
  ingestion/            # API clients per source
  extraction/
    rules/              # Path A: EntityRuler patterns, curated skill/tech lists
    nlp/                # Path B: spaCy pipeline, embeddings, clustering, classifiers
  aggregation/          # ranking + trend-delta logic
  app/                  # Streamlit dashboard
  data/
    seed/               # Kaggle bootstrap datasets
    jobpulse.db         # SQLite — updated by the scheduled GitHub Action
  notebooks/            # exploration, model evaluation
  .github/workflows/
    ingest.yml          # weekly cron: pull APIs -> extract -> aggregate -> commit db
```

Note the repo must be **public** for the free tiers to apply (unlimited GitHub Actions minutes and Streamlit Community Cloud both require it). That's fine here — nothing in this project is secret, and a public repo doubles as your portfolio piece.

---

## 8. Future-proofing: retraining on live data

The pipeline is designed so that models can be retrained on incoming live data forever, without re-architecting. Four rules make this work:

1. **Never delete raw data.** `raw_postings` keeps every posting ever ingested, with `source` and `ingested_at` stamps. Training data compounds weekly on its own — in a year the dataset is ~50x the MVP's. Storage is trivial (text is small; SQLite handles millions of rows).
2. **Extraction is a swappable interface.** Every extractor — rules (Path A), trained NER (Path B), anything future — implements the same contract: `extract(posting_text) -> {technologies, languages, soft_skills, role, seniority}`. Downstream (aggregation, dashboard) never knows which version produced the data. Swapping in a better model is a one-line change.
3. **Scheduled retraining loop (free, on GitHub Actions):** monthly job → pull accumulated raw postings → retrain NER/classifier → **evaluate against the frozen hand-labeled validation set** → if new model beats current model's F1, publish it (Hugging Face Hub, free) and bump the version the pipeline uses; else keep the old one. Models never silently get worse — this gate is what makes auto-retraining safe.
4. **Version everything:** `model_version` and `extractor_version` columns on extracted rows, so any ranking on the site can be traced to exactly which model produced it, and historical months can be re-extracted with newer models for consistency.

This is a miniature MLOps loop (data versioning → scheduled retraining → evaluation gate → model registry → deployment) — the same shape as production systems, which also makes it a strong resume/interview talking point.

## 9. Open decisions worth revisiting once MVP is live

- Refresh cadence: weekly vs monthly ingestion — with rule-based extraction there's no per-posting cost, so this is purely about freshness vs noise (weekly data is noisier; monthly rankings are the actual product).
- How far back to keep raw postings (storage cost vs ability to backfill trend history).
- Whether "soft skills HRs are noticing in resumes" is derived from job *postings* (what they ask for) or would need actual resume data (a much harder, more sensitive data source to acquire — recommend deriving this from postings language only, e.g. "communication," "stakeholder management" mentions, not from real resumes).
