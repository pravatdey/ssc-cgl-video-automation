"""
Thumbnail Generator - Uses the channel's branded base image (assets/thumbnail_base.png)
and overlays the dynamic per-video info: subject, topic title, and part number.

The base image already carries the channel branding ("SSC CGL MARATHON",
the presenter photo and @CivilPrepHub logo on the right). We only add a clean
lower-left text band so each video is identifiable while branding stays intact.
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .visual_themes import Colors, Fonts
from .slide_renderer import hex_to_rgb
from src.syllabus.topic_models import Topic
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Branded base thumbnail supplied by the channel owner
BASE_IMAGE_PATH = "assets/thumbnail_base.png"


class ThumbnailGenerator:
    """Generates thumbnails from a branded base image plus per-video overlay text."""

    def __init__(self):
        self.width = 1280
        self.height = 720
        self._font_cache = {}

    def _get_font(self, font_file: str, size: int) -> ImageFont.FreeTypeFont:
        key = (font_file, size)
        if key not in self._font_cache:
            paths = [
                f"assets/fonts/{font_file}",
                f"C:/Windows/Fonts/{font_file}",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                font_file,
            ]
            for p in paths:
                if os.path.exists(p):
                    self._font_cache[key] = ImageFont.truetype(p, size)
                    return self._font_cache[key]
            self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_outlined_text(self, draw, position, text, font, fill,
                            outline_color=(0, 0, 0), outline_width=4):
        x, y = position
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=fill)

    def _wrap(self, draw, text, font, max_width):
        words = text.split()
        lines, current = [], ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def generate(self, topic: Topic, output_path: str) -> str:
        """Compose the final thumbnail from the branded base + topic overlay."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # --- Load branded base image (fallback to plain dark canvas) ---
        try:
            img = Image.open(BASE_IMAGE_PATH).convert("RGB")
            img = img.resize((self.width, self.height), Image.LANCZOS)
        except Exception as e:
            logger.warning(f"Base thumbnail image missing ({e}); using plain background")
            img = Image.new("RGB", (self.width, self.height), hex_to_rgb(Colors.BG_PRIMARY))

        draw = ImageDraw.Draw(img, "RGBA")
        accent_rgb = hex_to_rgb(Colors.get_accent(topic.category))

        # --- Lower-left dark band for readable overlay text ---
        band_top = int(self.height * 0.66)
        band_w = int(self.width * 0.60)
        band = Image.new("RGBA", (band_w, self.height - band_top), (0, 0, 0, 200))
        img.paste(Image.alpha_composite(
            img.crop((0, band_top, band_w, self.height)).convert("RGBA"), band
        ).convert("RGB"), (0, band_top))
        draw = ImageDraw.Draw(img, "RGBA")

        # --- Subject badge (top of band, colored by subject) ---
        subject_text = topic.category_display.upper()
        badge_font = self._get_font(Fonts.BOLD, 30)
        bbox = draw.textbbox((0, 0), subject_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 36
        bx, by = 45, band_top + 18
        draw.rounded_rectangle([bx, by, bx + bw, by + 46], radius=12, fill=accent_rgb)
        draw.text((bx + 18, by + 8), subject_text, fill=(255, 255, 255), font=badge_font)

        # --- Part number pill (right of badge) ---
        part_text = f"PART {topic.part}"
        part_font = self._get_font(Fonts.BOLD, 30)
        pbbox = draw.textbbox((0, 0), part_text, font=part_font)
        pw = pbbox[2] - pbbox[0] + 36
        px = bx + bw + 14
        draw.rounded_rectangle([px, by, px + pw, by + 46], radius=12,
                               fill=hex_to_rgb(Colors.YELLOW))
        draw.text((px + 18, by + 8), part_text, fill=(0, 0, 0), font=part_font)

        # --- Topic title (big, wrapped) ---
        title_font = self._get_font(Fonts.BOLD, 52)
        title_lines = self._wrap(draw, topic.title.upper(), title_font,
                                 band_w - 70)[:2]
        ty = by + 60
        for line in title_lines:
            self._draw_outlined_text(draw, (45, ty), line, title_font,
                                     fill=(255, 255, 255), outline_width=4)
            ty += 60

        img.save(output_path, "PNG", quality=95)
        logger.info(f"Thumbnail generated from branded base: {output_path}")
        return output_path
