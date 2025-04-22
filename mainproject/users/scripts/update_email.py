from django.contrib.auth.models import User

def run():
    """Update email addresses for all users"""
    users = User.objects.all()
    print(f"Found {users.count()} users")
    
    for user in users:
        old_email = user.email
        user.email = 'shivam@uni.minerva.edu'
        user.save()
        print(f"Updated email for user {user.username}: {old_email} -> {user.email}") 