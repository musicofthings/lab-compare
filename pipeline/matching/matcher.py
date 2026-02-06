"""Multi-pass test matching algorithm.

Matches tests across labs to canonical test groups using:
1. Exact code matching
2. Neuberg alias matching
3. Normalized name exact matching
4. Fuzzy scoring (trigram + token overlap)
"""
from collections import defaultdict
from rapidfuzz import fuzz
from pipeline.models import NormalizedLabTest
from pipeline.matching.preprocessor import (
    normalize_test_name,
    tokenize,
    tokenize_expanded,
    expand_abbreviations,
)


class TestMatcher:
    def __init__(self):
        # cluster_id -> list of (lab_slug, source_test_code, source_test_name)
        self.clusters: dict[int, list[dict]] = {}
        self.next_cluster_id = 1

        # Lookup: normalized_name -> cluster_id
        self.name_to_cluster: dict[str, int] = {}
        # Lookup: alias_lower -> cluster_id
        self.alias_to_cluster: dict[str, int] = {}
        # Lookup: test key -> cluster_id (for results)
        self.assignment: dict[str, int] = {}  # "lab_slug:source_test_code" -> cluster_id

    def _make_key(self, t: dict | NormalizedLabTest) -> str:
        if isinstance(t, NormalizedLabTest):
            return f"{t.lab_slug}:{t.source_test_code}"
        return f"{t['lab_slug']}:{t['source_test_code']}"

    def _new_cluster(self, members: list[dict]) -> int:
        cid = self.next_cluster_id
        self.next_cluster_id += 1
        self.clusters[cid] = members
        return cid

    def _add_to_cluster(self, cid: int, member: dict):
        self.clusters[cid].append(member)

    def run(
        self,
        all_unique_tests: list[NormalizedLabTest],
    ) -> dict[str, int]:
        """Run all matching passes. Returns {test_key: cluster_id}."""
        print("\n=== Starting Test Matching ===")
        print(f"  Total unique tests to match: {len(all_unique_tests)}")

        unmatched = list(all_unique_tests)

        # Pass 1: Exact normalized name match (group by normalized name)
        unmatched = self._pass_exact_name(unmatched)
        print(f"  After Pass 1 (exact name): {len(self.clusters)} clusters, {len(unmatched)} unmatched")

        # Pass 2: Neuberg alias matching
        unmatched = self._pass_alias_match(unmatched)
        print(f"  After Pass 2 (alias): {len(self.clusters)} clusters, {len(unmatched)} unmatched")

        # Pass 3: Fuzzy matching
        unmatched = self._pass_fuzzy_match(unmatched)
        print(f"  After Pass 3 (fuzzy): {len(self.clusters)} clusters, {len(unmatched)} unmatched")

        # Pass 4: Create singleton clusters for remaining unmatched
        for t in unmatched:
            key = self._make_key(t)
            member = {
                "lab_slug": t.lab_slug,
                "source_test_code": t.source_test_code,
                "source_test_name": t.source_test_name,
                "confidence": 1.0,
                "method": "singleton",
            }
            cid = self._new_cluster([member])
            self.assignment[key] = cid
            norm = normalize_test_name(t.source_test_name)
            self.name_to_cluster[norm] = cid

        print(f"  Final: {len(self.clusters)} total clusters")

        # Stats
        multi = sum(1 for c in self.clusters.values() if len(c) > 1)
        labs_per_cluster = []
        for c in self.clusters.values():
            labs = set(m["lab_slug"] for m in c)
            labs_per_cluster.append(len(labs))
        cross_lab = sum(1 for n in labs_per_cluster if n >= 2)
        print(f"  Multi-member clusters: {multi}")
        print(f"  Cross-lab clusters (2+ labs): {cross_lab}")

        return self.assignment

    def _pass_exact_name(self, tests: list[NormalizedLabTest]) -> list[NormalizedLabTest]:
        """Group tests by exact normalized name."""
        name_groups: dict[str, list[NormalizedLabTest]] = defaultdict(list)
        for t in tests:
            norm = normalize_test_name(t.source_test_name)
            name_groups[norm].append(t)

        unmatched = []
        for norm_name, group in name_groups.items():
            if len(group) == 1:
                # Single test - still create a cluster
                t = group[0]
                key = self._make_key(t)
                member = {
                    "lab_slug": t.lab_slug,
                    "source_test_code": t.source_test_code,
                    "source_test_name": t.source_test_name,
                    "confidence": 1.0,
                    "method": "exact_name",
                }
                cid = self._new_cluster([member])
                self.assignment[key] = cid
                self.name_to_cluster[norm_name] = cid
                # These are "matched" to themselves; we'll try alias/fuzzy later
                # Actually, mark them as unmatched so they can join other clusters
                unmatched.append(t)
            else:
                # Multiple tests with same normalized name -> definite cluster
                members = []
                for t in group:
                    key = self._make_key(t)
                    members.append({
                        "lab_slug": t.lab_slug,
                        "source_test_code": t.source_test_code,
                        "source_test_name": t.source_test_name,
                        "confidence": 0.95,
                        "method": "exact_name",
                    })
                cid = self._new_cluster(members)
                self.name_to_cluster[norm_name] = cid
                for t in group:
                    self.assignment[self._make_key(t)] = cid

        # Only truly unmatched are singletons that might join other clusters
        return unmatched

    def _pass_alias_match(self, tests: list[NormalizedLabTest]) -> list[NormalizedLabTest]:
        """Match using Neuberg aliases and cross-lab name containment."""
        # Build alias index from all tests that have aliases
        for t in tests:
            if t.aliases:
                key = self._make_key(t)
                cid = self.assignment.get(key)
                if cid:
                    for alias in t.aliases:
                        clean = alias.strip().lower()
                        if clean and len(clean) > 2:
                            self.alias_to_cluster[clean] = cid
                    # Also add the main name
                    norm = normalize_test_name(t.source_test_name)
                    self.alias_to_cluster[norm] = cid

        unmatched = []
        for t in tests:
            key = self._make_key(t)
            if key in self.assignment:
                # Already in a multi-member cluster
                if len(self.clusters.get(self.assignment[key], [])) > 1:
                    continue

            # Try matching against aliases
            norm = normalize_test_name(t.source_test_name)
            matched_cid = self.alias_to_cluster.get(norm)

            if not matched_cid:
                # Try each word/phrase in the test name
                words = norm.split()
                for alias, cid in self.alias_to_cluster.items():
                    if alias == norm:
                        matched_cid = cid
                        break
                    # Check if the alias is a close match
                    if len(alias) > 3 and len(norm) > 3:
                        if alias in norm or norm in alias:
                            # Containment match - but be careful with short names
                            if min(len(alias), len(norm)) / max(len(alias), len(norm)) > 0.5:
                                matched_cid = cid
                                break

            if matched_cid and matched_cid != self.assignment.get(key):
                # Merge into the alias cluster
                member = {
                    "lab_slug": t.lab_slug,
                    "source_test_code": t.source_test_code,
                    "source_test_name": t.source_test_name,
                    "confidence": 0.90,
                    "method": "alias_match",
                }
                self._add_to_cluster(matched_cid, member)
                old_cid = self.assignment.get(key)
                self.assignment[key] = matched_cid
                # Remove old singleton cluster if it existed
                if old_cid and old_cid in self.clusters and len(self.clusters[old_cid]) <= 1:
                    del self.clusters[old_cid]
            else:
                unmatched.append(t)

        return unmatched

    def _pass_fuzzy_match(self, tests: list[NormalizedLabTest]) -> list[NormalizedLabTest]:
        """Fuzzy matching using combined scoring."""
        # Build list of cluster representatives for comparison
        cluster_reps: list[tuple[int, str, set[str]]] = []
        for cid, members in self.clusters.items():
            if len(members) > 1:  # Only try to join multi-member clusters
                # Use first member's name as representative
                rep_name = members[0]["source_test_name"]
                rep_norm = normalize_test_name(rep_name)
                rep_tokens = tokenize_expanded(rep_name)
                cluster_reps.append((cid, rep_norm, rep_tokens))

        unmatched = []
        for t in tests:
            key = self._make_key(t)
            if key in self.assignment and len(self.clusters.get(self.assignment[key], [])) > 1:
                continue

            norm = normalize_test_name(t.source_test_name)
            tokens = tokenize_expanded(t.source_test_name)

            best_score = 0.0
            best_cid = None

            for cid, rep_norm, rep_tokens in cluster_reps:
                # Trigram-like similarity via rapidfuzz
                trgm = fuzz.ratio(norm, rep_norm) / 100.0

                # Token Jaccard
                if tokens and rep_tokens:
                    jaccard = len(tokens & rep_tokens) / len(tokens | rep_tokens)
                else:
                    jaccard = 0.0

                # Partial ratio (handles substring matches)
                partial = fuzz.partial_ratio(norm, rep_norm) / 100.0

                # Combined score
                score = (0.35 * trgm) + (0.35 * jaccard) + (0.30 * partial)

                if score > best_score:
                    best_score = score
                    best_cid = cid

            if best_cid and best_score >= 0.65:
                member = {
                    "lab_slug": t.lab_slug,
                    "source_test_code": t.source_test_code,
                    "source_test_name": t.source_test_name,
                    "confidence": round(best_score, 4),
                    "method": "fuzzy_match",
                }
                self._add_to_cluster(best_cid, member)
                old_cid = self.assignment.get(key)
                self.assignment[key] = best_cid
                if old_cid and old_cid in self.clusters and len(self.clusters[old_cid]) <= 1:
                    del self.clusters[old_cid]
            else:
                unmatched.append(t)

        return unmatched

    def get_canonical_tests(self) -> list[dict]:
        """Generate canonical test records from clusters."""
        canonicals = []
        for cid, members in self.clusters.items():
            # Pick best name: prefer longest descriptive name, or Neuberg name
            best_name = members[0]["source_test_name"]
            for m in members:
                if m["lab_slug"] == "neuberg" and len(m["source_test_name"]) > 3:
                    best_name = m["source_test_name"]
                    break
                if len(m["source_test_name"]) > len(best_name):
                    best_name = m["source_test_name"]

            # Collect all name variants as keywords
            keywords = list(set(
                m["source_test_name"] for m in members
            ))

            lab_count = len(set(m["lab_slug"] for m in members))

            canonicals.append({
                "cluster_id": cid,
                "name": best_name,
                "keywords": keywords,
                "member_count": len(members),
                "lab_count": lab_count,
                "members": members,
            })

        return canonicals
