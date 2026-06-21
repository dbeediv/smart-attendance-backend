"""
Face recognition service.

Approach:
1. On registration, we extract a face EMBEDDING (a 128/512-dim vector that
   represents facial features) using DeepFace's ArcFace model, and store
   ONLY the embedding - never the raw photo. This is a meaningful privacy
   design choice worth mentioning in interviews.
2. On check-in, we extract an embedding from the live capture and compare
   it against the stored embedding using cosine similarity. Above a
   threshold = match.

Why ArcFace: it's one of the more accurate open models DeepFace ships,
good balance of speed vs accuracy for a CPU-only demo environment.
"""
import base64
import io
import json
import numpy as np
from PIL import Image
from deepface import DeepFace

MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "opencv"   # fast, no extra downloads beyond DeepFace's own weights
MATCH_THRESHOLD = 0.68        # cosine similarity threshold - tune based on testing


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Convert a base64 (or data-URL) string from the frontend into a numpy array DeepFace can use."""
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]  # strip "data:image/jpeg;base64," prefix
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return np.array(image)


def extract_embedding(image_base64: str) -> list:
    """
    Run face detection + embedding extraction on a captured image.
    Raises ValueError if no face is detected - caller should turn this
    into a clean 400 error for the frontend.
    """
    img_array = decode_base64_image(image_base64)
    try:
        result = DeepFace.represent(
            img_path=img_array,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )
    except ValueError as e:
        msg = str(e)
        # DeepFace/gdown raise ValueError for BOTH "no face detected" and
        # "model weights failed to download" - these need different handling,
        # so we distinguish by message content rather than masking both as
        # the same user-facing error.
        if "download" in msg.lower() or "weight" in msg.lower():
            raise RuntimeError(
                f"Face recognition model weights are not available locally: {msg}"
            ) from e
        raise ValueError(
            "No face detected in the captured image. Please try again with better lighting."
        ) from e

    # DeepFace.represent returns a list (one entry per detected face) - we take the first/largest face
    embedding = result[0]["embedding"]
    return embedding


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def serialize_embedding(embedding: list) -> str:
    return json.dumps(embedding)


def deserialize_embedding(embedding_json: str) -> list:
    return json.loads(embedding_json)


def find_best_match(captured_embedding: list, candidates: list[tuple[int, str]]) -> tuple[int | None, float]:
    """
    Compare a captured embedding against a list of (user_id, stored_embedding_json) tuples.
    Returns (best_matching_user_id, similarity_score), or (None, 0.0) if no match clears the threshold.

    Note: this is a linear O(n) scan - perfectly fine for a class of 60-200 students.
    At real scale (thousands of users) you'd swap this for a vector index (FAISS, pgvector)
    instead of looping - worth mentioning if asked about scaling this system.
    """
    best_user_id = None
    best_score = 0.0

    for user_id, embedding_json in candidates:
        stored_embedding = deserialize_embedding(embedding_json)
        score = cosine_similarity(captured_embedding, stored_embedding)
        if score > best_score:
            best_score = score
            best_user_id = user_id

    if best_score >= MATCH_THRESHOLD:
        return best_user_id, best_score
    return None, best_score
