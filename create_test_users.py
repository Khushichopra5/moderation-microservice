
from content.models import User
import os

def create_users():
    # Create Test User
    if not User.objects.filter(username='testuser').exists():
        user = User.objects.create_user(username='testuser', email='test@example.com', password='testpassword', role='user')
        print(f"Created user: {user.username} (role: {user.role})")
    else:
        print("User 'testuser' already exists")

    # Create Admin User
    if not User.objects.filter(username='adminuser').exists():
        admin = User.objects.create_user(username='adminuser', email='admin@example.com', password='adminpassword', role='admin')
        # Also make them a Django superuser so they can access the admin panel if needed, though our role based system is custom
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        print(f"Created admin: {admin.username} (role: {admin.role})")
    else:
        print("User 'adminuser' already exists")

if __name__ == '__main__':
    create_users()
