# fmt: off

TOKEN_TYPES = [
    # --- Comments ---
    ('COMMENT',      r'#.*'),

    # --- Directives ---
    ('DIR_METHOD_START', r'\.method'),
    ('DIR_METHOD_END',   r'\.end method'),
    ('DIR_REGISTERS',    r'\.registers|\.locals'),
    ('METHOD_REF',       r'L[\w/$]+;->[\w$<>-]+\(.*\)\S+'),
    ('FIELD_REF',        r'L[\w/$]+;->[\w$]+:\S+'),

    # --- Instructions ---
    ('OP_CONST',         r'const(-wide(/16|/32)?|(/4|/16|/high16)?|-string(-jumbo)?|-class)?'),
    # Matches:
    # const
    # const/4
    # const/16
    # const/high16
    # const-wide
    # const-wide/16
    # const-wide/high16
    # const-wide/32
    # const-string
    # const-string-jumbo
    # const-class

    ('OP_MOVE_RESULT',   r'move-(result(-wide|-object)?|exception)'),
    # Matches:
    # move-result
    # move-result-wide
    # move-result-object
    # move-exception

    ('OP_MOVE',          r'move(-wide|-object)?(/from16|/16)?'),
    # Matches:
    # move
    # move-wide
    # move-object
    # move/from16
    # move/16
    # move-wide/from16
    # move-wide/16
    # move-object/from16
    # move-object/16

    ('OP_RETURN',        r'return(-void|-wide|-object)?'),
    # Matches:
    # return
    # return-void
    # return-wide
    # return-object

    ('OP_GOTO',          r'goto(/16|/32)?'),
    # Matches:
    # goto
    # goto/16
    # goto/32

    ('OP_BRANCH_BIN',    r'if-(eq|ne|lt|ge|gt|le)(?![z])'),
    # Matches:
    # if-eq
    # if-ne
    # if-lt
    # if-ge
    # if-gt
    # if-le

    ('OP_BRANCH_ZERO',   r'if-(eqz|nez|ltz|gez|gtz|lez)'),
    # Matches:
    # if-nez
    # if-eqz
    # if-ltz
    # if-gez
    # if-gtz
    # if-lez

    ('OP_INVOKE',        r'invoke-(virtual|direct|static|super|interface)(?!/range)'),
    # Matches:
    # invoke-virtual
    # invoke-super
    # invoke-direct
    # invoke-static
    # invoke-interface

    ('OP_INVOKE_RANGE',  r'invoke-(virtual|direct|static|super|interface)/range'),
    # Matches:
    # invoke-virtual/range
    # invoke-super/range
    # invoke-direct/range
    # invoke-static/range
    # invoke-interface/range

    ('OP_IGET',          r'iget(-wide|-object|-boolean|-byte|-char|-short)?'),
    # Matches:
    # iget
    # iget-wide
    # iget-object
    # iget-boolean
    # iget-byte
    # iget-char
    # iget-short

    # --- Argument Lists ---
    ('BRACE_OPEN',       r'{'),
    ('BRACE_CLOSE',      r'}'),
    ('DOT_DOT',          r'\.\.'),

    # --- Operands ---
    ('REGISTER',         r'[vp]\d+'),
    ('LABEL',            r':[a-zA-Z0-9_]+'),
    ('HEX_LITERAL',      r'-?0x[0-9a-fA-F]+'),
    ('INT_LITERAL',      r'-?\d+'),
    ('STRING',           r'"[^"]*"'),
    ('COMMA',            r','),

    # --- Utility ---
    ('WHITESPACE',       r'\s+'),
    ('UNKNOWN',          r'.'),
]


class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"
