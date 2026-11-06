import os
import re
import urllib.request

SOURCES_FILE = "sources.txt"
OUTPUT_DIR = "Sumber Gratis"
EXCLUDE_FILE = "chanel_pilihan.txt"  # Sekarang berfungsi sebagai daftar yang KECUALI / DIKECUALIKAN
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
            i += 1

    # 1. Simpan file M3U terpisah per channel di folder Sumber Gratis
    for channel_name, entries in channels.items():
        file_path = os.path.join(OUTPUT_DIR, f"{channel_name}.m3u")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for block in entries:
                for bline in block:
                    f.write(f"{bline}\n")

    # 2. Ambil daftar channel yang ingin DIKECUALIKAN (dibuang) dari chanel_pilihan.txt
    excluded_norms = set()
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, "r", encoding="utf-8") as f:
            excluded_names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            excluded_norms = {normalize_name(name) for name in excluded_names}

    # 3. Buat playlist gabungan: SEMUA channel dimasukkan, KECUALI yang ada di daftar pengecualian
    with open(CUSTOM_PLAYLIST, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        total_added = 0
        total_excluded = 0
        
        for safe_name, blocks in channels.items():
            norm_name = normalize_name(safe_name)
            
            # Cek apakah channel ini masuk daftar pengecualian
            is_excluded = any(exc in norm_name or norm_name in exc for exc in excluded_norms)
            
            if is_excluded:
                print(f"Channel dikecualikan (dibuang): {safe_name}")
                total_excluded += 1
            else:
                for block in blocks:
                    for bline in block:
                        f.write(f"{bline}\n")
                total_added += 1

        print(f"Berhasil memperbarui playlist custom: {CUSTOM_PLAYLIST} (Ditambahkan: {total_added}, Dikecualikan: {total_excluded})")

if __name__ == "__main__":
    parse_and_split_m3u()
