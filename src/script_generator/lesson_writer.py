"""
Lesson Writer - Generates structured lesson content using LLM
"""

import json
import re
from typing import Optional

from .llm_client import LLMClient
from .prompt_templates import (
    get_system_prompt, LESSON_PROMPT_TEMPLATE,
    SECTION_INTRO_CONCEPT, SECTION_FORMULAS_EXAMPLES, SECTION_TIPS_PRACTICE,
)
from src.syllabus.topic_models import Topic, LessonPlan, FormulaBlock, Example, Question
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LessonWriter:
    """Generates complete lesson plans from topics using LLM.

    Strategy:
      1. Try ONE big call (works on a paid/high-TPM Groq key -> longest content).
      2. If that fails (e.g. free-tier 12k TPM 413), fall back to THREE smaller
         sectional calls and stitch them. Each section stays under the limit so
         a full 15+ min lesson is still produced.
      3. If everything fails, use a basic template lesson.
    """

    def __init__(self, provider: str = "groq", max_tokens: int = 8000, **llm_kwargs):
        self.llm = LLMClient(provider=provider, **llm_kwargs)
        self.max_tokens = max_tokens
        logger.info(f"LessonWriter initialized (max_tokens={max_tokens})")

    def _fmt(self, template: str, topic: Topic) -> str:
        return template.format(
            title=topic.title,
            part=topic.part,
            category=topic.category_display,
            difficulty=topic.difficulty,
            subtopics=", ".join(topic.subtopics),
            formulas=", ".join(topic.formulas) if topic.formulas else "No specific formulas",
            duration_target=topic.duration_target_minutes,
        )

    # ~15 spoken Hindi minutes needs roughly this many narration characters.
    # (Gemini Hindi voice ~ 950 chars/min after the 0.92x slow-down.)
    MIN_NARRATION_CHARS = 13000

    def generate_lesson(self, topic: Topic, max_retries: int = 2) -> LessonPlan:
        """Generate a complete lesson plan, ensuring ~15+ minutes of content."""
        system = get_system_prompt(topic.category)

        # --- Attempt 1: single big call ---
        prompt = self._fmt(LESSON_PROMPT_TEMPLATE, topic)
        single = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating lesson (single-call) Part {topic.part} attempt {attempt + 1}")
                response = self.llm.generate(
                    prompt=prompt, system_prompt=system,
                    max_tokens=self.max_tokens, temperature=0.7,
                )
                data = self._parse_response(response)
                if data and data.get("concept_explanation"):
                    single = self._build_lesson_plan(topic, data)
                    chars = len(single.get_narration_text())
                    logger.info(f"Single-call lesson: {chars} chars")
                    if chars >= self.MIN_NARRATION_CHARS:
                        return single  # long enough — done
                    logger.info("Single-call too short for 15 min — using sectional generation")
                    break
                logger.warning("Single-call response unparseable/incomplete")
            except Exception as e:
                logger.warning(f"Single-call failed ({e}); falling back to sectional generation")
                break

        # --- Attempt 2: sectional generation (3 calls -> longer, free-tier friendly) ---
        try:
            sectional = self._generate_sectional(topic, system)
            if sectional and sectional.concept_explanation:
                chars = len(sectional.get_narration_text())
                logger.info(f"Sectional lesson: {chars} chars")
                # Pick whichever is longer (sectional usually wins)
                if single and len(single.get_narration_text()) > chars:
                    return single
                return sectional
        except Exception as e:
            logger.error(f"Sectional generation failed: {e}")

        if single:
            return single  # better than the template fallback
        logger.warning(f"Using fallback lesson for Part {topic.part}")
        return self._create_fallback_lesson(topic)

    def _generate_sectional(self, topic: Topic, system: str) -> LessonPlan:
        """Generate the lesson in 3 smaller calls and merge."""
        merged = {}
        section_tokens = min(self.max_tokens, 7000)  # keep each call under free TPM
        for name, tmpl in [
            ("intro_concept", SECTION_INTRO_CONCEPT),
            ("formulas_examples", SECTION_FORMULAS_EXAMPLES),
            ("tips_practice", SECTION_TIPS_PRACTICE),
        ]:
            logger.info(f"  Sectional call: {name}")
            resp = self.llm.generate(
                prompt=self._fmt(tmpl, topic), system_prompt=system,
                max_tokens=section_tokens, temperature=0.7,
            )
            part_data = self._parse_response(resp) or {}
            merged.update(part_data)
        return self._build_lesson_plan(topic, merged)

    def _parse_response(self, response: str) -> Optional[dict]:
        """Parse LLM response as JSON."""
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object boundaries
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from response: {response[:200]}...")
        return None

    def _build_lesson_plan(self, topic: Topic, data: dict) -> LessonPlan:
        """Build a LessonPlan from parsed JSON data."""
        formulas = []
        for f in data.get("formulas", []):
            formulas.append(FormulaBlock(
                formula=f.get("formula", ""),
                explanation=f.get("explanation", ""),
                visual_label=f.get("visual_label", ""),
            ))

        examples = []
        for e in data.get("solved_examples", []):
            examples.append(Example(
                question=e.get("question", ""),
                steps=e.get("steps", []),
                answer=e.get("answer", ""),
                explanation=e.get("explanation", ""),
            ))

        questions = []
        for q in data.get("practice_questions", []):
            questions.append(Question(
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
            ))

        return LessonPlan(
            topic=topic,
            introduction=data.get("introduction", ""),
            concept_explanation=data.get("concept_explanation", ""),
            formulas=formulas,
            solved_examples=examples,
            tips_and_tricks=data.get("tips_and_tricks", []),
            practice_questions=questions,
            summary_points=data.get("summary_points", []),
        )

    def _create_fallback_lesson(self, topic: Topic) -> LessonPlan:
        """Create a basic lesson plan when LLM fails."""
        return LessonPlan(
            topic=topic,
            introduction=f"Namaste doston! Aaj hum {topic.title} seekhenge. Yeh topic SSC CGL exam ke liye bahut important hai.",
            concept_explanation=f"{topic.title} is a key topic in {topic.category_display}. It covers: {', '.join(topic.subtopics)}. Let's understand each concept step by step.",
            formulas=[
                FormulaBlock(
                    formula=f,
                    explanation=f"This formula is essential for solving {topic.title} problems.",
                    visual_label=f"Formula {i+1}"
                )
                for i, f in enumerate(topic.formulas[:3])
            ],
            solved_examples=[
                Example(
                    question=f"Example question on {sub}",
                    steps=["Step 1: Identify the pattern", "Step 2: Apply the concept", "Step 3: Verify the answer"],
                    answer="See the detailed solution",
                    explanation="This approach works because it follows the standard method."
                )
                for sub in topic.subtopics[:3]
            ],
            tips_and_tricks=[
                "Always read the question carefully before solving",
                "Look for patterns and shortcuts",
                "Practice with a timer to improve speed",
            ],
            practice_questions=[],
            summary_points=[
                f"{topic.title} is essential for competitive exams",
                "Practice regularly with timed exercises",
                "Review formulas before the exam",
            ],
        )
