"""Command-line entry point.

    python run.py                      # process sample inbox, write to output/
    python run.py --rules              # force the offline rule engine
    python run.py --eval               # also score accuracy against labels
    python run.py --input my_inbox.json --out results/
"""

import argparse
from pathlib import Path

from intake.evaluate import evaluate, render_eval
from intake.pipeline import load_inquiries, process, write_outputs

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description="AI-assisted customer intake automation")
    p.add_argument("--input", default=ROOT / "sample_data" / "inquiries.json")
    p.add_argument("--labels", default=ROOT / "sample_data" / "labels.json")
    p.add_argument("--out", default=ROOT / "output")
    p.add_argument("--rules", action="store_true", help="use the offline rule engine even if an API key is set")
    p.add_argument("--eval", action="store_true", help="measure accuracy against hand-labeled answers")
    args = p.parse_args()

    records = process(load_inquiries(args.input), force_rules=args.rules)
    stats = write_outputs(records, args.out)

    print(f"Processed {stats['total']} inquiries using the '{stats['engine']}' engine")
    print(f"  Ready to send:      {stats['auto_ready']}")
    print(f"  Needs human review: {stats['needs_review']}")
    print(f"  Est. time saved:    {stats['minutes_saved']} min ({stats['pct_time_saved']}%)")

    if args.eval:
        result = evaluate(records, args.labels)
        Path(args.out, "accuracy.md").write_text(render_eval(result, stats["engine"]), encoding="utf-8")
        print(f"  Field accuracy:     {result['overall_accuracy']}%")

    print(f"\nOutputs written to {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
