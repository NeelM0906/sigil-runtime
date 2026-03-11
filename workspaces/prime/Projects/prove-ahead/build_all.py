from __future__ import annotations

from pathlib import Path

from benchmark import run_benchmark
from competitors import DB_PATH, init_and_seed
from matrix import OUTPUT_PATH as MATRIX_PATH, build_matrix
from report import BENCHMARK_PATH, REPORT_PATH, generate_report


def main() -> None:
    init_and_seed(DB_PATH)
    build_matrix(DB_PATH, MATRIX_PATH)
    run_benchmark(Path(BENCHMARK_PATH))
    generate_report(Path(REPORT_PATH), Path(DB_PATH), Path(MATRIX_PATH), Path(BENCHMARK_PATH))


if __name__ == "__main__":
    main()
