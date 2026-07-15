import argparse

from agents.init import create_llm
from app.graph import build_graph
from lib.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local music agent workflow")
    parser.add_argument(
        "request",
        nargs="?",
        default="生成一首钢琴协奏曲，风格恢弘壮阔，长度在三分钟左右",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="submit the final prompt to the configured music provider",
    )
    return parser.parse_args()


def brief_value(brief: object, field: str, default: object = None) -> object:
    if isinstance(brief, dict):
        return brief.get(field, default)
    return getattr(brief, field, default)


def main() -> None:
    setup_logging("cli")
    args = parse_args()
    logger.info("cli_workflow_started generate=%s", args.generate)
    result = build_graph(create_llm()).invoke({"user_request": args.request})
    final_prompt = result["final_prompt"]
    print(final_prompt)
    logger.info("cli_workflow_completed workflow=%s", result.get("workflow"))

    if args.generate:
        from lib.suno import generate

        brief = result.get("creative_brief")
        style_parts = []
        title = None
        if brief:
            title = brief_value(brief, "title")
            style_parts.extend(
                [
                    brief_value(brief, "genre", ""),
                    brief_value(brief, "production_style", ""),
                ]
            )
            style_parts.extend(brief_value(brief, "mood", []) or [])

        generate(
            final_prompt,
            instrumental=result["workflow"] == "classical_instrumental",
            style=", ".join(str(part) for part in style_parts if part),
            title=str(title) if title else None,
        )
        logger.info("cli_music_generation_completed")


if __name__ == "__main__":
    main()
