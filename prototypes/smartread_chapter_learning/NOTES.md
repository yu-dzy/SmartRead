# SmartRead Chapter-Learning Prototype Notes

## Question

Which chapter-learning UI direction better supports SmartRead's core flow: cited understanding, active recall, immediate feedback, missed-concept review, and retrying missed questions?

## Variants

**A: Study console**

A focused workspace with a chapter map, tabbed chapter lesson sections, an evidence panel, and a mastery panel. This tests whether learners prefer clear navigation between Summary, Core Concepts, Key Takeaways, Quiz, and Review.

**B: Reading path**

A linear chapter journey with summary, concepts, takeaways, quiz, evidence, and review stacked in order. This tests whether learners prefer a guided flow that feels closer to completing a chapter lesson from top to bottom.

## Constraints

- Throwaway Streamlit prototype code only.
- Fake prepared data only.
- No PDF or EPUB processing.
- No FastAPI.
- No database storage.
- No authentication.
- No real LLM calls.
- No slide generation.

## Verdict

Fill this in after comparing the variants.
## Selected Prototype

Design A: Study Console

Design A is the chosen direction for SmartRead’s chapter-learning experience.

Reasons:

- It makes the learning sections easy to find.
- The Summary → Concepts → Quiz → Review flow is clear.
- Citations are easy to access.
- It feels suitable for serious self-learners.

The prototype is only a design reference. Its code should not be reused as production code without review.