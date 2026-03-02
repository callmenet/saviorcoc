import sys, os, re, json, struct, zipfile, io, shutil, subprocess
from urllib.request import urlopen

sys.stdout.reconfigure(encoding="utf-8")

DEBLOAT_REG_URL = "https://raw.githubusercontent.com/bibicadotnet/coccoc-portable/main/debloat.reg"

ALL_RESOURCE_TYPES = [
    "main_frame", "sub_frame", "stylesheet", "script", "image", "font",
    "object", "xmlhttprequest", "ping", "csp_report", "media", "websocket", "other",
]

DOMAIN_PATTERN = re.compile(
    r'(?:https?://)?([a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9\-]+)*\.'
    r'(?:coccoc\.com|comedia\.vn|qccoccocmedia\.vn))',
    re.IGNORECASE,
)


def extract_crx(crx_path, out_dir):
    data = open(crx_path, "rb").read()
    if data[:4] == b"Cr24":
        header_len = struct.unpack_from("<I", data, 8)[0]
        zip_start  = 12 + header_len
    else:
        zip_start = 0
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    with zipfile.ZipFile(io.BytesIO(data[zip_start:])) as zf:
        zf.extractall(out_dir)
    print(f"Extracted {len(data[zip_start:])//1024} KB -> {out_dir}/")


def apply_jq_patch(file_path, jq_path):
    result = subprocess.run(
        ["jq", "-f", jq_path, file_path],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(f"jq failed:\n{result.stderr}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(result.stdout)
    print(f"  {os.path.basename(file_path)} patched OK")


def find_extension_domains(ext_dir):
    found = set()
    for root, _, files in os.walk(ext_dir):
        for f in files:
            if not f.endswith((".js", ".json")):
                continue
            try:
                text = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
                for m in DOMAIN_PATTERN.finditer(text):
                    found.add(m.group(1).lower())
            except Exception:
                pass
    return sorted(found)


def fetch_debloat_block_domains():
    text     = urlopen(DEBLOAT_REG_URL).read().decode("utf-8-sig")
    domains  = []
    in_block = False
    for line in text.splitlines():
        line = line.strip()
        if re.search(r'\[.+URLBlocklist\]', line, re.IGNORECASE):
            in_block = True
            continue
        if line.startswith("["):
            in_block = False
            continue
        if in_block:
            m = re.match(r'"\d+"="(.+)"', line)
            if m:
                domains.append(m.group(1).lstrip("."))
    return sorted(set(domains))


def merge_rules(rules_path, discovered, debloat_block):
    rules = json.load(open(rules_path, encoding="utf-8"))
    existing_filters = {r["condition"].get("urlFilter", "") for r in rules}
    next_id = max((r["id"] for r in rules), default=199) + 1

    for domain in sorted(set(discovered) | set(debloat_block)):
        f = domain if domain.startswith("||") else f"||{domain}"
        if f in existing_filters:
            continue
        rules.append({
            "id":        next_id,
            "priority":  1,
            "action":    {"type": "block"},
            "condition": {"urlFilter": f, "resourceTypes": ALL_RESOURCE_TYPES},
        })
        existing_filters.add(f)
        next_id += 1

    with open(rules_path, "w", encoding="utf-8") as fp:
        json.dump(rules, fp, indent=2)
    print(f"  rules.json: {len(rules)} total rules")


def remove_files(ext_dir, list_path):
    if not os.path.exists(list_path):
        return
    for line in open(list_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        target = os.path.join(ext_dir, line)
        if os.path.exists(target):
            shutil.rmtree(target) if os.path.isdir(target) else os.remove(target)
            print(f"  Removed: {line}")


def repack(src_dir, out_zip):
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, src_dir))
    print(f"Packed -> {out_zip} ({os.path.getsize(out_zip)//1024} KB)")


def main():
    if len(sys.argv) < 3:
        print("Usage: patch.py <crx_path> <version>")
        sys.exit(1)

    crx_path = sys.argv[1]
    version  = sys.argv[2]
    work     = "work"
    out_zip  = f"savior-patched-{version}.zip"

    print("-- Extract")
    extract_crx(crx_path, work)

    print("-- Patch manifest.json")
    apply_jq_patch(os.path.join(work, "manifest.json"), "patched/manifest.patch.jq")

    print("-- Patch rules.json")
    apply_jq_patch(os.path.join(work, "rules.json"), "patched/rules.patch.jq")

    print("-- Discover domains from JS source")
    discovered = find_extension_domains(work)
    print(f"  Found {len(discovered)}: {discovered}")

    print("-- Fetch debloat.reg block domains")
    debloat = fetch_debloat_block_domains()
    print(f"  Found {len(debloat)}: {debloat}")

    print("-- Merge block domains into rules.json")
    merge_rules(os.path.join(work, "rules.json"), discovered, debloat)

    print("-- Remove debloat files")
    remove_files(work, "patched/remove_files.txt")

    print("-- Repack")
    repack(work, out_zip)
    shutil.rmtree(work)
    print(f"\nDone: {out_zip}")


if __name__ == "__main__":
    main()

