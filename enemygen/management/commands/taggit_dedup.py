from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = (
        "Deduplicate django-taggit's taggit_taggeditem rows by (content_type_id, object_id, tag_id). "
        "Keeps the lowest id per unique triple, deletes the rest."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be deleted without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        # Find duplicate groups
        with connection.cursor() as cursor:
            self.stdout.write("Scanning for duplicates in taggit_taggeditem ...")
            cursor.execute(
                """
                SELECT content_type_id, object_id, tag_id, COUNT(*) AS cnt
                FROM taggit_taggeditem
                GROUP BY content_type_id, object_id, tag_id
                HAVING COUNT(*) > 1
                """
            )
            dup_groups = cursor.fetchall()

        if not dup_groups:
            self.stdout.write(self.style.SUCCESS("No duplicates found in taggit_taggeditem."))
            return 0

        total_deleted = 0
        total_groups = len(dup_groups)

        for (content_type_id, object_id, tag_id, _cnt) in dup_groups:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM taggit_taggeditem
                    WHERE content_type_id=%s AND object_id=%s AND tag_id=%s
                    ORDER BY id ASC
                    """,
                    [content_type_id, object_id, tag_id],
                )
                ids = [row[0] for row in cursor.fetchall()]

            if len(ids) <= 1:
                continue

            keep_id = ids[0]
            delete_ids = ids[1:]

            if dry_run:
                self.stdout.write(
                    f"Group ({content_type_id}-{object_id}-{tag_id}): keep id={keep_id}, delete {len(delete_ids)} duplicates: {delete_ids}"
                )
            else:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        in_clause = ",".join(["%s"] * len(delete_ids))
                        cursor.execute(
                            f"DELETE FROM taggit_taggeditem WHERE id IN ({in_clause})",
                            delete_ids,
                        )
                total_deleted += len(delete_ids)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run complete: {total_groups} duplicate groups found. Would delete {total_deleted} rows."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deduplication complete: {total_groups} duplicate groups fixed, deleted {total_deleted} rows."
                )
            )

        return 0
