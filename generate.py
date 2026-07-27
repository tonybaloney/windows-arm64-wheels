from svg_wheel import generate_svg_wheel
from utils import (
    annotate_wheels,
    fetch_deployed_result,
    get_top_packages,
    get_package_wheel_status,
    load_history,
    remove_irrelevant_packages,
    save_to_file,
)

TO_CHART = 1000


def main(to_chart: int = TO_CHART) -> None:
    # Fetch current status
    deployed_result = fetch_deployed_result()
    if deployed_result is None:
        raise RuntimeError(
            "Could not fetch the deployed results; refusing to discard wheel history"
        )
    old_packages = get_package_wheel_status(deployed_result)
    history = load_history(deployed_result)
    packages = remove_irrelevant_packages(get_top_packages(), to_chart)
    annotate_wheels(packages, old_packages)
    save_to_file(packages, "results.json", history)
    generate_svg_wheel(packages, to_chart)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-n", "--number", type=int, default=TO_CHART, help="number of packages to chart"
    )
    args = parser.parse_args()

    main(args.number)
