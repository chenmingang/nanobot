#!/usr/bin/env python3
"""
Code analysis tool for understanding code structure, complexity, and quality.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

class CodeAnalyzer:
    def __init__(self):
        self.metrics = {}
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a single file and return metrics."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        
        analysis = {
            'filepath': filepath,
            'size_bytes': len(content),
            'lines': len(content.splitlines()),
            'language': self._detect_language(filepath),
            'complexity': self._calculate_complexity(content),
            'issues': self._find_issues(content),
            'imports': self._extract_imports(content, filepath),
            'functions': self._extract_functions(content),
            'classes': self._extract_classes(content),
        }
        
        return analysis
    
    def _detect_language(self, filepath: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(filepath).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'c++',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.less': 'less',
            '.vue': 'vue',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.json': 'json',
            '.md': 'markdown',
            '.txt': 'text',
        }
        return language_map.get(ext, 'unknown')
    
    def _is_comment_line(self, line: str) -> bool:
        """True if line is only comment (Python #, Java/JS //, or block)."""
        s = line.strip()
        if not s:
            return False
        if s.startswith('#') or s.startswith('//'):
            return True
        if s in ('/*', '*/') or (s.startswith('/*') and '*/' in s):
            return True
        return False
    
    def _calculate_complexity(self, content: str) -> Dict[str, int]:
        """Calculate code complexity metrics. Supports #, //, /* */ comments."""
        lines = content.splitlines()
        comment_lines = [l for l in lines if self._is_comment_line(l)]
        code_lines = [l for l in lines if l.strip() and not self._is_comment_line(l)]
        return {
            'total_lines': len(lines),
            'code_lines': len(code_lines),
            'comment_lines': len(comment_lines),
            'blank_lines': len([l for l in lines if not l.strip()]),
        }
    
    def _find_issues(self, content: str) -> List[str]:
        """Find potential issues. Python, Java, JS/TS aware."""
        issues = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if 'TODO' in line_stripped or 'FIXME' in line_stripped:
                issues.append(f"Line {i}: TODO/FIXME comment found")
            if len(line_stripped) > 120:
                issues.append(f"Line {i}: Line exceeds 120 characters")
            if 'print(' in line_stripped and 'debug' not in line_stripped.lower():
                issues.append(f"Line {i}: Potential debug print statement")
            if 'except:' in line_stripped:
                issues.append(f"Line {i}: Bare except clause (consider specifying exception type)")
            if 'System.out.println' in line_stripped:
                issues.append(f"Line {i}: Debug System.out.println (consider logger)")
            if re.search(r'\bcatch\s*\(\s*Exception\s+\w+\s*\)', line_stripped):
                issues.append(f"Line {i}: Catching Exception broadly (consider specific type)")
            if re.match(r'^\s*console\.log\s*\(', line_stripped):
                issues.append(f"Line {i}: console.log (consider removing or logger)")
        return issues
    
    def _extract_imports(self, content: str, filepath: str) -> List[str]:
        """Extract import/package/require statements."""
        imports = []
        for line in content.splitlines():
            s = line.strip()
            if s.startswith(('import ', 'from ', 'require(', 'include ', '#include ', 'package ')):
                imports.append(s)
        return imports
    
    def _extract_functions(self, content: str) -> List[Dict[str, str]]:
        """Extract function/method definitions. Java, Python, JS/TS focused."""
        functions = []
        lines = content.splitlines()
        patterns = [
            r'def\s+(\w+)\s*\(',
            r'function\s+(\w+)\s*\(',
            (r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]+>)?\s+)+\s*(\w+)\s*\(', 1),
            r'\b(\w+)\s*\([^)]*\)\s*\{',
            r'fn\s+(\w+)\s*\(',
            r'func\s+(\w+)\s*\(',
            r'(?:const|let)\s+(\w+)\s*=\s*\([^)]*\)\s*=>',
            r'(\w+)\s*\([^)]*\)\s*:\s*\w+\s*\{',
        ]
        for i, line in enumerate(lines, 1):
            for p in patterns:
                pattern = p[0] if isinstance(p, tuple) else p
                group = p[1] if isinstance(p, tuple) else 1
                m = re.search(pattern, line)
                if m:
                    functions.append({'name': m.group(group), 'line': i, 'signature': line.strip()})
                    break
        return functions
    
    def _extract_classes(self, content: str) -> List[Dict[str, str]]:
        """Extract class/interface/type definitions."""
        classes = []
        lines = content.splitlines()
        patterns = [
            r'class\s+(\w+)',
            r'interface\s+(\w+)',
            r'struct\s+(\w+)',
            r'type\s+(\w+)\s*=',
        ]
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    classes.append({'name': match.group(1), 'line': i, 'definition': line.strip()})
                    break
        return classes
    
    def analyze_project(self, project_path: str) -> Dict[str, Any]:
        """Analyze an entire project directory."""
        project_path = Path(project_path)
        results = {
            'project_path': str(project_path),
            'files': [],
            'summary': {
                'total_files': 0,
                'total_lines': 0,
                'total_issues': 0,
                'languages': {},
            }
        }
        
        # Common code file extensions
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.vue',
            '.html', '.css', '.scss', '.less', '.json', '.xml', '.yaml', '.yml',
            '.cpp', '.c', '.h', '.hpp', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
        }
        
        for filepath in project_path.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in code_extensions:
                try:
                    analysis = self.analyze_file(str(filepath))
                    results['files'].append(analysis)
                    
                    # Update summary
                    results['summary']['total_files'] += 1
                    results['summary']['total_lines'] += analysis['complexity']['total_lines']
                    results['summary']['total_issues'] += len(analysis['issues'])
                    
                    lang = analysis['language']
                    results['summary']['languages'][lang] = results['summary']['languages'].get(lang, 0) + 1
                except Exception as e:
                    print(f"Error analyzing {filepath}: {e}")
        
        return results

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python code_analyzer.py <file_or_directory>")
        sys.exit(1)
    
    analyzer = CodeAnalyzer()
    target = sys.argv[1]
    
    if Path(target).is_file():
        result = analyzer.analyze_file(target)
        print(json.dumps(result, indent=2))
    else:
        result = analyzer.analyze_project(target)
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()