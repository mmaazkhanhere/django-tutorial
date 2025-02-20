# Generated by Django 5.1.6 on 2025-02-20 07:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTranscript',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_email', models.EmailField(max_length=254)),
                ('transcript', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='PCPContract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=50, null=True)),
                ('last_name', models.CharField(blank=True, max_length=50, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('postal_code', models.CharField(blank=True, max_length=20, null=True)),
                ('country', models.CharField(blank=True, max_length=50, null=True)),
                ('mobile_number', models.CharField(blank=True, max_length=15, null=True)),
                ('email_address', models.EmailField(max_length=254, unique=True)),
                ('car_details', models.CharField(blank=True, max_length=255, null=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('classification', models.CharField(choices=[('unsure', 'Unsure'), ('approved', 'Approved'), ('refused', 'Refused')], default='unsure', max_length=10)),
                ('is_contacted', models.BooleanField(default=False)),
                ('email_transcript', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='contracts.emailtranscript')),
                ('pcp_contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='contracts.pcpcontract')),
            ],
        ),
    ]
