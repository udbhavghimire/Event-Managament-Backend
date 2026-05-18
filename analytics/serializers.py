from rest_framework import serializers


class EventStatsSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    event_title = serializers.CharField()
    total_registrations = serializers.IntegerField()
    confirmed_registrations = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    capacity = serializers.IntegerField()
    fill_rate = serializers.FloatField()
