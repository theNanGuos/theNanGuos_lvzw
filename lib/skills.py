from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_DIR / "skills"


def read_skill(name: str) -> str:
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError(f"Invalid skill name: {name}")
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(f"Skill not found: {name}")
    return _strip_frontmatter(path.read_text(encoding="utf-8")).strip()


def with_skills(base_prompt: str, *skill_names: str) -> str:
    if not skill_names:
        return base_prompt
    loaded = "\n\n".join(
        f"## Skill: {name}\n{read_skill(name)}"
        for name in skill_names
    )
    return f"{base_prompt.rstrip()}\n\n# Loaded Skills\n{loaded}"


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    _, _, remainder = text.partition("\n---\n")
    return remainder if remainder else text
