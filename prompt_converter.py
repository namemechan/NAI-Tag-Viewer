import re

def split_tokens(text):
    """
    Split original string by commas,
    return tokens and their start/end positions
    """
    tokens = []
    start = 0
    for i, ch in enumerate(text):
        if ch == ',':
            token = text[start:i]
            if token.strip():
                tokens.append((token, start, i-1))
            start = i + 1
    if start < len(text):
        token = text[start:]
        if token.strip():
            tokens.append((token, start, len(text)-1))
    return tokens

def find_word_bounds(token, token_offset):
    """
    Get word bounds inside a token, ignoring spaces and brackets
    Returns the actual start, end index (based on original string)
    """
    # Left to right search: skip spaces and { } [ ]
    left = 0
    while left < len(token) and token[left] in " \t{}[]":
        left += 1
    # Right to left search
    right = len(token) - 1
    while right >= 0 and token[right] in " \t{}[]":
        right -= 1
    if left > right:
        # If no word, use the entire token
        return token_offset, token_offset + len(token) - 1
    return token_offset + left, token_offset + right

def count_before(text, pos, target, stopper):
    """
    Count occurrences of target character to the left of pos,
    stopping at stopper character
    """
    count = 0
    i = pos - 1
    while i >= 0:
        if text[i] == stopper:
            break
        if text[i] == target:
            count += 1
        i -= 1
    return count

def count_after(text, pos, target, stopper):
    """
    Count occurrences of target character to the right of pos,
    stopping at stopper character
    """
    count = 0
    i = pos + 1
    while i < len(text):
        if text[i] == stopper:
            break
        if text[i] == target:
            count += 1
        i += 1
    return count

def _replace_closing_colons(text):
    """
    Replaces ' ::' with the appropriate number of closing brackets based on
    the preceding unclosed opening brackets of the same type.
    """
    processed_text = []
    open_brackets_stack = [] # Stores the type of open bracket ('{' or '[')
    i = 0
    while i < len(text):
        if text[i:i+3] == ' ::':
            closing_brackets = ''
            if open_brackets_stack:
                last_open_type = open_brackets_stack[-1]
                # Pop all brackets of the same type from the stack
                while open_brackets_stack and open_brackets_stack[-1] == last_open_type:
                    open_brackets_stack.pop()
                    if last_open_type == '{':
                        closing_brackets += '}'
                    elif last_open_type == '[':
                        closing_brackets += ']'
            processed_text.append(closing_brackets)
            i += 3 # Skip ' ::'
        elif text[i] == '{':
            open_brackets_stack.append('{')
            processed_text.append(text[i])
            i += 1
        elif text[i] == '[':
            open_brackets_stack.append('[')
            processed_text.append(text[i])
            i += 1
        elif text[i] == '}': # Handle explicit closing curly brace
            if open_brackets_stack and open_brackets_stack[-1] == '{':
                open_brackets_stack.pop()
            processed_text.append(text[i])
            i += 1
        elif text[i] == ']': # Handle explicit closing square brace
            if open_brackets_stack and open_brackets_stack[-1] == '[':
                open_brackets_stack.pop()
            processed_text.append(text[i])
            i += 1
        else:
            processed_text.append(text[i])
            i += 1
    return "".join(processed_text)

def calculate_w_values(text):
    """
    Convert NAI prompt style to WebUI format with weights
    """
    # Replace underscores with spaces
    text = text.replace('_', ' ')

    # Handle new NAI weight syntax: weight::prompt ::
    # This pattern matches "NUMBER::TEXT ::"
    # Group 1: weight (e.g., 1.5)
    # Group 2: prompt content (e.g., apple)
    new_syntax_pattern = re.compile(r'(\d+\.?\d*)::(.*?)\s::')

    def replace_new_syntax(match):
        weight = float(match.group(1))
        content = match.group(2).strip()
        return f"({content}:{weight:.2f})"

    # Replace all occurrences of the new syntax first
    text = new_syntax_pattern.sub(replace_new_syntax, text)

    # Handle new NAI closing bracket syntax: ::
    text = _replace_closing_colons(text)
    
    tokens = split_tokens(text)
    results = []
    
    # Global bracket adjustment
    stripped = text.strip()
    global_curly_adj = 1 if (stripped.startswith('{') and stripped.endswith('}')) else 0
    global_square_adj = 1 if (stripped.startswith('[') and stripped.endswith(']')) else 0

    for token, t_start, t_end in tokens:
        word_start, word_end = find_word_bounds(token, t_start)
        # P-O: Count '{' to the left (stop at '}')
        p_o = count_before(text, word_start, '{', '}')
        # P-C: Count '}' to the right (stop at '{')
        p_c = count_after(text, word_end, '}', '{')
        p_w = max(p_o, p_c)
        if global_curly_adj:
            p_w = max(p_w - 1, 0)
        
        # N-O: Count '[' to the left (stop at ']')
        n_o = count_before(text, word_start, '[', ']')
        # N-C: Count ']' to the right (stop at '[')
        n_c = count_after(text, word_end, ']', '[')
        n_w = max(n_o, n_c)
        if global_square_adj:
            n_w = max(n_w - 1, 0)
        
        # Calculate weight
        lw = p_w - n_w
        w = 1.0
        if lw > 0:
            for _ in range(lw):
                w *= 1.05
        elif lw < 0:
            for _ in range(abs(lw)):
                w *= 0.95
        w = round(w + 1e-8, 2)
        
        # Clean token: remove brackets and trim
        cleaned = re.sub(r'[{}\[\]]', '', token).strip()
        if not cleaned:
            continue
        if abs(w - 1.0) < 1e-8:
            results.append(cleaned)
        else:
            results.append(f"({cleaned}:{w:.2f})")
            
    return ", ".join(results)