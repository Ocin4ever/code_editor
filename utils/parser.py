class DalvikParser:
    def __init__(self, context):
        self.tokens = []
        self.pos = 0
        self.ctx = context
        self.lines = []
        self.line_index = 0
        self.errors = []

    # --- Main function ---
    def parse_code(self, code, lexer):
        """
        Parse a full block of Dalvik code and collects errors.
        """
        self.errors = []
        self.lines = code.splitlines()

        for i, line in enumerate(self.lines):
            clean = line.strip()
            if not clean:
                continue

            try:
                tokens = lexer.tokenize(line)
                if not tokens:
                    continue

                self.tokens = tokens
                self.pos = 0
                self.line_index = i

                self.parse_line()

            except Exception as e:
                self.errors.append((i, str(e)))

        if self.ctx.in_method:
            self.errors.append(
                (len(self.lines) - 1, "Unexpected EOF: missing '.end method'")
            )
            self.ctx.exit_method()

        return len(self.errors) == 0

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

    # --- Semantic Checks ---
    def check_register_access(self, token):
        if not self.ctx.in_method:
            raise SyntaxError(f"Instruction '{token.value}' outside method.")

        reg_type = token.value[0]  # 'v' or 'p'
        idx = int(token.value[1:])

        if reg_type == "v":
            if idx >= self.ctx.register_count:
                raise ValueError(
                    f"Local register {token.value} out of bounds (max v{self.ctx.register_count - 1})."
                )

        elif reg_type == "p":
            max_p = self.ctx.get_max_p_index()
            if idx > max_p:
                msg = f"Parameter register {token.value} out of bounds."
                if max_p == -1:
                    msg += " Method has no parameters."
                else:
                    msg += f" Max is p{max_p}."
                raise ValueError(msg)

    def get_register_index(self, token):
        return int(token.value[1:])  # Strip 'v' or 'p'

    def get_literal_value(self, token):
        base = 16 if token.value.startswith(("0x", "-0x")) else 10
        return int(token.value, base)

    def check_register_width(self, token, max_bits):
        """Validates if register index fits in N bits (unsigned)."""
        idx = self.get_register_index(token)
        max_val = (1 << max_bits) - 1
        if idx > max_val:
            raise ValueError(
                f"Register {token.value} out of range for instruction. Max: v{max_val} ({max_bits}-bit)."
            )

    def check_literal_width(self, token, max_bits):
        """Validates if literal fits in N bits (signed)."""
        val = self.get_literal_value(token)
        min_val = -(1 << (max_bits - 1))
        max_val = (1 << (max_bits - 1)) - 1
        if not (min_val <= val <= max_val):
            raise ValueError(
                f"Literal {token.value} out of range for {max_bits}-bit signed int. Allowed: [{min_val}, {max_val}]"
            )

    def check_label_target(self, token):
        # The Context already knows all labels from the forward scan
        if not self.ctx.has_label(token.value):
            raise ValueError(f"Jump target '{token.value}' not found in this method.")

    # --- Syntaxic Checks ---
    def parse_line(self):
        """
        Decide the order of the choosen instructions
        """
        token = self.current_token()
        if token is None:
            return False

        # Directives
        match token.type:
            case "DIR_METHOD_START":
                if self.lines is not None:
                    self.ctx.enter_method(self.lines, self.line_index)
                self.eat("DIR_METHOD_START")
                while self.current_token():
                    self.pos += 1

            case "DIR_METHOD_END":
                self.eat("DIR_METHOD_END")
                self.ctx.exit_method()

            case "DIR_REGISTERS":
                dir = self.eat("DIR_REGISTERS")
                lit = self.eat("INT_LITERAL")
                self.ctx.set_registers(int(lit.value), dir.value)

            case "LABEL":
                self.eat("LABEL")

            case token_type if token_type.startswith("OP_"):
                self.parse_instruction()

            case _:
                self.pos += 1
                raise SyntaxError(f"Unexpected token: {token.value}")

        return True

    def parse_instruction(self):
        token = self.current_token()
        if token is None:
            return

        match token.type:
            case "OP_CONST":
                self.parse_const()
            case "OP_BRANCH_BIN":
                self.parse_binary_branch()
            case "OP_BRANCH_ZERO":
                self.parse_zero_branch()
            case "OP_MOVE":
                self.parse_move()
            case "OP_MOVE_RESULT":
                self.parse_move_result()
            case "OP_GOTO":
                self.parse_goto()
            case "OP_RETURN":
                self.parse_return()
            case "OP_INVOKE":
                self.parse_invoke_standard()
            case "OP_INVOKE_RANGE":
                self.parse_invoke_range()
            case "OP_IGET":
                self.parse_iget()

    def parse_const(self):
        """
        Format:
        const vx, lit
        const/4 vx, lit
        const/16 vx, lit
        const/high16 vx, lit
        const-wide vx, lit
        const-wide/16 vx, lit
        const-wide/high16 vx, lit
        const-wide/32 vx, lit
        const-string vx, str
        const-string-jumbo vx, str
        const-class vx, obj
        """

        tok = self.eat("OP_CONST")
        op_name = tok.value

        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("COMMA")

        if "const-class" in op_name:
            self.eat("INT_LITERAL")  # This needs to be handled properly
        elif "const-string" in op_name:
            self.eat("STRING")
        else:
            lit1 = self.eat("INT_LITERAL")
            if "32" in op_name:
                self.check_register_width(reg1, 8)
                self.check_literal_width(lit1, 32)
            if "16" in op_name:
                self.check_register_width(reg1, 8)
                self.check_literal_width(lit1, 16)
            if "4" in op_name:
                # Apparently registers are stored on 8 bits (except for const/4)
                self.check_register_width(reg1, 4)
                self.check_literal_width(lit1, 4)

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

        self.eat("OP_BRANCH_BIN")
        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("COMMA")
        reg2 = self.eat("REGISTER")
        self.check_register_access(reg2)
        self.eat("COMMA")
        lbl1 = self.eat("LABEL")
        self.check_label_target(lbl1)

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

        self.eat("OP_BRANCH_ZERO")
        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("COMMA")
        lbl1 = self.eat("LABEL")
        self.check_label_target(lbl1)

    def parse_move(self):
        """
        Format:
        move vx, vy
        move-wide vx, vy
        move-object vx, vy
        move/from16 vx, vy
        move/16 vx, vy
        move-wide/from16 vx, vy
        move-wide/16 vx, vy
        move-object/from16 vx, vy
        move-object/16 vx, vy
        """

        tok = self.eat("OP_MOVE")
        op_name = tok.value

        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("COMMA")
        reg2 = self.eat("REGISTER")
        self.check_register_access(reg2)

        if "/from16" in op_name:
            self.check_register_width(reg1, 8)
            self.check_register_width(reg2, 16)
        elif "/16" in op_name:
            self.check_register_width(reg1, 16)
            self.check_register_width(reg2, 16)
        else:
            self.check_register_width(reg1, 4)
            self.check_register_width(reg2, 4)

    def parse_move_result(self):
        """
        Format:
        move-result vx
        move-result-wide vx
        move-result-object vx
        move-exception vx
        """

        self.eat("OP_MOVE_RESULT")
        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.check_register_width(reg1, 8)

    def parse_goto(self):
        """
        Format:
        goto :label
        goto/16 :label
        goto/32 :label
        """

        self.eat("OP_GOTO")
        lbl = self.eat("LABEL")
        self.check_label_target(lbl)

    def parse_return(self):
        """
        Format:
        return vx
        return-void
        return-wide vx
        return-object vx
        """

        tok = self.eat("OP_RETURN")
        op_name = tok.value

        if "void" in op_name:
            return
        else:
            reg1 = self.eat("REGISTER")
            self.check_register_access(reg1)

    def parse_invoke_standard(self):
        """
        Format:
        invoke-virtual {vx, vy, ...}, MethodRef
        invoke-super {vx, vy, ...}, MethodRef
        invoke-direct {vx, vy, ...}, MethodRef
        invoke-static {vx, vy, ...}, MethodRef
        invoke-interface {vx, vy, ...}, MethodRef
        """

        self.eat("OP_INVOKE")
        self.eat("BRACE_OPEN")

        arg_count = 0
        token = self.current_token()
        if token and token.type != "BRACE_CLOSE":
            while True:
                reg1 = self.eat("REGISTER")
                self.check_register_access(reg1)
                arg_count += 1

                token = self.current_token()
                if token and token.type == "COMMA":
                    self.eat("COMMA")
                else:
                    break
        self.eat("BRACE_CLOSE")

        if arg_count > 5:
            raise ValueError(
                f"Standard invoke supports max 5 registers. Found {arg_count}. Use /range instead."
            )

        self.eat("COMMA")
        self.eat("METHOD_REF")

    def parse_invoke_range(self):
        """
        Format:
        invoke-virtual/range {vx .. vy}, MethodRef
        invoke-super/range {vx .. vy}, MethodRef
        invoke-direct/range {vx .. vy}, MethodRef
        invoke-static/range {vx .. vy}, MethodRef
        invoke-interface/range {vx .. vy}, MethodRef
        """

        self.eat("OP_INVOKE_RANGE")

        self.eat("BRACE_OPEN")
        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("DOT_DOT")
        reg2 = self.eat("REGISTER")
        self.check_register_access(reg2)
        self.eat("BRACE_CLOSE")

        # Validate Range Consistency (e.g. v0 .. v4)
        s_type, s_idx = reg1.value[0], int(reg1.value[1:])
        e_type, e_idx = reg2.value[0], int(reg2.value[1:])

        if s_type != e_type:
            raise ValueError("Range registers must be of the same type (v or p).")
        if s_idx > e_idx:
            raise ValueError(f"Invalid register range: {reg1.value} .. {reg2.value}")

        self.eat("COMMA")

        self.eat("METHOD_REF")

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

        self.eat("OP_IGET")
        reg1 = self.eat("REGISTER")
        self.check_register_access(reg1)
        self.eat("COMMA")
        reg2 = self.eat("REGISTER")
        self.check_register_access(reg2)
        self.eat("COMMA")
        self.eat("FIELD_REF")
