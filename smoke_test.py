"""Verify the running API serves the model for the checked-out commit."""
import json
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"
RECORD = dict(basket_volatility=0.5, stock_gap=0.2, promotion_load=-0.3, delivery_delay=0.1)


def fetch(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(BASE_URL + path, data=body, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=3) as response:
        return json.load(response)


def main(git_sha, expected_rows):
    for attempt in range(20):
        try:
            metrics = fetch("/metrics")
            break
        except URLError:
            if attempt == 19:
                raise
            time.sleep(1)

    assert metrics["student_id"] == "SP23-BAI-043", metrics
    assert metrics["git_sha"] == git_sha, metrics
    assert metrics["training_rows"] == expected_rows, metrics
    assert 0 <= metrics["accuracy"] <= 1, metrics
    assert len(metrics["model_version"]) == 12, metrics

    result = fetch("/predict", {"records": [RECORD]})
    assert len(result["predictions"]) == len(result["probabilities"]) == 1, result
    assert result["predictions"][0] in (0, 1), result
    assert 0 <= result["probabilities"][0] <= 1, result
    print(json.dumps(metrics))
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
