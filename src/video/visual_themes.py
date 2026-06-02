"""
Visual Themes - Colors, typography, and layout constants for video rendering
"""


class Colors:
    """Color palette for the video UI — vibrant, modern edtech look"""

    # Background — rich dark with subtle blue/purple tint
    BG_PRIMARY = "#0A0E1A"
    BG_SECONDARY = "#0F1629"
    BG_CARD = "#151C30"
    BG_CARD_LIGHT = "#1C2540"
    BG_GRADIENT_TOP = "#0D1224"
    BG_GRADIENT_BOTTOM = "#0A1628"

    # --- SSC CGL subject themes (4 subjects) ---
    # Reasoning — vibrant cyan/blue
    REASONING_ACCENT = "#00D4FF"
    REASONING_SECONDARY = "#0099DD"
    REASONING_GLOW = "#00D4FF"

    # Quantitative Aptitude — vibrant green
    QUANT_ACCENT = "#10E08C"
    QUANT_SECONDARY = "#0FB873"
    QUANT_GLOW = "#10E08C"

    # English — warm orange
    ENGLISH_ACCENT = "#FB923C"
    ENGLISH_SECONDARY = "#EA7B22"
    ENGLISH_GLOW = "#FB923C"

    # General Awareness — vibrant purple/magenta
    GA_ACCENT = "#A855FF"
    GA_SECONDARY = "#8B2FE8"
    GA_GLOW = "#A855FF"

    # Backward-compatible aliases
    VR_ACCENT = REASONING_ACCENT
    VR_SECONDARY = REASONING_SECONDARY
    VR_GRADIENT_START = "#001a33"
    VR_GLOW = REASONING_GLOW
    VR_HIGHLIGHT = "#00FFE0"
    AR_ACCENT = GA_ACCENT
    AR_SECONDARY = GA_SECONDARY
    AR_GRADIENT_START = "#1a0033"
    AR_GLOW = GA_GLOW
    AR_HIGHLIGHT = "#E040FB"

    # Common
    WHITE = "#FFFFFF"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#C0CDE0"
    TEXT_DIM = "#8899AA"
    GREEN = "#10B981"
    GREEN_BRIGHT = "#34D399"
    GREEN_DARK = "#064E3B"
    RED = "#EF4444"
    RED_BRIGHT = "#FF6B6B"
    YELLOW = "#FBBF24"
    ORANGE = "#FB923C"
    PROGRESS_BG = "#1E2538"
    GOLD = "#FFD700"

    # Subject -> (accent, secondary, glow) lookup keyed by category
    @staticmethod
    def _theme(category: str):
        themes = {
            "reasoning": (Colors.REASONING_ACCENT, Colors.REASONING_SECONDARY, Colors.REASONING_GLOW),
            "quant": (Colors.QUANT_ACCENT, Colors.QUANT_SECONDARY, Colors.QUANT_GLOW),
            "english": (Colors.ENGLISH_ACCENT, Colors.ENGLISH_SECONDARY, Colors.ENGLISH_GLOW),
            "general_awareness": (Colors.GA_ACCENT, Colors.GA_SECONDARY, Colors.GA_GLOW),
        }
        return themes.get((category or "").lower(), themes["reasoning"])

    @staticmethod
    def get_accent(category: str) -> str:
        return Colors._theme(category)[0]

    @staticmethod
    def get_secondary(category: str) -> str:
        return Colors._theme(category)[1]

    @staticmethod
    def get_glow(category: str) -> str:
        return Colors._theme(category)[2]


class Fonts:
    """Font configuration — large readable text for YouTube"""

    # Font sizes — optimized for 1920x1080 Full HD YouTube viewing
    # YouTube compresses heavily — use larger, bolder text for readability
    TITLE = 96
    SECTION_LABEL = 60
    BODY = 64
    BODY_SMALL = 56
    FORMULA = 72
    SMALL = 44
    TINY = 36
    OPTION = 56
    STEP_NUMBER = 52
    BADGE = 38

    # Font families (will use system fonts or custom)
    BOLD = "arialbd.ttf"
    REGULAR = "arial.ttf"
    MONO = "consola.ttf"


class Layout:
    """Layout constants for 1920x1080 Full HD video"""

    # Video dimensions
    WIDTH = 1920
    HEIGHT = 1080

    # Margins
    MARGIN_X = 90
    MARGIN_Y = 30
    CONTENT_PADDING = 50

    # Top bar
    TOP_BAR_HEIGHT = 70
    PROGRESS_BAR_HEIGHT = 6
    PROGRESS_BAR_Y = 0

    # Content area
    CONTENT_TOP = 100
    CONTENT_BOTTOM = 1000
    CONTENT_WIDTH = WIDTH - 2 * MARGIN_X

    # Bottom bar
    BOTTOM_BAR_Y = 1005
    BOTTOM_BAR_HEIGHT = 75

    # Card dimensions
    CARD_PADDING = 28
    CARD_RADIUS = 16

    # Section header
    SECTION_HEADER_Y = 110

    # Formula box
    FORMULA_BOX_PADDING = 32
    FORMULA_BOX_MARGIN_Y = 24

    # Step circle
    STEP_CIRCLE_RADIUS = 24

    # Option card
    OPTION_HEIGHT = 95
    OPTION_GAP = 24
