"""Test the matching algorithm locally without Supabase."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.config import CSV_FILES
from pipeline.ingest.metropolis_loader import MetropolisLoader
from pipeline.ingest.agilus_loader import AgilusLoader
from pipeline.ingest.apollo_loader import ApolloLoader
from pipeline.ingest.neuberg_loader import NeubergLoader
from pipeline.ingest.trustlab_loader import TRUSTlabLoader
from pipeline.matching.matcher import TestMatcher


def main():
    print("=== Loading CSVs ===")

    loaders = {
        "metropolis": MetropolisLoader(),
        "agilus": AgilusLoader(),
        "apollo": ApolloLoader(),
        "neuberg": NeubergLoader(),
        "trustlab": TRUSTlabLoader(),
    }

    all_tests = {}
    for slug, loader in loaders.items():
        csv_path = CSV_FILES.get(slug)
        if not csv_path or not os.path.exists(csv_path):
            print(f"  WARNING: CSV not found for {slug}: {csv_path}")
            continue
        tests = loader.load(csv_path)
        all_tests[slug] = tests

    # Get unique tests for matching
    print("\n=== Deduplicating ===")
    unique_tests = []

    for slug, tests in all_tests.items():
        loader = loaders[slug]
        if hasattr(loader, "get_unique_tests"):
            unique = loader.get_unique_tests(tests)
        else:
            seen = {}
            for t in tests:
                key = t.source_test_code or t.source_test_name
                if key not in seen:
                    seen[key] = t
            unique = list(seen.values())
            print(f"  {slug}: {len(unique)} unique from {len(tests)} total")

        unique_tests.extend(unique)

    print(f"\n  Total unique tests for matching: {len(unique_tests)}")

    # Run matching
    matcher = TestMatcher()
    assignments = matcher.run(unique_tests)
    canonicals = matcher.get_canonical_tests()

    # Summary
    print(f"\n=== Matching Summary ===")
    print(f"  Total canonical tests: {len(canonicals)}")

    cross_lab = sum(1 for c in canonicals if c["lab_count"] >= 2)
    print(f"  Cross-lab matches (2+ labs): {cross_lab}")

    three_plus = sum(1 for c in canonicals if c["lab_count"] >= 3)
    print(f"  Available at 3+ labs: {three_plus}")

    four_plus = sum(1 for c in canonicals if c["lab_count"] >= 4)
    print(f"  Available at 4+ labs: {four_plus}")

    all_five = sum(1 for c in canonicals if c["lab_count"] >= 5)
    print(f"  Available at all 5 labs: {all_five}")

    # Show some cross-lab examples
    print(f"\n=== Sample Cross-Lab Matches (3+ labs) ===")
    cross_lab_tests = sorted(
        [c for c in canonicals if c["lab_count"] >= 3],
        key=lambda x: x["lab_count"],
        reverse=True
    )

    for ct in cross_lab_tests[:20]:
        labs = set(m["lab_slug"] for m in ct["members"])
        names = [f'{m["lab_slug"]}:"{m["source_test_name"][:50]}"' for m in ct["members"]]
        print(f"\n  [{ct['lab_count']} labs] {ct['name']}")
        for n in names:
            print(f"    {n}")

    # Show lab distribution
    print(f"\n=== Lab Distribution ===")
    for lab_count in [5, 4, 3, 2, 1]:
        count = sum(1 for c in canonicals if c["lab_count"] == lab_count)
        print(f"  {lab_count} labs: {count} tests")


if __name__ == "__main__":
    main()
