ENGLISH TUTOR BOT - COMPLETE FLOWCHART From User Input → Bot Output and Other Info

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER SENDS MESSAGE                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CHECK: Is user whitelisted?                      │
│                    (For beta testing only)                          │
└────────────────┬────────────────────────────────┬───────────────────┘
                 │                                │
                 │ NO                             │ YES
                 ▼                                ▼
        ┌────────────────┐              ┌─────────────────────────────┐
        │ Send: Access   │              │  CHECK: User exists in DB?  │
        │ denied message │              └──────────┬──────────────────┘
        └────────────────┘                         │
                                                   ▼
                                          ┌────────┴────────┐
                                          │                 │
                                    NO    │                 │  YES
                                          │                 │
                                          ▼                 ▼
                              ┌──────────────────┐   ┌────────────────┐
                              │ Create user in   │   │ Load user data │
                              │ DB (no grade)    │   │ from DB        │
                              └────────┬─────────┘   └───────┬────────┘
                                       │                     │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                              ┌──────────────────────────────────────┐
                              │  CHECK: Does user have grade set?    │
                              └──────────┬───────────────────────────┘
                                         │
                                         ▼
                                  ┌──────┴─────┐
                                  │            │
                            NO    │            │  YES
                                  │            │
                                  ▼            ▼
                      ┌────────────────────┐   │
                      │ Show grade         │   │
                      │ selection buttons  │   │
                      │ (1-11)             │   │
                      │ [WAIT FOR CLICK]   │   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ User clicks grade  │   │
                      │ button             │   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ Save grade to DB   │   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ Show textbook      │   │
                      │ buttons:           │   │
                      │ 1. Spotlight       │   │
                      │ 2. Unknown edition │   │
                      │ [WAIT FOR CLICK]   │   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ User clicks        │   │
                      │ textbook button    │   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ Save textbook to DB│   │
                      └──────────┬─────────┘   │
                                 │             │
                                 ▼             │
                      ┌────────────────────┐   │
                      │ Send: "Setup done! │   │
                      │ Ask questions"     │   │
                      │ [END]              │   │
                      └────────────────────┘   │
                                               │
                                               │
                      ┌────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│              CHECK: Daily message limit reached?                    │
│              (Check messagecount in DB)                             │
└────────────────┬────────────────────────────────┬───────────────────┘
                 │                                │
                 │ YES (>=30)                     │ NO (<30)
                 ▼                                ▼
        ┌────────────────┐              ┌─────────────────────────────-┐
        │ Send: "Daily   │              │    TIER-1 CLASSIFIER         │
        │ limit reached" │              │    (Cheap YandexGPT call)    │
        │ [END]          │              │                              │
        └────────────────┘              │  Prompt: "Classify:          │
                                        │  GREETING / CASUAL / TEACHING│
                                        │  Input: {user_message}"      │
                                        │                              │
                                        │  Model: YandexGPT Lite       │
                                        │  maxTokens: 10               │
                                        │  temperature: 0              │
                                        │  Cost: ~50 tokens            │
                                        └──────────┬────────────────-──┘
                                                   │
                                                   ▼
                                          ┌────────┴────────┐
                                          │                 │
                                    GREETING/CASUAL         TEACHING
                                          │                 │
                                          ▼                 ▼
                              ┌──────────────────┐   ┌────────────────┐
                              │ TEMPLATE RESPONSE│   │ CONTINUE TO    │
                              │ (No API call)    │   │ TIER-2         │
                              │                  │   └───────┬────────┘
                              │ If GREETING:     │           │
                              │ "Привет! Готов   │           │
                              │ помочь с         │           │
                              │ английским"      │           │
                              │                  │           │
                              │ If CASUAL:       │           │
                              │ "Давай вернёмся  │           │
                              │ к английскому"   │           │
                              │                  │           │
                              │ Do NOT save to   │           │
                              │ conversation DB  │           │
                              │                  │           │
                              │ Do NOT increment │           │
                              │ message count    │           │
                              │                  │           │
                              │ Send response    │           │
                              │ [END]            │           │
                              └──────────────────┘           │
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         TIER-2: FULL TEACHING                       │
│                                                                     │
│  STEP 1: Load from Database                                         │
│  ├─ user_id                                                         │
│  ├─ grade                                                           │
│  └─ textbook                                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Load Last 3 Conversations from conversations table         │
│  Format: [(user_msg1, bot_msg1), (user_msg2, bot_msg2), ...]        │
│                                                                     │
│  If < 3 messages exist: use what's available                        │
│  Context string built as:                                           │
│  "User: {msg1}\nBot: {response1}\nUser: {msg2}\nBot: {response2}"   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Build Dynamic Context                                      │
│                                                                     │
│  dynamic_context = f"""                                             │
│  Student: Grade {grade}                                             │
│  Textbook: {textbook}                                               │
│                                                                     │
│  Recent conversation:                                               │
│  {conversation_history}                                             │
│                                                                     │
│  Current question: {user_message}                                   │
│                                                                     │
│  Remember: Use {language_for_grade} for this grade.                 │
│  Max {max_sentences} sentences.                                     │
│  """                                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Build Complete Prompt                                      │
│                                                                     │
│  full_prompt = STATIC_PROMPT + "\n\n" + dynamic_context             │
│                                                                     │
│  Estimated tokens: ~600-650 total                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: Call YandexGPT Pro 5.1                                     │
│                                                                     │
│  WITH:                                                              │
│  ├─ Rate limiting (2 sec between calls)                             │
│  ├─ Retry logic (3 attempts with exponential backoff)               │
│  ├─ Timeout handling (120 sec total)                                │
│  ├─ Error handling (429, network, timeout)                          │
│  └─ maxTokens: 400                                                  │
│                                                                     │
│  Cost: ~0.21 rubles per call                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                        ┌──────┴──────┐
                        │             │
                  ERROR │             │ SUCCESS
                        │             │
                        ▼             ▼
            ┌──────────────────┐   ┌─────────────────────────────────┐
            │ Retry up to 3x   │   │ STEP 6: Receive API Response    │
            │ with exponential │   │                                 │
            │ backoff          │   │ Extract:                        │
            │                  │   │ ├─ answer_text                  │
            │ If all fail:     │   │ ├─ input_tokens                 │
            │ Send error msg   │   │ └─ output_tokens                │
            │ [END]            │   └────────┬────────────────────────┘
            └──────────────────┘            │
                                            ▼
                              ┌──────────────────────────────────────┐
                              │ STEP 7: Post-process Response        │
                              │                                      │
                              │ Append disclaimer (in backend):      │
                              │                                      │
                              │ final_response = answer_text + "\n\n"│
                              │ + "---\n\nThis response is generated │
                              │ by an AI system to support learning  │
                              │ within the official Russian FGOS     │
                              │ curriculum and Spotlight themes. It  │
                              │ does not replace a qualified teacher │
                              │ and does not do homework for         │
                              │ students."                           │
                              └────────┬─────────────────────────────┘
                                       │
                                       ▼
                              ┌────────────────────────────────────┐
                              │ STEP 8: Save to Database           │
                              │                                    │
                              │ 1. Save conversation pair:         │
                              │    INSERT INTO conversations       │
                              │    (user_id, user_msg, bot_msg,    │
                              │     timestamp)                     │
                              │                                    │
                              │ 2. Increment message count:        │
                              │    UPDATE users                    │
                              │    SET messagecount = messagecount │
                              │    + 1                             │
                              │    WHERE user_id = {user_id}       │
                              │                                    │
                              │ 3. Auto-cleanup old messages:      │
                              │    Keep only last 3 per user       │
                              │    DELETE FROM conversations       │
                              │    WHERE user_id = {user_id}       │
                              │    AND id NOT IN (                 │
                              │      SELECT id FROM conversations  │
                              │      WHERE user_id = {user_id}     │
                              │      ORDER BY timestamp DESC       │
                              │      LIMIT 3                       │
                              │    )                               │
                              └────────┬───────────────────────────┘
                                       │
                                       ▼
                              ┌────────────────────────────────────┐
                              │ STEP 9: Send Response to User      │
                              │                                    │
                              │ With retry logic:                  │
                              │ - Try 3 times                      │
                              │ - Exponential backoff (1s, 2s, 4s) │
                              │ - If all fail: send network error  │
                              └────────┬───────────────────────────┘
                                       │
                                       ▼
                              ┌────────────────────────────────────┐
                              │          [END]                     │
                              │                                    │
                              │ User receives:                     │
                              │ - Teaching response in correct     │
                              │   language for their grade         │
                              │ - With disclaimer footer           │
                              │ - Conversation context preserved   │
                              └────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════
                            SPECIAL CASES
═══════════════════════════════════════════════════════════════════════

CASE 1: Multi-question Detection
─────────────────────────────────
If user sends: "What is Past Simple and Present Perfect?"

Action: Before processing, send template response:
"Пожалуйста, задавай по одному вопросу. Начни с первого."
[END]


CASE 2: /start Command
──────────────────────
User sends: /start

Action: Force grade selection flow regardless of existing data
Show grade buttons → Show textbook buttons → Save → Confirm


CASE 3: /reset Command (optional)
──────────────────────────────────
User sends: /reset

Action:
1. DELETE FROM users WHERE telegram_id = {user_id}
2. DELETE FROM conversations WHERE user_id = {user_id}
3. Send: "Profile deleted. Use /start to begin again."
[END]


CASE 4: Classifier Timeout/Failure
───────────────────────────────────
If Tier-1 classifier fails to respond within 5 seconds:

Action: Default to TEACHING (send to Tier-2)
Reason: Better to process than to block user


CASE 5: Daily Reset (Cron Job)
───────────────────────────────
Every day at 00:00 UTC:

Action:
UPDATE users SET messagecount = 0, last_reset = CURRENT_TIMESTAMP


═══════════════════════════════════════════════════════════════════════
                        DATABASE SCHEMA
═══════════════════════════════════════════════════════════════════════

TABLE: users
────────────
- user_id (INTEGER PRIMARY KEY AUTOINCREMENT)
- telegram_id (INTEGER UNIQUE NOT NULL)
- grade (INTEGER)
- textbook (TEXT)
- messagecount (INTEGER DEFAULT 0)
- last_reset (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

TABLE: conversations
────────────────────
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- user_id (INTEGER) [FK to users.user_id]
- user_message (TEXT)
- bot_response (TEXT)
- timestamp (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

INDEX: idx_user_timestamp ON conversations(user_id, timestamp DESC)
  (for fast retrieval of last 3 messages)


═══════════════════════════════════════════════════════════════════════
                        COST BREAKDOWN
═══════════════════════════════════════════════════════════════════════

PER MESSAGE:
────────────
Tier-1 Classifier (GREETING/CASUAL):
  - Input: ~30 tokens (prompt) + ~20 tokens (user msg) = 50 tokens
  - Output: 1 token (GREETING/CASUAL/TEACHING)
  - Cost: 0.01 rubles
  - If GREETING/CASUAL: STOP HERE → Total cost: 0.01 rubles

Tier-2 Teaching (TEACHING):
  - Input: 450 (static) + 150 (dynamic) + 50 (user) = 650 tokens
  - Output: 400 tokens
  - Cost: 0.21 rubles
  - Total cost: 0.01 (classifier) + 0.21 (teaching) = 0.22 rubles

PER STUDENT PER MONTH (30 msgs/day):
─────────────────────────────────────
Assuming 70% teaching, 30% casual:
- Teaching messages: 21 × 0.22 = 4.62 rubles
- Casual messages: 9 × 0.01 = 0.09 rubles
- Total per student: ~4.71 rubles/day × 30 = 141 rubles/month

For 50 students: 7,050 rubles/month


═══════════════════════════════════════════════════════════════════════
                    LANGUAGE MAPPING BY GRADE
═══════════════════════════════════════════════════════════════════════

Grade 1-4:  "only Russian"           | Max 4-5 sentences
Grade 5-7:  "mostly Russian"         | Max 8 sentences
Grade 8-9:  "mixed Russian/English"  | Max 12 sentences
Grade 10-11: "mostly English"        | Concise structured


═══════════════════════════════════════════════════════════════════════
```
