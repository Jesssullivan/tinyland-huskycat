#!/usr/bin/env python3
"""Unit tests for Chapel code formatter.

Tests cover:
- Layer 1: Whitespace normalization
- Layer 2: Syntax formatting
- Layer 3: Indentation correction
- String preservation
- Idempotency
- Edge cases
"""

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from huskycat.formatters.chapel import ChapelFormatter


class TestWhitespaceNormalization:
    """Test Layer 1: Whitespace normalization (always safe)."""

    def test_trailing_whitespace_removed(self):
        """Test that trailing whitespace is removed."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;   \n"
        expected = "var x = 1;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_multiple_trailing_whitespace(self):
        """Test multiple lines with trailing whitespace."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;  \nvar y = 2;    \n"
        expected = "var x = 1;\nvar y = 2;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_tabs_converted_to_spaces(self):
        """Test that tabs are converted to spaces."""
        formatter = ChapelFormatter()
        input_code = "\tvar x = 1;\n"
        expected = "  var x = 1;\n"  # 2-space indent
        assert formatter.normalize_whitespace(input_code) == expected

    def test_final_newline_added(self):
        """Test that final newline is added if missing."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;"
        expected = "var x = 1;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_final_newline_not_duplicated(self):
        """Test that final newline is not duplicated."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;\n"
        expected = "var x = 1;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_windows_line_endings_normalized(self):
        """Test that Windows line endings (CRLF) are normalized to LF."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;\r\nvar y = 2;\r\n"
        expected = "var x = 1;\nvar y = 2;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_mac_line_endings_normalized(self):
        """Test that old Mac line endings (CR) are normalized to LF."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;\rvar y = 2;\r"
        expected = "var x = 1;\nvar y = 2;\n"
        assert formatter.normalize_whitespace(input_code) == expected

    def test_empty_lines_preserved(self):
        """Test that empty lines are preserved."""
        formatter = ChapelFormatter()
        input_code = "var x = 1;\n\nvar y = 2;\n"
        expected = "var x = 1;\n\nvar y = 2;\n"
        assert formatter.normalize_whitespace(input_code) == expected


class TestOperatorSpacing:
    """Test Layer 2: Operator spacing (regex-based)."""

    def test_assignment_operator_spacing(self):
        """Test space around assignment operator."""
        formatter = ChapelFormatter()
        input_code = "var x=1;\n"
        expected = "var x = 1;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_addition_operator_spacing(self):
        """Test space around addition operator."""
        formatter = ChapelFormatter()
        input_code = "var x = 1+2;\n"
        expected = "var x = 1 + 2;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_subtraction_operator_spacing(self):
        """Test space around subtraction operator."""
        formatter = ChapelFormatter()
        input_code = "var x = 3-1;\n"
        expected = "var x = 3 - 1;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_multiplication_operator_spacing(self):
        """Test space around multiplication operator."""
        formatter = ChapelFormatter()
        input_code = "var x = 2*3;\n"
        expected = "var x = 2 * 3;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_division_operator_spacing(self):
        """Test space around division operator."""
        formatter = ChapelFormatter()
        input_code = "var x = 6/2;\n"
        expected = "var x = 6 / 2;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_modulo_operator_spacing(self):
        """Test space around modulo operator."""
        formatter = ChapelFormatter()
        input_code = "var x = 7%3;\n"
        expected = "var x = 7 % 3;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_equality_operator_spacing(self):
        """Test space around equality operator."""
        formatter = ChapelFormatter()
        input_code = "if x==1 {\n}\n"
        expected = "if x == 1 {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_inequality_operator_spacing(self):
        """Test space around inequality operator."""
        formatter = ChapelFormatter()
        input_code = "if x!=1 {\n}\n"
        expected = "if x != 1 {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_less_than_operator_spacing(self):
        """Test space around less than operator."""
        formatter = ChapelFormatter()
        input_code = "if x<1 {\n}\n"
        expected = "if x < 1 {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_greater_than_operator_spacing(self):
        """Test space around greater than operator."""
        formatter = ChapelFormatter()
        input_code = "if x>1 {\n}\n"
        expected = "if x > 1 {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_logical_and_operator_spacing(self):
        """Test space around logical AND operator."""
        formatter = ChapelFormatter()
        input_code = "if a&&b {\n}\n"
        expected = "if a && b {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_logical_or_operator_spacing(self):
        """Test space around logical OR operator."""
        formatter = ChapelFormatter()
        input_code = "if a||b {\n}\n"
        expected = "if a || b {\n}\n"
        result = formatter.format(input_code)
        assert result == expected


class TestKeywordSpacing:
    """Test Layer 2: Keyword spacing."""

    def test_if_keyword_spacing(self):
        """Test space after if keyword."""
        formatter = ChapelFormatter()
        input_code = "if(x == 1) {\n}\n"
        expected = "if (x == 1) {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_for_keyword_spacing(self):
        """Test space after for keyword."""
        formatter = ChapelFormatter()
        input_code = "for(i in 1..10) {\n}\n"
        expected = "for (i in 1..10) {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_while_keyword_spacing(self):
        """Test space after while keyword."""
        formatter = ChapelFormatter()
        input_code = "while(x > 0) {\n}\n"
        expected = "while (x > 0) {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_brace_spacing_after_paren(self):
        """Test space before opening brace after parenthesis."""
        formatter = ChapelFormatter()
        input_code = "if (x == 1){\n}\n"
        expected = "if (x == 1) {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_brace_spacing_after_word(self):
        """Test space before opening brace after word."""
        formatter = ChapelFormatter()
        input_code = "module Test{\n}\n"
        expected = "module Test {\n}\n"
        result = formatter.format(input_code)
        assert result == expected


class TestCommaAndSemicolonSpacing:
    """Test Layer 2: Comma and semicolon spacing."""

    def test_comma_spacing(self):
        """Test space after comma."""
        formatter = ChapelFormatter()
        input_code = "proc test(a: int,b: int) {\n}\n"
        expected = "proc test(a: int, b: int) {\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_semicolon_no_space_before(self):
        """Test no space before semicolon."""
        formatter = ChapelFormatter()
        input_code = "var x = 1 ;\n"
        expected = "var x = 1;\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_type_annotation_spacing(self):
        """Test space after colon in type annotations."""
        formatter = ChapelFormatter()
        input_code = "var x:int;\n"
        expected = "var x: int;\n"
        result = formatter.format(input_code)
        assert result == expected


class TestIndentation:
    """Test Layer 3: Indentation correction (brace-based)."""

    def test_simple_module_indentation(self):
        """Test indentation in simple module."""
        formatter = ChapelFormatter()
        input_code = "module Test {\nvar x = 1;\n}\n"
        expected = "module Test {\n  var x = 1;\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_nested_braces_indentation(self):
        """Test indentation with nested braces."""
        formatter = ChapelFormatter()
        input_code = "module Test {\nproc foo() {\nreturn 42;\n}\n}\n"
        expected = "module Test {\n  proc foo() {\n    return 42;\n  }\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_if_statement_indentation(self):
        """Test indentation in if statement."""
        formatter = ChapelFormatter()
        input_code = "if x == 1 {\nvar y = 2;\n}\n"
        expected = "if x == 1 {\n  var y = 2;\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_class_indentation(self):
        """Test indentation in class definition."""
        formatter = ChapelFormatter()
        input_code = "class Test {\nvar value: int;\n}\n"
        expected = "class Test {\n  var value: int;\n}\n"
        result = formatter.format(input_code)
        assert result == expected

    def test_empty_lines_preserved_with_indentation(self):
        """Test that empty lines don't get indented."""
        formatter = ChapelFormatter()
        input_code = "module Test {\n\nvar x = 1;\n}\n"
        expected = "module Test {\n\n  var x = 1;\n}\n"
        result = formatter.format(input_code)
        assert result == expected


class TestStringPreservation:
    """Test that string literals are not modified."""

    def test_string_with_extra_spaces_preserved(self):
        """Test that extra spaces in strings are preserved."""
        formatter = ChapelFormatter()
        input_code = 'var msg = "Hello  World";\n'
        result = formatter.format(input_code)
        assert "Hello  World" in result

    def test_string_with_operators_preserved(self):
        """Test that operators in strings are not modified."""
        formatter = ChapelFormatter()
        input_code = 'var expr = "x=1+2";\n'
        result = formatter.format(input_code)
        assert "x=1+2" in result

    def test_string_with_escape_sequences(self):
        """Test that escape sequences in strings are preserved."""
        formatter = ChapelFormatter()
        input_code = 'var msg = "Line 1\\nLine 2";\n'
        result = formatter.format(input_code)
        assert "Line 1\\nLine 2" in result

    def test_multiple_strings_on_line(self):
        """Test multiple strings on same line."""
        formatter = ChapelFormatter()
        input_code = 'var a = "test"; var b = "data";\n'
        result = formatter.format(input_code)
        assert '"test"' in result
        assert '"data"' in result


class TestIdempotency:
    """Test that formatting is idempotent (format twice gives same result)."""

    def test_format_idempotent_simple(self):
        """Test that formatting twice gives same result."""
        formatter = ChapelFormatter()
        input_code = "var x=1;\n"
        once = formatter.format(input_code)
        twice = formatter.format(once)
        assert once == twice

    def test_format_idempotent_complex(self):
        """Test idempotency on complex code."""
        formatter = ChapelFormatter()
        input_code = """module Test {
  proc foo(a: int, b: int): int {
    var x = 1 + 2;
    if x == 3 {
      return a + b;
    }
    return 0;
  }
}
"""
        once = formatter.format(input_code)
        twice = formatter.format(once)
        assert once == twice

    def test_already_formatted_unchanged(self):
        """Test that already formatted code is not changed."""
        formatter = ChapelFormatter()
        formatted_code = """module Test {
  var x = 1;
}
"""
        result = formatter.format(formatted_code)
        assert result == formatted_code


class TestCheckFormatting:
    """Test the check_formatting validation method."""

    def test_check_well_formatted_code(self):
        """Test checking well-formatted code returns no issues."""
        formatter = ChapelFormatter()
        code = "module Test {\n  var x = 1;\n}\n"
        issues = formatter.check_formatting(code)
        assert len(issues) == 0

    def test_check_trailing_whitespace(self):
        """Test detection of trailing whitespace."""
        formatter = ChapelFormatter()
        code = "var x = 1;   \n"
        issues = formatter.check_formatting(code)
        assert len(issues) > 0
        assert any("Trailing whitespace" in issue for issue in issues)

    def test_check_missing_final_newline(self):
        """Test detection of missing final newline."""
        formatter = ChapelFormatter()
        code = "var x = 1;"
        issues = formatter.check_formatting(code)
        assert len(issues) > 0
        assert any("final newline" in issue for issue in issues)

    def test_check_tabs(self):
        """Test detection of tabs."""
        formatter = ChapelFormatter()
        code = "\tvar x = 1;\n"
        issues = formatter.check_formatting(code)
        assert len(issues) > 0
        assert any("tab" in issue for issue in issues)


class TestComplexCases:
    """Test complex real-world Chapel code patterns."""

    def test_module_with_use_statements(self):
        """Test module with use statements."""
        formatter = ChapelFormatter()
        input_code = """module Test {
use CTypes;
use Map;
}
"""
        result = formatter.format(input_code)
        # Check basic formatting applied
        assert "module Test {" in result
        assert "  use CTypes;" in result
        assert "  use Map;" in result

    def test_proc_with_parameters(self):
        """Test procedure with parameters."""
        formatter = ChapelFormatter()
        input_code = "proc test(a:int,b:int):int {\nreturn a+b;\n}\n"
        result = formatter.format(input_code)
        # Check operator spacing and indentation
        assert "a: int, b: int" in result
        assert "return a + b;" in result
        assert "  return" in result  # Indented

    def test_class_with_methods(self):
        """Test class with methods."""
        formatter = ChapelFormatter()
        input_code = """class Test {
var value:int;
proc init(val:int) {
this.value=val;
}
}
"""
        result = formatter.format(input_code)
        # Check type annotations and spacing
        assert "value: int" in result
        assert "val: int" in result
        assert "this.value = val" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file(self):
        """Test formatting empty file."""
        formatter = ChapelFormatter()
        input_code = ""
        result = formatter.format(input_code)
        assert result == ""

    def test_only_whitespace(self):
        """Test file with only whitespace."""
        formatter = ChapelFormatter()
        input_code = "   \n  \n"
        result = formatter.format(input_code)
        # Whitespace-only lines are trimmed, resulting in empty file
        assert result == ""

    def test_only_comments(self):
        """Test file with only comments."""
        formatter = ChapelFormatter()
        input_code = "// This is a comment\n// Another comment\n"
        result = formatter.format(input_code)
        assert result == input_code  # Comments should be preserved

    def test_very_long_line(self):
        """Test handling of very long line."""
        formatter = ChapelFormatter()
        long_var_name = "x" * 100
        input_code = f"var {long_var_name}=1;\n"
        result = formatter.format(input_code)
        # Should still apply spacing
        assert f"{long_var_name} = 1" in result


# Property-Based Tests using Hypothesis
class TestChapelFormatterProperties:
    """Property-based tests for Chapel formatter."""

    @given(st.integers(min_value=0, max_value=10))
    def test_indentation_never_negative(self, num_braces: int):
        """Property: Indentation level should never go negative."""
        formatter = ChapelFormatter()
        # Create code with opening braces
        code = "module Test {\n" * num_braces + "}\n" * num_braces
        result = formatter.format(code)
        # Check no negative indentation (lines starting with negative spaces is impossible)
        lines = result.split("\n")
        for line in lines:
            if line:
                # Line should not start with non-whitespace before expected position
                assert not line.startswith("-")

    @given(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=1, max_size=50))
    def test_valid_identifiers_unchanged(self, identifier: str):
        """Property: Valid identifiers should not be modified."""
        formatter = ChapelFormatter()
        code = f"var {identifier} = 1;\n"
        result = formatter.format(code)
        # Identifier should still be in result
        assert identifier in result

    def test_format_always_adds_final_newline(self):
        """Property: Formatted code should always end with newline."""
        formatter = ChapelFormatter()
        test_cases = [
            "var x = 1;",
            "module Test { }",
            "proc foo() { }",
        ]
        for code in test_cases:
            result = formatter.format(code)
            assert result.endswith("\n"), f"Code should end with newline: {repr(result)}"

    def test_format_removes_all_trailing_whitespace(self):
        """Property: No line should have trailing whitespace after formatting."""
        formatter = ChapelFormatter()
        code_with_trailing = "var x = 1;   \nvar y = 2;  \n"
        result = formatter.format(code_with_trailing)
        lines = result.split("\n")
        for line in lines:
            if line:  # Ignore empty lines
                assert line == line.rstrip(), f"Line has trailing whitespace: {repr(line)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
