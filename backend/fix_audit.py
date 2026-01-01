path = 'shared/services/audit.py'
with open(path, 'r') as f:
    content = f.read()

target = '        conditions = [\n        conditions = ['
replacement = '        conditions = ['

new_content = content.replace(target, replacement)

if new_content == content:
    print("No changes made.")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'conditions = [' in line and i < len(lines)-1:
            if 'conditions = [' in lines[i+1]:
                print(f"Found duplicate at line {i+1}:")
                print(repr(line))
                print(repr(lines[i+1]))
else:
    with open(path, 'w') as f:
        f.write(new_content)
    print("Fixed file.")
