from records.models import User
from django.db.models import Count, Max
import logging

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
	help = "Searches for duplicate usernames and deletes those with the lowest IDs."

	def handle(self, *args, **options):
		duplicate_users = User.objects.values('username').annotate(username_count=Count('username'), max_id=Max('id')).filter(username_count__gte=2)
		logging.info("Found {0} duplicate usernames.".format(len(duplicate_users.all())))
		usernames = [user['username'] for user in duplicate_users]
		max_ids = [user["max_id"] for user in duplicate_users]
		duplicate_users = User.objects.filter(username__in=usernames)
		deleted_users = 0
		for user in duplicate_users:
			if user.id not in max_ids:
				user.delete()
				deleted_users += 1
		logging.info("Deleted {0} users.".format(deleted_users))