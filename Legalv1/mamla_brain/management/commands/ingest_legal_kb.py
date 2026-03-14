from django.core.management.base import BaseCommand

from mamla_brain.tasks import ingest_knowledge_base


class Command(BaseCommand):
    help = 'Ingest the legal Mamla Brain knowledge base into OpenSearch.'

    def handle(self, *args, **options):
        result = ingest_knowledge_base(domain_key='legal')
        self.stdout.write(self.style.SUCCESS(str(result)))
