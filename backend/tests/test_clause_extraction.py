"""Tests for clause reference extraction in UnstructuredPDFParser.

Tests various Australian legal document citation patterns:
- Section numbers (3.2.1)
- Clause numbers (Clause 42)
- Regulations (Regulation 12)
- Subsections with brackets (5(2)(a))
- Schedules and Annexes
- Parts (Part 3, Part III)
"""

import pytest

from green_gov_rag.etl.parsers.unstructured_parser import UnstructuredPDFParser


class TestClauseExtraction:
    """Test clause reference extraction patterns."""

    def setup_method(self):
        """Initialize parser for testing."""
        self.parser = UnstructuredPDFParser()

    def test_section_number_with_prefix(self):
        """Test: 'Section 3.2.1' → 's.3.2.1'"""
        hierarchy = ["Part 3", "Section 3.2.1 Methods"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.3.2.1"

    def test_section_number_standalone(self):
        """Test: '3.2.1 Market-Based Accounting' → 's.3.2.1'"""
        hierarchy = ["Part 3", "3.2.1 Market-Based Accounting"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.3.2.1"

    def test_section_number_only(self):
        """Test: '5.4' → 's.5.4'"""
        hierarchy = ["Chapter 5", "5.4"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.5.4"

    def test_clause_reference(self):
        """Test: 'Clause 42' → 'cl.42'"""
        hierarchy = ["Clause 42"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "cl.42"

    def test_clause_abbreviated(self):
        """Test: 'cl. 12' → 'cl.12'"""
        hierarchy = ["cl. 12 Definitions"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "cl.12"

    def test_regulation_reference(self):
        """Test: 'Regulation 12' → 'reg.12'"""
        hierarchy = ["Regulation 12"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "reg.12"

    def test_regulation_abbreviated(self):
        """Test: 'reg. 5' → 'reg.5'"""
        hierarchy = ["reg. 5 Compliance"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "reg.5"

    def test_subsection_with_brackets(self):
        """Test: '5(2)(a)' → 's.5(2)(a)'"""
        hierarchy = ["Section 5", "5(2)(a)"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.5(2)(a)"

    def test_subsection_single_bracket(self):
        """Test: 'Section 5(2)' → 's.5(2)'"""
        hierarchy = ["Section 5(2)"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.5(2)"

    def test_schedule_reference(self):
        """Test: 'Schedule 2' → 'sch.2'"""
        hierarchy = ["Schedule 2"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "sch.2"

    def test_schedule_letter(self):
        """Test: 'Schedule A' → 'sch.A'"""
        hierarchy = ["Schedule A Definitions"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "sch.A"

    def test_annex_reference(self):
        """Test: 'Annex B' → 'ann.B'"""
        hierarchy = ["Annex B Technical Specifications"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "ann.B"

    def test_part_reference_number(self):
        """Test: 'Part 3' → 'part.3'"""
        hierarchy = ["Part 3 Compliance"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "part.3"

    def test_part_reference_roman(self):
        """Test: 'Part III' → 'part.III'"""
        hierarchy = ["Part III Administrative Provisions"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "part.III"

    def test_no_recognizable_pattern(self):
        """Test: No pattern → None"""
        hierarchy = ["Introduction", "General Background"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result is None

    def test_empty_hierarchy(self):
        """Test: Empty hierarchy → None"""
        hierarchy: list[str] = []
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result is None

    def test_complex_hierarchy(self):
        """Test: Complex nested hierarchy extracts last section"""
        hierarchy = [
            "Part 3 Scope 2 Emissions",
            "Division 1 Market-Based Methods",
            "Section 3.2.1 Calculation",
        ]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.3.2.1"

    def test_case_insensitivity(self):
        """Test: Case-insensitive matching"""
        test_cases: list[tuple[list[str], str]] = [
            (["SECTION 5.2"], "s.5.2"),
            (["Clause 42"], "cl.42"),
            (["CLAUSE 42"], "cl.42"),
            (["Regulation 12"], "reg.12"),
            (["REGULATION 12"], "reg.12"),
        ]
        for hierarchy, expected in test_cases:
            result = self.parser._extract_clause_reference("", hierarchy)
            assert result == expected, f"Failed for {hierarchy}"


# Real-world test cases from Australian legislation
class TestRealWorldPatterns:
    """Test against real Australian legal document patterns."""

    def setup_method(self):
        """Initialize parser for testing."""
        self.parser = UnstructuredPDFParser()

    def test_nger_act_pattern(self):
        """Test: NGER Act section pattern"""
        hierarchy = [
            "Part 2 Registration and reporting obligations",
            "Division 2 Obligations",
            "Section 22A",
        ]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.22A"

    def test_cer_guideline_pattern(self):
        """Test: Clean Energy Regulator guideline pattern"""
        hierarchy = [
            "Part 3: Scope 2 Emissions Accounting",
            "Section 3.2: Calculation Methods",
            "3.2.1 Market-Based Accounting",
        ]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "s.3.2.1"

    def test_state_epa_regulation_pattern(self):
        """Test: State EPA regulation pattern"""
        hierarchy = ["Regulation 12 Reporting Requirements"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "reg.12"

    def test_planning_policy_schedule(self):
        """Test: Planning policy schedule pattern"""
        hierarchy = ["Schedule 1 Definitions and Abbreviations"]
        result = self.parser._extract_clause_reference("", hierarchy)
        assert result == "sch.1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
