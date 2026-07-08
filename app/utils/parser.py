import re


def extract_phone(text: str):

    numbers = re.findall(r"\d+", text)

    if not numbers:
        return None

    phone = "".join(numbers)

    if len(phone) >= 10:
        return phone[-10:]

    return None



def extract_name(text: str):

    text = text.lower().strip()

    remove_words = [
        "my name is",
        "i am",
        "this is",
        "it's",
        "its",
        "hello",
        "hi",
        "hey"
    ]

    for word in remove_words:
        text = text.replace(word, "")

    text = text.strip()

    if not text:
        return None

    return " ".join(
        word.capitalize()
        for word in text.split()
    )



def extract_time(text: str):

    text = text.lower().strip()

    patterns = [

        # 6:30 pm
        r"\d{1,2}:\d{2}\s*(am|pm)",

        # 6 pm
        r"\d{1,2}\s*(am|pm)",

        # 6.30 pm
        r"\d{1,2}\.\d{2}\s*(am|pm)",

        # 6 o'clock
        r"\d{1,2}\s*o'?clock",
        
        # 6 o clock
        r"\d{1,2}\s*o\s*clock",

        # 18:30
        r"\d{1,2}:\d{2}"

    ]


    for pattern in patterns:

        match = re.search(pattern, text)

        if match:
            return match.group(0).upper()


    return None
