from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

def read(path: Path) -> str:
    prompt = path.read_text(encoding="utf-8")
    return prompt


def chat() -> str:
    return read(PROJECT_DIR / "prompts" / "chat.md")

def conductor() -> str:
    path = PROJECT_DIR / "prompts" / "conductor.md"
    return read(path)
    

def lyrics() -> str:
    path = PROJECT_DIR / "prompts" / "lyrics.md"
    return read(path)

def melody() -> str:
    path = PROJECT_DIR / "prompts" / "melody.md"
    return read(path)

def arrange() -> str:
    path  = PROJECT_DIR / "prompts" / "arrange.md"
    return read(path)


def harmony() -> str:
    path = PROJECT_DIR / "prompts" / "harmony.md"
    return read(path)


def rhythm() -> str:
    path = PROJECT_DIR / "prompts" / "rhythm.md"
    return read(path)


def improvisation() -> str:
    path = PROJECT_DIR / "prompts" / "improvisation.md"
    return read(path)


def performance() -> str:
    path = PROJECT_DIR / "prompts" / "performance.md"
    return read(path)


def sound_design() -> str:
    path = PROJECT_DIR / "prompts" / "sound_design.md"
    return read(path)


def mix_review() -> str:
    path = PROJECT_DIR / "prompts" / "mix_review.md"
    return read(path)


def prompt_compiler() -> str:
    path = PROJECT_DIR / "prompts" / "prompt_compiler.md"
    return read(path)
