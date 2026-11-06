import os
import re
import urllib.request

SOURCES_FILE = "sources.txt"
OUTPUT_DIR = "Sumber Gratis"
SELECT_FILE = "chanel_pilihan.txt"
CUSTOM_PLAYLIST = "ZeroTVGRATIS.m3u"

GITHUB_TOKEN = os.environ.get("GH_PAT", "")

def fetch_url_content(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    target_url = url
    if "githubusercontent.com" in url and GITHUB_TOKEN:
        parts = url.replace("https://raw.githubusercontent.com/", "").split("/")
        if len(parts) >= 3:
            owner = parts[0]
            repo = parts[1]
            path = "/".join(parts[3:])
            target_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            headers['Accept'] = 'application/vnd.github.v3.raw'
            headers['Authorization'] = f"token {GITHUB_TOKEN}"
    elif "github.com" in url and GITHUB_TOKEN and "api.github.com" not in url:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8')

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def parse_and_split_m3u():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    if not os.path.exists(SOURCES_FILE):
        print(f"File {SOURCES_FILE} tidak ditemukan!")
        return

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        source_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not source_urls:
        print("Tidak ada link sumber yang ditemukan di sources.txt")
        return

    channels = {}
    all_blocks = []

    for url_idx, source_url in enumerate(source_urls, 1):
        print(f"Mengambil data dari URL ke-{url_idx}: {source_url}")
        try:
            content = fetch_url_content(source_url)
        except Exception as e:
            print(f"GAGAL mengambil data dari URL {source_url}: {e}")
            continue

        lines = content.splitlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:"):
                extinf_line = line
                
                # Cek nama kategori (group-title) jika ada di baris EXTINF
                group_match = re.search(r'group-title="([^"]+)"', extinf_line, re.IGNORECASE)
                group_name = group_match.group(1) if group_match else ""

                match = re.search(r',([^,]+)$', extinf_line)
                raw_name = match.group(1).strip() if match else "Unknown"
                clean_name = re.sub(r'\.\d+[A-Z]+$', '', raw_name)
                safe_name = re.sub(r'[\\/*?:"<>|]', "", clean_name).strip().replace(" ", "_")
                if not safe_name:
                    safe_name = "Unknown"

                block_lines = [extinf_line]
                i += 1
                
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith("#EXTINF:") or next_line.startswith("#EXTM3U"):
                        i -= 1
                        break
                    if next_line:
                        block_lines.append(next_line)
                    i += 1

                # Simpan untuk file terpisah per channel
                if safe_name not in channels:
                    channels[safe_name] = []
                channels[safe_name].append(block_lines)

                # Simpan ke daftar keseluruhan beserta info nama & kategorinya untuk disaring
                all_blocks.append({
                    "name": safe_name,
                    "group": group_name,
                    "lines": block_lines
                })
            i += 1

    # 1. Simpan file M3U terpisah per channel di folder Sumber Gratis
    for channel_name, entries in channels.items():
        file_path = os.path.join(OUTPUT_DIR, f"{channel_name}.m3u")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for block in entries:
                for bline in block:
                    f.write(f"{bline}\n")

    # 2. Baca daftar pengecualian (blacklist) dari chanel_pilihan.txt
    excluded_keywords = []
    if os.path.exists(SELECT_FILE):
        with open(SELECT_FILE, "r", encoding="utf-8") as f:
            excluded_keywords = [normalize_name(line.strip()) for line in f if line.strip() and not line.startswith("#")]

    # 3. Buat playlist utama ZeroTVGRATIS.m3u (Otomatis masuk SEMUA kecuali yang ada di blacklist)
    with open(CUSTOM_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        added_count = 0
        skipped_count = 0

        for item in all_blocks:
            c_name_norm = normalize_name(item["name"])
            c_group_norm = normalize_name(item["group"])
            
            # Cek apakah nama channel atau kategori mengandung kata-kata yang dikecualikan
            is_excluded = False
            for keyword in excluded_keywords:
                if keyword and (keyword in c_name_norm or keyword in c_group_norm):
                    is_excluded = True
                    break
            
            if is_excluded:
                skipped_count += 1
            else:
                for bline in item["lines"]:
                    f.write(f"{bline}\n")
                added_count += 1

        print(f"Berhasil memperbarui {CUSTOM_PLAYLIST}: {added_count} channel ditambahkan, {skipped_count} channel/kategori dikecualikan.")

if __name__ == "__main__":
    parse_and_split_m3u()
