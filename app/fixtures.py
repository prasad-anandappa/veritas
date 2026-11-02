"""Bundled fixture corpus for deterministic offline (mock) mode.

These documents are SYNTHETIC demo data, written for this project so the
whole pipeline — planning, search, extraction, scoring, synthesis,
verification — can run and be tested with zero API keys. They are clearly
hosted on ``.example`` domains so nobody mistakes them for live sources.
In live mode the same pipeline runs against real Tavily results instead;
no pipeline code changes.
"""
from __future__ import annotations

# Each doc: title, url, published_date, keywords (mock-search matching),
# content (the "extracted" full text the verification pass checks against).
CORPUS: list[dict] = [
    # ---- Solid-state batteries -------------------------------------------
    {
        "title": "Solid-State Batteries Move From Lab to Pilot Lines",
        "url": "https://energy-storage-review.example/solid-state-pilot-lines-2026",
        "published_date": "2026-09-14",
        "keywords": ["solid-state", "battery", "batteries", "ev", "electric", "vehicle", "vehicles", "lithium"],
        "content": (
            "Solid-state batteries replace the flammable liquid electrolyte of a lithium-ion cell "
            "with a solid ceramic or sulfide layer. Pilot production lines in Japan and South Korea "
            "began shipping sample cells to carmakers in 2026. The best sample cells reach an energy "
            "density of about 500 watt-hours per kilogram, roughly double a conventional lithium-ion "
            "cell. Carmakers say the first production electric vehicles using solid-state cells are "
            "targeted for 2027 and 2028. Cost remains the main barrier, with pilot cells costing "
            "several times more per kilowatt-hour than mass-produced lithium-ion cells."
        ),
    },
    {
        "title": "Why Solid-State Cells Are Hard to Manufacture",
        "url": "https://advanced-materials-journal.example/solid-state-manufacturing-challenges",
        "published_date": "2026-06-02",
        "keywords": ["solid-state", "battery", "batteries", "manufacturing", "challenges", "dendrite", "yield"],
        "content": (
            "Manufacturing solid-state batteries at scale is difficult for three reasons. First, the "
            "solid electrolyte layer cracks when cells expand and contract during charging. Second, "
            "lithium dendrites can still grow through ceramic electrolytes at high charging rates, "
            "causing short circuits. Third, pilot-line yields remain low, with some factories "
            "reporting that fewer than half of finished cells pass quality checks. Engineers are "
            "addressing these problems with stack pressure systems and thinner electrolyte layers. "
            "Most analysts expect meaningful production volumes only after 2028."
        ),
    },
    {
        "title": "Government Lab Reports Solid-State Cycle-Life Milestone",
        "url": "https://national-energy-lab.example/news/solid-state-cycle-life-2026",
        "published_date": "2026-10-05",
        "keywords": ["solid-state", "battery", "batteries", "cycle", "life", "research", "government", "lab"],
        "content": (
            "A government research laboratory reported a solid-state cell that retained 90 percent "
            "of its capacity after 1000 full charge cycles. The result was achieved with a sulfide "
            "electrolyte and a lithium-metal anode at room temperature. Independent experts called "
            "the cycle life a milestone because earlier solid-state prototypes often failed before "
            "400 cycles. The laboratory cautioned that the cells were small pouch prototypes, not "
            "full-size automotive packs. The team published its methods so other laboratories can "
            "replicate the result."
        ),
    },
    {
        "title": "EV Makers Hedge With Semi-Solid Batteries First",
        "url": "https://ev-industry-weekly.example/semi-solid-hedge-2026",
        "published_date": "2026-08-19",
        "keywords": ["solid-state", "battery", "batteries", "ev", "electric", "semi-solid", "vehicle"],
        "content": (
            "Several electric vehicle makers are shipping semi-solid batteries as a stepping stone "
            "while full solid-state cells mature. Semi-solid designs keep a small amount of liquid "
            "electrolyte, which makes them easier to manufacture on existing lines. Cars using "
            "semi-solid packs advertise ranges above 900 kilometres on a single charge in Chinese "
            "testing cycles. Industry forecasts suggest semi-solid cells will hold a small but "
            "growing share of the premium electric vehicle market through 2030. Full solid-state "
            "cells are still expected to win on energy density once yields improve."
        ),
    },
    # ---- Fusion energy ----------------------------------------------------
    {
        "title": "Fusion Reactor Sustains Record Plasma for 22 Minutes",
        "url": "https://plasma-physics-today.example/fusion-record-plasma-2026",
        "published_date": "2026-07-21",
        "keywords": ["fusion", "plasma", "tokamak", "reactor", "energy", "record"],
        "content": (
            "A tokamak reactor sustained a high-performance plasma for 22 minutes, setting a new "
            "duration record for its class of device. During the run the plasma reached temperatures "
            "above 100 million degrees Celsius. Sustained operation matters because a power plant "
            "must run continuously, not in short pulses. The experiment did not produce net "
            "electricity, and the reactor consumed more power than the plasma generated. Engineers "
            "said the run validated new tungsten wall components designed to survive years of heat."
        ),
    },
    {
        "title": "Private Fusion Companies Race Toward Net Energy",
        "url": "https://energy-storage-review.example/private-fusion-race-2026",
        "published_date": "2026-05-11",
        "keywords": ["fusion", "energy", "private", "startup", "net", "investment", "power"],
        "content": (
            "Private fusion companies have raised more than 7 billion dollars in investment "
            "worldwide. Several startups promise demonstration reactors that produce more energy "
            "than they consume before 2030. Their designs rely on high-temperature superconducting "
            "magnets, which allow smaller and cheaper reactors than earlier generations. Skeptics "
            "note that no private reactor has yet achieved net energy gain. Governments continue "
            "to fund large public projects in parallel with the private race."
        ),
    },
    {
        "title": "What Still Stands Between Fusion and the Grid",
        "url": "https://national-energy-lab.example/analysis/fusion-grid-challenges",
        "published_date": "2026-03-27",
        "keywords": ["fusion", "energy", "grid", "challenges", "tritium", "materials", "outlook"],
        "content": (
            "Three obstacles stand between fusion experiments and grid power. Reactor walls must "
            "survive intense neutron bombardment for years without becoming brittle. The tritium "
            "fuel cycle must breed more tritium than the reactor burns, which has never been "
            "demonstrated at scale. Finally, the cost per megawatt must fall enough to compete "
            "with fission, solar, and storage. Most roadmaps place the first fusion pilot plants "
            "in the 2030s. Even optimistic timelines do not expect fusion to supply a large share "
            "of electricity before 2050."
        ),
    },
    # ---- GLP-1 medicines ---------------------------------------------------
    {
        "title": "GLP-1 Drugs Show Benefits Beyond Weight Loss in Large Trial",
        "url": "https://medical-evidence-review.example/glp1-outcomes-trial-2026",
        "published_date": "2026-09-30",
        "keywords": ["glp-1", "semaglutide", "ozempic", "weight", "loss", "diabetes", "obesity", "drug", "trial"],
        "content": (
            "A large clinical trial found that GLP-1 medicines reduced major cardiovascular events "
            "by about 20 percent in patients with obesity and heart disease. Participants lost an "
            "average of 15 percent of their body weight over 68 weeks of treatment. The same trial "
            "reported slower progression of chronic kidney disease in patients with type 2 diabetes. "
            "Common side effects included nausea and vomiting, which caused about 10 percent of "
            "participants to stop treatment. Researchers cautioned that weight typically returns "
            "after patients stop taking the medicine."
        ),
    },
    {
        "title": "Oral GLP-1 Pills Aim to Replace Weekly Injections",
        "url": "https://pharma-development-digest.example/oral-glp1-pills-2026",
        "published_date": "2026-08-08",
        "keywords": ["glp-1", "oral", "pill", "semaglutide", "weight", "drug", "injection"],
        "content": (
            "Drug makers are racing to replace weekly GLP-1 injections with a daily pill. In a "
            "phase 3 trial, an oral GLP-1 pill produced average weight loss of about 11 percent "
            "over 64 weeks. Pills are cheaper to manufacture and do not require refrigeration, "
            "which could expand access in lower-income countries. The pill must be taken on an "
            "empty stomach, and food reduces its absorption sharply. Analysts expect the first "
            "oral approvals for obesity treatment in 2026 or 2027."
        ),
    },
    {
        "title": "Insurers Wrestle With the Cost of Covering GLP-1 Drugs",
        "url": "https://health-policy-forum.example/glp1-coverage-cost-2026",
        "published_date": "2026-04-15",
        "keywords": ["glp-1", "cost", "insurance", "coverage", "obesity", "drug", "price"],
        "content": (
            "List prices for GLP-1 obesity medicines exceed 1000 dollars per month in the United "
            "States. Insurers say covering the drugs for every eligible patient would consume a "
            "large share of pharmacy budgets. Some employers have dropped coverage, while others "
            "require patients to try cheaper therapies first. Economists argue that preventing "
            "diabetes and heart disease could offset part of the cost over time. Negotiated prices "
            "have begun to fall as competing products enter the market."
        ),
    },
    # ---- Research agents / AI (default topic) ------------------------------
    {
        "title": "Research Agents That Cite Their Sources Earn More Trust",
        "url": "https://ai-systems-review.example/research-agents-citations-2026",
        "published_date": "2026-10-12",
        "keywords": ["research", "agent", "agents", "ai", "citation", "citations", "sources", "llm"],
        "content": (
            "Research agents combine web search with language models to answer questions with "
            "citations. Studies of user trust find that answers with inline citations to retrieved "
            "sources are rated more trustworthy than uncited answers. However, citation alone is "
            "not enough, because models sometimes cite sources that do not support the claim. "
            "Verification passes that check each claim against its cited excerpt catch many of "
            "these unsupported statements. Systems that drop or flag unsupported claims produce "
            "measurably more accurate reports."
        ),
    },
    {
        "title": "How Retrieval Quality Limits Research Agent Accuracy",
        "url": "https://ai-systems-review.example/retrieval-quality-limits-2026",
        "published_date": "2026-06-25",
        "keywords": ["research", "agent", "agents", "ai", "retrieval", "search", "accuracy", "sources"],
        "content": (
            "The accuracy of a research agent is limited by the quality of the sources it "
            "retrieves. Duplicate and near-duplicate pages can crowd out independent evidence, "
            "which is why deduplication matters. Scoring sources by authority and recency improves "
            "answer quality compared with raw search ranking alone. Extracting full page text, "
            "rather than relying on short snippets, gives the verification step more evidence to "
            "check claims against. Evaluations show these pipeline steps matter as much as the "
            "choice of language model."
        ),
    },
    {
        "title": "Open Models Reach Parity for Structured Research Tasks",
        "url": "https://open-model-weekly.example/open-models-research-tasks-2026",
        "published_date": "2026-09-02",
        "keywords": ["open", "model", "models", "llm", "ai", "research", "inference"],
        "content": (
            "Open-weight language models now perform close to proprietary models on structured "
            "research tasks such as query planning and claim extraction. Serving these models "
            "through OpenAI-compatible inference APIs makes them drop-in replacements in agent "
            "pipelines. Cost per query is typically far lower than with proprietary APIs at "
            "similar quality. The remaining gaps appear mainly in long, ambiguous reasoning "
            "chains. For well-scoped research questions, evaluators found the difference in "
            "citation accuracy to be small."
        ),
    },
]

DEFAULT_TOPIC_HINT = (
    "No fixture documents matched that topic closely, so the mock corpus "
    "returned its general research-agent documents."
)
