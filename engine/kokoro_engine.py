from __future__ import annotations

import pickle
import re
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SAMPLE_RATE = 24000
MAX_PHONEMES = 510
CHUNK_PHONEMES = 480
PAD_ID = 0
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_SECONDARY_PUNCT = re.compile(r"[,;:—–]\s")


class _Storage:
    def __init__(self, key: str, numel: int) -> None:
        self.key = key
        self.numel = numel


def _rebuild_tensor_v2(storage, offset, size, stride, *args):
    return {"storage": storage, "offset": offset, "size": tuple(size)}


class _VoicepackUnpickler(pickle.Unpickler):
    """Đọc tensor PyTorch (.pt) thuần bằng pickle/zip, không cần cài torch."""

    def find_class(self, module: str, name: str):
        if module.startswith("torch"):
            if name == "_rebuild_tensor_v2":
                return _rebuild_tensor_v2
            if "Storage" in name:
                return type(name, (), {})
            raise pickle.UnpicklingError(f"torch symbol not supported: {name}")
        return super().find_class(module, name)

    def persistent_load(self, pid):
        return _Storage(key=pid[2], numel=pid[4])


def load_voicepack(path: Path) -> np.ndarray:
    with zipfile.ZipFile(path) as zf:
        pkl_name = next(n for n in zf.namelist() if n.endswith("data.pkl"))
        prefix = pkl_name.rsplit("data.pkl", 1)[0]
        with zf.open(pkl_name) as handle:
            obj = _VoicepackUnpickler(handle).load()
        if isinstance(obj, (list, tuple)) and len(obj) == 1:
            obj = obj[0]
        storage, size = obj["storage"], obj["size"]
        raw = zf.read(f"{prefix}data/{storage.key}")
        flat = np.frombuffer(raw, dtype=np.float32, count=storage.numel)
        total = int(np.prod(size))
        return flat[obj["offset"]:obj["offset"] + total].reshape(size).copy()


class KokoroTTS:
    """Chạy Kokoro-Vietnamese ONNX với interface giống sherpa OfflineTTS.

    generate(text, speed) -> SimpleNamespace(samples, sample_rate)
    """

    def __init__(self, model_path: Path, config_path: Path,
                 voicepack_path: Path, num_threads: int = 2) -> None:
        import json

        import onnxruntime as ort

        model_path, config_path = Path(model_path), Path(config_path)
        voicepack_path = Path(voicepack_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self._vocab: dict[str, int] = config["vocab"]
        options = ort.SessionOptions()
        options.intra_op_num_threads = num_threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            str(model_path), sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self._voicepack = load_voicepack(voicepack_path)
        self.sample_rate = SAMPLE_RATE

    def generate(self, text: str, speed: float = 1.0, **kwargs) -> SimpleNamespace:
        from vig2p import phonemize_text

        pieces: list[np.ndarray] = []
        for chunk in self._split_for_phonemes(text):
            phonemes = phonemize_text(chunk)
            if not phonemes:
                continue
            ids = [self._vocab[ch] for ch in phonemes if ch in self._vocab]
            if not ids:
                continue
            input_ids = np.asarray([[PAD_ID, *ids, PAD_ID]], dtype=np.int64)
            style_index = min(len(phonemes), self._voicepack.shape[0]) - 1
            ref_s = self._voicepack[style_index]
            outputs = self._session.run(
                None,
                {
                    "input_ids": input_ids,
                    "ref_s": ref_s,
                    "speed": np.asarray(float(speed), dtype=np.float32),
                },
            )
            waveform = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
            pieces.append(waveform)

        samples = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        return SimpleNamespace(samples=samples, sample_rate=self.sample_rate)

    @staticmethod
    def _cut_point(sentence: str, start: int) -> int:
        """Vị trí cắt tiếp theo cho mảnh bắt đầu tại `start`.

        Ưu tiên cắt ngay sau dấu phụ (, ; : — –) để giữ trọn nghĩa cụm từ;
        chỉ dùng khoảng trắng làm dự phòng khi không có dấu câu nào phù hợp.
        """
        window_end = min(start + 240, len(sentence))
        for m in reversed(list(_SECONDARY_PUNCT.finditer(sentence, start, window_end))):
            if m.end() - start >= 40:
                return m.end()
        ws = sentence.rfind(" ", start, min(start + 100, len(sentence)))
        if ws > start:
            return ws
        return window_end

    @staticmethod
    def _split_for_phonemes(text: str, limit: int = CHUNK_PHONEMES) -> list[str]:
        """Chia văn bản thành chunk sao cho mỗi chunk <= `limit` phoneme.

        Model Kokoro giới hạn ~510 phoneme/đoạn (node /bert/Expand lỗi nếu
        vượt). Chia theo ký tự không đủ chính xác vì tiếng Việt phát sinh
        ~1.6 phoneme/ký tự, nên phải đo bằng vig2p.
        """
        from vig2p import phonemize_text

        text = re.sub(r"\s+", " ", text.strip())
        if not text:
            return []

        raw_pieces: list[str] = []
        for sentence in _SENTENCE_SPLIT.split(text):
            sentence = sentence.strip()
            if not sentence:
                continue
            start = 0
            while start < len(sentence):
                end = KokoroTTS._cut_point(sentence, start)
                piece = sentence[start:end].strip()
                if piece:
                    raw_pieces.append(piece)
                start = end

        chunks: list[str] = []
        current = ""
        for piece in raw_pieces:
            candidate = f"{current} {piece}" if current else piece
            if current and len(phonemize_text(candidate)) > limit:
                chunks.append(current)
                current = piece
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks
