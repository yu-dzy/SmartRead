"""PROTOTYPE ONLY.

Question: two variants of SmartRead's chapter-learning experience, switchable
with ?variant=, using fake prepared data only.

Run:
    streamlit run prototypes/smartread_chapter_learning/streamlit_app.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


VARIANTS = {
    "A": "Study console",
    "B": "Reading path",
}

BOOK = {
    "title": "The Compounding Practice",
    "author": "Mara Ellison",
    "chapter": "Chapter 4: Make Progress Visible",
    "chapter_progress": 0.42,
    "mastery_target": 0.8,
}

CITATIONS = {
    "C1": {
        "label": "p. 41",
        "location": "Page 41, paragraph 2",
        "excerpt": (
            "The first signal of durable change is not a dramatic result, but a "
            "visible trace that the learner returned to the practice today."
        ),
    },
    "C2": {
        "label": "p. 43",
        "location": "Page 43, paragraph 1",
        "excerpt": (
            "A scoreboard is useful only when it reduces doubt. It should show "
            "the next action, the current streak, and the smallest evidence of "
            "progress."
        ),
    },
    "C3": {
        "label": "p. 45",
        "location": "Page 45, paragraph 4",
        "excerpt": (
            "Reflection converts activity into learning. Without a short review, "
            "effort can feel productive while leaving the old pattern intact."
        ),
    },
    "C4": {
        "label": "p. 47",
        "location": "Page 47, paragraph 3",
        "excerpt": (
            "Friction is not always bad. The right kind of friction interrupts "
            "automatic behavior long enough for a better choice to become visible."
        ),
    },
    "C5": {
        "label": "p. 50",
        "location": "Page 50, paragraph 2",
        "excerpt": (
            "The learner who waits for motivation has made motivation the gate. "
            "The learner who designs a cue has made beginning the default."
        ),
    },
    "C6": {
        "label": "p. 52",
        "location": "Page 52, paragraph 5",
        "excerpt": (
            "A review queue should not punish forgetting. It should make the next "
            "small repair obvious while the idea is still recoverable."
        ),
    },
}

SUMMARY = [
    {
        "text": (
            "The chapter argues that visible progress changes how a learner "
            "interprets effort. A small trace of completion makes practice feel "
            "real before larger results appear."
        ),
        "citations": ["C1"],
    },
    {
        "text": (
            "The author warns that tracking can become vanity unless it points to "
            "the next useful action. A good scoreboard lowers doubt instead of "
            "creating pressure."
        ),
        "citations": ["C2"],
    },
    {
        "text": (
            "Reflection is framed as the mechanism that turns repeated action into "
            "learning. The chapter treats review as part of practice, not a bonus "
            "after practice."
        ),
        "citations": ["C3", "C6"],
    },
    {
        "text": (
            "The chapter distinguishes harmful friction from helpful friction. "
            "Helpful friction interrupts automatic behavior and makes the desired "
            "choice easier to notice."
        ),
        "citations": ["C4"],
    },
]

CONCEPTS = [
    {
        "id": "visible-progress",
        "name": "Visible Progress",
        "short": "Small traces that prove a learner returned to the practice.",
        "why": (
            "It helps the learner trust the process before outcomes are obvious."
        ),
        "example": "A daily mark beside a chapter, quiz, or concept review.",
        "citation": "C1",
    },
    {
        "id": "useful-scoreboard",
        "name": "Useful Scoreboard",
        "short": "A progress display that clarifies the next action.",
        "why": "It reduces uncertainty instead of becoming a vanity metric.",
        "example": "Showing one due review and the next unfinished chapter.",
        "citation": "C2",
    },
    {
        "id": "reflection-loop",
        "name": "Reflection Loop",
        "short": "A short review that converts effort into learning.",
        "why": "It reveals whether practice changed understanding or only consumed time.",
        "example": "Answering a concept question after reading a summary.",
        "citation": "C3",
    },
    {
        "id": "productive-friction",
        "name": "Productive Friction",
        "short": "A small interruption that makes better choices easier to see.",
        "why": "It breaks autopilot without making learning feel heavy.",
        "example": "A quick check before marking a chapter complete.",
        "citation": "C4",
    },
    {
        "id": "designed-cue",
        "name": "Designed Cue",
        "short": "A prompt that makes beginning the default action.",
        "why": "It reduces dependence on motivation.",
        "example": "Opening directly to the next unfinished chapter.",
        "citation": "C5",
    },
]

TAKEAWAYS = [
    {"text": "Make progress visible before results are impressive.", "citation": "C1"},
    {"text": "Track only what helps you choose the next action.", "citation": "C2"},
    {"text": "Treat reflection as part of practice.", "citation": "C3"},
    {"text": "Use light friction to interrupt autopilot.", "citation": "C4"},
    {"text": "Design cues so starting is easier than negotiating.", "citation": "C5"},
]

QUIZ = [
    {
        "id": "q1",
        "concept_id": "visible-progress",
        "question": "Why does the chapter value visible progress early in learning?",
        "options": [
            "It proves the learner is already an expert.",
            "It gives evidence of returning before major results appear.",
            "It removes the need for reflection.",
            "It replaces the need to practice consistently.",
        ],
        "answer": "It gives evidence of returning before major results appear.",
        "explanation": (
            "The chapter treats visible progress as evidence that the learner "
            "returned to the practice, even before larger outcomes are available."
        ),
        "citation": "C1",
    },
    {
        "id": "q2",
        "concept_id": "useful-scoreboard",
        "question": "A useful scoreboard should primarily do what?",
        "options": [
            "Make every metric public.",
            "Reduce doubt and clarify the next action.",
            "Show as many charts as possible.",
            "Reward only perfect streaks.",
        ],
        "answer": "Reduce doubt and clarify the next action.",
        "explanation": (
            "The chapter says a scoreboard is useful when it reduces doubt and "
            "shows the next action, not when it adds pressure."
        ),
        "citation": "C2",
    },
    {
        "id": "q3",
        "concept_id": "reflection-loop",
        "question": "True or false: reflection is optional once enough effort has been spent.",
        "options": ["True", "False"],
        "answer": "False",
        "explanation": (
            "The chapter argues that reflection is what converts activity into "
            "learning, so effort alone is not enough."
        ),
        "citation": "C3",
    },
    {
        "id": "q4",
        "concept_id": "productive-friction",
        "question": (
            "Which scenario best matches productive friction from the chapter?"
        ),
        "options": [
            "Hiding the next lesson until tomorrow.",
            "Adding a quick confidence check before marking a chapter complete.",
            "Making users reupload the book for every chapter.",
            "Removing review prompts so study feels faster.",
        ],
        "answer": "Adding a quick confidence check before marking a chapter complete.",
        "explanation": (
            "Productive friction interrupts autopilot just enough to make a better "
            "choice visible without blocking progress."
        ),
        "citation": "C4",
    },
    {
        "id": "q5",
        "concept_id": "designed-cue",
        "question": "What problem does a designed cue solve?",
        "options": [
            "It makes motivation unnecessary by making beginning easier.",
            "It guarantees every chapter will be remembered forever.",
            "It turns all learning into passive reading.",
            "It removes the need for citations.",
        ],
        "answer": "It makes motivation unnecessary by making beginning easier.",
        "explanation": (
            "The chapter contrasts waiting for motivation with designing a cue "
            "that makes the first step the default."
        ),
        "citation": "C5",
    },
]


def main() -> None:
    st.set_page_config(
        page_title="SmartRead Chapter Prototype",
        page_icon="SR",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    init_state()

    variant = get_variant()

    if variant == "A":
        render_variant_a()
    else:
        render_variant_b()

    render_variant_switcher(variant)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --sr-ink: #17201a;
            --sr-muted: #5b665e;
            --sr-line: #d9ded7;
            --sr-paper: #fbfcf8;
            --sr-surface: #ffffff;
            --sr-green: #2f6f4e;
            --sr-teal: #26727d;
            --sr-gold: #a06a1b;
            --sr-red: #a23e32;
        }

        .stApp {
            background:
                linear-gradient(180deg, #fbfcf8 0%, #f4f6ef 52%, #f7f3eb 100%);
            color: var(--sr-ink);
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--sr-line);
            background: #f7f8f3;
        }

        .sr-kicker {
            color: var(--sr-green);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
        }

        .sr-muted {
            color: var(--sr-muted);
        }

        .sr-panel {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid var(--sr-line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 8px 22px rgba(34, 44, 36, 0.05);
        }

        .sr-lesson-title {
            font-size: 2.8rem;
            line-height: 1.02;
            margin: 0.2rem 0 0.8rem;
        }

        .sr-micro {
            font-size: 0.82rem;
            color: var(--sr-muted);
        }

        .sr-concept-name {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.1rem;
        }

        .sr-rule {
            height: 1px;
            background: var(--sr-line);
            margin: 0.8rem 0 1rem;
        }

        .sr-status-ok {
            color: var(--sr-green);
            font-weight: 800;
        }

        .sr-status-miss {
            color: var(--sr-red);
            font-weight: 800;
        }

        .sr-path-step {
            border-left: 4px solid var(--sr-green);
            padding: 0.1rem 0 0.8rem 1rem;
            margin-bottom: 1rem;
        }

        .sr-cite-row {
            margin-top: -0.25rem;
            margin-bottom: 0.65rem;
        }

        div[data-testid="stButton"] > button {
            border-radius: 999px;
            border: 1px solid #c8d1c7;
            min-height: 2.15rem;
        }

        div[data-testid="stButton"] > button:hover {
            border-color: var(--sr-green);
            color: var(--sr-green);
        }

        .sr-switcher {
            position: fixed;
            left: 50%;
            bottom: 18px;
            transform: translateX(-50%);
            z-index: 99999;
            display: flex;
            align-items: center;
            gap: 0.7rem;
            padding: 0.58rem 0.7rem;
            border-radius: 999px;
            background: #162018;
            color: white;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.25);
            font: 14px/1.2 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .sr-switcher a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 2.25rem;
            height: 2.25rem;
            border-radius: 999px;
            color: #162018;
            background: #eef6ed;
            text-decoration: none;
            font-weight: 900;
        }

        .sr-switcher span {
            min-width: 12rem;
            text-align: center;
            font-weight: 750;
        }

        @media (max-width: 760px) {
            .sr-lesson-title {
                font-size: 1.9rem;
            }

            .sr-switcher {
                width: calc(100vw - 22px);
                justify-content: space-between;
            }

            .sr-switcher span {
                min-width: 0;
                font-size: 0.84rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    st.session_state.setdefault("selected_citation", "C1")
    for question in QUIZ:
        st.session_state.setdefault(answer_key(question["id"]), "Choose an answer")
        st.session_state.setdefault(submitted_key(question["id"]), False)


def get_variant() -> str:
    try:
        raw = st.query_params.get("variant", "A")
    except Exception:
        raw_params = st.experimental_get_query_params()
        raw = raw_params.get("variant", ["A"])[0]
    if isinstance(raw, list):
        raw = raw[0] if raw else "A"
    return raw if raw in VARIANTS else "A"


def previous_variant(current: str) -> str:
    keys = list(VARIANTS)
    return keys[(keys.index(current) - 1) % len(keys)]


def next_variant(current: str) -> str:
    keys = list(VARIANTS)
    return keys[(keys.index(current) + 1) % len(keys)]


def render_variant_switcher(current: str) -> None:
    if os.environ.get("SMARTREAD_PROTOTYPE_HIDE_SWITCHER") == "1":
        return

    prev_key = previous_variant(current)
    next_key = next_variant(current)
    label = f"{current}: {VARIANTS[current]}"
    st.markdown(
        f"""
        <div class="sr-switcher">
            <a aria-label="Previous variant" href="?variant={prev_key}">&lt;</a>
            <span>{label}</span>
            <a aria-label="Next variant" href="?variant={next_key}">&gt;</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        f"""
        <script>
        const variants = {json.dumps(list(VARIANTS.keys()))};
        const current = "{current}";
        function move(delta) {{
            const active = document.activeElement;
            if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) {{
                return;
            }}
            const index = variants.indexOf(current);
            const next = variants[(index + delta + variants.length) % variants.length];
            const url = new URL(window.parent.location.href);
            url.searchParams.set("variant", next);
            window.parent.location.href = url.toString();
        }}
        window.parent.document.addEventListener("keydown", (event) => {{
            if (event.key === "ArrowLeft") move(-1);
            if (event.key === "ArrowRight") move(1);
        }}, {{ once: false }});
        </script>
        """,
        height=0,
    )


def render_sidebar_state() -> None:
    correct = correct_count()
    answered = answered_count()
    missed = missed_questions()
    mastery = correct / len(QUIZ)

    st.sidebar.markdown("### SmartRead")
    st.sidebar.caption("Throwaway prototype. Fake prepared data only.")
    st.sidebar.markdown(f"**{BOOK['title']}**")
    st.sidebar.caption(f"{BOOK['chapter']}")
    st.sidebar.progress(BOOK["chapter_progress"], text="Book progress")
    st.sidebar.progress(mastery, text=f"Chapter mastery: {correct}/{len(QUIZ)}")
    st.sidebar.metric("Answered", f"{answered}/{len(QUIZ)}")
    st.sidebar.metric("Missed concepts", len(missed_concepts(missed)))

    if st.sidebar.button("Reset quiz state", use_container_width=True):
        reset_all_quiz_state()
        st.rerun()

    with st.sidebar.expander("Prototype state", expanded=False):
        st.json(current_state())


def render_variant_a() -> None:
    render_sidebar_state()

    left, main_col, right = st.columns([0.95, 2.1, 1.05], gap="large")
    with left:
        st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
        st.markdown('<div class="sr-kicker">My Books</div>', unsafe_allow_html=True)
        st.markdown(f"**{BOOK['title']}**")
        st.caption("Nonfiction self-learning book")
        st.progress(BOOK["chapter_progress"], text="5 of 12 chapters touched")
        st.markdown('<div class="sr-rule"></div>', unsafe_allow_html=True)
        st.markdown("**Chapter map**")
        st.caption("Chapter 1: Starting Small")
        st.caption("Chapter 2: Practice Cues")
        st.caption("Chapter 3: Useful Friction")
        st.markdown(f"**{BOOK['chapter']}**")
        st.caption("Chapter 5: Durable Review")
        st.markdown("</div>", unsafe_allow_html=True)

    with main_col:
        st.markdown('<div class="sr-kicker">Chapter lesson</div>', unsafe_allow_html=True)
        st.markdown(f'<h1 class="sr-lesson-title">{BOOK["chapter"]}</h1>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-muted">A focused study console for learners who want '
            'to move between evidence, concepts, quiz feedback, and review.</p>',
            unsafe_allow_html=True,
        )

        tabs = st.tabs(["Summary", "Core Concepts", "Key Takeaways", "Quiz", "Review"])
        with tabs[0]:
            render_summary()
        with tabs[1]:
            render_concepts(compact=False)
        with tabs[2]:
            render_takeaways()
        with tabs[3]:
            render_quiz()
        with tabs[4]:
            render_review_panel()

    with right:
        render_evidence_panel()
        st.divider()
        render_mastery_panel()


def render_variant_b() -> None:
    render_sidebar_state()

    top_left, top_right = st.columns([1.55, 1], gap="large")
    with top_left:
        st.markdown('<div class="sr-kicker">Reading path</div>', unsafe_allow_html=True)
        st.markdown(f'<h1 class="sr-lesson-title">{BOOK["chapter"]}</h1>', unsafe_allow_html=True)
        st.markdown(
            "Study this chapter as a single path: understand the argument, inspect "
            "the evidence, answer five checks, then repair missed concepts."
        )
    with top_right:
        render_mastery_panel()

    st.markdown("## 1. Summary")
    st.markdown('<div class="sr-path-step">', unsafe_allow_html=True)
    render_summary(numbered=False)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 2. Core Concepts")
    concept_cols = st.columns(2, gap="large")
    for index, concept in enumerate(CONCEPTS):
        with concept_cols[index % 2]:
            render_concept_card(concept, f"path_concept_{index}", include_example=True)

    st.markdown("## 3. Key Takeaways")
    st.markdown('<div class="sr-path-step">', unsafe_allow_html=True)
    render_takeaways()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## 4. Quiz")
    quiz_col, evidence_col = st.columns([1.55, 1], gap="large")
    with quiz_col:
        render_quiz(path_style=True)
    with evidence_col:
        render_evidence_panel()

    st.markdown("## 5. Missed-Concept Review")
    render_review_panel()


def render_summary(numbered: bool = True) -> None:
    for index, item in enumerate(SUMMARY, start=1):
        prefix = f"**{index}.** " if numbered else ""
        st.markdown(f"{prefix}{item['text']}")
        render_citation_buttons(item["citations"], f"summary_{index}")


def render_concepts(compact: bool) -> None:
    for index, concept in enumerate(CONCEPTS):
        render_concept_card(concept, f"concept_{index}", include_example=not compact)


def render_concept_card(concept: dict[str, Any], namespace: str, include_example: bool) -> None:
    st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="sr-concept-name">{concept["name"]}</div>', unsafe_allow_html=True)
    st.markdown(concept["short"])
    st.caption(f"Why it matters: {concept['why']}")
    if include_example:
        st.caption(f"Example: {concept['example']}")
    render_citation_buttons([concept["citation"]], namespace)
    st.markdown("</div>", unsafe_allow_html=True)


def render_takeaways() -> None:
    for index, takeaway in enumerate(TAKEAWAYS, start=1):
        st.markdown(f"**{index}. {takeaway['text']}**")
        render_citation_buttons([takeaway["citation"]], f"takeaway_{index}")


def render_quiz(path_style: bool = False) -> None:
    for index, question in enumerate(QUIZ, start=1):
        if path_style:
            st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
        st.markdown(f"**Question {index}**")
        st.markdown(question["question"])
        key = answer_key(question["id"])
        options = ["Choose an answer"] + question["options"]
        st.selectbox(
            "Answer",
            options=options,
            key=key,
            label_visibility="collapsed",
        )
        button_cols = st.columns([0.45, 1.55])
        with button_cols[0]:
            if st.button("Check answer", key=f"check_{question['id']}", use_container_width=True):
                if st.session_state[key] != "Choose an answer":
                    st.session_state[submitted_key(question["id"])] = True
                    st.rerun()
        with button_cols[1]:
            render_question_feedback(question)
        if path_style:
            st.markdown("</div>", unsafe_allow_html=True)
        st.divider()


def render_question_feedback(question: dict[str, Any]) -> None:
    if not st.session_state[submitted_key(question["id"])]:
        st.caption("Feedback appears after checking an answer.")
        return

    selected = st.session_state[answer_key(question["id"])]
    is_correct = selected == question["answer"]
    concept = concept_by_id(question["concept_id"])
    if is_correct:
        st.markdown('<span class="sr-status-ok">Correct</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="sr-status-miss">Review needed</span>', unsafe_allow_html=True)
        st.caption(f"Correct answer: {question['answer']}")
    st.write(question["explanation"])
    st.caption(f"Concept tested: {concept['name']}")
    render_citation_buttons([question["citation"]], f"feedback_{question['id']}")


def render_review_panel() -> None:
    missed = missed_questions()
    concepts = missed_concepts(missed)

    if not missed:
        if answered_count() == 0:
            st.info("Answer quiz questions to build a review queue.")
        else:
            st.success("No missed concepts are due from checked answers.")
        return

    st.markdown("### Due review")
    for concept in concepts:
        related = [q for q in missed if q["concept_id"] == concept["id"]]
        st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
        st.markdown(f"**{concept['name']}**")
        st.write(concept["short"])
        st.caption(f"Review focus: {concept['why']}")
        st.caption("Missed questions: " + ", ".join(q["id"].upper() for q in related))
        render_citation_buttons([concept["citation"]], f"review_{concept['id']}")
        st.markdown("</div>", unsafe_allow_html=True)

    retry_cols = st.columns([0.6, 1.4])
    with retry_cols[0]:
        if st.button("Retry missed questions", use_container_width=True):
            retry_missed_questions(missed)
            st.rerun()
    with retry_cols[1]:
        st.caption("Retry clears only missed answers. Correct answers stay checked.")


def render_evidence_panel() -> None:
    selected = st.session_state.get("selected_citation", "C1")
    citation = CITATIONS[selected]
    st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
    st.markdown("### Evidence")
    st.caption("Click any citation chip to inspect the source excerpt.")
    st.markdown(f"**{selected} - {citation['location']}**")
    st.write(citation["excerpt"])
    st.caption("Fake prepared excerpt for prototype validation.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_mastery_panel() -> None:
    correct = correct_count()
    answered = answered_count()
    mastery = correct / len(QUIZ)
    missed = missed_questions()

    st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
    st.markdown("### Mastery")
    st.metric("Score", f"{correct}/{len(QUIZ)}")
    st.progress(mastery, text=f"{int(mastery * 100)} percent mastery")
    st.caption(f"{answered} of {len(QUIZ)} questions checked")
    if missed:
        st.caption("Review due: " + ", ".join(c["name"] for c in missed_concepts(missed)))
    else:
        st.caption("No missed concepts are due yet.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_citation_buttons(citation_ids: list[str], namespace: str) -> None:
    st.markdown('<div class="sr-cite-row">', unsafe_allow_html=True)
    cols = st.columns([0.22] * len(citation_ids) + [1])
    for index, citation_id in enumerate(citation_ids):
        citation = CITATIONS[citation_id]
        with cols[index]:
            if st.button(
                f"{citation_id} {citation['label']}",
                key=f"cite_{namespace}_{citation_id}",
                help=citation["location"],
            ):
                st.session_state["selected_citation"] = citation_id
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def answer_key(question_id: str) -> str:
    return f"answer_{question_id}"


def submitted_key(question_id: str) -> str:
    return f"submitted_{question_id}"


def concept_by_id(concept_id: str) -> dict[str, Any]:
    return next(concept for concept in CONCEPTS if concept["id"] == concept_id)


def answered_count() -> int:
    return sum(1 for q in QUIZ if st.session_state[submitted_key(q["id"])])


def correct_count() -> int:
    return sum(
        1
        for q in QUIZ
        if st.session_state[submitted_key(q["id"])]
        and st.session_state[answer_key(q["id"])] == q["answer"]
    )


def missed_questions() -> list[dict[str, Any]]:
    return [
        q
        for q in QUIZ
        if st.session_state[submitted_key(q["id"])]
        and st.session_state[answer_key(q["id"])] != q["answer"]
    ]


def missed_concepts(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    concepts = []
    for question in questions:
        concept = concept_by_id(question["concept_id"])
        if concept["id"] not in seen:
            seen.add(concept["id"])
            concepts.append(concept)
    return concepts


def retry_missed_questions(questions: list[dict[str, Any]]) -> None:
    for question in questions:
        st.session_state[answer_key(question["id"])] = "Choose an answer"
        st.session_state[submitted_key(question["id"])] = False


def reset_all_quiz_state() -> None:
    for question in QUIZ:
        st.session_state[answer_key(question["id"])] = "Choose an answer"
        st.session_state[submitted_key(question["id"])] = False
    st.session_state["selected_citation"] = "C1"


def current_state() -> dict[str, Any]:
    missed = missed_questions()
    return {
        "selected_citation": st.session_state.get("selected_citation"),
        "answered_count": answered_count(),
        "correct_count": correct_count(),
        "missed_question_ids": [q["id"] for q in missed],
        "review_queue": [concept["name"] for concept in missed_concepts(missed)],
        "answers": {
            q["id"]: {
                "selected": st.session_state[answer_key(q["id"])],
                "checked": st.session_state[submitted_key(q["id"])],
                "correct": st.session_state[answer_key(q["id"])] == q["answer"],
            }
            for q in QUIZ
        },
    }


if __name__ == "__main__":
    main()
