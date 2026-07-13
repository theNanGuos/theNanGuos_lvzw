import argparse

from agents.init import create_llm
from app.graph import build_graph


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


def main() -> None:
    args = parse_args()
    result = build_graph(create_llm()).invoke({"user_request": args.request})
    final_prompt = result["final_prompt"]
    print(final_prompt)

    if args.generate:
        from lib.suno import generate

        generate(
            final_prompt,
            instrumental=result["workflow"] == "classical_instrumental",
        )


if __name__ == "__main__":
    main()
