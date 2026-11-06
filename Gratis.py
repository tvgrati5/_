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
    normalized_channels = {}

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

                if safe_name not in channels:
                    channels[safe_name] = []
                channels[safe_name].append(block_lines)
                
                norm_key = normalize_name(safe_name)
                if norm_key not in normalized_channels:
                    normalized_channels[norm_key] = []
                normalized_channels[norm_key].append(block_lines)
            i += 1

    # 1. Simpan file M3U terpisah per channel di folder Sumber Gratis
    for channel_name, entries in channels.items():
        file_path = os.path.join(OUTPUT_DIR, f"{channel_name}.m3u")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for block in entries:
                for bline in block:
                    f.write(f"{bline}\n")

    # 2. Buat playlist gabungan berdasarkan chanel_pilihan.txt secara fleksibel
    if os.path.exists(SELECT_FILE):
        with open(SELECT_FILE, "r", encoding="utf-8") as f:
            selected_names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        if selected_names:
            with open(CUSTOM_PLAYLIST, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name in selected_names:
                    norm_target = normalize_name(name)
                    found = False
                    for n_key, blocks in normalized_channels.items():
                        if norm_target in n_key or n_key in norm_target:
                            for block in blocks:
                                for bline in block:
                                    f.write(f"{bline}\n")
                            print(f"Channel ditambahkan (fleksibel): {name}")
                            found = True
                            break
                    if not found:
                        print(f"Channel pilihan tidak ditemukan: {name}")
            print(f"Berhasil memperbarui playlist custom: {CUSTOM_PLAYLIST}")

if __name__ == "__main__":
    parse_and_split_m3u()
