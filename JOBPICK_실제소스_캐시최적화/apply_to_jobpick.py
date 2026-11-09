"""Apply source changes to a JOBPICK checkout without requiring any third-party libs.

The two actual matching helper sources are in ./matching/. The existing large
main/main_matching.py remains in the user's repository; this tool edits it in
place only after validating all expected anchors, with a .bak backup.
"""
from __future__ import annotations
import argparse
import ast
from difflib import unified_diff
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace_one(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, got {count}; no files changed")
    return s.replace(old, new, 1)


def patch_main(s: str) -> str:
    s = replace_one(
        s,
        "from database.firebase_init import init_firebase\n",
        "from database.firebase_init import init_firebase\n"
        "from matching.job_cache import get_cached_flattened_job, get_cached_job_embedding_text\n"
        "from matching.optimized_preload import preload_prepared_score_embeddings as optimized_preload\n",
        "imports",
    )
    s = replace_one(
        s,
        '''    flattened_jobs = [
        flatten_job(
            job_raw
        )
        for _, job_raw
        in candidate_jobs
    ]''',
        '''    flattened_job_cache_results = [
        get_cached_flattened_job(job_raw)
        for _, job_raw in candidate_jobs
    ]
    flattened_jobs = [result for result, _ in flattened_job_cache_results]
    print(
        f"[job-cache] flatten: {sum(hit for _, hit in flattened_job_cache_results)}/"
        f"{len(flattened_job_cache_results)} RAM hits", flush=True,
    )''',
        "flatten stage",
    )
    s = replace_one(
        s,
        '''    job_embedding_texts = [
        get_job_embedding_text(job_raw)
        for _, job_raw in candidate_jobs
    ]''',
        '''    embedding_text_cache_results = [
        get_cached_job_embedding_text(job_raw)
        for _, job_raw in candidate_jobs
    ]
    job_embedding_texts = [result for result, _ in embedding_text_cache_results]
    print(
        f"[job-cache] embedding text: {sum(hit for _, hit in embedding_text_cache_results)}/"
        f"{len(embedding_text_cache_results)} RAM hits", flush=True,
    )''',
        "job embedding stage",
    )
    s = replace_one(
        s,
        '''    preload_stats = preload_prepared_score_embeddings(
        prepared_score_contexts,
        extra_similarity_texts=[
            resume_embedding_text,
            *job_embedding_texts,
        ],
    )''',
        '''    preload_stats = optimized_preload(
        prepared_score_contexts,
        extra_similarity_texts=[
            resume_embedding_text,
            *job_embedding_texts,
        ],
    )''',
        "preload function",
    )
    old = '''    print(
        f"[matching-perf] 6. 임베딩 preload: "
        f"{preload_elapsed:.2f}초 "
        f"(live encode {int((preload_stats or {}).get('encodedCount', 0))}개)"
    )'''
    s = replace_one(
        s, old, old + '''
    print(
        f"[embedding-cache] unique={preload_stats['uniqueCount']} "
        f"RAM={preload_stats['memoryHitCount']} "
        f"precomputed={preload_stats['vectorHitCount']} "
        f"live={preload_stats['encodedCount']} "
        f"duplicates={preload_stats['duplicateCount']}",
        flush=True,
    )
    for field, counts in preload_stats["fieldStats"].items():
        print(
            f"[embedding-cache] {field}: "
            f"RAM={counts['memory']} "
            f"precomputed={counts['precomputed']} "
            f"live={counts['live']} "
            f"duplicates={counts['duplicate']}",
            flush=True,
        )''',
        "performance logging",
    )
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    root = args.project.resolve()
    target = root / "main" / "main_matching.py"
    if not (root / "server.py").exists() or not target.exists():
        raise SystemExit("--project must point to the JOBPICK repository root")
    original = target.read_text(encoding="utf-8-sig")
    updated = patch_main(original)
    ast.parse(updated, filename="main/main_matching.py")
    for name in ["job_cache.py", "optimized_preload.py"]:
        ast.parse((HERE / "matching" / name).read_text(encoding="utf-8"))
    print("VALID: 2 Python helper files + complete main_matching.py patch")
    if args.preview:
        print("".join(unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile="a/main/main_matching.py", tofile="b/main/main_matching.py")))
    if args.check or args.preview:
        return
    for name in ["job_cache.py", "optimized_preload.py"]:
        destination = root / "matching" / name
        if destination.exists():
            raise SystemExit(f"Already exists, stopping safely: {destination}")
    backup = target.with_suffix(".py.before_cache_fix.bak")
    if backup.exists():
        raise SystemExit(f"Backup already exists, stopping safely: {backup}")
    shutil.copy2(target, backup)
    for name in ["job_cache.py", "optimized_preload.py"]:
        shutil.copy2(HERE / "matching" / name, root / "matching" / name)
    target.write_text(updated, encoding="utf-8")
    print("APPLIED:", target)
    print("Backup:", backup)
    print("New files: matching/job_cache.py matching/optimized_preload.py")


if __name__ == "__main__":
    main()
