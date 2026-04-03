from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
import torch
import numpy as np
from pymongo import ASCENDING, MongoClient
from datetime import datetime, timedelta, timezone
from itertools import combinations
import base64
import hashlib
import hmac
import json
import os
import time
from dotenv import load_dotenv

# ------------------ FIX OPENMP ERROR ------------------
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ------------------ APP INIT ------------------
app = FastAPI()

load_dotenv()


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw = _get_env(name, "1" if default else "0").lower()
    return raw in {"1", "true", "yes", "on"}


MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set")

DB_NAME = _get_env("DB_NAME", "keystroke_saas")
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = _get_env("MODEL_PATH", os.path.abspath(os.path.join(BASE_DIR, "..", "models", "transformer_model.pth")))
MEAN_PATH = _get_env("MEAN_PATH", os.path.abspath(os.path.join(BASE_DIR, "..", "models", "mean.npy")))
STD_PATH = _get_env("STD_PATH", os.path.abspath(os.path.join(BASE_DIR, "..", "models", "std.npy")))

TOKEN_SECRET = _get_env("TOKEN_SECRET", "dev-only-change-me")
TOKEN_TTL_MINUTES = int(_get_env("TOKEN_TTL_MINUTES", "120"))

CORS_ORIGINS = [origin.strip() for origin in _get_env("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

MAX_LOGIN_ATTEMPTS = int(_get_env("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_SECONDS = int(_get_env("LOCKOUT_SECONDS", "300"))
RATE_LIMIT_WINDOW_SECONDS = int(_get_env("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_ATTEMPTS = int(_get_env("RATE_LIMIT_MAX_ATTEMPTS", "20"))
ALLOW_DB_RESET = _get_bool_env("ALLOW_DB_RESET", False)
ADMIN_RESET_KEY = _get_env("ADMIN_RESET_KEY", "")

SKIP_STARTUP_DB_INIT = _get_bool_env("SKIP_STARTUP_DB_INIT", False)
SKIP_MODEL_LOAD = _get_bool_env("SKIP_MODEL_LOAD", False)

# ------------------ CORS FIX (VERY IMPORTANT) ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ------------------ DATABASE ------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["users"]
sessions_collection = db["sessions"]
alerts_collection = db["alerts"]


if not SKIP_STARTUP_DB_INIT:
    try:
        collection.create_index(
            [("username_normalized", ASCENDING)],
            unique=True,
            partialFilterExpression={"username_normalized": {"$type": "string"}}
        )
    except Exception as exc:
        print(f"[WARN] Could not create unique username index: {exc}")

    sessions_collection.create_index([("username_normalized", ASCENDING), ("time", ASCENDING)])
    alerts_collection.create_index([("username_normalized", ASCENDING), ("time", ASCENDING)])

MIN_KEYSTROKES = 20
REQUIRED_ENROLLMENTS = 3
MAX_ENROLLMENTS_TO_KEEP = 5
MIN_THRESHOLD = 0.80
MAX_THRESHOLD = 0.85
EMBEDDING_WEIGHT = 0.80
STAT_WEIGHT = 0.20
PASSWORD_MIN_LENGTH = 8
PASSWORD_HASH_ITERATIONS = 210000

security = HTTPBearer(auto_error=False)
failed_logins = {}
rate_limit_state = {}


def _load_normalization_vectors() -> tuple[np.ndarray, np.ndarray]:
    default_mean = np.array([0.0, 0.0], dtype=np.float32)
    default_std = np.array([1.0, 1.0], dtype=np.float32)

    try:
        mean = np.load(MEAN_PATH).astype(np.float32)
        std = np.load(STD_PATH).astype(np.float32)

        if mean.shape != (2,) or std.shape != (2,):
            print("[WARN] mean/std shape invalid. Expected (2,), using defaults.")
            return default_mean, default_std

        return mean, std
    except Exception:
        print("[WARN] mean.npy or std.npy missing/unreadable. Using default normalization.")
        return default_mean, default_std


NORM_MEAN, NORM_STD = _load_normalization_vectors()

# ------------------ MODEL ------------------

class TransformerModel(torch.nn.Module):
    def __init__(self, input_size, d_model, num_heads, num_layers, num_classes):
        super().__init__()

        self.input_fc = torch.nn.Linear(input_size, d_model)

        encoder_layer = torch.nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            batch_first=True
        )

        self.transformer = torch.nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        self.fc = torch.nn.Linear(d_model, num_classes)

    def forward(self, x):
        x = self.input_fc(x)
        x = self.transformer(x)
        x = x[:, -1, :]
        x = self.fc(x)
        return x


# ------------------ LOAD MODEL ------------------

model = None
if not SKIP_MODEL_LOAD:
    model = TransformerModel(2, 64, 4, 2, 50)

    model.load_state_dict(
        torch.load(
            MODEL_PATH,
            map_location=torch.device('cpu')
        )
    )

    model.eval()


# ------------------ REQUEST MODEL ------------------

class UserInput(BaseModel):
    username: str
    password: str
    keystrokes: list[dict] | None = None
    sequence: list | None = None


class KeystrokeEvent(BaseModel):
    key: str = Field(default="")
    down: float
    up: float


def _normalize_username(username: str):
    display = username.strip()
    normalized = display.casefold()
    return display, normalized


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def _create_access_token(username_normalized: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username_normalized,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=TOKEN_TTL_MINUTES)).timestamp())
    }
    header = {"alg": "HS256", "typ": "JWT"}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _verify_access_token(token: str) -> str:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(signature_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload") from exc

    exp = payload.get("exp")
    sub = payload.get("sub")
    if not exp or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    if int(time.time()) >= int(exp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return str(sub)


def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return _verify_access_token(credentials.credentials)


def _check_rate_limit(identifier: str):
    now = int(time.time())
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    attempts = rate_limit_state.get(identifier, [])
    attempts = [ts for ts in attempts if ts >= window_start]
    attempts.append(now)
    rate_limit_state[identifier] = attempts

    if len(attempts) > RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait and try again."
        )


def _check_lockout(username_normalized: str):
    state = failed_logins.get(username_normalized)
    if not state:
        return

    lock_until = state.get("lock_until", 0)
    if int(time.time()) < lock_until:
        remaining = lock_until - int(time.time())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked. Try again in {remaining} seconds."
        )


def _record_failed_login(username_normalized: str):
    now = int(time.time())
    state = failed_logins.get(username_normalized, {"count": 0, "lock_until": 0})
    state["count"] += 1

    if state["count"] >= MAX_LOGIN_ATTEMPTS:
        state["count"] = 0
        state["lock_until"] = now + LOCKOUT_SECONDS

    failed_logins[username_normalized] = state


def _clear_failed_login(username_normalized: str):
    if username_normalized in failed_logins:
        del failed_logins[username_normalized]


def _safe_cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm == 0.0 or b_norm == 0.0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def _validate_password_strength(password: str):
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
        )


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    raw_salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        raw_salt,
        PASSWORD_HASH_ITERATIONS
    )
    return _b64url_encode(raw_salt), _b64url_encode(digest)


def _verify_password(password: str, password_salt: str, password_hash: str) -> bool:
    try:
        raw_salt = _b64url_decode(password_salt)
    except Exception:
        return False

    _, computed_hash = _hash_password(password, raw_salt)
    return hmac.compare_digest(computed_hash, password_hash)


def _record_suspicious_alert(
    username: str,
    username_normalized: str,
    reason: str,
    request: Request,
    metadata: dict | None = None
):
    alerts_collection.insert_one({
        "username": username,
        "username_normalized": username_normalized,
        "time": str(datetime.now()),
        "ip": request.client.host if request.client else "unknown",
        "reason": reason,
        "metadata": metadata or {}
    })


def _validate_and_convert_events(raw_keystrokes: list[dict]) -> list[KeystrokeEvent]:
    if not isinstance(raw_keystrokes, list) or len(raw_keystrokes) < MIN_KEYSTROKES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {MIN_KEYSTROKES} keystrokes are required"
        )

    events: list[KeystrokeEvent] = []
    for idx, item in enumerate(raw_keystrokes):
        if not isinstance(item, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid keystroke event format")

        try:
            event = KeystrokeEvent(**item)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid keystroke event at index {idx}") from exc

        if event.down is None or event.up is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing key down/up timings")

        if float(event.up) < float(event.down):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sequence: key up before key down")

        events.append(event)

    # Frontend may append events in key-up order; always normalize to key-down order.
    events.sort(key=lambda e: (float(e.down), float(e.up)))

    return events


def _events_to_features(events: list[KeystrokeEvent]) -> np.ndarray:
    rows = []

    for idx, current in enumerate(events):
        dwell_time = float(current.up) - float(current.down)
        if idx < len(events) - 1:
            next_event = events[idx + 1]
            flight_time = float(next_event.down) - float(current.up)
        else:
            flight_time = 0.0

        rows.append([max(dwell_time, 0.0), max(flight_time, 0.0)])

    features = np.array(rows, dtype=np.float32)
    if features.shape[0] < MIN_KEYSTROKES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {MIN_KEYSTROKES} keystrokes are required"
        )

    return features


def _normalize_features(features: np.ndarray) -> np.ndarray:
    return (features - NORM_MEAN) / (NORM_STD + 1e-6)


def _extract_stat_vectors(features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean_vector = np.mean(features, axis=0).astype(np.float32)
    std_vector = np.std(features, axis=0).astype(np.float32)
    return mean_vector, std_vector


def _statistical_similarity(sample_mean: np.ndarray, sample_std: np.ndarray, user_mean: np.ndarray, user_std: np.ndarray) -> float:
    baseline = np.array([10.0, 10.0], dtype=np.float32)
    scale = np.maximum(user_std, baseline)

    mean_z = np.abs(sample_mean - user_mean) / (scale + 1e-6)
    std_z = np.abs(sample_std - user_std) / (scale + 1e-6)

    combined_dist = float(np.mean(mean_z) + np.mean(std_z))
    score = float(1.0 / (1.0 + combined_dist))
    return max(0.0, min(1.0, score))


def get_embedding(model_ref: TransformerModel | None, x: torch.Tensor) -> np.ndarray:
    if model_ref is None:
        fallback = x.squeeze(0).detach().cpu().numpy().flatten().astype(np.float32)
        if fallback.size == 0:
            return np.zeros((50,), dtype=np.float32)
        repeats = int(np.ceil(50 / fallback.size))
        return np.tile(fallback, repeats)[:50]

    with torch.no_grad():
        x = model_ref.input_fc(x)
        x = model_ref.transformer(x)
        x = x[:, -1, :]
    return x.squeeze(0).detach().cpu().numpy().astype(np.float32)


def _build_embedding(features_normalized: np.ndarray) -> np.ndarray:
    input_tensor = torch.tensor(features_normalized, dtype=torch.float32).unsqueeze(0)
    return get_embedding(model, input_tensor)


def _get_feature_profiles(user_doc: dict) -> list[dict]:
    profiles = user_doc.get("feature_profiles", [])
    if isinstance(profiles, list):
        return profiles
    return []


def _adaptive_threshold(embeddings: list[list[float]], feature_profiles: list[dict]) -> float:
    if len(embeddings) < 2:
        return MIN_THRESHOLD

    vectors = [np.array(e, dtype=np.float32) for e in embeddings]
    pairwise_scores: list[float] = []

    for i, j in combinations(range(len(vectors)), 2):
        emb_score = _safe_cosine_similarity(vectors[i], vectors[j])

        if i < len(feature_profiles) and j < len(feature_profiles):
            mean_i = np.array(feature_profiles[i].get("mean", [0.0, 0.0]), dtype=np.float32)
            std_i = np.array(feature_profiles[i].get("std", [1.0, 1.0]), dtype=np.float32)
            mean_j = np.array(feature_profiles[j].get("mean", [0.0, 0.0]), dtype=np.float32)
            std_j = np.array(feature_profiles[j].get("std", [1.0, 1.0]), dtype=np.float32)
            stat_score = _statistical_similarity(mean_i, std_i, mean_j, std_j)
        else:
            stat_score = emb_score

        pairwise_scores.append(float((EMBEDDING_WEIGHT * emb_score) + (STAT_WEIGHT * stat_score)))

    if not pairwise_scores:
        return MIN_THRESHOLD

    threshold = float(np.mean(pairwise_scores) - np.std(pairwise_scores))
    threshold = min(MAX_THRESHOLD, threshold)
    return max(MIN_THRESHOLD, threshold)


def _get_user_embeddings(user_doc: dict) -> list[list[float]]:
    embeddings = user_doc.get("embeddings", [])
    if isinstance(embeddings, list):
        return embeddings
    return []


def _parse_request_features(data: UserInput) -> tuple[np.ndarray, np.ndarray]:
    if data.keystrokes is not None:
        events = _validate_and_convert_events(data.keystrokes)
        features = _events_to_features(events)
        return features, _normalize_features(features)

    # Backward compatibility while frontend migrates to event objects.
    if data.sequence is not None and isinstance(data.sequence, list):
        if len(data.sequence) < MIN_KEYSTROKES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"At least {MIN_KEYSTROKES} keystrokes are required"
            )
        try:
            arr = np.array(data.sequence, dtype=np.float32)
            if arr.ndim != 2 or arr.shape[1] != 2:
                raise ValueError("Invalid sequence shape")
            if np.any(arr < 0):
                raise ValueError("Negative timings are invalid")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sequence payload") from exc
        return arr, _normalize_features(arr)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing keystrokes payload")


# ------------------ REGISTER ------------------

@app.post("/register")
def register(data: UserInput, request: Request):
    _check_rate_limit(f"register:{request.client.host}")
    if not data.username or not data.username.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")
    _validate_password_strength(data.password)

    username, username_normalized = _normalize_username(data.username)
    features_raw, features_norm = _parse_request_features(data)
    embedding = _build_embedding(features_norm).tolist()
    sample_mean, sample_std = _extract_stat_vectors(features_raw)

    user = collection.find_one({"username_normalized": username_normalized})
    embeddings = _get_user_embeddings(user) if user else []
    feature_profiles = _get_feature_profiles(user) if user else []
    is_legacy_user = bool(user and not user.get("password_hash"))

    password_salt = None
    password_hash = None
    if user:
        password_salt = user.get("password_salt", "")
        password_hash = user.get("password_hash", "")

        if password_salt and password_hash and not _verify_password(data.password, password_salt, password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not password_salt or not password_hash:
        password_salt, password_hash = _hash_password(data.password)

    if user and len(embeddings) >= MAX_ENROLLMENTS_TO_KEEP and not is_legacy_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has {MAX_ENROLLMENTS_TO_KEEP} enrollment samples. Use login for authentication."
        )

    if is_legacy_user and len(embeddings) >= MAX_ENROLLMENTS_TO_KEEP:
        collection.update_one(
            {"username_normalized": username_normalized},
            {
                "$set": {
                    "username": username,
                    "username_normalized": username_normalized,
                    "password_salt": password_salt,
                    "password_hash": password_hash,
                    "password_updated_at": str(datetime.now()),
                    "updated_at": str(datetime.now())
                }
            }
        )
        return {
            "message": "Legacy account migrated. Password has been added.",
            "sample_count": len(embeddings),
            "required_samples": REQUIRED_ENROLLMENTS,
            "remaining_samples": 0,
            "ready_for_login": True,
            "max_samples": MAX_ENROLLMENTS_TO_KEEP,
            "threshold": float(user.get("threshold", MIN_THRESHOLD)),
            "migrated_legacy_account": True
        }

    embeddings.append(embedding)
    embeddings = embeddings[-MAX_ENROLLMENTS_TO_KEEP:]

    feature_profiles.append({
        "mean": sample_mean.tolist(),
        "std": sample_std.tolist()
    })
    feature_profiles = feature_profiles[-MAX_ENROLLMENTS_TO_KEEP:]

    matrix = np.array(embeddings, dtype=np.float32)
    mean_vector = np.mean(matrix, axis=0).astype(np.float32)
    std_vector = np.std(matrix, axis=0).astype(np.float32)

    feature_mean_matrix = np.array([p["mean"] for p in feature_profiles], dtype=np.float32)
    feature_std_matrix = np.array([p["std"] for p in feature_profiles], dtype=np.float32)
    user_feature_mean = np.mean(feature_mean_matrix, axis=0).astype(np.float32)
    user_feature_std = np.mean(feature_std_matrix, axis=0).astype(np.float32)

    threshold = _adaptive_threshold(embeddings, feature_profiles)

    collection.update_one(
        {"username_normalized": username_normalized},
        {
            "$set": {
                "username": username,
                "username_normalized": username_normalized,
                "embeddings": embeddings,
                "feature_profiles": feature_profiles,
                "mean_vector": mean_vector.tolist(),
                "std_vector": std_vector.tolist(),
                "feature_mean_vector": user_feature_mean.tolist(),
                "feature_std_vector": user_feature_std.tolist(),
                "threshold": float(threshold),
                "password_salt": password_salt,
                "password_hash": password_hash,
                "password_updated_at": str(datetime.now()),
                "updated_at": str(datetime.now())
            },
            "$setOnInsert": {
                "created_at": str(datetime.now())
            }
        },
        upsert=True
    )

    sample_count = len(embeddings)
    remaining = max(0, REQUIRED_ENROLLMENTS - sample_count)

    return {
        "message": "Enrollment sample saved",
        "sample_count": sample_count,
        "required_samples": REQUIRED_ENROLLMENTS,
        "remaining_samples": remaining,
        "ready_for_login": sample_count >= REQUIRED_ENROLLMENTS,
        "max_samples": MAX_ENROLLMENTS_TO_KEEP,
        "threshold": float(threshold)
    }


# ------------------ LOGIN ------------------

@app.post("/login")
def login(data: UserInput, request: Request):
    _check_rate_limit(f"login:{request.client.host}")
    if not data.username or not data.username.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")
    if not data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")

    username, username_normalized = _normalize_username(data.username)
    _check_lockout(username_normalized)

    user = collection.find_one({"username_normalized": username_normalized})
    if user is None:
        _record_failed_login(username_normalized)
        _record_suspicious_alert(username, username_normalized, "unknown_user_attempt", request)
        return {"status": "failure", "message": "User not found"}

    password_salt = user.get("password_salt", "")
    password_hash = user.get("password_hash", "")
    if not password_salt or not password_hash or not _verify_password(data.password, password_salt, password_hash):
        _record_failed_login(username_normalized)
        _record_suspicious_alert(username, username_normalized, "invalid_password", request)
        return {"status": "failure", "message": "Invalid credentials"}

    embeddings = _get_user_embeddings(user)
    feature_profiles = _get_feature_profiles(user)
    if len(embeddings) < REQUIRED_ENROLLMENTS:
        _record_failed_login(username_normalized)
        return {
            "status": "failure",
            "message": f"Need {REQUIRED_ENROLLMENTS} enrollment samples before login",
            "sample_count": len(embeddings),
            "required_samples": REQUIRED_ENROLLMENTS
        }

    features_raw, features_norm = _parse_request_features(data)
    new_embedding = _build_embedding(features_norm)
    sample_mean, sample_std = _extract_stat_vectors(features_raw)

    similarities = []
    for emb in embeddings:
        stored_embedding = np.array(emb, dtype=np.float32)
        similarities.append(_safe_cosine_similarity(new_embedding, stored_embedding))

    max_similarity = float(max(similarities)) if similarities else 0.0

    threshold = float(_adaptive_threshold(embeddings, feature_profiles))

    if max_similarity < 0.85:
        _record_failed_login(username_normalized)
        _record_suspicious_alert(
            username,
            username_normalized,
            "biometric_mismatch_hard_floor",
            request,
            {
                "max_similarity": float(max_similarity),
                "threshold": float(threshold)
            }
        )
        sessions_collection.insert_one({
            "username": username,
            "username_normalized": username_normalized,
            "time": str(datetime.now()),
            "score": float(max_similarity),
            "max_similarity": max_similarity,
            "stat_score": 0.0,
            "threshold": threshold,
            "status": "failure",
            "sequence_length": int(features_raw.shape[0]),
            "reason": "max_similarity_below_hard_floor"
        })
        return {
            "status": "failure",
            "score": float(max_similarity),
            "threshold": threshold,
            "token": None,
            "components": {
                "max_similarity": max_similarity,
                "stat_score": 0.0
            },
            "message": "Authentication rejected: similarity too low"
        }

    user_mean = np.array(user.get("feature_mean_vector", [0.0, 0.0]), dtype=np.float32)
    user_std = np.array(user.get("feature_std_vector", [1.0, 1.0]), dtype=np.float32)
    stat_score = _statistical_similarity(sample_mean, sample_std, user_mean, user_std)

    final_score = float((EMBEDDING_WEIGHT * max_similarity) + (STAT_WEIGHT * stat_score))
    login_status = "success" if final_score >= threshold else "failure"

    token = None
    if login_status == "success":
        _clear_failed_login(username_normalized)
        token = _create_access_token(username_normalized)
    else:
        _record_failed_login(username_normalized)
        _record_suspicious_alert(
            username,
            username_normalized,
            "biometric_mismatch_threshold",
            request,
            {
                "score": float(final_score),
                "threshold": float(threshold),
                "max_similarity": float(max_similarity),
                "stat_score": float(stat_score)
            }
        )

    sessions_collection.insert_one({
        "username": username,
        "username_normalized": username_normalized,
        "time": str(datetime.now()),
        "score": final_score,
        "max_similarity": max_similarity,
        "stat_score": stat_score,
        "threshold": threshold,
        "status": login_status,
        "sequence_length": int(features_raw.shape[0])
    })

    return {
        "status": login_status,
        "score": final_score,
        "threshold": threshold,
        "token": token,
        "components": {
            "max_similarity": max_similarity,
            "stat_score": stat_score
        },
        "message": (
            "Authentication successful"
            if login_status == "success"
            else (
                f"Authentication failed: score {final_score:.4f} is below threshold {threshold:.4f} "
                f"(max_similarity={max_similarity:.4f}, stat_score={stat_score:.4f})"
            )
        )
    }


# ------------------ ANALYTICS ------------------

@app.get("/analytics/{username}")
def get_analytics(username: str, current_user: str = Depends(_get_current_user)):

    _, username_normalized = _normalize_username(username)
    if username_normalized != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: token does not match user")

    sessions = list(sessions_collection.find({"username_normalized": username_normalized}, {"_id": 0, "username_normalized": 0}))

    return {
        "sessions": sessions
    }


@app.get("/alerts/{username}")
def get_alerts(username: str, current_user: str = Depends(_get_current_user)):
    _, username_normalized = _normalize_username(username)
    if username_normalized != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: token does not match user")

    alerts = list(
        alerts_collection.find(
            {"username_normalized": username_normalized},
            {"_id": 0, "username_normalized": 0}
        ).sort("time", -1)
    )
    return {"alerts": alerts}


@app.post("/admin/reset-users")
def reset_users(request: Request):
    if not ALLOW_DB_RESET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Database reset is disabled")

    if ADMIN_RESET_KEY:
        provided_key = request.headers.get("x-admin-reset-key", "")
        if provided_key != ADMIN_RESET_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin reset key")

    users_result = collection.delete_many({})
    sessions_result = sessions_collection.delete_many({})
    alerts_result = alerts_collection.delete_many({})

    return {
        "message": "Authentication data reset complete",
        "users_deleted": users_result.deleted_count,
        "sessions_deleted": sessions_result.deleted_count,
        "alerts_deleted": alerts_result.deleted_count
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "keystroke-backend",
        "db_init_skipped": SKIP_STARTUP_DB_INIT,
        "model_loaded": model is not None
    }


# ------------------ RUN SERVER ------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)