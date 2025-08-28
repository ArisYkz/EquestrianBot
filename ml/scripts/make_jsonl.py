import csv, json, random, pathlib, sys

repo = pathlib.Path(__file__).resolve().parents[1]
src = repo / "data" / "faq_knowledgebase.csv"
out_all = repo / "data" / "training_data.jsonl"
out_train = repo / "data" / "train.jsonl"
out_val   = repo / "data" / "val.jsonl"
out_test  = repo / "data" / "test.jsonl"

RANDOM_SEED = 42
VAL_FRACTION = 0.10
TEST_FRACTION = 0.10

def row_to_example(row):
    q = (row.get("question") or "").strip()
    a = (row.get("answer") or "").strip()
    if not q or not a:
        return None
    return {"instruction": q, "input": "", "output": a}

def write_jsonl(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as w:
        for it in items:
            w.write(json.dumps(it, ensure_ascii=False) + "\n")

def main():
    if not src.exists():
        print(f"ERROR: CSV not found at {src}")
        sys.exit(1)

    rows = []
    with open(src, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ex = row_to_example(row)
            if ex: rows.append(ex)

    if not rows:
        print("ERROR: No valid rows found (check headers & content).")
        sys.exit(1)

    random.seed(RANDOM_SEED)
    random.shuffle(rows)

    n = len(rows)
    n_val = max(1, int(n * VAL_FRACTION))
    n_test = max(1, int(n * TEST_FRACTION))
    n_train = max(1, n - n_val - n_test)

    train = rows[:n_train]
    val   = rows[n_train:n_train+n_val]
    test  = rows[n_train+n_val:]

    write_jsonl(out_all, rows)
    write_jsonl(out_train, train)
    write_jsonl(out_val, val)
    write_jsonl(out_test, test)

    print(f"Total: {n} | train: {len(train)} | val: {len(val)} | test: {len(test)}")
    print(f"Wrote:\n - {out_all}\n - {out_train}\n - {out_val}\n - {out_test}")

if __name__ == "__main__":
    main()
