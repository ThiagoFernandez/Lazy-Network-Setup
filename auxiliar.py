import ipaddress
import re


# =========================
# Sentinels
# =========================

CANCEL = object()
SKIP = object()


# =========================
# General
# =========================

def greeting_text(text):
    print()
    print(f"{text:^60}")
    print()


def show_options(options):
    print()

    for i, option in enumerate(options, start=1):
        print(f"{i}. {option}")

    print("0. Cancel")


# =========================
# Number validation
# =========================

def validate_number(options):
    while True:
        try:
            result = int(input("Choose an option: "))

            if result == 0:
                return -1

            if 1 <= result <= len(options):
                return result

            print("Invalid option.")

        except ValueError:
            print("Please enter a number.")


# =========================
# Optional string
# =========================

def validate_optional_string(message, current=None):

    while True:

        if current is None:
            prompt = message
        else:
            prompt = f"{message} [{current}]"

        value = input(
            f"{prompt} "
            "(skip = keep current, cancel = abort): "
        ).strip()

        if value.lower() == "cancel":
            return CANCEL

        if value.lower() == "skip":
            return SKIP

        if value:
            return value

        print("The value cannot be empty.")


# =========================
# Hostname
# =========================

def validate_hostname(message, current=None):

    while True:

        if current is None:
            prompt = message
        else:
            prompt = f"{message} [{current}]"

        value = input(
            f"{prompt} "
            "(skip = keep current, cancel = abort): "
        ).strip()

        if value.lower() == "cancel":
            return CANCEL

        if value.lower() == "skip":
            return SKIP

        if not value:
            print("The hostname cannot be empty.")
            continue

        if len(value) > 63:
            print("Hostname cannot be longer than 63 characters.")
            continue

        if value[0].isdigit():
            print("Hostname cannot start with a digit.")
            continue

        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            print(
                "Hostname can only contain letters, "
                "numbers, '_' and '-'."
            )
            continue

        return value


# =========================
# IP validation
# =========================

def validate_ip(message, current=None):

    while True:

        if current is None:
            prompt = message
        else:
            prompt = f"{message} [{current}]"

        value = input(
            f"{prompt} "
            "(skip = keep current, cancel = abort): "
        ).strip()

        if value.lower() == "cancel":
            return CANCEL

        if value.lower() == "skip":
            return SKIP

        try:
            ipaddress.ip_address(value)
            return value

        except ValueError:
            print("Invalid IP address.")


# =========================
# Yes / No
# =========================

def validate_yes_no(message, current=None):

    print()

    if current is True:
        print(f"{message} [yes]")

    elif current is False:
        print(f"{message} [no]")

    else:
        print(message)

    print("1. yes")
    print("2. no")
    print("0. cancel")

    while True:

        try:
            result = int(input("Choose an option: "))

            if result == 0:
                return CANCEL

            if result == 1:
                return True

            if result == 2:
                return False

            print("Invalid option.")

        except ValueError:
            print("Please enter a number.")
