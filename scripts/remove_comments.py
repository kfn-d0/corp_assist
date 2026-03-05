import os
import tokenize
import io
import sys

def remove_comments(source):
    try:
        io_obj = io.StringIO(source)
        tokens = list(tokenize.generate_tokens(io_obj.readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source

    lines = source.splitlines(keepends=True)
    
    # We want to identify the range of each comment token
    # and "delete" that text from the lines.
    
    # We'll work backwards through the tokens to avoid index shifting if we were modifying a single string,
    # but we are modifying a list of lines, so we can just track which parts to kill.
    
    # Map of line index -> list of (start_col, end_col) to remove
    to_remove = {}
    
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokens:
        if toktype == tokenize.COMMENT:
            for l in range(slineno, elineno + 1):
                s = scol if l == slineno else 0
                e = ecol if l == elineno else len(lines[l-1])
                if l not in to_remove:
                    to_remove[l] = []
                to_remove[l].append((s, e))
                
    if not to_remove:
        return source

    new_lines = []
    for i, line in enumerate(lines, 1):
        if i in to_remove:
            # Sort removals for this line descending by column
            removals = sorted(to_remove[i], key=lambda x: x[0], reverse=True)
            current_line = list(line)
            for s, e in removals:
                # Remove the segment. 
                # Be careful: if it's the end of the line, we might want to keep the newline.
                # tokenize.COMMENT usually includes the '#' but not the trailing newline.
                del current_line[s:e]
            
            processed_line = "".join(current_line)
            
            # If the line is now just whitespace (and maybe a newline), we might want to clean it up.
            if processed_line.strip() == "":
                if "\n" in processed_line:
                    new_lines.append("\n")
                else:
                    # Line was completely removed? (only if it didn't have a newline)
                    pass
            else:
                # Strip trailing whitespace that might have been before the comment
                if "\n" in processed_line:
                    new_lines.append(processed_line.rstrip() + "\n")
                else:
                    new_lines.append(processed_line.rstrip())
        else:
            new_lines.append(line)
            
    # Post-process: Remove excessive blank lines (max 2 consecutive)
    final_lines = []
    blank_count = 0
    for line in new_lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                final_lines.append(line)
        else:
            blank_count = 0
            final_lines.append(line)
            
    return "".join(final_lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python remove_comments.py <file_or_dir>")
        sys.exit(1)
        
    target = sys.argv[1]
    
    if os.path.isfile(target):
        files = [target]
    else:
        files = []
        for root, dirs, filenames in os.walk(target):
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
                    
    for fpath in files:
        print(f"Processing {fpath}...")
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = remove_comments(content)
        
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
    
    print("Done.")
