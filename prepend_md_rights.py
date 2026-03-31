import os

DISCLOSURE = """
> [!NOTE]
> **Open Translation — Under Review**
>
> This is an AI-generated English translation of Abraham Kuyper's *Antirevolutionaire Staatkunde* (1916–1917). The translation is currently under review and has not been fully verified against the Dutch source text.
>
> This project is open to the public, open to critique, and open to improvement. The original Dutch work is in the public domain. This translation and all project materials are released under the MIT License — free to use, modify, and distribute for any purpose.
>
> **AI Disclosure:** This translation was produced using advanced AI systems and is currently under human review. Contributions, corrections, and improvements are welcome.
"""

MD_FILES = [
    "01_Editions/Kuyper_Antirevolutionary_Politics_Vol1_FULL.md",
    "01_Editions/Kuyper_Antirevolutionary_Politics_Vol2_FULL.md",
]


def prepend_frontmatter():
    for fpath in MD_FILES:
        if not os.path.exists(fpath):
            print(f"Skipping {fpath} (not found)")
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if already present to avoid double stacking
        if (
            "Open Translation" in content
            or "Rights, Attribution, and Fair Use" in content
        ):
            print(f"Front matter already present in {fpath}")
            continue

        # Insert after YAML front matter if present, or at top
        if content.startswith("---"):
            # Find second ---
            parts = content.split("---", 2)
            if len(parts) >= 3:
                new_content = f"---{parts[1]}---\n\n{DISCLOSURE}\n\n{parts[2]}"
            else:
                new_content = DISCLOSURE + "\n\n" + content
        else:
            new_content = DISCLOSURE + "\n\n" + content

        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"✅ Prepended Front Matter to {fpath}")


if __name__ == "__main__":
    prepend_frontmatter()
