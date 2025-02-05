import os
import sys
import re

def process(extracted_string):
    effects = []
    cleaned_lines = re.sub(r'^\s*\n', '', extracted_string, flags=re.MULTILINE)
    lines = cleaned_lines.splitlines()
    for i, line in enumerate(lines, start=0):
        if 'init=' in line:
            init = extract_init(line)
            effects.append(init)
        elif 'color=' in line:
            color = extract_color(line)
            effects.append(color)
            
    global eff
    eff = effects

def extract_init(line):
    eff = re.compile(r'init= "([^"]+)"')
    match = eff.search(line)
    if match:
        return match.group(1)
    return None

def extract_color(line):
    col = re.compile(r'color= "([^"]+)"')
    match = col.search(line)
    if match:
        color_values = match.group(1).split()
        return list(map(float, color_values))
    return None