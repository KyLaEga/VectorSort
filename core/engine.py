import os
import sys
import io
import gc
import shutil
import subprocess
from core.hash_utils import hex_to_hash, phash
import uuid
import numpy as np
import faiss
import torch
import platform
import concurrent.futures
import imageio_ffmpeg
from PIL import Image
from pathlib import Path
from transformers import AutoProcessor, SiglipVisionModel, AutoFeatureExtractor, ASTModel

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# --- МАТРИЦА ДОПУСКОВ ---
SIM_V_ACCEPT = 0.84  
SIM_V_REVIEW = 0.72  
SIM_A_ACCEPT = 0.90  

MODEL_VIS = "google/siglip-base-patch16-224"
MODEL_AUD = "MIT/ast-finetuned-audioset-10-10-0.4593"

VALID_EXT = {'.mp4', '.mkv', '.mov', '.webm', '.ts', '.avi', '.m4v'}
MAX_IO_THREADS = 3  
CHUNK_SIZE = 50  

def _get_model_path(repo_id: str, local_name: str) -> str:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
    elif getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if sys.platform == "darwin":
            mac_resources = exe_dir.parent / "Resources"
            base = mac_resources if mac_resources.exists() else exe_dir
        else:
            base = exe_dir
    else:
        base = Path(__file__).resolve().parent.parent
    
    local_path = base / "assets" / "models" / local_name
    if local_path.exists():
        return str(local_path)
    return repo_id

class MultimodalEngine:
    def __init__(self, base_dir: str, log_callback=None, progress_callback=None, result_callback=None):
        self.base_dir = Path(base_dir)
        self.reference_dir = self.base_dir / "Reference_Matrix"
        self.trash_dir = self.base_dir / "Trash_Matrix"
        
        self.idx_v_good_path = self.base_dir / "matrix_v11_vis_good.faiss"
        self.idx_v_bad_path = self.base_dir / "matrix_v11_vis_bad.faiss"
        self.idx_a_good_path = self.base_dir / "matrix_v11_aud_good.faiss"
        self.idx_a_bad_path = self.base_dir / "matrix_v11_aud_bad.faiss"
        
        self.log_path = self.base_dir / "indexed_files_log.txt"
        self.hash_db_path = self.base_dir / "visual_hashes.npy"
        
        self.log_cb = log_callback if log_callback else print
        self.prog_cb = progress_callback if progress_callback else lambda p, m: None
        self.result_cb = result_callback if result_callback else lambda f, s, r: None
        
        self._verify_dirs()
        self.device = self._detect_device()
        self.log_cb(f"Инициализация ядра (Vision+Audio, O(1) Hash). Устройство: {self.device.upper()}")
        
        import warnings; warnings.filterwarnings("ignore")
        
        vis_path = _get_model_path(MODEL_VIS, "siglip-base-patch16-224")
        self.log_cb("Загрузка визуальной модели SigLIP...")
        self.v_proc = AutoProcessor.from_pretrained(vis_path)
        self.v_model = SiglipVisionModel.from_pretrained(vis_path).to(self.device)
        self.v_dim = self.v_model.config.hidden_size
        
        aud_path = _get_model_path(MODEL_AUD, "ast-finetuned-audioset")
        self.log_cb("Загрузка аудио модели AST...")
        self.a_proc = AutoFeatureExtractor.from_pretrained(aud_path)
        self.a_model = ASTModel.from_pretrained(aud_path).to(self.device)
        self.a_dim = self.a_model.config.hidden_size
        
        self.log_cb("Загрузка матриц FAISS...")
        self.idx_v_good = self._load_idx(self.idx_v_good_path, self.v_dim)
        self.idx_v_bad = self._load_idx(self.idx_v_bad_path, self.v_dim)
        self.idx_a_good = self._load_idx(self.idx_a_good_path, self.a_dim)
        self.idx_a_bad = self._load_idx(self.idx_a_bad_path, self.a_dim)
        
        self.indexed_files = set()
        if self.log_path.exists():
            with self.log_path.open('r', encoding='utf-8', errors='replace') as f: 
                self.indexed_files = {l.strip() for l in f}
            
        self.hash_db = {}
        self.precomputed_hashes = [] 
        
        if self.hash_db_path.exists():
            try:
                self.hash_db = np.load(self.hash_db_path, allow_pickle=True).item()
                for h_list in self.hash_db.values():
                    if h_list and len(h_list) > 0:
                        self.precomputed_hashes.append(hex_to_hash(h_list[0]))
            except Exception as e:
                self.log_cb(f"Ошибка загрузки хэшей: {e}")

        self.log_cb("Ядро успешно инициализировано.")

    def _detect_device(self):
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _get_ffmpeg_hw_flags(self):
        sys_name = platform.system().lower()
        if sys_name == 'darwin':
            return ['-hwaccel', 'videotoolbox']
        elif sys_name == 'windows':
            return []
        return []

    def _load_idx(self, path, dim):
        if path.exists():
            try:
                return faiss.read_index(str(path))
            except Exception as e:
                self.log_cb(f"Ошибка чтения индекса {path}: {e}. Создан новый пустой индекс.")
        return faiss.IndexFlatIP(dim)

    def _verify_dirs(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        for d in [self.reference_dir, self.trash_dir]: 
            d.mkdir(parents=True, exist_ok=True)

    def _safe_move(self, src: Path, dest_dir: Path, filename: str):
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename
        if dest_path.exists():
            unique_suffix = uuid.uuid4().hex[:6]
            dest_path = dest_dir / f"{dest_path.stem}_{unique_suffix}{dest_path.suffix}"
        shutil.move(str(src), str(dest_path))
        
    def _io_worker(self, video_path: Path):
        images, hashes, audio_waveform = [], [], None
        try:
            import re
            dur_cmd = [FFMPEG_EXE, '-i', str(video_path)]
            out = subprocess.run(dur_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out.stderr)
            if not match:
                return video_path, None, None, None, "NO_DURATION"
            
            h, m, s = match.groups()
            dur = float(h) * 3600 + float(m) * 60 + float(s)
            
            if dur < 2.0: 
                return video_path, None, None, None, "SHORT"

            # 1. Извлекаем аудио напрямую в ОЗУ через PIPE
            aud_ts = max(0, (dur / 2) - 1.0)
            cmd_aud = [
                FFMPEG_EXE, '-ss', str(aud_ts), '-i', str(video_path), 
                '-t', '2', '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', 
                '-ac', '1', '-f', 's16le', '-'
            ]
            proc_aud = subprocess.run(cmd_aud, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            if proc_aud.returncode == 0 and len(proc_aud.stdout) >= 32000:
                audio_waveform = np.frombuffer(proc_aud.stdout, dtype=np.int16).astype(np.float32) / 32768.0

            is_sync_phase = "Reference_Matrix" in str(video_path) or "Trash_Matrix" in str(video_path)
            if not is_sync_phase and audio_waveform is None:
                return video_path, None, None, None, "NO_AUDIO"

            # 2. Извлекаем кадры напрямую в ОЗУ в формате MJPEG
            timestamps = [dur * i for i in [0.2, 0.35, 0.5, 0.65, 0.8]]
            hw_flags = self._get_ffmpeg_hw_flags()
            
            for ts in timestamps:
                cmd_hw = [
                    FFMPEG_EXE, '-y'
                ] + hw_flags + [
                    '-ss', str(ts), '-i', str(video_path), 
                    '-vframes', '1', '-vf', 'scale=224:224', 
                    '-f', 'image2', '-vcodec', 'mjpeg', '-'
                ]
                proc_img = subprocess.run(cmd_hw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
                
                if proc_img.returncode != 0 or len(proc_img.stdout) < 512:
                    cmd_sw = [
                        FFMPEG_EXE, '-y', 
                        '-ss', str(ts), '-i', str(video_path), 
                        '-vframes', '1', '-vf', 'scale=224:224', 
                        '-f', 'image2', '-vcodec', 'mjpeg', '-'
                    ]
                    proc_img = subprocess.run(cmd_sw, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
                
                if proc_img.returncode == 0 and len(proc_img.stdout) >= 512:
                    try:
                        with Image.open(io.BytesIO(proc_img.stdout)) as img_raw:
                            img = img_raw.convert("RGB")
                            hashes.append(str(phash(img)))
                            images.append(img.copy())
                    except Exception:
                        pass

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
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    f = self.v_model(**inputs).pooler_output
                    v_feats = (f / f.norm(p=2, dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)
            except Exception as e: 
                self.log_cb(f"Vision Tensorize Error: {e}")
                
        if waveform is not None and len(waveform) > 8000:
            try:
                inputs = self.a_proc(waveform, sampling_rate=16000, return_tensors="pt")
                with torch.no_grad():
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    f = self.a_model(**inputs).pooler_output
                    a_feat = (f / f.norm(p=2, dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)
            except Exception as e: 
                self.log_cb(f"Audio Tensorize Error: {e}")
                
        return v_feats, a_feat

    def sync(self):
        targets = [
            (self.reference_dir, self.idx_v_good, self.idx_a_good, self.idx_v_good_path, self.idx_a_good_path, "GOOD"), 
            (self.trash_dir, self.idx_v_bad, self.idx_a_bad, self.idx_v_bad_path, self.idx_a_bad_path, "BAD")
        ]
        
        self.log_cb("Начат процесс синхронизации...")
        total_files = 0
        for d, _, _, _, _, _ in targets:
            total_files += len([f for f in os.listdir(d) if Path(f).suffix.lower() in VALID_EXT and f not in self.indexed_files and not f.startswith('.')])
            
        if total_files == 0:
            self.log_cb("Нет новых файлов для синхронизации матриц.")
            self.prog_cb(100, "Готово")
            return

        processed = 0
        for d, i_v, i_a, p_v, p_a, name in targets:
            files = [f for f in os.listdir(d) if Path(f).suffix.lower() in VALID_EXT and f not in self.indexed_files and not f.startswith('.')]
            if not files: continue
                
            self.log_cb(f"\nСинхронизация {name}: {len(files)} файлов")
            
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
                                    self.precomputed_hashes.append(hex_to_hash(hashes[0]))
                                    
                                self.indexed_files.add(filename)
                                with self.log_path.open('a', encoding='utf-8', errors='replace') as log: 
                                    log.write(filename + '\n')
                                self.log_cb(f" [+] Запись в матрицу: {filename} (Звук: {'ДА' if a_vec is not None else 'НЕТ'})")
                        else:
                            self.log_cb(f" [-] Ошибка синхронизации {filename}: {status}")
                        
                        # Освобождение ресурсов во избежание утечек памяти
                        del images, waveform
                        if 'v_vecs' in locals(): del v_vecs
                        if 'a_vec' in locals(): del a_vec
                        gc.collect()

                        processed += 1
                        self.prog_cb(int((processed / total_files) * 100), f"Синхронизация: {processed}/{total_files}")

            if i_v.ntotal > 0: faiss.write_index(i_v, str(p_v))
            if i_a.ntotal > 0: faiss.write_index(i_a, str(p_a))
            np.save(self.hash_db_path, self.hash_db)
            
        self.log_cb("Синхронизация успешно завершена.")

    def route(self, target_dir_path: str):
        target = Path(target_dir_path)
        if not target.exists() or not target.is_dir():
            self.log_cb("ОШИБКА: Целевая папка недоступна или не существует.")
            return
        
        self.log_cb(f"Целевая директория для проверки: {target}")
        
        dirs = ["Accepted", "Review", "Rejected", "Corrupted", "Duplicates", "No_Audio"]
        for d in dirs: (target / d).mkdir(exist_ok=True)
            
        files = [f for f in os.listdir(target) if Path(f).suffix.lower() in VALID_EXT and not f.startswith('.')]
        if not files: 
            self.log_cb("Медиафайлы для сканирования не найдены.")
            self.prog_cb(100, "Готово")
            return
            
        self.log_cb(f"\nАнализ {len(files)} файлов (Multimodal Scan)...")
        
        processed = 0
        for i in range(0, len(files), CHUNK_SIZE):
            chunk = files[i:i + CHUNK_SIZE]
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_IO_THREADS) as executor:
                futures = [executor.submit(self._io_worker, target / f) for f in chunk]
                
                for future in concurrent.futures.as_completed(futures):
                    v_path, images, hashes, waveform, status = future.result()
                    filename = v_path.name
                    
                    if status == "NO_AUDIO":
                        self.log_cb(f"[{filename}] -> NO AUDIO (Изолирован)")
                        self.result_cb(filename, "NO_AUDIO", "Нет аудиодорожки")
                        self._safe_move(v_path, target / "No_Audio", filename)
                        processed += 1
                        self.prog_cb(int((processed / len(files)) * 100), f"Анализ: {processed}/{len(files)}")
                        continue
                    
                    if status != "OK":
                        self.log_cb(f"[{filename}] -> CORRUPTED ({status})")
                        self.result_cb(filename, "CORRUPTED", status)
                        self._safe_move(v_path, target / "Corrupted", filename)
                        processed += 1
                        self.prog_cb(int((processed / len(files)) * 100), f"Анализ: {processed}/{len(files)}")
                        continue

                    is_duplicate = False
                    if hashes and len(hashes) > 0:
                        t_hash = hex_to_hash(hashes[0])
                        for p_hash in self.precomputed_hashes:
                            if t_hash - p_hash <= 2:
                                is_duplicate = True; break
                                
                    if is_duplicate:
                        self.log_cb(f"[{filename}] -> DUPLICATE")
                        self.result_cb(filename, "DUPLICATE", "Повтор в базе")
                        self._safe_move(v_path, target / "Duplicates", filename)
                        processed += 1
                        self.prog_cb(int((processed / len(files)) * 100), f"Анализ: {processed}/{len(files)}")
                        continue

                    v_vecs, a_vec = self._tensorize(images, waveform)
                    if len(v_vecs) == 0:
                        self.log_cb(f"[{filename}] -> ERROR (Сбой тензоризации)")
                        self.result_cb(filename, "ERROR", "Сбой тензоризации")
                        self._safe_move(v_path, target / "Corrupted", filename)
                        processed += 1
                        self.prog_cb(int((processed / len(files)) * 100), f"Анализ: {processed}/{len(files)}")
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
                        self.log_cb(f"[{filename}] -> REJECTED ({trigger} TRASH{aud_log})")
                        self.result_cb(filename, "REJECTED", f"{trigger} TRASH")
                        self._safe_move(v_path, target / "Rejected", filename)
                    elif max_g_v >= SIM_V_ACCEPT:
                        self.log_cb(f"[{filename}] -> ACCEPTED (V:{max_g_v:.2f}{aud_log})")
                        self.result_cb(filename, "ACCEPTED", f"Match: {max_g_v:.2f}")
                        self._safe_move(v_path, target / "Accepted", filename)
                    elif max_g_v >= SIM_V_REVIEW:
                        self.log_cb(f"[{filename}] -> REVIEW (V:{max_g_v:.2f}{aud_log})")
                        self.result_cb(filename, "REVIEW", f"Match: {max_g_v:.2f}")
                        self._safe_move(v_path, target / "Review", filename)
                    else:
                        self.log_cb(f"[{filename}] -> REJECTED (Low Match{aud_log})")
                        self.result_cb(filename, "REJECTED", "Low Match")
                        self._safe_move(v_path, target / "Rejected", filename)

                    # Освобождение ресурсов во избежание утечек памяти
                    del images, waveform
                    if 'v_vecs' in locals(): del v_vecs
                    if 'a_vec' in locals(): del a_vec
                    gc.collect()

                    processed += 1
                    self.prog_cb(int((processed / len(files)) * 100), f"Анализ: {processed}/{len(files)}")

        self.log_cb("Сканирование успешно завершено.")
        self.prog_cb(100, "Готово")
