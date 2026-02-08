#!/usr/bin/env python3
"""
Code generation tool for creating boilerplate code, tests, and documentation.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class CodeGenerator:
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Load code templates."""
        return {
            'python_class': '''class {class_name}:
    """{docstring}"""
    
    def __init__(self{init_params}):
        """Initialize {class_name}."""
        {init_body}
    
    def __str__(self):
        """String representation."""
        return f"{class_name}()"
    
    def __repr__(self):
        """Representation for debugging."""
        return f"{class_name}()"
''',
            'python_function': '''def {function_name}({params}):
    """{docstring}
    
    Args:
        {param_docs}
    
    Returns:
        {return_doc}
    """
    {body}
''',
            'python_test': '''import unittest
import {module_name}

class Test{test_class}(unittest.TestCase):
    """Test cases for {module_name}.{test_target}."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Tear down test fixtures."""
        pass
    
    def test_{test_name}(self):
        """Test {test_target}."""
        {test_body}
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
''',
            'javascript_function': '''/**
 * {docstring}
 * @param {params_with_types}
 * @returns {return_type}
 */
function {function_name}({params}) {
    {body}
}
''',
            'typescript_interface': '''interface {interface_name} {{
    {properties}
}}
''',
            'html_template': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    {body}
    <script>
        {javascript}
    </script>
</body>
</html>
''',
            'java_class': '''package {package_name};

/**
 * {docstring}
 */
public class {class_name} {{

    public {class_name}() {{
        {init_body}
    }}

    @Override
    public String toString() {{
        return "{class_name}()";
    }}
}}
''',
            'java_test': '''package {package_name};

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Test{test_class} {{

    @Test
    void test_{test_name}() {{
        {test_body}
        assertTrue(true);
    }}
}}
''',
            'react_component': '''import React from 'react';

/**
 * {docstring}
 */
export function {component_name}({props}) {{
  return (
    <div className="{class_name}">
      {body}
    </div>
  );
}}

export default {component_name};
''',
        }
    
    def generate_python_class(self, class_name: str, docstring: str = "", 
                             attributes: List[str] = None) -> str:
        """Generate a Python class template."""
        if attributes is None:
            attributes = []
        
        init_params = ""
        init_body = ""
        if attributes:
            init_params = ", " + ", ".join(attributes)
            init_body = "\n        ".join([f"self.{attr} = {attr}" for attr in attributes])
        
        template = self.templates['python_class']
        return template.format(
            class_name=class_name,
            docstring=docstring or f"A {class_name} class.",
            init_params=init_params,
            init_body=init_body or "pass"
        )
    
    def generate_python_function(self, function_name: str, params: List[str] = None,
                                docstring: str = "", return_type: str = "Any") -> str:
        """Generate a Python function template."""
        if params is None:
            params = []
        
        param_str = ", ".join(params)
        param_docs = "\n        ".join([f"{param}: Description of {param}" for param in params])
        
        template = self.templates['python_function']
        return template.format(
            function_name=function_name,
            params=param_str,
            docstring=docstring or f"Perform {function_name}.",
            param_docs=param_docs or "None",
            return_doc=f"{return_type}: Return value",
            body="pass"
        )
    
    def generate_java_class(self, class_name: str, package_name: str = "com.example",
                           docstring: str = "") -> str:
        """Generate a Java class template."""
        return self.templates['java_class'].format(
            package_name=package_name,
            class_name=class_name,
            docstring=docstring or f"{class_name} entity or service.",
            init_body="// TODO: initialize"
        )
    
    def generate_java_test(self, class_under_test: str, package_name: str = "com.example",
                           test_name: str = "basic") -> str:
        """Generate a JUnit 5 test class template."""
        test_class = class_under_test.replace(".", "")
        return self.templates['java_test'].format(
            package_name=package_name,
            test_class=test_class,
            test_name=test_name,
            test_body="// TODO: arrange, act, assert"
        )
    
    def generate_react_component(self, component_name: str, docstring: str = "") -> str:
        """Generate a React function component template."""
        class_name = component_name.replace(" ", "-").lower()
        return self.templates['react_component'].format(
            component_name=component_name,
            docstring=docstring or f"{component_name} component.",
            props="props",
            class_name=class_name,
            body="{/* content */}"
        )
    
    def generate_ts_interface(self, interface_name: str, properties: List[str] = None) -> str:
        """Generate a TypeScript interface."""
        if properties is None:
            properties = []
        props = "\n    ".join([f"{p}: unknown;" for p in properties]) if properties else "// add properties"
        return self.templates['typescript_interface'].format(
            interface_name=interface_name,
            properties=props
        )
    
    def generate_unit_test(self, module_name: str, test_target: str,
                          test_cases: List[Dict] = None) -> str:
        """Generate unit tests for a module."""
        if test_cases is None:
            test_cases = [{'name': 'basic', 'body': '# Add test logic here'}]
        
        test_class = f"Test{test_target.title().replace('_', '')}"
        
        # Build test methods
        test_methods = []
        for i, test_case in enumerate(test_cases):
            test_name = test_case.get('name', f'test_case_{i+1}')
            test_body = test_case.get('body', 'pass')
            test_method = f'''
    def test_{test_name}(self):
        """Test {test_target} - {test_name}."""
        {test_body}'''
            test_methods.append(test_method)
        
        test_methods_str = '\n'.join(test_methods)
        
        template = '''import unittest
import {module_name}

class {test_class}(unittest.TestCase):
    """Test cases for {module_name}.{test_target}."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Tear down test fixtures."""
        pass
{test_methods}

if __name__ == '__main__':
    unittest.main()
'''
        
        return template.format(
            module_name=module_name,
            test_class=test_class,
            test_target=test_target,
            test_methods=test_methods_str
        )
    
    def generate_documentation(self, filepath: str) -> str:
        """Generate documentation for a code file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        
        filename = Path(filepath).name
        lines = content.splitlines()
        
        doc = f"""# Documentation for {filename}

## File Overview
- **Location**: {filepath}
- **Lines**: {len(lines)}
- **Size**: {len(content)} bytes

## Code Structure
"""
        
        # Extract imports / package
        imports = []
        for l in lines:
            s = l.strip()
            if s.startswith(('import ', 'from ', 'require(', 'include ', 'package ')):
                imports.append(s)
        if imports:
            doc += "\n### Imports / Package\n```\n" + '\n'.join(imports) + "\n```\n"
        
        # Extract functions and classes (Python, Java, JS/TS)
        functions = []
        classes = []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if re.match(r'^\s*def\s+\w+', line):
                functions.append((i, s))
            elif re.match(r'^\s*class\s+\w+', line) or re.match(r'^\s*interface\s+\w+', line) or re.match(r'^\s*type\s+\w+\s*=', line):
                classes.append((i, s))
            elif re.match(r'^\s*(?:public|private|protected)\s+', line) and re.search(r'\s+\w+\s*\([^)]*\)\s*\{', line):
                functions.append((i, s))
            elif re.match(r'^\s*function\s+\w+\s*\(', line) or re.match(r'^\s*(?:const|let)\s+\w+\s*=\s*\(', line):
                functions.append((i, s))
        
        if classes:
            doc += "\n### Classes\n"
            for line_num, class_def in classes:
                doc += f"- **Line {line_num}**: `{class_def}`\n"
        
        if functions:
            doc += "\n### Functions\n"
            for line_num, func_def in functions:
                doc += f"- **Line {line_num}**: `{func_def}`\n"
        
        # Add TODO/FIXME items
        todos = []
        for i, line in enumerate(lines, 1):
            if any(marker in line for marker in ['TODO:', 'FIXME:', 'XXX:', 'HACK:']):
                todos.append((i, line.strip()))
        
        if todos:
            doc += "\n### TODO Items\n"
            for line_num, todo in todos:
                doc += f"- **Line {line_num}**: {todo}\n"
        
        return doc
    
    def create_file_from_template(self, filepath: str, template_type: str, 
                                 **kwargs) -> bool:
        """Create a new file from a template."""
        if template_type not in self.templates:
            print(f"Unknown template type: {template_type}")
            return False
        
        template = self.templates[template_type]
        content = template.format(**kwargs)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error creating file: {e}")
            return False

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python code_generator.py <command> [args...]")
        print("Commands: class, function, test, docs, template, java-class, java-test, react-component, ts-interface")
        sys.exit(1)
    
    generator = CodeGenerator()
    command = sys.argv[1]
    
    if command == 'java-class':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py java-class <class_name> [package_name]")
            sys.exit(1)
        class_name = sys.argv[2]
        package = sys.argv[3] if len(sys.argv) > 3 else "com.example"
        print(generator.generate_java_class(class_name, package))
    elif command == 'java-test':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py java-test <class_under_test> [package_name]")
            sys.exit(1)
        cut = sys.argv[2]
        package = sys.argv[3] if len(sys.argv) > 3 else "com.example"
        print(generator.generate_java_test(cut, package))
    elif command == 'react-component':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py react-component <ComponentName>")
            sys.exit(1)
        print(generator.generate_react_component(sys.argv[2]))
    elif command == 'ts-interface':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py ts-interface <InterfaceName> [prop1 prop2 ...]")
            sys.exit(1)
        name = sys.argv[2]
        props = sys.argv[3:] if len(sys.argv) > 3 else []
        print(generator.generate_ts_interface(name, props))
    elif command == 'class':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py class <class_name> [docstring]")
            sys.exit(1)
        class_name = sys.argv[2]
        docstring = sys.argv[3] if len(sys.argv) > 3 else ""
        print(generator.generate_python_class(class_name, docstring))
    
    elif command == 'function':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py function <function_name> [params...]")
            sys.exit(1)
        function_name = sys.argv[2]
        params = sys.argv[3:] if len(sys.argv) > 3 else []
        print(generator.generate_python_function(function_name, params))
    
    elif command == 'test':
        if len(sys.argv) < 4:
            print("Usage: python code_generator.py test <module_name> <test_target>")
            sys.exit(1)
        module_name = sys.argv[2]
        test_target = sys.argv[3]
        print(generator.generate_unit_test(module_name, test_target))
    
    elif command == 'docs':
        if len(sys.argv) < 3:
            print("Usage: python code_generator.py docs <filepath>")
            sys.exit(1)
        filepath = sys.argv[2]
        print(generator.generate_documentation(filepath))
    
    elif command == 'template':
        if len(sys.argv) < 4:
            print("Usage: python code_generator.py template <template_type> <filepath> [kwargs...]")
            print("Available templates:", list(generator.templates.keys()))
            sys.exit(1)
        template_type = sys.argv[2]
        filepath = sys.argv[3]
        # Parse additional kwargs from command line (simplified)
        kwargs = {}
        for arg in sys.argv[4:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                kwargs[key] = value
        success = generator.create_file_from_template(filepath, template_type, **kwargs)
        print(f"File creation {'successful' if success else 'failed'}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()