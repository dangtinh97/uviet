"""Composition state for a single Telex word."""

import unicodedata

TONES = dict(zip("sfrxj", "\u0301\u0300\u0309\u0303\u0323"))
VOWELS = "aeiouyăâêôơư"
CODAS = {"", "c", "ch", "m", "n", "ng", "nh", "p", "t"}
ONSETS = set("b c ch d đ g gh h k kh l m n ng ngh nh p ph q r s t th tr v x".split())
ONSETS.add("")
SHAPES = {
    "a": {"a": "â"},
    "e": {"e": "ê"},
    "o": {"o": "ô"},
    "d": {"d": "đ"},
    "w": {"a": "ă", "o": "ơ", "u": "ư"},
}
PLAIN = {changed: plain for mapping in SHAPES.values() for plain, changed in mapping.items()}


def match_case(letter, original):
    return letter.upper() if original.isupper() else letter


class Telex:
    def __init__(self):
        self.letters = []
        self.tone = ""

    def clear(self):
        self.letters.clear()
        self.tone = ""

    def spelling(self):
        letters = self.letters.copy()
        for index in range(1, len(letters)):
            if letters[index - 1].lower() == "ư" and letters[index].lower() == "o":
                letters[index] = match_case("ơ", letters[index])
        return letters

    @staticmethod
    def tone_position(letters):
        vowel_positions = [
            index for index, letter in enumerate(letters) if letter.lower() in VOWELS
        ]
        if len(vowel_positions) > 1 and "".join(letters[:2]).lower() in ("qu", "gi"):
            vowel_positions = [index for index in vowel_positions if index != 1]
        if not vowel_positions:
            return None

        for index in reversed(vowel_positions):
            if letters[index].lower() in "ăâêôơư":
                return index

        if len(vowel_positions) == 3:
            return vowel_positions[1]
        if len(vowel_positions) == 2 and vowel_positions[-1] < len(letters) - 1:
            return vowel_positions[-1]
        return vowel_positions[0]

    @property
    def text(self):
        letters = self.spelling()
        position = self.tone_position(letters) if self.tone else None
        if position is not None:
            letters[position] = unicodedata.normalize("NFC", letters[position] + self.tone)
        return "".join(letters)

    def backspace(self):
        position = self.tone_position(self.spelling()) if self.tone else None
        self.letters.pop()
        if position == len(self.letters):
            self.tone = ""

    def can_modify_vowels(self):
        word = "".join(self.letters).lower()
        start = next((index for index, letter in enumerate(word) if letter in VOWELS), None)
        if start is None or word[:start] not in ONSETS:
            return False
        coda = word[start:].lstrip(VOWELS)
        return coda in CODAS

    def push(self, letter):
        key = letter.lower()
        if key in TONES and self.can_modify_vowels():
            tone = TONES[key]
            if self.tone != tone:
                self.tone = tone
                return
            self.tone = ""
        elif key == "z" and (self.tone or any(c.lower() in PLAIN for c in self.letters)):
            self.tone = ""
            self.letters = [match_case(PLAIN.get(c.lower(), c.lower()), c) for c in self.letters]
            return
        elif key in SHAPES and (key == "d" or self.can_modify_vowels()) and self.apply_shape(key):
            return
        self.letters.append(letter)

    def apply_shape(self, key):
        mapping = SHAPES[key]
        if key == "w":
            double_horn = self.apply_double_horn()
            if double_horn is not None:
                return double_horn

        for index in range(len(self.letters) - 1, -1, -1):
            original = self.letters[index]
            plain = original.lower()
            if key == "w" and plain == "a" and index > 0:
                previous = self.letters[index - 1]
                follows_qu = index == 2 and self.letters[0].lower() == "q"
                if not follows_qu and previous.lower() == "u":
                    self.letters[index - 1] = match_case("ư", previous)
                    return True
                if not follows_qu and previous.lower() == "ư":
                    self.letters[index - 1] = match_case("u", previous)
                    return False
            if plain in mapping:
                self.letters[index] = match_case(mapping[plain], original)
                return True
            if plain in mapping.values():
                self.letters[index] = match_case(PLAIN[plain], original)
                return False
        return False

    def apply_double_horn(self):
        for index in range(len(self.letters) - 2, -1, -1):
            pair = "".join(self.letters[index:index + 2]).lower()
            if pair in ("uo", "ưo", "uơ") and (index != 1 or self.letters[0].lower() != "q"):
                self.letters[index:index + 2] = [
                    match_case("ư", self.letters[index]),
                    match_case("ơ", self.letters[index + 1]),
                ]
                return True
            if pair == "ươ":
                self.letters[index:index + 2] = [
                    match_case("u", self.letters[index]),
                    match_case("o", self.letters[index + 1]),
                ]
                return False
        return None
