"""Run deal_finder's funnel over a JSON list of property records and
print a summary of each stage's survivors.

Usage:
    python scripts/run_deal_funnel.py [path/to/properties.json]

Defaults to sample_properties.json in the repo root.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deal_finder import analyze_property, run_funnel


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "sample_properties.json"
    with open(path) as f:
        properties = json.load(f)

    stage_sizes = tuple(size for size in (500, 100, 25, 8, 3) if size <= len(properties))
    stages = run_funnel(properties, stage_sizes=stage_sizes)

    for size, stage in zip(stage_sizes, stages):
        print(f"\n=== Top {size} ===")
        for prop in stage:
            analysis = analyze_property(prop)
            print(f"{prop.get('address', '(unknown)')}")
            print(f"  Asking: ${analysis['asking_price']:,.0f}")
            print(f"  Estimated stabilized value: ${analysis['stabilized_value']:,.0f}")
            print(f"  Estimated rehab: ${analysis['rehab_cost']:,.0f}")
            print(f"  Acquisition + rehab + carrying: ${analysis['total_cost']:,.0f}")
            print(f"  Potential gross spread: ${analysis['spread']:,.0f}")
            print(f"  Confidence: {analysis['confidence']}")
            if analysis["reasons"]:
                print(f"  Why it surfaced: {', '.join(analysis['reasons'])}")


if __name__ == "__main__":
    main()
