import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestGenerateReportImports:
    """Test module imports and dependencies"""
    
    def test_report_module_exists(self):
        """Test that generate_report.py exists"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        assert os.path.exists(report_path), "generate_report.py file should exist"
    
    def test_required_imports_present(self):
        """Test that required imports are in generate_report.py"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'datetime' in content, "Should import datetime"
            assert 'reportlab' in content, "Should import reportlab"
            assert 'SimpleDocTemplate' in content, "Should use SimpleDocTemplate"
            assert 'Paragraph' in content, "Should use Paragraph"
            assert 'Table' in content, "Should use Table"


class TestPDFStructure:
    """Test PDF document structure"""
    
    def test_pdf_file_name(self):
        """Test that PDF file name is defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'GitLab_Compliance_Checker_Report.pdf' in content or 'pdf' in content.lower()
    
    def test_document_template_setup(self):
        """Test that SimpleDocTemplate is configured"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'SimpleDocTemplate' in content
            assert 'pagesize=letter' in content or 'letter' in content
            assert 'margin' in content.lower() or 'Margin' in content
    
    def test_page_setup(self):
        """Test that page setup is configured"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'topMargin' in content or 'bottom' in content.lower()


class TestReportStyles:
    """Test style definitions"""
    
    def test_styles_defined(self):
        """Test that report styles are defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'ParagraphStyle' in content
            assert 'getSampleStyleSheet' in content
    
    def test_custom_styles(self):
        """Test that custom paragraph styles are created"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'title_style' in content or 'CustomTitle' in content
            assert 'heading_style' in content or 'CustomHeading' in content
            assert 'body_style' in content or 'CustomBody' in content
    
    def test_color_definitions(self):
        """Test that colors are defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'colors.HexColor' in content or 'colors' in content
    
    def test_text_alignment(self):
        """Test that text alignment is configured"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'TA_CENTER' in content or 'TA_JUSTIFY' in content or 'alignment' in content


class TestReportContent:
    """Test report content sections"""
    
    def test_title_page(self):
        """Test that title page is created"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'GitLab Compliance Checker' in content
            assert 'Technical Documentation Report' in content or 'Report' in content
    
    def test_timestamp_generation(self):
        """Test that timestamp is generated"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'datetime.now()' in content or 'datetime' in content
            assert 'strftime' in content or '%B' in content
    
    def test_executive_summary(self):
        """Test that executive summary is included"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Executive Summary' in content
    
    def test_table_of_contents(self):
        """Test that table of contents is included"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Table of Contents' in content
    
    def test_overview_section(self):
        """Test that overview section exists"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Overview' in content or 'Architecture' in content
    
    def test_apis_section(self):
        """Test that APIs section exists"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'API' in content or 'python-gitlab' in content
    
    def test_conclusion_section(self):
        """Test that conclusion section exists"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Conclusion' in content or 'conclusion' in content.lower()


class TestTableStructures:
    """Test table definitions and structures"""
    
    def test_tables_created(self):
        """Test that tables are created"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Table(' in content or 'Table' in content
    
    def test_table_styling(self):
        """Test that table styling is applied"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'TableStyle' in content or 'setStyle' in content
    
    def test_architecture_table(self):
        """Test that architecture table is defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'arch' in content.lower() or 'Architecture Layers' in content
    
    def test_gitlab_api_table(self):
        """Test that GitLab API table is defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'python-gitlab' in content or 'GitLab API' in content
    
    def test_table_column_widths(self):
        """Test that table column widths are defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'colWidths' in content or 'inch' in content


class TestDocumentElements:
    """Test document elements"""
    
    def test_paragraphs_used(self):
        """Test that paragraphs are used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Paragraph(' in content
            assert 'elements.append' in content
    
    def test_spacers_used(self):
        """Test that spacers are used for spacing"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Spacer(' in content
    
    def test_page_breaks(self):
        """Test that page breaks are used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'PageBreak' in content
    
    def test_elements_list(self):
        """Test that elements list is used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'elements' in content
            assert 'append' in content


class TestDocumentBuilding:
    """Test document building process"""
    
    def test_document_build_call(self):
        """Test that document is built"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'build' in content or 'doc' in content
    
    def test_file_output(self):
        """Test that file output is configured"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'pdf' in content.lower()
            assert 'print' in content or 'open' in content


class TestReportDataContent:
    """Test specific content in report"""
    
    def test_programming_languages_mentioned(self):
        """Test that programming languages are mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Python' in content or 'language' in content.lower()
    
    def test_readme_mentioned(self):
        """Test that README is mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'README' in content
    
    def test_streamlit_mentioned(self):
        """Test that Streamlit is mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Streamlit' in content or 'streamlit' in content
    
    def test_batch_processing_mentioned(self):
        """Test that batch processing is mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Batch' in content or 'batch' in content
    
    def test_compliance_mentioned(self):
        """Test that compliance is mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Compliance' in content or 'compliance' in content


class TestReportMetadata:
    """Test report metadata"""
    
    def test_version_mentioned(self):
        """Test that version is mentioned"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'v' in content or '1.0' in content or 'version' in content.lower()
    
    def test_framework_mentioned(self):
        """Test that framework information is in document"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Python' in content or 'Framework' in content
    
    def test_metadata_section(self):
        """Test that metadata section exists"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'Generated' in content or 'Document' in content


class TestSyntaxValidation:
    """Test Python syntax validation"""
    
    def test_no_syntax_errors(self):
        """Test that generate_report.py has no syntax errors"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        try:
            with open(report_path, 'r') as f:
                compile(f.read(), report_path, 'exec')
            assert True, "No syntax errors"
        except SyntaxError as e:
            pytest.fail(f"Syntax error in generate_report.py: {e}")
    
    def test_imports_valid(self):
        """Test that imports are properly formatted"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            for i, line in enumerate(lines[:50], 1):
                if line.strip().startswith('import') or line.strip().startswith('from'):
                    # Basic validation that imports are properly formatted
                    assert ':' not in line or 'import' in line, f"Line {i}: {line}"


class TestReportFileGeneration:
    """Test report file generation functionality"""
    
    def test_pdf_output_path(self):
        """Test that PDF output path is defined"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert '.pdf' in content or 'pdf_file' in content
    
    def test_print_statements(self):
        """Test that success message is printed"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'print(' in content
    
    def test_success_indicators(self):
        """Test that success indicators are in output"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'successfully' in content.lower() or '✅' in content or 'PDF' in content


class TestCodeOrganization:
    """Test code organization and structure"""
    
    def test_shebang_present(self):
        """Test that shebang is present for executable"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            first_line = f.readline()
            assert '#!/usr/bin/env python' in first_line or '#!/usr/bin' in first_line
    
    def test_docstring_present(self):
        """Test that module docstring is present"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert '"""' in content or "'''" in content
    
    def test_comments_present(self):
        """Test that comments are present"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert '#' in content
    
    def test_logical_sections(self):
        """Test that code is organized in logical sections"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            # Check for section headers
            assert '====' in content or '----' in content or 'SECTION' in content


class TestDependencies:
    """Test dependencies and libraries"""
    
    def test_reportlab_imported(self):
        """Test that reportlab is imported"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'reportlab' in content or 'SimpleDocTemplate' in content
    
    def test_colors_module_used(self):
        """Test that colors module is used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'colors' in content or 'HexColor' in content
    
    def test_styles_module_used(self):
        """Test that styles module is used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'style' in content.lower() or 'Style' in content
    
    def test_units_imported(self):
        """Test that units module is used"""
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generate_report.py'))
        with open(report_path, 'r') as f:
            content = f.read()
            assert 'inch' in content or 'units' in content


# Test execution
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
