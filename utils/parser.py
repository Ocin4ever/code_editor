from .tokens import Token

class SmaliParser:
    def __init__(self, tokens, context, lines=None, line_index=0):
        self.tokens = tokens
        self.pos = 0
        self.ctx = context
        self.lines = lines
        self.line_index = line_index

    # --- Utilities ---
    def current_token(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, token_type):
        token = self.current_token()
        if token and token.type == token_type:
            self.pos += 1
            return token
        found = token.type if token else "EOF"
        raise SyntaxError(f"Expected {token_type}, but found {found}")

    # --- Semantic Validators ---
    def check_register_access(self, token):
        if not self.ctx.in_method:
             raise SyntaxError(f"Instruction '{token.value}' outside method.")
        
        reg_type = token.value[0] # 'v' or 'p'
        idx = int(token.value[1:])
        
        if reg_type == 'v':
            if idx >= self.ctx.register_count:
                raise ValueError(f"Local register {token.value} out of bounds (max v{self.ctx.register_count-1}).")
        
        elif reg_type == 'p':
            max_p = self.ctx.get_max_p_index()
            if idx > max_p:
                msg = f"Parameter register {token.value} out of bounds."
                if max_p == -1:
                    msg += " Method has no parameters."
                else:
                    msg += f" Max is p{max_p}."
                raise ValueError(msg)

    def get_register_index(self, token):
        return int(token.value[1:]) # Strip 'v' or 'p'
                
    def get_literal_value(self, token):
        base = 16 if token.value.startswith(('0x', '-0x')) else 10
        return int(token.value, base)

    def check_register_width(self, token, max_bits):
        """Validates if register index fits in N bits (unsigned)."""
        idx = self.get_register_index(token)
        max_val = (1 << max_bits) - 1
        if idx > max_val:
            raise ValueError(f"Register {token.value} out of range for instruction. Max: v{max_val} ({max_bits}-bit).")

    def check_literal_width(self, token, max_bits):
        """Validates if literal fits in N bits (signed)."""
        val = self.get_literal_value(token)
        min_val = -(1 << (max_bits - 1))
        max_val = (1 << (max_bits - 1)) - 1
        if not (min_val <= val <= max_val):
             raise ValueError(f"Literal {token.value} out of range for {max_bits}-bit signed int. Allowed: [{min_val}, {max_val}]")

    def check_label_target(self, token):
        # The Context already knows all labels from the forward scan
        if not self.ctx.has_label(token.value):
            raise ValueError(f"Jump target '{token.value}' not found in this method.")

    def parse_line(self):
        """
        Decide the order of the choosen instructions
        """
        token = self.current_token()
        if not token: return False

        # Directives
        if token.type == 'DIR_METHOD_START':
            if self.lines is not None:
                self.ctx.enter_method(self.lines, self.line_index)

            self.eat('DIR_METHOD_START')
            while self.current_token(): self.pos += 1 
            
        elif token.type == 'DIR_METHOD_END':
            self.eat('DIR_METHOD_END')
            self.ctx.exit_method()

        elif token.type == 'DIR_REGISTERS':
            self.eat('DIR_REGISTERS')
            lit = self.eat('INT_LITERAL')
            self.ctx.set_registers(int(lit.value))

        elif token.type == 'LABEL':
            self.eat('LABEL')

        elif token.type.startswith('OP_'):
            self.parse_instruction()
        
        else:
            self.pos += 1
            raise SyntaxError(f"Unexpected token: {token.value}")
        return True

    def parse_instruction(self):
        token = self.current_token()
        
        if token.type == 'OP_CONST_4':
            self.eat('OP_CONST_4')
            reg = self.eat('REGISTER')
            self.check_register_width(reg, 4)
            self.check_register_access(reg)
            self.eat('COMMA')
            lit = self.eat('INT_LITERAL')
            self.check_literal_width(lit, 4)

        elif token.type == 'OP_BRANCH_BIN':
            self.parse_binary_branch()
            
        elif token.type == 'OP_BRANCH_ZERO':
            self.parse_zero_branch()

        elif token.type == 'OP_MOVE':
            self.parse_move()

        elif token.type == 'OP_MOVE_RESULT':
            self.parse_move_result()

        elif token.type == 'OP_GOTO':
            self.eat('OP_GOTO')
            lab = self.eat('LABEL')
            self.check_label_target(lab) # <--- Validates Jump
            
        elif token.type == 'OP_RETURN':
            self.eat('OP_RETURN')

        elif token.type == 'OP_INVOKE':
            self.parse_invoke_standard()

        elif token.type == 'OP_INVOKE_RANGE':
            self.parse_invoke_range()

        elif token.type == 'OP_IGET':
            self.parse_iget()

    def parse_binary_branch(self):
        """
        Format: 
        if-eq vx, vy, :label
        if-ne vx, vy, :label
        if-lt vx, vy, :label
        if-ge vx, vy, :label
        if-gt vx, vy, :label
        if-le vx, vy, :label
        """

        self.eat('OP_BRANCH_BIN')
        reg1 = self.eat('REGISTER')
        self.check_register_access(reg1)
        self.eat('COMMA')
        reg2 = self.eat('REGISTER')
        self.check_register_access(reg2)
        self.eat('COMMA')
        lab = self.eat('LABEL')
        self.check_label_target(lab)

    def parse_zero_branch(self):
        """
        Format: 
        if-eqz vx, :label
        if-nez vx, :label
        if-ltz vx, :label
        if-gez vx, :label
        if-gtz vx, :label
        if-lez vx, :label
        """

        self.eat('OP_BRANCH_ZERO')
        r1 = self.eat('REGISTER')
        self.check_register_access(r1)
        self.eat('COMMA')
        lbl = self.eat('LABEL')
        self.check_label_target(lbl)
    
    def parse_invoke_standard(self):
        """
        Format:
        invoke-virtual {vx, vy, ...}, MethodRef
        invoke-super {vx, vy, ...}, MethodRef
        invoke-direct {vx, vy, ...}, MethodRef
        invoke-static {vx, vy, ...}, MethodRef
        invoke-interface {vx, vy, ...}, MethodRef
        """

        self.eat('OP_INVOKE')
        
        self.eat('BRACE_OPEN')
        arg_count = 0
        if self.current_token().type != 'BRACE_CLOSE':
            while True:
                reg = self.eat('REGISTER')
                self.check_register_access(reg)
                arg_count += 1
                
                if self.current_token().type == 'COMMA':
                    self.eat('COMMA')
                else:
                    break
        self.eat('BRACE_CLOSE')
        
        if arg_count > 5:
            raise ValueError(f"Standard invoke supports max 5 registers. Found {arg_count}. Use /range instead.")

        self.eat('COMMA')
        self.eat('METHOD_REF')

    def parse_invoke_range(self):
        """
        Format:
        invoke-virtual/range {vx .. vy}, MethodRef
        invoke-super/range {vx .. vy}, MethodRef
        invoke-direct/range {vx .. vy}, MethodRef
        invoke-static/range {vx .. vy}, MethodRef
        invoke-interface/range {vx .. vy}, MethodRef
        """

        self.eat('OP_INVOKE_RANGE')

        self.eat('BRACE_OPEN')
        start_reg = self.eat('REGISTER')
        self.check_register_access(start_reg)
        self.eat('DOT_DOT')
        end_reg = self.eat('REGISTER')
        self.check_register_access(end_reg)
        self.eat('BRACE_CLOSE')
        
        # Validate Range Consistency (e.g. v0 .. v4)
        s_type, s_idx = start_reg.value[0], int(start_reg.value[1:])
        e_type, e_idx = end_reg.value[0], int(end_reg.value[1:])
        
        if s_type != e_type:
            raise ValueError("Range registers must be of the same type (v or p).")
        if s_idx > e_idx:
            raise ValueError(f"Invalid register range: {start_reg.value} .. {end_reg.value}")

        self.eat('COMMA')

        self.eat('METHOD_REF')

    def parse_iget(self):
        """
        Format: 
        iget vx, vy, :label
        iget-wide vx, vy, :label
        iget-object vx, vy, :label
        iget-boolean vx, vy, :label
        iget-byte vx, vy, :label
        iget-char vx, vy, :label
        iget-short vx, vy, :label
        """

        self.eat('OP_IGET')
        r1 = self.eat('REGISTER')
        self.check_register_access(r1)
        self.eat('COMMA')
        r2 = self.eat('REGISTER')
        self.check_register_access(r2)
        self.eat('COMMA')
        self.eat('FIELD_REF')

    def parse_move(self):
        """
        Format:
        move vx,vy
        move-wide vx, vy
        move-object vx, vy
        move/from16 vx, vy
        move/16 vx, vy
        move-wide/from16 vx, vy
        move-wide/16 vx, vy
        move-object/from16 vx, vy
        move-object/16 vx, vy
        """

        token = self.eat('OP_MOVE')
        op_name = token.value

        reg1 = self.eat('REGISTER')
        self.check_register_access(reg1)
        self.eat('COMMA')
        reg2 = self.eat('REGISTER')
        self.check_register_access(reg2)

        if '/from16' in op_name:
            self.check_register_width(reg1, 8)
            self.check_register_width(reg2, 16)
        elif '/16' in op_name:
            self.check_register_width(reg1, 16)
            self.check_register_width(reg2, 16)
        else:
            self.check_register_width(reg1, 8)
            self.check_register_width(reg2, 8)

    def parse_move_result(self):
        """
        Format:
        move-result vx
        move-result-wide vx
        move-result-object vx
        move-exception vx
        """
        
        token = self.eat('OP_MOVE_RESULT')
        reg = self.eat('REGISTER')
        self.check_register_access(reg)
        self.check_register_width(reg, 8)