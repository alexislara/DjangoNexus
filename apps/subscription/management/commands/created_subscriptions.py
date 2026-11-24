from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from faker import Faker

from apps.subscription.models import Subscription

User = get_user_model()

faker = Faker()


class Command(BaseCommand):
    help = "Este comando crea lectores con sus suscripciones"

    def handle(self, *args, **options):
        for _ in range(0, 20):
            user = User.objects.create_user(
                email=faker.email(),
                first_name=faker.first_name(),
                last_name=faker.last_name(),
                password=faker.password(),
            )

            Subscription.objects.create(
                user=user,
                book=faker.sentence(nb_words=3),
                author=faker.name(),
                is_renewal=True,
            )

        self.stdout.write(self.style.SUCCESS("Successfully...."))
