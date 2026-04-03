import os

os.environ.setdefault("SKIP_STARTUP_DB_INIT", "true")
os.environ.setdefault("SKIP_MODEL_LOAD", "true")
os.environ.setdefault("TOKEN_SECRET", "test-secret")

from fastapi.testclient import TestClient
import main


class InMemoryUsersCollection:
    def __init__(self):
        self.docs = []

    def find_one(self, query):
        key, value = next(iter(query.items()))
        for doc in self.docs:
            if doc.get(key) == value:
                return dict(doc)
        return None

    def update_one(self, flt, update, upsert=False):
        key, value = next(iter(flt.items()))
        idx = None
        for i, doc in enumerate(self.docs):
            if doc.get(key) == value:
                idx = i
                break

        if idx is None:
            if not upsert:
                return
            base = dict(flt)
            base.update(update.get("$setOnInsert", {}))
            base.update(update.get("$set", {}))
            self.docs.append(base)
            return

        doc = self.docs[idx]
        doc.update(update.get("$set", {}))
        for unset_key in update.get("$unset", {}).keys():
            doc.pop(unset_key, None)
        self.docs[idx] = doc


    def insert_legacy_user(self, doc):
        self.docs.append(dict(doc))


class InMemorySessionsCollection:
    def __init__(self):
        self.docs = []

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, query, projection=None):
        key, value = next(iter(query.items()))
        out = []
        for doc in self.docs:
            if doc.get(key) == value:
                item = dict(doc)
                if projection:
                    for proj_key, include in projection.items():
                        if include == 0:
                            item.pop(proj_key, None)
                out.append(item)
        return out


class InMemoryAlertsCollection:
    def __init__(self):
        self.docs = []

    def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, query, projection=None):
        key, value = next(iter(query.items()))
        out = []
        for doc in self.docs:
            if doc.get(key) == value:
                item = dict(doc)
                if projection:
                    for proj_key, include in projection.items():
                        if include == 0:
                            item.pop(proj_key, None)
                out.append(item)
        return out


def _sample_sequence(n=24):
    out = []
    t = 1000
    for i in range(n):
        down = t
        up = down + 80 + (i % 5)
        out.append({"key": "a", "down": down, "up": up})
        t = up + 60 + (i % 7)
    return out


def _imposter_sequence(n=24):
    out = []
    t = 5000
    for i in range(n):
        down = t
        up = down + 10 + (i % 3)
        out.append({"key": "a", "down": down, "up": up})
        t = up + 600 + (i % 11)
    return out


def setup_module(_module):
    main.collection = InMemoryUsersCollection()
    main.sessions_collection = InMemorySessionsCollection()
    main.alerts_collection = InMemoryAlertsCollection()
    main.failed_logins.clear()
    main.rate_limit_state.clear()


def test_register_requires_min_keystrokes():
    client = TestClient(main.app)
    payload = {"username": "alice", "password": "supersecret", "keystrokes": _sample_sequence(5)}
    res = client.post("/register", json=payload)
    assert res.status_code == 400
    assert "At least" in res.json()["detail"]


def test_register_login_and_protected_analytics_flow():
    client = TestClient(main.app)
    seq = _sample_sequence(24)

    # 3 enrollment samples required
    for expected_count in (1, 2, 3):
        res = client.post("/register", json={"username": "alice", "password": "supersecret", "keystrokes": seq})
        assert res.status_code == 200
        body = res.json()
        assert body["sample_count"] == expected_count

    # login should issue token
    login_res = client.post("/login", json={"username": "alice", "password": "supersecret", "keystrokes": seq})
    assert login_res.status_code == 200
    login_body = login_res.json()
    assert login_body["status"] == "success"
    token = login_body.get("token")
    assert token

    # analytics without token should be unauthorized
    no_auth_res = client.get("/analytics/alice")
    assert no_auth_res.status_code == 401

    # analytics with token should work
    auth_res = client.get("/analytics/alice", headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 200
    sessions = auth_res.json()["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["status"] in {"success", "failure"}


def test_health_endpoint():
    client = TestClient(main.app)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "keystroke-backend"


def test_imposter_pattern_is_rejected_for_enrolled_user():
    client = TestClient(main.app)
    genuine = _sample_sequence(24)
    imposter = _imposter_sequence(24)

    for _ in range(3):
        reg_res = client.post("/register", json={"username": "victim", "password": "victim-pass", "keystrokes": genuine})
        assert reg_res.status_code == 200

    login_res = client.post("/login", json={"username": "victim", "password": "victim-pass", "keystrokes": imposter})
    assert login_res.status_code == 200

    body = login_res.json()
    assert body["status"] == "failure"
    assert body["token"] is None
    assert body["components"]["max_similarity"] < 0.85


def test_login_fails_with_wrong_password_and_creates_alert():
    client = TestClient(main.app)
    seq = _sample_sequence(24)

    for _ in range(3):
        client.post("/register", json={"username": "bob", "password": "right-pass", "keystrokes": seq})

    login_res = client.post("/login", json={"username": "bob", "password": "wrong-pass", "keystrokes": seq})
    assert login_res.status_code == 200
    assert login_res.json()["status"] == "failure"
    assert login_res.json()["message"] == "Invalid credentials"


def test_legacy_user_can_be_migrated_with_password():
    client = TestClient(main.app)
    seq = _sample_sequence(24)

    main.collection.insert_legacy_user({
        "username": "legacy",
        "username_normalized": "legacy",
        "embeddings": [main._build_embedding(main._normalize_features(main._events_to_features(main._validate_and_convert_events(seq)))).tolist() for _ in range(5)],
        "feature_profiles": [
            {
                "mean": [100.0, 50.0],
                "std": [10.0, 5.0]
            }
            for _ in range(5)
        ],
        "mean_vector": [0.0] * 50,
        "std_vector": [0.0] * 50,
        "feature_mean_vector": [100.0, 50.0],
        "feature_std_vector": [10.0, 5.0],
        "threshold": 0.85
    })

    res = client.post("/register", json={"username": "legacy", "password": "legacy-pass-123", "keystrokes": seq})
    assert res.status_code == 200
    body = res.json()
    assert body["migrated_legacy_account"] is True
    assert body["ready_for_login"] is True

    login_res = client.post("/login", json={"username": "legacy", "password": "legacy-pass-123", "keystrokes": seq})
    assert login_res.status_code == 200
    assert login_res.json()["status"] == "success"
