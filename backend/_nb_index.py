import json, re

with open(r"C:\Users\imao3\.claude\projects\C--Users-imao3-Documents-GitHub-pharma-shift\f6259589-d232-47de-91fa-c2326c1d619d\tool-results\toolu_01Ev8DFWW4u4hnfLnH3dbZna.json", encoding="utf-8") as f:
    data = json.load(f)

text = data[0]["text"]
cells = re.split(r'<cell id="(cell-\d+)">', text)
for i in range(1, len(cells), 2):
    cell_id = cells[i]
    content = cells[i+1]
    # strip cell_type tag
    content = re.sub(r'</?cell_type>|</?cell id="cell-\d+">', '', content)
    lines = [l for l in content.strip().split('\n') if l.strip()]
    preview = lines[0][:120] if lines else "(empty)"
    print(f"{cell_id}: {preview}")
