"""Initial schema per docs/db-schema.md v0.1 (pgvector, HNSW, RLS on every table).

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = pg.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)

TABLES = (
    "users",
    "conversations",
    "messages",
    "memories",
    "pending_actions",
    "audit_logs",
    "privacy_events",
    "llm_usage",
    "reminders",
    "skill_runs",
)


def _id() -> sa.Column:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
    ]


def _user_fk(nullable: bool = False, ondelete: str = "CASCADE") -> sa.Column:
    return sa.Column(
        "user_id", UUID, sa.ForeignKey("users.id", ondelete=ondelete), nullable=nullable
    )


def upgrade() -> None:
    op.execute("create extension if not exists pgcrypto")
    op.execute("create extension if not exists vector")

    # Local/CI shim: Supabase provides auth.uid() and the authenticated role. Plain Postgres
    # (docker-compose, CI service container) gets compatible stand-ins. Never overwrites Supabase's.
    op.execute(
        """
        do $$
        begin
          if not exists (select 1 from pg_roles where rolname = 'authenticated') then
            create role authenticated nologin;
          end if;
          if not exists (select 1 from pg_namespace where nspname = 'auth') then
            create schema auth;
            grant usage on schema auth to authenticated;
          end if;
          if not exists (
            select 1 from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname = 'auth' and p.proname = 'uid'
          ) then
            execute $f$
              create function auth.uid() returns uuid language sql stable as $body$
                select nullif(
                  coalesce(
                    current_setting('request.jwt.claim.sub', true),
                    current_setting('request.jwt.claims', true)::jsonb ->> 'sub'
                  ), '')::uuid
              $body$
            $f$;
          end if;
        end $$;
        """
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),  # == auth.users.id (FK only on Supabase, see TODO)
        sa.Column("display_name", sa.String(120)),
        sa.Column("locale", sa.String(10), nullable=False, server_default="hi-IN"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("voice_pref", sa.String(64)),
        sa.Column("daily_budget_usd", sa.Numeric(10, 4)),
        sa.Column("is_demo", sa.Boolean, nullable=False, server_default=sa.false()),
        *_ts(),
    )
    op.create_table(
        "conversations",
        _id(),
        _user_fk(),
        sa.Column("title", sa.String(200)),
        sa.Column("last_message_at", TS, nullable=False),
        *_ts(),
    )
    op.create_index(
        "ix_conversations_user_last_message", "conversations", ["user_id", "last_message_at"]
    )
    op.create_table(
        "messages",
        _id(),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        _user_fk(),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content_masked", sa.Text, nullable=False),
        sa.Column("model", sa.String(200)),
        sa.Column("tokens_in", sa.Integer),
        sa.Column("tokens_out", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        *_ts(),
        sa.CheckConstraint(
            "role in ('user','assistant','system','tool')", name="ck_messages_role_valid"
        ),
    )
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )
    op.create_table(
        "memories",
        _id(),
        _user_fk(),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("content_ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("nonce", sa.LargeBinary, nullable=False),
        sa.Column("key_version", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("embedding", Vector(1024)),
        sa.Column("source", sa.String(32)),
        sa.Column("deleted_at", TS),
        *_ts(),
        sa.CheckConstraint(
            "kind in ('fact','preference','person','note')", name="ck_memories_kind_valid"
        ),
    )
    op.create_index("ix_memories_user_kind_created", "memories", ["user_id", "kind", "created_at"])
    op.execute(
        "create index ix_memories_embedding_hnsw on memories "
        "using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64)"
    )
    op.create_table(
        "pending_actions",
        _id(),
        _user_fk(),
        sa.Column("skill", sa.String(64), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("payload_ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("decided_at", TS),
        *_ts(),
        sa.CheckConstraint(
            "status in ('pending','approved','rejected','expired','executed','failed')",
            name="ck_pending_actions_status_valid",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_pending_actions_idempotency_key"),
    )
    op.create_index(
        "ix_pending_actions_user_status_created",
        "pending_actions",
        ["user_id", "status", "created_at"],
    )
    op.create_table(
        "audit_logs",
        _id(),
        _user_fk(nullable=True, ondelete="SET NULL"),
        sa.Column("actor", sa.String(16), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", UUID),
        sa.Column("metadata", pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_ts(),
        sa.CheckConstraint("actor in ('user','system')", name="ck_audit_logs_actor_valid"),
    )
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_table(
        "privacy_events",
        _id(),
        _user_fk(),
        sa.Column("message_id", UUID, sa.ForeignKey("messages.id", ondelete="SET NULL")),
        sa.Column("entity_counts", pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *_ts(),
    )
    op.create_index("ix_privacy_events_user_created", "privacy_events", ["user_id", "created_at"])
    op.create_table(
        "llm_usage",
        _id(),
        _user_fk(nullable=True, ondelete="SET NULL"),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("tokens_in", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("escalated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("request_id", sa.String(128)),
        *_ts(),
    )
    op.create_index("ix_llm_usage_user_created", "llm_usage", ["user_id", "created_at"])
    op.create_index("ix_llm_usage_created", "llm_usage", ["created_at"])
    op.create_table(
        "reminders",
        _id(),
        _user_fk(),
        sa.Column("text_ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("nonce", sa.LargeBinary, nullable=False),
        sa.Column(
            "key_version", sa.SmallInteger, nullable=False, server_default="1"
        ),  # addition, see TODO
        sa.Column("due_at", TS, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("repeat_rule", sa.String(128)),
        *_ts(),
        sa.CheckConstraint(
            "status in ('pending','done','cancelled')", name="ck_reminders_status_valid"
        ),
    )
    op.create_index("ix_reminders_user_status_due", "reminders", ["user_id", "status", "due_at"])
    op.create_table(
        "skill_runs",
        _id(),
        _user_fk(nullable=True, ondelete="SET NULL"),
        sa.Column("skill", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)),
        *_ts(),
    )
    op.create_index("ix_skill_runs_user_created", "skill_runs", ["user_id", "created_at"])

    # ---------------------------------------------------------------- RLS
    owner_col = {t: ("id" if t == "users" else "user_id") for t in TABLES}
    for table in TABLES:
        col = owner_col[table]
        op.execute(f"alter table {table} enable row level security")
        op.execute(f"grant select, insert on {table} to authenticated")
        op.execute(
            f"create policy {table}_select_own on {table} for select to authenticated using ({col} = auth.uid())"
        )
        op.execute(
            f"create policy {table}_insert_own on {table} for insert to authenticated with check ({col} = auth.uid())"
        )
        if table != "audit_logs":  # append-only: no update/delete policy
            op.execute(f"grant update, delete on {table} to authenticated")
            op.execute(
                f"create policy {table}_update_own on {table} for update to authenticated "
                f"using ({col} = auth.uid()) with check ({col} = auth.uid())"
            )
            op.execute(
                f"create policy {table}_delete_own on {table} for delete to authenticated using ({col} = auth.uid())"
            )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
    # Extensions, the auth shim and the role are left in place (shared with Supabase).
