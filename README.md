## English Tutor Bot — AI English Tutor for Russian Students

This is a Telegram bot that helps Russian school students (Grades 1-11) learn English within their FGOS curriculum and Spotlight textbook program. I built it in late January 2026, during the same period I was struggling to fix RUSLAN.

Honestly, this one working well gave me the confidence to go back and push RUSLAN further. It was proof that the architecture I had arrived at was sound, even if RUSLAN itself was still misbehaving.


## What it does:
The bot answers English language questions like grammar, vocabulary, translation guidance, textbook topics but stays strictly within what is appropriate for the student's grade. A Grade 3 student gets responses in Russian only with simple practice prompts. A Grade 10 student mostly gets English with structured explanations.

It does not do homework. It does not give full translations but it only guides.


## How it works:
Same core architecture as RUSLAN but simpler because the domain is simpler. English tutoring does not need the strict chronological enforcement that history does. 

There is no equivalent of "you cannot study Stalin before you have studied collectivisation." so the system is lighter by design, not by accident.

## Two tier pipeline:
Tier 1 —> YandexGPT Lite classifies the message as GREETING, CASUAL, or TEACHING. Greetings and casual messages get template responses immediately. No Pro call made, no message count incremented.

Tier 2 —> Teaching requests go to YandexGPT Pro with a prompt assembled from the student's grade, textbook, language settings, and last 3 conversation turns.

The static prompt lives in the config file. The dynamic part that is grade, textbook, context is assembled fresh for each teaching request. Backend owns all decisions.

Like all my projects, this was built using principles from RITA, a personal framework I developed for structured AI system design.


## What the testing looked like:
I ran 34 test cases across 10 categories in Phase 1 and the setup flow, grade-appropriate language, response length, teaching approach, boundaries, context memory, safety, edge cases, system features, and jailbreak resistance. Phase 1 came back at 65% pass, 24% partial, 12% fail.

I then fixed every failing and partial case I could and ran Phase 2 on all 12 problematic cases. 6 were fully fixed, 4 improved to acceptable, 2 remained open which are abusive language handling and message limit awareness and these both are non-blocking.

The two remaining failures did not affect teaching quality or safety. The bot was declared ready for pilot testing after Phase 2.


## What worked and what did not:
Context and state management worked reliably throughout testing. The bot maintained coherent conversation across multiple turns, remembered grade and textbook settings, and enforced curriculum boundaries consistently.

What did not fully work was the classifier occasionally misread intent in edge cases. This was the same problem I was fighting in RUSLAN. I understood the cause but fixing it properly required deeper work than I could do independently at that stage.


## Current status:
Not running. The Yandex API credit period ended and the bot was never publicly deployed. It was tested internally only.


## What is in this repository:
Full system prompt in the config file, all Python modules, flowchart, and 2 phases QA report with detailed test cases and outputs.


## A note on the code:
Same as RUSLAN i.e. architecture, logic, and QA were mine. Code was implemented with AI assistance and this is stated explicitly and intentionally.

However I am studying Python in parallel to understand the code even better and code independently in future projects.


Built with Python, aiogram, YandexGPT API, SQLite, Telegram Bot API.
