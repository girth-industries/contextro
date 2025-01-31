import os
import fnmatch
import time
import argparse
from pathlib import Path
from datetime import datetime
import glob

class Contextro:
    def __init__(self, root_dir='.', ignore_file='.contextignore'):
        self.root_dir = Path(root_dir).resolve()
        self.ignore_file = self.root_dir / ignore_file
        self.ignore_patterns = self._load_ignore_patterns()
        self.ignore_patterns.append('contextro_context_*.txt')

    def _load_ignore_patterns(self):
        """Load and parse the .contextignore file, similar to .gitignore"""
        patterns = []
        if self.ignore_file.exists():
            with open(self.ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
        return patterns

    def _should_ignore(self, path):
        """
        Check if a path should be ignored based on .contextignore patterns.
        Implements gitignore-style pattern matching.
        """
        # Convert path to relative path from root_dir
        rel_path = str(Path(path).resolve().relative_to(self.root_dir))
        
        # Also create path with trailing slash for directory matching
        rel_path_with_slash = rel_path + '/' if os.path.isdir(path) else rel_path
        
        for pattern in self.ignore_patterns:
            # Handle pattern variations
            pattern_variations = [
                pattern,                    # Original pattern
                f"**/{pattern}",           # Match in any subdirectory
                f"**/{pattern}/**"         # Match all contents in any subdirectory
            ]
            
            # Handle negation patterns
            if pattern.startswith('!'):
                clean_pattern = pattern[1:]
                for var in pattern_variations:
                    if fnmatch.fnmatch(rel_path, clean_pattern):
                        return False
            else:
                for var in pattern_variations:
                    # Handle directory-specific patterns
                    if pattern.endswith('/'):
                        if fnmatch.fnmatch(rel_path_with_slash, var):
                            return True
                    # Handle regular patterns
                    elif fnmatch.fnmatch(rel_path, var):
                        return True
        return False

    def _is_binary(self, path):
        """Check if a file is binary by reading its first few bytes"""
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return True

    def _cleanup_old_context_files(self):
        """Delete any existing context_{timestamp}.txt files"""
        pattern = self.root_dir / 'contextro_context_*.txt'
        for file in glob.glob(str(pattern)):
            try:
                os.remove(file)
                print(f"Deleted old context file: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")

    def build_context(self):
        """
        Build the context file by concatenating all non-ignored files,
        separated by the specified delimiter.
        """
        # Clean up old context files first
        self._cleanup_old_context_files()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.root_dir / f'contextro_context_{timestamp}.txt'
        
        with open(output_file, 'w', encoding='utf-8') as out:
            for root, dirs, files in os.walk(self.root_dir):
                # Skip the output file itself and the .contextignore file
                files = [f for f in files if f != output_file and f != '.contextignore']
                
                # Remove ignored directories
                dirs[:] = [d for d in dirs if not self._should_ignore(os.path.join(root, d))]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._should_ignore(file_path):
                        try:
                            # Skip binary files
                            if self._is_binary(file_path):
                                continue
                                
                            # Get relative path for the separator
                            rel_path = os.path.relpath(file_path, self.root_dir)
                            
                            # Write the separator
                            out.write(f"\n{'=' * 7}{rel_path}{'=' * 7}\n")
                            
                            # Write the file contents
                            with open(file_path, 'r', encoding='utf-8') as f:
                                out.write(f.read())
                                
                        except Exception as e:
                            print(f"Error processing {file_path}: {e}")

        print(f"Context file created: {output_file}")
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Build a context file from directory contents, respecting .contextignore')
    parser.add_argument('directory', nargs='?', default='.', 
                      help='Directory to process (default: current directory)')
    parser.add_argument('--ignore-file', default='.contextignore',
                      help='Name of the ignore file (default: .contextignore)')
    
    args = parser.parse_args()
    
    try:
        builder = Contextro(args.directory, args.ignore_file)
        builder.build_context()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())