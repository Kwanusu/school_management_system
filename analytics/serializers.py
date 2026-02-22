from rest_framework import serializers
from .models import SystemLog

class SystemLogSerializer(serializers.ModelSerializer):
    # Fetch the username of the person who triggered the log
    user_name = serializers.ReadOnlyField(source='user.username')
    # Format the timestamp for a cleaner UI display
    formatted_time = serializers.DateTimeField(source='timestamp', format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = SystemLog
        fields = [
            'id', 
            'action', 
            'user', 
            'user_name', 
            'timestamp', 
            'formatted_time', 
            'details'
        ]
        # Professional standard: Audit logs should always be immutable
        read_only_fields = ['action', 'user', 'timestamp', 'details']
        
        