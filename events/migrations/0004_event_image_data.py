from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_event_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="image_data",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="image_mime_type",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="event",
            name="image_thumbnail_data",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="image_thumbnail_mime_type",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
