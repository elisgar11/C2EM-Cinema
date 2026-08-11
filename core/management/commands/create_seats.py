from django.core.management.base import BaseCommand, CommandError

from core.models import Room, Seat


class Command(BaseCommand):
    help = "Crea butacas para una sala."

    def add_arguments(self, parser):
        parser.add_argument("room")
        parser.add_argument("rows", nargs="+")
        parser.add_argument("--count", type=int, required=True)

    def handle(self, *args, **options):
        if options["count"] < 1:
            raise CommandError("--count debe ser mayor que 0.")
        try:
            room = Room.objects.get(name=options["room"])
        except Room.DoesNotExist as exc:
            raise CommandError(f"No existe la sala: {options['room']}") from exc

        created = 0
        for row in options["rows"]:
            for number in range(1, options["count"] + 1):
                _, was_created = Seat.objects.get_or_create(room=room, row=row.upper(), number=number)
                created += int(was_created)

        self.stdout.write(self.style.SUCCESS(f"{created} butacas creadas en {room.name}."))
