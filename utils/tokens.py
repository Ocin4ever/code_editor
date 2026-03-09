TOKEN_TYPES = [
    # --- Comments ---
    ('COMMENT',      r'#.*'),
    
    # --- Directives ---
    ('DIR_METHOD_START', r'\.method'),      
    ('DIR_METHOD_END',   r'\.end method'),  
    ('DIR_REGISTERS',    r'\.registers'), 
    # ('METHOD_REF',   r'L[\w/$]+;->[\w$]+\(.*\)\S+'),
    ('METHOD_REF',   r'L[\w/$]+;->[\w$<>-]+\(.*\)\S+'), 
    ('FIELD_REF',        r'L[\w/$]+;->[\w$]+:\S+'), 
    
    # --- Instructions ---
    ('OP_CONST',   r'const(-wide(/16|/32)?|(/4|/16|/high16)?|-string(-jumbo)?|-class)?'),
    # Matches: move-result, move-result-wide, move-result-object, move-exception
    ('OP_MOVE_RESULT', r'move-(result(-wide|-object)?|exception)'),
    
    # Matches: move, move/from16, move/16, move-wide, move-object, etc.
    ('OP_MOVE',        r'move(-wide|-object)?(/from16|/16)?'),        
    ('OP_RETURN',    r'return(-void|-wide|-object)?'),
    ('OP_GOTO',      r'goto(/16|/32)?'),

    # Matches if-eq, if-ne, if-lt, if-ge, if-gt, if-le
    ('OP_BRANCH_BIN',  r'if-(eq|ne|lt|ge|gt|le)(?![z])'), 
    
    # Matches if-eqz, if-nez, if-ltz, if-gez, if-gtz, if-lez
    ('OP_BRANCH_ZERO', r'if-(eqz|nez|ltz|gez|gtz|lez)'),  

    # --- Invocation Instructions ---
    # Matches: invoke-virtual, invoke-static, invoke-direct, etc.
    ('OP_INVOKE',       r'invoke-(virtual|direct|static|super|interface)(?!/range)'),
    
    # Matches: invoke-virtual/range, invoke-static/range, etc.
    ('OP_INVOKE_RANGE', r'invoke-(virtual|direct|static|super|interface)/range'),

    ('OP_IGET',       r'iget(-wide|-object|-boolean|-byte|-char|-short)?'),

    # --- Syntax for Argument Lists ---
    ('BRACE_OPEN',   r'{'),
    ('BRACE_CLOSE',  r'}'),
    ('DOT_DOT',      r'\.\.'), # For range syntax "v0 .. v4"  
    
    # --- Operands ---
    ('REGISTER',     r'[vp]\d+'),       
    ('LABEL',        r':[a-zA-Z0-9_]+'),
    ('HEX_LITERAL',  r'-?0x[0-9a-fA-F]+'), 
    ('INT_LITERAL',  r'-?\d+'),         
    ('STRING',       r'"[^"]*"'),       
    ('COMMA',        r','),
    
    # --- Utility ---
    ('WHITESPACE',   r'\s+'),           
    ('UNKNOWN',      r'.'),             
]

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self): return f"Token({self.type}, '{self.value}')"