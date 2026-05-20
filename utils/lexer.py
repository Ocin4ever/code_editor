import re

from .tokens import TOKEN_TYPES, Token


class Lexer:
    def __init__(self):
        self.rules = TOKEN_TYPES

    def tokenize(self, text):
        tokens = []
        pos = 0
        while pos < len(text):
            match = None
            for token_type, pattern in self.rules:
                regex = re.compile(pattern)
                match = regex.match(text, pos)
                if match:
                    if token_type not in ["WHITESPACE", "COMMENT"]:
                        tokens.append(Token(token_type, match.group(0)))
                    pos = (
                        match.end()
                    )  # We need to shift the index to the end of the token
                    break

            if not match:
                raise SyntaxError(f"Illegal char at position {pos}: {text[pos]}")
        return tokens
