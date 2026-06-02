"""
Syllabus Manager - Loads the SSC CGL syllabus (4 subjects) and supports
slot-aware topic selection for the two-videos-per-day schedule.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

from .topic_models import Topic
from src.utils.logger import get_logger
from src.utils.database import Database

logger = get_logger(__name__)


class SyllabusManager:
    """Loads the syllabus YAML and tracks progress through the database."""

    def __init__(self, config_path: str = "config/syllabus.yaml", db: Database = None):
        self.config_path = config_path
        self.db = db
        self.topics: Dict[int, Topic] = {}
        self._load_syllabus()

    def _load_syllabus(self) -> None:
        """Load all topics from syllabus YAML."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            syllabus = data.get("syllabus", {})
            sections = syllabus.get("sections", [])

            for section in sections:
                category = section.get("category", "reasoning")
                slot = section.get("slot", "morning")
                for topic_data in section.get("topics", []):
                    part = topic_data["part"]
                    self.topics[part] = Topic(
                        part=part,
                        title=topic_data["title"],
                        category=category,
                        slot=topic_data.get("slot", slot),
                        subtopics=topic_data.get("subtopics", []),
                        difficulty=topic_data.get("difficulty", "intermediate"),
                        formulas=topic_data.get("formulas", []),
                        duration_target_minutes=topic_data.get("duration_target_minutes", 12),
                    )

            logger.info(f"Loaded {len(self.topics)} topics from syllabus")

        except Exception as e:
            logger.error(f"Failed to load syllabus: {e}")
            raise

    def get_topic_by_part(self, part_number: int) -> Optional[Topic]:
        """Get a specific topic by part number."""
        topic = self.topics.get(part_number)
        if not topic:
            logger.warning(f"Topic not found for part {part_number}")
        return topic

    def get_all_topics(self) -> List[Topic]:
        """Get all topics sorted by part number."""
        return [self.topics[k] for k in sorted(self.topics.keys())]

    def get_topics_by_category(self, category: str) -> List[Topic]:
        """Get topics filtered by category."""
        return [t for t in self.get_all_topics() if t.category == category]

    def get_topics_by_slot(self, slot: str) -> List[Topic]:
        """Get topics for a release slot ('morning' or 'evening'), in part order."""
        return [t for t in self.get_all_topics() if t.slot == slot]

    def get_first_part_for_slot(self, slot: str) -> Optional[int]:
        """Return the lowest part number for a slot (used to seed progress)."""
        slot_topics = self.get_topics_by_slot(slot)
        return slot_topics[0].part if slot_topics else None

    def get_next_part_for_slot(self, slot: str, after_part: int) -> Optional[int]:
        """Return the next part number in the slot sequence after a given part."""
        slot_parts = [t.part for t in self.get_topics_by_slot(slot)]
        for p in slot_parts:
            if p > after_part:
                return p
        return None  # slot sequence finished

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress summary."""
        total = len(self.topics)
        db_progress = self.db.get_progress() if self.db else {}
        uploaded = db_progress.get("uploaded", 0)
        return {
            "total_topics": total,
            "completed": uploaded,
            "percentage": round(uploaded / total * 100, 1) if total else 0,
        }

    def mark_completed(self, part_number: int, video_id: str = "") -> None:
        """Mark a topic as completed."""
        if self.db:
            self.db.update_lesson_status(part_number, "uploaded", youtube_id=video_id)
            logger.info(f"Part {part_number} marked as completed")
