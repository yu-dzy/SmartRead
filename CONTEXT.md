# SmartRead Context

SmartRead's shared product-domain language for turning nonfiction books into cited chapter lessons, active-recall quizzes, and targeted review. This context exists to keep product, design, and implementation discussions aligned on what SmartRead is and what it must not become.

## Language

### Product Identity

**SmartRead**:
A private learning system that transforms nonfiction books into cited chapter lessons, quizzes, and targeted review for serious self-learners.
_Avoid_: AI summarizer, book-summary app, slide generator

**Structured Retention Workflow**:
The end-to-end learning loop of book map, chapter lesson, cited understanding, active recall, immediate feedback, targeted review, and long-term retention.
_Avoid_: Chat flow, one-shot summary, document Q&A

**Generic AI Summary**:
A broad, one-shot AI response that summarizes a chapter or book without SmartRead's chapter structure, citations, quiz feedback, mastery tracking, or review loop.
_Avoid_: SmartRead lesson, chapter lesson

### People And Content

**Serious Self-Learner**:
A person using SmartRead to understand and remember nonfiction material they genuinely want to learn.
_Avoid_: Teacher, classroom student, corporate trainee, shortcut seeker

**Nonfiction Self-Learning Book**:
A nonfiction book about personal development, business, productivity, practical skills, or general learning that can be studied chapter by chapter.
_Avoid_: Fiction, school exam text, academic research corpus, corporate training material

**User-Owned Book**:
A book file the user owns or has permission to use privately in SmartRead.
_Avoid_: Pirated book, DRM-protected import, public library asset

**Uploaded Book**:
A user-owned PDF or EPUB submitted to SmartRead for private analysis and learning.
_Avoid_: Public book, marketplace title, shared library item

### Book Structure

**Book Analysis**:
The initial pass that identifies a book's structure and prepares it for chapter-based learning.
_Avoid_: Whole-book lesson generation, whole-book summary

**Book Map**:
The reviewable structure of an uploaded book, including detected chapters and study progress.
_Avoid_: Raw table of contents, library listing

**Detected Chapter**:
A chapter or chapter-like section inferred from an uploaded book during book analysis.
_Avoid_: Final chapter, immutable chapter

**Chapter Boundary**:
The start and end range for a detected chapter that determines what source material belongs to that chapter.
_Avoid_: Page guess, section marker

**Editable Chapter Boundary**:
A chapter boundary the user can correct before SmartRead generates learning content for that chapter.
_Avoid_: Fixed detection, hidden parsing result

### Chapter Learning

**Chapter Lesson**:
The canonical learning unit for one chapter, ordered as Summary, Core Concepts, Key Takeaways, and Quiz.
_Avoid_: Lesson pack, slide deck, module

**Summary**:
A cited explanation of the chapter's central argument and important supporting ideas.
_Avoid_: TL;DR, synopsis, generic summary

**Core Concept**:
A central idea from the chapter, named and explained with why it matters and supporting evidence.
_Avoid_: Keyword, tag, vague theme

**Key Takeaway**:
A concise idea the learner should remember from the chapter.
_Avoid_: Random highlight, motivational quote, action plan

**Cited Understanding**:
Understanding built from claims that can be verified against the uploaded book through citations and source excerpts.
_Avoid_: Unsupported interpretation, model guess

### Evidence And Trust

**Grounded Claim**:
An important generated statement that is traceable to source material in the uploaded book.
_Avoid_: Unsupported claim, invented claim

**Clickable Citation**:
A citation attached to generated material that reveals the supporting source excerpt and source location.
_Avoid_: Decorative citation, unverifiable footnote

**Source Excerpt**:
A short passage from the uploaded book that supports a generated claim, answer explanation, or quiz feedback.
_Avoid_: Full book text, long quotation, paraphrase without source

**Trustworthy Output**:
Generated learning material that is accurate, specific, verifiable, useful, and easy to understand.
_Avoid_: AI fluff, vague output, unsupported output

### Assessment And Review

**Quiz**:
An active-recall check for a chapter that mainly tests understanding and application of core concepts.
_Avoid_: Exam, trivia test, generic question list

**Objective Question**:
A quiz question with a clear correct answer that can be graded immediately, such as multiple-choice, true-or-false, or scenario application.
_Avoid_: Ambiguous prompt, subjective question

**Self-Check Short Answer**:
An optional short-answer prompt where the learner compares their answer with a suggested answer instead of receiving authoritative automated grading.
_Avoid_: AI-graded essay, scored free response

**Immediate Feedback**:
The response shown after a quiz answer, including correctness, the correct answer, an explanation, the supporting source excerpt, and the concept being tested.
_Avoid_: Raw score only, delayed feedback

**Mastery Result**:
A post-quiz view of how well the learner understood the chapter's concepts, including missed concepts and what to review.
_Avoid_: Score only, completion badge

**Missed Concept**:
A core concept connected to an incorrect or weak quiz response.
_Avoid_: Wrong answer, failed question

**Review Item**:
A follow-up item created from a missed concept to help the learner revisit and retain that idea.
_Avoid_: Generic reminder, unrelated flashcard

**Spaced Review Queue**:
A lightweight list of review items due for the learner based on missed concepts.
_Avoid_: Full flashcard system, Anki clone, notification system

**Targeted Review**:
Review focused on missed concepts and related missed questions from prior chapter quizzes.
_Avoid_: Rereading everything, generic review

### Product Boundaries

**Private Upload**:
An uploaded book and its generated learning data that belong only to the uploading user.
_Avoid_: Public upload, shared book, public lesson

**Public Redistribution**:
Making uploaded book content, full copyrighted summaries, or source-heavy generated material available outside the private learner workflow.
_Avoid_: Sharing, publishing, public library

**Piracy Tool**:
A product behavior that helps users obtain, bypass protection on, or redistribute copyrighted books without permission.
_Avoid_: Import convenience, library feature

**Replace-Reading Positioning**:
Messaging or behavior that frames SmartRead as a way to avoid reading books entirely rather than understand and retain them better.
_Avoid_: Speed-reading promise, "read without reading"

**Concierge Prototype**:
A manual or semi-manual validation process that creates SmartRead-style chapter learning packages before the full product is built.
_Avoid_: MVP app, production prototype

## Domain Rules

- SmartRead is a private learning system, not a generic AI summarizer.
- SmartRead's first user is the serious self-learner, not teachers, classrooms, corporate trainers, academic researchers, or people trying to avoid reading entirely.
- SmartRead's first content type is nonfiction self-learning books, especially personal development, business, productivity, practical skills, and general learning.
- SmartRead should accept user-owned or permissioned PDF and EPUB files; Kindle imports, DRM bypassing, piracy, and public book libraries are out of bounds.
- Uploaded books and generated learning data must remain private to the uploading user.
- Book analysis happens before chapter learning; chapter lessons are generated one chapter at a time.
- Users must be able to review and correct detected chapter boundaries before chapter learning content is generated.
- The canonical chapter lesson order is Summary, Core Concepts, Key Takeaways, then Quiz.
- Every important summary claim, concept explanation, quiz explanation, and feedback item should be grounded in the uploaded book.
- Clickable citations must reveal source excerpts and must not be invented.
- Quiz questions should test understanding or application, not trivia.
- Objective quiz questions should provide immediate grading and explanations.
- Short-answer questions are self-check prompts in the MVP, not authoritative AI-graded answers.
- Incorrect quiz responses create missed concepts.
- Missed concepts create review items for targeted spaced review.
- The dashboard centers on My Books, chapter progress, quiz performance, concept mastery, and due reviews.
- MVP scope excludes modern slide generation, public sharing, classroom mode, LMS integrations, native mobile apps, marketplace content, and AI chat as the main interface.
- SmartRead must not publicly expose complete book text, become a searchable copyrighted-book library, or encourage public redistribution of copyrighted summaries.
