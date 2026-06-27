# SmartRead MVP Product Requirements Document

Status: Draft  
Selected prototype reference: Design A, Study Console  
Source inputs: `docs/SMARTREAD_DISCOVERY.md`, `CONTEXT.md`, and the throwaway SmartRead chapter-learning prototype

## Problem Statement

Serious self-learners read nonfiction books because they want to understand and retain useful ideas, but their current tools mostly help them consume information rather than learn it. Generic AI chat tools can summarize a book or answer questions, but they do not create a reliable structured retention workflow with chapter progress, verifiable citations, active recall, immediate feedback, missed-concept review, and long-term retention.

SmartRead solves the problem of turning a user-owned nonfiction book into a private, chapter-by-chapter learning system that helps the learner understand what the book says, verify important claims, test themselves, and review the concepts they missed.

## Target User

The MVP target user is a serious self-learner reading nonfiction self-learning books about personal development, business, productivity, practical skills, or general learning.

The target user:

- Owns or has permission to use the uploaded PDF or EPUB.
- Wants to understand and remember the book, not avoid reading entirely.
- Studies one chapter at a time.
- Values citations and source excerpts because they want trustworthy output.
- Benefits from quizzes, immediate feedback, and targeted review.

The MVP is not designed for teachers, classrooms, school exam preparation, fiction readers, academic researchers, corporate trainers, or people looking for pirated book access.

## Product Goal

SmartRead should help a serious self-learner upload a user-owned nonfiction book, review the detected chapter map, study one generated chapter lesson at a time, verify claims through clickable citations, answer a quiz, receive immediate feedback, and review missed concepts until they improve mastery.

The MVP should prove that a structured retention workflow is more valuable than a generic AI summary.

## Core User Journey

1. The user lands on the My Books dashboard.
2. The user uploads a clean PDF or EPUB that they own or have permission to use.
3. SmartRead analyzes the uploaded book.
4. SmartRead detects chapters and creates a book map.
5. The user reviews and edits detected chapter boundaries before generation.
6. The user selects a chapter from the book map.
7. SmartRead generates a chapter lesson for that chapter.
8. The user studies the chapter lesson in the Study Console.
9. The user reads the cited Summary, Core Concepts, and Key Takeaways.
10. The user clicks citations to inspect supporting source excerpts.
11. The user answers five quiz questions.
12. SmartRead immediately marks each objective answer and explains the result.
13. Incorrect answers create missed concepts.
14. Missed concepts appear in the Review tab and spaced review queue.
15. The user retries missed questions.
16. The dashboard updates chapter progress, quiz performance, concept mastery, and due reviews.
17. The user continues to the next chapter or returns later for due review.

## Chapter-Learning Experience Reference

The MVP chapter-learning experience should follow Design A: Study Console.

The Study Console contains:

- A left-side book and chapter map area showing the current book, chapter progress, and nearby chapters.
- A central chapter lesson area with tabs for Summary, Core Concepts, Key Takeaways, Quiz, and Review.
- A right-side Evidence panel that updates when the learner clicks a citation.
- A right-side Mastery panel showing score, answered count, missed concepts, and review status.
- A reset or retry behavior for prototype and learning-state recovery, translated in production into retry missed questions and retake quiz actions.

The Study Console should feel like a focused learning workspace, not a chat box and not a slide deck.

## User Stories

1. As a serious self-learner, I want to upload a nonfiction book I own, so that I can study it privately in SmartRead.
2. As a serious self-learner, I want SmartRead to accept PDF and EPUB files, so that I can use common book formats.
3. As a serious self-learner, I want to know that Kindle and DRM-protected imports are not supported, so that I understand the legal and product boundaries.
4. As a serious self-learner, I want SmartRead to analyze my uploaded book, so that I do not have to manually recreate its structure.
5. As a serious self-learner, I want SmartRead to detect chapters, so that I can study the book chapter by chapter.
6. As a serious self-learner, I want to review detected chapters before generation, so that I can catch incorrect chapter boundaries.
7. As a serious self-learner, I want to edit chapter boundaries, so that generated lessons use the correct source material.
8. As a serious self-learner, I want a book map, so that I can understand where I am in the book.
9. As a serious self-learner, I want a My Books dashboard, so that I can resume books I am studying.
10. As a serious self-learner, I want to see chapter progress, so that I know what I have completed.
11. As a serious self-learner, I want chapter lessons generated one chapter at a time, so that I can focus and avoid waiting for unused chapters.
12. As a serious self-learner, I want each chapter lesson to contain a Summary, Core Concepts, Key Takeaways, and Quiz, so that the lesson has a predictable learning structure.
13. As a serious self-learner, I want the Summary to explain the chapter's central argument, so that I understand the point of the chapter.
14. As a serious self-learner, I want summary claims to include citations, so that I can verify important statements.
15. As a serious self-learner, I want Core Concepts with names, explanations, and why they matter, so that I can remember the chapter's reusable ideas.
16. As a serious self-learner, I want each Core Concept to include supporting evidence, so that I can trust that it came from the chapter.
17. As a serious self-learner, I want Key Takeaways, so that I can quickly review the ideas I should remember.
18. As a serious self-learner, I want clickable citations, so that I can inspect the source excerpt behind a generated claim.
19. As a serious self-learner, I want the Evidence panel to update when I click a citation, so that verification feels immediate.
20. As a serious self-learner, I want source excerpts to be short and focused, so that I can verify claims without exposing full book text.
21. As a serious self-learner, I want quiz questions that test understanding, so that I can check whether I learned the concept rather than memorized trivia.
22. As a serious self-learner, I want five quiz questions per chapter in the MVP, so that the quiz is substantial but not exhausting.
23. As a serious self-learner, I want immediate answer feedback, so that I can correct misunderstandings while the material is fresh.
24. As a serious self-learner, I want each quiz explanation to show the correct answer, the tested concept, and a source excerpt, so that I know why my answer was right or wrong.
25. As a serious self-learner, I want incorrect answers to create missed concepts, so that SmartRead knows what I need to review.
26. As a serious self-learner, I want a Review tab, so that I can see the concepts I missed in the current chapter.
27. As a serious self-learner, I want a spaced review queue, so that missed concepts return later instead of disappearing after the quiz.
28. As a serious self-learner, I want to retry missed questions, so that I can repair misunderstandings without retaking everything.
29. As a serious self-learner, I want a Mastery panel, so that I can see score, answered questions, missed concepts, and review status while studying.
30. As a serious self-learner, I want empty states before I upload a book, generate a chapter, or answer a quiz, so that I know what to do next.
31. As a serious self-learner, I want clear loading states during upload, analysis, chapter generation, and quiz feedback, so that I know SmartRead is working.
32. As a serious self-learner, I want clear error states when upload, parsing, generation, citation retrieval, or quiz feedback fails, so that I can retry or recover.
33. As a serious self-learner, I want uploaded books and generated learning data to remain private, so that my reading material is not exposed.
34. As a serious self-learner, I want to delete uploaded books and generated learning data, so that I control my private library.
35. As a serious self-learner, I want SmartRead to explain whether book content is sent to an external AI provider, so that I can make an informed privacy decision.
36. As a serious self-learner, I want SmartRead to avoid replace-reading positioning, so that the product stays focused on learning and retention.

## Functional Requirements

### My Books Dashboard

- The dashboard must show the user's uploaded books.
- Each book must show title, author when available, upload status, analysis status, chapter progress, quiz performance, concept mastery, and due reviews.
- Each book must provide a clear continue action that opens the next unfinished chapter or due review.
- The dashboard must show an upload entry point.
- The dashboard must include an empty state when no books have been uploaded.

### Upload

- The MVP must support user-owned or permissioned PDF uploads.
- The MVP must support user-owned or permissioned EPUB uploads.
- The upload flow must clearly state that users should only upload books they own or have permission to use.
- The upload flow must reject unsupported file types.
- The upload flow must reject files that cannot be read or are too malformed to analyze.
- The upload flow must not support Kindle imports, DRM bypassing, public book search, or marketplace content.
- The upload flow must show progress while the file is being uploaded and prepared for analysis.
- The user must be able to delete an uploaded book and its generated learning data.

### Book Analysis And Chapter Detection

- SmartRead must analyze the uploaded book before any chapter lesson is generated.
- SmartRead must produce a book map from the uploaded book.
- The book map must include detected chapters or chapter-like sections.
- Each detected chapter must include a title when available.
- Each detected chapter must include a chapter boundary.
- The user must be able to review detected chapters before generating chapter lessons.
- The user must be able to rename a detected chapter.
- The user must be able to adjust a chapter boundary.
- The user must be able to merge or split detected chapter-like sections when detection is wrong.
- SmartRead must warn the user when chapter detection confidence is low.
- SmartRead must not generate a chapter lesson until the relevant chapter boundary is accepted or corrected.

### Chapter Generation

- SmartRead must generate learning content one chapter at a time.
- A generated chapter lesson must be based only on the source material inside the accepted chapter boundary.
- Each generated chapter lesson must contain Summary, Core Concepts, Key Takeaways, Quiz, and Review.
- Generated chapter content must be saved for the learner so they can resume later.
- The user must be able to regenerate a chapter lesson when generation fails or when chapter boundaries are corrected.
- Regeneration must make it clear whether existing quiz progress and review items will be reset or preserved.

### Study Console

- The chapter-learning surface must use the selected Study Console pattern.
- The left area must show book context and chapter map context.
- The central area must use separate sections or tabs for Summary, Core Concepts, Key Takeaways, Quiz, and Review.
- The right area must include Evidence and Mastery panels.
- Clicking a citation must update the Evidence panel with the selected source excerpt and location.
- The Mastery panel must update as quiz questions are checked.
- The Review section must show missed concepts created from incorrect answers.
- The Study Console must remain usable on desktop and smaller screens, with layout adapting without hiding core learning content.

### Summary

- The Summary must explain the chapter's central argument.
- The Summary must include important supporting ideas.
- The Summary must preserve important nuance and limitations.
- The Summary must avoid vague or generic statements.
- Important summary claims must include clickable citations.

### Core Concepts

- Core Concepts must be central to the chapter.
- Each Core Concept must include a concept name.
- Each Core Concept must include a simple explanation.
- Each Core Concept must include why it matters.
- Each Core Concept may include an example when useful.
- Each Core Concept must include at least one supporting citation.
- Core Concepts must avoid generic labels that could apply to any book.

### Key Takeaways

- Key Takeaways must be concise ideas the learner should remember.
- Key Takeaways must be derived from the chapter, not generic advice.
- Key Takeaways must include citations when they make claims about the chapter.

### Quiz

- Each MVP chapter quiz must include five questions.
- The quiz must primarily use objective questions that can be graded immediately.
- Supported objective question types include multiple-choice, true-or-false, and scenario/application questions.
- Optional short-answer prompts may be included only as self-check questions.
- Short-answer self-check questions must not be presented as authoritative AI-graded answers in the MVP.
- Each quiz question must be connected to a Core Concept.
- Each quiz question must have a clear correct answer when it is objective.
- Each quiz question must include an explanation.
- Each quiz question must include a supporting source excerpt.
- The quiz must avoid unnecessary trivia.
- The quiz must avoid ambiguous wording.

### Immediate Feedback

- After the learner checks an objective answer, SmartRead must show whether the answer is correct.
- If the answer is incorrect, SmartRead must show the correct answer.
- Feedback must include an explanation.
- Feedback must identify the concept being tested.
- Feedback must include a clickable citation or source excerpt.
- Feedback must update the Mastery panel.
- Incorrect answers must create missed concepts.

### Missed-Concept Review

- Incorrect objective quiz answers must create missed concepts.
- A missed concept must be linked to the Core Concept tested by the missed question.
- The Review tab must list due missed concepts for the current chapter.
- Each review item must show the concept name, a short explanation, the reason it matters, and supporting citation.
- The learner must be able to retry missed questions.
- Retrying missed questions should clear only the missed questions being retried; correct answers should remain intact unless the learner explicitly retakes the full quiz.
- The spaced review queue must include missed concepts that are due for future review.
- The dashboard must show due reviews.

## Citation And Content-Quality Requirements

### Grounding Requirements

- Every important generated claim must be traceable to the uploaded book.
- Citations must point to the correct source location.
- Citations must reveal the supporting source excerpt.
- Source excerpts must clearly support the generated claim.
- Citations must never be invented by the language model.
- SmartRead must not present unsupported model guesses as grounded claims.

### Source Excerpt Requirements

- A source excerpt must be short enough to support verification without exposing excessive book text.
- A source excerpt must be tied to one source location.
- A source excerpt must be shown in context of the generated claim, quiz explanation, or feedback item it supports.
- A missing source excerpt must be treated as a content-quality failure for any claim that requires support.

### Summary Quality Requirements

- A good Summary must explain the chapter's central argument.
- A good Summary must include important supporting ideas.
- A good Summary must preserve nuance, caveats, and limitations.
- A good Summary must remove unnecessary detail.
- A good Summary must be more useful than a generic one-shot AI summary.

### Concept Quality Requirements

- A good Core Concept must be central to the chapter.
- A good Core Concept must use the author's intended meaning.
- A good Core Concept must be understandable to the target user.
- A good Core Concept must avoid generic labels.
- A good Core Concept must include source support.

### Quiz Quality Requirements

- A good quiz question must be answerable from the chapter.
- A good quiz question must have a clear correct answer when objective.
- A good quiz question must test understanding or application.
- A good quiz question must avoid unnecessary trivia.
- A good quiz question must avoid ambiguous wording.
- A good quiz question must include a useful explanation.
- A good quiz question must be connected to a Core Concept.

## Loading, Empty, Error, And Retry States

### Loading States

- Uploading: show that the file is being uploaded and do not allow duplicate upload submission.
- Analyzing book: show that SmartRead is creating the book map and detecting chapters.
- Saving chapter edits: show that corrected chapter boundaries are being saved.
- Generating chapter lesson: show that Summary, Core Concepts, Key Takeaways, Quiz, and Review are being prepared.
- Loading evidence: show a lightweight state when a citation is clicked and the source excerpt is being retrieved.
- Checking answer: show a lightweight state while answer feedback is being prepared.
- Retrying missed questions: show that missed-question state is being reset.
- Loading dashboard: show a dashboard skeleton or equivalent placeholder while books and review status load.

### Empty States

- No uploaded books: explain that the learner can upload a user-owned PDF or EPUB to begin.
- No detected chapters: explain that SmartRead could not confidently identify chapters and ask the user to create or adjust chapter boundaries.
- No generated chapter lesson: prompt the learner to generate the selected chapter lesson.
- No answered quiz questions: show that feedback and review will appear after checking answers.
- No missed concepts: show that no missed concepts are due from checked answers.
- No due reviews: show that the learner has no review items due.

### Error States

- Unsupported file type: explain that the MVP supports only PDF and EPUB.
- File unreadable: explain that the file could not be read and offer retry or replacement upload.
- File too large or malformed: explain the constraint and offer next steps.
- Book analysis failed: explain that SmartRead could not create a book map and allow retry.
- Chapter detection low confidence: warn the user and require manual review.
- Chapter lesson generation failed: allow regeneration.
- Citation missing or unsupported: show that the source excerpt could not be retrieved and do not present the claim as fully verified.
- Quiz generation failed: allow regeneration for the chapter quiz.
- Answer feedback failed: allow checking the answer again.
- Review queue update failed: warn that the missed concept may not have been saved and allow retry.
- Delete failed: explain that the book or generated data could not be deleted and allow retry.

### Retry Behavior

- Upload retry must not create duplicate books.
- Analysis retry must preserve the uploaded file.
- Chapter boundary save retry must preserve the user's edits.
- Chapter generation retry must not silently overwrite existing learning progress.
- Citation retrieval retry must keep the learner on the current section.
- Quiz answer retry must not change the selected answer unless the learner changes it.
- Retry missed questions must target only missed questions unless the learner chooses a full quiz retake.
- Delete retry must not partially expose or orphan private content.

## Privacy And Copyright Boundaries

- SmartRead must process private user uploads only.
- Uploaded books must not become part of a public library.
- A user must not be able to access another user's books.
- Generated learning data must remain private to the uploading user.
- Users must be able to delete uploaded books and generated learning data.
- SmartRead must clearly explain whether book content is sent to an external AI provider.
- SmartRead must not support DRM bypassing.
- SmartRead must not support Kindle or DRM-protected imports in the MVP.
- SmartRead must not help users find, download, or redistribute copyrighted books without permission.
- SmartRead must not expose complete book text through public links.
- SmartRead must not enable public redistribution of full copyrighted summaries or source-heavy generated material.
- SmartRead must avoid replace-reading positioning such as "read without reading."
- SmartRead should position itself around cited understanding, active recall, memory, and retention.

## Measurable Acceptance Criteria

### Product Flow Acceptance Criteria

- A learner can upload a valid PDF or EPUB and reach book analysis.
- A learner can see a book map after analysis succeeds.
- A learner can review detected chapters before generation.
- A learner can edit at least one detected chapter boundary before generating a chapter lesson.
- A learner can generate one chapter lesson without generating all chapters upfront.
- A learner can navigate the Study Console sections: Summary, Core Concepts, Key Takeaways, Quiz, and Review.
- A learner can click a citation in Summary, Core Concepts, Key Takeaways, or Quiz feedback and see the corresponding source excerpt in the Evidence panel.
- A learner can answer five quiz questions for a chapter.
- A learner receives immediate feedback after checking each objective answer.
- A wrong answer creates a missed concept.
- A missed concept appears in the Review tab.
- The learner can retry missed questions.
- The My Books dashboard reflects chapter progress, quiz performance, concept mastery, and due reviews.

### Content-Quality Acceptance Criteria

- 100% of important summary claims include citations.
- 100% of Core Concepts include at least one supporting citation.
- 100% of objective quiz questions are connected to a Core Concept.
- 100% of objective quiz questions have one clear correct answer.
- 100% of answer explanations include supporting source evidence.
- 0 generated citations may point to nonexistent source locations.
- 0 generated source excerpts may be invented by the model.
- In internal review, generated Summary, Core Concepts, Key Takeaways, and Quiz should be judged more useful than a generic "summarize this chapter and generate a quiz" output for the same chapter.

### UX Acceptance Criteria

- The Study Console uses the Design A structure: chapter map area, tabbed chapter lesson area, Evidence panel, and Mastery panel.
- The user can understand what to do next from every empty state.
- Loading states are visible for upload, analysis, chapter generation, citation retrieval, answer checking, and retry actions.
- Error states explain what failed and provide a recovery path when recovery is possible.
- The learner can complete the core chapter-learning flow without using an AI chat interface.

### Validation Acceptance Criteria

- In concierge or early MVP validation, at least 3 out of 10 target users ask to use SmartRead for another chapter or book within seven days.
- At least 2 out of 10 target users say they would pay approximately $10-15 per month.
- Users find citations useful and trustworthy.
- Users demonstrate repeat usage rather than only giving compliments.
- Users show improved understanding or delayed recall compared with a generic AI summary baseline.

## Explicit MVP Exclusions

The MVP must not include:

- Modern slide generation.
- Kindle imports.
- DRM-protected imports.
- DRM bypassing.
- Public book library.
- Publicly searchable books.
- Sharing or publishing summaries.
- Public lesson links.
- Teacher or classroom mode.
- Learning management system integrations.
- Corporate training features.
- Social features.
- Native mobile application.
- AI chat as the main interface.
- Marketplace or publisher partnerships.
- Public redistribution of copyrighted summaries.
- Full flashcard-system complexity beyond a lightweight spaced review queue.
- Authoritative AI grading for short-answer questions.
- Whole-book lesson generation upfront.

## Implementation Decisions For MVP Planning

- Design A: Study Console is the product reference for the chapter-learning experience.
- The primary product surface is not chat; it is a structured Study Console.
- The chapter is the primary learning unit.
- Book analysis happens upfront, but chapter learning content is generated one chapter at a time.
- The product must keep citations and source excerpts as first-class learning objects, not decorative footnotes.
- The MVP should favor objective quiz questions because they can produce trustworthy immediate feedback.
- Optional short-answer prompts are self-check only in the MVP.
- Missed concepts are the bridge between quiz feedback and spaced review.
- The product should make content quality failures visible rather than quietly presenting unsupported output as trustworthy.

## Testing Decisions

Product testing should focus on external learner behavior and content trust rather than implementation details.

The highest-value seams to test are:

- Upload to book map: valid PDF or EPUB produces reviewable detected chapters.
- Chapter boundary review: user corrections affect the chapter material used for generation.
- Chapter generation: a selected chapter produces Summary, Core Concepts, Key Takeaways, Quiz, and Review structure.
- Citation verification: generated claims expose source excerpts that support them.
- Quiz feedback: objective answers produce correct feedback and source-supported explanations.
- Missed-concept review: wrong answers create missed concepts, review items, and retryable missed questions.
- Dashboard progress: chapter progress, mastery, and due reviews reflect completed learning actions.

Tests should verify that learners can complete the core journey and that unsupported or failed content does not appear as trustworthy output.

## Further Notes

The MVP's primary product risk is content quality and trust. If summaries are vague, concepts are generic, citations are incorrect, source excerpts do not support claims, quiz questions test trivia, or review recommendations feel random, SmartRead will collapse into a generic AI summarizer. The MVP should be judged by whether serious self-learners repeatedly use it to understand and retain chapters they care about.

The throwaway Streamlit prototype is a design reference only. Its code should not be reused as production code without review.
