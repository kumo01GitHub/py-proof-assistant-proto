"""Proof certificate model for kernel-verified theorem entries."""

import hmac
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, List, Optional


_CERT_SECRET = os.environ.get("ZFC_LEANPY_CERT_SECRET", "zfc-leanpy-dev-secret").encode("utf-8")


def _payload(statement: str, tactics: List[str], replay_ok: bool) -> bytes:
    body = {
        "statement": statement,
        "tactics": list(tactics),
        "replay_ok": replay_ok,
    }
    return json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sign_payload(payload: bytes) -> str:
    return hmac.new(_CERT_SECRET, payload, sha256).hexdigest()


@dataclass(frozen=True)
class ProofCertificate:
    statement: str
    tactics: List[str]
    replay_ok: bool
    signature: str

    def verify(self) -> bool:
        expected = _sign_payload(_payload(self.statement, self.tactics, self.replay_ok))
        return hmac.compare_digest(expected, self.signature)

    def to_dict(self) -> Dict[str, object]:
        return {
            "statement": self.statement,
            "tactics": list(self.tactics),
            "replay_ok": self.replay_ok,
            "signature": self.signature,
            "kind": "kernel-certificate",
        }


def issue_certificate(statement: str, tactics: List[str], replay_ok: bool) -> Optional[ProofCertificate]:
    if not replay_ok:
        return None
    sig = _sign_payload(_payload(statement, tactics, replay_ok))
    cert = ProofCertificate(statement=statement, tactics=list(tactics), replay_ok=replay_ok, signature=sig)
    if not cert.verify():
        return None
    return cert
