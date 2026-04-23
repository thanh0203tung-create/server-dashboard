"""
Colors and Themes for the Terminal UI
"""

# Color palette
class Colors:
    # Basic colors
    DEFAULT = 'default'
    BLACK = 'black'
    DARK_RED = 'dark red'
    DARK_GREEN = 'dark green'
    BROWN = 'brown'
    DARK_BLUE = 'dark blue'
    DARK_MAGENTA = 'dark magenta'
    DARK_CYAN = 'dark cyan'
    LIGHT_GRAY = 'light gray'
    DARK_GRAY = 'dark gray'
    RED = 'red'
    GREEN = 'green'
    YELLOW = 'yellow'
    BLUE = 'blue'
    MAGENTA = 'magenta'
    CYAN = 'cyan'
    WHITE = 'white'

    # Custom colors for the app
    HEADER_BG = 'dark blue'
    HEADER_FG = 'white'

    # Status colors
    SUCCESS = 'green'
    WARNING = 'yellow'
    ERROR = 'red'
    INFO = 'cyan'

    # CPU/Memory indicators
    CPU_LOW = 'green'
    CPU_MEDIUM = 'yellow'
    CPU_HIGH = 'red'

    MEMORY_LOW = 'green'
    MEMORY_MEDIUM = 'yellow'
    MEMORY_HIGH = 'red'

    # Service states
    SERVICE_RUNNING = 'green'
    SERVICE_STOPPED = 'dark gray'
    SERVICE_FAILED = 'red'

    # Container states
    CONTAINER_RUNNING = 'green'
    CONTAINER_EXITED = 'dark gray'
    CONTAINER_PAUSED = 'yellow'
    CONTAINER_DEAD = 'red'

    # Pod states
    POD_RUNNING = 'green'
    POD_PENDING = 'yellow'
    POD_FAILED = 'red'

# Theme definitions
class Theme:
    @staticmethod
    def get_cpu_color(percent: float) -> str:
        if percent >= 90:
            return Colors.CPU_HIGH
        elif percent >= 70:
            return Colors.CPU_MEDIUM
        return Colors.CPU_LOW

    @staticmethod
    def get_memory_color(percent: float) -> str:
        if percent >= 90:
            return Colors.MEMORY_HIGH
        elif percent >= 70:
            return Colors.MEMORY_MEDIUM
        return Colors.MEMORY_LOW

    @staticmethod
    def get_service_color(state: str) -> str:
        state_lower = state.lower()
        if state_lower == 'active':
            return Colors.SERVICE_RUNNING
        elif state_lower == 'failed':
            return Colors.SERVICE_FAILED
        return Colors.SERVICE_STOPPED

    @staticmethod
    def get_container_color(state: str) -> str:
        state_lower = state.lower()
        if state_lower == 'running':
            return Colors.CONTAINER_RUNNING
        elif state_lower == 'exited':
            return Colors.CONTAINER_EXITED
        elif state_lower == 'paused':
            return Colors.CONTAINER_PAUSED
        elif state_lower == 'dead':
            return Colors.CONTAINER_DEAD
        return Colors.DEFAULT

    @staticmethod
    def get_log_level_color(level: str) -> str:
        level_upper = level.upper()
        if level_upper in ('ERROR', 'ERR', 'CRITICAL', 'CRIT', 'ALERT', 'EMERGENCY'):
            return Colors.ERROR
        elif level_upper in ('WARNING', 'WARN'):
            return Colors.WARNING
        elif level_upper in ('INFO', 'NOTICE'):
            return Colors.INFO
        elif level_upper == 'DEBUG':
            return Colors.BLUE
        return Colors.DEFAULT

# UI Constants
class UIConstants:
    BOX_CHAR = {
        'top_left': '+',
        'top_right': '+',
        'bottom_left': '+',
        'bottom_right': '+',
        'horizontal': '-',
        'vertical': '|'
    }

    INDICATOR = {
        'arrow_up': '^',
        'arrow_down': 'v',
        'arrow_left': '<',
        'arrow_right': '>',
        'bullet': '*',
        'dot': '.',
        'checkbox': '[ ]',
        'checkbox_checked': '[x]'
    }

# Progress bar styles
def create_progress_bar(percent: float, width: int = 20, show_text: bool = True) -> str:
    """Create a text-based progress bar"""
    filled = int(width * percent / 100)
    empty = width - filled

    if percent >= 90:
        color = Colors.RED
    elif percent >= 70:
        color = Colors.YELLOW
    else:
        color = Colors.GREEN

    bar = '[' + '#' * filled + ' ' * empty + ']'

    if show_text:
        bar += f' {percent:.1f}%'

    return bar

# Header styles
HEADER_STYLE = {
    'align': 'center',
    'wrap': 'clip',
    'attr': Colors.HEADER_BG
}

MENU_ITEM_ACTIVE = {
    'align': 'center',
    'wrap': 'clip',
    'attr': Colors.BLUE
}

MENU_ITEM_INACTIVE = {
    'align': 'center',
    'wrap': 'clip',
    'attr': Colors.DEFAULT
}
