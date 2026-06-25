from django.core.management.base import BaseCommand

from mamla_brain.tasks import ingest_knowledge_base


class Command(BaseCommand):
    help = 'Ingest Mamla Brain knowledge-base text files into the configured OpenSearch index.'

    def add_arguments(self, parser):
        parser.add_argument('--domain', default='legal', help='Domain key to ingest, such as legal, banking, or markets.')

    def handle(self, *args, **options):
        result = ingest_knowledge_base(domain_key=options['domain'])
        self.stdout.write(self.style.SUCCESS(str(result)))
