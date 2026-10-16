"""Run the extraction evaluation over the golden cases and append the results.

    cd apps/api && uv run python evals/intake_eval.py --provider text-layer --runs 5
    cd apps/api && INTAKE_MODEL_ID=claude-haiku-5-5 ANTHROPIC_API_KEY=… \\
        uv run python evals/intake_eval.py --provider model --runs 5
    cd apps/api && INTAKE_MODEL_BACKEND=openai_compatible \\
        INTAKE_MODEL_BASE_URL=http://127.0.0.1:11434/v1 INTAKE_MODEL_ID=qwen2.5vl:7b \\
        uv run python evals/intake_eval.py --provider model

Results go to evals/results/intake_eval_results.jsonl (append-only; part of the evidence
trail — never overwrite it) and a Markdown table to stdout (or --report FILE). Two providers
or two models are compared by running the script twice and reading the two blocks of lines.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from hadp_api.config import get_settings  # noqa: E402
from hadp_api.modules.intake import evaluation  # noqa: E402
from hadp_api.modules.intake.pages import OCR_TESSERACT, TesseractEngine  # noqa: E402
from hadp_api.modules.intake.providers import get_provider  # noqa: E402

DEFAULT_CASES = HERE.parent / "tests" / "intake_cases"
DEFAULT_RESULTS = HERE / "results" / "intake_eval_results.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--provider", default="text-layer", help="text-layer or model")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=None, help="write the Markdown table here")
    parser.add_argument("--ocr", default="off", help="off or tesseract (scanned pages only)")
    parser.add_argument("--only", default=None, help="run one case directory by name")
    args = parser.parse_args(argv)

    settings = get_settings()
    provider = get_provider(args.provider, settings)
    ocr = TesseractEngine(settings.intake_ocr_languages) if args.ocr == OCR_TESSERACT else None
    case_dirs = sorted(p for p in args.cases.iterdir() if (p / "input" / "truth.json").exists())
    if args.only:
        case_dirs = [p for p in case_dirs if p.name == args.only]
    entries = []
    for case_dir in case_dirs:
        result = evaluation.evaluate_case(case_dir, provider, settings, runs=args.runs, ocr=ocr)
        entries.append(
            evaluation.record(args.results, provider=provider, result=result, ocr_name=args.ocr)
        )
        print(f"{case_dir.name}: {result.summary()}", file=sys.stderr)
    table = (
        f"## {provider.name} · {provider.model_id} · {provider.prompt_version} · "
        f"{args.runs} runs · OCR {args.ocr}\n\n" + evaluation.report_table(entries) + "\n"
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("a", encoding="utf-8") as fh:
            fh.write(table + "\n")
    print(table)
    print(f"appended {len(entries)} record(s) to {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
