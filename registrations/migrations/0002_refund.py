# Generated migration for Refund model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Refund",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("gateway_ref", models.CharField(max_length=200)),
                ("reason", models.TextField()),
                ("refunded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refunds",
                        to="registrations.registration",
                    ),
                ),
            ],
            options={
                "db_table": "registrations_refund",
            },
        ),
        migrations.AddIndex(
            model_name="refund",
            index=models.Index(
                fields=["registration"], name="idx_refund_registration"
            ),
        ),
    ]
