# Plan: End-to-End Encryption + S3 Document Storage (Harvey-style)

## Context

mamlaAI stores all user documents in MongoDB GridFS on the **free Atlas tier** (M0), which does **not** include encryption at rest — files on disk are plaintext. Sensitive case/chat data is also stored as plaintext in MongoDB. The only encryption in the app today covers session metadata (IP/location). This plan brings the app to Harvey-style data privacy: documents encrypted at rest in cheap object storage, sensitive database fields encrypted at the application layer, and a clear picture of what Supabase handles vs what we must handle ourselves.

---

## 1. Storage Recommendation: Cloudflare R2

**Use Cloudflare R2** (S3-compatible API, `boto3` works with a single `endpoint_url` override).

| Option | Storage | Egress | Notes |
|---|---|---|---|
| **Cloudflare R2** | $0.015/GB | **$0 egress** | Best for our use case |
| AWS S3 ap-south-1 | $0.023/GB | $0.09/GB | Only if strict Indian data residency is legally required |
| Backblaze B2 | $0.006/GB | $0.01/GB | Worse SDK, high egress |

Egress costs matter because every Celery ingest task downloads the full file from storage. R2 eliminates that cost entirely. The abstraction layer means switching to AWS S3 ap-south-1 later is a one-line env var change.

---

## 2. Supabase — What's Already Safe (No Action Needed)

Supabase `user_metadata` stores: `user_id`, `phone`, `first_name`, `last_name`, `email`.

**Supabase already provides:**
- Encryption at rest (managed Postgres, AES-256 at the infrastructure level)
- Row-Level Security (RLS) policies
- TLS in transit

We **cannot** add application-level Fernet encryption to Supabase columns — it would break Supabase's own auth queries and phone-number lookups used by the WhatsApp module. The infrastructure-level encryption Supabase provides is sufficient for this table. No changes needed here.

---

## 3. MongoDB — The Gap

The **free Atlas tier (M0) does NOT include encryption at rest.** This means `cases`, `case_notes`, `hearing_notes`, `whatsapp_chat_sessions`, `draft_conversations`, etc. are stored as plaintext on disk. Two options to fix this:

- **Option A (recommended):** Application-level field encryption on sensitive fields — works on any Atlas tier, no cost increase
- **Option B:** Upgrade to Atlas M10+ which adds encryption at rest — costs ~$57/month and still doesn't protect against a compromised DB credential

We use **Option A** — application-level encryption using the existing `Fernet(ENCRYPTION_KEY)` already in the codebase.

---

## 4. Encryption Scheme

### Document Files — Envelope Encryption

```
MASTER_KEY (existing ENCRYPTION_KEY env var, Fernet)
    └── per-document DATA_KEY (32-byte random AES-256-GCM key, generated at upload)
            └── encrypted ciphertext stored on R2/S3
```

- Uses `cryptography.hazmat.primitives.ciphers.aead.AESGCM` (already a transitive dep)
- `DATA_KEY` wrapped with master Fernet key → stored in `rag_documents.storage.encrypted_data_key`
- Key rotation: re-wrap the stored `encrypted_data_key` values in Mongo only — S3 objects never change

### MongoDB Field-Level Encryption — extend existing Fernet

Encrypt the **content** of sensitive free-text fields. Indexed/query fields (`title`, `case_ref`, `status`, `phone_number`) stay plaintext — encrypting them would break lookups.

**Priority 1 — Legal case content (encrypt immediately):**

| Collection | Fields to encrypt |
|---|---|
| `cases` | `brief` |
| `case_notes` | `content` |
| `hearing_notes` | `content`, `outcome` |
| `aidrafts_complete_data` | `draft_sections[].content` |
| `draft_conversations` | `turns[].content` / `messages[].text` |

**Priority 2 — Chat & communication history (encrypt next):**

| Collection | Fields to encrypt |
|---|---|
| `whatsapp_chat_sessions` | `messages[].text`, `updates[].transcription` |
| `rag_chat_sessions` | `messages[].content` |
| `rag_messages` | `query` |

**Priority 3 — Meeting & calendar data (lower sensitivity, encrypt last):**

| Collection | Fields to encrypt |
|---|---|
| `user_details.meetings` | `description` per meeting entry (nested dict) |

**Do NOT encrypt:** `title`, `case_ref`, `status`, `phone_number`, `email`, `fname`, `lname`, `court`, `hearing_date`, timestamps — these are indexed, displayed in lists, and used for lookups. Encrypting them would break the app without meaningful security benefit (they're identifiers, not sensitive content).

**`decrypt_field()` must have a try/except fallback** — returns plaintext if decryption fails. This handles the migration window where old records are still plaintext.

---

## 5. Files to Create / Modify

### New files
| File | Purpose |
|---|---|
| `talkdoc/storage_backends/__init__.py` | Package init |
| `talkdoc/storage_backends/base.py` | Abstract `BaseStorageBackend` with `upload`, `download`, `delete` |
| `talkdoc/storage_backends/gridfs_backend.py` | Wraps existing GridFS logic |
| `talkdoc/storage_backends/s3_backend.py` | boto3-based R2/S3 backend |
| `talkdoc/document_crypto.py` | `generate_data_key`, `encrypt_document`, `decrypt_document`, `wrap_data_key`, `unwrap_data_key` |
| `scripts/migrate_gridfs_to_s3.py` | One-time migration: `--dry-run`, `--batch-size`, idempotent, `--cleanup-gridfs` separate pass |
| `scripts/backfill_encrypt_mongo_fields.py` | Backfill plaintext fields in existing Mongo docs, collection by collection |

### Modified files
| File | Change |
|---|---|
| `talkdoc/storage.py` | Backend factory + encrypted `upload_bytes()` |
| `talkdoc/tasks.py` | Replace hard-coded GridFS download with dual-backend read + conditional decrypt |
| `talkdoc/views.py` | `document_file` and `delete_document` use storage backend; add `decrypt_field` for `case.brief` in `_load_case_context` |
| `users/routes/encryption.py` | Add `encrypt_field(value)` / `decrypt_field(token)` helpers |
| `cases/routes/case_crud.py` | Encrypt `brief` on write, decrypt on read (including `_load_case_context` in talkdoc) |
| `cases/routes/case_notes.py` | Encrypt/decrypt `content` |
| `cases/routes/hearing_notes.py` | Encrypt/decrypt `content`, `outcome` |
| `ai_draft/routes/creatupdateAIdrafts.py` | Encrypt/decrypt `draft_sections[].content` (list iteration) |
| `agents/conversational_draft_agent.py` | Encrypt/decrypt `turns[].content` |
| `whatsapp_module/routes/handlewhatsappmessage.py` | Encrypt `messages[].text`, `updates[].transcription` on write; decrypt on read |
| `Legalv1/settings.py` | Add `STORAGE_BACKEND`, `STORAGE_BUCKET_NAME`, `STORAGE_ENDPOINT_URL`, `AWS_*` settings |
| `requirements.txt` | Add `boto3>=1.34.0` |
| `legalenv` | Add S3/R2 env var template entries |

---

## 6. Key Design Decisions

**Zero-breaking-change backward compatibility:**
- Old GridFS docs have no `encrypted_data_key` and `storage.backend='gridfs'` — ingest task handles both transparently
- `decrypt_field()` fallback: returns the value as-is if decryption fails (covers legacy plaintext docs)
- `storage.file_id` preserved on S3 docs (set to S3 key string) so existing clients don't break

**Download stays server-side proxy** (not pre-signed URL redirect):
- S3 object is ciphertext — browser can't decrypt it
- Existing `document_file` Django view remains the download endpoint, adds decrypt step

**Cross-app coupling to watch:**
- `_load_case_context` in `talkdoc/views.py` reads `case.brief` directly from MongoDB — must call `decrypt_field` there too, not just in `case_crud._serialize()`
- WhatsApp `messages[]` and `updates[]` are arrays — encrypt/decrypt must iterate; write with encryption, read with decryption on every access path

**WhatsApp note:** `phone_number` stays plaintext as it's the lookup key. Only the message/transcription content gets encrypted.

---

## 7. Implementation Steps

| Step | What | Duration |
|---|---|---|
| 1 | Provision R2 bucket, add env vars to `legalenv` | Day 1 |
| 2 | Create `document_crypto.py` + unit tests (pure functions, no Django) | Day 1 |
| 3 | Add `encrypt_field`/`decrypt_field` to `users/routes/encryption.py` | Day 1 |
| 4 | Create `storage_backends/` package + update `storage.py` factory | Day 2–3 |
| 5 | Update `tasks.py` for dual-backend ingest | Day 3 |
| 6 | Update `views.py` for dual-backend download/delete + decrypt | Day 4 |
| 7 | Wire encryption into `storage.py` upload path | Day 4 |
| 8 | Set `STORAGE_BACKEND=s3` in dev, full smoke test | Day 5 |
| 9 | Run `migrate_gridfs_to_s3.py --dry-run` then live on prod; flip `STORAGE_BACKEND=s3` | Day 6 |
| 10 | **Priority 1** field encryption: `case_crud`, `case_notes`, `hearing_notes`, `creatupdateAIdrafts`, `conversational_draft_agent` | Day 7–9 |
| 11 | **Priority 2** field encryption: `whatsapp_module`, `rag_chat_sessions`, `rag_messages` | Day 10–11 |
| 12 | **Priority 3** field encryption: `user_details.meetings.description` | Day 12 |
| 13 | Run `backfill_encrypt_mongo_fields.py` per collection on prod (safe — decrypt fallback in place) | Day 13 |

---

## 8. Verification

1. **Unit tests** for `document_crypto.py`: encrypt→decrypt round-trip, wrap/unwrap key cycle
2. **Integration test**: upload a PDF with `STORAGE_BACKEND=s3`, confirm R2 shows a binary blob, Celery ingest extracts correct text, download returns original file
3. **Regression test**: `STORAGE_BACKEND=gridfs` path still works
4. **Field encryption test**: create a case → inspect MongoDB Atlas UI directly → `brief` should be a Fernet token (`gAAAAA...`)
5. **WhatsApp test**: send a message → inspect `whatsapp_chat_sessions` directly → `messages[0].text` should be ciphertext, API response returns plaintext
6. **Migration dry-run**: zero errors before running live
7. **Backfill verification**: read a pre-migration case note through the API after backfill → returns correct plaintext