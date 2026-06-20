import argparse

from gyaan.pipeline import GyaanPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the GYAAAN multi-model + web-search demo."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="What is the latest news about AI models?",
        help="Question to ask GYAAAN.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Show routing and model-mixing internals.",
    )
    parser.add_argument(
        "--deep-research",
        "--deep",
        action="store_true",
        help="Run multiple searches and produce an evidence-based research report.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the local browser interface.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Web server host.")
    parser.add_argument("--port", type=int, default=8000, help="Web server port.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.serve:
        from gyaan.web_app import serve

        serve(args.host, args.port)
        return

    pipeline = GyaanPipeline()
    run = pipeline.ask(args.question, deep_research=args.deep_research)

    print(run.final.answer)
    if args.trace:
        print("\n--- TRACE ---")
        print(run.final.trace)


if __name__ == "__main__":
    main()
