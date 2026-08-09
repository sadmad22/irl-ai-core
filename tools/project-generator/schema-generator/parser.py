from pathlib import Path

def load_model(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def parse_sections(content: str):

    sections = {}

    current = None

    buffer = []

    for line in content.splitlines():

        if line.startswith("## "):

            if current is not None:
                sections[current] = "\n".join(buffer).strip()

            current = line.replace("## ", "").strip()

            buffer = []

        else:

            if current is not None:
                buffer.append(line)

    if current is not None:
        sections[current] = "\n".join(buffer).strip()

    return sections

def parse_fields(section: str):

    fields = []

    lines = section.splitlines()

    for line in lines:

        line = line.strip()

        if not line.startswith("|"):
            continue

        if "---" in line:
            continue

        parts = [part.strip() for part in line.split("|")[1:-1]]

        if parts[0] == "Field":
            continue

        if len(parts) != 4:
            continue

        fields.append(
            {
                "field": parts[0],
                "type": parts[1],
                "required": parts[2],
                "description": parts[3]
            }
        )

    return fields

def parse_model(path: Path):

    content = load_model(path)
    sections = parse_sections(content)

    fields = []

    if "Fields" in sections:
        fields = parse_fields(
        sections["Fields"]
    )
        
    lines = content.splitlines()
    title = ""

    for line in lines:
        if line.startswith("# "):
           title = line.replace("# ", "").strip()
        break
        
    return {
    "name": path.stem,
    "title": title,
    "content": content,
    "sections": sections,
    "fields": fields
}

if __name__ == "__main__":

    model = parse_model(
        Path("shared/models/keyword.md")
    )

    print(model)