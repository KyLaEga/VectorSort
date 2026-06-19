import os
import sys
import wave
import gc

# --- АППАРАТНЫЕ ПРЕДОХРАНИТЕЛИ APPLE SILICON ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
sys.stdout.reconfigure(line_buffering=True)

import shutil
import subprocess
import tempfile
import imagehash
import uuid
import numpy as np
import faiss
import torch
import concurrent.futures
from PIL import Image
from pathlib import Path
from transformers import AutoProcessor, SiglipVisionModel, AutoFeatureExtractor, ASTModel

# --- ТОПОЛОГИЯ ---
BASE_DIR = Path("/Volumes/KINGSTON/Файлы_телеграмм/NSFW_Arbitrage")
REFERENCE_DIR = BASE_DIR / "Reference_Matrix"
TRASH_DIR = BASE_DIR / "Trash_Matrix"

IDX_V_GOOD_PATH = BASE_DIR / "matrix_v11_vis_good.faiss"
IDX_V_BAD_PATH = BASE_DIR / "matrix_v11_vis_bad.faiss"
IDX_A_GOOD_PATH = BASE_DIR / "matrix_v11_aud_good.faiss"
IDX_A_BAD_PATH = BASE_DIR / "matrix_v11_aud_bad.faiss"

LOG_PATH = BASE_DIR / "indexed_files_log.txt"
HASH_DB_PATH = BASE_DIR / "visual_hashes.npy"

# --- МАТРИЦА ДОПУСКОВ ---
SIM_V_ACCEPT = 0.84  
SIM_V_REVIEW = 0.72  
SIM_A_ACCEPT = 0.90  

MODEL_VIS = "google/siglip-base-patch16-224"
MODEL_AUD = "MIT/ast-finetuned-audioset-10-10-0.4593"

VALID_EXT = {'.mp4', '.mkv', '.mov', '.webm', '.ts', '.avi', '.m4v'}
MAX_IO_THREADS = 3  
CHUNK_SIZE = 50  

class MultimodalEngine:
    def __init__(self):
        self._verify_mount()
        self.device = "cpu"
        print(f"Инициализация ядра v.11.6 (macOS Native GUI, Vision+Audio, O(1) Hash, GC)")
        import warnings; warnings.filterwarnings("ignore")
        
        self.v_proc = AutoProcessor.from_pretrained(MODEL_VIS)
        self.v_model = SiglipVisionModel.from_pretrained(MODEL_VIS).to(self.device)
        self.v_dim = self.v_model.config.hidden_size
        
        self.a_proc = AutoFeatureExtractor.from_pretrained(MODEL_AUD)
        self.a_model = ASTModel.from_pretrained(MODEL_AUD).to(self.device)
        self.a_dim = self.a_model.config.hidden_size
        
        self.idx_v_good = self._load_idx(IDX_V_GOOD_PATH, self.v_dim)
        self.idx_v_bad = self._load_idx(IDX_V_BAD_PATH, self.v_dim)
        self.idx_a_good = self._load_idx(IDX_A_GOOD_PATH, self.a_dim)
        self.idx_a_bad = self._load_idx(IDX_A_BAD_PATH, self.a_dim)
        
        self.indexed_files = set()
        if LOG_PATH.exists():
            with LOG_PATH.open('r', encoding='utf-8', errors='replace') as f: 
                self.indexed_files = {l.strip() for l in f}
            
        self.hash_db = {}
        self.precomputed_hashes = [] 
        
        if HASH_DB_PATH.exists():
            self.hash_db = np.load(HASH_DB_PATH, allow_pickle=True).item()
            for h_list in self.hash_db.values():
                if h_list and len(h_list) > 0:
                    self.precomputed_hashes.append(imagehash.hex_to_hash(h_list[0]))

    def _load_idx(self, path, dim):
        if path.exists(): 
            return faiss.read_index(str(path))
        return faiss.IndexFlatIP(dim)

    def _verify_mount(self):
        if not Path("/Volumes/KINGSTON").exists():
            print("CRITICAL: Диск KINGSTON не найден.")
            sys.exit(1)
        for d in [REFERENCE_DIR, TRASH_DIR]: 
            d.mkdir(parents=True, exist_ok=True)

    def _safe_move(self, src: Path, dest_dir: Path, filename: str):
        # ПАТЧ: Принудительное создание директории за миллисекунду до записи (обход потери связи с USB)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / filename
        if dest_path.exists():
            unique_suffix = uuid.uuid4().hex[:6]
            dest_path = dest_dir / f"{dest_path.stem}_{unique_suffix}{dest_path.suffix}"
        shutil.move(str(src), str(dest_path))
        
    def _io_worker(self, video_path: Path):
        images, hashes, audio_waveform = [], [], None
        try:
            dur_cmd = ['ffprobe', '-v', '0', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)]
            dur = float(subprocess.check_output(dur_cmd, timeout=10))
            
            if dur < 2.0: 
                return video_path, None, None, None, "SHORT"

            with tempfile.TemporaryDirectory() as tmp:
                aud_ts = max(0, (dur / 2) - 1.0)
                out_aud = os.path.join(tmp, "audio.wav")
                cmd_aud = ['ffmpeg', '-y', '-ss', str(aud_ts), '-i', str(video_path), '-t', '2', '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', out_aud]
                subprocess.run(cmd_aud, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                
                if os.path.exists(out_aud) and os.path.getsize(out_aud) > 1000:
                    with wave.open(out_aud, 'rb') as wf:
                        frames = wf.readframes(wf.getnframes())
                        audio_waveform = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

                is_sync_phase = "Reference_Matrix" in str(video_path) or "Trash_Matrix" in str(video_path)
                if not is_sync_phase and audio_waveform is None:
                    return video_path, None, None, None, "NO_AUDIO"

                timestamps = [dur * i for i in [0.2, 0.35, 0.5, 0.65, 0.8]]
                for i, ts in enumerate(timestamps):
                    out = os.path.join(tmp, f"v_{i}.jpg")
                    cmd_hw = ['ffmpeg', '-y', '-hwaccel', 'videotoolbox', '-ss', str(ts), '-i', str(video_path), '-vframes', '1', '-vf', 'scale=224:224', '-q:v', '2', out]
                    
                    if subprocess.run(cmd_hw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15).returncode != 0:
                        cmd_sw = ['ffmpeg', '-y', '-ss', str(ts), '-i', str(video_path), '-vframes', '1', '-vf', 'scale=224:224', out]
                        subprocess.run(cmd_sw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)

                    if os.path.exists(out) and os.path.getsize(out) > 512:
                        with Image.open(out).convert("RGB") as img:
                            hashes.append(str(imagehash.phash(img)))
                            images.append(img.copy())

            if not images: 
                return video_path, None, None, None, "DECODE_FAIL"
                
            return video_path, images, hashes, audio_waveform, "OK"
            
        except Exception as e:
            return video_path, None, None, None, f"ERROR: {str(e)}"

    def _tensorize(self, images, waveform):
        v_feats, a_feat = [], None
        if images:
            try:
                inputs = self.v_proc(images=images, return_tensors="pt")
                with torch.no_grad():
                    f = self.v_model(**inputs).pooler_output
                    v_feats = (f / f.norm(p=2, dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)
            except Exception: pass
                
        if waveform is not None and len(waveform) > 8000:
            try:
                inputs = self.a_proc(waveform, sampling_rate=16000, return_tensors="pt")
                with torch.no_grad():
                    f = self.a_model(**inputs).pooler_output
                    a_feat = (f / f.norm(p=2, dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)
            except Exception: pass
                
        return v_feats, a_feat

    def sync(self):
        targets = [
            (REFERENCE_DIR, self.idx_v_good, self.idx_a_good, IDX_V_GOOD_PATH, IDX_A_GOOD_PATH, "GOOD"), 
            (TRASH_DIR, self.idx_v_bad, self.idx_a_bad, IDX_V_BAD_PATH, IDX_A_BAD_PATH, "BAD")
        ]
        
        for d, i_v, i_a, p_v, p_a, name in targets:
            files = [f for f in os.listdir(d) if Path(f).suffix.lower() in VALID_EXT and f not in self.indexed_files and not f.startswith('.')]
            if not files: continue
                
            print(f"\nСинхронизация {name}: {len(files)} файлов")
            
            for i in range(0, len(files), CHUNK_SIZE):
                chunk = files[i:i + CHUNK_SIZE]
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IO_THREADS) as executor:
                    futures = [executor.submit(self._io_worker, d / f) for f in chunk]
                    
                    for future in concurrent.futures.as_completed(futures):
                        v_path, images, hashes, waveform, status = future.result()
                        filename = v_path.name
                        
                        if status == "OK" or (status == "NO_AUDIO" and images):
                            v_vecs, a_vec = self._tensorize(images, waveform)
                            if len(v_vecs) > 0:
                                for v in v_vecs: i_v.add(v.reshape(1, -1))
                                if a_vec is not None: i_a.add(a_vec.reshape(1, -1))
                                    
                                self.hash_db[filename] = hashes
                                if hashes and len(hashes) > 0:
                                    self.precomputed_hashes.append(imagehash.hex_to_hash(hashes[0]))
                                    
                                self.indexed_files.add(filename)
                                with LOG_PATH.open('a', encoding='utf-8', errors='replace') as log: 
                                    log.write(filename + '\n')
                                print(f" [+] Запись: {filename} (Звук: {'ДА' if a_vec is not None else 'НЕТ'})")
                        
                        del images, waveform; gc.collect()

            if i_v.ntotal > 0: faiss.write_index(i_v, str(p_v))
            if i_a.ntotal > 0: faiss.write_index(i_a, str(p_a))
            np.save(HASH_DB_PATH, self.hash_db)

    def route(self):
        print("\n" + "="*50)
        print("Ожидание выбора папки (откроется системное окно macOS)...")
        
        # ПАТЧ: Нативный вызов Finder через AppleScript
        script = '''
        tell application "System Events"
            activate
            set folderPath to choose folder with prompt "Выберите папку для проверки видео:"
            POSIX path of folderPath
        end tell
        '''
        try:
            raw_path = subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            if not raw_path:
                print("Отмена сканирования.")
                return
            target = Path(raw_path)
        except Exception:
            print("Сбой вызова окна Finder или отмена операции.")
            return
            
        print(f"Целевая директория: {target}")
        
        if not target.exists() or not target.is_dir():
            print("CRITICAL: Папка недоступна.")
            return
        
        dirs = ["Accepted", "Review", "Rejected", "Corrupted", "Duplicates", "No_Audio"]
        for d in dirs: (target / d).mkdir(exist_ok=True)
            
        files = [f for f in os.listdir(target) if Path(f).suffix.lower() in VALID_EXT and not f.startswith('.')]
        if not files: 
            print("Медиафайлы для сканирования не найдены.")
            return
            
        print(f"\nАнализ {len(files)} файлов (Multimodal Scan)...")
        
        for i in range(0, len(files), CHUNK_SIZE):
            chunk = files[i:i + CHUNK_SIZE]
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IO_THREADS) as executor:
                futures = [executor.submit(self._io_worker, target / f) for f in chunk]
                
                for future in concurrent.futures.as_completed(futures):
                    v_path, images, hashes, waveform, status = future.result()
                    filename = v_path.name
                    
                    if status == "NO_AUDIO":
                        print(f"[{filename}] -> NO AUDIO (Изолирован)")
                        self._safe_move(v_path, target / "No_Audio", filename)
                        del images, waveform; gc.collect()
                        continue
                    
                    if status != "OK":
                        print(f"[{filename}] -> CORRUPTED ({status})")
                        self._safe_move(v_path, target / "Corrupted", filename)
                        del images, waveform; gc.collect()
                        continue

                    is_duplicate = False
                    if hashes and len(hashes) > 0:
                        t_hash = imagehash.hex_to_hash(hashes[0])
                        for p_hash in self.precomputed_hashes:
                            if t_hash - p_hash <= 2:
                                is_duplicate = True; break
                                
                    if is_duplicate:
                        print(f"[{filename}] -> DUPLICATE")
                        self._safe_move(v_path, target / "Duplicates", filename)
                        del images, waveform; gc.collect()
                        continue

                    v_vecs, a_vec = self._tensorize(images, waveform)
                    if len(v_vecs) == 0:
                        print(f"[{filename}] -> ERROR (Сбой тензоризации)")
                        self._safe_move(v_path, target / "Corrupted", filename)
                        del images, waveform, v_vecs, a_vec; gc.collect()
                        continue

                    res_g_v, res_b_v = [], []
                    for v in v_vecs:
                        v_exp = v.reshape(1, -1)
                        k_g = min(5, self.idx_v_good.ntotal)
                        k_b = min(5, self.idx_v_bad.ntotal)
                        if k_g > 0: res_g_v.append(np.mean(self.idx_v_good.search(v_exp, k_g)[0]))
                        if k_b > 0: res_b_v.append(np.mean(self.idx_v_bad.search(v_exp, k_b)[0]))

                    max_g_v = np.max(res_g_v) if res_g_v else 0
                    max_b_v = np.max(res_b_v) if res_b_v else 0

                    max_g_a, max_b_a = 0, 0
                    if a_vec is not None:
                        a_exp = a_vec.reshape(1, -1)
                        k_ga = min(5, self.idx_a_good.ntotal)
                        k_ba = min(5, self.idx_a_bad.ntotal)
                        if k_ga > 0: max_g_a = np.mean(self.idx_a_good.search(a_exp, k_ga)[0])
                        if k_ba > 0: max_b_a = np.mean(self.idx_a_bad.search(a_exp, k_ba)[0])

                    is_visual_trash = max_b_v > max_g_v
                    is_audio_trash = max_b_a > max_g_a and max_b_a > SIM_A_ACCEPT
                    aud_log = f" | A_G:{max_g_a:.2f} A_B:{max_b_a:.2f}"

                    if is_visual_trash or is_audio_trash:
                        trigger = "AUDIO" if is_audio_trash and not is_visual_trash else "VISION"
                        print(f"[{filename}] -> REJECTED ({trigger} TRASH{aud_log})")
                        self._safe_move(v_path, target / "Rejected", filename)
                    elif max_g_v >= SIM_V_ACCEPT:
                        print(f"[{filename}] -> ACCEPTED (V:{max_g_v:.2f}{aud_log})")
                        self._safe_move(v_path, target / "Accepted", filename)
                    elif max_g_v >= SIM_V_REVIEW:
                        print(f"[{filename}] -> REVIEW (V:{max_g_v:.2f}{aud_log})")
                        self._safe_move(v_path, target / "Review", filename)
                    else:
                        print(f"[{filename}] -> REJECTED (Low Match{aud_log})")
                        self._safe_move(v_path, target / "Rejected", filename)

                    del images, waveform, v_vecs, a_vec; gc.collect()

if __name__ == "__main__":
    e = MultimodalEngine(); e.sync(); e.route()