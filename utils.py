import datetime
import json
import pytz
import requests_cache


BASE_URL = "https://pypi.org/pypi"
HISTORY_FILE = "history.json"
HISTORY_PACKAGE_TOTAL = 1000
DEPLOYED_RESULTS_URL = (
    "https://github.com/tonybaloney/windows-arm64-wheels/raw/refs/heads/gh-pages/"
    "results.json"
)

DEPRECATED_PACKAGES = {
    "BeautifulSoup",
    "bs4",
    "distribute",
    "django-social-auth",
    "nose",
    "pep8",
    "pycrypto",
    "pypular",
    "sklearn",
}

# Keep responses for one hour
SESSION = requests_cache.CachedSession("requests-cache", expire_after=60 * 60)


def get_json_url(package_name):
    return BASE_URL + "/" + package_name + "/json"


def fetch_deployed_result():
    response = SESSION.get(DEPLOYED_RESULTS_URL)
    if response.status_code != 200:
        print(" ! Skipping " + DEPLOYED_RESULTS_URL)
        return None
    return response.json()


def get_package_wheel_status(result):
    if result is None:
        return {}
    return {d["name"]: int(d.get("wheel_enabled", 0)) for d in result["data"]}


def fetch_old_result():
    result = fetch_deployed_result()
    if result is None:
        return None
    return get_package_wheel_status(result)


def validate_history(history):
    if not isinstance(history, list):
        raise ValueError("Wheel history must be a list")

    validated = []
    for point in history:
        if not isinstance(point, dict):
            raise ValueError("Each wheel history point must be an object")

        date = point.get("date")
        unsupported = point.get("unsupported")
        total = point.get("total")
        try:
            datetime.date.fromisoformat(date)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid wheel history date: {date!r}") from error

        if (
            not isinstance(unsupported, int)
            or isinstance(unsupported, bool)
            or not isinstance(total, int)
            or isinstance(total, bool)
            or unsupported < 0
            or total < 0
            or unsupported > total
        ):
            raise ValueError(f"Invalid wheel history counts for {date}")

        validated.append({"date": date, "unsupported": unsupported, "total": total})

    return validated


def load_history(deployed_result, file_name=HISTORY_FILE):
    if deployed_result is not None and "history" in deployed_result:
        history = deployed_result["history"]
    else:
        with open(file_name) as history_file:
            history = json.load(history_file)

    return [
        point
        for point in validate_history(history)
        if point["total"] == HISTORY_PACKAGE_TOTAL
    ]


def update_history(history, packages, now):
    point = {
        "date": now.date().isoformat(),
        "unsupported": sum(package["css_class"] == "warning" for package in packages),
        "total": len(packages),
    }
    by_date = {item["date"]: item for item in validate_history(history)}
    by_date[point["date"]] = point
    return [by_date[date] for date in sorted(by_date)]


def annotate_wheels(packages, old_packages):
    print("Getting wheel data...")
    num_packages = len(packages)
    for index, package in enumerate(packages):
        print(index + 1, num_packages, package["name"])
        has_abi_none_wheel = False
        has_win_arm64_wheel = False
        url = get_json_url(package["name"])
        response = SESSION.get(url)
        if response.status_code != 200:
            print(" ! Skipping " + package["name"])
            continue
        data = response.json()

        for download in data["urls"]:
            if download["packagetype"] == "bdist_wheel":
                # The wheel filename is:
                # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                whl_spec = download["filename"].removesuffix(".whl").split("-")
                abi_tag = whl_spec[-2]
                platform_tag = whl_spec[-1]

                if abi_tag == "none":
                    has_abi_none_wheel = True

                if "win_arm64" in platform_tag:
                    has_win_arm64_wheel = True

        package["wheel"] = has_win_arm64_wheel or has_abi_none_wheel

        # Display logic. I know, I'm sorry.
        package["value"] = 1
        if has_win_arm64_wheel:
            package["css_class"] = "success"
            package["icon"] = "💪"
            package["title"] = "This package provides a free-threaded wheel."
        elif has_abi_none_wheel:
            package["css_class"] = "default"
            package["icon"] = "🐍"
            package["title"] = "This package provides pure Python wheels."
        else:
            package["css_class"] = "warning"
            package["icon"] = "\u2717"  # Ballot X
            package["title"] = "This package has no wheel archives uploaded (yet!)."

        package["wheel_enabled"] = 0
        if package["name"] in old_packages:
            if old_packages[package["name"]] == 0 and has_win_arm64_wheel:
                package["wheel_enabled"] = datetime.datetime.now().timestamp()
        else:
            if has_win_arm64_wheel:
                package["wheel_enabled"] = datetime.datetime.now().timestamp()


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def not_deprecated(package):
    return package["name"] not in DEPRECATED_PACKAGES


def remove_irrelevant_packages(packages, limit):
    print("Removing cruft...")
    active_packages = list(filter(not_deprecated, packages))
    return active_packages[:limit]


def save_to_file(packages, file_name, history=None):
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    result = {
        "data": packages,
        "last_update": now.strftime("%A, %d %B %Y, %X %Z"),
    }
    if history is not None:
        result["history"] = update_history(history, packages, now)

    with open(file_name, "w") as f:
        f.write(json.dumps(result, indent=1))
