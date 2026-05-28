from utils import DalvikParser, Lexer, MethodContext


class Colors:
    PASS = "\033[92m"
    FAIL = "\033[91m"
    RESET = "\033[0m"


def run_test(name, code, expected_errors=None):
    """
    Runs a single test case.
    - If expected_error_substring is None, we expect PASS.
    - If it's a string, we expect a FAIL containing that string.
    """
    if expected_errors is None:
        expected_errors = []

    lexer = Lexer()
    ctx = MethodContext()
    parser = DalvikParser(ctx)

    parser.parse_code(code, lexer)
    actual_errors = parser.errors

    if len(actual_errors) != len(expected_errors):
        print(f"{Colors.FAIL}[FAIL] {name}{Colors.RESET}")
        print(
            f"       Expected {len(expected_errors)} errors, got {len(actual_errors)}."
        )
        print(f"       Expected: {expected_errors}")
        print(f"       Got:      {actual_errors}")
        return False

    for i in range(len(expected_errors)):
        exp_line, exp_sub = expected_errors[i]
        act_line, act_msg = actual_errors[i]
        if exp_line != act_line or exp_sub not in act_msg:
            print(f"{Colors.FAIL}[FAIL] {name}{Colors.RESET}")
            print(f"       Mismatch details:")
            print(f"       Expected: Line {exp_line} containing '{exp_sub}'")
            print(f"       Got:      Line {act_line} with message '{act_msg}'")
            return False

    print(f"{Colors.PASS}[PASS] {name}{Colors.RESET}")
    return True


# ==========================================
# TEST CASES
# ==========================================


def main():
    tests_passed = 0
    total_tests = 0

    print("=== Running Regression Tests ===\n")

    total_tests += 1
    code_semantics_valid = """
    .method public test()V
        .registers 4
        const/4 v0, -8
        const/4 v1, 7
        move v0, v1
    .end method
    """
    if run_test(
        "Semantics: Valid const/4 range",
        code_semantics_valid,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_semantics_invalid = """
    .method public test()V
        .registers 4
        const/4 v0, 8
    .end method
    """
    if run_test(
        "Semantics: Invalid const/4 range",
        code_semantics_invalid,
        [(3, "Literal 8 out of range for 4-bit signed int. Allowed: [-8, 7]")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_scope_reg = """
    .method public test()V
        .registers 2
        move v0, v1
        move v1, v2
    .end method
    """
    if run_test(
        "Scope: Register Out of Bounds",
        code_scope_reg,
        [(4, "Local register v2 out of bounds (max v1)")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_scope_orphan = """
    const/4 v0, 1
    """
    if run_test(
        "Scope: Instruction outside method",
        code_scope_orphan,
        [(1, "Instruction 'v0' outside method.")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_jumps = """
    .method public test()V
        .registers 1
        goto :future
        return-void
        :future
    .end method
    """
    if run_test(
        "Labels: Valid Forward Jump",
        code_jumps,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_jumps_bad = """
    .method public test()V
        .registers 1
        goto :nowhere
    .end method
    """
    if run_test(
        "Labels: Invalid Jump Target",
        code_jumps_bad,
        [(3, "Jump target ':nowhere' not found in this method.")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_branch_mixed = """
    .method public test()V
        .registers 2
        :start
        const/4 v0, 4
        const/4 v1, 3
        if-eq v0, v1, :start
        if-eqz v0, :start
    .end method
    """
    if run_test(
        "Branching: Correct usage of if-eq and if-eqz",
        code_branch_mixed,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_branch_fail = """
    .method public test()V
        .registers 2
        :start
        const/4 v0, 4
        const/4 v1, 3
        if-eqz v0, v1, :start
    .end method
    """
    if run_test(
        "Branching: if-eqz with too many regs",
        code_branch_fail,
        [(6, "Expected LABEL, but found REGISTER")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_params_wide = """
    .method public test(J)V
        .registers 1
        # (J)V means p0 is 'this', p1+p2 is Long Arg.
        # Max p-index is 2.
        move v0, p2
    .end method
    """
    if run_test(
        "Params: Wide Type (Long) calculation",
        code_params_wide,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_params_array = """
    .method public static test([J)V
        .registers 1
        # ([J)V is static (no this). Arg is Array (1 reg).
        # Max p-index is 0.
        move v0, p1
    .end method
    """
    if run_test(
        "Params: Array of Longs (Reference)",
        code_params_array,
        [(5, "Parameter register p1 out of bounds. Max is p0.")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_invoke_valid = """
    .method public test()V
        .registers 5
        # Standard: 3 args
        invoke-virtual {v0, v1, v2}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;

        # Range: v0 to v4 (5 registers)
        invoke-static/range {v0 .. v4}, Lutil/Log;->print()V
    .end method
    """
    if run_test(
        "Invoke: Valid Standard and Range",
        code_invoke_valid,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_invoke_fail_limit = """
    .method public test()V
        .registers 10
        # Fail: Standard invoke cannot take 6 arguments
        invoke-static {v0, v1, v2, v3, v4, v5}, Lbad/Code;->run()V
    .end method
    """
    if run_test(
        "Invoke: Exceeds 5 args limit",
        code_invoke_fail_limit,
        [(4, "Standard invoke supports max 5 registers. Found 6. Use /range instead.")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_invoke_fail_range = """
    .method public test()V
        .registers 5
        # Fail: Start > End
        invoke-direct/range {v2 .. v0}, Lbad/Range;->run()V
    .end method
    """
    if run_test(
        "Invoke: Invalid Range Order",
        code_invoke_fail_range,
        [(4, "Invalid register range: v2 .. v0")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_params_array = """
    .method public static test()V
        .registers 1
        # No parameter.
        move v0, p0
    .end method
    """
    if run_test(
        "Params: Invalid call with no parameter",
        code_params_array,
        [(4, "Parameter register p0 out of bounds. Method has no parameters.")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_method_unended = """
    .method public test()V
        .registers 2
        invoke-static {v1}, Lcom/samsung/android/settings/uwb/UwbPreferenceController;->-$$Nest$fgetmUwbManager(Lcom/samsung/android/settings/uwb/UwbPreferenceController;)Landroid/uwb/UwbManager;
        return-void
    """
    if run_test(
        "Method: Invalid call with no closing",
        code_method_unended,
        [(5, "Unexpected EOF: missing '.end method'")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_method_in_method = """
    .method public test()V
        .registers 1
        return-void
    .method public test()V
        .registers 1
        return-void
    .end method
    .end method
    """
    if run_test(
        "Method: method inside a method",
        code_method_in_method,
        [(4, "Unexpected method declaration: already in a method")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_random = """
    # virtual methods
    .method public final run()V
        .registers 2

        iget-object v0, p0, Lcom/samsung/android/settings/uwb/UwbPreferenceController$1;->this$0:Lcom/samsung/android/settings/uwb/UwbPreferenceController;

        invoke-static {v0}, Lcom/samsung/android/settings/uwb/UwbPreferenceController;->-$$Nest$mupdateSummary(Lcom/samsung/android/settings/uwb/UwbPreferenceController;)V

        iget-object v0, p0, Lcom/samsung/android/settings/uwb/UwbPreferenceController$1;->this$0:Lcom/samsung/android/settings/uwb/UwbPreferenceController;

        invoke-static {v0}, Lcom/samsung/android/settings/uwb/UwbPreferenceController;->-$$Nest$fgetmUwbSettingPolicy(Lcom/samsung/android/settings/uwb/UwbPreferenceController;)Lcom/samsung/android/settings/uwb/UwbSettingPolicy;

        move-result-object v0

        return-void
    .end method
    """
    if run_test(
        "Global: good code",
        code_random,
        [],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_registers_vs_locals = """
    .method static public test([J)V
        .registers 3
        # allowed : v0, v1 = p0, v2 = p1

        const/4 v2, 0
        const/4 v3, 0

        return-void
    .end method

    .method static public test([J)V
        .locals 3
        # allowed : v0, v1, v2, v3 = p0, v4 = p1

        const/4 v2, 0
        const/4 v3, 0

        return-void
    .end method
    """
    if run_test(
        "Method: registers vs locals",
        code_registers_vs_locals,
        [(6, "Local register v3 out of bounds (max v2).")],
    ):
        tests_passed += 1

    # ----------------------

    total_tests += 1
    code_multiple_errors = """
    .method public test()V
        .registers 2
        const/4 v0, 99
        move v1, v5
        goto :nonexistent
    .end method
    """
    if run_test(
        "Method: Multiple Errors in One Method",
        code_multiple_errors,
        [
            (3, "Literal 99 out of range for 4-bit signed int. Allowed: [-8, 7]"),
            (4, "Local register v5 out of bounds (max v1)."),
            (5, "Jump target ':nonexistent' not found in this method."),
        ],
    ):
        tests_passed += 1

    print("\n" + "=" * 30)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    if tests_passed == total_tests:
        print(f"{Colors.PASS}FINE{Colors.RESET}")
    else:
        print(f"{Colors.FAIL}REGRESSIONS DETECTED{Colors.RESET}")


if __name__ == "__main__":
    main()
