# Generated by Django 3.2 on 2022-12-13 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=200, verbose_name='Key')),
                ('bucket', models.CharField(max_length=64, verbose_name='Bucket')),
            ],
        ),
    ]
