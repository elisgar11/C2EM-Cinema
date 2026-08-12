from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Advertisement, Movie, Pack, PackItem, Product, Room, Screening, Seat, SiteSettings


class Command(BaseCommand):
    help = "Crea datos de demostración sin borrar datos existentes."

    def handle(self, *args, **options):
        settings = SiteSettings.load()
        settings.cinema_name = "Cine Lumière del Sótano"
        settings.tagline = "Sesiones privadas para gente de confianza."
        settings.home_message = "Elige película, reserva tus butacas y prepara las palomitas."
        settings.ticket_footer = "Guarda esta entrada: es tu acceso a la sesión."
        settings.save()

        room, _ = Room.objects.get_or_create(name="Sala Principal", defaults={"description": "Sala privada"})
        for row in "ABCDE":
            for number in range(1, 7):
                seat, _ = Seat.objects.get_or_create(room=room, row=row, number=number)
                if row == "E" and number in {3, 4} and seat.seat_type != Seat.VIP:
                    seat.seat_type = Seat.VIP
                    seat.save(update_fields=["seat_type"])

        product_data = [
            ("Palomitas pequeñas", "Ración individual", "2.00", 10),
            ("Palomitas grandes", "Para compartir o no", "4.00", 20),
            ("Refresco", "Bebida fría", "2.00", 30),
            ("Agua", "Botella de agua", "1.00", 40),
            ("Nachos", "Con salsa", "3.00", 50),
        ]
        products = {}
        for name, description, price, order in product_data:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={"description": description, "price": Decimal(price), "sort_order": order},
            )
            products[name] = product

        pack, _ = Pack.objects.get_or_create(
            name="Pack Pareja",
            defaults={"description": "Palomitas grandes y dos refrescos", "price": Decimal("6.00"), "sort_order": 10},
        )
        PackItem.objects.get_or_create(pack=pack, product=products["Palomitas grandes"], defaults={"quantity": 1})
        PackItem.objects.get_or_create(pack=pack, product=products["Refresco"], defaults={"quantity": 2})

        marathon, _ = Pack.objects.get_or_create(
            name="Pack Maratón",
            defaults={"description": "Para una sesión larga: palomitas, refrescos y nachos", "price": Decimal("8.50"), "sort_order": 20},
        )
        PackItem.objects.get_or_create(pack=marathon, product=products["Palomitas grandes"], defaults={"quantity": 1})
        PackItem.objects.get_or_create(pack=marathon, product=products["Refresco"], defaults={"quantity": 2})
        PackItem.objects.get_or_create(pack=marathon, product=products["Nachos"], defaults={"quantity": 1})

        movies = []
        for title, slug, duration, rating, description in [
            ("Alien", "alien", 117, "+16", "Terror y ciencia ficción para una noche oscura."),
            ("Dune", "dune", 155, "+12", "Una gran aventura de ciencia ficción."),
            ("Shrek", "shrek", 90, "TP", "Una sesión ligera para todos."),
        ]:
            movie, _ = Movie.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "duration_minutes": duration, "age_rating": rating, "description": description},
            )
            movies.append(movie)

        local_now = timezone.localtime()
        first_day = local_now.date() + timedelta(days=1)
        times = [time(18, 0), time(21, 0)]
        for day_offset, movie in enumerate(movies):
            if not movie.screenings.filter(start_at__gte=timezone.now()).exists():
                for start_time in times:
                    naive = datetime.combine(first_day + timedelta(days=day_offset), start_time)
                    Screening.objects.create(
                        movie=movie,
                        room=room,
                        start_at=timezone.make_aware(naive),
                        base_price=Decimal("5.00"),
                    )

        Advertisement.objects.get_or_create(
            name="Bar Paco Deluxe",
            defaults={
                "headline": "Esta sesión está patrocinada por Bar Paco Deluxe",
                "body": "Técnicamente no somos un bar, pero el anuncio queda estupendo.",
                "placement": Advertisement.HOME,
                "priority": 10,
            },
        )
        Advertisement.objects.get_or_create(
            name="Club de críticos del sofá",
            defaults={
                "headline": "Crítica oficial al terminar la sesión",
                "body": "Se aceptan opiniones firmes, spoilers solo después de los créditos.",
                "placement": Advertisement.CHECKOUT,
                "priority": 5,
            },
        )
        Advertisement.objects.get_or_create(
            name="Normas de la sala",
            defaults={
                "headline": "Silencia el móvil. Coge palomitas. Empieza el cine.",
                "body": "Los comentarios de director se reservan para después de los créditos.",
                "placement": Advertisement.PRESHOW,
                "priority": 20,
            },
        )

        self.stdout.write(self.style.SUCCESS("Datos de demostración preparados."))
