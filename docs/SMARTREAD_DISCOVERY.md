# SmartRead Discovery Brief

## Product Positioning

SmartRead helps serious self-learners turn nonfiction books into structured, cited chapter lessons so they can understand and remember what they read.

### Working Value Proposition

SmartRead turns nonfiction books into cited chapter lessons with summaries, core concepts, quizzes, and spaced review so users actually remember what they read.

---

## Target User

### First Target User

Serious self-learners who read nonfiction books about:

* Personal development
* Business
* Productivity
* Practical skills
* General learning

### Not the First Target User

SmartRead will not initially focus on:

* Teachers
* Students preparing for school exams
* Fiction readers
* Academic researchers
* Corporate trainers
* People trying to avoid reading the book entirely

---

## Core Product Loop

1. The user uploads a clean PDF or EPUB that they own or have permission to use.
2. SmartRead analyzes the book.
3. SmartRead detects the book’s chapters.
4. The user reviews and edits the detected chapter boundaries.
5. The user selects and studies one chapter at a time.
6. Each chapter lesson contains:

   * Summary
   * Core concepts
   * Key takeaways
   * Quiz
7. The quiz provides immediate feedback and explanations.
8. Concepts the user misses are added to a lightweight spaced-review queue.
9. The dashboard shows:

   * Uploaded books
   * Chapter progress
   * Quiz performance
   * Concept mastery
   * Reviews that are due

---

## MVP Scope

### Included in the MVP

* PDF upload
* EPUB upload
* Initial book analysis
* Automatic chapter detection
* Editable chapter boundaries
* One-chapter-at-a-time content generation
* Cited chapter summaries
* Core concept extraction
* Key takeaway extraction
* Clickable citations
* Source excerpts for citations
* Mostly objective quiz questions
* Immediate quiz feedback
* Answer explanations
* Optional self-check short-answer questions
* Quiz score
* Missed-concept tracking
* Targeted review
* Retry missed questions
* My Books dashboard
* Lightweight spaced-review queue

### Excluded from the MVP

* Modern slide generation
* Kindle or DRM-protected book imports
* DRM bypassing
* Public book library
* Publicly searchable books
* Sharing or publishing summaries
* Teacher or classroom mode
* Learning management system integrations
* Corporate training features
* Social features
* Native mobile application
* AI chat as the main interface
* Marketplace or publisher partnerships

---

## Main Chapter Learning Experience

Each chapter should contain the following sections:

### 1. Summary

A clear explanation of the chapter’s central argument and important supporting ideas.

The summary should:

* Be based only on the uploaded chapter
* Preserve important nuance
* Avoid vague or generic statements
* Include citations for important claims

### 2. Core Concepts

A list of the most important concepts in the chapter.

Each concept should contain:

* Concept name
* Simple explanation
* Why it matters
* Example when useful
* Supporting citation

### 3. Key Takeaways

A short list of the most important ideas the learner should remember.

### 4. Quiz

The quiz should mainly test understanding rather than trivia.

The MVP quiz can include:

* Multiple-choice questions
* True-or-false questions
* Scenario or application questions
* Optional short-answer self-check questions

After answering, the user should immediately see:

* Whether the answer was correct
* The correct answer
* An explanation
* The supporting source excerpt
* The concept being tested

### 5. Targeted Review

Incorrect answers should create review items connected to the concepts the user misunderstood.

The user should be able to:

* Review missed concepts
* Retry missed questions
* See which reviews are due
* Track improvement over time

---

## Differentiation

SmartRead should not compete as another AI book summarizer.

ChatGPT, NotebookLM, and similar tools can already summarize documents.

SmartRead’s advantage is its structured retention workflow:

```text
Book Map
→ Chapter Lesson
→ Cited Understanding
→ Active Recall
→ Immediate Feedback
→ Targeted Review
→ Long-Term Retention
```

The core product belief is:

> A structured retention workflow is more valuable than generic AI chat.

SmartRead should win by providing:

* A clear book map
* Chapter-based learning units
* Verifiable citations
* Core concept extraction
* High-quality quizzes
* Mastery tracking
* Spaced review

---

## Primary Product Risk

The biggest risk is content quality and user trust.

The product will fail if:

* Summaries are vague
* Important ideas are missed
* Concepts are generic
* Quiz questions are weak
* Questions test trivia instead of understanding
* Citations do not support the claims
* Source excerpts are incorrect
* Feedback is not useful
* Review recommendations feel random

SmartRead must produce learning materials that feel:

* Accurate
* Specific
* Verifiable
* Useful
* Easy to understand
* Worth returning to

---

## Content Quality Requirements

### Grounding

Every important generated claim must be traceable to the uploaded book.

Citations must:

* Point to the correct source location
* Reveal the supporting excerpt
* Clearly support the generated claim
* Never be invented by the language model

### Summary Quality

A good summary should:

* Explain the chapter’s central argument
* Include important supporting ideas
* Preserve important limitations and nuance
* Remove unnecessary detail
* Be more useful than a generic one-shot AI summary

### Concept Quality

A good concept should:

* Be central to the chapter
* Use the author’s intended meaning
* Avoid generic labels
* Be understandable to the target user
* Include source support

### Quiz Quality

A good quiz question should:

* Be answerable from the chapter
* Have a clear correct answer
* Test understanding or application
* Avoid unnecessary trivia
* Avoid ambiguous wording
* Include a useful explanation
* Be connected to a core concept

---

## Validation Plan

Before building the full application, SmartRead should be tested through a concierge prototype.

### Participants

Recruit 5–10 serious self-learners.

Each participant should provide one nonfiction chapter they genuinely care about.

### Learning Package

For each chapter, manually or semi-manually create:

* Cited summary
* Core concepts
* Key takeaways
* Quiz
* Immediate feedback
* Missed-concept review list

### Baseline Comparison

Compare the SmartRead learning package with a generic AI response created using a simple prompt such as:

> Summarize this chapter and generate a quiz.

Ask users which version:

* Helped them understand the chapter better
* Felt more trustworthy
* Was easier to remember
* They would use for another chapter
* Made citations useful

### Success Criteria

The first validation is successful when:

* At least 3 out of 10 users ask to use SmartRead for another chapter or book within seven days.
* At least 2 users say they would pay approximately $10–15 per month.
* Users demonstrate repeat usage rather than only giving compliments.
* Users find the citations useful and trustworthy.
* Users show improved understanding or delayed recall.

Compliments alone do not count as validation.

Repeat use and payment behavior are stronger signals.

---

## Product Boundaries

SmartRead must not become:

* A piracy tool
* A DRM bypass tool
* A searchable copyrighted-book library
* A public redistribution engine
* A platform for publicly sharing full copyrighted summaries
* A product designed to replace reading completely

SmartRead should remain focused on:

* Private user uploads
* Books the user owns or can legally access
* Cited understanding
* Active recall
* Memory and retention
* Personal learning progress

---

## Privacy Principles

* Uploaded books remain private.
* A user should not be able to access another user’s books.
* Users should be able to delete uploaded books and generated learning data.
* SmartRead should clearly explain whether book content is sent to an external AI provider.
* Uploaded content should not become part of a public library.
* The system should not expose complete book text through public links.

---

## MVP Technology Direction

The initial implementation may use:

* Streamlit for the frontend
* FastAPI for the backend API
* Python for document and AI processing
* PostgreSQL for structured data
* A vector-search solution for source retrieval
* Structured LLM output validated with Pydantic
* Background processing for book analysis

These choices are not permanent product requirements and may change after prototyping.

---

## Current Product Decision

SmartRead is not an AI summarizer.

SmartRead is:

> A private learning system that transforms nonfiction books into cited chapter lessons, active-recall quizzes, and targeted review so serious self-learners can understand and retain what they read.

---

## Next Step

Use this document as the input for a `/grill-with-docs` session.

The goal of that session is to:

* Define SmartRead’s shared domain vocabulary
* Create or update `CONTEXT.md`
* Identify unresolved product rules
* Record important invariants
* Avoid writing application code
