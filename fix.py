import re

# Read the file
with open('static/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Function to fix mojibake
def fix_mojibake(text):
    try:
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text

# Find alert lines with mojibake
alert_pattern = re.compile(r"alert\('([^']*Ã[^']*)'\);")

def replace_alert(match):
    corrupted = match.group(1)
    fixed = fix_mojibake(corrupted)
    return f"alert('{fixed}');"

# Replace
new_content = alert_pattern.sub(replace_alert, content)

print(f"Replaced {alert_pattern.subn(replace_alert, content)[1]} alerts")

# Write back
with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Fixed alerts')