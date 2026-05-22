import django.utils.timezone
from django.db import migrations, models


def mark_existing_refunds_approved(apps, schema_editor):
    Refund = apps.get_model("registrations", "Refund")
    Refund.objects.exclude(gateway_ref="").update(status="APPROVED")


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0002_refund"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registration",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("CONFIRMED", "Confirmed"),
                    ("CANCELLED", "Cancelled"),
                    ("REFUND_PENDING", "Pending Refund"),
                    ("REFUNDED", "Refunded"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="refund",
            name="requested_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="refund",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="refund",
            name="gateway_ref",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="refund",
            name="refunded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_refunds_approved, migrations.RunPython.noop),
    ]
