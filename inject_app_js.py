import os
import glob

base_dir = r"C:\Users\gokai\.gemini\antigravity-ide\scratch\casa da foto"
html_files = glob.glob(os.path.join(base_dir, "*.html"))

for file_path in html_files:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "app.js" not in content:
        if "</body>" in content:
            new_content = content.replace("</body>", "  <script src=\"app.js\"></script>\n</body>")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Added app.js to: {os.path.basename(file_path)}")
        else:
            print(f"No </body> in: {os.path.basename(file_path)}")
    else:
        print(f"app.js already present in: {os.path.basename(file_path)}")

print("Done updating HTML files with app.js!")
