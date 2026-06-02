"""
SSC CGL Video Pipeline - Generates and uploads one lesson video per run.

Two release slots per day:
    --slot morning   -> next Reasoning/Quant topic   (scheduled 5:00 AM IST)
    --slot evening   -> next English/GA topic         (scheduled 5:00 PM IST)

progress.json tracks two independent sequences (morning_next, evening_next).

Usage:
    python main.py --slot morning              # next morning topic, upload public
    python main.py --slot evening              # next evening topic, upload public
    python main.py --part 1 --no-upload        # generate a specific part, no upload
    python main.py --slot morning --test       # upload as private (test)
    python main.py --progress                  # show progress
"""

import argparse
import asyncio
import json
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.syllabus.syllabus_manager import SyllabusManager
from src.script_generator.lesson_writer import LessonWriter
from src.tts.tts_manager import TTSManager
from src.video.composer import VideoComposer
from src.video.thumbnail import ThumbnailGenerator
from src.youtube.auth import YouTubeAuth
from src.youtube.uploader import YouTubeUploader
from src.youtube.metadata import MetadataGenerator
from src.youtube.comment_poster import CommentPoster
from src.youtube.playlist_manager import PlaylistManager
from src.utils.database import Database
from src.utils.logger import setup_logger, get_logger

PROGRESS_FILE = "progress.json"
MIN_DURATION_SEC = 15 * 60  # hard minimum video length: 15 minutes


class CGLVideoPipeline:
    """Topic -> Script -> Audio -> Video -> Upload -> Comment -> Playlist."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        setup_logger(log_file="logs/pipeline.log")
        self.logger = get_logger("Pipeline")

        db_path = self.config.get("database", {}).get("path", "data/cgl_tracker.db")
        self.db = Database(db_path)

        syllabus_path = self.config.get("syllabus", {}).get("file", "config/syllabus.yaml")
        self.syllabus = SyllabusManager(syllabus_path, self.db)
        self.total_parts = self.config.get("syllabus", {}).get("total_parts", 320)

        llm_config = self.config.get("llm", {})
        groq_cfg = llm_config.get("groq", {})
        self.lesson_writer = LessonWriter(
            provider=llm_config.get("provider", "groq"),
            model=groq_cfg.get("model", "llama-3.3-70b-versatile"),
            max_tokens=groq_cfg.get("max_tokens", 8000),
        )

        self.tts = TTSManager(config_path)
        self.composer = VideoComposer(self.config)
        self.thumbnail_gen = ThumbnailGenerator()
        self.metadata_gen = MetadataGenerator()

        self._yt_auth = None
        self._uploader = None
        self._comment_poster = None
        self._playlist_mgr = None

        self.logger.info("CGL pipeline initialized")

    # ---- lazy YouTube components ----
    @property
    def yt_auth(self):
        if not self._yt_auth:
            self._yt_auth = YouTubeAuth()
        return self._yt_auth

    @property
    def uploader(self):
        if not self._uploader:
            self._uploader = YouTubeUploader(self.yt_auth)
        return self._uploader

    @property
    def comment_poster(self):
        if not self._comment_poster:
            self._comment_poster = CommentPoster(self.yt_auth)
        return self._comment_poster

    @property
    def playlist_mgr(self):
        if not self._playlist_mgr:
            self._playlist_mgr = PlaylistManager(self.yt_auth)
        return self._playlist_mgr

    # ---- progress (two independent slot sequences) ----
    def _read_progress(self) -> dict:
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _next_part_for_slot(self, slot: str) -> int:
        """Return the next part to publish for a slot, seeding from the syllabus."""
        data = self._read_progress()
        key = f"{slot}_next"
        if key in data and data[key]:
            return data[key]
        # seed: first part of that slot
        return self.syllabus.get_first_part_for_slot(slot)

    def _save_progress(self, slot: str, completed_part: int) -> None:
        data = self._read_progress()
        data.setdefault("completed", [])
        if completed_part not in data["completed"]:
            data["completed"].append(completed_part)
        data["completed"] = sorted(data["completed"])

        nxt = self.syllabus.get_next_part_for_slot(slot, completed_part)
        data[f"{slot}_next"] = nxt  # may be None if the slot sequence is finished

        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Progress saved: {slot}_next={nxt}")

    # ---- main run ----
    async def run(self, slot: str = None, part_number: int = None,
                  upload: bool = True, test_mode: bool = False) -> dict:
        result = {"success": False, "part": 0, "slot": slot}

        try:
            # Step 1: pick topic
            if part_number:
                topic = self.syllabus.get_topic_by_part(part_number)
                slot = slot or (topic.slot if topic else "morning")
            else:
                if not slot:
                    raise ValueError("Either --slot or --part is required")
                next_part = self._next_part_for_slot(slot)
                if not next_part:
                    self.logger.info(f"Slot '{slot}' sequence complete — nothing to publish")
                    result["success"] = True
                    result["done"] = True
                    return result
                topic = self.syllabus.get_topic_by_part(next_part)

            if not topic:
                self.logger.error("No topic available")
                return result

            result["part"] = topic.part
            self.logger.info(f"=== [{slot}] Part {topic.part}: {topic.title} ({topic.category}) ===")
            self.db.create_lesson_record(topic.part, topic.title, topic.category)

            # Step 2: script
            self.logger.info("Step 2: Generating lesson script...")
            lesson = self.lesson_writer.generate_lesson(topic)

            output_config = self.config.get("output", {})
            script_path = Path(output_config.get("script_dir", "output/scripts")) / f"part_{topic.part:03d}_script.json"
            script_path.parent.mkdir(parents=True, exist_ok=True)
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump(self._lesson_to_dict(topic, lesson), f, indent=2, ensure_ascii=False)
            self.db.update_lesson_status(topic.part, "generated", script_path=str(script_path))

            # Step 3: audio
            self.logger.info("Step 3: Generating audio...")
            audio_dir = output_config.get("audio_dir", "output/audio")
            narration_text = lesson.get_narration_text()
            audio_result = await self.tts.generate_lesson_audio(narration_text, audio_dir, topic.part)
            if not audio_result.get("success"):
                raise RuntimeError(f"Audio generation failed: {audio_result.get('error')}")
            audio_path = audio_result["audio_path"]
            duration = audio_result.get("duration", 0)
            self.db.update_lesson_status(topic.part, "generated", audio_path=audio_path)

            # 15-minute floor check (warn — content length is driven by the LLM prompt)
            if duration and duration < MIN_DURATION_SEC:
                self.logger.warning(
                    f"Audio is {duration/60:.1f} min — below the 15 min target. "
                    f"Consider regenerating; the prompt asks for 15-18 min of content."
                )

            # Step 4: video
            self.logger.info("Step 4: Composing video...")
            video_path = str(Path(output_config.get("video_dir", "output/videos")) / f"part_{topic.part:03d}.mp4")
            self.composer.compose(lesson, audio_path, video_path)
            self.db.update_lesson_status(topic.part, "generated", video_path=video_path, duration=duration)
            result["video_path"] = video_path

            # Step 5: thumbnail (uses branded base image + topic overlay)
            self.logger.info("Step 5: Generating thumbnail...")
            thumb_path = str(Path(output_config.get("thumbnail_dir", "output/thumbnails")) / f"part_{topic.part:03d}_thumb.png")
            self.thumbnail_gen.generate(topic, thumb_path)
            self.db.update_lesson_status(topic.part, "generated", thumbnail_path=thumb_path)
            result["thumbnail_path"] = thumb_path

            if not upload:
                self.logger.info(f"Video generated (no upload): {video_path}")
                result["success"] = True
                return result

            # Step 6: upload (public)
            self.logger.info("Step 6: Uploading to YouTube...")
            privacy = "private" if test_mode else self.config.get("youtube", {}).get("privacy_status", "public")
            metadata = self.metadata_gen.generate(topic, lesson)
            upload_result = self.uploader.upload(
                video_path=video_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                category_id=metadata["category_id"],
                privacy_status=privacy,
                thumbnail_path=thumb_path,
                made_for_kids=metadata["made_for_kids"],
            )
            if not upload_result.success:
                raise RuntimeError(f"Upload failed: {upload_result.error}")

            video_id = upload_result.video_id
            self.db.update_lesson_status(topic.part, "uploaded",
                                         youtube_id=video_id, youtube_url=upload_result.video_url)
            result["youtube_url"] = upload_result.video_url

            # Step 7: playlist
            self.logger.info("Step 7: Adding to playlist...")
            self.playlist_mgr.add_video(video_id)

            # Step 8: pinned study-notes + practice-questions comment (+ answer-key reply)
            self.logger.info("Step 8: Posting study notes & practice questions comment...")
            comment_id = self.comment_poster.post_study_notes(video_id, lesson)
            if comment_id:
                self.db.update_lesson_status(topic.part, "uploaded", comment_id=comment_id)

            progress = self.db.get_progress()
            self.playlist_mgr.update_description(progress["uploaded"], total=self.total_parts)

            # Save slot progress for the next run
            self._save_progress(slot, topic.part)

            self.logger.info(f"=== [{slot}] Part {topic.part} COMPLETE: {upload_result.video_url} ===")
            result["success"] = True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            result["error"] = str(e)
            if result.get("part"):
                self.db.update_lesson_status(result["part"], "failed", error=str(e))

        return result

    @staticmethod
    def _lesson_to_dict(topic, lesson) -> dict:
        return {
            "part": topic.part,
            "title": topic.title,
            "category": topic.category,
            "slot": topic.slot,
            "introduction": lesson.introduction,
            "concept": lesson.concept_explanation,
            "formulas": [{"formula": f.formula, "explanation": f.explanation,
                          "label": f.visual_label} for f in lesson.formulas],
            "examples": [{"question": e.question, "steps": e.steps,
                          "answer": e.answer, "explanation": e.explanation}
                         for e in lesson.solved_examples],
            "tips": lesson.tips_and_tricks,
            "practice": [{"question": q.question, "options": q.options,
                          "correct": q.correct_answer, "explanation": q.explanation}
                         for q in lesson.practice_questions],
            "summary": lesson.summary_points,
        }


def main():
    parser = argparse.ArgumentParser(description="SSC CGL Video Pipeline")
    parser.add_argument("--slot", choices=["morning", "evening"], help="Release slot")
    parser.add_argument("--part", type=int, help="Specific part number to generate")
    parser.add_argument("--no-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--test", action="store_true", help="Upload as private (test)")
    parser.add_argument("--progress", action="store_true", help="Show progress")
    args = parser.parse_args()

    pipeline = CGLVideoPipeline()

    if args.progress:
        p = pipeline.syllabus.get_progress()
        prog = pipeline._read_progress()
        print("\n=== SSC CGL Preparation Progress ===")
        print(f"Total Topics : {p['total_topics']}")
        print(f"Completed    : {p['completed']} ({p['percentage']}%)")
        print(f"Morning next : Part {prog.get('morning_next', pipeline.syllabus.get_first_part_for_slot('morning'))}")
        print(f"Evening next : Part {prog.get('evening_next', pipeline.syllabus.get_first_part_for_slot('evening'))}")
        return

    result = asyncio.run(pipeline.run(
        slot=args.slot,
        part_number=args.part,
        upload=not args.no_upload,
        test_mode=args.test,
    ))

    if result["success"]:
        if result.get("done"):
            print(f"\nSlot '{result['slot']}' sequence complete — no more topics.")
        else:
            print(f"\n[{result.get('slot')}] Part {result['part']} generated successfully!")
            if result.get("youtube_url"):
                print(f"YouTube: {result['youtube_url']}")
            if result.get("video_path"):
                print(f"Video: {result['video_path']}")
    else:
        print(f"\nFailed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
