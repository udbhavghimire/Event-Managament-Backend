from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0002_event_created_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="events/images/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="event",
            name="image_thumbnail",
            field=models.ImageField(
                blank=True,
                editable=False,
                null=True,
                upload_to="events/thumbnails/%Y/%m/",
            ),
        ),
    ]
