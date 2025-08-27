import io
from django.test import TransactionTestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from taggit.models import Tag, TaggedItem

from enemygen.models import Party


class TaggitDedupTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        # Create a simple object to tag
        User = get_user_model()
        # On shared DB for tests, username 'tester' may already exist; reuse if present to avoid IntegrityError
        user = User.objects.filter(username="tester").first()
        if not user:
            user = User.objects.create_user(username="tester", password="x")
        self.user = user
        self.party = Party.objects.create(name="P", owner=self.user)
        # Create or reuse a tag (idempotent on shared DB)
        self.tag, _ = Tag.objects.get_or_create(name="dup-tag")
        # Identify content type for Party
        self.ct = ContentType.objects.get_for_model(Party)

        # Ensure unique index exists before test begins (create if missing)
        self._ensure_unique_index(True)

        # Drop the unique index so we can insert duplicate rows intentionally
        self._ensure_unique_index(False)

        # Insert two duplicate TaggedItem rows
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO taggit_taggeditem (tag_id, content_type_id, object_id) VALUES (%s, %s, %s)",
                [self.tag.id, self.ct.id, self.party.id],
            )
            cur.execute(
                "INSERT INTO taggit_taggeditem (tag_id, content_type_id, object_id) VALUES (%s, %s, %s)",
                [self.tag.id, self.ct.id, self.party.id],
            )

        # Record current ids to evaluate which should be kept (lowest id)
        self.initial_ids = list(
            TaggedItem.objects.filter(tag_id=self.tag.id, content_type_id=self.ct.id, object_id=self.party.id)
            .order_by("id")
            .values_list("id", flat=True)
        )
        assert len(self.initial_ids) == 2, "Setup failed to create duplicates"

    def tearDown(self):
        # Recreate the unique index so subsequent tests (if any) see the canonical schema
        self._ensure_unique_index(True)

    def _get_unique_index_name(self):
        # Discover the unique index name for the triple columns on MySQL/MariaDB
        with connection.cursor() as cur:
            cur.execute(
                "SHOW INDEX FROM taggit_taggeditem WHERE Non_unique = 0"
            )
            rows = cur.fetchall()
        # rows columns: Table, Non_unique, Key_name, Seq_in_index, Column_name, ...
        # We look for an index that covers the triple columns (order may be fixed).
        candidate = None
        by_name = {}
        for row in rows:
            key_name = row[2]
            col_name = row[4]
            by_name.setdefault(key_name, []).append(col_name)
        for key_name, cols in by_name.items():
            if set(cols) == {"content_type_id", "object_id", "tag_id"}:
                candidate = key_name
                break
        return candidate

    def _ensure_unique_index(self, present: bool):
        idx = self._get_unique_index_name()
        with connection.cursor() as cur:
            if present:
                if not idx:
                    # Create the canonical unique index with a stable name similar to taggit migration
                    # If creation fails due to existing duplicates in a shared DB, ignore and proceed.
                    try:
                        cur.execute(
                            "CREATE UNIQUE INDEX taggit_taggeditem_ct_obj_tag_uniq ON taggit_taggeditem (content_type_id, object_id, tag_id)"
                        )
                    except Exception:
                        # Likely duplicates already exist; index cannot be created now. Proceed without it.
                        pass
            else:
                if idx:
                    cur.execute(f"ALTER TABLE taggit_taggeditem DROP INDEX {idx}")

    def test_dedup_dry_run_and_apply(self):
        # Sanity: we have duplicates
        qs = TaggedItem.objects.filter(tag_id=self.tag.id, content_type_id=self.ct.id, object_id=self.party.id)
        self.assertEqual(qs.count(), 2)

        # Dry-run: should not delete anything
        out = io.StringIO()
        call_command("taggit_dedup", dry_run=True, stdout=out)
        self.assertIn("Dry-run complete", out.getvalue())
        self.assertEqual(qs.count(), 2)

        # Apply: should delete one (keep the lowest id)
        out = io.StringIO()
        call_command("taggit_dedup", stdout=out)
        self.assertIn("Deduplication complete", out.getvalue())
        self.assertEqual(qs.count(), 1)
        remaining_id = qs.values_list("id", flat=True).first()
        self.assertEqual(remaining_id, self.initial_ids[0])

        # Idempotency: running again changes nothing
        out = io.StringIO()
        call_command("taggit_dedup", stdout=out)
        self.assertEqual(qs.count(), 1)
