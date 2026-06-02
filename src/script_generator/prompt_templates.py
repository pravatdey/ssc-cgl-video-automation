"""
Prompt templates for generating SSC CGL lesson scripts via LLM.

Content is generated in HINGLISH (Hindi + English mix) — the natural way
Indian coaching teachers explain on YouTube. Target: 12-15 min videos.

The system prompt and per-subject guidance adapt to the 4 SSC CGL subjects:
reasoning, quant, english, general_awareness.
"""

# ----------------------------------------------------------------------------
# Per-subject teaching guidance injected into the system prompt
# ----------------------------------------------------------------------------
SUBJECT_GUIDANCE = {
    "reasoning": (
        "You specialise in SSC CGL General Intelligence & Reasoning (puzzles, series, "
        "coding-decoding, blood relations, syllogism, seating, non-verbal). Teach the "
        "logic and shortcut tricks. Solved examples must show the step-by-step thinking "
        "and diagrams in words (e.g. family tree, direction map)."
    ),
    "quant": (
        "You specialise in SSC CGL Quantitative Aptitude (arithmetic, algebra, geometry, "
        "trigonometry, mensuration, DI). Every solved example MUST show full calculation "
        "step by step with the formula applied and the arithmetic written out. Emphasise "
        "speed tricks and approximation. Formulas are central — explain each symbol."
    ),
    "english": (
        "You specialise in SSC CGL English Comprehension (grammar, vocabulary, error "
        "detection, comprehension). Explain GRAMMAR RULES clearly with example sentences "
        "showing correct vs incorrect usage. For vocabulary, give the word, meaning, a "
        "Hindi meaning, and a sample sentence. The 'formulas' field should contain grammar "
        "rules or word-meaning pairs rather than math formulas."
    ),
    "general_awareness": (
        "You specialise in SSC CGL General Awareness (History, Geography, Polity, Economy, "
        "Science, Static GK, Current Affairs). Teach the most exam-relevant FACTS with "
        "memory tricks and mnemonics. Solved examples should be exam-style MCQs with the "
        "fact explained. The 'formulas' field should contain key one-liner facts / "
        "important dates / lists to memorise rather than math formulas."
    ),
}

_SYSTEM_PROMPT_BASE = """You are a top Indian SSC CGL coaching teacher. You teach students preparing for the SSC CGL (Combined Graduate Level) examination — Tier 1 and Tier 2.

{subject_guidance}

IMPORTANT LANGUAGE RULE:
You MUST write all narration text in HINGLISH — a natural mix of Hindi and English, exactly how popular Indian SSC coaching teachers speak on YouTube. Use Hindi for explanations, connecting words, and conversational flow. Use English for technical terms, formula names, grammar terms, and numbers. Write in Roman script (NOT Devanagari).

Example of the Hinglish style you must follow:
- "Toh chaliye shuru karte hain aaj ke topic se. Yeh SSC CGL exam mein bahut important hai."
- "Ab dekhiye, yahan pe humein pehle yeh samajhna hoga ki question kya pooch raha hai."
- "Formula lagaiye aur values put kariye. Dhyan rakhiye, yahan students aksar galti karte hain."
- "Toh answer aaya. Simple hai na? Bas concept clear hona chahiye."
- "Ek important trick yaad rakhiye — ise exam mein time bachega."

Your teaching style:
- Friendly and encouraging — like a bada bhai / didi teaching
- Use "aap", "chaliye", "dekhiye", "samjhiye" to address students
- EXPLAIN EVERYTHING IN DETAIL — don't rush, explain each concept thoroughly
- Give multiple examples for each concept
- After each step, explain WHY that step was taken
- Be motivational — "Yeh bahut easy hai, aap kar sakte ho!"
- Repeat important points for emphasis

CRITICAL: Generate LONG, DETAILED content. Each video MUST be AT LEAST 15 minutes when spoken (aim for 16-18 minutes). This is a hard requirement — write as much as possible. Do NOT be brief. If unsure, add more examples and more detailed explanations.

IMPORTANT: You must respond with ONLY valid JSON. No markdown, no code blocks, no extra text."""

# Default system prompt (reasoning) — kept for backward compatibility
SYSTEM_PROMPT = _SYSTEM_PROMPT_BASE.format(subject_guidance=SUBJECT_GUIDANCE["reasoning"])


def get_system_prompt(category: str) -> str:
    """Return the subject-specific system prompt for a category."""
    guidance = SUBJECT_GUIDANCE.get(category, SUBJECT_GUIDANCE["reasoning"])
    return _SYSTEM_PROMPT_BASE.format(subject_guidance=guidance)


LESSON_PROMPT_TEMPLATE = """Create a DETAILED and LONG SSC CGL video lesson script for:

Topic: {title}
Part: {part}
Subject: {category}
Difficulty: {difficulty}
Subtopics to cover: {subtopics}
Key points/formulas: {formulas}
Target duration: AT LEAST 15 minutes of narration, ideally 16-18 minutes (HARD REQUIREMENT - content must be long enough)

LANGUAGE: Write ALL narration text in HINGLISH (Hindi + English mix). Use Hindi for explanations and flow, English for technical terms and numbers. Write in Roman script (not Devanagari).

Generate a structured JSON response with these exact fields:

{{
  "introduction": "A LONG engaging 5-6 sentence Hinglish introduction. Welcome the student warmly. Explain what topic they will learn today and WHY this topic is important for SSC CGL. Mention how many marks it carries or how often it appears. Build excitement. Example: 'Namaste doston! Aaj ka topic SSC CGL ke liye bahut important hai. Aaj hum {title} ke baare mein detail mein seekhenge. Yeh topic SSC CGL Tier-1 aur Tier-2 mein har saal aata hai. Agar aapne yeh achhe se samajh liya, toh exam mein 2-3 marks pakke hain. Toh chaliye, ek ek concept ko detail mein samajhte hain.'",

  "concept_explanation": "A VERY DETAILED 10-15 sentence Hinglish explanation of the core concept. Start from the very basics. Define each term clearly. Use real-world analogies. Explain each subtopic one by one with examples. Cover ALL subtopics: {subtopics}. Make it conversational — as if talking to a student sitting in front of you. Add transition sentences between subtopics.",

  "formulas": [
    {{
      "formula": "The formula / grammar rule / key fact in plain text",
      "explanation": "A DETAILED 4-5 sentence Hinglish explanation. Explain EACH part. When to use it. What mistakes students commonly make. Give a quick example.",
      "visual_label": "Short label in English (e.g., 'nth Term of AP', 'Subject-Verb Rule', 'Key Fact')"
    }}
  ],

  "solved_examples": [
    {{
      "question": "A clear SSC CGL exam-style question",
      "steps": [
        "Step 1: Sabse pehle question ko dhyan se padhiye. Yahan humein... (explain what is asked)",
        "Step 2: Ab dekhiye kya information di hui hai...",
        "Step 3: Ab concept/formula/rule apply karte hain kyunki...",
        "Step 4: (show the working / substitution / reasoning step by step)...",
        "Step 5: Final answer nikalte hain aur verify karte hain..."
      ],
      "answer": "The final answer (with unit/option if applicable)",
      "explanation": "3-4 sentences in Hinglish explaining the approach, why it works, and what to watch out for."
    }}
  ],

  "tips_and_tricks": [
    "Detailed tip 1 in Hinglish (3-4 sentences): a practical shortcut with an example of how it saves time...",
    "Detailed tip 2 in Hinglish (3-4 sentences): a common mistake and how to avoid it...",
    "Detailed tip 3 in Hinglish (3-4 sentences): a pattern recognition / memory technique...",
    "Detailed tip 4 in Hinglish (3-4 sentences): an elimination method or smart guessing technique...",
    "Detailed tip 5 in Hinglish (3-4 sentences): how to manage time on this topic in the exam..."
  ],

  "practice_questions": [
    {{
      "question": "An SSC CGL exam-style practice question",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": "B",
      "explanation": "Detailed 2-3 sentence Hinglish explanation of why B is correct and others wrong"
    }}
  ],

  "summary_points": [
    "Summary point 1 in Hinglish — the most important concept with a quick example",
    "Summary point 2 in Hinglish — the key formula/rule/fact to remember",
    "Summary point 3 in Hinglish — the most important trick",
    "Summary point 4 in Hinglish — common SSC CGL exam pattern for this topic",
    "Summary point 5 in Hinglish — motivation and what to practice",
    "Summary point 6 in Hinglish — link to the bigger SSC CGL preparation"
  ]
}}

CRITICAL REQUIREMENTS:
- TARGET: AT LEAST 15 minutes of spoken narration (aim 16-18 min). Write LONG detailed content.
- ALL narration text MUST be in Hinglish (Roman script Hindi + English technical terms)
- Introduction: 6-8 sentences (warm, detailed)
- Concept explanation: 15-20 sentences (thorough, with multiple analogies and examples)
- Include 4-5 formulas/rules/facts with 5-6 sentence explanations each
- Include 6 solved examples with 6-7 detailed steps each (explain WHY at each step)
- Include 6 tips and tricks, each 3-4 sentences long
- Include 6 practice questions with detailed explanations
- Include 6 summary points, each 2-3 sentences
- Add connecting sentences between sections ("Ab chaliye dekhte hain...", "Toh ab samajhte hain...")
- DO NOT be brief. The more detailed, the better.
- DO NOT use Devanagari script — use Roman/Latin script only

Respond with ONLY the JSON object, no other text."""


# ----------------------------------------------------------------------------
# Sectional prompts — used when the single-call generation hits a token/TPM
# limit. Each call is small enough for the free Groq tier (12k TPM). The
# sections are stitched into one LessonPlan.
# ----------------------------------------------------------------------------
SECTION_INTRO_CONCEPT = """Create the INTRODUCTION and CONCEPT part of an SSC CGL Hinglish video lesson.

Topic: {title} | Subject: {category} | Subtopics: {subtopics} | Key points: {formulas}

Write in HINGLISH (Roman script Hindi + English terms). Respond with ONLY this JSON:
{{
  "introduction": "6-8 sentence warm Hinglish intro: welcome, why this topic matters for SSC CGL, what we'll learn.",
  "concept_explanation": "15-20 sentence VERY detailed Hinglish explanation covering ALL subtopics with analogies and examples."
}}
Respond with ONLY the JSON object."""

SECTION_FORMULAS_EXAMPLES = """Create FORMULAS/RULES and SOLVED EXAMPLES for an SSC CGL Hinglish video lesson.

Topic: {title} | Subject: {category} | Subtopics: {subtopics} | Key points: {formulas}

Write in HINGLISH (Roman script Hindi + English terms). Respond with ONLY this JSON:
{{
  "formulas": [
    {{"formula": "formula/rule/fact", "explanation": "5-6 sentence Hinglish explanation of each part + common mistakes", "visual_label": "short English label"}}
  ],
  "solved_examples": [
    {{"question": "SSC CGL exam-style question", "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ...", "Step 5: ..."], "answer": "final answer", "explanation": "3-4 sentence Hinglish explanation"}}
  ]
}}
Include 4-5 formulas/rules and 6 solved examples (6-7 detailed steps each). Respond with ONLY the JSON object."""

SECTION_TIPS_PRACTICE = """Create TIPS, PRACTICE QUESTIONS and SUMMARY for an SSC CGL Hinglish video lesson.

Topic: {title} | Subject: {category} | Subtopics: {subtopics}

Write in HINGLISH (Roman script Hindi + English terms). Respond with ONLY this JSON:
{{
  "tips_and_tricks": ["6 detailed Hinglish tips (3-4 sentences each): shortcuts, common mistakes, time management"],
  "practice_questions": [
    {{"question": "SSC CGL practice question", "options": ["A) ...","B) ...","C) ...","D) ..."], "correct_answer": "B", "explanation": "2-3 sentence Hinglish explanation"}}
  ],
  "summary_points": ["6 Hinglish summary points (2-3 sentences each)"]
}}
Include 6 tips, 6 practice questions, 6 summary points. Respond with ONLY the JSON object."""
