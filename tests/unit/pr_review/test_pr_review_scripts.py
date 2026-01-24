"""Tests for AI PR review scripts"""
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "pr_review"))


def test_gemini_auto_editor_imports():
    """Test that gemini_auto_editor can be imported"""
    try:
        import gemini_auto_editor
        assert hasattr(gemini_auto_editor, 'GeminiAutoEditor')
        assert hasattr(gemini_auto_editor, 'PROTECTED_FILES')
    except ImportError as e:
        assert False, f"Failed to import gemini_auto_editor: {e}"


def test_perplexity_reviewer_imports():
    """Test that perplexity_reviewer can be imported"""
    try:
        import perplexity_reviewer
        assert hasattr(perplexity_reviewer, 'PerplexityAuditor')
        assert hasattr(perplexity_reviewer, 'PROTECTED_FILES')
    except ImportError as e:
        assert False, f"Failed to import perplexity_reviewer: {e}"


def test_protected_files_defined():
    """Test that protected files are properly defined"""
    import gemini_auto_editor
    import perplexity_reviewer
    
    assert len(gemini_auto_editor.PROTECTED_FILES) > 0
    assert len(perplexity_reviewer.PROTECTED_FILES) > 0
    
    # Check critical files are protected
    assert "docker-compose.yml" in gemini_auto_editor.PROTECTED_FILES
    assert "docker-compose.yml" in perplexity_reviewer.PROTECTED_FILES


def test_gemini_editor_class_structure():
    """Test GeminiAutoEditor class has required methods"""
    import gemini_auto_editor
    
    editor = gemini_auto_editor.GeminiAutoEditor()
    assert hasattr(editor, 'get_pr_diff')
    assert hasattr(editor, 'get_changed_files')
    assert hasattr(editor, 'call_gemini_api')
    assert hasattr(editor, 'apply_improvements')
    assert hasattr(editor, 'is_protected_file')
    assert hasattr(editor, 'run')


def test_perplexity_auditor_class_structure():
    """Test PerplexityAuditor class has required methods"""
    import perplexity_reviewer
    
    auditor = perplexity_reviewer.PerplexityAuditor()
    assert hasattr(auditor, 'get_pr_diff')
    assert hasattr(auditor, 'get_file_content')
    assert hasattr(auditor, 'audit_with_perplexity')
    assert hasattr(auditor, 'apply_auto_fixes')
    assert hasattr(auditor, 'generate_audit_report')
    assert hasattr(auditor, 'run')
