#!/usr/bin/env python3
"""
Code refactoring tool for automated code improvements.
"""

import re
import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple
import shutil

class CodeRefactorer:
    def __init__(self):
        self.backup_dir = None
    
    def create_backup(self, filepath: str) -> str:
        """Create a backup of the file."""
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        return backup_path
    
    def restore_backup(self, filepath: str, backup_path: str) -> None:
        """Restore file from backup."""
        shutil.copy2(backup_path, filepath)
        os.remove(backup_path)
    
    def rename_variable(self, filepath: str, old_name: str, new_name: str) -> bool:
        """Rename a variable throughout a file."""
        backup = self.create_backup(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex-based renaming (not perfect but works for many cases)
            # This is a basic implementation - for production use, consider using AST
            pattern = r'\b' + re.escape(old_name) + r'\b'
            new_content = re.sub(pattern, new_name, content)
            
            # Check if any changes were made
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                os.remove(backup)
                return True
            else:
                os.remove(backup)
                return False
                
        except Exception as e:
            print(f"Error renaming variable: {e}")
            self.restore_backup(filepath, backup)
            return False
    
    def _language_from_path(self, filepath: str) -> str:
        """Infer language from file extension. Returns 'java', 'python', or 'javascript'."""
        ext = Path(filepath).suffix.lower()
        if ext == '.java':
            return 'java'
        if ext in ('.js', '.jsx', '.ts', '.tsx', '.vue'):
            return 'javascript'
        return 'python'
    
    def extract_method(self, filepath: str, start_line: int, end_line: int, method_name: str) -> bool:
        """Extract selected lines into a new method. Language inferred from file extension."""
        backup = self.create_backup(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                print("Invalid line range")
                return False
            extracted = lines[start_line - 1:end_line]
            base_indent = len(extracted[0]) - len(extracted[0].lstrip())
            min_indent = min((len(line) - len(line.lstrip()) for line in extracted if line.strip()), default=base_indent)
            indent_str = " " * base_indent
            inner_indent = " " * (base_indent + 4)
            body_lines = [inner_indent + line[min_indent:].rstrip() + "\n" for line in extracted]
            lang = self._language_from_path(filepath)
            new_lines = lines[: start_line - 1]
            if lang == 'java':
                new_lines.append(indent_str + f"private void {method_name}() {{\n")
                new_lines.extend(body_lines)
                new_lines.append(indent_str + "}\n\n")
                new_lines.append(indent_str + f"{method_name}();\n")
            elif lang == 'javascript':
                new_lines.append(indent_str + f"function {method_name}() {{\n")
                new_lines.extend(body_lines)
                new_lines.append(indent_str + "}\n\n")
                new_lines.append(indent_str + f"{method_name}();\n")
            else:
                new_lines.append(indent_str + f"def {method_name}():\n")
                new_lines.extend(body_lines)
                new_lines.append("\n")
                new_lines.append(indent_str + f"{method_name}()\n")
            new_lines.extend(lines[end_line:])
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            os.remove(backup)
            return True
        except Exception as e:
            print(f"Error extracting method: {e}")
            self.restore_backup(filepath, backup)
            return False
    
    def remove_dead_code(self, filepath: str) -> Tuple[int, List[str]]:
        """Remove dead/unused code (simplified implementation)."""
        backup = self.create_backup(filepath)
        removed_count = 0
        removed_items = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check for common dead code patterns
                s = line.strip()
                if s.startswith('# TODO:') or s.startswith('# FIXME:') or s.startswith('// TODO:') or s.startswith('// FIXME:'):
                    new_lines.append(line)
                    i += 1
                elif line.strip() == 'pass' and i > 0 and lines[i-1].strip().startswith('def '):
                    # Empty function - might be intentional, so keep
                    new_lines.append(line)
                    i += 1
                elif re.match(r'^\s*print\(.*\)\s*$', line.strip()):
                    # Debug print statements - remove them
                    removed_count += 1
                    removed_items.append(f"Line {i+1}: Debug print - {line.strip()}")
                    i += 1
                elif re.match(r'^\s*console\.log\(.*\)\s*$', line.strip()):
                    removed_count += 1
                    removed_items.append(f"Line {i+1}: Console log - {line.strip()}")
                    i += 1
                elif re.search(r'^\s*System\.out\.println\s*\(', line):
                    removed_count += 1
                    removed_items.append(f"Line {i+1}: System.out.println - {line.strip()}")
                    i += 1
                else:
                    new_lines.append(line)
                    i += 1
            
            # Write cleaned file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            os.remove(backup)
            return removed_count, removed_items
            
        except Exception as e:
            print(f"Error removing dead code: {e}")
            self.restore_backup(filepath, backup)
            return 0, []

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python code_refactor.py <command> <file> [args...]")
        print("Commands: rename, extract-method, remove-dead-code")
        sys.exit(1)
    
    command = sys.argv[1]
    filepath = sys.argv[2]
    refactorer = CodeRefactorer()
    
    if command == 'rename':
        if len(sys.argv) != 5:
            print("Usage: python code_refactor.py rename <file> <old_name> <new_name>")
            sys.exit(1)
        old_name = sys.argv[3]
        new_name = sys.argv[4]
        success = refactorer.rename_variable(filepath, old_name, new_name)
        print(f"Renaming {'successful' if success else 'failed'}")
    
    elif command == 'extract-method':
        if len(sys.argv) != 6:
            print("Usage: python code_refactor.py extract-method <file> <start_line> <end_line> <method_name>")
            sys.exit(1)
        start_line = int(sys.argv[3])
        end_line = int(sys.argv[4])
        method_name = sys.argv[5]
        success = refactorer.extract_method(filepath, start_line, end_line, method_name)
        print(f"Method extraction {'successful' if success else 'failed'}")
    
    elif command == 'remove-dead-code':
        removed_count, removed_items = refactorer.remove_dead_code(filepath)
        print(f"Removed {removed_count} dead code items:")
        for item in removed_items:
            print(f"  - {item}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()