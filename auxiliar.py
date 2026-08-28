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
# Number validation v2
# =========================

def validate_number_v2(message, current=None):
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
            result = int(value)

            if 16>=result>=0:
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
# transport
# =========================

def validate_transport(question, current=None):

    options = [
        "ssh",
        "telnet",
        "rlogin",
        "lat",
        "mop",
        "nasi",
        "pad",
        "udptn",
        "v120",
        "acercon",
        "all",
        "none"
    ]
    method = ""

    while True:

        if current is None:
            prompt = question
        else:
            prompt = f"{question} [{current}]"

        print()
        print(prompt)

        for i, option in enumerate(options, start=1):
            print(f"{i}. {option}")

        skip_option = len(options) + 1
        cancel_option = len(options) + 2
        finish_option = len(options) + 3

        print(f"{skip_option}. skip")
        print(f"{cancel_option}. cancel")
        if method != "":
            print(f"{finish_option}. finish")


        try:
            result = int(input("Choose an option: "))

            if 1 <= result <= len(options):
                method += options[result - 1] + " "
                options.pop(result - 1)
                continue

            if result == skip_option:
                return SKIP

            if result == cancel_option:
                return CANCEL

            if result == finish_option:
                if not method:
                    return SKIP
                return method.strip()

            print("Invalid option.")

        except ValueError:
            print("Please enter a number.")

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

def validate_no_spaces(question, current):

    while True:

        if current is None:
            prompt = (
                f"{question} "
                "(skip = keep current, cancel = abort): "
            )
        else:
            prompt = (
                f"{question} [{current}] "
                "(skip = keep current, cancel = abort): "
            )

        value = input(prompt).strip()

        if value.lower() == "cancel":
            return CANCEL

        if value.lower() == "skip":
            return SKIP

        if " " in value:
            print("Value cannot contain spaces.")
            continue

        if value == "":
            print("Value cannot be empty.")
            continue

        return value

# =========================
# USERNAME-SECRET
# =========================

def validate_username(question, current):

    if current is None:
        current_user = None
        current_secret = None
    else:
        current_user = current["user"]
        current_secret = current["secret"]

    # --------------------------------------------------------
    # USERNAME
    # --------------------------------------------------------

    user = validate_no_spaces(
        "Write the username",
        current_user
    )

    if user is CANCEL:
        return CANCEL

    if user is SKIP:
        return SKIP

    # --------------------------------------------------------
    # SECRET
    # --------------------------------------------------------

    secret = validate_no_spaces(
        "Write the secret",
        current_secret
    )

    if secret is CANCEL:
        return CANCEL

    if secret is SKIP:
        return SKIP

    return {
        "user": user,
        "secret": secret
    }


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
